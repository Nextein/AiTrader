
const RiskManagement = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-emerald-400 to-green-500 bg-clip-text text-transparent mb-6">
        Risk Management
      </h1>

      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-emerald-500 border border-[var(--border-primary)]">
        <p className="text-[var(--text-secondary)]">
          Risk management is the cornerstone of trading longevity. Protecting your capital is the <strong className="text-[var(--text-primary)]">#1 goal</strong>.
        </p>

        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li><strong className="text-[var(--text-primary)]">Risk only 1–2%</strong> of capital per trade.</li>
          <li>Limit total open trades to <strong className="text-[var(--text-primary)]">7 at a time</strong>.</li>
          <li>Use <strong className="text-[var(--text-primary)]">stop losses</strong> religiously.</li>
          <li>Ensure your plan defines <strong className="text-[var(--text-primary)]">invalidation and exit rules</strong>.</li>
        </ul>

        <p className="text-[var(--text-secondary)]">
          For growing accounts: use <strong className="text-[var(--text-primary)]">2% risk</strong> on intraday 1:1 trades. Adjust as equity and experience grow.
        </p>
      </section>
    </div>
  );
};

export default RiskManagement;
