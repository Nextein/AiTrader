import React from "react";

export default function Essence({ symbol }: { symbol: string; onSymbolSelect: (s: string) => void }) {
    return (
        <div className="space-y-8 max-w-7xl mx-auto">
            <header className="space-y-2">
                <h1 className="text-4xl font-extrabold bg-gradient-to-r from-sky-400 to-indigo-500 bg-clip-text text-transparent">
                    Essence Strategy
                </h1>
                <p className="text-gray-400 max-w-3xl text-lg">
                    A distilled, pure price-action strategy based on previous candle extremes.
                </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <section className="bg-gray-800/50 p-8 rounded-2xl border border-gray-700 shadow-xl">
                    <h3 className="text-2xl font-bold mb-6 flex items-center gap-2">
                        <span className="bg-sky-500/20 text-sky-400 p-2 rounded-lg">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </span>
                        Core Concept
                    </h3>
                    <p className="text-gray-300 mb-6 leading-relaxed">
                        Essence is the fundamental core of the Eternal algorithm. It eliminates all market context filters (phases, cycles, trends) to focus solely on the breaking of previous candle levels.
                    </p>
                    <div className="space-y-4">
                        <div className="flex items-start gap-4">
                            <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                                <span className="text-emerald-500 font-bold">1</span>
                            </div>
                            <div>
                                <h4 className="text-white font-semibold">Previous High/Low</h4>
                                <p className="text-sm text-gray-400">Orders are placed at the highest and lowest points of the most recently closed candle.</p>
                            </div>
                        </div>
                        <div className="flex items-start gap-4">
                            <div className="w-8 h-8 rounded-full bg-sky-500/10 flex items-center justify-center flex-shrink-0">
                                <span className="text-sky-500 font-bold">2</span>
                            </div>
                            <div>
                                <h4 className="text-white font-semibold">Continuous Updates</h4>
                                <p className="text-sm text-gray-400">As each new candle forms, orders are recalculated and moved to the new extremes.</p>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-2xl p-8 border border-gray-700 shadow-xl">
                    <h3 className="text-2xl font-bold mb-6">Execution Logic</h3>
                    <div className="space-y-6">
                        <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-xl">
                            <h4 className="text-emerald-400 font-bold mb-2 uppercase text-xs tracking-wider">Buy Order</h4>
                            <p className="text-sm text-gray-300">Placed at the <span className="text-white font-mono">Previous High</span>. If triggered, Stop Loss is set at the <span className="text-white font-mono">Previous Low</span>.</p>
                        </div>
                        <div className="p-4 bg-red-500/5 border border-red-500/10 rounded-xl">
                            <h4 className="text-red-400 font-bold mb-2 uppercase text-xs tracking-wider">Sell Order</h4>
                            <p className="text-sm text-gray-300">Placed at the <span className="text-white font-mono">Previous Low</span>. If triggered, Stop Loss is set at the <span className="text-white font-mono">Previous High</span>.</p>
                        </div>
                        <div className="flex items-center justify-between p-4 bg-indigo-500/5 border border-indigo-500/10 rounded-xl">
                            <div>
                                <h4 className="text-indigo-400 font-bold uppercase text-xs tracking-wider">Take Profit</h4>
                                <p className="text-sm text-gray-300">Fixed <span className="text-white font-bold">1:1 Risk/Reward</span> ratio.</p>
                            </div>
                            <div className="px-3 py-1 bg-indigo-500 text-white text-xs font-bold rounded-full">
                                1:1 RR
                            </div>
                        </div>
                    </div>
                </section>
            </div>

            <section className="bg-gray-800 p-8 rounded-2xl border border-gray-700">
                <h3 className="text-xl font-bold mb-4">When to use?</h3>
                <p className="text-gray-400 text-sm">
                    Essence is designed for high-volatility environments where price frequently breaks candle extremes. It's a "raw" strategy that requires careful symbol selection as it lacks the sophisticated filters of the Eternal model.
                </p>
            </section>
        </div>
    );
}
