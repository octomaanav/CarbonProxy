export const CARBONPROXY_API_PREFIX = '/api';

export const CARBONPROXY_API_ROUTES = {
  optimize: `${CARBONPROXY_API_PREFIX}/optimize`,
  cacheCheck: `${CARBONPROXY_API_PREFIX}/cache/check`,
  cacheStore: `${CARBONPROXY_API_PREFIX}/cache/store`,
  metrics: `${CARBONPROXY_API_PREFIX}/metrics`,
  reset: `${CARBONPROXY_API_PREFIX}/demo/reset`,
  health: `${CARBONPROXY_API_PREFIX}/health`,
} as const;

export type CarbonProxyApiRouteKey = keyof typeof CARBONPROXY_API_ROUTES;
