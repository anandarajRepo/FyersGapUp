import websocket
import json
import threading
import time
import logging
from typing import Dict, List, Callable, Optional
from datetime import datetime
import asyncio
from queue import Queue

from config.settings import FyersConfig
from config.websocket_config import WebSocketConfig
from models.trading_models import LiveQuote

logger = logging.getLogger(__name__)


class FyersWebSocketService:
    """Enhanced Fyers WebSocket service for real-time data"""

    def __init__(self, fyers_config: FyersConfig, ws_config: WebSocketConfig):
        self.fyers_config = fyers_config
        self.ws_config = ws_config

        # WebSocket connection
        self.ws = None
        self.is_connected = False
        self.reconnect_count = 0

        # Data management
        self.subscribed_symbols = set()
        self.live_quotes: Dict[str, LiveQuote] = {}
        self.data_callbacks: List[Callable] = []
        self.data_queue = Queue()

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

        # Threading
        self.ws_thread = None
        self.data_processor_thread = None
        self.stop_event = threading.Event()

    def connect(self) -> bool:
        """Connect to Fyers WebSocket"""
        try:
            if self.is_connected:
                logger.info("WebSocket already connected")
                return True

            # Prepare WebSocket URL with authentication
            ws_url = f"{self.ws_config.websocket_url}?access_token={self.fyers_config.access_token}"

            # Configure WebSocket
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )

            # Start WebSocket in separate thread
            self.ws_thread = threading.Thread(
                target=self.ws.run_forever,
                kwargs={
                    'ping_interval': self.ws_config.ping_interval,
                    'ping_timeout': 10
                }
            )
            self.ws_thread.daemon = True
            self.ws_thread.start()

            # Start data processor thread
            self.data_processor_thread = threading.Thread(target=self._process_data)
            self.data_processor_thread.daemon = True
            self.data_processor_thread.start()

            # Wait for connection
            start_time = time.time()
            while not self.is_connected and time.time() - start_time < self.ws_config.connection_timeout:
                time.sleep(0.1)

            if self.is_connected:
                logger.info("WebSocket connected successfully")
                return True
            else:
                logger.error("WebSocket connection timeout")
                return False

        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {e}")
            return False

    def disconnect(self):
        """Disconnect from WebSocket"""
        try:
            self.stop_event.set()
            self.is_connected = False

            if self.ws:
                self.ws.close()

            logger.info("WebSocket disconnected")

        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")

    def subscribe_symbols(self, symbols: List[str]) -> bool:
        """Subscribe to real-time data for symbols"""
        try:
            if not self.is_connected:
                logger.error("WebSocket not connected")
                return False

            # Convert symbols to Fyers format
            fyers_symbols = []
            for symbol in symbols:
                fyers_symbol = self.symbol_mapping.get(symbol, symbol)
                fyers_symbols.append(fyers_symbol)
                self.subscribed_symbols.add(symbol)

            # Prepare subscription message
            subscription_msg = {
                "T": "SUB_L2",  # Subscribe to Level 2 data
                "L2LIST": fyers_symbols,
                "SUB_T": 1  # Subscribe type
            }

            # Send subscription
            self.ws.send(json.dumps(subscription_msg))

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

            # Convert symbols to Fyers format
            fyers_symbols = []
            for symbol in symbols:
                fyers_symbol = self.symbol_mapping.get(symbol, symbol)
                fyers_symbols.append(fyers_symbol)
                self.subscribed_symbols.discard(symbol)

            # Prepare unsubscription message
            unsubscription_msg = {
                "T": "UNSUB_L2",
                "L2LIST": fyers_symbols,
                "SUB_T": 0
            }

            self.ws.send(json.dumps(unsubscription_msg))

            logger.info(f"Unsubscribed from {len(symbols)} symbols")
            return True

        except Exception as e:
            logger.error(f"Error unsubscribing from symbols: {e}")
            return False

    def get_live_quote(self, symbol: str) -> Optional[LiveQuote]:
        """Get latest live quote for symbol"""
        return self.live_quotes.get(symbol)

    def get_all_live_quotes(self) -> Dict[str, LiveQuote]:
        """Get all live quotes"""
        return self.live_quotes.copy()

    def add_data_callback(self, callback: Callable):
        """Add callback for real-time data updates"""
        self.data_callbacks.append(callback)

    def _on_open(self, ws):
        """WebSocket connection opened"""
        self.is_connected = True
        self.reconnect_count = 0
        logger.info("WebSocket connection opened")

    def _on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            # Add message to processing queue
            self.data_queue.put(message)

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        logger.error(f"WebSocket error: {error}")
        self.is_connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket close"""
        logger.warning(f"WebSocket closed: {close_status_code} - {close_msg}")
        self.is_connected = False

        # Attempt reconnection if not manually stopped
        if not self.stop_event.is_set() and self.reconnect_count < self.ws_config.max_reconnect_attempts:
            self._attempt_reconnect()

    def _attempt_reconnect(self):
        """Attempt to reconnect WebSocket"""
        self.reconnect_count += 1
        logger.info(f"Attempting reconnection {self.reconnect_count}/{self.ws_config.max_reconnect_attempts}")

        time.sleep(self.ws_config.reconnect_interval)

        if self.connect():
            # Re-subscribe to symbols
            if self.subscribed_symbols:
                self.subscribe_symbols(list(self.subscribed_symbols))

    def _process_data(self):
        """Process incoming data from queue"""
        while not self.stop_event.is_set():
            try:
                if not self.data_queue.empty():
                    message = self.data_queue.get(timeout=1)
                    self._parse_and_update_quotes(message)
                else:
                    time.sleep(0.01)  # Small sleep to prevent high CPU usage

            except Exception as e:
                if not self.stop_event.is_set():
                    logger.error(f"Error processing data: {e}")

    def _parse_and_update_quotes(self, message: str):
        """Parse WebSocket message and update live quotes"""
        try:
            data = json.loads(message)

            # Handle different message types
            if isinstance(data, dict):
                if 'symbol' in data and 'ltp' in data:
                    self._update_quote_from_data(data)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'symbol' in item:
                        self._update_quote_from_data(item)

        except json.JSONDecodeError:
            logger.debug(f"Non-JSON message received: {message}")
        except Exception as e:
            logger.error(f"Error parsing WebSocket data: {e}")

    def _update_quote_from_data(self, data: dict):
        """Update live quote from parsed data"""
        try:
            # Map Fyers symbol back to our format
            fyers_symbol = data.get('symbol', '')
            symbol = None

            for our_symbol, fyers_sym in self.symbol_mapping.items():
                if fyers_sym == fyers_symbol:
                    symbol = our_symbol
                    break

            if not symbol:
                return

            # Create or update live quote
            live_quote = LiveQuote(
                symbol=symbol,
                ltp=float(data.get('ltp', 0)),
                open_price=float(data.get('open_price', 0)),
                high_price=float(data.get('high_price', 0)),
                low_price=float(data.get('low_price', 0)),
                volume=int(data.get('volume', 0)),
                previous_close=float(data.get('prev_close_price', 0)),
                timestamp=datetime.now()
            )

            # Update internal storage
            self.live_quotes[symbol] = live_quote

            # Notify callbacks
            for callback in self.data_callbacks:
                try:
                    callback(symbol, live_quote)
                except Exception as e:
                    logger.error(f"Error in data callback: {e}")

        except Exception as e:
            logger.error(f"Error updating quote from data: {e}")