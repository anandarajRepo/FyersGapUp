from datetime import datetime
import pytz
from config.settings import TradingConfig

# IST timezone
IST = pytz.timezone('Asia/Kolkata')


class MarketTimingService:
    """Service for market timing logic"""

    def __init__(self, config: TradingConfig):
        self.config = config

    def is_trading_time(self) -> bool:
        """Check if within trading hours"""
        now = datetime.now(IST)

        # Skip weekends
        if now.weekday() >= 5:
            return False

        market_start = now.replace(
            hour=self.config.market_start_hour,
            minute=self.config.market_start_minute,
            second=0,
            microsecond=0
        )
        market_end = now.replace(
            hour=self.config.market_end_hour,
            minute=self.config.market_end_minute,
            second=0,
            microsecond=0
        )

        return market_start <= now <= market_end

    def is_signal_generation_time(self) -> bool:
        """Check if within signal generation window"""
        now = datetime.now(IST)

        if not self.is_trading_time():
            return False

        signal_end = now.replace(
            hour=self.config.signal_generation_end_hour,
            minute=self.config.signal_generation_end_minute,
            second=0,
            microsecond=0
        )

        market_start = now.replace(
            hour=self.config.market_start_hour,
            minute=self.config.market_start_minute,
            second=0,
            microsecond=0
        )

        return market_start <= now <= signal_end