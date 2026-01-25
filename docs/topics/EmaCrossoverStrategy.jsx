
const EmaCrossoverStrategy = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-sky-400 to-blue-500 bg-clip-text text-transparent mb-6">
        EMA Crossover Strategy
      </h1>

      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-sky-500 border border-[var(--border-primary)]">
        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li>H1 EMA 20-50 cross triggers setup.</li>
          <li>Enter on price closing above 20 EMA after pullback.</li>
          <li>Confirm D1 trend (20-50 EMAs aligned & new daily highs).</li>
          <li>Use EMAs 9-25 for crypto markets.</li>
        </ul>
      </section>
    </div>
  );
};

export default EmaCrossoverStrategy;
