# 🚀 Fantasy Football Draft Assistant - Setup Guide

## Quick Setup for Testing

### 1. Clone & Install
```bash
git clone https://github.com/adamrubinsky/FantasyAgent.git
cd FantasyAgent
pip3 install --user python-dotenv aiohttp click rich
```

### 2. Configure Your Credentials
```bash
# Copy the example file
cp .env.example .env.local

# Edit .env.local with your actual Sleeper info:
# SLEEPER_USERNAME=your-username
# SLEEPER_LEAGUE_ID=your-league-id
```

### 3. Test Everything
```bash
# Test API connection
python3 main.py test

# View your league
python3 main.py league

# See available QBs (critical for SUPERFLEX!)
python3 main.py available -p QB -l 10
```

## How Credentials Work

The app automatically loads credentials in this order:
1. **`.env.local`** - Your real credentials (local only, not in Git)
2. **`.env`** - Placeholder file (safe for public GitHub)

This means:
- ✅ Your real data works locally
- ✅ Public repo stays secure
- ✅ No credential management needed

## Available Commands

```bash
python3 main.py test                    # Test connections
python3 main.py league                  # League details
python3 main.py available               # All players (top 20)
python3 main.py available -p QB -l 10   # Top 10 QBs
python3 main.py available -p RB -l 15   # Top 15 RBs
python3 main.py available -p WR -l 20   # Top 20 WRs
python3 main.py available -p TE -l 5    # Top 5 TEs
```

## Getting Your Sleeper Info

1. **Username**: Your Sleeper app username
2. **League ID**: Found in your league URL:
   - Go to your league in Sleeper app/web
   - Copy the long number from the URL
   - Example: `https://sleeper.app/leagues/1234567890123456789`
   - League ID is: `1234567890123456789`

## Troubleshooting

**"Please set SLEEPER_USERNAME..."**
- Make sure `.env.local` exists with your real credentials

**"python: command not found"**
- Use `python3` instead of `python`

**"No module named 'aiohttp'"**
- Run: `pip3 install --user python-dotenv aiohttp click rich`

**SSL certificate errors**
- This is handled automatically for macOS development

## What You Should See

✅ **Successful test**: Shows your league name and player count  
✅ **SUPERFLEX detection**: Should show "SUPERFLEX League: YES"  
✅ **High QB ranks**: Josh Allen = rank 2, Lamar Jackson = rank 3  
✅ **Fast responses**: All commands should be <1 second