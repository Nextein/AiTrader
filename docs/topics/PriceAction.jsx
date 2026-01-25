
const PriceAction = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-sky-400 to-blue-500 bg-clip-text text-transparent mb-6">
        Price Action
      </h1>

      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-sky-500 border border-[var(--border-primary)]">
        <p className="text-[var(--text-secondary)]">
          Price action is the study of how price moves — without relying heavily on indicators. It's about reading candlesticks and understanding market structure.
        </p>

        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li>Identify <strong className="text-[var(--text-primary)]">support and resistance zones</strong></li>
          <li>Look for <strong className="text-[var(--text-primary)]">breakouts, retests, and false break patterns</strong></li>
          <li>Combine with <strong className="text-[var(--text-primary)]">volume</strong> for confirmation</li>
        </ul>
      </section>
    </div>
  );
};

export default PriceAction;
