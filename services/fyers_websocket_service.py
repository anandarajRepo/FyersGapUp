# services/fyers_websocket_service.py - CORRECT IMPLEMENTATION

"""
Correct Fyers WebSocket implementation using the official fyers-apiv3 library
The issue is that we should use the built-in WebSocket functionality from fyers-apiv3
rather than trying to implement WebSocket manually.
"""

import logging
import threading
import time
import asyncio
from typing import Dict, List, Callable, Optional
from datetime import datetime
from queue import Queue

# Import the official Fyers API
from fyers_apiv3 import fyersModel
from fyers_apiv3.FyersWebsocket import data_ws

from config.settings import FyersConfig
from config.websocket_config import WebSocketConfig
from models.trading_models import LiveQuote

logger = logging.getLogger(__name__)


class FyersWebSocketService:
    """Correct Fyers WebSocket service using official fyers-apiv3 library"""

    def __init__(self, fyers_config: FyersConfig, ws_config: WebSocketConfig):
        self.fyers_config = fyers_config
        self.ws_config = ws_config

        # Connection state
        self.is_connected = False
        self.reconnect_count = 0

        # Data management
        self.subscribed_symbols = set()
        self.live_quotes: Dict[str, LiveQuote] = {}
        self.data_callbacks: List[Callable] = []

        # Fyers WebSocket instance
        self.fyers_socket = None

        # Symbol mapping for Fyers format
        self.symbol_mapping = {
            'NESTLEIND.NS': 'NSE:NESTLEIND-EQ',
            'COLPAL.NS': 'NSE:COLPAL-EQ',
            'TATACONSUM.NS': 'NSE:TATACONSUM-EQ',
            'HINDUNILVR.NS': 'NSE:HINDUNILVR-EQ',
            'ITC.NS': 'NSE:ITC-EQ',
            'BRITANNIA.NS': 'NSE:BRITANNIA-EQ',
            'DABUR.NS': 'NSE:DABUR-EQ',
            'MARICO.NS': 'NSE:MARICO-EQ',
            'TCS.NS': 'NSE:TCS-EQ',
            'INFY.NS': 'NSE:INFY-EQ',
            'WIPRO.NS': 'NSE:WIPRO-EQ',
            'HCLTECH.NS': 'NSE:HCLTECH-EQ',
            'TECHM.NS': 'NSE:TECHM-EQ',
            'HDFCBANK.NS': 'NSE:HDFCBANK-EQ',
            'ICICIBANK.NS': 'NSE:ICICIBANK-EQ',
            'SBIN.NS': 'NSE:SBIN-EQ',
            'AXISBANK.NS': 'NSE:AXISBANK-EQ',
            'KOTAKBANK.NS': 'NSE:KOTAKBANK-EQ',
            'INDUSINDBK.NS': 'NSE:INDUSINDBK-EQ',
            'MARUTI.NS': 'NSE:MARUTI-EQ',
            'TATAMOTORS.NS': 'NSE:TATAMOTORS-EQ',
            'BAJAJ-AUTO.NS': 'NSE:BAJAJ-AUTO-EQ',
            'M&M.NS': 'NSE:M&M-EQ',
            'HEROMOTOCO.NS': 'NSE:HEROMOTOCO-EQ',
            'EICHERMOT.NS': 'NSE:EICHERMOT-EQ',
            'RELIANCE.NS': 'NSE:RELIANCE-EQ',
        }

        # Create reverse mapping
        self.reverse_symbol_mapping = {v: k for k, v in self.symbol_mapping.items()}

    def connect(self) -> bool:
        """Connect using official Fyers WebSocket"""
        try:
            logger.info("Connecting to Fyers WebSocket using official API...")

            # Create Fyers WebSocket instance
            self.fyers_socket = data_ws.FyersDataSocket(
                access_token=self.fyers_config.access_token,
                log_path="",  # No file logging
                litemode=False,  # Full mode for all data
                write_to_file=False,  # Don't write to file
                reconnect=True,  # Enable auto-reconnection to WebSocket on disconnection.
                reconnect_retry=10,  # Number of times re-connection will be attempted in case
                on_message=self._on_message,
                on_connect=self._on_open,
                on_close=self._on_close,
                on_error=self._on_error
            )

            # Start connection in background thread
            self._start_connection_thread()

            # Wait for connection
            start_time = time.time()
            while not self.is_connected and time.time() - start_time < self.ws_config.connection_timeout:
                time.sleep(0.1)

            if self.is_connected:
                logger.info("Fyers WebSocket connected successfully")
                return True
            else:
                logger.error("Fyers WebSocket connection timeout")
                return False

        except Exception as e:
            logger.error(f"Error connecting to Fyers WebSocket: {e}")
            return False

    def _start_connection_thread(self):
        """Start WebSocket connection in background thread"""

        def run_connection():
            try:
                self.fyers_socket.connect()
            except Exception as e:
                logger.error(f"Connection thread error: {e}")

        connection_thread = threading.Thread(target=run_connection)
        connection_thread.daemon = True
        connection_thread.start()

    def disconnect(self):
        """Disconnect from Fyers WebSocket"""
        try:
            self.is_connected = False
            if self.fyers_socket:
                self.fyers_socket.close_connection()
            logger.info("Fyers WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

    def subscribe_symbols(self, symbols: List[str]) -> bool:
        """Subscribe to symbols using official Fyers API"""
        try:
            if not self.is_connected:
                logger.error("WebSocket not connected")
                return False

            # Convert to Fyers format
            fyers_symbols = []
            for symbol in symbols:
                fyers_symbol = self.symbol_mapping.get(symbol, symbol)
                fyers_symbols.append(fyers_symbol)
                self.subscribed_symbols.add(symbol)

            # Subscribe using official API
            symbol_list = fyers_symbols

            # Subscribe to data
            self.fyers_socket.subscribe(symbols=symbol_list, data_type="SymbolUpdate")

            logger.info(f"Subscribed to {len(symbols)} symbols: {symbols}")
            return True

        except Exception as e:
            logger.error(f"Error subscribing to symbols: {e}")
            return False

    def unsubscribe_symbols(self, symbols: List[str]) -> bool:
        """Unsubscribe from symbols"""
        try:
            if not self.is_connected:
                return False

            # Convert to Fyers format
            fyers_symbols = []
            for symbol in symbols:
                fyers_symbol = self.symbol_mapping.get(symbol, symbol)
                fyers_symbols.append(fyers_symbol)
                self.subscribed_symbols.discard(symbol)

            # Unsubscribe using official API
            self.fyers_socket.unsubscribe(symbol=fyers_symbols, data_type="SymbolUpdate")

            logger.info(f"Unsubscribed from {len(symbols)} symbols")
            return True

        except Exception as e:
            logger.error(f"Error unsubscribing: {e}")
            return False

    def get_live_quote(self, symbol: str) -> Optional[LiveQuote]:
        """Get latest live quote"""
        return self.live_quotes.get(symbol)

    def get_all_live_quotes(self) -> Dict[str, LiveQuote]:
        """Get all live quotes"""
        return self.live_quotes.copy()

    def add_data_callback(self, callback: Callable):
        """Add callback for data updates"""
        self.data_callbacks.append(callback)

    def _on_open(self):
        """WebSocket opened"""
        self.is_connected = True
        self.reconnect_count = 0
        logger.info("Fyers WebSocket opened")

    def _on_close(self, message):
        """WebSocket closed"""
        self.is_connected = False
        logger.warning(f"Fyers WebSocket closed: {message}")

    def _on_error(self, message):
        """WebSocket error"""
        self.is_connected = False
        logger.error(f"Fyers WebSocket error: {message}")

    def _on_message(self, message):
        """Handle incoming message from Fyers WebSocket"""
        try:
            # Process the message data
            self._process_fyers_data(message)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.debug(f"Message content: {message}")

    def _process_fyers_data(self, data):
        """Process data from Fyers WebSocket"""
        try:
            # Handle different data formats from Fyers
            if isinstance(data, dict):
                symbol_data = data.get('symbol', '')

                # Map back to our symbol format
                our_symbol = self.reverse_symbol_mapping.get(symbol_data)

                if our_symbol:
                    # Create LiveQuote from Fyers data
                    live_quote = LiveQuote(
                        symbol=our_symbol,
                        ltp=float(data.get('ltp', data.get('last_price', 0))),
                        open_price=float(data.get('open_price', data.get('open', 0))),
                        high_price=float(data.get('high_price', data.get('high', 0))),
                        low_price=float(data.get('low_price', data.get('low', 0))),
                        volume=int(data.get('volume', data.get('vol_traded_today', 0))),
                        previous_close=float(data.get('prev_close_price', data.get('prev_close', 0))),
                        timestamp=datetime.now()
                    )

                    # Update storage
                    self.live_quotes[our_symbol] = live_quote

                    # Notify callbacks
                    for callback in self.data_callbacks:
                        try:
                            callback(our_symbol, live_quote)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")

                    logger.debug(f"{our_symbol}: Rs.{live_quote.ltp:.2f} ({live_quote.change_pct:+.2f}%)")

        except Exception as e:
            logger.error(f"Error processing Fyers data: {e}")
            logger.debug(f"Data: {data}")


# Fallback implementation using REST API polling
class FallbackDataService:
    """Fallback service using REST API when WebSocket fails"""

    def __init__(self, fyers_config: FyersConfig, ws_config: WebSocketConfig):
        self.fyers_config = fyers_config
        self.ws_config = ws_config

        # State
        self.is_connected = False
        self.subscribed_symbols = set()
        self.live_quotes: Dict[str, LiveQuote] = {}
        self.data_callbacks: List[Callable] = []

        # Fyers model for REST API
        self.fyers = fyersModel.FyersModel(
            client_id=fyers_config.client_id,
            token=fyers_config.access_token
        )

        # Threading
        self.polling_thread = None
        self.stop_event = threading.Event()

        # Symbol mapping
        self.symbol_mapping = {
            'NESTLEIND.NS': 'NSE:NESTLEIND-EQ',
            'COLPAL.NS': 'NSE:COLPAL-EQ',
            'TATACONSUM.NS': 'NSE:TATACONSUM-EQ',
            'HINDUNILVR.NS': 'NSE:HINDUNILVR-EQ',
            'ITC.NS': 'NSE:ITC-EQ',
            'BRITANNIA.NS': 'NSE:BRITANNIA-EQ',
            'TCS.NS': 'NSE:TCS-EQ',
            'INFY.NS': 'NSE:INFY-EQ',
            'HDFCBANK.NS': 'NSE:HDFCBANK-EQ',
            'ICICIBANK.NS': 'NSE:ICICIBANK-EQ',
            'SBIN.NS': 'NSE:SBIN-EQ',
            'RELIANCE.NS': 'NSE:RELIANCE-EQ',
        }

        self.reverse_symbol_mapping = {v: k for k, v in self.symbol_mapping.items()}

    def connect(self) -> bool:
        """Start fallback data service"""
        try:
            logger.info("Starting fallback REST API data service...")

            # Test API connection
            profile = self.fyers.get_profile()
            if profile.get('s') != 'ok':
                logger.error("Fyers API authentication failed")
                return False

            logger.info(f"Connected to Fyers API for user: {profile.get('data', {}).get('name', 'Unknown')}")

            # Start polling
            self.is_connected = True
            self._start_polling()

            return True

        except Exception as e:
            logger.error(f"Fallback connection error: {e}")
            return False

    def _start_polling(self):
        """Start polling thread"""
        self.polling_thread = threading.Thread(target=self._poll_data)
        self.polling_thread.daemon = True
        self.polling_thread.start()
        logger.info("Fallback polling started")

    def _poll_data(self):
        """Poll for data every few seconds"""
        while not self.stop_event.is_set() and self.is_connected:
            try:
                if self.subscribed_symbols:
                    self._fetch_quotes()
                time.sleep(5)  # Poll every 5 seconds
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(10)  # Longer sleep on error

    def _fetch_quotes(self):
        """Fetch quotes using REST API"""
        try:
            symbols = list(self.subscribed_symbols)
            fyers_symbols = [self.symbol_mapping.get(s, s) for s in symbols]

            # Limit to 25 symbols per request to avoid rate limits
            symbol_chunks = [fyers_symbols[i:i + 25] for i in range(0, len(fyers_symbols), 25)]

            for chunk in symbol_chunks:
                # Get quotes from Fyers API
                data = {"symbols": ",".join(chunk)}
                response = self.fyers.quotes(data)

                if response.get('s') == 'ok':
                    self._process_rest_quotes(response.get('d', {}))
                else:
                    logger.debug(f"API response: {response}")

                # Small delay between chunks
                time.sleep(1)

        except Exception as e:
            logger.debug(f"Fetch quotes error: {e}")

    def _process_rest_quotes(self, data: dict):
        """Process quotes from REST API"""
        try:
            for fyers_symbol, quote_data in data.items():
                our_symbol = self.reverse_symbol_mapping.get(fyers_symbol)

                if our_symbol and isinstance(quote_data, dict):
                    live_quote = LiveQuote(
                        symbol=our_symbol,
                        ltp=float(quote_data.get('lp', 0)),
                        open_price=float(quote_data.get('open_price', 0)),
                        high_price=float(quote_data.get('high_price', 0)),
                        low_price=float(quote_data.get('low_price', 0)),
                        volume=int(quote_data.get('volume', 0)),
                        previous_close=float(quote_data.get('prev_close_price', 0)),
                        timestamp=datetime.now()
                    )

                    # Update storage
                    old_quote = self.live_quotes.get(our_symbol)
                    self.live_quotes[our_symbol] = live_quote

                    # Only notify callbacks if price changed
                    if not old_quote or old_quote.ltp != live_quote.ltp:
                        for callback in self.data_callbacks:
                            try:
                                callback(our_symbol, live_quote)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")

                        logger.info(f"{our_symbol}: Rs.{live_quote.ltp:.2f} ({live_quote.change_pct:+.2f}%)")

        except Exception as e:
            logger.error(f"Process REST quotes error: {e}")

    def subscribe_symbols(self, symbols: List[str]) -> bool:
        """Subscribe to symbols"""
        self.subscribed_symbols.update(symbols)
        logger.info(f"Subscribed to {len(symbols)} symbols: {symbols}")
        return True

    def unsubscribe_symbols(self, symbols: List[str]) -> bool:
        """Unsubscribe from symbols"""
        for symbol in symbols:
            self.subscribed_symbols.discard(symbol)
        logger.info(f"Unsubscribed from {len(symbols)} symbols")
        return True

    def add_data_callback(self, callback: Callable):
        """Add data callback"""
        self.data_callbacks.append(callback)

    def get_live_quote(self, symbol: str) -> Optional[LiveQuote]:
        """Get live quote"""
        return self.live_quotes.get(symbol)

    def get_all_live_quotes(self) -> Dict[str, LiveQuote]:
        """Get all live quotes"""
        return self.live_quotes.copy()

    def disconnect(self):
        """Disconnect"""
        self.stop_event.set()
        self.is_connected = False
        logger.info("Fallback service disconnected")


# Hybrid service that tries WebSocket first, falls back to REST
class HybridFyersDataService:
    """Hybrid service that tries WebSocket first, falls back to REST API"""

    def __init__(self, fyers_config: FyersConfig, ws_config: WebSocketConfig):
        self.fyers_config = fyers_config
        self.ws_config = ws_config

        # Try WebSocket first, fallback to REST
        self.primary_service = None
        self.fallback_service = None
        self.using_fallback = False

        # State
        self.is_connected = False
        self.subscribed_symbols = set()
        self.data_callbacks = []

    def connect(self) -> bool:
        """Try WebSocket first, fallback to REST API"""
        logger.info("Attempting hybrid connection (WebSocket -> REST fallback)")

        # Try WebSocket first
        try:
            self.primary_service = FyersWebSocketService(self.fyers_config, self.ws_config)

            if self.primary_service.connect():
                logger.info("Using WebSocket service")
                self.is_connected = True
                self._setup_callbacks(self.primary_service)
                return True
        except Exception as e:
            logger.warning(f"WebSocket failed: {e}")

        # Fallback to REST API
        try:
            logger.info("Falling back to REST API polling...")
            self.fallback_service = FallbackDataService(self.fyers_config, self.ws_config)

            if self.fallback_service.connect():
                logger.info("Using REST API fallback")
                self.using_fallback = True
                self.is_connected = True
                self._setup_callbacks(self.fallback_service)
                return True
        except Exception as e:
            logger.error(f"Fallback also failed: {e}")

        logger.error("All connection methods failed")
        return False

    def _setup_callbacks(self, service):
        """Setup callbacks for the active service"""
        for callback in self.data_callbacks:
            service.add_data_callback(callback)

    def subscribe_symbols(self, symbols: List[str]) -> bool:
        """Subscribe using active service"""
        active_service = self.fallback_service if self.using_fallback else self.primary_service
        if active_service:
            self.subscribed_symbols.update(symbols)
            return active_service.subscribe_symbols(symbols)
        return False

    def unsubscribe_symbols(self, symbols: List[str]) -> bool:
        """Unsubscribe using active service"""
        active_service = self.fallback_service if self.using_fallback else self.primary_service
        if active_service:
            for symbol in symbols:
                self.subscribed_symbols.discard(symbol)
            return active_service.unsubscribe_symbols(symbols)
        return False

    def add_data_callback(self, callback: Callable):
        """Add callback"""
        self.data_callbacks.append(callback)
        active_service = self.fallback_service if self.using_fallback else self.primary_service
        if active_service:
            active_service.add_data_callback(callback)

    def get_live_quote(self, symbol: str) -> Optional[LiveQuote]:
        """Get live quote"""
        active_service = self.fallback_service if self.using_fallback else self.primary_service
        return active_service.get_live_quote(symbol) if active_service else None

    def get_all_live_quotes(self) -> Dict[str, LiveQuote]:
        """Get all live quotes"""
        active_service = self.fallback_service if self.using_fallback else self.primary_service
        return active_service.get_all_live_quotes() if active_service else {}

    def disconnect(self):
        """Disconnect active service"""
        if self.primary_service:
            self.primary_service.disconnect()
        if self.fallback_service:
            self.fallback_service.disconnect()
        self.is_connected = False


# Quick test function
def test_fyers_connection():
    """Test Fyers connection with all methods"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    config = FyersConfig(
        client_id=os.environ.get('FYERS_CLIENT_ID'),
        secret_key=os.environ.get('FYERS_SECRET_KEY'),
        access_token=os.environ.get('FYERS_ACCESS_TOKEN')
    )

    ws_config = WebSocketConfig()

    print("Testing Fyers Data Services")
    print("=" * 50)

    # Test hybrid service
    service = HybridFyersDataService(config, ws_config)

    def on_data(symbol, quote):
        print(f"{symbol}: Rs.{quote.ltp:.2f} ({quote.change_pct:+.2f}%)")

    service.add_data_callback(on_data)

    if service.connect():
        print(f"Connected! Using: {'REST API' if service.using_fallback else 'WebSocket'}")

        # Test subscription
        test_symbols = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']
        if service.subscribe_symbols(test_symbols):
            print(f"Subscribed to: {test_symbols}")

            # Wait for data
            print("Waiting for data (60 seconds)...")
            time.sleep(60)
        else:
            print("Subscription failed")

        service.disconnect()
    else:
        print("All connection methods failed")


if __name__ == "__main__":
    test_fyers_connection()