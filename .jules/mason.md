## 2024-05-24 - Magic Numbers in Core Strategy Logic
**Anti-Pattern:** Hardcoded magic numbers (e.g., `5400`, `2.7`, `0.98`) buried deep within conditional logic in strategy classes like `AlphaTwoLateCompression`. This makes the code hard to read, hard to tune, and prone to errors when parameters need to be adjusted.
**Improvement:** Extracted these numbers into named constants (e.g., `SOCCER_GAME_DURATION_SECONDS`, `CONFIDENCE_VERY_HIGH`) and moved specific logic (soccer confidence calculation) into a dedicated helper method `_calculate_soccer_confidence`.
**Guideline:** Core strategy parameters must always be defined as named constants to clarify the mathematical model being used.

## 2025-02-18 - Magic Numbers in Simulation Logic
**Anti-Pattern:** Hardcoded numeric literals (e.g., `0.5`, `0.001`, `0.99`) were scattered throughout the price simulation logic in `AlphaOneUnderdog`, making the random walk behavior opaque and difficult to tune.
**Improvement:** Extracted these values into semantic constants (e.g., `SIM_ANNUAL_VOLATILITY`, `SIM_DRIFT_FACTOR`, `SIM_PRICE_CEILING`) grouped at the module level.
**Guideline:** Simulation parameters and thresholds should be defined as named constants to clarify the mathematical model being used.

## 2025-02-19 - Local Imports and Mixed Responsibilities
**Anti-Pattern:** Found `import random` inside a method (`_simulate_price_movement`) and simulation logic mixed with state updates. Also found local imports in `OrchestrationEngine` masking dependencies.
**Improvement:** Moved imports to module level. Extracted clean logic flow.
**Guideline:** Imports should always be at the top of the file to make dependencies explicit.

## 2026-01-27 - Magic Strings in Market Status and Outcomes
**Anti-Pattern:** Hardcoded string literals (e.g., `"resolved"`, `"active"`, `"YES"`, `"NO"`) were used throughout `AlphaTwoLateCompression`, increasing the risk of typos and making refactoring difficult.
**Improvement:** Introduced `MarketSide` Enum and enforced usage of existing `MarketStatus` Enum. Replaced all literals with Enum members.
**Guideline:** Use Enums for fixed sets of string values (like status or outcome sides) to ensure type safety and centralized definition.

## 2026-05-15 - Duplicated Async Polling Logic
**Anti-Pattern:** Identical "place order and loop to verify fill" logic was copy-pasted across multiple strategy classes (`AlphaOneUnderdog`, `AlphaTwoLateCompression`), leading to code duplication and potential for divergent behavior.
**Improvement:** Extracted the logic into a reusable `place_order_and_wait_for_fill` method within the `PolymarketClient` class.
**Guideline:** Complex async workflows (like order verification) that are shared across consumers should be encapsulated in the client/provider class rather than repeated in every consumer.

## 2026-05-16 - Duplicated Event Logging
**Anti-Pattern:** Repeated identical event logging logic (`event_log` list, `_log_event`, `export_event_log`) duplicated across multiple alpha strategy classes (`AlphaOneUnderdog`, `AlphaTwoLateCompression`).
**Improvement:** Abstracted the shared logging logic into a `BaseAlpha` utility class which the strategies now inherit from, reducing code duplication.
**Guideline:** Repeated operational logic across similar classes should be extracted into shared base classes or utility mixins to improve maintainability and ensure consistency.

## 2026-06-12 - Pydantic V2 Deprecated `.dict()`
**Anti-Pattern:** Use of Pydantic's deprecated `.dict()` method on models throughout endpoints (e.g., `match.dict()`). This raises noisy deprecation warnings (`PydanticDeprecatedSince20`) and creates technical debt for future version upgrades.
**Improvement:** Replaced all instances of `.dict()` with the modern `.model_dump()` method.
**Guideline:** Always use `.model_dump()` instead of `.dict()` for Pydantic V2+ models to ensure compatibility and maintain warning-free logs.

## 2024-05-24 - Magic Numbers in Frontend App Components
**Anti-Pattern:** Hardcoded magic numbers (e.g., `100`, `1000`, `2`, `20`) were buried within the frontend `SplashScreen` component's `useEffect` hook in `app/src/App.tsx`. This made the animation logic opaque and difficult to configure without digging into the component internals.
**Improvement:** Extracted these magic numbers into descriptive, semantic constants (`SPLASH_PROGRESS_TARGET`, `SPLASH_COMPLETION_DELAY_MS`, `SPLASH_PROGRESS_INCREMENT`, `SPLASH_PROGRESS_INTERVAL_MS`) defined at the module scope.
**Guideline:** Configuration values governing UI timings, limits, and step sizes must be extracted into named constants to improve maintainability and self-document the code's intent.
