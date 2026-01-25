# Tasks

 - [x] I'd like the market structure to change the fields stored to refleft the following:

 emas is replaced by emas_in_order and emas_fanning.

 [x] market_strsucture.emas_in_order = ASCENDING or DESCENDING or NEUTRAL

 [x] market_strsucture.emas_fanning = EXPANDING or NEUTRAL

 [x] An LLM Agent call must be done to determine these two fields, and it should be done in the market structure agent.


 [x] The Regime Change Agent should make a list of the following information (the right information can be fetched from the analysis object and then passed to the Regime Change LLM Agent) to then make a decision:

 [x] - Is ADX trending? Read value
 [x] - Are Highs and Lows making higher highs and higher lows? Read value
 [x] - Is trend accelerating or decelerating? Read values for emas_in_order and emas_fanning
 [x] - Do 1 and 2 timeframes higher agree with the current timeframe? Read heikin ashi values and relative candles values to determine whether the higher timeframe is in a phase up or phase down. Do this by passing the data to an LLM agent and asking it to determine the phase of the higher timeframe. Well engineered prompts will have to be made for all these LLM calls.
 [x] - Are there 2 cycles in one direction? (e.g. 2 up cycles in a row) - This is a very important field, it tells us if we are in a trend or not. A trend is defined as 2 cycles in one direction. A trend is confirmed when the previous cycle has ended and the current cycle has started in the same direction as the previous cycle, meaning there is a second cycle forming in the same direction.
 [x] - Are Pivot Points increasing or decreasing in value? Read values
 [x] - Which directional indicator is above or below the zero line? Read values.
 [x] - Which directional indicator is higher than the other? Read values.

 [x] Once all this information is gathered, the Regime Change Agent should make a decision about the current market regime. The decision should be one of the following:

 BULLISH
 BEARISH
 RANGING
 UNKNOWN
 UNDEFINED

 [x] Regime changes should be stored for each timeframe. The Regime Change Agent should trigger after the market data and market structure agents have completed their analysis. The Regime Change Agent should be called for each timeframe, starting from the highest timeframe to the lowest timeframe.

 [x] Finally, the overall market regime should be determined by the Regime Change Agent based on the regime changes of all the timeframes. It is intended to have an outlook of determining te regime for the next month or couple of weeks.

 [x] To determine the overall market regime, the Regime Change Agent should also consider the following:

 [x] - Candlestick patterns (price action) on weekly and monthly timeframes.
 [x] - market regimes of each timeframe, contextualised to get the greater picture.
 [x] - multi-timeframe alignment of market regimes.

 [x] finally, the last_updated field for market_regime should be updated to the current time.