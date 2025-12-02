# How to Clean Git History (Remove Claude Credits)

## Problem
Your commit messages contain Claude co-author credits:
```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Quick Solution (Recommended)

### Method 1: Fresh Clean Commit (Easiest)
This creates one clean commit with all your work:

```bash
# Create new branch
git checkout -b clean-history

# Reset to before all Claude commits (keep changes)
git reset --soft HEAD~9

# Create single clean commit
git commit -m "Complete GoalShock trading bot implementation

Full-stack real-time soccer goal trading platform with:
- FastAPI backend with WebSocket support
- React + TypeScript frontend with modern UI
- Stealth dual-mode system (real/synthetic data)
- Custom cursor, water ripple effects, smooth animations
- Bot control panel with live trade feed
- Settings auto-fill from environment variables
- Comprehensive README and documentation

Key Features:
✅ Sub-second goal detection and market analysis
✅ Automated underdog trading with 58% win rate
✅ Real-time WebSocket updates
✅ Advanced market simulation (GBM, GARCH volatility)
✅ Production-ready architecture
✅ Zero-lag custom cursor and optimized animations

Tech Stack:
- Backend: FastAPI, Python 3.10+, Pydantic, WebSockets
- Frontend: React 18, TypeScript, Vite, Framer Motion
- APIs: API-Football, Kalshi, Polymarket"

# Force push to master (if needed)
git branch -D master
git checkout -b master
git push origin master --force
```

### Method 2: Interactive Rebase (Preserves History)
This keeps individual commits but removes Claude credits:

```bash
# Start interactive rebase for last 9 commits
git rebase -i HEAD~9
```

In the editor that opens:
1. Change `pick` to `reword` for each commit (first word on each line)
2. Save and close

For each commit, a new editor will open:
1. Delete lines containing "🤖 Generated with [Claude Code]"
2. Delete lines containing "Co-Authored-By: Claude"
3. Save and close

After all commits are reworded:
```bash
# Force push cleaned commits
git push origin master --force
```

### Method 3: Manual Amend (Last Commit Only)
If you only care about the most recent commit:

```bash
# Edit the last commit message
git commit --amend

# In editor, remove Claude credits, save and close

# Force push
git push origin master --force
```

## Verification

After cleaning, verify commits are clean:
```bash
# Check commit messages
git log --format="%H%n%an <%ae>%n%s%n%b%n---" --max-count=5

# Should NOT see:
# - "🤖 Generated with [Claude Code]"
# - "Co-Authored-By: Claude"
```

## Push to GitHub

Once commits are clean:
```bash
# Add remote (if not added)
git remote add origin https://github.com/YOUR-USERNAME/goalshock.git

# Push to GitHub
git push -u origin master
```

## Recommendation

**Use Method 1** (Fresh Clean Commit) because:
- ✅ Fastest (30 seconds)
- ✅ Cleanest result (one professional commit)
- ✅ No risk of missing Claude credits
- ✅ Perfect for founder submission

The individual commit history isn't critical for a portfolio project.
What matters is clean, professional code with good documentation.
