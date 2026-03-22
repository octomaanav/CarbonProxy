import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
META_API_KEY = os.getenv("META_API_KEY", "")

MODEL_FLASH = "gemini-2.5-flash"
MODEL_PRO = "gemini-2.5-pro"
MODEL_FLASH_LITE = "gemini-2.5-flash"
DEFAULT_MODEL = MODEL_FLASH

MODEL_MULTIPLIERS = {
    MODEL_FLASH: 0.1,
    MODEL_FLASH_LITE: 0.1,
    MODEL_PRO: 1.0,
    "cache": 0.0,
}

MODEL_COST_PER_1M_TOKENS_USD = {
    MODEL_FLASH: 0.35,
    MODEL_FLASH_LITE: 0.35,
    MODEL_PRO: 3.50,
    "gpt-4o-mini": 0.60,
    "gpt-4o": 7.50,
    "gpt-4.1": 12.00,
    "claude-3-5-haiku-latest": 1.20,
    "claude-3-5-sonnet-latest": 6.00,
    "claude-3-7-sonnet-latest": 7.00,
    "llama-3.1-70b-instruct": 0.90,
    "llama-3.1-405b-instruct": 5.00,
    "cache": 0.0,
}

DEFAULT_BASELINE_MODEL = "gpt-4o-mini"

KWH_PER_TOKEN = 0.0000002
GRID_INTENSITY = 400

CACHE_SIMILARITY_THRESHOLD = 0.92
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

DEFAULT_MAX_CONTEXT_TOKENS = 4000
DEFAULT_ROLLING_WINDOW = 10
SUMMARIZE_THRESHOLD_TOKENS = 2000

MAX_TOKENS_BY_INTENT = {
    "simple_qa": 500,
    "code_gen": 2000,
    "code_review": 1200,
    "analysis": 1500,
    "creative": 2000,
    "default": 800,
}

ROUTE_FLASH_MAX_TOKENS = 600

# Layer 1 (compression) heuristics
L1_STRIP_PREFIXES = [
    "you are a helpful assistant",
    "you are a helpful ai assistant",
    "you are an expert",
    "you are a senior",
    "you are an experienced",
    "as a language model",
    "as an ai",
    "please help me",
    "can you help me",
    "could you please",
    "i would like you to",
    "i need you to",
    "make sure to",
    "ensure that",
    "don't forget to",
    "it is important that you",
    "it's important that you",
    "in your response, please",
    "your answer should",
    "feel free to",
    "thank you",
    "kindly",
]

L1_INLINE_NOISE_WORDS = [
    "kindly",
    "please",
]

# Layer 2 (system prompt audit) heuristics
L2_AUDIT_FILLER_PHRASES = [
    "you are a helpful",
    "you are an honest",
    "your goal is to",
    "always be polite",
    "always be professional",
    "try to be",
    "make sure to",
    "don't forget",
    "as an ai",
    "i want you to",
    "please provide",
]

# Layer 3 (semantic cache) normalization and concept matching
L3_CANONICAL_REPLACEMENTS = {
    "difference between": "vs",
    "graphql apis": "graphql",
    "rest apis": "rest",
    "apis": "api",
    "javascript": "js",
    "js": "js",
    "ml": "machine learning",
}

L3_CONCEPT_GROUPS = [
    {"rest", "graphql"},
    {"machine", "learning"},
    {"async", "await"},
    {"docker", "container"},
    {"sql", "nosql"},
]

L3_LOW_OVERLAP_CUTOFF = 0.1
L3_LOW_OVERLAP_SIMILARITY_CAP = 0.49

# Layer 4 (routing) keywords by intent
L4_INTENT_KEYWORDS = {
    "architecture": ["architecture", "cap theorem", "globally distributed", "distributed database", "scalability"],
    "code_review": ["review this code", "review code", "bugs", "bug", "lint", "security issues"],
    "code_gen": ["write a", "function", "implement", "generate code", "build a"],
    "analysis": ["analyze", "tradeoffs", "compare pros and cons", "evaluate"],
    "explain": ["explain", "to a beginner", "how does"],
    "creative": ["story", "poem", "creative", "brainstorm"],
}

# Layer 5 (context management)
L5_SUMMARIZE_SYSTEM = (
    "Summarize this conversation in 3-5 bullet points. "
    "Preserve: decisions made, code written, key facts, constraints. "
    "Omit: greetings, tangents, repetition. "
    "Output bullet points only."
)

L5_SUMMARIZE_KEEP_LAST = 6

# Provider-aware routing order by task intent (best → fallback)
PROVIDER_MODEL_CATALOG = {
    "simple_qa": [
        {"provider": "google", "model": MODEL_FLASH},
        {"provider": "openai", "model": "gpt-4o-mini"},
        {"provider": "anthropic", "model": "claude-3-5-haiku-latest"},
        {"provider": "meta", "model": "llama-3.1-70b-instruct"},
    ],
    "code_gen": [
        {"provider": "google", "model": MODEL_FLASH},
        {"provider": "openai", "model": "gpt-4o"},
        {"provider": "anthropic", "model": "claude-3-5-sonnet-latest"},
        {"provider": "meta", "model": "llama-3.1-70b-instruct"},
    ],
    "code_review": [
        {"provider": "google", "model": MODEL_FLASH},
        {"provider": "anthropic", "model": "claude-3-5-sonnet-latest"},
        {"provider": "openai", "model": "gpt-4o"},
        {"provider": "meta", "model": "llama-3.1-70b-instruct"},
    ],
    "analysis": [
        {"provider": "google", "model": MODEL_FLASH},
        {"provider": "openai", "model": "gpt-4o"},
        {"provider": "anthropic", "model": "claude-3-5-sonnet-latest"},
        {"provider": "meta", "model": "llama-3.1-70b-instruct"},
    ],
    "explain": [
        {"provider": "google", "model": MODEL_FLASH},
        {"provider": "openai", "model": "gpt-4o-mini"},
        {"provider": "anthropic", "model": "claude-3-5-haiku-latest"},
        {"provider": "meta", "model": "llama-3.1-70b-instruct"},
    ],
    "creative": [
        {"provider": "anthropic", "model": "claude-3-5-sonnet-latest"},
        {"provider": "openai", "model": "gpt-4o"},
        {"provider": "google", "model": MODEL_PRO},
        {"provider": "meta", "model": "llama-3.1-70b-instruct"},
    ],
    "architecture": [
        {"provider": "google", "model": MODEL_PRO},
        {"provider": "anthropic", "model": "claude-3-7-sonnet-latest"},
        {"provider": "openai", "model": "gpt-4.1"},
        {"provider": "meta", "model": "llama-3.1-405b-instruct"},
    ],
    "default": [
        {"provider": "google", "model": MODEL_FLASH},
        {"provider": "openai", "model": "gpt-4o-mini"},
        {"provider": "anthropic", "model": "claude-3-5-haiku-latest"},
        {"provider": "meta", "model": "llama-3.1-70b-instruct"},
    ],
}
