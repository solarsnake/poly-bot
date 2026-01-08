# Interactive Brokers Setup Guide

## Overview

This guide walks you through setting up Interactive Brokers (IBKR) for ForecastEx trading.

**Goal**: Get the "boring plumbing" working so you can test real contract mapping.

## Why IBKR?

ForecastEx is **only** accessible through IBKR. You cannot trade ForecastEx contracts on:
- ❌ Robinhood
- ❌ Schwab
- ❌ Fidelity
- ❌ E*TRADE
- ✅ **Interactive Brokers ONLY**

## Step-by-Step Setup

### Step 1: Create IBKR Account (30 minutes)

#### 1.1 Go to Interactive Brokers Website
```
https://www.interactivebrokers.com
```

#### 1.2 Click "Open Account"
Choose:
- **Account Type**: Individual
- **Account Features**: Trading
- **Citizenship**: United States

#### 1.3 Complete Application
You'll need:
- ✓ Social Security Number
- ✓ Driver's License / ID
- ✓ Employment Information
- ✓ Financial Information (net worth, income)
- ✓ Trading Experience (be honest)

**Important Settings:**
- Enable **Futures** (required for event contracts)
- Enable **Options** (helpful but optional)
- Select **Margin** or **Cash** (Cash is simpler)

#### 1.4 Funding Requirements

**Paper Trading Account**: $0 (starts with $1M virtual money)
**Live Trading Account**:
- Minimum: $0 (but recommended $2,000+)
- For ForecastEx: Start with $500-1,000

#### 1.5 Application Processing
- Usually approved in **1-3 business days**
- May require identity verification (selfie + ID)
- You'll receive credentials via email

### Step 2: Enable ForecastEx Trading (15 minutes)

Once your account is approved:

#### 2.1 Log In to Client Portal
```
https://www.interactivebrokers.com/portal
```

#### 2.2 Navigate to Trading Permissions
1. Click your name (top right)
2. Select **Settings** → **Account Settings**
3. Click **Trading Experience and Permissions**

#### 2.3 Request Event Contracts Permission
1. Find **Event Contracts** or **Prediction Markets**
2. Click **Add Permission**
3. Answer experience questions:
   - Experience level: Select appropriate
   - Knowledge: "I understand event contracts"
   - Objective: "Speculation" or "Hedging"
4. Submit request

**Note**: This may require **additional approval** (1-2 days)

#### 2.4 Verify Permission Granted
Look for:
- Event Contracts: ✅ Approved
- ForecastEx: ✅ Enabled

### Step 3: Download and Configure TWS/Gateway (15 minutes)

You need **one** of these:

#### Option A: TWS (Trader Workstation) - Full Platform
**Pros**: Full-featured, charts, research
**Cons**: Heavier, more complex UI

**Download:**
```
https://www.interactivebrokers.com/en/trading/tws.php
```

#### Option B: IB Gateway - API Only
**Pros**: Lightweight, perfect for bots
**Cons**: No GUI, API only

**Download:**
```
https://www.interactivebrokers.com/en/trading/ibgateway-stable.php
```

**Recommendation**: Start with **IB Gateway** (simpler for bots)

#### 3.1 Install the Software

**macOS:**
```bash
# Download the DMG file
# Open and drag to Applications
# Run IB Gateway
```

**Windows:**
```bash
# Download the EXE file
# Run installer
# Launch IB Gateway
```

**Linux:**
```bash
# Download the SH file
chmod +x ibgateway-*.sh
./ibgateway-*.sh
```

#### 3.2 Initial Configuration

1. **Launch IB Gateway**
2. **Login**:
   - Username: (your IBKR username)
   - Password: (your IBKR password)
3. **Select Mode**:
   - ✅ **Paper Trading** (use this first!)
   - ⬜ Live Trading (use later)

#### 3.3 Enable API Access

1. In IB Gateway, click **Configure** → **Settings**
2. Go to **API** → **Settings** tab
3. Enable these options:
   - ✅ **Enable ActiveX and Socket Clients**
   - ✅ **Read-Only API** (for safety during testing)
   - ✅ **Download open orders on connection**
4. Set **Socket Port**:
   - Paper Trading: **4002** (default)
   - Live Trading: **7496** (default)
5. **Trusted IP addresses**: Add `127.0.0.1`
6. Click **OK** and restart IB Gateway

### Step 4: Update Your .env File (2 minutes)

Edit `/Users/tippens/solarcode/repos/poly-bot/.env`:

```bash
# IBKR Connection Settings
IB_HOST=127.0.0.1
IB_PORT=4002              # 4002 for paper, 7496 for live
IB_CLIENT_ID=1            # Use unique IDs if running multiple bots

# Trading Settings
USER_REGION=US_CA
ALLOW_POLYMARKET_EXECUTION=false  # Must be false!
ALLOW_US_EXECUTION=true           # Enable IBKR trading
RISK_FREE_RATE=0.045              # 4.5% (current 2026 rate)
```

### Step 5: Test the Connection (5 minutes)

With IB Gateway running and configured:

```bash
# Activate your virtual environment
cd /Users/tippens/solarcode/repos/poly-bot
source venv/bin/activate

# Test IBKR connection
PYTHONPATH=/Users/tippens/solarcode/repos/poly-bot python tests/test_integration_ibkr.py
```

**Expected Output:**
```
============================================================
TEST: Connect to IBKR TWS/Gateway
============================================================
Connecting to IBKR at 127.0.0.1:4002 with client ID 1...
Connected to IBKR successfully.
✓ Successfully connected to IBKR

============================================================
TEST: Look Up Contract Details
============================================================
Looking up SPY (S&P 500 ETF) contract...
✓ Found 1 contract details for SPY
```

### Step 6: Verify ForecastEx Contracts (Critical!)

This is the "boring plumbing" that makes money.

```bash
source venv/bin/activate

python -c "
import sys
sys.path.insert(0, '/Users/tippens/solarcode/repos/poly-bot')

from src.execution.ibkr_client import IBKRClient
from ib_insync import Contract

# Connect to IBKR
client = IBKRClient()
client.ib.connect('127.0.0.1', 4002, 1)

if client._connected:
    print('✓ Connected to IBKR')

    # Try to find ForecastEx contracts
    print()
    print('Searching for ForecastEx contracts...')

    # Search for event contracts
    contract = Contract(
        secType='EVENT',  # or 'OPT' for binary options
        exchange='FORECASTX',
        currency='USD'
    )

    details = client.get_contract_details(contract)

    if details:
        print(f'✓ Found {len(details)} ForecastEx contracts!')
        for i, d in enumerate(details[:5], 1):
            print(f'{i}. {d.longName} (Symbol: {d.contract.symbol})')
    else:
        print('⚠ No ForecastEx contracts found.')
        print('  This might mean:')
        print('  1. ForecastEx permission not yet approved')
        print('  2. No contracts currently available')
        print('  3. Need to use different contract search parameters')

    client.disconnect()
else:
    print('✗ Could not connect to IBKR')
"
```

### Step 7: Map Your First Contract (The Money-Making Part!)

Once you find ForecastEx contracts, you need to map them:

**Example Mapping:**
```python
# In src/execution/forecastex_contracts.py

symbol_root_map = {
    "US CPI YoY": "USCPI",           # ← You need to find this
    "BTC Quarterly": "BTCQ",         # ← And this
    "Fed Rate Decision": "FED",      # ← And this
    # Add more as you discover them
}
```

**How to find the correct symbols:**

1. **Use IBKR Contract Search:**
   ```python
   # Search broadly
   contract = Contract(secType='EVENT', exchange='FORECASTX')
   details = client.get_contract_details(contract)

   # Print all available
   for d in details:
       print(f"Symbol: {d.contract.symbol}")
       print(f"Description: {d.longName}")
       print(f"Expiry: {d.contract.lastTradeDateOrContractMonth}")
       print("---")
   ```

2. **Match to Polymarket Events:**
   - Find same event on Polymarket
   - Map Polymarket condition_id → IBKR symbol
   - Update watchlist in `main_execution_bot.py`

3. **Test the Mapping:**
   ```python
   # Try to get contract
   contract = factory.get_forecastex_contract(
       description="US CPI YoY",
       strike=100.0,
       expiry_date="2026-03-15",
       is_yes=True
   )

   if contract:
       print(f"✓ Mapping works! Symbol: {contract.symbol}")
   else:
       print("✗ Mapping failed - need to update symbol_root_map")
   ```

## Troubleshooting

### Connection Refused

**Problem**: `[Errno 61] Connection refused`

**Solutions:**
1. Make sure IB Gateway is running
2. Check you're using correct port (4002 for paper)
3. Verify API is enabled in settings
4. Check firewall isn't blocking port

### API Not Enabled

**Problem**: Connection succeeds but can't execute requests

**Solution:**
1. IB Gateway → Configure → Settings
2. API → Settings
3. Enable ActiveX and Socket Clients
4. Restart IB Gateway

### No ForecastEx Contracts Found

**Problem**: Search returns empty list

**Possible Reasons:**
1. **Permission not approved yet** - Check Client Portal
2. **No contracts available** - ForecastEx may have limited offerings
3. **Wrong search parameters** - Try different secType values
4. **Market closed** - Try during US trading hours

**Action:**
1. Verify permission in Client Portal
2. Contact IBKR support: `1-877-442-2757`
3. Ask specifically about "ForecastEx event contract access"

### Read-Only API Blocking Trades

**Problem**: Can query but can't place orders

**Solution**: This is intentional for safety!
- For testing: Keep Read-Only enabled
- For paper trading: Disable Read-Only API
- For live trading: Re-enable Read-Only initially

## Summary Checklist

Before proceeding, verify:

- ✅ IBKR account created and approved
- ✅ ForecastEx permission enabled
- ✅ IB Gateway installed and running
- ✅ API access enabled (port 4002)
- ✅ Connection test passes
- ✅ Can find at least one ForecastEx contract
- ✅ Symbol mapping documented
- ✅ .env file updated

## Next Steps

Once setup is complete:

1. **Document available contracts** - List all ForecastEx symbols
2. **Find Polymarket matches** - Map same events
3. **Update watchlist** - Add to `main_execution_bot.py`
4. **Run paper trading** - Test for 30 days
5. **Analyze results** - Measure actual spreads

## Support

**IBKR Support:**
- Phone: 1-877-442-2757
- Email: help@interactivebrokers.com
- Hours: 24/7

**Common Questions:**
- "How do I enable ForecastEx trading?"
- "What are the margin requirements for event contracts?"
- "How do I find available ForecastEx symbols?"

**Your Bot Support:**
- Check TESTING.md for troubleshooting
- Review TEST_RESULTS.md for test status
- See YIELD_ANALYSIS.md for math validation

---

**Estimated Time**: 1-2 hours total
**Cost**: $0 (paper trading)
**Difficulty**: Moderate (account setup is the hardest part)

Ready to set up your account? Let me know if you hit any issues! 🚀
