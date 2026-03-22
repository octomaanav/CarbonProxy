import sys
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from layers import l1, l2, l3, l4, l5, l6
from layers.gemini_client import call, call_with_history
from metrics import SessionMetrics, RequestRecord, estimate_tokens, estimate_co2, estimate_cost_usd, format_usd
from config import DEFAULT_BASELINE_MODEL


class CarbonProxyEngine:
    def __init__(self):
        self.session = SessionMetrics()

    def complete(
        self,
        prompt: str,
        task_type: Optional[str] = None,
        output_format: Optional[str] = None,
        max_words: Optional[int] = None,
        bullet_count: Optional[int] = None,
        baseline_model: Optional[str] = None,
        history: Optional[list] = None,
        static_context: Optional[str] = None,
        use_cache: bool = True,
        use_classifier: bool = True,
    ) -> dict:
        prompt = (prompt or "").strip()
        if not prompt:
            return {
                "response": "",
                "error": "empty prompt",
                "cache_hit": False,
                "cached_response": None,
                "tokens_before": 0,
                "tokens_after": 0,
                "savings_pct": 0,
                "co2_g": 0.0,
                "carbon_saved_g": 0.0,
                "money_saved_usd": 0.0,
                "money_saved_display": "$0.00000000",
                "baseline_model": baseline_model or DEFAULT_BASELINE_MODEL,
                "actual_cost_usd": 0.0,
                "baseline_cost_usd": 0.0,
                "money_saved_vs_baseline_usd": 0.0,
                "model": "none",
                "provider": "none",
                "intent": "default",
                "route_reason": "none",
            }

        tokens_before = estimate_tokens(prompt)

        if use_cache:
            cache_result = l3.check(prompt)
            if cache_result["hit"]:
                response = cache_result["response"]
                tokens_used = estimate_tokens(response)
                self.session.record(
                    RequestRecord(
                        model="cache",
                        tokens_before=tokens_before,
                        tokens_after=tokens_before,
                        tokens_used=tokens_used,
                        co2_g=0.0,
                        cached=True,
                    )
                )
                return {
                    "response": response,
                    "cache_hit": True,
                    "cached_response": response,
                    "tokens_before": tokens_before,
                    "tokens_after": tokens_before,
                    "savings_pct": 0,
                    "co2_g": 0.0,
                    "carbon_saved_g": 0.0,
                    "money_saved_usd": 0.0,
                    "money_saved_display": "$0.00000000",
                    "baseline_model": baseline_model or DEFAULT_BASELINE_MODEL,
                    "actual_cost_usd": 0.0,
                    "baseline_cost_usd": 0.0,
                    "money_saved_vs_baseline_usd": 0.0,
                    "model": "cache",
                    "provider": "cache",
                    "intent": "cache",
                    "route_reason": "semantic cache hit",
                    "matched_prompt": cache_result.get("matched_prompt"),
                    "similarity": cache_result.get("similarity", 0.0),
                    "compressed_prompt": prompt,
                }

        route_result = l4.route(prompt=prompt, task_type=task_type, use_classifier=use_classifier)
        model = route_result["model"]
        provider = route_result.get("provider", "google")
        intent = route_result.get("intent", "default")

        compression_result = l1.compress(prompt, use_llm=True)
        compressed_prompt = compression_result["compressed"]
        tokens_after_compression = compression_result["tokens_after"]  # Capture BEFORE constraints
        savings_pct = compression_result["savings_pct"]

        final_prompt = l6.build_structured_prompt(
            compressed_prompt,
            output_format=output_format,
            max_words=max_words,
            bullet_count=bullet_count,
        )

        system_prompt = l2.get_system_with_context(intent, static_context)
        max_tokens = l6.get_max_tokens(intent, output_format=output_format)

        response = ""
        if history:
            prepared_history = l5.rolling_window(history)
            prepared_history = l5.summarize_history(prepared_history)
            prepared_history = l5.enforce_token_budget(prepared_history)
            prepared_history = prepared_history + [{"role": "user", "content": final_prompt}]

            response = call_with_history(
                messages=prepared_history,
                model=model,
                system=system_prompt,
                max_tokens=max_tokens,
                temperature=0.2,
            )
        else:
            response = call(
                prompt=final_prompt,
                model=model,
                system=system_prompt,
                max_tokens=max_tokens,
                temperature=0.2,
            )

        tokens_used = tokens_after_compression + estimate_tokens(response)
        co2_g = estimate_co2(tokens_used, model)
        tokens_saved = max(0, tokens_before - tokens_after_compression)
        carbon_saved_g = estimate_co2(tokens_saved, model)
        money_saved_usd = estimate_cost_usd(tokens_saved, model)
        baseline = baseline_model or DEFAULT_BASELINE_MODEL
        actual_cost_usd = estimate_cost_usd(tokens_used, model)
        baseline_cost_usd = estimate_cost_usd(tokens_used, baseline)
        money_saved_vs_baseline_usd = round(max(0.0, baseline_cost_usd - actual_cost_usd), 8)

        if use_cache and response.strip():
            l3.store(prompt, response)

        self.session.record(
            RequestRecord(
                model=model,
                tokens_before=tokens_before,
                tokens_after=tokens_after_compression,
                tokens_used=tokens_used,
                co2_g=co2_g,
                cached=False,
            )
        )

        return {
            "response": response,
            "cache_hit": False,
            "cached_response": None,
            "tokens_before": tokens_before,
            "tokens_after": tokens_after_compression,
            "savings_pct": savings_pct,
            "co2_g": co2_g,
            "carbon_saved_g": carbon_saved_g,
            "money_saved_usd": money_saved_usd,
            "money_saved_display": format_usd(money_saved_usd),
            "baseline_model": baseline,
            "actual_cost_usd": actual_cost_usd,
            "baseline_cost_usd": baseline_cost_usd,
            "money_saved_vs_baseline_usd": money_saved_vs_baseline_usd,
            "model": model,
            "provider": provider,
            "intent": intent,
            "route_reason": route_result.get("reason", ""),
            "matched_prompt": None,
            "similarity": 0.0,
            "compressed_prompt": compressed_prompt,
        }

    def metrics(self) -> dict:
        data = self.session.to_dict()
        data["history"] = [
            {
                "model": rec.model,
                "tokens_before": rec.tokens_before,
                "tokens_after": rec.tokens_after,
                "tokens_used": rec.tokens_used,
                "co2_g": rec.co2_g,
                "cached": rec.cached,
                "timestamp": rec.timestamp,
            }
            for rec in self.session.history[-50:]
        ]
        return data

    def cache_stats(self) -> dict:
        return l3.stats()

    def reset_session(self) -> None:
        self.session.reset()

    def reset_all(self) -> None:
        self.session.reset()
        l3.clear()

    def cache_check(self, prompt: str) -> dict:
        return l3.check(prompt)

    def cache_store(self, prompt: str, response: str) -> None:
        if prompt.strip() and response.strip():
            l3.store(prompt, response)

    def warm_cache(self, pairs: list[tuple[str, str]]) -> None:
        if pairs:
            l3.warm(pairs)
