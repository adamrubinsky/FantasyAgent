# Yahoo Fantasy OAuth Setup Instructions

## Overview
This is a **one-time setup** to connect to your Yahoo Fantasy leagues. Once completed, the token will be saved and automatically refresh for months.

---

## Step-by-Step Terminal Instructions

### Step 1: Open Terminal
Navigate to your FantasyAgent directory:
```bash
cd /Users/adamrubinsky/VSCode/FantasyAgent
```

### Step 2: Start Python Interactive Session
```bash
python3
```

### Step 3: Copy and Paste This Code Block
Copy this ENTIRE block and paste it into Python:
```python
from yfpy.query import YahooFantasySportsQuery
import os
from dotenv import load_dotenv

# Load your credentials
load_dotenv('.env.local')

# Initialize Yahoo connection
yahoo = YahooFantasySportsQuery(
    league_id='475629',
    game_code='nfl',
    game_id=449,
    yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
    yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET'),
    browser_callback=True
)
```

### Step 4: Browser Will Open
- Your browser will automatically open to Yahoo
- Log in if needed
- Click "Agree" to authorize FantasyAgent
- You'll see an SSL error page - **THIS IS NORMAL!**

### Step 5: Copy the URL
From your browser's address bar, copy the ENTIRE URL. It will look like:
```
https://localhost:3000/auth/yahoo/callback?code=XXXXXXXXXX
```

### Step 6: Paste the URL
- Go back to your terminal
- You should see a prompt asking for the URL
- Paste the URL you copied and press Enter

### Step 7: Verify Success
If successful, you'll see:
```
Enter the URL: [paste here]
Token saved successfully!
```

### Step 8: Exit Python
```python
exit()
```

---

## Test Your Connection

After completing OAuth, test it works:

```bash
python3 -c "
from yfpy.query import YahooFantasySportsQuery
import os
from dotenv import load_dotenv
load_dotenv('.env.local')

yahoo = YahooFantasySportsQuery(
    league_id='475629',
    game_code='nfl',
    game_id=449,
    yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
    yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET')
)

settings = yahoo.get_league_settings()
print(f'✅ Connected to: {settings.name}')
print(f'   Teams: {settings.num_teams}')
print(f'   Draft Status: {settings.draft_status}')
"
```

---

## Troubleshooting

### If the browser doesn't open automatically:
Open this URL manually in your browser:
```
https://api.login.yahoo.com/oauth2/request_auth?client_id=dj0yJmk9TE40dEtIRWxrb0hNJmQ9WVdrOU5WRnpZWEpwUkZFbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PWRm&redirect_uri=https://localhost:3000/auth/yahoo/callback&response_type=code&language=en-us
```

### If you get an error:
1. Make sure you copied the ENTIRE URL including `?code=...`
2. Try deleting any existing token files and retry:
   ```bash
   rm -rf private/
   rm -f token.json
   rm -f yahoo_token.json
   ```
3. Make sure your .env.local has the correct Yahoo credentials

### If you need to redo OAuth:
```bash
# Delete saved tokens
rm -rf private/
rm -f *.json

# Start over from Step 2
```

---

## Token Persistence

Once OAuth is complete:
- **Access Token**: Valid for ~1 hour (auto-refreshes)
- **Refresh Token**: Valid for ~6 months
- **Storage**: Saved in `private/` directory
- **Automatic**: All future API calls use the saved token

You won't need to do this again unless:
- You delete the token files
- The refresh token expires (after 6 months)
- You revoke access on Yahoo's website

---

## Your League Information

### Snake Draft League (Aug 19)
- **League ID**: 475629
- **Team**: #5
- **Scoring**: FULL PPR
- **URL**: https://football.fantasysports.yahoo.com/f1/475629/5

### Auction League (Aug 24)
- **League ID**: 682492
- **Team**: #2
- **Scoring**: Half-PPR
- **Budget**: $200
- **URL**: https://football.fantasysports.yahoo.com/f1/682492/2

---

## Quick Test After Setup

Once OAuth is complete, you can test both leagues:

```bash
# Test Snake League
python3 -c "
from yfpy.query import YahooFantasySportsQuery
import os
from dotenv import load_dotenv
load_dotenv('.env.local')

yahoo = YahooFantasySportsQuery(
    league_id='475629',
    game_code='nfl',
    game_id=449,
    yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
    yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET')
)
print('✅ Snake League Connected!')
"

# Test Auction League  
python3 -c "
from yfpy.query import YahooFantasySportsQuery
import os
from dotenv import load_dotenv
load_dotenv('.env.local')

yahoo = YahooFantasySportsQuery(
    league_id='682492',
    game_code='nfl',
    game_id=449,
    yahoo_consumer_key=os.getenv('YAHOO_CLIENT_ID'),
    yahoo_consumer_secret=os.getenv('YAHOO_CLIENT_SECRET')
)
print('✅ Auction League Connected!')
"
```

---

*Last Updated: August 11, 2025*