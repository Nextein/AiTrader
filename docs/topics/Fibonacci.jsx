
const Fibonacci = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-amber-400 to-yellow-500 bg-clip-text text-transparent mb-6">
        Fibonacci Tools
      </h1>

      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-amber-500 border border-[var(--border-primary)]">
        <p className="text-[var(--text-secondary)]">
          Fibonacci retracements and extensions are key tools for identifying potential support and resistance levels.
        </p>

        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li>Common retracement levels: 38.2%, 50%, 61.8%</li>
          <li>Combine with trend analysis for high-probability setups</li>
          <li>Watch confluence zones for entries</li>
        </ul>
      </section>
    </div>
  );
};

export default Fibonacci;
