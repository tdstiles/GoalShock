## 2025-02-14 - Stoppage Time Ignored in Late Compression
**Bug:** `AlphaTwoLateCompression` marked markets as "resolved" and stopped trading when `minute >= 90`, ignoring stoppage time.
**Cause:** `seconds_remaining` calculation used `max(0, (90 - minute) * 60)`, forcing 0 seconds for any minute >= 90.
**Fix:** Modified `feed_live_fixture_update` to assign 60 seconds of remaining time if `seconds_remaining <= 0` but status is still active (e.g. "2H"), keeping the market open during critical stoppage time.
