import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { useQuery } from "../../hooks/useQuery";
import { useMutation } from "../../hooks/useMutation";
import { toast } from "sonner";

interface Candle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface WatchlistTicker {
  symbol: string;
  notes?: string | null;
}

interface Watchlist {
  id: string;
  name: string;
  tickers: WatchlistTicker[];
}

export default function EmaCrossover({ symbol, onSymbolSelect }: { symbol: string; onSymbolSelect: (s: string) => void }) {
  const [chartData, setChartData] = useState<Record<string, Candle[]>>({});
  const [crosshair, setCrosshair] = useState<{ tf: string | null; x: number; y: number }>({
    tf: null,
    x: 0,
    y: 0,
  });

  // === Fetch EmaCrossover watchlist ===
  const { data: watchlists, refetch } = useQuery<Watchlist[]>(api.watchlists.getScannerWatchlists);
  const removeTicker = useMutation<unknown>("DELETE", { onSuccess: () => refetch() });

  const emaWatchlist = watchlists?.find((wl) => wl.name === "EMA Crossover") || null;

  const handleRemoveTicker = async (wlId: string, tickerSymbol: string) => {
    if (!confirm(`Remove ${tickerSymbol}?`)) return;
    try {
      await removeTicker(undefined, {
        endpoint: api.watchlists.removeTickerFromWatchlist(wlId, tickerSymbol),
      });
      toast.success("Ticker removed");
    } catch (err) {
      console.error(err);
      toast.error("Failed to remove ticker");
    }
  };

  // === Fetch candle data ===
  useEffect(() => {
    const fetchData = async () => {
      const intervals = ["1h", "1d"];
      const results: Record<string, Candle[]> = {};
      const token = localStorage.getItem("access_token");
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      for (const tf of intervals) {
        try {
          const res = await fetch(api.marketData.fetch(symbol, tf, 100), { headers });
          if (res.ok) {
            const data = await res.json();
            results[tf] = data; // Backend now returns data in chronological order
          }
        } catch (e) {
          console.error(`Error fetching ${tf}`, e);
        }
      }
      setChartData(results);
    };
    fetchData();
  }, [symbol]);

  // === Compute EMA ===
  const calcEMA = (data: Candle[], period: number): number[] => {
    if (!data.length) return [];
    const k = 2 / (period + 1);
    let ema = data[0].close;
    const result: number[] = [ema];
    for (let i = 1; i < data.length; i++) {
      ema = data[i].close * k + ema * (1 - k);
      result.push(ema);
    }
    return result;
  };

  const renderChart = (tf: string, candles: Candle[]) => {
    if (!candles.length) return <div className="h-64 flex items-center justify-center text-gray-500 italic">Loading {tf}...</div>;

    const ema20 = calcEMA(candles, 20);
    const ema50 = calcEMA(candles, 50);
    const slice = candles.slice(-50);
    const e20 = ema20.slice(-50);
    const e50 = ema50.slice(-50);

    const max = Math.max(...slice.map(c => c.high));
    const min = Math.min(...slice.map(c => c.low));
    const range = max - min || 1;

    const chartW = 600;
    const chartH = 250;
    const padX = 20;
    const padY = 20;

    const getX = (i: number) => (i / (slice.length - 1)) * (chartW - 2 * padX) + padX;
    const getY = (val: number) => chartH - padY - ((val - min) / range) * (chartH - 2 * padY);

    return (
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 shadow-2xl relative group">
        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          {tf} Chart
          <span className="text-[10px] text-gray-500 font-mono uppercase tracking-widest">{symbol}</span>
        </h3>

        <svg viewBox={`0 0 ${chartW} ${chartH}`} width="100%" height={chartH} className="cursor-crosshair overflow-visible">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map(p => {
            const y = getY(min + p * range);
            return (
              <line key={p} x1={padX} x2={chartW - padX} y1={y} y2={y} stroke="rgba(255,255,255,0.03)" strokeWidth="1" />
            );
          })}

          {/* EMA 50 (Atmosphere/Cloud) */}
          <polyline
            fill="none"
            stroke="rgba(146, 64, 14, 0.3)"
            strokeWidth="3"
            strokeLinecap="round"
            points={e50.map((v, i) => `${getX(i)},${getY(v)}`).join(" ")}
          />

          {/* EMA 20 (Leading) */}
          <polyline
            fill="none"
            stroke="#facc15"
            strokeWidth="2"
            strokeLinecap="round"
            strokeDasharray="4 2"
            points={e20.map((v, i) => `${getX(i)},${getY(v)}`).join(" ")}
          />

          {/* EMA 50 (Solid) */}
          <polyline
            fill="none"
            stroke="#92400e"
            strokeWidth="1.5"
            strokeLinecap="round"
            points={e50.map((v, i) => `${getX(i)},${getY(v)}`).join(" ")}
          />

          {/* Candles */}
          {slice.map((c, i) => {
            const x = getX(i);
            const color = c.close >= c.open ? "#10b981" : "#ef4444";
            const w = (chartW - 2 * padX) / slice.length * 0.75;

            return (
              <g key={i}>
                <line x1={x} y1={getY(c.high)} x2={x} y2={getY(c.low)} stroke={color} strokeWidth="1.2" />
                <rect
                  x={x - w / 2}
                  y={Math.min(getY(c.open), getY(c.close))}
                  width={w}
                  height={Math.max(1, Math.abs(getY(c.close) - getY(c.open)))}
                  fill={color}
                  rx="1"
                />
              </g>
            );
          })}
        </svg>

        <div className="mt-4 flex gap-4 text-[10px] text-gray-500 font-mono">
          <div className="flex items-center gap-1"><div className="w-2 h-0.5 bg-yellow-400"></div> EMA 20</div>
          <div className="flex items-center gap-1"><div className="w-2 h-0.5 bg-amber-800"></div> EMA 50</div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <header className="space-y-2">
        <h1 className="text-4xl font-extrabold bg-gradient-to-r from-yellow-400 to-amber-600 bg-clip-text text-transparent">
          EMA Crossover
        </h1>
        <p className="text-gray-400 max-w-3xl text-lg">
          Classic trend-following strategy using dual Exponential Moving Averages to capture momentum shifts and pullback entries.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <section className="lg:col-span-2 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {renderChart("1h", chartData["1h"] || [])}
            {renderChart("1d", chartData["1d"] || [])}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gradient-to-br from-gray-800 to-gray-900 p-6 rounded-xl border border-gray-700 shadow-xl">
              <h3 className="text-xl font-bold text-white mb-4 border-l-4 border-yellow-400 pl-4 uppercase tracking-wider text-sm">Entry Logic</h3>
              <p className="text-gray-300 text-sm leading-relaxed mb-4">
                The primary trigger occurs when price closes back above the <span className="text-yellow-400 font-bold">20 EMA</span> following a shallow pullback, provided the trend is established.
              </p>
              <div className="flex items-center gap-3 bg-yellow-400/5 p-3 rounded-lg border border-yellow-400/20">
                <div className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></div>
                <span className="text-xs text-yellow-200/80 font-mono font-bold">CROSSOVER CONFIRMATION REQUIRED</span>
              </div>
            </div>

            <div className="bg-gradient-to-br from-gray-800 to-gray-900 p-6 rounded-xl border border-gray-700 shadow-xl">
              <h3 className="text-xl font-bold text-white mb-4 border-l-4 border-amber-800 pl-4 uppercase tracking-wider text-sm">Trend Filters</h3>
              <ul className="space-y-3 text-sm text-gray-400">
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500 mt-1">✓</span>
                  <span>Daily EMAs must be in correct order (20 {'>'} 50)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500 mt-1">✓</span>
                  <span>Hourly EMAs must have crossed recently</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500 mt-1">✓</span>
                  <span>Price action making new daily highs (for longs)</span>
                </li>
              </ul>
            </div>
          </div>
        </section>

        <aside className="space-y-6">
          <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden shadow-2xl">
            <div className="bg-gradient-to-r from-yellow-500/10 to-amber-500/10 p-5 border-b border-gray-700">
              <h3 className="font-bold text-yellow-400 flex justify-between items-center">
                EMA Watchlist
                <span className="text-[10px] bg-yellow-500/20 px-2 py-0.5 rounded uppercase tracking-tighter">Scanner Results</span>
              </h3>
            </div>
            <div className="p-3 max-h-[500px] overflow-y-auto custom-scrollbar">
              {!emaWatchlist?.tickers.length && (
                <div className="p-8 text-center text-gray-500 text-sm italic py-20">
                  <div className="mb-2">⌛</div>
                  No active setups found.<br />Wait for next crossover.
                </div>
              )}
              {emaWatchlist?.tickers.map(t => {
                const isRecent = t.notes?.includes("Just now");
                return (
                  <div key={t.symbol} className="flex justify-between items-center p-3 hover:bg-white/5 rounded-xl group transition-all mb-1 active:scale-95 cursor-pointer" onClick={() => onSymbolSelect(t.symbol)}>
                    <div className="flex flex-col">
                      <span className="font-bold text-gray-200">{t.symbol}</span>
                      <span className={`text-[10px] font-mono uppercase ${isRecent ? "text-green-400 font-bold animate-pulse" : "text-gray-500"}`}>
                        {t.notes || "Setup Detected"}
                      </span>
                    </div>
                    <button onClick={(e) => { e.stopPropagation(); handleRemoveTicker(emaWatchlist.id, t.symbol); }} className="p-2 text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">×</button>
                  </div>
                );
              })}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
