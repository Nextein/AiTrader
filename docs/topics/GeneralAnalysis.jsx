
const GeneralAnalysis = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-sky-400 to-blue-500 bg-clip-text text-transparent mb-6">
        General Analysis Strategy
      </h1>

      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-sky-500 border border-[var(--border-primary)]">
        <p className="text-[var(--text-secondary)]">
          Comprehensive multi-timeframe approach:
        </p>

        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li><strong className="text-[var(--text-primary)]">W1:</strong> Direction</li>
          <li><strong className="text-[var(--text-primary)]">D1:</strong> Direction & Levels</li>
          <li><strong className="text-[var(--text-primary)]">H4:</strong> Cyclicity, Trendlines, Divergences</li>
          <li><strong className="text-[var(--text-primary)]">H1:</strong> Price Action & Divergences</li>
          <li><strong className="text-[var(--text-primary)]">M15:</strong> Cyclicity & Relative Candles</li>
        </ul>

        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)] mt-6">Chain Champion Analysis</h2>
        <p className="text-[var(--text-secondary)]">
          Tools: Pitchfork, FIB CC Channel, VAH/VAL, VWAP
        </p>
        <p className="text-[var(--text-secondary)]">
          Look for strength when price movement aligns with volume increases.
        </p>
      </section>
    </div>
  );
};

export default GeneralAnalysis;
