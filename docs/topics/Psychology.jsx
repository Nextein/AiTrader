
const Psychology = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-sky-400 to-blue-500 bg-clip-text text-transparent mb-6">
        Trading Psychology
      </h1>

      {/* Introduction */}
      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-sky-500 border border-[var(--border-primary)]">
        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)]">Introduction</h2>
        <p className="text-[var(--text-secondary)]">
          Trading emotions can betray us and need to be handled carefully. Emotional control separates professionals from amateurs.
        </p>

        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li><strong className="text-[var(--text-primary)]">Fear:</strong> leads to hesitation and poor execution.</li>
          <li><strong className="text-[var(--text-primary)]">Depression:</strong> loss of confidence after a losing streak.</li>
          <li><strong className="text-[var(--text-primary)]">Greed:</strong> inability to take profits and overtrading.</li>
          <li><strong className="text-[var(--text-primary)]">Euphoria:</strong> overconfidence after big wins.</li>
        </ul>

        <p className="text-[var(--text-secondary)]">To control emotions, get "in the zone" by maintaining:</p>
        <ul className="list-disc ml-6 space-y-1 text-[var(--text-secondary)]">
          <li>Organized trading station</li>
          <li>No distractions</li>
          <li>Full focus</li>
          <li>Positive mental environment</li>
        </ul>
      </section>

      {/* Risk Management */}
      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-emerald-500 border border-[var(--border-primary)]">
        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)]">Risk Management for Emotional Stability</h2>
        <ol className="list-decimal ml-6 space-y-2 text-[var(--text-secondary)]">
          <li>Protect your capital through planning and position sizing.</li>
          <li>Stick to your plan and ignore external opinions.</li>
          <li>Remember: no trade is also a trade.</li>
          <li>Use leverage sensibly — higher leverage = higher emotional pressure.</li>
        </ol>
      </section>

      {/* Mindset and Emotions */}
      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-purple-500 border border-[var(--border-primary)]">
        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)]">Mindset and Emotions</h2>
        <p className="text-[var(--text-secondary)]">
          A correct mindset means accepting risk and understanding you are trading probabilities, not certainties.
        </p>
        <ul className="list-disc ml-6 space-y-1 text-[var(--text-secondary)]">
          <li>Recognize emotional triggers like pressure and comparison.</li>
          <li>Accept that losses are part of the process.</li>
          <li>Develop a structured strategy and follow it for 25 trades before review.</li>
          <li>Focus on consistency, not daily profits.</li>
        </ul>
      </section>

      {/* Psychology in Trading */}
      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-amber-500 border border-[var(--border-primary)]">
        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)]">Psychology in Trading</h2>
        <p className="text-[var(--text-secondary)]">
          Professional traders see markets as tools for capital growth; amateurs see them as threats. You must lose the fear of losing money — scared money doesn't make money.
        </p>
        <p className="text-[var(--text-secondary)]">
          The ultimate goal is to trade effortlessly and intuitively through preparation and emotional mastery.
        </p>
        <blockquote className="border-l-4 border-sky-500 pl-4 italic text-[var(--text-secondary)] mt-4 bg-[var(--bg-tertiary)] p-4 rounded-lg">
          "No man ever reached excellence in any art or profession without having passed
          through the slow and painful process of preparation." — Quintus Horatius Flaccus
        </blockquote>
      </section>

      {/* Practical Tips */}
      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-rose-500 border border-[var(--border-primary)]">
        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)]">Practical Tips</h2>
        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li>Focus mentally and physically (exercise, diet, rest).</li>
          <li>Patience is key — only take the best setups.</li>
          <li>Keep a trading journal and review your performance.</li>
          <li>Handle stress through mindfulness, meditation, or prayer.</li>
          <li>Don't trade when emotionally unstable or stressed.</li>
          <li>Focus on being a trader long-term, not short-term profits.</li>
        </ul>
      </section>
    </div>
  );
};

export default Psychology;
