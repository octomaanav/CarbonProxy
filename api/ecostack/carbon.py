"""Carbon estimation constants and helpers for the EcoStack memory layer."""

# carbon.py
# Sources: Google AI environmental report (Aug 2025), Devera AI analysis (2025),
# Epoch AI benchmarks, academic inference studies (Jegham et al. 2025)
# Method: Wh/token × grid carbon intensity (0.39 kg CO₂/kWh US average)
# All values in grams CO₂ per token (inference only, not training)

MODEL_CO2_RATES: dict[str, float] = {

    # ── Google Gemini ─────────────────────────────────────
    "gemini-2.0-flash":        0.00021,   # lightest frontier model
    "gemini-2.5-flash":        0.00025,   # slightly heavier than 2.0 flash
    "gemini-2.5-pro":          0.0018,    # full Pro reasoning model

    # ── OpenAI ────────────────────────────────────────────
    "gpt-4o-mini":             0.00019,   # comparable to Gemini Flash tier
    "gpt-4o":                  0.00130,   # 0.30 Wh/query ÷ ~230 tokens avg
    "gpt-4-turbo":             0.00290,   # older architecture, less efficient
    "o3-mini":                 0.00035,   # reasoning model, surprisingly lean
    "o3":                      0.00420,   # full reasoning — extended thinking

    # ── Anthropic Claude ──────────────────────────────────
    "claude-haiku-4-5":        0.00023,   # fastest Claude, lowest footprint
    "claude-sonnet-4-5":       0.00120,   # mid-tier — strong eco-efficiency
    "claude-opus-4-5":         0.00380,   # 4.05 Wh/query (Devera, 2025)

    # ── Meta Llama (self-hosted, H100 cluster) ────────────
    "llama-3.1-8b":            0.00008,   # tiny model, very low emissions
    "llama-3.1-70b":           0.00063,   # ~1.7 Wh/query (AI Energy Score)
    "llama-3.1-405b":          0.00310,   # largest open model

    # ── DeepSeek ──────────────────────────────────────────
    "deepseek-v3":             0.00015,   # MoE — only 37B active params
    "deepseek-r1":             0.00028,   # reasoning variant, slightly heavier

    # ── Mistral ───────────────────────────────────────────
    "mistral-large-2":         0.00095,   # ~1g CO₂ per page (Mistral LCA)
    "mistral-small":           0.00021,   # efficient small model

}

# Grid intensity used for derivation: 0.39 kg CO₂/kWh (US average, IEA 2024)
# Google uses 30% clean energy, so Gemini numbers are naturally lower
# Self-hosted values assume typical H100 cluster at US grid intensity
GRID_INTENSITY_KG_PER_KWH = 0.39

DEFAULT_CO2_RATE = 0.00021  # fallback to flash rate

def estimate_carbon(
    model: str,
    tokens_sent: int,
    tokens_saved: int,
) -> tuple[float, float]:
    """Return (co2_consumed, co2_avoided) in grams."""
    rate = MODEL_CO2_RATES.get(model, DEFAULT_CO2_RATE)
    co2_consumed = round(tokens_sent * rate, 6)
    co2_avoided = round(tokens_saved * rate, 6)
    return co2_consumed, co2_avoided
