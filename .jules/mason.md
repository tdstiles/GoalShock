## 2024-05-24 - Magic Numbers in Core Strategy Logic
**Anti-Pattern:** Hardcoded magic numbers (e.g., `5400`, `2.7`, `0.98`) buried deep within conditional logic in strategy classes like `AlphaTwoLateCompression`. This makes the code hard to read, hard to tune, and prone to errors when parameters need to be adjusted.
**Improvement:** Extracted these numbers into named constants (e.g., `SOCCER_GAME_DURATION_SECONDS`, `CONFIDENCE_VERY_HIGH`) and moved specific logic (soccer confidence calculation) into a dedicated helper method `_calculate_soccer_confidence`.
**Guideline:** Core strategy parameters must always be defined as named constants at the top of the file or in a configuration object to ensure visibility and maintainability.

## 2025-02-18 - Magic Numbers in Simulation Logic
**Anti-Pattern:** Hardcoded numeric literals (e.g., `0.5`, `0.001`, `0.99`) were scattered throughout the price simulation logic in `AlphaOneUnderdog`, making the random walk behavior opaque and difficult to tune.
**Improvement:** Extracted these values into semantic constants (e.g., `SIM_ANNUAL_VOLATILITY`, `SIM_DRIFT_FACTOR`, `SIM_PRICE_CEILING`) grouped at the module level.
**Guideline:** Simulation parameters and thresholds should be defined as named constants to clarify the mathematical model being used.
