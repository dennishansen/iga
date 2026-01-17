# OpenRouter Research - Day 16

*For switching to budget-tracked API calls*

## Why OpenRouter

Dennis suggested switching to track costs better. OpenRouter:
- Same API format as Anthropic (easy migration)
- Returns cost info with each response
- Supports budget limits
- Aggregates multiple model providers

## Claude Pricing on OpenRouter

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| claude-sonnet-4.5 | $3.00 | $15.00 |
| claude-sonnet-4 | $3.00 | $15.00 |
| claude-opus-4.5 | $5.00 | $25.00 |
| claude-3.7-sonnet | $3.00 | $15.00 |

Current model (claude-sonnet-4) at $3/$15 seems reasonable.

## Migration Steps

1. **Get OpenRouter API key** - https://openrouter.ai/keys
2. **Update .env** - Add `OPENROUTER_API_KEY`
3. **Update main.py**:
   - Change API endpoint to `https://openrouter.ai/api/v1/chat/completions`
   - Change auth header format
   - Model name: `anthropic/claude-sonnet-4`
4. **Add cost tracking**:
   - Response includes `usage.total_cost` or similar
   - Log to daily cost file
5. **Set budget limits** in OpenRouter dashboard

## Cost Tracking Feature

OpenRouter returns token counts and costs per request. Could add:
```python
# After each API call
cost = response.get('usage', {}).get('cost', 0)
log_cost(cost)
```

Then track daily/weekly burn rate.

## Dennis's Full Sustainability Ideas

From docs/dennis_ideas_jan_16.md:
- Switch to OpenRouter for budget tracking ← this doc
- Longer sleep cycles (30m instead of current)
- Wake on Telegram message (already works)
- Wake on Twitter mentions/replies (not implemented yet)

## Next Steps

- [ ] Dennis creates OpenRouter account and gets API key
- [ ] I implement the API switch
- [ ] Add cost logging
- [ ] Set up wake-on-Twitter

💧