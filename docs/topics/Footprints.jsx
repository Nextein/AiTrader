
const Footprints = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-purple-400 to-indigo-500 bg-clip-text text-transparent mb-6">
        Footprint Charts
      </h1>

      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-purple-500 border border-[var(--border-primary)]">
        <p className="text-[var(--text-secondary)]">
          Footprint charts visualize order flow — showing where buyers and sellers are most active inside each candle.
        </p>

        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li>Analyze bid/ask imbalances</li>
          <li>Spot absorption and exhaustion zones</li>
          <li>Understand true market intent beyond price action</li>
        </ul>
      </section>
    </div>
  );
};

export default Footprints;
