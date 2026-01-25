
const Hedging = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-amber-400 to-yellow-500 bg-clip-text text-transparent mb-6">
        Hedging
      </h1>

      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-amber-500 border border-[var(--border-primary)]">
        <p className="text-[var(--text-secondary)]">
          Hedging is about protecting your assets by managing trades like a business. Use leverage strategically so a portion of your positions protect your entire portfolio.
        </p>

        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li><strong className="text-[var(--text-primary)]">Long-term view and portfolio protection:</strong> hedge trades complement your main positions.</li>
          <li><strong className="text-[var(--text-primary)]">Different handling:</strong> hedge trades are held longer and treated differently than normal trades.</li>
          <li><strong className="text-[var(--text-primary)]">Exit rules:</strong> close hedges only on strong signals against them or stop-loss hits.</li>
          <li><strong className="text-[var(--text-primary)]">Normal trades:</strong> short-term with defined targets.</li>
        </ul>

        <p className="text-[var(--text-secondary)]">
          Example: if a hedge short is profitable, scale or rebalance using generated profits to safely increase long exposure.
        </p>
      </section>
    </div>
  );
};

export default Hedging;
