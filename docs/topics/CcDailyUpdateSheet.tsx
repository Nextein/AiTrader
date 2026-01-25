import React from "react";

const ChainChampionsDailyUpdate = () => {
  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold font-outfit text-center bg-gradient-to-r from-sky-400 to-blue-500 bg-clip-text text-transparent mb-6">
        Chain Champions — Daily Update
      </h1>

      {/* Current Levels */}
      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-sky-500 border border-[var(--border-primary)]">
        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)]">Current Levels</h2>
        <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 list-disc ml-5 text-[var(--text-secondary)]">
          <li>Daily Open</li>
          <li>Weekly Open</li>
          <li>Monthly Open</li>
          <li>Daily Support</li>
          <li>Daily Resistance</li>
          <li>Weekly Support</li>
          <li>Weekly Resistance</li>
          <li>Global CC Support</li>
          <li>Global CC Resistance</li>
          <li>Local CC Support</li>
          <li>Local CC Resistance</li>
        </ul>
      </section>

      {/* Nearest POCs */}
      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-emerald-500 border border-[var(--border-primary)]">
        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)]">Nearest POCs</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Downside</h3>
            <ul className="list-disc ml-5 text-[var(--text-secondary)]">
              <li>Daily</li>
              <li>Weekly</li>
              <li>Monthly</li>
              <li>NSPOC ?</li>
            </ul>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Upside</h3>
            <ul className="list-disc ml-5 text-[var(--text-secondary)]">
              <li>Daily</li>
              <li>Weekly</li>
              <li>Monthly</li>
              <li>NSPOC ?</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Market Info */}
      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-purple-500 border border-[var(--border-primary)]">
        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)]">Market Info</h2>
        <ul className="list-disc ml-5 text-[var(--text-secondary)]">
          <li>Current Price</li>
          <li>Session VWAP</li>
          <li>Funding %</li>
          <li>15m CVD Divergences</li>
        </ul>
      </section>

      {/* Previous Day Levels */}
      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-amber-500 border border-[var(--border-primary)]">
        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)]">Previous Day Levels</h2>
        <ul className="grid grid-cols-2 sm:grid-cols-3 gap-4 list-disc ml-5 text-[var(--text-secondary)]">
          <li>High</li>
          <li>VAH</li>
          <li>POC</li>
          <li>EQ</li>
          <li>VAL</li>
          <li>LOW</li>
        </ul>
      </section>

      {/* Previous Month Levels */}
      <section className="bg-[var(--bg-secondary)]/50 backdrop-blur-md shadow-lg rounded-xl p-6 space-y-4 border-l-4 border-rose-500 border border-[var(--border-primary)]">
        <h2 className="text-xl font-semibold font-outfit text-[var(--text-primary)]">Previous Month Levels</h2>
        <ul className="grid grid-cols-2 sm:grid-cols-3 gap-4 list-disc ml-5 text-[var(--text-secondary)]">
          <li>High</li>
          <li>VAH</li>
          <li>POC</li>
          <li>EQ</li>
          <li>VAL</li>
          <li>LOW</li>
        </ul>
      </section>
    </div>
  );
};

export default ChainChampionsDailyUpdate;
