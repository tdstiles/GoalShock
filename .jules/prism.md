## 2024-05-22 - Market Probability Bars
**Clutter:** Markets displayed YES/NO prices as raw text ($0.75 / $0.25), requiring users to mentally visualize the spread.
**Clarity:** Added a horizontal Probability Bar (Green/Red split) to instantly show market sentiment.
**Principle:** "Show, Don't Just Tell" - Visual weight (bar width) is faster to process than numerical comparison.

## 2026-01-20 - Enhanced Probability Bars
**Clutter:** The probability bar was too thin (6px) and relied on a native `title` attribute for tooltips, which is invisible on mobile and poor on desktop.
**Clarity:** Increased bar height, added a "No Data" state, and implemented a custom interactive tooltip showing exact percentages.
**Principle:** "Data density should match interaction depth" - Hovering reveals precise data that doesn't need to clutter the main view.
