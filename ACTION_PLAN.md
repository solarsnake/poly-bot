# Action Plan: From Code to Down Payment

## Executive Summary

**Goal**: $150k down payment for house in Poway, CA

**Strategy**: Capture yield-adjusted arbitrage between Polymarket (signal) and ForecastEx (execution)

**Current Status**:
- ✅ Code complete and tested (28/28 tests passing)
- ✅ Yield calculation verified and calibrated for 2026 rates
- ⬜ IBKR account setup (next step)
- ⬜ Contract mapping (the "boring plumbing")
- ⬜ Paper trading validation

**Analyst Assessment**: ✅ Plan is sound - move to sophisticated participant tier

## Phase 1: Digital Twin (Current - Week 2)

**Status**: ✅ **COMPLETE**

What we built:
- ✅ Read-only Polymarket signal collection
- ✅ Yield-adjusted fair value calculator
- ✅ Arbitrage detection engine
- ✅ Paper trading ledger
- ✅ Safety controls (no Polymarket execution)
- ✅ All tests passing (100% success rate)

**Key Achievement**:
The math is correct. Formula `P_FX = p_poly × (1 + r × t/365)` is properly calibrated for 2026 interest rates (4.5%).

## Phase 2: The Boring Plumbing (Week 3-4)

**Status**: ⬜ **IN PROGRESS**

### Critical Path Items:

#### Task 2.1: IBKR Account Setup ⏱️ 1-3 days
**Owner**: You
**Action**: Follow SETUP_IBKR.md step-by-step
**Success Criteria**:
- ✅ Account approved
- ✅ ForecastEx permission granted
- ✅ IB Gateway installed and running
- ✅ Connection test passes

**Deliverable**: Screenshot of successful connection test

---

#### Task 2.2: Contract Discovery ⏱️ 2-4 hours
**Owner**: You (with bot assistance)
**Action**:
```python
# Run contract discovery script
python scripts/discover_forecastex_contracts.py

# This will:
# 1. Connect to IBKR
# 2. Search for all ForecastEx contracts
# 3. Output to contracts_available.csv
```

**Success Criteria**:
- Find at least 5 active ForecastEx contracts
- Document: symbol, description, expiry, current price

**Deliverable**: `contracts_available.csv` with market data

---

#### Task 2.3: Polymarket Matching ⏱️ 1-2 hours
**Owner**: You
**Action**: For each ForecastEx contract, find matching Polymarket market

**Example:**
```
ForecastEx: "USCPI" - US CPI YoY above 3% by March 2026
Polymarket: condition_id "0xabc123..." - US CPI March 2026
```

**Success Criteria**:
- At least 3 matched pairs
- Both markets have >$10k liquidity

**Deliverable**: `market_mapping.csv` with pairs

---

#### Task 2.4: Update Bot Configuration ⏱️ 30 minutes
**Owner**: You
**Action**: Update `main_execution_bot.py` watchlist

```python
self.watchlist = [
    {
        "description": "US CPI YoY",
        "strike": 100.0,
        "expiry_date": "2026-03-15",
        "is_yes": True,
        "condition_id": "0xabc123...",  # From Polymarket
        "ibkr_symbol": "USCPI",         # From ForecastEx discovery
        "tags": ["Economics"]
    },
    # Add 2-4 more markets
]
```

**Success Criteria**:
- Bot can fetch Polymarket probability
- Bot can find ForecastEx contract
- Bot calculates spread correctly

**Deliverable**: Updated `main_execution_bot.py`

---

#### Task 2.5: Dry Run Test ⏱️ 15 minutes
**Owner**: You
**Action**:
```bash
# Run bot for 1 iteration (no trades)
python main_execution_bot.py --mode paper --max-iterations 1
```

**Success Criteria**:
- No errors
- Fetches Polymarket data
- Finds ForecastEx contracts
- Calculates spreads
- Logs to database

**Deliverable**: `data/trades.db` with at least 1 logged opportunity (even if below threshold)

---

### Phase 2 Success Criteria:

When Phase 2 is complete, you should be able to:
1. ✅ Connect to IBKR programmatically
2. ✅ Fetch ForecastEx contract prices
3. ✅ Fetch Polymarket probabilities
4. ✅ Calculate yield-adjusted spreads
5. ✅ Log opportunities (even if not executing)

**Next Decision Point**: Do spreads of 2-3% occur frequently enough?

## Phase 3: Paper Trading Validation (Week 5-8)

**Status**: ⬜ **WAITING**

### Objective: Validate Strategy Before Risking Capital

#### Task 3.1: Run Bot Continuously ⏱️ 30 days
**Owner**: Bot (monitored by you)
**Action**:
```bash
# Run in background, checking every 60 seconds
nohup python main_execution_bot.py --mode paper --polling-interval 60 > logs/bot.log 2>&1 &

# Or use systemd/launchd for proper daemon
```

**Monitoring**: Check daily
```bash
# View recent trades
python scripts/view_paper_trades.py --last 7d

# View PnL
python scripts/calculate_pnl.py
```

**Success Criteria**:
- Bot runs without crashes
- Finds 5-20 opportunities/week
- Average spread > 1.5%

---

#### Task 3.2: Analyze Results ⏱️ 2-4 hours/week
**Owner**: You
**Action**: Weekly analysis
```python
# Run analysis notebook
jupyter notebook analysis/weekly_review.ipynb
```

**Key Metrics to Track**:
1. **Opportunity Frequency**: Trades/week
2. **Average Spread**: Mean arb %
3. **Spread Distribution**: Histogram
4. **Win Rate**: % of positive outcomes (simulated)
5. **Max Drawdown**: Worst case scenario

**Decision Thresholds**:
- If frequency < 1/week → Strategy not viable
- If average spread < 1.0% → Adjust threshold
- If win rate < 60% → Review methodology

---

#### Task 3.3: Backtest Refinement ⏱️ Ongoing
**Owner**: You + Bot
**Action**: Tune parameters based on observations

**Parameters to Optimize**:
```python
arb_threshold = 0.02      # Start at 2%, adjust based on frequency
risk_free_rate = 0.045    # Update monthly with T-Bill rates
position_size = 10.0      # Start small, scale up
```

**Approach**:
```python
# Test multiple thresholds
for threshold in [0.01, 0.015, 0.02, 0.025, 0.03]:
    results = backtest_with_threshold(threshold)
    print(f"{threshold}: {results['trades_per_week']} trades, "
          f"{results['avg_spread']:.2%} spread")
```

**Goal**: Find optimal threshold that balances frequency × spread

---

### Phase 3 Success Criteria:

Before moving to live trading, verify:
1. ✅ Bot ran for 30 consecutive days without failures
2. ✅ Found 20+ opportunities (any spread)
3. ✅ Found 10+ opportunities above threshold
4. ✅ Paper PnL positive (accounting for fees)
5. ✅ Understand market patterns (time of day, volatility)

**Go/No-Go Decision**:
- If metrics look good → Proceed to Phase 4
- If insufficient opportunities → Revisit strategy or expand markets

## Phase 4: Small Capital Deployment (Month 3-4)

**Status**: ⬜ **FUTURE**

### Objective: Validate Execution with Real Money (But Small Size)

**Starting Capital**: $500 - $1,000

#### Task 4.1: Risk Management Setup ⏱️ 1 hour
**Owner**: You
**Action**: Set strict limits

```python
# In .env
MAX_POSITION_SIZE=50        # $50 per trade (1% of $5k)
MAX_DAILY_TRADES=2          # 2 trades max per day
MAX_TOTAL_EXPOSURE=500      # $500 max across all positions
STOP_LOSS_PERCENTAGE=0.10   # Stop bot if down 10%
```

**Success Criteria**: Bot respects all limits

---

#### Task 4.2: Enable Live Mode ⏱️ 30 minutes
**Owner**: You
**Action**:
1. Update `.env`: `ALLOW_US_EXECUTION=true`
2. IB Gateway: Disable Read-Only API
3. Switch to paper mode OFF (use live credentials)
4. Test with 1 small trade manually

```bash
# Run with confirmation
python main_execution_bot.py --mode live --max-iterations 1

# You'll get prompted: "Type 'YES' to confirm"
```

**Success Criteria**:
- First trade executes successfully
- Shows up in IBKR account
- Ledger records correctly

---

#### Task 4.3: Monitor Closely ⏱️ Daily, for 30 days
**Owner**: You
**Action**: Daily review

**Check Every Day**:
1. Bot status (still running?)
2. Open positions
3. Realized PnL
4. Unrealized PnL
5. Any errors/warnings

**Weekly Review**:
1. Win rate vs paper trading
2. Slippage (execution price vs expected)
3. Transaction costs (higher than expected?)
4. Market impact (are we moving prices?)

**Red Flags** (stop immediately if):
- Losing > 10% of capital
- Execution prices consistently worse than expected
- Unable to exit positions
- Bot making irrational trades

---

### Phase 4 Success Criteria:

After 30 days of small live trading:
1. ✅ Net positive PnL (after all fees)
2. ✅ No major execution issues
3. ✅ Win rate within 10% of paper trading
4. ✅ Slippage within acceptable range (<0.5%)
5. ✅ Confidence in bot's reliability

**Decision**: Scale up capital or refine further?

## Phase 5: Scale to Down Payment Goal (Month 5-24)

**Status**: ⬜ **FUTURE**

### Conservative Path: 2-3 Years to $150k

**Assumptions**:
- Starting capital: $5,000
- Average spread: 2%
- Trades/week: 5
- Win rate: 65%
- Compound returns

**Year 1 Projection**:
```
Weeks: 52
Trades: 260 (5/week)
Gross per trade: $5,000 × 2% = $100
Win rate: 65%
Expected per trade: $100 × 0.65 = $65
Annual gross: $65 × 260 = $16,900
After fees (10%): $15,210
Year 1 balance: $5,000 + $15,210 = $20,210
```

**Year 2 Projection** (compounding):
```
Starting: $20,210
Annual return: ~300% of capital
Year 2 balance: $80,840
```

**Year 3 Projection**:
```
Starting: $80,840
Reach $150k: Yes, likely by month 30-36
```

### Aggressive Path: 1-2 Years to $150k

**Assumptions**:
- Starting capital: $10,000
- Average spread: 3%
- Trades/week: 10
- Win rate: 70%

**This requires**:
- More capital
- Higher frequency
- Better spreads
- May not be realistic

### Capital Scaling Strategy

**DO NOT** scale linearly. Scale based on:

1. **Demonstrated Success**:
   - Milestone 1: $5k → $10k (double)
   - Milestone 2: $10k → $25k (2.5x)
   - Milestone 3: $25k → $60k (2.4x)
   - Milestone 4: $60k → $150k (2.5x)

2. **Market Capacity**:
   - If $10k positions move prices → Don't scale
   - If execution worsens → Don't scale
   - If spreads compress → Pause scaling

3. **Risk Management**:
   - Never more than 20% of capital in one position
   - Always maintain 2-3 months living expenses in separate account
   - Have stop-loss at every milestone

### Exit Scenarios

**Success**: Reached $150k
- ✅ Make down payment
- Continue running bot for mortgage payments?

**Partial Success**: Reached $50-100k
- Consider smaller house or wait longer
- Bot still valuable even if goal takes longer

**Failure**: Lost > 30% of capital
- Stop immediately
- Review what went wrong
- Decide: Fix and retry, or abandon strategy

## Timeline Summary

| Phase | Duration | Key Deliverable | Go/No-Go |
|-------|----------|-----------------|----------|
| **1. Digital Twin** | Week 1-2 | ✅ Code complete | ✅ DONE |
| **2. Plumbing** | Week 3-4 | Contract mapping | Spreads exist? |
| **3. Paper Trading** | Week 5-8 | 30-day validation | PnL positive? |
| **4. Small Live** | Month 3-4 | $500 proof | Execution good? |
| **5. Scale** | Month 5-24 | $150k goal | Market capacity? |

**Total Time**: 18-36 months to goal (depending on path)

## Risk Disclosure

**This is NOT a guaranteed path to $150k.**

**Risks**:
1. **Market Risk**: Spreads may not materialize
2. **Execution Risk**: Slippage, partial fills
3. **Regulatory Risk**: ForecastEx could shut down
4. **Competition Risk**: Others find same opportunities
5. **Technology Risk**: Bot failures, API changes
6. **Capital Risk**: You could lose money

**Mitigation**:
- Start small ($500-1,000)
- Validate thoroughly in paper mode
- Set strict stop-losses
- Diversify across multiple strategies
- Keep day job until proven

## Next Actions (This Week)

**Monday-Tuesday**:
1. ⬜ Submit IBKR account application (SETUP_IBKR.md)
2. ⬜ While waiting: Review YIELD_ANALYSIS.md

**Wednesday-Friday** (once IBKR approved):
3. ⬜ Install IB Gateway
4. ⬜ Run connection test
5. ⬜ Discover ForecastEx contracts
6. ⬜ Map to Polymarket events
7. ⬜ Run first dry-run test

**Weekend**:
8. ⬜ Review results
9. ⬜ Decide: Proceed to Phase 3 or refine Phase 2

## Questions to Answer Along the Way

**Phase 2 Questions**:
- Are there ForecastEx contracts available?
- Can we find Polymarket matches?
- Do spreads of 2%+ exist?

**Phase 3 Questions**:
- How often do opportunities occur?
- What's the actual win rate?
- Are transaction costs acceptable?

**Phase 4 Questions**:
- Does execution match paper trading?
- Is slippage a problem?
- Can we exit positions easily?

**Phase 5 Questions**:
- At what capital size do we hit limits?
- Do spreads compress as we scale?
- Is the goal achievable in our timeline?

---

**You are here**: End of Phase 1 ✅

**Next step**: Set up IBKR account (Phase 2, Task 2.1)

**Ready?** Open SETUP_IBKR.md and let's get the boring plumbing working! 🚀
