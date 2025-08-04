#!/bin/bash

echo "🔧 Fixing deployment issues..."

# Check if we're in a git repository
if [[ -d .git ]]; then
    echo "📦 Git repository detected"
    
    # Check for uncommitted changes
    if [[ -n $(git status --porcelain) ]]; then
        echo "⚠️  Found uncommitted changes. Stashing them..."
        git stash push -m "Auto-stash before deployment fix"
    fi
    
    # Try to pull updates
    echo "🔄 Pulling latest changes..."
    git pull
    
    # If there are still conflicts, reset to remote
    if [[ $? -ne 0 ]]; then
        echo "⚠️  Git pull failed. Resetting to remote version..."
        git fetch origin
        git reset --hard origin/main
    fi
else
    echo "ℹ️  Not a git repository, skipping git operations"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if [[ -f requirements.txt ]]; then
    pip3 install -U --prefix .local -r requirements.txt
else
    echo "⚠️  requirements.txt not found"
fi

# Install specific packages if needed
echo "📦 Installing core dependencies..."
pip3 install -U --prefix .local discord.py requests better-profanity

echo "✅ Deployment fix completed!"
echo "🚀 Starting bot..."
python3 regex.py 