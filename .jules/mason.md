## 2024-05-24 - Magic Numbers in Core Strategy Logic
**Anti-Pattern:** Hardcoded magic numbers (e.g., `5400`, `2.7`, `0.98`) buried deep within conditional logic in strategy classes like `AlphaTwoLateCompression`. This makes the code hard to read, hard to tune, and prone to errors when parameters need to be adjusted.
**Improvement:** Extracted these numbers into named constants (e.g., `SOCCER_GAME_DURATION_SECONDS`, `CONFIDENCE_VERY_HIGH`) and moved specific logic (soccer confidence calculation) into a dedicated helper method `_calculate_soccer_confidence`.
**Guideline:** Core strategy parameters must always be defined as named constants at the top of the file or in a configuration object to ensure visibility and maintainability.
