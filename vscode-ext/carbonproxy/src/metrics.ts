const KWH_PER_TOKEN = 0.0000002;
const GRID_INTENSITY = 400;

export const MODEL_MULTIPLIER: Record<string, number> = {
  'claude-haiku-4-5': 0.1,
  'claude-haiku-3': 0.1,
  'claude-sonnet-4-5': 1.0,
  'claude-sonnet-3-5': 1.0,
  'claude-opus-4-5': 3.0,
  'claude-opus-3': 3.0,
  'gpt-4o-mini': 0.2,
  'gpt-4o': 1.5,
  'gpt-4': 2.0,
  cache: 0.0,
};

export function estimateCO2(tokensIn: number, tokensOut: number, model: string): number {
  const total = tokensIn + tokensOut;
  const multiplier = MODEL_MULTIPLIER[model] ?? 1.0;
  const kwh = total * KWH_PER_TOKEN * multiplier;
  const co2 = kwh * GRID_INTENSITY;
  return parseFloat(co2.toFixed(6));
}

export function estimateTokens(text: string): number {
  return Math.ceil(text.split(/\s+/).length * 1.3);
}

export function co2ToEquivalent(grams: number): string {
  if (grams === 0) return 'nothing — cache hit';
  if (grams < 0.001) return 'less than a breath of air';
  if (grams < 0.01) return `${(grams * 1000).toFixed(1)}mg — a few keystrokes of energy`;
  if (grams < 0.1) return `${(grams * 30).toFixed(1)}m of phone scrolling`;
  if (grams < 1.0) return `${(grams * 0.5).toFixed(2)} seconds of laptop use`;
  if (grams < 10) return `${(grams / 10).toFixed(2)}g of coal equivalent`;
  return `${(grams / 1000).toFixed(3)}kg CO₂`;
}

export function buildMetricsTable(opts: {
  cacheHit: boolean;
  tokensBefore: number;
  tokensAfter: number;
  co2G: number;
  model: string;
  savingsPct: number;
}): string {
  if (opts.cacheHit) {
    return `
---
**⚡ CarbonProxy — CACHE HIT**

| Metric | Value |
|---|---|
| Tokens consumed | \`0\` — reused cached response |
| CO₂ emitted | \`0.000000g\` |
| Savings | \`100%\` |
| Source | Semantic cache (cosine similarity ≥ 0.92) |

`;
  }

  return `
---
**🌱 CarbonProxy Metrics**

| Metric | Value |
|---|---|
| Tokens before optimization | \`${opts.tokensBefore}\` |
| Tokens after optimization | \`${opts.tokensAfter}\` |
| Token savings | \`${opts.savingsPct}%\` fewer tokens |
| Model selected | \`${opts.model}\` |
| CO₂ this request | \`${opts.co2G.toFixed(6)}g\` |
| Equivalent to | ${co2ToEquivalent(opts.co2G)} |

`;
}
