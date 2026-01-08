# Polymarket → ForecastEx Arbitrage Bot

A production-ready Python trading system that uses Polymarket as a read-only signal source and executes trades on US-regulated venues (ForecastEx via Interactive Brokers).

## 🎯 Core Objective

Build a "Signal → Execution" hybrid trading system that:

- **Signal Layer**: Treats Polymarket strictly as read-only (no private keys, public APIs only)
- **Execution Layer**: Executes real trades only on US-regulated venues (ForecastEx via IBKR TWS API)
- **Paper Trading**: Starts in paper mode for all execution logic
- **Yield-Adjusted Pricing**: Uses time-value-of-money adjustments for fair value calculations

## 🏗️ Architecture

### Two-Layer Design

1. **Signal Layer** - Polymarket "Digital Twin" (Read-Only)
   - FastMCP-based signal server
   - Calls Polymarket Gamma API for market discovery
   - Calls Polymarket CLOB public endpoints for order book data
   - Computes liquidity-weighted probability metrics
   - Exposes signals via MCP resources and tools

2. **Execution Layer** - US-Regulated Venues
   - ForecastEx via Interactive Brokers TWS API
   - ib_insync for async-friendly IBKR integration
   - Contract factory for ForecastEx binary options
   - Execution engine with yield-adjusted fair value
   - Paper trading ledger (SQLite + CSV)

## 📁 Project Structure

```
poly-bot/
├── src/
│   ├── signal_server/
│   │   ├── config.py              # Settings via pydantic and .env
│   │   ├── polymarket_client.py   # Gamma + CLOB read-only client
│   │   └── mcp_server.py          # FastMCP server with resources/tools
│   ├── execution/
│   │   ├── ibkr_client.py         # IBKR connection and wrappers
│   │   ├── forecastex_contracts.py # ForecastEx contract factory
│   │   └── forecastex_execution.py # Execution engine with yield adjustment
│   ├── models/
│   │   └── trade_intent.py        # Pydantic model for trade intents
│   └── storage/
│       └── ledger.py              # SQLite/CSV ledger for paper trades
├── main_signal_server.py          # Entry point for MCP signal server
├── main_execution_bot.py          # Entry point for execution bot
├── pyproject.toml                 # Dependencies
├── .env.example                   # Environment variables template
└── README.md                      # This file
```

## 🚀 Setup

### Prerequisites

1. **Python 3.9+**
2. **Interactive Brokers Account**
   - TWS (Trader Workstation) or IB Gateway installed
   - Paper trading account recommended for initial testing
3. **Polymarket Access**
   - No account needed (read-only public APIs)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd poly-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .
   ```

   Or using pip directly:
   ```bash
   pip install fastmcp py-clob-client ib_insync pydantic pydantic-settings \
       python-dotenv requests aiohttp websockets numpy pandas
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your settings:
   ```env
   USER_REGION=US_CA
   ALLOW_POLYMARKET_EXECUTION=false  # MUST be false (read-only)
   ALLOW_US_EXECUTION=true
   IB_HOST=127.0.0.1
   IB_PORT=4002                      # 4002 for paper, 7496 for live TWS
   IB_CLIENT_ID=1
   RISK_FREE_RATE=0.045              # 4.5% annual
   ```

4. **Start Interactive Brokers:**
   - Launch TWS or IB Gateway
   - Enable API connections:
     - Go to `File` → `Global Configuration` → `API` → `Settings`
     - Check "Enable ActiveX and Socket Clients"
     - Check "Read-Only API" for extra safety
     - Note the Socket Port (7496 for live, 4002 for paper)
   - Log in to your account

## 🎮 Usage

### Running the Signal Server

The signal server exposes Polymarket data via FastMCP:

```bash
python main_signal_server.py
```

This will start the MCP server which exposes:
- **Resource**: `polymarket://probability/{condition_id}`
- **Tool**: `get_arb_spread(event_id, regulated_price, days_to_expiry)`

### Running the Execution Bot

The execution bot is the main application that:
1. Fetches signals from Polymarket
2. Prices contracts on ForecastEx via IBKR
3. Calculates yield-adjusted arbitrage spreads
4. Executes trades (paper or live mode)

**Paper Trading (Default):**
```bash
python main_execution_bot.py --mode paper --arb-threshold 0.02 --polling-interval 60
```

**Live Trading (Advanced):**
```bash
python main_execution_bot.py --mode live --arb-threshold 0.02
```

**Options:**
- `--mode`: Trading mode (`paper` or `live`) - default: `paper`
- `--arb-threshold`: Minimum arb spread to trigger trades (e.g., 0.02 = 2%) - default: 0.02
- `--polling-interval`: Seconds between polling cycles - default: 60
- `--max-iterations`: Maximum number of iterations (default: infinite)

**Example:**
```bash
# Run 10 iterations in paper mode with 1% threshold, polling every 30s
python main_execution_bot.py --mode paper --arb-threshold 0.01 --polling-interval 30 --max-iterations 10
```

## 📊 How It Works

### Yield-Adjusted Fair Value

The system calculates fair value for ForecastEx contracts using:

```
P_FX = p_poly × (1 + r × t_days / 365)
```

Where:
- `p_poly` = Polymarket probability (0-1)
- `r` = Risk-free rate (e.g., 0.045 = 4.5%)
- `t_days` = Days to expiry

### Arbitrage Detection

The bot looks for opportunities where:

```
Arb Spread = P_FX_fair - P_FX_market > threshold
```

If the spread exceeds the threshold (e.g., 2%), the bot will:
1. Create a `TradeIntent` to buy on ForecastEx
2. Execute the trade (paper or live mode)
3. Record to the ledger

### Paper Trading Ledger

All trades (paper and live) are recorded to:
- **SQLite Database**: `data/trades.db`
- **CSV Export**: `data/trades.csv`

Query trades:
```python
from src.storage.ledger import TradeLedger

ledger = TradeLedger()
trades = ledger.get_trades(status="EXECUTED", limit=10)
pnl = ledger.calculate_pnl()
```

## 🔒 Safety Features

1. **Read-Only Polymarket Access**
   - No private keys or signing
   - Public APIs only
   - `ALLOW_POLYMARKET_EXECUTION` must be `false`

2. **Paper Trading by Default**
   - All trades start in paper mode
   - Requires explicit `--mode live` flag
   - Confirmation prompt for live mode

3. **US-Only Execution**
   - Only executes on IBKR-regulated venues
   - ForecastEx contracts only

4. **Trade Ledger**
   - All intents logged before execution
   - Full audit trail in SQLite
   - CSV exports for analysis

## 📝 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USER_REGION` | User's region | `US_CA` |
| `ALLOW_POLYMARKET_EXECUTION` | Allow Polymarket execution (MUST be false) | `false` |
| `ALLOW_US_EXECUTION` | Allow US venue execution | `true` |
| `IB_HOST` | IBKR TWS/Gateway host | `127.0.0.1` |
| `IB_PORT` | IBKR TWS/Gateway port | `4002` |
| `IB_CLIENT_ID` | IBKR client ID | `1` |
| `RISK_FREE_RATE` | Annual risk-free rate | `0.045` |

### Market Watchlist

Edit `main_execution_bot.py` to configure your watchlist:

```python
self.watchlist: List[Dict[str, Any]] = [
    {
        "description": "US CPI YoY",
        "strike": 100.0,
        "expiry_date": "2026-03-15",
        "is_yes": True,
        "condition_id": "your_polymarket_condition_id",
        "tags": ["Economics"]
    },
    # Add more markets...
]
```

## 🧪 Testing

### Test Polymarket Client

```bash
python -m src.signal_server.polymarket_client
```

### Test IBKR Connection

```bash
python -m src.execution.ibkr_client
```

### Test ForecastEx Contracts

```bash
python -m src.execution.forecastex_contracts
```

### Test Execution Engine

```bash
python -m src.execution.forecastex_execution
```

### Test Ledger

```bash
python -m src.storage.ledger
```

## 📈 Monitoring

The bot logs detailed information during execution:

- Market scanning results
- Polymarket probabilities
- ForecastEx prices
- Arb spread calculations
- Trade executions
- PnL summaries

Example output:
```
============================================================
Processing: US CPI YoY
============================================================
Polymarket probability: 0.4800
Days to expiry: 45

Arb Analysis for US CPI YoY:
  Polymarket prob: 0.4800
  ForecastEx price: 0.4650
  Yield-adjusted fair: 0.4826
  Arb spread: 0.0176 (1.76%)
  -> No arb: spread 1.76% < threshold 2.00%
```

## ⚠️ Important Notes

### ForecastEx Contract Mapping

ForecastEx contracts on IBKR are modeled as:
- **Security Type**: `OPT` (Options)
- **Exchange**: `FORECASTX`
- **Right**: `C` for Yes, `P` for No
- **Strike**: Event threshold (e.g., 100)
- **Expiry**: Event date in YYYYMMDD format

The contract factory (`forecastex_contracts.py`) includes a symbol mapping:

```python
symbol_root_map = {
    "US CPI YoY": "USCPI",
    "BTC Quarterly": "BTCQ",
    # Add your mappings here
}
```

**Note**: This mapping is placeholder logic. In production, you'll need to:
1. Query IBKR for available ForecastEx contracts
2. Build a dynamic mapping from descriptions to contract symbols
3. Handle contract rollovers and expirations

### Polymarket Condition IDs

To find Polymarket condition IDs:

1. Browse markets at https://polymarket.com
2. Use the Gamma API: `https://gamma-api.polymarket.com/markets`
3. Filter by tags: `https://gamma-api.polymarket.com/markets?tags=Economics`
4. Extract the `condition_id` from the response

## 🛠️ Development

### Project Dependencies

- **fastmcp**: FastMCP server framework
- **py-clob-client**: Polymarket CLOB client (read-only)
- **ib_insync**: Interactive Brokers API wrapper
- **pydantic**: Data validation and settings
- **python-dotenv**: Environment variable management

### Code Style

- Type hints for all functions/classes
- Docstrings for public APIs
- No incomplete TODOs
- Working stubs with clear comments

## 📄 License

[Your License Here]

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Check IBKR API documentation: https://interactivebrokers.github.io/tws-api/
- Check ib_insync documentation: https://ib-insync.readthedocs.io/

## ⚖️ Disclaimer

This software is for educational and research purposes only. Trading involves risk of loss. The authors are not responsible for any financial losses incurred through the use of this software.

**Important:**
- Always test in paper trading mode first
- Understand the risks of algorithmic trading
- Comply with all applicable regulations
- ForecastEx is subject to IBKR and CFTC regulations
- Polymarket may have regional restrictions

---

**Version**: 0.1.0
**Last Updated**: 2026-01-08
