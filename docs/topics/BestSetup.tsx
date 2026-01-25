
import React from 'react';

const BestSetup = () => {
    return (
        <div className="space-y-8 max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-emerald-400 to-sky-500 bg-clip-text text-transparent mb-6">
                The Ultimate Trading Setup
            </h1>

            <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-sky-500 border border-[var(--border-primary)]">
                <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)] flex items-center gap-2">
                    <span>💻</span> Hardware & Software
                </h2>
                <div className="space-y-4 text-[var(--text-secondary)]">
                    <div className="bg-[var(--bg-tertiary)] p-4 rounded-lg border border-[var(--border-primary)]">
                        <h3 className="font-bold text-[var(--text-primary)] mb-1">The Arc Browser</h3>
                        <p>Install the <strong>Arc browser</strong>. Its sidebar-based navigation and "Spaces" feature allow you to organize your trading tools, charts, and journals without the clutter of traditional tabs.</p>
                    </div>

                    <div className="bg-[var(--bg-tertiary)] p-4 rounded-lg border border-[var(--border-primary)]">
                        <h3 className="font-bold text-[var(--text-primary)] mb-1">Large Screen Real Estate</h3>
                        <p>Use a <strong>large monitor</strong> (or multiple). Being able to see multiple timeframes and your order book simultaneously is a significant advantage. If you're on a laptop, consider an external display.</p>
                    </div>

                    <div className="bg-[var(--bg-tertiary)] p-4 rounded-lg border border-[var(--border-primary)]">
                        <h3 className="font-bold text-[var(--text-primary)] mb-1">BingX Account</h3>
                        <p>Setup a <strong>BingX account</strong>. It provides a robust API for TopTrader to execute trades and offers a wide range of perpetual futures with competitive fees.</p>
                    </div>
                </div>
            </section>

            <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-emerald-500 border border-[var(--border-primary)]">
                <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)] flex items-center gap-2">
                    <span>🧘</span> The Trading Environment
                </h2>
                <p className="text-[var(--text-secondary)]">
                    Your physical surroundings directly impact your mental state. A professional environment breeds professional results.
                </p>
                <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
                    <li><strong className="text-[var(--text-primary)]">Clean Room:</strong> A cluttered space leads to a cluttered mind. Keep your trading desk and room spotless.</li>
                    <li><strong className="text-[var(--text-primary)]">Zero Distractions:</strong> Trade in a quiet room. Turn off non-trading notifications on your phone.</li>
                    <li><strong className="text-[var(--text-primary)]">Ergonomics:</strong> A comfortable chair and proper desk height prevent physical fatigue during long sessions.</li>
                </ul>
            </section>

            <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-purple-500 border border-[var(--border-primary)]">
                <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)] flex items-center gap-2">
                    <span>🧠</span> Professional Recommendations
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 rounded-lg bg-sky-500/5 border border-sky-500/20">
                        <h3 className="font-bold text-sky-400 mb-1 italic">Mindset First</h3>
                        <p className="text-sm text-[var(--text-secondary)]">Treat trading as a business, not a hobby. If you treat it like a hobby, it will pay you like a hobby (or worse, charge you like one).</p>
                    </div>
                    <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                        <h3 className="font-bold text-emerald-400 mb-1 italic">The 1% Rule</h3>
                        <p className="text-sm text-[var(--text-secondary)]">Never risk more than 1% of your total account balance on a single trade. Preservation of capital is your first priority.</p>
                    </div>
                    <div className="p-4 rounded-lg bg-amber-500/5 border border-amber-500/20">
                        <h3 className="font-bold text-amber-400 mb-1 italic">Continuous Learning</h3>
                        <p className="text-sm text-[var(--text-secondary)]">The market is always changing. Spend at least 30 minutes a day reviewing your trades and studying price action.</p>
                    </div>
                    <div className="p-4 rounded-lg bg-rose-500/5 border border-rose-500/20">
                        <h3 className="font-bold text-rose-400 mb-1 italic">Health is Wealth</h3>
                        <p className="text-sm text-[var(--text-secondary)]">Your brain is your most valuable asset. Proper sleep, hydration, and nutrition are as important as any technical indicator.</p>
                    </div>
                </div>
            </section>

            <blockquote className="border-l-4 border-sky-500 pl-4 italic text-[var(--text-secondary)] mt-4 bg-[var(--bg-tertiary)] p-6 rounded-lg text-lg">
                "Environment is the invisible hand that shapes human behavior."
            </blockquote>
        </div>
    );
};

export default BestSetup;
