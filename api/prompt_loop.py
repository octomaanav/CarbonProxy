#!/usr/bin/env python3
import json

from engine import CarbonProxyEngine


def read_prompt() -> str:
    print("\nPaste your prompt. End input with a line containing only /run")
    print("Type /quit on a new line to exit.")

    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            return "/quit"

        if line.strip() == "/quit":
            return "/quit"
        if line.strip() == "/run":
            break

        lines.append(line)

    return "\n".join(lines).strip()


def main() -> None:
    engine = CarbonProxyEngine()

    print("CarbonProxy prompt loop started.")
    print("Commands: /run (submit), /quit (exit)")

    while True:
        prompt = read_prompt()

        if prompt == "/quit":
            print("Exiting prompt loop.")
            break

        if not prompt:
            print("Empty prompt. Try again.")
            continue

        try:
            result = engine.complete(
                prompt=prompt,
                output_format="bullets",
                bullet_count=3,
                use_cache=False,
            )
        except Exception as err:
            print(f"Engine error: {err}")
            continue

        output = {
            "original_prompt": prompt,
            "optimized_prompt": result.get("compressed_prompt", prompt),
            "tokens_before": result.get("tokens_before", 0),
            "tokens_after": result.get("tokens_after", 0),
            "savings_pct": result.get("savings_pct", 0),
            "response": result.get("response", ""),
            "model": result.get("model", "unknown"),
            "provider": result.get("provider", "unknown"),
            "intent": result.get("intent", "default"),
            "co2_g": result.get("co2_g", 0.0),
            "carbon_saved_g": result.get("carbon_saved_g", 0.0),
            "money_saved_usd": result.get("money_saved_usd", 0.0),
            "money_saved_display": result.get("money_saved_display", "$0.00000000"),
        }
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
