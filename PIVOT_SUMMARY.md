# Strategy Pivot: Sentiment-Enhanced Trading Bot

## What Changed

### Before: Pure Arbitrage
- Signal: Polymarket (polling)
- Execution: ForecastEx only
- Strategy: Price discrepancy arbitrage
- Entry: Required IBKR + ForecastEx access

### After: Sentiment-Enhanced Signal Trading
- **Signal**: Polymarket (WebSocket streaming) + **Sentiment Analysis**
- **Execution**: ForecastEx (primary) + potentially other venues
- **Strategy**: Confidence-boosted trading using market sentiment
- **Entry**: Lower barrier - can start with just Polymarket analysis

## New Architecture

### Layer 1: Polymarket Signal Engine (Enhanced)
- ✅ Already have: Gamma API + CLOB
- 🆕 Adding: WebSocket streaming for real-time updates
- 🆕 Adding: VWAP calculation from streaming order book

### Layer 2: Sentiment & Confidence Layer (NEW)
- 🆕 News API integration (NewsAPI, Alpha Vantage)
- 🆕 FinBERT sentiment scoring
- 🆕 Confidence boost: `confidence = polymarket_prob × (1 + sentiment_score)`
- 🆕 Event matching: "CPI" news → CPI markets

### Layer 3: Execution Engine (Enhanced)
- ✅ Already have: IBKR connection, yield adjustment
- 🆕 Adding: Sentiment-based trade filtering
- 🆕 Adding: Confidence threshold (not just spread threshold)

## Benefits of New Approach

### 1. Lower Entry Point
**Before**: Required approved IBKR account + ForecastEx access
**After**: Can start analysis-only mode without broker

### 2. More Signals
**Before**: Only price discrepancies
**After**: Price + sentiment alignment

### 3. Better Edge
**Before**: Pure arbitrage (efficient markets)
**After**: Information advantage (sentiment before price)

### 4. Automatable
**Before**: Manual contract mapping needed
**After**: Event detection from news headlines

## Implementation Plan

### Phase 1: Add Sentiment Layer (This Week)
1. ✅ Integrate NewsAPI
2. ✅ Add FinBERT sentiment model
3. ✅ Create confidence scoring system
4. ✅ Build event matching logic

### Phase 2: Add Real-Time Streaming (Next Week)
1. ✅ WebSocket connection to Polymarket CLOB
2. ✅ Streaming VWAP calculation
3. ✅ Real-time signal updates

### Phase 3: Unified Orchestration (Week 3)
1. ✅ Create main_bot.py orchestrator
2. ✅ Run all layers in parallel (asyncio)
3. ✅ Unified logging and monitoring

### Phase 4: Testing & Validation (Week 4)
1. Test sentiment accuracy
2. Backtest confidence-boosted signals
3. Paper trade with new system

## What We Keep From Before

- ✅ Yield adjustment formula (still correct)
- ✅ Paper trading ledger
- ✅ IBKR integration (optional now)
- ✅ Safety controls
- ✅ All tests and validation

## New Use Cases

### Use Case 1: Analysis Only (No Broker Needed)
```python
# Run sentiment + Polymarket analysis
# No execution, just alerts
python main_bot.py --mode analysis-only
```

### Use Case 2: Paper Trading (Simulated Execution)
```python
# Full system but no real money
python main_bot.py --mode paper
```

### Use Case 3: Live Trading (Full System)
```python
# Real money on ForecastEx
python main_bot.py --mode live
```

## Sustainable Financial Pipeline

### How Sentiment Adds Value

**Scenario 1: CPI Report**
```
1. News: "CPI expected to rise above 3.5%"
2. Sentiment: +0.15 (bullish)
3. Polymarket: 48% probability
4. Confidence boost: 48% × 1.15 = 55.2%
5. ForecastEx: 49%
6. Trade: BUY (undervalued vs confidence-adjusted fair value)
```

**Scenario 2: Fed Decision**
```
1. News: "Fed signals rate cut coming"
2. Sentiment: +0.20 (very bullish)
3. Polymarket: 52%
4. Confidence boost: 52% × 1.20 = 62.4%
5. ForecastEx: 54%
6. Trade: BUY (strong conviction)
```

### Revenue Streams

**Stream 1: Sentiment-Driven Trades**
- Trade when sentiment aligns with Polymarket
- Higher win rate than pure arbitrage
- Target: 3-5% edge per trade

**Stream 2: Early Information Advantage**
- News breaks → Sentiment scores → Trade before market adjusts
- First-mover advantage
- Target: 5-10% edge on fast-moving events

**Stream 3: Contrarian Opportunities**
- Sentiment extremely negative, Polymarket oversold
- Buy the dip on quality events
- Target: 10-20% edge on reversals

## Next Steps

1. **This Session**: Build sentiment layer
2. **Test**: Run sentiment analysis on historical events
3. **Validate**: Compare sentiment-boosted signals vs actual outcomes
4. **Deploy**: Start in analysis-only mode

Ready to build the enhanced system?
