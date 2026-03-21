export interface SessionMetrics {
  requests: number;
  tokensSaved: number;
  co2SavedG: number;
  cacheHits: number;
  history: Array<{
    model: string;
    co2G: number;
    tokensSaved: number;
    cached: boolean;
    timestamp: number;
  }>;
}

export const session: SessionMetrics = {
  requests: 0,
  tokensSaved: 0,
  co2SavedG: 0,
  cacheHits: 0,
  history: [],
};

export function recordMetric(opts: {
  model: string;
  co2G: number;
  tokensSaved: number;
  cached: boolean;
}): void {
  session.requests++;
  session.tokensSaved += opts.tokensSaved;
  session.co2SavedG = parseFloat((session.co2SavedG + opts.co2G).toFixed(6));
  if (opts.cached) session.cacheHits++;
  session.history.push({ ...opts, timestamp: Date.now() });
}

export function resetSession(): void {
  session.requests = 0;
  session.tokensSaved = 0;
  session.co2SavedG = 0;
  session.cacheHits = 0;
  session.history = [];
}
