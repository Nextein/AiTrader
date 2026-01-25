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
    volume: number;
}

interface RelativeCandle extends Candle {
    state: string; // U, D, RU, RD, I, X, etc.
    phase: number; // 1 (UP) or -1 (DOWN)
    displayOpen: number;
    displayClose: number;
    displayColor: string;
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

export default function Eternal({ symbol, onSymbolSelect }: { symbol: string; onSymbolSelect: (s: string) => void }) {
    const [timeframes, setTimeframes] = useState<string[]>(() => {
        const saved = localStorage.getItem("eternal_timeframes");
        return saved ? JSON.parse(saved) : ["15m", "1h", "4h", "1d"];
    });
    const [chartData, setChartData] = useState<Record<string, Candle[]>>({});

    // === Watchlist logic ===
    const { data: watchlists, refetch } = useQuery<Watchlist[]>(api.watchlists.getScannerWatchlists);
    const removeTicker = useMutation<unknown>("DELETE", { onSuccess: () => refetch() });

    const eternalBuyWl = watchlists?.find((wl) => wl.name === "Eternal Buy") || null;
    const eternalSellWl = watchlists?.find((wl) => wl.name === "Eternal Sell") || null;

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

    const handleTimeframeChange = (index: number, newTf: string) => {
        const newTfs = [...timeframes];
        newTfs[index] = newTf;
        setTimeframes(newTfs);
        localStorage.setItem("eternal_timeframes", JSON.stringify(newTfs));
    };

    // === Fetch data ===
    useEffect(() => {
        const fetchData = async () => {
            const results: Record<string, Candle[]> = { ...chartData };
            const token = localStorage.getItem("access_token");
            const headers: Record<string, string> = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = `Bearer ${token}`;

            for (const tf of timeframes) {
                try {
                    const res = await fetch(api.marketData.fetch(symbol, tf, 150), { headers });
                    if (res.ok) {
                        const data = await res.json();
                        results[tf] = data;
                    }
                } catch (e) {
                    console.error(`Error fetching ${tf}`, e);
                }
            }
            setChartData(results);
        };
        fetchData();
    }, [symbol, timeframes]);

    // === Relative Candle Logic ===
    const processRelativeCandles = (candles: Candle[]) => {
        if (candles.length < 2) return { processed: [], phases: [], cycles: [], trend: "NEUTRAL" };

        const processed: RelativeCandle[] = [];
        const states: string[] = new Array(candles.length).fill('X');
        const phases: number[] = new Array(candles.length).fill(0);

        // Helper for basic candle color
        const isGreen = (c: Candle) => c.close > c.open;

        // 1. Determine Relative States (U, D, RU, RD, RU2, RD2, I, I2)
        // We start from index 1 (needs prev candle)
        for (let i = 0; i < candles.length; i++) {
            const curr = candles[i];

            // Default display values (standard)
            let dOpen = curr.open;
            let dClose = curr.close;
            let dColor = isGreen(curr) ? "#10b981" : "#ef4444";

            if (i === 0) {
                processed.push({ ...curr, state: 'X', phase: 0, displayOpen: dOpen, displayClose: dClose, displayColor: dColor });
                phases[0] = isGreen(curr) ? 1 : -1; // Initial phase guess
                continue;
            }

            const prev = candles[i - 1];
            const hh = curr.high > prev.high;
            const hl = curr.low > prev.low;
            const ll = curr.low < prev.low;

            let state = 'X';

            // Refined Relative Candle Logic (consistent with EnhancedCharts.tsx)
            if (hh && !ll) {
                // Bullish
                state = 'U';
                dOpen = curr.low;
                dClose = curr.high;
                dColor = "#10b981";
            } else if (ll && !hh) {
                // Bearish
                state = 'D';
                dOpen = curr.high;
                dClose = curr.low;
                dColor = "#ef4444";
            } else if (hh && ll) {
                // Outside
                state = isGreen(curr) ? 'RU' : 'RD';
                dOpen = isGreen(curr) ? curr.low : curr.high;
                dClose = isGreen(curr) ? curr.high : curr.low;
                dColor = isGreen(curr) ? "#10b981" : "#ef4444";
            } else {
                // Inside or match
                state = 'I';
                dOpen = curr.high;
                dClose = curr.low;
                dColor = "#9ca3af";
            }

            states[i] = state;
            processed.push({ ...curr, state, phase: 0, displayOpen: dOpen, displayClose: dClose, displayColor: dColor });
        }

        // 2. Determine Phases
        phases[0] = processed[0].displayColor === "#10b981" ? 1 : -1;

        for (let i = 1; i < processed.length; i++) {
            const currColor = processed[i].displayColor;
            const prevColor = processed[i - 1].displayColor;

            const getDir = (color: string) => color === "#10b981" ? 1 : (color === "#ef4444" ? -1 : 0);
            const currDir = getDir(currColor);

            let lastNonGreyDir = 0;
            for (let k = i - 1; k >= 0; k--) {
                const d = getDir(processed[k].displayColor);
                if (d !== 0) {
                    lastNonGreyDir = d;
                    break;
                }
            }

            if (currDir !== 0 && (currDir as any) === lastNonGreyDir) {
                phases[i] = currDir;
            } else if (currDir !== 0 && lastNonGreyDir !== 0 && currDir !== lastNonGreyDir) {
                if ((currDir as any) === (getDir(processed[i - 1].displayColor) as any) && (currDir as any) !== 0) {
                    phases[i] = currDir;
                } else {
                    phases[i] = phases[i - 1];
                }
            } else {
                phases[i] = phases[i - 1];
            }

            processed[i].phase = phases[i];
        }

        // 3. Cycles
        const cycles: any[] = [];
        let startIdx = 0;
        for (let i = 1; i <= phases.length; i++) {
            if (i === phases.length || phases[i] !== phases[startIdx]) {
                const chunk = candles.slice(startIdx, i);
                cycles.push({
                    phase: phases[startIdx] === 1 ? "UP" : "DOWN",
                    high: Math.max(...chunk.map((c) => c.high)),
                    low: Math.min(...chunk.map((c) => c.low)),
                    startIdx,
                    endIdx: i,
                });
                startIdx = i;
            }
        }

        // 4. Trend
        let trend = "NEUTRAL";
        const completedCycles = cycles.slice(0, -1);
        const upCycles = completedCycles.filter((c) => c.phase === "UP");
        const downCycles = completedCycles.filter((c) => c.phase === "DOWN");

        if (upCycles.length >= 2 && downCycles.length >= 2) {
            const lastUp = upCycles[upCycles.length - 1];
            const prevUp = upCycles[upCycles.length - 2];
            const lastDown = downCycles[downCycles.length - 1];
            const prevDown = downCycles[downCycles.length - 2];

            const hh = lastUp.high > prevUp.high;
            const hl = lastDown.low > prevDown.low;
            const lh = lastUp.high < prevUp.high;
            const ll = lastDown.low < prevDown.low;

            if (hh && hl) trend = "UP";
            else if (lh && ll) trend = "DOWN";
        }

        return { processed, phases, cycles, trend };
    };

    const renderChart = (tf: string, candles: Candle[], index: number) => {
        const availableTfs = ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d", "1w"];

        if (!candles.length) return (
            <div className="bg-gray-800 rounded-xl p-2 border border-gray-700 shadow-2xl h-[200px] flex flex-col">
                <div className="flex justify-between items-center mb-1">
                    <select
                        value={tf}
                        onChange={(e) => handleTimeframeChange(index, e.target.value)}
                        className="bg-gray-700 text-white text-xs rounded px-2 py-1 border border-gray-600 outline-none"
                    >
                        {availableTfs.map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                </div>
                <div className="flex-1 flex items-center justify-center text-gray-500 italic">Loading {tf} data...</div>
            </div>
        );

        const { processed, trend } = processRelativeCandles(candles);
        const slice = processed.slice(-100);

        const max = Math.max(...slice.map(c => c.high));
        const min = Math.min(...slice.map(c => c.low));
        const range = (max - min) * 1.02 || 1; // Add 2% breathing room

        const chartW = 800;
        const chartH = 200;
        const padX = 5;
        const padY = 1;

        const getX = (i: number) => (i / (slice.length - 1)) * (chartW - 2 * padX) + padX;
        const getY = (val: number) => chartH - padY - ((val - min) / range) * (chartH - 2 * padY);

        return (
            <div className="bg-gray-800 rounded-lg px-2 py-1 border border-gray-700 shadow-2xl">
                <div className="flex justify-between items-center mb-0">
                    <div className="flex items-center gap-2">
                        <select
                            value={tf}
                            onChange={(e) => handleTimeframeChange(index, e.target.value)}
                            className="bg-gray-700 text-white text-sm font-bold rounded px-2 py-1 border border-gray-600 outline-none focus:ring-2 focus:ring-emerald-500/50"
                        >
                            {availableTfs.map(t => <option key={t} value={t}>{t}</option>)}
                        </select>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${trend === 'UP' ? 'bg-emerald-500/20 text-emerald-400' : trend === 'DOWN' ? 'bg-red-500/20 text-red-400' : 'bg-gray-700 text-gray-400'}`}>
                            {trend}
                        </span>
                    </div>
                </div>

                <svg viewBox={`0 0 ${chartW} ${chartH}`} width="100%" height={chartH} className="cursor-crosshair overflow-visible">
                    {slice.map((c, i) => {
                        if (i === 0) return null;
                        const xPrev = getX(i - 1);
                        const xCurr = getX(i);
                        const phaseColor = c.phase === 1 ? "rgba(16, 185, 129, 0.05)" : "rgba(239, 68, 68, 0.05)";
                        return <rect key={`phase-${i}`} x={xPrev} y={0} width={xCurr - xPrev} height={chartH} fill={phaseColor} />;
                    })}

                    {[0, 0.25, 0.5, 0.75, 1].map(p => (
                        <line key={p} x1={padX} x2={chartW - padX} y1={getY(min + p * range)} y2={getY(min + p * range)} stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
                    ))}

                    {slice.map((c, i) => {
                        const x = getX(i);
                        const color = c.displayColor;
                        const w = (chartW - 2 * padX) / slice.length * 0.7;

                        const wickY1 = getY(c.high);
                        const wickY2 = getY(c.low);
                        const bodyY1 = getY(c.displayOpen);
                        const bodyY2 = getY(c.displayClose);

                        const bodyTop = Math.min(bodyY1, bodyY2);
                        const bodyHeight = Math.max(1, Math.abs(bodyY1 - bodyY2));

                        return (
                            <g key={i}>
                                <line x1={x} y1={wickY1} x2={x} y2={wickY2} stroke={color} strokeWidth="1.5" />
                                <rect x={x - w / 2} y={bodyTop} width={w} height={bodyHeight} fill={color} />
                                <circle cx={x} cy={chartH - 4} r="1.5" fill={c.phase === 1 ? "#10b981" : "#ef4444"} />
                            </g>
                        );
                    })}
                </svg>
            </div>
        );
    };

    return (
        <div className="space-y-2 max-w-7xl mx-auto p-2">
            <header className="space-y-0.5">
                <h1 className="text-2xl font-extrabold bg-gradient-to-r from-emerald-400 to-sky-500 bg-clip-text text-transparent">
                    Eternal Strategy
                </h1>
                <p className="text-gray-400 max-w-3xl text-[10px]">
                    A robust trend-following strategy that utilizes relative candles and market cycles.
                </p>
            </header>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {timeframes.map((tf, i) => renderChart(tf, chartData[tf] || [], i))}
            </div>

            {/* Info and Watchlists */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Watchlists */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-xl">
                        <div className="bg-emerald-500/10 p-2 border-b border-gray-700">
                            <h3 className="font-bold text-emerald-400 text-sm">Eternal Buy Setups</h3>
                        </div>
                        <div className="p-1 max-h-[200px] overflow-y-auto custom-scrollbar">
                            {!eternalBuyWl?.tickers.length && <div className="p-4 text-center text-gray-500 text-xs italic">Scanning...</div>}
                            {eternalBuyWl?.tickers.map(t => (
                                <div key={t.symbol} className="flex justify-between items-center p-2 hover:bg-white/5 rounded-lg group transition-all">
                                    <span className="font-mono text-gray-200 text-xs cursor-pointer hover:text-emerald-400" onClick={() => onSymbolSelect(t.symbol)}>{t.symbol}</span>
                                    <button onClick={() => handleRemoveTicker(eternalBuyWl.id, t.symbol)} className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">×</button>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden shadow-xl">
                        <div className="bg-red-500/10 p-2 border-b border-gray-700">
                            <h3 className="font-bold text-red-400 text-sm">Eternal Sell Setups</h3>
                        </div>
                        <div className="p-1 max-h-[200px] overflow-y-auto custom-scrollbar">
                            {!eternalSellWl?.tickers.length && <div className="p-4 text-center text-gray-500 text-xs italic">Scanning...</div>}
                            {eternalSellWl?.tickers.map(t => (
                                <div key={t.symbol} className="flex justify-between items-center p-2 hover:bg-white/5 rounded-lg group transition-all">
                                    <span className="font-mono text-gray-200 text-xs cursor-pointer hover:text-red-400" onClick={() => onSymbolSelect(t.symbol)}>{t.symbol}</span>
                                    <button onClick={() => handleRemoveTicker(eternalSellWl.id, t.symbol)} className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity">×</button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Strategy Notes */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="bg-gray-800/50 p-4 rounded-xl border border-gray-700 hover:border-emerald-500/30 transition-colors">
                        <h4 className="font-bold text-emerald-400 mb-1 uppercase tracking-wider text-[10px]">Phases</h4>
                        <p className="text-[10px] text-gray-400 leading-tight">Determined by relative candle sequences and color consistency.</p>
                    </div>
                    <div className="bg-gray-800/50 p-4 rounded-xl border border-gray-700 hover:border-sky-500/30 transition-colors">
                        <h4 className="font-bold text-sky-400 mb-1 uppercase tracking-wider text-[10px]">Cycles</h4>
                        <p className="text-[10px] text-gray-400 leading-tight">Alternating UP/DOWN phases forming historical market chunks.</p>
                    </div>
                    <div className="bg-gray-800/50 p-4 rounded-xl border border-gray-700 hover:border-purple-500/30 transition-colors">
                        <h4 className="font-bold text-purple-400 mb-1 uppercase tracking-wider text-[10px]">Trend</h4>
                        <p className="text-[10px] text-gray-400 leading-tight">Derived from HH+HL or LH+LL across recent completed cycles.</p>
                    </div>
                </div>
            </div>

            {/* Rules */}
            <section className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-2xl p-3 border border-gray-700 shadow-2xl">
                <h3 className="text-lg font-bold mb-2 flex items-center gap-2">
                    <span className="text-emerald-400">⚡</span> Execution Rules
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-gray-300">
                    <div>
                        <h5 className="text-white font-bold mb-2 border-l-4 border-emerald-500 pl-4 text-sm">Entry Conditions</h5>
                        <ul className="space-y-1 text-xs list-disc ml-5">
                            <li><span className="text-emerald-400 font-bold">Long:</span> Trend UP + trigger on DOWN phase pullback.</li>
                            <li><span className="text-red-400 font-bold">Short:</span> Trend DOWN + trigger on UP phase relief rally.</li>
                            <li>Orders placed as <span className="text-white">Stop Market</span> at the extreme break.</li>
                        </ul>
                    </div>
                    <div>
                        <h5 className="text-white font-bold mb-2 border-l-4 border-sky-500 pl-4 text-sm">Management</h5>
                        <ul className="space-y-1 text-xs list-disc ml-5">
                            <li>Stop Loss anchored to the previous candle's extreme.</li>
                            <li>Targeting a fixed <span className="text-white font-bold">2:1 R:R ratio</span>.</li>
                            <li>Unfilled orders expire after 1 candle to maintain validity.</li>
                        </ul>
                    </div>
                </div>
            </section>
        </div>
    );
}
