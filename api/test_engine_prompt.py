#!/usr/bin/env python3
import argparse
import json

from engine import CarbonProxyEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test CarbonProxyEngine with a single prompt")
    parser.add_argument("prompt", help="Prompt string to optimize and run")
    parser.add_argument("--task-type", default=None, help="Optional task type hint")
    parser.add_argument("--output-format", default=None, choices=["json", "code", "bullets"], help="Optional output format")
    parser.add_argument("--max-words", type=int, default=None, help="Optional max words constraint")
    parser.add_argument("--bullet-count", type=int, default=None, help="Optional bullet count for bullets format")
    parser.add_argument("--baseline-model", default=None, help="Optional baseline model for cost comparison")
    parser.add_argument("--no-cache", action="store_true", help="Disable semantic cache for this request")
    parser.add_argument("--no-classifier", action="store_true", help="Disable intent classifier routing")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = CarbonProxyEngine()

    result = engine.complete(
        prompt=args.prompt,
        task_type=args.task_type,
        output_format=args.output_format,
        max_words=args.max_words,
        bullet_count=args.bullet_count,
        baseline_model=args.baseline_model,
        history=None,
        static_context=None,
        use_cache=not args.no_cache,
        use_classifier=not args.no_classifier,
    )

    output = {
        "original_prompt": args.prompt,
        "optimized_prompt": result.get("compressed_prompt", args.prompt),
        "tokens_before": result.get("tokens_before", 0),
        "tokens_after": result.get("tokens_after", 0),
        "savings_pct": result.get("savings_pct", 0),
        "cache_hit": result.get("cache_hit", False),
        "response": result.get("response", ""),
        "carbon_saved_g": result.get("carbon_saved_g", 0.0),
        "money_saved_usd": result.get("money_saved_usd", 0.0),
        "money_saved_display": result.get("money_saved_display", "$0.00000000"),
        "baseline_model": result.get("baseline_model", "gpt-4o-mini"),
        "actual_cost_usd": result.get("actual_cost_usd", 0.0),
        "baseline_cost_usd": result.get("baseline_cost_usd", 0.0),
        "money_saved_vs_baseline_usd": result.get("money_saved_vs_baseline_usd", 0.0),
        "model": result.get("model", "unknown"),
        "provider": result.get("provider", "unknown"),
        "intent": result.get("intent", "default"),
        "route_reason": result.get("route_reason", ""),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
