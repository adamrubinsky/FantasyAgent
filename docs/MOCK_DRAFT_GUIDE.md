# Mock Draft Testing Guide

## How to Test with Sleeper Mock Drafts

The Fantasy Football Draft Assistant works seamlessly with Sleeper mock drafts! Here's how to test:

### Step 1: Create a Mock Draft in Sleeper

1. **Go to Sleeper App/Website**
   - Navigate to "Mock Drafts" section
   - Create a new mock draft with your desired settings:
     - **League Type**: Superflex (recommended for testing)
     - **Scoring**: Half PPR 
     - **Team Count**: 12 teams
     - **Draft Position**: Any position you want to test

2. **Join the Mock Draft**
   - Sleeper will give you a draft room URL
   - The URL contains the draft ID (looks like: `drafts/123456789012345678`)

### Step 2: Get the Draft ID

Extract the draft ID from the URL or draft room. It's an 18-digit number.

Example:
- Draft URL: `https://sleeper.app/draft/nfl/123456789012345678`
- Draft ID: `123456789012345678`

### Step 3: Run the Draft Assistant

```bash
# Option 1: Run with specific draft ID
python main.py --draft-id 123456789012345678

# Option 2: Update .env.local with mock draft ID
SLEEPER_MOCK_DRAFT_ID=123456789012345678
python main.py --use-mock
```

### Step 4: Test Features

During the mock draft, you can test:

1. **Real-time Draft Monitoring**
   - Assistant polls every 5 seconds
   - Shows picks as they happen
   - Updates available players

2. **AI Recommendations**
   - Get pick suggestions based on:
     - Current roster needs
     - ADP value analysis
     - Tier breaks
     - Superflex strategy

3. **Pre-computation Engine**
   - When you're 3 picks away, the system pre-analyzes
   - Instant recommendations when it's your turn

4. **Natural Language Queries**
   - "Who should I draft?"
   - "Compare Josh Allen vs Lamar Jackson"
   - "Show me best available RBs"
   - "What's my roster need?"

### Mock Draft Best Practices

1. **Test Different Scenarios**:
   - Early picks (1-4): Test elite player decisions
   - Middle picks (5-8): Test value vs need balance
   - Late picks (9-12): Test reaching for positions

2. **Test Edge Cases**:
   - Let timer run low to test pre-computation
   - Draft from different positions
   - Test with autopick on/off

3. **Performance Testing**:
   - Monitor response times
   - Check caching effectiveness
   - Verify fallback systems work

### Limitations

- Mock drafts may have shorter timers than real drafts
- Other mock drafters might autopick or leave
- Mock draft data doesn't persist long-term

### Troubleshooting

If the assistant can't connect to your mock draft:

1. **Verify Draft ID**: Ensure you have the correct 18-digit ID
2. **Check Draft Status**: Draft must be "drafting" status, not "complete"
3. **Permissions**: Mock drafts are public, so no auth issues
4. **Try Fresh Mock**: Old mock drafts may be cleaned up by Sleeper

## Example Test Session

```bash
# 1. Create mock draft in Sleeper app
# 2. Get draft ID: 987654321098765432
# 3. Run assistant
python main.py --draft-id 987654321098765432

# Assistant output:
🏈 Fantasy Football Draft Assistant Started!
📊 Monitoring draft: 987654321098765432
👤 You are pick #7
⏱️  Your turn! Current pick: 7

🤖 AI Recommendation:
RECOMMENDED: Justin Jefferson (WR) - Elite WR1, great value at pick 7

Available commands:
- "help" - Show all commands
- "who should I draft?" - Get AI recommendation
- "show qb" - Show available QBs
- "compare [player1] vs [player2]" - Compare players
```