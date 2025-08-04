# Deployment Fix Instructions

## Issues Identified

The server was crashing due to two main issues:

1. **Git Merge Conflict**: Local changes to `regex.py` were preventing git pull from completing
2. **Missing Dependencies**: The `requests` module was not installed due to a typo in `requirements.txt`

## Solutions

### ✅ Fixed Issues

1. **requirements.txt**: Fixed typo from "request" to "requests"
2. **Dependencies**: All required packages are now properly listed

### 🔧 Manual Fix Steps

If the automatic fix doesn't work, follow these steps:

#### Step 1: Handle Git Conflicts
```bash
# Option A: Stash local changes and pull
git stash push -m "Auto-stash before deployment"
git pull

# Option B: Reset to remote version (WARNING: loses local changes)
git fetch origin
git reset --hard origin/main
```

#### Step 2: Install Dependencies
```bash
# Install all dependencies
pip3 install -U --prefix .local -r requirements.txt

# Or install individually if needed
pip3 install -U --prefix .local discord.py requests better-profanity
```

#### Step 3: Test Dependencies
```bash
# Run the test script
python3 test_dependencies.py
```

#### Step 4: Start the Bot
```bash
# Start the bot
python3 regex.py
```

### 🚀 Automatic Fix

Run the provided fix script:
```bash
chmod +x fix_deployment.sh
./fix_deployment.sh
```

## Environment Variables

Make sure the `MY_SECRET_TOKEN` environment variable is set with your Discord bot token.

## File Structure

```
Cygex Bot/
├── regex.py              # Main bot file
├── requirements.txt      # Python dependencies
├── profanity.json       # Custom profanity patterns
├── fix_deployment.sh    # Automatic fix script
├── test_dependencies.py # Dependency test script
└── DEPLOYMENT_FIX.md   # This file
```

## Troubleshooting

### If dependencies still fail:
1. Check Python version: `python3 --version`
2. Check pip version: `pip3 --version`
3. Try installing with `--user` flag: `pip3 install --user -r requirements.txt`

### If git issues persist:
1. Check git status: `git status`
2. View conflicts: `git diff`
3. Reset completely: `git reset --hard HEAD`

### If bot still crashes:
1. Check logs for specific error messages
2. Verify environment variables are set
3. Test with the dependency checker script 