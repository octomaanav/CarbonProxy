from layers.l4 import route
from config import MODEL_FLASH, MODEL_PRO

tests = [
    ("What is 2+2?", MODEL_FLASH, "simple_qa"),
    ("Write a Python function to reverse a string", MODEL_FLASH, "code_gen"),
    ("Review this code for bugs: def add(a,b): return a+b", MODEL_FLASH, "code_review"),
    ("Analyze the tradeoffs between microservices and monolith", MODEL_FLASH, "analysis"),
    ("Explain how TCP/IP works to a beginner", MODEL_FLASH, "explain"),
    (
        "Design a globally distributed database architecture with CAP theorem tradeoffs",
        MODEL_PRO,
        "architecture",
    ),
]

print(f"{'Prompt':<52} {'Expected':<10} {'Got':<10} {'Intent':<15} Status")
print("-" * 105)
for prompt, expected_model, expected_intent in tests:
    result = route(prompt)
    status = "PASS" if (result["model"] == expected_model and result["intent"] == expected_intent) else "FAIL"
    got_short = "pro" if "pro" in result["model"] else "flash"
    exp_short = "pro" if "pro" in expected_model else "flash"
    print(f"{prompt[:50]:<52} {exp_short:<10} {got_short:<10} {result['intent']:<15} {status}")
