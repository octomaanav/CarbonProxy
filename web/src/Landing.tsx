import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Leaf, Cpu, ArrowRight, Zap, Shield, BarChart3,
  TreePine, Globe, Server, ChevronDown,
} from 'lucide-react';

/* ── Scroll-reveal hook ─────────────────────────────────────────────── */

function useReveal() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.15 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, className: visible ? 'reveal reveal-visible' : 'reveal' };
}

/* ── Animated counter (standalone for landing) ──────────────────────── */

function AnimatedStat({ value, suffix = '' }: { value: string; suffix?: string }) {
  return (
    <span className="counter-value text-4xl md:text-5xl text-white">
      {value}<span className="text-emerald-400/70 text-2xl ml-1">{suffix}</span>
    </span>
  );
}

/* ── Component ──────────────────────────────────────────────────────── */

export default function Landing() {
  const problem = useReveal();
  const howStep1 = useReveal();
  const howStep2 = useReveal();
  const howStep3 = useReveal();
  const impact = useReveal();
  const cta = useReveal();

  return (
    <div className="min-h-screen">

      {/* ── Navbar ───────────────────────────────────────────────────── */}
      <nav className="fixed top-0 inset-x-0 z-50 backdrop-blur-md bg-[#0a0a0f]/80 border-b border-zinc-800/50">
        <div className="max-w-[1200px] mx-auto flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="relative w-9 h-9 flex items-center justify-center">
              <Leaf className="w-5 h-5 text-emerald-400 absolute" />
              <Cpu className="w-4 h-4 text-emerald-600 absolute translate-x-1.5 translate-y-1.5" />
            </div>
            <span className="text-lg font-semibold tracking-tight">CarbonProxy</span>
          </div>
          <Link
            to="/dashboard"
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                       bg-emerald-500/10 text-emerald-400 border border-emerald-500/20
                       hover:bg-emerald-500/20 transition-all"
          >
            Open Dashboard
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="min-h-screen flex items-center justify-center relative overflow-hidden pt-20 px-6">
        {/* Background glow */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-emerald-500/5 blur-[120px]" />
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full bg-teal-500/3 blur-[100px]" />
        </div>

        <div className="relative z-10 max-w-[800px] text-center space-y-8 animate-in">
          {/* Orb */}
          <div className="orb-container mx-auto mb-4">
            <div className="orb-ring"></div>
            <div className="orb-ring"></div>
            <div className="orb-ring"></div>
            <div className="orb-dot"></div>
            <div className="orb-dot"></div>
            <div className="orb-dot"></div>
            <div className="orb-core"></div>
          </div>

          <p className="text-[11px] text-emerald-400/70 uppercase tracking-[0.25em] font-semibold">
            AI Sustainability Middleware
          </p>

          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold leading-[1.1] tracking-tight">
            Every AI Prompt Has a{' '}
            <span className="bg-gradient-to-r from-emerald-300 to-teal-400 bg-clip-text text-transparent">
              Carbon Cost
            </span>
          </h1>

          <p className="text-lg md:text-xl text-zinc-400 max-w-[600px] mx-auto leading-relaxed">
            CarbonProxy intercepts your LLM calls, compresses prompts, routes to efficient models,
            and caches responses — so you use less energy without changing your workflow.
          </p>

          <div className="flex items-center justify-center gap-4 pt-4">
            <Link
              to="/dashboard"
              className="flex items-center gap-2 px-6 py-3 rounded-xl text-base font-semibold
                         bg-emerald-500 text-black hover:bg-emerald-400 transition-all
                         shadow-lg shadow-emerald-500/20"
            >
              See Your Impact
              <ArrowRight className="w-5 h-5" />
            </Link>
            <a
              href="#the-problem"
              className="flex items-center gap-2 px-6 py-3 rounded-xl text-base font-medium
                         text-zinc-400 border border-zinc-700 hover:border-zinc-500 hover:text-zinc-200
                         transition-all"
            >
              Learn More
              <ChevronDown className="w-4 h-4" />
            </a>
          </div>
        </div>
      </section>

      {/* ── The Problem ──────────────────────────────────────────────── */}
      <section id="the-problem" className="py-28 px-6">
        <div className="max-w-[1100px] mx-auto">
          <div {...problem} >
            <p className="text-[11px] text-red-400/70 uppercase tracking-[0.2em] font-semibold mb-3 text-center">
              The Problem
            </p>
            <h2 className="text-3xl md:text-5xl font-bold text-center mb-6 leading-tight">
              AI Is{' '}
              <span className="text-red-400">Hungry</span>{' '}
              for Energy
            </h2>
            <p className="text-zinc-500 text-center max-w-[650px] mx-auto mb-16 text-lg">
              The explosive growth of large language models has created an invisible
              environmental cost that most developers never see.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="card p-6 text-center group">
                <div className="p-3 rounded-xl bg-red-500/10 w-fit mx-auto mb-4 group-hover:scale-110 transition-transform">
                  <Zap className="w-6 h-6 text-red-400" />
                </div>
                <div className="counter-value text-3xl text-white mb-2">10×</div>
                <p className="text-sm text-zinc-500 leading-relaxed">
                  A single ChatGPT query uses <strong className="text-zinc-300">10× more energy</strong> than
                  a Google search
                </p>
              </div>

              <div className="card p-6 text-center group">
                <div className="p-3 rounded-xl bg-amber-500/10 w-fit mx-auto mb-4 group-hover:scale-110 transition-transform">
                  <Globe className="w-6 h-6 text-amber-400" />
                </div>
                <div className="counter-value text-3xl text-white mb-2">552t</div>
                <p className="text-sm text-zinc-500 leading-relaxed">
                  Training GPT-4 emitted an estimated <strong className="text-zinc-300">552 tonnes of CO₂</strong> —
                  equivalent to 123 cars driving for a year
                </p>
              </div>

              <div className="card p-6 text-center group">
                <div className="p-3 rounded-xl bg-orange-500/10 w-fit mx-auto mb-4 group-hover:scale-110 transition-transform">
                  <Server className="w-6 h-6 text-orange-400" />
                </div>
                <div className="counter-value text-3xl text-white mb-2">2027</div>
                <p className="text-sm text-zinc-500 leading-relaxed">
                  By 2027, AI data centers could consume as much electricity as a{' '}
                  <strong className="text-zinc-300">small country</strong>
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How It Works ─────────────────────────────────────────────── */}
      <section className="py-28 px-6 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-emerald-500/[0.02] to-transparent" />
        <div className="max-w-[1100px] mx-auto relative z-10">
          <p className="text-[11px] text-emerald-400/70 uppercase tracking-[0.2em] font-semibold mb-3 text-center">
            How It Works
          </p>
          <h2 className="text-3xl md:text-5xl font-bold text-center mb-20 leading-tight">
            Three Steps to{' '}
            <span className="bg-gradient-to-r from-emerald-300 to-teal-400 bg-clip-text text-transparent">
              Greener AI
            </span>
          </h2>

          <div className="space-y-20 md:space-y-28">
            {/* Step 1 */}
            <div {...howStep1} className={`${howStep1.className} flex flex-col md:flex-row items-center gap-10 md:gap-16`}>
              <div className="flex-1 order-2 md:order-1">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full border-2 border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm">
                    1
                  </div>
                  <h3 className="text-xl font-semibold">Intercept</h3>
                </div>
                <p className="text-zinc-400 leading-relaxed">
                  CarbonProxy sits transparently between your code and the LLM API. Every prompt
                  passes through it — no code changes needed. Just point your API calls to the proxy.
                </p>
              </div>
              <div className="flex-shrink-0 order-1 md:order-2">
                <div className="w-32 h-32 rounded-2xl bg-emerald-500/5 border border-emerald-500/10 flex items-center justify-center step-icon">
                  <Shield className="w-14 h-14 text-emerald-400/60" />
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div {...howStep2} className={`${howStep2.className} flex flex-col md:flex-row items-center gap-10 md:gap-16`}>
              <div className="flex-shrink-0">
                <div className="w-32 h-32 rounded-2xl bg-blue-500/5 border border-blue-500/10 flex items-center justify-center step-icon">
                  <Zap className="w-14 h-14 text-blue-400/60" />
                </div>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full border-2 border-blue-500/30 flex items-center justify-center text-blue-400 font-bold text-sm">
                    2
                  </div>
                  <h3 className="text-xl font-semibold">Optimize</h3>
                </div>
                <p className="text-zinc-400 leading-relaxed">
                  Prompts are compressed to remove redundancy. Requests are routed to the cheapest model
                  that can handle them. Repeated queries are served from a semantic cache instantly — zero tokens, zero CO₂.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div {...howStep3} className={`${howStep3.className} flex flex-col md:flex-row items-center gap-10 md:gap-16`}>
              <div className="flex-1 order-2 md:order-1">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-full border-2 border-purple-500/30 flex items-center justify-center text-purple-400 font-bold text-sm">
                    3
                  </div>
                  <h3 className="text-xl font-semibold">Track</h3>
                </div>
                <p className="text-zinc-400 leading-relaxed">
                  Every request is measured: tokens saved, CO₂ avoided, energy consumed, and cost reduction.
                  The dashboard gives you a live view of your environmental impact — broken down per model, per request.
                </p>
              </div>
              <div className="flex-shrink-0 order-1 md:order-2">
                <div className="w-32 h-32 rounded-2xl bg-purple-500/5 border border-purple-500/10 flex items-center justify-center step-icon">
                  <BarChart3 className="w-14 h-14 text-purple-400/60" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Impact ───────────────────────────────────────────────────── */}
      <section className="py-28 px-6">
        <div className="max-w-[900px] mx-auto" {...impact}>
          <p className="text-[11px] text-emerald-400/70 uppercase tracking-[0.2em] font-semibold mb-3 text-center">
            The Impact
          </p>
          <h2 className="text-3xl md:text-5xl font-bold text-center mb-6 leading-tight">
            Small Changes,{' '}
            <span className="bg-gradient-to-r from-emerald-300 to-teal-400 bg-clip-text text-transparent">
              Big Impact
            </span>
          </h2>
          <p className="text-zinc-500 text-center max-w-[550px] mx-auto mb-16 text-lg">
            When every developer measures their AI footprint, the savings compound.
          </p>

          <div className="card p-8 md:p-12 text-center">
            <TreePine className="w-16 h-16 text-emerald-400/40 mx-auto mb-6 tree-sway" />
            <AnimatedStat value="1" suffix="tree" />
            <p className="text-zinc-500 text-sm mt-3 max-w-[400px] mx-auto">
              A single mature tree absorbs ~22kg of CO₂ per year.
              With a team of 10 developers, CarbonProxy can offset
              the equivalent of planting trees every year.
            </p>

            <div className="grid grid-cols-3 gap-6 mt-10 pt-8 border-t border-zinc-800">
              <div>
                <div className="counter-value text-xl md:text-2xl text-white">0.004g</div>
                <p className="text-[11px] text-zinc-600 uppercase tracking-wider mt-1">CO₂ per session</p>
              </div>
              <div>
                <div className="counter-value text-xl md:text-2xl text-white">20%</div>
                <p className="text-[11px] text-zinc-600 uppercase tracking-wider mt-1">Cache hit rate</p>
              </div>
              <div>
                <div className="counter-value text-xl md:text-2xl text-white">~50%</div>
                <p className="text-[11px] text-zinc-600 uppercase tracking-wider mt-1">Token reduction</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────── */}
      <section className="py-28 px-6">
        <div className="max-w-[700px] mx-auto text-center" {...cta}>
          <h2 className="text-3xl md:text-5xl font-bold mb-6 leading-tight">
            See Your Impact{' '}
            <span className="bg-gradient-to-r from-emerald-300 to-teal-400 bg-clip-text text-transparent">
              Right Now
            </span>
          </h2>
          <p className="text-zinc-500 text-lg mb-10">
            Open the dashboard to see how much carbon you've saved.<br />
            Every prompt counts.
          </p>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-3 px-8 py-4 rounded-xl text-lg font-semibold
                       bg-emerald-500 text-black hover:bg-emerald-400 transition-all
                       shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40"
          >
            Open Dashboard
            <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="border-t border-zinc-800/50 py-8 px-6 text-center text-[12px] text-zinc-600">
        CarbonProxy — Making AI sustainable, one prompt at a time.
      </footer>
    </div>
  );
}
