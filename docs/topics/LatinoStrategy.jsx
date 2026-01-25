
const LatinoStrategy = () => {
  // Fake candlestick data for illustration
  const candles = [
    { open: 100, high: 105, low: 98, close: 102 },
    { open: 102, high: 107, low: 101, close: 106 },
    { open: 106, high: 108, low: 104, close: 105 },
    { open: 105, high: 110, low: 104, close: 109 },
    { open: 109, high: 111, low: 107, close: 108 },
    { open: 108, high: 112, low: 106, close: 110 },
    { open: 110, high: 115, low: 109, close: 114 },
    { open: 114, high: 116, low: 112, close: 113 },
    { open: 113, high: 118, low: 112, close: 117 },
    { open: 117, high: 120, low: 115, close: 119 },
    { open: 119, high: 122, low: 117, close: 121 },
    { open: 121, high: 124, low: 119, close: 123 },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold font-outfit bg-gradient-to-r from-sky-400 to-blue-500 bg-clip-text text-transparent mb-2">
        TradingLatino — Squeeze-line + ADX + EMA
      </h2>

      {/* Short summary */}
      <div className="prose dark:prose-invert max-w-none">
        <p className="text-[var(--text-secondary)]">
          This strategy uses the Squeeze-line oscillator for entries when its slope changes
          direction, combined with ADX to confirm trend strength and an EMA to filter entries
          based on price proximity. The chart below illustrates this visually.
        </p>
      </div>

      {/* Rules box */}
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-md p-6 rounded-xl border border-[var(--border-primary)] shadow-lg shadow-sky-500/5">
        <h3 className="text-lg font-semibold font-outfit text-[var(--text-primary)] mb-3">Key Rules</h3>
        <ul className="list-disc ml-6 space-y-2 text-[var(--text-secondary)]">
          <li>Enter when the Squeeze-line changes slope (up or down).</li>
          <li>Buy when it slopes up it and its below 0.</li>
          <li>Sell when it slopes down it and its above 0.</li>
          <li>Only enter when ADX confirms a strong trend (rising above ~23).</li>
          <li>EMA filter: avoid entering if price is too far from the chosen EMA.</li>
          <li>Exits: flattening slope, ADX dropping, or price failing to react to 0 level.</li>
        </ul>
      </div>

      {/* Illustrative chart */}
      <div className="bg-[var(--bg-secondary)]/50 backdrop-blur-md p-6 rounded-xl border border-[var(--border-primary)] shadow-lg shadow-sky-500/5">
        <h3 className="text-md font-semibold font-outfit text-[var(--text-primary)] mb-3">Illustration</h3>
        <svg viewBox="0 0 600 250" width="100%" height="250" className="block">
          {/* Candlesticks */}
          {candles.map((candle, idx) => {
            const x = 40 + idx * 45;
            const scale = 8; // scale for visual simplicity
            const yOpen = 150 - (candle.open - 100) * scale;
            const yClose = 150 - (candle.close - 100) * scale;
            const yHigh = 150 - (candle.high - 100) * scale;
            const yLow = 150 - (candle.low - 100) * scale;
            const color = candle.close >= candle.open ? "#10B981" : "#EF4444";
            return (
              <g key={idx}>
                {/* Wick */}
                <line x1={x} x2={x} y1={yHigh} y2={yLow} stroke={color} strokeWidth="1" />
                {/* Body */}
                <rect x={x - 4} y={Math.min(yOpen, yClose)} width={8} height={Math.abs(yClose - yOpen) || 1} fill={color} />
              </g>
            );
          })}

          {/* EMA line */}
          <path
            d="M40 145 C 85 140, 130 138, 175 136 C 220 135, 265 137, 310 134 C 355 132, 400 135, 445 133 C 490 130, 535 132, 580 131"
            stroke="#0EA5E9"
            strokeWidth="2"
            fill="none"
            strokeDasharray="6 4"
          />
          <text x="450" y="120" fontSize="12" fill="#0EA5E9">EMA</text>

          {/* Squeeze-line oscillator */}
          <path
            d="M40 180 C 85 170, 130 165, 175 163 C 220 160, 265 165, 310 150 C 355 135, 400 120, 445 130 C 490 140, 535 135, 580 132"
            stroke="#F59E0B"
            strokeWidth="2.5"
            fill="none"
          />
          <line x1="40" x2="580" y1="150" y2="150" stroke="#9CA3AF" strokeWidth="1" /> {/* zero line */}
          <text x="45" y="147" fontSize="11" fill="#9CA3AF">0</text>

          {/* Slope-change markers */}
          <circle cx="310" cy="150" r="4" fill="#10B981" />
          <text x="318" y="154" fontSize="11" fill="#10B981">slope→up (entry)</text>

          <circle cx="400" cy="120" r="4" fill="#EF4444" />
          <text x="408" y="124" fontSize="11" fill="#EF4444">slope→down (entry)</text>

          {/* ADX annotation */}
          <path d="M310 180 C 350 160, 400 140, 450 145" stroke="#3B82F6" strokeWidth="1.5" fill="none" strokeDasharray="4 3" />
          <text x="460" y="140" fontSize="12" fill="#3B82F6">ADX ↑ (confirm)</text>
        </svg>
        <p className="text-sm text-[var(--text-secondary)] mt-3">
          Candlesticks represent price action. EMA is the blue dashed line. The orange line
          shows the Squeeze-line oscillator. Entry points are marked where the slope changes
          and ADX confirms trend strength.
        </p>
      </div>
    </div>
  );
};

export default LatinoStrategy;
