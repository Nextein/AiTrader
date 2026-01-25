import React from "react";

type Pattern = {
  id: string;
  name: string;
  description: string;
  category: "Single" | "Dual" | "Triple";
  draw: () => JSX.Element;
};

const patterns: Pattern[] = [
  // === SINGLE CANDLE PATTERNS ===
  {
    id: "doji",
    name: "Doji",
    category: "Single",
    description:
      "Indecision candle with nearly equal open and close prices, forming a cross shape.",
    draw: () => (
      <>
        <line x1={50} y1={20} x2={50} y2={80} stroke="#9ca3af" strokeWidth="2" />
        <line x1={40} y1={50} x2={60} y2={50} stroke="#9ca3af" strokeWidth="3" />
      </>
    ),
  },
  {
    id: "hammer",
    name: "Hammer",
    category: "Single",
    description:
      "Bullish reversal after a downtrend; small body near the top and long lower shadow.",
    draw: () => (
      <>
        <line x1={50} y1={30} x2={50} y2={90} stroke="#10b981" strokeWidth="2" />
        <rect x={40} y={30} width={20} height={10} fill="#10b981" stroke="#10b981" />
      </>
    ),
  },
  {
    id: "inverted_hammer",
    name: "Inverted Hammer",
    category: "Single",
    description:
      "Bullish reversal after a decline; small body near the bottom and long upper wick.",
    draw: () => (
      <>
        <line x1={50} y1={10} x2={50} y2={70} stroke="#10b981" strokeWidth="2" />
        <rect x={40} y={70} width={20} height={10} fill="#10b981" stroke="#10b981" />
      </>
    ),
  },
  {
    id: "shooting_star",
    name: "Shooting Star",
    category: "Single",
    description:
      "Bearish reversal after an uptrend; small body and long upper wick indicating exhaustion.",
    draw: () => (
      <>
        <line x1={50} y1={10} x2={50} y2={80} stroke="#ef4444" strokeWidth="2" />
        <rect x={40} y={70} width={20} height={10} fill="#ef4444" stroke="#ef4444" />
      </>
    ),
  },
  {
    id: "spinning_top",
    name: "Spinning Top",
    category: "Single",
    description:
      "Small body with long upper and lower shadows; indicates indecision or balance of forces.",
    draw: () => (
      <>
        <line x1={50} y1={20} x2={50} y2={80} stroke="#9ca3af" strokeWidth="2" />
        <rect x={45} y={45} width={10} height={10} fill="#9ca3af" stroke="#9ca3af" />
      </>
    ),
  },
  {
    id: "marubozu_bullish",
    name: "Bullish Marubozu",
    category: "Single",
    description:
      "Strong bullish candle with no shadows; open equals low, close equals high.",
    draw: () => <rect x={40} y={20} width={20} height={60} fill="#10b981" stroke="#10b981" />,
  },
  {
    id: "marubozu_bearish",
    name: "Bearish Marubozu",
    category: "Single",
    description:
      "Strong bearish candle with no shadows; open equals high, close equals low.",
    draw: () => <rect x={40} y={20} width={20} height={60} fill="#ef4444" stroke="#ef4444" />,
  },

  // === DUAL CANDLE PATTERNS ===
  {
    id: "bullish_engulfing",
    name: "Bullish Engulfing",
    category: "Dual",
    description:
      "A large green candle fully engulfs the previous small red candle — bullish reversal.",
    draw: () => (
      <>
        <rect x={30} y={50} width={10} height={20} fill="#ef4444" stroke="#ef4444" />
        <rect x={45} y={30} width={20} height={40} fill="#10b981" stroke="#10b981" />
      </>
    ),
  },
  {
    id: "bearish_engulfing",
    name: "Bearish Engulfing",
    category: "Dual",
    description:
      "A large red candle fully engulfs the previous small green candle — bearish reversal.",
    draw: () => (
      <>
        <rect x={30} y={50} width={10} height={20} fill="#10b981" stroke="#10b981" />
        <rect x={45} y={30} width={20} height={40} fill="#ef4444" stroke="#ef4444" />
      </>
    ),
  },
  {
    id: "tweezer_bottoms",
    name: "Tweezer Bottoms",
    category: "Dual",
    description:
      "Two candles with matching lows after a decline — potential bullish reversal.",
    draw: () => (
      <>
        <rect x={35} y={50} width={10} height={20} fill="#ef4444" stroke="#ef4444" />
        <rect x={55} y={50} width={10} height={20} fill="#10b981" stroke="#10b981" />
      </>
    ),
  },
  {
    id: "tweezer_tops",
    name: "Tweezer Tops",
    category: "Dual",
    description:
      "Two candles with matching highs after an uptrend — potential bearish reversal.",
    draw: () => (
      <>
        <rect x={35} y={30} width={10} height={20} fill="#10b981" stroke="#10b981" />
        <rect x={55} y={30} width={10} height={20} fill="#ef4444" stroke="#ef4444" />
      </>
    ),
  },
  {
    id: "train_tracks",
    name: "Train Tracks",
    category: "Dual",
    description:
      "Two large candles of opposite color and similar size; signals strong potential reversal.",
    draw: () => (
      <>
        <rect x={30} y={30} width={15} height={40} fill="#ef4444" stroke="#ef4444" />
        <rect x={55} y={30} width={15} height={40} fill="#10b981" stroke="#10b981" />
      </>
    ),
  },

  // === TRIPLE CANDLE PATTERNS ===
  {
    id: "morning_star",
    name: "Morning Star",
    category: "Triple",
    description:
      "Three-candle bullish reversal: red candle, small indecisive candle, then strong green candle.",
    draw: () => (
      <>
        <rect x={20} y={40} width={10} height={40} fill="#ef4444" stroke="#ef4444" />
        <rect x={40} y={60} width={10} height={10} fill="#9ca3af" stroke="#9ca3af" />
        <rect x={60} y={20} width={10} height={60} fill="#10b981" stroke="#10b981" />
      </>
    ),
  },
  {
    id: "evening_star",
    name: "Evening Star",
    category: "Triple",
    description:
      "Three-candle bearish reversal: green candle, small indecisive candle, then strong red candle.",
    draw: () => (
      <>
        <rect x={20} y={20} width={10} height={60} fill="#10b981" stroke="#10b981" />
        <rect x={40} y={60} width={10} height={10} fill="#9ca3af" stroke="#9ca3af" />
        <rect x={60} y={40} width={10} height={40} fill="#ef4444" stroke="#ef4444" />
      </>
    ),
  },
  {
    id: "three_white_soldiers",
    name: "Three White Soldiers",
    category: "Triple",
    description:
      "Three consecutive bullish candles, each closing higher — strong bullish reversal signal.",
    draw: () => (
      <>
        <rect x={25} y={40} width={10} height={40} fill="#10b981" stroke="#10b981" />
        <rect x={45} y={30} width={10} height={50} fill="#10b981" stroke="#10b981" />
        <rect x={65} y={20} width={10} height={60} fill="#10b981" stroke="#10b981" />
      </>
    ),
  },
  {
    id: "three_black_crows",
    name: "Three Black Crows",
    category: "Triple",
    description:
      "Three consecutive bearish candles, each closing lower — strong bearish reversal signal.",
    draw: () => (
      <>
        <rect x={25} y={20} width={10} height={60} fill="#ef4444" stroke="#ef4444" />
        <rect x={45} y={30} width={10} height={50} fill="#ef4444" stroke="#ef4444" />
        <rect x={65} y={40} width={10} height={40} fill="#ef4444" stroke="#ef4444" />
      </>
    ),
  },
];

const CandlestickCheatsheet = () => (
  <div className="space-y-12">
    <div>
      <h2 className="text-3xl font-bold font-outfit mb-2 bg-gradient-to-r from-sky-400 to-blue-500 bg-clip-text text-transparent">
        Candlestick Cheat Sheet
      </h2>
      <p className="text-[var(--text-secondary)] max-w-2xl">
        A visual guide to key candlestick patterns — from single-candle indecision signals like the
        Doji to multi-candle reversal setups like the Morning and Evening Star.
      </p>
    </div>

    {["Single", "Dual", "Triple"].map((category) => (
      <div key={category}>
        <h3 className="text-2xl font-semibold font-outfit mb-4 text-[var(--text-primary)]">
          {category}-Candle Patterns
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {patterns
            .filter((p) => p.category === category)
            .map((pattern) => (
              <div
                key={pattern.id}
                className="bg-[var(--bg-secondary)]/50 backdrop-blur-md p-6 rounded-xl border border-[var(--border-primary)] text-center hover:shadow-lg hover:shadow-sky-500/10 transition-all"
              >
                <svg viewBox="0 0 100 100" width="120" height="120" className="mx-auto mb-3">
                  {pattern.draw()}
                </svg>
                <h4 className="text-lg font-semibold font-outfit text-[var(--text-primary)] mb-1">
                  {pattern.name}
                </h4>
                <p className="text-sm text-[var(--text-secondary)]">{pattern.description}</p>
              </div>
            ))}
        </div>
      </div>
    ))}
  </div>
);

export default CandlestickCheatsheet;
