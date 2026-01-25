
const BounceStrategy = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-purple-400 to-indigo-500 bg-clip-text text-transparent mb-6">
        20 Bounce Strategy
      </h1>

      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-purple-500 border border-[var(--border-primary)]">
        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li>D1 EMA 8-20 alignment</li>
          <li>D1 MACD default configuration</li>
          <li>H4 pullback below 20 EMA before cross</li>
          <li>M30 EMA 20-50 crossover for entry confirmation</li>
          <li>For crypto: use EMAs 9-25</li>
        </ul>
      </section>
    </div>
  );
};

export default BounceStrategy;
