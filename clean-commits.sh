#!/bin/bash
# Script to clean Claude co-author credits from commit messages

# Get commit message
COMMIT_MSG=$(cat "$1")

# Remove Claude credits
CLEANED_MSG=$(echo "$COMMIT_MSG" | sed '/🤖 Generated with \[Claude Code\]/d' | sed '/Co-Authored-By: Claude/d' | sed '/^$/N;/^\n$/D')

# Write cleaned message back
echo "$CLEANED_MSG" > "$1"
