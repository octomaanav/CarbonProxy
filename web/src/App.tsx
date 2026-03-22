import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Leaf, Cpu, Zap, Bot, RotateCcw, Activity,
  TrendingDown, Coins, BatteryCharging, Users,
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';

/* ── Types ──────────────────────────────────────────────────────────── */

interface DashboardSummary {
  requests: number;
  tokens_saved: number;
  total_tokens_in: number;
  total_tokens_out: number;
  co2_saved_g: number;
  cache_hits: number;
  cache_hit_rate: number;
  co2_equivalent: string;
}

interface EnergyData {
  total_kwh: number;
  total_cost_usd: number;
  annual_team_co2_g: number;
}

interface ModelDist { model: string; count: number; }

interface TimelineItem {
  timestamp: number;
  co2_g: number;
  cumulative_co2: number;
  tokens_in: number;
  model: string;
  cached: boolean;
}

interface ActivityItem {
  model: string;
  co2_g: number;
  cached: boolean;
  timestamp: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  prompt_preview: string;
}

interface DashboardData {
  summary: DashboardSummary;
  energy: EnergyData;
  model_distribution: ModelDist[];
  timeline: TimelineItem[];
  recent_activity: ActivityItem[];
}

const API = 'http://localhost:8080';

const MODEL_COLORS: Record<string, string> = {
  'claude-haiku-4-5': '#2dd4bf',
  'claude-sonnet-4-5': '#60a5fa',
  'gpt-4o': '#a78bfa',
  'gpt-4o-mini': '#f472b6',
  'gpt-4': '#fb923c',
  'cache': '#fbbf24',
};
const PIE_COLORS = ['#34d399', '#60a5fa', '#a78bfa', '#fbbf24', '#f472b6', '#fb923c'];

/* ── Animated counter hook ──────────────────────────────────────────── */

function useAnimatedNumber(target: number, decimals = 0, duration = 600) {
  const [display, setDisplay] = useState(target);
  const raf = useRef<number>(0);

  useEffect(() => {
    const start = display;
    const diff = target - start;
    if (Math.abs(diff) < (decimals > 0 ? 0.00005 : 0.5)) { setDisplay(target); return; }
    const t0 = performance.now();
    const step = (now: number) => {
      const elapsed = now - t0;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(start + diff * eased);
      if (progress < 1) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [target]);

  return decimals > 0 ? display.toFixed(decimals) : Math.round(display).toLocaleString();
}

/* ── Time formatting ────────────────────────────────────────────────── */

function timeAgo(ts: number): string {
  const diff = Math.floor(Date.now() / 1000 - ts);
  if (diff < 5) return 'just now';
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

/* ── Component ──────────────────────────────────────────────────────── */

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [connected, setConnected] = useState(true);

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/dashboard`);
      if (!res.ok) throw new Error();
      setData(await res.json());
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
    const id = setInterval(fetchDashboard, 2000);
    return () => clearInterval(id);
  }, [fetchDashboard]);

  const resetSession = async () => {
    await fetch(`${API}/api/demo/reset`, { method: 'POST' });
    fetchDashboard();
  };

  // Animated counters
  const co2Val = useAnimatedNumber(data?.summary.co2_saved_g ?? 0, 4);
  const tokenVal = useAnimatedNumber(data?.summary.tokens_saved ?? 0);
  const reqVal = useAnimatedNumber(data?.summary.requests ?? 0);
  const hitVal = useAnimatedNumber(data?.summary.cache_hit_rate ?? 0, 1);

  /* ── Disconnected state ──────────────────────────────────────────── */
  if (!connected && !data) {
    return (
      <div className="flex items-center justify-center min-h-screen p-6">
        <div className="text-center p-10 card max-w-md">
          <div className="orb-container mx-auto mb-6 w-[120px] h-[120px]">
            <div className="orb-core" style={{ opacity: 0.3 }}></div>
          </div>
          <h2 className="text-xl font-semibold mb-2 text-zinc-300">Backend Offline</h2>
          <p className="text-sm text-zinc-500">
            Cannot connect to CarbonProxy backend.<br />
            Ensure the Python server is running on port 8080.
          </p>
        </div>
      </div>
    );
  }

  const s = data?.summary;
  const e = data?.energy;

  // Chart data
  const timelineData = (data?.timeline ?? []).map((t, i) => ({
    idx: i + 1,
    co2: t.cumulative_co2,
    instant: t.co2_g,
    cached: t.cached,
  }));

  const pieData = (data?.model_distribution ?? []).map(d => ({
    name: d.model,
    value: d.count,
  }));

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8">
      <div className="max-w-[1400px] mx-auto space-y-6">

        {/* ── Navbar ─────────────────────────────────────────────────── */}
        <nav className="flex items-center justify-between py-3 animate-in">
          <div className="flex items-center gap-3">
            <div className="relative w-9 h-9 flex items-center justify-center">
              <Leaf className="w-5 h-5 text-emerald-400 absolute" />
              <Cpu className="w-4 h-4 text-emerald-600 absolute translate-x-1.5 translate-y-1.5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold leading-tight tracking-tight">CarbonProxy</h1>
              <p className="text-[11px] text-zinc-500 tracking-wide">SUSTAINABILITY DASHBOARD</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-zinc-800 bg-zinc-900/60 text-xs">
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400 status-dot-live' : 'bg-red-400'}`} />
              <span className="text-zinc-400 font-medium">{connected ? 'Live' : 'Offline'}</span>
            </div>
            <button
              onClick={resetSession}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                         text-zinc-400 hover:text-zinc-200 bg-zinc-900/40 hover:bg-zinc-800/60
                         border border-zinc-800 transition-all"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset
            </button>
          </div>
        </nav>

        {/* ── Hero ───────────────────────────────────────────────────── */}
        <section className="card p-6 md:p-8 flex flex-col md:flex-row items-center gap-8 animate-in animate-delay-1">
          {/* 3D Orb */}
          <div className="orb-container">
            <div className="orb-ring"></div>
            <div className="orb-ring"></div>
            <div className="orb-ring"></div>
            <div className="orb-dot"></div>
            <div className="orb-dot"></div>
            <div className="orb-dot"></div>
            <div className="orb-core"></div>
          </div>

          {/* Text */}
          <div className="flex-1 text-center md:text-left">
            <p className="text-[11px] text-zinc-500 uppercase tracking-[0.2em] font-semibold mb-2">
              Environmental Impact Avoided
            </p>
            <h2 className="text-3xl md:text-5xl font-bold bg-gradient-to-r from-emerald-300 to-teal-400 bg-clip-text text-transparent leading-tight mb-3">
              {s?.co2_equivalent || '—'}
            </h2>
            <p className="text-sm text-zinc-500">
              {s?.co2_saved_g?.toFixed(6) ?? '0'}g CO₂ saved across {s?.requests ?? 0} proxy requests
            </p>
          </div>
        </section>

        {/* ── KPI Strip ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
          <div className="card card-accent p-5 animate-in animate-delay-1" style={{ '--accent-color': '#34d399' } as React.CSSProperties}>
            <div className="flex items-center gap-2 mb-3">
              <TrendingDown className="w-4 h-4 text-emerald-400" />
              <span className="text-[11px] text-zinc-500 font-semibold uppercase tracking-wider">CO₂ Avoided</span>
            </div>
            <div className="counter-value text-2xl md:text-3xl text-white">{co2Val}<span className="text-base text-emerald-400/60 ml-1">g</span></div>
          </div>

          <div className="card card-accent p-5 animate-in animate-delay-2" style={{ '--accent-color': '#60a5fa' } as React.CSSProperties}>
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-blue-400" />
              <span className="text-[11px] text-zinc-500 font-semibold uppercase tracking-wider">Tokens Saved</span>
            </div>
            <div className="counter-value text-2xl md:text-3xl text-white">{tokenVal}</div>
          </div>

          <div className="card card-accent p-5 animate-in animate-delay-3" style={{ '--accent-color': '#a78bfa' } as React.CSSProperties}>
            <div className="flex items-center gap-2 mb-3">
              <Bot className="w-4 h-4 text-purple-400" />
              <span className="text-[11px] text-zinc-500 font-semibold uppercase tracking-wider">Requests</span>
            </div>
            <div className="counter-value text-2xl md:text-3xl text-white">{reqVal}</div>
          </div>

          <div className="card card-accent p-5 animate-in animate-delay-4" style={{ '--accent-color': '#fbbf24' } as React.CSSProperties}>
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-[11px] text-zinc-500 font-semibold uppercase tracking-wider">Cache Hit Rate</span>
            </div>
            <div className="counter-value text-2xl md:text-3xl text-white">{hitVal}<span className="text-base text-zinc-500 ml-1">%</span></div>
          </div>
        </div>

        {/* ── Charts Row ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">

          {/* Area Chart */}
          <div className="card p-5 lg:col-span-2 animate-in animate-delay-2" style={{ minHeight: 340 }}>
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4">Cumulative CO₂ Timeline</h3>
            {timelineData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={timelineData}>
                  <defs>
                    <linearGradient id="co2Grad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#34d399" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="idx"
                    stroke="#333"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `#${v}`}
                  />
                  <YAxis
                    stroke="#333"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `${v}g`}
                    width={45}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#18181b',
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: 12,
                      fontSize: 12,
                    }}
                    formatter={(val: number) => [`${val.toFixed(6)}g`, 'CO₂']}
                    labelFormatter={(v) => `Request #${v}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="co2"
                    stroke="#34d399"
                    strokeWidth={2}
                    fill="url(#co2Grad)"
                    dot={(props: any) => {
                      const { cx, cy, payload } = props;
                      return (
                        <circle
                          cx={cx}
                          cy={cy}
                          r={payload.cached ? 5 : 3}
                          fill={payload.cached ? '#fbbf24' : '#34d399'}
                          stroke="#0a0a0f"
                          strokeWidth={2}
                        />
                      );
                    }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[280px] text-zinc-600 text-sm">No data yet</div>
            )}
          </div>

          {/* Pie Chart */}
          <div className="card p-5 animate-in animate-delay-3" style={{ minHeight: 340 }}>
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4">Model Distribution</h3>
            {pieData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={3}
                      dataKey="value"
                      stroke="none"
                    >
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: '#18181b',
                        border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: 12,
                        fontSize: 12,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-2 mt-2">
                  {pieData.map((d, i) => (
                    <div key={d.name} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                        <span className="text-zinc-400">{d.name}</span>
                      </div>
                      <span className="font-medium text-zinc-300">{d.value}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-zinc-600 text-sm">No data yet</div>
            )}
          </div>
        </div>

        {/* ── Bottom Row ─────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">

          {/* Cost / Energy Panel */}
          <div className="card p-5 animate-in animate-delay-3">
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-5">Cost & Energy</h3>
            <div className="space-y-5">
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-emerald-500/10">
                  <Coins className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <p className="text-[11px] text-zinc-500 uppercase tracking-wider">Est. Cost Processed</p>
                  <p className="counter-value text-xl text-white">${e?.total_cost_usd?.toFixed(6) ?? '0.000000'}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <BatteryCharging className="w-4 h-4 text-blue-400" />
                </div>
                <div>
                  <p className="text-[11px] text-zinc-500 uppercase tracking-wider">Energy Consumed</p>
                  <p className="counter-value text-xl text-white">{e?.total_kwh?.toFixed(8) ?? '0'} <span className="text-sm text-zinc-500">kWh</span></p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-purple-500/10">
                  <Users className="w-4 h-4 text-purple-400" />
                </div>
                <div>
                  <p className="text-[11px] text-zinc-500 uppercase tracking-wider">Team Projection (annual)</p>
                  <p className="counter-value text-xl text-white">{e?.annual_team_co2_g?.toFixed(1) ?? '0'}<span className="text-sm text-zinc-500 ml-1">g CO₂</span></p>
                  <p className="text-[10px] text-zinc-600 mt-0.5">10 devs × 50 queries/day × 250 days</p>
                </div>
              </div>
            </div>
          </div>

          {/* Activity Feed */}
          <div className="card p-5 lg:col-span-2 flex flex-col animate-in animate-delay-4" style={{ maxHeight: 420 }}>
            <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4">Recent Activity</h3>
            <div className="overflow-y-auto custom-scroll flex-1 space-y-2 pr-1">
              {(data?.recent_activity ?? []).map((a, i) => (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-zinc-900/40 border border-zinc-800/50 hover:bg-zinc-800/40 transition-colors">
                  <div className={`p-2 rounded-lg shrink-0 ${a.cached ? 'bg-amber-500/10 text-amber-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                    {a.cached ? <Zap className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-zinc-300 truncate">{a.prompt_preview || '—'}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="pill" style={{ color: MODEL_COLORS[a.model] || '#71717a' }}>
                        {a.model}
                      </span>
                      <span className="text-[10px] text-zinc-600">{timeAgo(a.timestamp)}</span>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <div className="text-xs font-mono font-semibold text-zinc-300">{a.co2_g.toFixed(4)}g</div>
                    <div className="text-[10px] text-zinc-600">{a.tokens_in + a.tokens_out} tok</div>
                  </div>
                </div>
              ))}
              {(!data?.recent_activity || data.recent_activity.length === 0) && (
                <div className="flex flex-col items-center justify-center py-16 text-zinc-600">
                  <Activity className="w-6 h-6 mb-2 opacity-20" />
                  <p className="text-xs">No requests yet</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Footer ─────────────────────────────────────────────────── */}
        <footer className="text-center py-4 text-[11px] text-zinc-700">
          CarbonProxy — Making AI sustainable, one prompt at a time.
        </footer>
      </div>
    </div>
  );
}
