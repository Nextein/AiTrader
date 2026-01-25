
const Indicators = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-purple-400 to-indigo-500 bg-clip-text text-transparent mb-6">
        Technical Indicators
      </h1>

      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-purple-500 border border-[var(--border-primary)]">
        <p className="text-[var(--text-secondary)]">
          Indicators help traders visualize trends and momentum. Use them as <strong className="text-[var(--text-primary)]">confirmation tools</strong>, not as standalone signals.
        </p>

        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li><strong className="text-[var(--text-primary)]">Moving Averages (MA, EMA, SMA):</strong> track trends over time</li>
          <li><strong className="text-[var(--text-primary)]">Relative Strength Index (RSI):</strong> identifies overbought/oversold conditions</li>
          <li><strong className="text-[var(--text-primary)]">MACD:</strong> trend and momentum tracking</li>
          <li><strong className="text-[var(--text-primary)]">Bollinger Bands:</strong> measure market volatility</li>
        </ul>
      </section>
    </div>
  );
};

export default Indicators;
