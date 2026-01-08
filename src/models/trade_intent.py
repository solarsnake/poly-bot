from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional

class TradeIntent(BaseModel):
    """Pydantic model for a trade intention, used for paper trading and logging."""
    venue: str
    market_type: str # e.g., "Binary Option", "Prediction Market"
    symbol_root: str # e.g., "USCPI", "BTCQ"
    strike: float
    expiry: str      # YYYYMMDD format
    side: Literal['BUY', 'SELL']
    quantity: float
    limit_price: float
    order_type: Literal['LMT'] = 'LMT'
    mode: Literal['paper', 'live']
    timestamp: datetime = datetime.utcnow()
    status: Literal['PENDING', 'EXECUTED', 'CANCELLED', 'FAILED'] = 'PENDING'
    transaction_id: Optional[str] = None # IBKR orderId or similar
    notes: Optional[str] = None

