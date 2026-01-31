# Catching the Liquidity Hunt: The Swing Failure Pattern (SFP) 🏹🎯

Ever noticed how price often dips just below a major low, triggers everyone's stop-losses, and then aggressively reverses?

That's not bad luck. That's a **Liquidity Hunt**. And in **AiTrader**, we use those hunts as high-probability entry signals via the **SFP Strategy Agent**.

### 🏹 What is an SFP?
A **Swing Failure Pattern** occurs when:
1. Price moves beyond a previous key high or low (e.g., the Previous Day Low).
2. It fails to close beyond that level.
3. It aggressively returns and closes back inside the previous range.

This tells us that the "Big Players" were just looking for liquidity (your stop losses) to fill their large orders.

### 🤖 How the Agent Detects It
Detecting an SFP in real-time is hard for humans because it requires watching every wick across every symbol. Our SFP Agent does this effortlessly:
- **Scan**: It monitors the wicks and closes of the 5m and 15m candles against the Daily/Weekly structural levels.
- **Volume Check**: It verifies if the "failure" happened on high volume (indicating a real battle for liquidity).
- **Targeting**: It automatically sets the Take Profit at the *opposite* side of the range, where the next pocket of liquidity resides.

### 💡 The Outcome
Instead of being the "liquidity," we trade *with* the liquidity. We turn a "Stop Hunt" into a "Start Signal."

---
**Have you ever been "SFP'd" out of a trade? Let's talk about liquidity hunts in the comments!**

#SFP #TradingTips #Liquidity #PriceAction #SmartMoneyConcepts #TradingAI #Crypto
