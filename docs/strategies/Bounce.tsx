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

export default function Bounce({ symbol, onSymbolSelect }: { symbol: string; onSymbolSelect: (s: string) => void }) {
    const [chartData, setChartData] = useState<Record<string, Candle[]>>({});

    // === Watchlist logic ===
    const { data: watchlists, refetch } = useQuery<Watchlist[]>(api.watchlists.getScannerWatchlists);
    const removeTicker = useMutation<unknown>("DELETE", { onSuccess: () => refetch() });

    const bounceWatchlist = watchlists?.find((wl) => wl.name.toLowerCase().includes("bounce")) || null;

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

    // === Indicators ===
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

    const calcRSI = (data: Candle[], period = 14): number[] => {
        if (data.length < period) return [];
        const deltas: number[] = [];
        for (let i = 1; i < data.length; i++) deltas.push(data[i].close - data[i - 1].close);
        let gains = deltas.slice(0, period).filter((d) => d > 0).reduce((a, b) => a + b, 0) / period;
        let losses = deltas.slice(0, period).filter((d) => d < 0).reduce((a, b) => a - b, 0) / period;
        const rsi: number[] = [];
        for (let i = period; i < deltas.length; i++) {
            const delta = deltas[i];
            gains = (gains * (period - 1) + (delta > 0 ? delta : 0)) / period;
            losses = (losses * (period - 1) + (delta < 0 ? -delta : 0)) / period;
            const rs = losses === 0 ? 100 : gains / losses;
            rsi.push(100 - 100 / (1 + rs));
        }
        return rsi;
    };

    const linearRegressionLine = (values: number[]): number[] => {
        const n = values.length;
        if (n === 0) return [];
        const xSum = values.reduce((sum, _, i) => sum + i, 0);
        const ySum = values.reduce((sum, y) => sum + y, 0);
        const xySum = values.reduce((sum, y, i) => sum + i * y, 0);
        const x2Sum = values.reduce((sum, _, i) => sum + i * i, 0);
        const denom = n * x2Sum - xSum * xSum;
        const slope = denom === 0 ? 0 : (n * xySum - xSum * ySum) / denom;
        const intercept = (ySum - slope * xSum) / n;
        return values.map((_, i) => slope * i + intercept);
    };

    const renderStrategyCharts = (tf: string, candles: Candle[]) => {
        if (!candles.length) return <div className="h-64 flex items-center justify-center text-gray-500 italic">Gathering {tf} data...</div>;

        const ema20 = calcEMA(candles, 20);
        const rsiValues = calcRSI(candles);

        const slice = candles.slice(-50);
        const e20 = ema20.slice(-50);
        const rsi = rsiValues.slice(-50);

        const max = Math.max(...slice.map(c => c.high));
        const min = Math.min(...slice.map(c => c.low));
        const range = max - min || 1;

        // LR on price
        const half = Math.floor(slice.length / 2);
        const lrLine = linearRegressionLine(slice.slice(half).map(c => c.close));

        const chartW = 600;
        const padX = 20;

        return (
            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700 shadow-2xl space-y-4">
                <h3 className="text-xl font-bold text-white mb-2 flex items-center justify-between">
                    {tf} Pulse
                    <span className="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20 font-mono tracking-widest">{symbol}</span>
                </h3>

                {/* Price Chart */}
                <div className="relative group">
                    <svg viewBox={`0 0 ${chartW} 180`} width="100%" height="180" className="overflow-visible">
                        {[0, 0.5, 1].map(p => {
                            const y = 160 - p * 140;
                            return <line key={p} x1={padX} x2={chartW - padX} y1={y} y2={y} stroke="rgba(255,255,255,0.02)" strokeWidth="1" />;
                        })}

                        {/* EMA 20 */}
                        <polyline
                            fill="none"
                            stroke="#3b82f6"
                            strokeWidth="2"
                            points={e20.map((v, i) => `${(i / (slice.length - 1)) * (chartW - 2 * padX) + padX},${160 - ((v - min) / range) * 140}`).join(" ")}
                        />

                        {/* LR Line */}
                        <polyline
                            fill="none"
                            stroke="white"
                            strokeWidth="1.5"
                            opacity="0.5"
                            strokeDasharray="4 4"
                            points={lrLine.map((v, i) => `${((i + half) / (slice.length - 1)) * (chartW - 2 * padX) + padX},${160 - ((v - min) / range) * 140}`).join(" ")}
                        />

                        {/* Candles */}
                        {slice.map((c, i) => {
                            const x = (i / (slice.length - 1)) * (chartW - 2 * padX) + padX;
                            const color = c.close >= c.open ? "#10b981" : "#ef4444";
                            const w = (chartW - 2 * padX) / slice.length * 0.7;
                            return (
                                <g key={i}>
                                    <line x1={x} y1={160 - ((c.high - min) / range) * 140} x2={x} y2={160 - ((c.low - min) / range) * 140} stroke={color} strokeWidth="1" />
                                    <rect x={x - w / 2} y={160 - ((Math.max(c.open, c.close) - min) / range) * 140} width={w} height={Math.max(1, (Math.abs(c.open - c.close) / range) * 140)} fill={color} rx="0.5" />
                                </g>
                            );
                        })}
                    </svg>
                    <div className="absolute top-0 right-0 text-[10px] text-blue-400 font-mono font-bold uppercase tracking-widest">Momentum Entry</div>
                </div>

                {/* RSI Chart */}
                <div className="relative pt-4 border-t border-gray-700/50">
                    <svg viewBox={`0 0 ${chartW} 80`} width="100%" height="80" className="overflow-visible">
                        {/* Overbought/Oversold levels */}
                        <line x1={padX} x2={chartW - padX} y1={15} y2={15} stroke="#ef4444" strokeWidth="1" strokeDasharray="2 2" opacity="0.3" />
                        <line x1={padX} x2={chartW - padX} y1={65} y2={65} stroke="#10b981" strokeWidth="1" strokeDasharray="2 2" opacity="0.3" />
                        <polyline
                            fill="none"
                            stroke="#f59e0b"
                            strokeWidth="2"
                            points={rsi.map((v, i) => `${(i / (rsi.length - 1)) * (chartW - 2 * padX) + padX},${80 - (v / 100) * 80}`).join(" ")}
                        />
                    </svg>
                    <div className="absolute top-4 right-0 text-[10px] text-amber-500 font-mono font-bold uppercase tracking-widest">RSI (14)</div>
                </div>
            </div>
        );
    };

    return (
        <div className="space-y-10 max-w-7xl mx-auto">
            <header className="space-y-3">
                <h1 className="text-4xl font-black bg-gradient-to-r from-emerald-400 to-blue-500 bg-clip-text text-transparent uppercase tracking-tighter">
                    20 Bounce Strategy
                </h1>
                <p className="text-gray-400 max-w-2xl text-lg leading-relaxed">
                    Aggressive trend continuation system identifying entries near the dynamic 20-period moving average with regression confirmation.
                </p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
                <section className="lg:col-span-2 space-y-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        {renderStrategyCharts("1h", chartData["1h"] || [])}
                        {renderStrategyCharts("1d", chartData["1d"] || [])}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div className="bg-gray-800/50 rounded-3xl p-8 border border-gray-700 shadow-2xl backdrop-blur-sm relative group">
                            <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none transition-opacity group-hover:opacity-20 text-blue-400 font-black text-7xl">01</div>
                            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-3">
                                <span className="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs">🚀</span>
                                ENTRY MODEL
                            </h3>
                            <ul className="space-y-4 text-sm text-gray-300">
                                <li className="flex gap-3">
                                    <span className="text-blue-500 font-bold">1.</span>
                                    <span>D1 Trend established with EMA 8-20 alignment.</span>
                                </li>
                                <li className="flex gap-3">
                                    <span className="text-blue-500 font-bold">2.</span>
                                    <span>H4 Pullback below 20 EMA followed by immediate recovery.</span>
                                </li>
                                <li className="flex gap-3">
                                    <span className="text-blue-500 font-bold">3.</span>
                                    <span>M30 EMA 20/50 cross confirms final execution.</span>
                                </li>
                            </ul>
                        </div>

                        <div className="bg-gray-800/50 rounded-3xl p-8 border border-gray-700 shadow-2xl backdrop-blur-sm relative group">
                            <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none transition-opacity group-hover:opacity-20 text-amber-400 font-black text-7xl">02</div>
                            <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-3">
                                <span className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center text-xs">🛡️</span>
                                RISK FILTERS
                            </h3>
                            <ul className="space-y-4 text-sm text-gray-300">
                                <li className="flex gap-3">
                                    <span className="text-amber-500 font-bold">●</span>
                                    <span>MACD must align with the primary D1 trend direction.</span>
                                </li>
                                <li className="flex gap-3">
                                    <span className="text-amber-500 font-bold">●</span>
                                    <span>Linear regression slope must be positive for longs.</span>
                                </li>
                                <li className="flex gap-3">
                                    <span className="text-amber-500 font-bold">●</span>
                                    <span>Avoid trading during high-impact news or D1 exhaustion.</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </section>

                <aside className="space-y-8">
                    <div className="bg-gray-800 rounded-3xl border border-gray-700 overflow-hidden shadow-2xl">
                        <div className="bg-gradient-to-br from-gray-700 to-gray-800 p-6 border-b border-gray-700">
                            <h3 className="font-bold text-white flex justify-between items-center text-lg">
                                Setup Watchlist
                                <span className="text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-3 py-1 rounded-full font-black uppercase tracking-widest">Live</span>
                            </h3>
                        </div>
                        <div className="p-4 max-h-[600px] overflow-y-auto">
                            {!bounceWatchlist?.tickers.length && <div className="p-20 text-center text-gray-500 text-sm italic py-32 opacity-50">Monitoring for high-probability bounces...</div>}
                            {bounceWatchlist?.tickers.map(t => (
                                <div key={t.symbol} className="flex justify-between items-center p-4 hover:bg-white/5 rounded-2xl group transition-all mb-2 cursor-pointer border border-transparent hover:border-gray-700" onClick={() => onSymbolSelect(t.symbol)}>
                                    <div className="flex flex-col">
                                        <span className="font-black text-gray-200 tracking-tight">{t.symbol}</span>
                                        <span className="text-[10px] text-gray-500 font-medium uppercase mt-0.5">{t.notes || "Aggressive Setup"}</span>
                                    </div>
                                    <button onClick={(e) => { e.stopPropagation(); handleRemoveTicker(bounceWatchlist.id, t.symbol); }} className="w-8 h-8 flex items-center justify-center rounded-xl text-gray-600 hover:text-red-400 hover:bg-red-400/10 opacity-0 group-hover:opacity-100 transition-all font-bold">×</button>
                                </div>
                            ))}
                        </div>
                    </div>
                </aside>
            </div>
        </div>
    );
}
