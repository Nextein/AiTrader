# Tasks

The list of symbols should not be predefined. Instead, it should be fetched from the exchange. Then, the symbols should be filtered to only include USDT perpetual contracts, if they are not filtered already (I believe there is an API endpoint only for USDT perpetual contracts, but I might be wrong).

The top 10 symbols should be analysed first, and then the rest should be analysed in a random order.

The first thing that should happen for each symbol is a check to see whether the symbol is an actual cryptocurrency coin or token or if it's some weird derivative like BTCUP-USDT or 1000PEPE-USDT or something similar.

To do so, the Governor Agent should call the Sanity Agent with the symbol as a parameter. The Sanity Agent should return a boolean value indicating whether the symbol is a valid cryptocurrency coin or token or not. To do so it should simply ask the LLM via langchain if the symbol is a valid cryptocurrency coin or token or not. This question should be wrapped in a prompt with maxed out prompt engineering and best practices to ensure a correct answer every time. The LLM available is running locally on ollama. It is phi3:mini, and it is available on my windows laptop via ollama in the usual port.

Only if the Sanity Agent returns true should the analysis object for that symbol be created. If it returns false, the symbol should be skipped.