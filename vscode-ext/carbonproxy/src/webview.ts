import { OptimizeResult } from './api';

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function buildResultHtml(data: OptimizeResult): string {
  const isCacheHit = data.cache_hit;
  const savings = data.savings_pct ?? 0;
  const responsePreview = isCacheHit
    ? `${(data.cached_response ?? '').substring(0, 600)}\n\n[Full response from cache]`
    : data.optimized_prompt;

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
<style>
  body {
    font-family: system-ui, -apple-system, sans-serif;
    padding: 24px;
    color: #1a1a1a;
    background: #ffffff;
    line-height: 1.6;
  }
  @media (prefers-color-scheme: dark) {
    body { color: #e0e0e0; background: #1e1e1e; }
    .before { background: #3a1a1a !important; }
    .after  { background: #1a3a1a !important; }
    .stat   { background: #2a2a2a !important; }
    .cache-badge { background: #1a3a1a !important; }
  }
  h2 { font-size: 15px; margin: 0 0 16px; font-weight: 600; }
  .stats {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
    margin-bottom: 18px;
  }
  .stat {
    background: #f5f5f5;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }
  .stat-val { font-size: 22px; font-weight: 700; }
  .stat-lbl {
    font-size: 10px;
    color: #888;
    margin-top: 3px;
    text-transform: uppercase;
    letter-spacing: .06em;
  }
  .cache-badge {
    background: #e6f9f0;
    border: 1px solid #1D9E75;
    color: #085041;
    border-radius: 8px;
    padding: 12px 16px;
    font-weight: 600;
    font-size: 13px;
    text-align: center;
    margin-bottom: 16px;
  }
  .before { background: #fff0f0; border-radius: 8px; padding: 14px; margin-bottom: 12px; }
  .after  { background: #f0fff4; border-radius: 8px; padding: 14px; }
  .section-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .07em;
    margin-bottom: 8px;
  }
  .before .section-label { color: #c0392b; }
  .after  .section-label { color: #1a7a4a; }
  pre {
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 12px;
    margin: 0;
    line-height: 1.65;
    font-family: 'SF Mono', 'Fira Code', monospace;
  }
</style>
</head>
<body>

<h2>CarbonProxy Result</h2>

<div class="stats">
  <div class="stat">
    <div class="stat-val">${savings}%</div>
    <div class="stat-lbl">tokens saved</div>
  </div>
  <div class="stat">
    <div class="stat-val">${isCacheHit ? 'Cache' : (data.model?.split('-')[1] ?? 'AI')}</div>
    <div class="stat-lbl">source</div>
  </div>
  <div class="stat">
    <div class="stat-val">${(data.co2_g ?? 0).toFixed(4)}g</div>
    <div class="stat-lbl">CO₂ used</div>
  </div>
</div>

${isCacheHit ? '<div class="cache-badge">⚡ CACHE HIT — 0 tokens consumed · 0.0000g CO₂ · Instant response</div>' : ''}

<div class="before">
  <div class="section-label">Before — ${data.tokens_before} tokens</div>
  <pre>${escapeHtml(data.original_prompt ?? '')}</pre>
</div>

<div class="after">
  <div class="section-label">
    ${isCacheHit ? 'Cached response (preview)' : `After — ${data.tokens_after} tokens`}
  </div>
  <pre>${escapeHtml(responsePreview ?? '')}</pre>
</div>

</body>
</html>`;
}
