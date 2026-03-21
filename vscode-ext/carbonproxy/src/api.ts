import * as vscode from 'vscode';

const API_ROUTES = {
  optimize: '/api/optimize',
  cacheCheck: '/api/cache/check',
  cacheStore: '/api/cache/store',
  metrics: '/api/metrics',
  reset: '/api/demo/reset',
  health: '/api/health',
} as const;

function getBaseUrl(): string {
  return vscode.workspace
    .getConfiguration('carbonproxy')
    .get<string>('backendUrl', 'http://localhost:8080');
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${getBaseUrl()}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`CarbonProxy backend error ${res.status} on ${path}`);
  }
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${getBaseUrl()}${path}`);
  if (!res.ok) {
    throw new Error(`CarbonProxy backend error ${res.status} on ${path}`);
  }
  return res.json() as Promise<T>;
}

export interface OptimizeResult {
  original_prompt: string;
  optimized_prompt: string;
  tokens_before: number;
  tokens_after: number;
  savings_pct: number;
  cache_hit: boolean;
  cached_response?: string;
  response?: string;
  co2_g: number;
  model: string;
}

export interface CacheCheckResult {
  hit: boolean;
  cached_response?: string;
  similarity: number;
}

export interface BackendMetrics {
  requests: number;
  tokens_saved: number;
  co2_saved_g: number;
  cache_hits: number;
  co2_equivalent: string;
  history: Array<{ model: string; co2_g: number; cached: boolean }>;
}

export const optimizePrompt = (prompt: string) =>
  post<OptimizeResult>(API_ROUTES.optimize, { prompt });

export const checkCache = (prompt: string) =>
  post<CacheCheckResult>(API_ROUTES.cacheCheck, { prompt });

export const storeCache = (prompt: string, response: string) =>
  post<{ stored: boolean }>(API_ROUTES.cacheStore, { prompt, response });

export const getMetrics = () =>
  get<BackendMetrics>(API_ROUTES.metrics);

export const resetBackendSession = () =>
  post<{ ok: boolean }>(API_ROUTES.reset, {});

export const checkHealth = () =>
  get<{ status: string; cache_size: number }>(API_ROUTES.health);
