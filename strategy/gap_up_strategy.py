import asyncio
import logging
from typing import Dict, List
from datetime import datetime

from config.settings import FyersConfig, StrategyConfig, TradingConfig, Sector
from config.websocket_config import WebSocketConfig
from models.trading_models import Position, TradingSignal, LiveQuote
from services.fyers_websocket_service import FyersWebSocketService
from services.analysis_service import TechnicalAnalysisService
from services.market_timing_service import MarketTimingService

logger = logging.getLogger(__name__)


class GapUpStrategyWebSocket:
    """Gap-Up Short Strategy with WebSocket Integration"""

    def __init__(self, fyers_config: FyersConfig, strategy_config: StrategyConfig,
                 trading_config: TradingConfig, ws_config: WebSocketConfig):

        # Configuration
        self.fyers_config = fyers_config
        self.strategy_config = strategy_config
        self.trading_config = trading_config
        self.ws_config = ws_config

        # Services
        self.websocket_service = FyersWebSocketService(fyers_config, ws_config)
        self.analysis_service = TechnicalAnalysisService(self.websocket_service)
        self.timing_service = MarketTimingService(trading_config)

        # Strategy state
        self.positions: Dict[str, Position] = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0

        # Stock universe
        self.stock_sectors = {
            'NESTLEIND.NS': Sector.FMCG,
            'COLPAL.NS': Sector.FMCG,
            'TATACONSUM.NS': Sector.FMCG,
            'HINDUNILVR.NS': Sector.FMCG,
            'ITC.NS': Sector.FMCG,
            'BRITANNIA.NS': Sector.FMCG,
            'TCS.NS': Sector.IT,
            'INFY.NS': Sector.IT,
            'WIPRO.NS': Sector.IT,
            'HCLTECH.NS': Sector.IT,
            'TECHM.NS': Sector.IT,
            'HDFCBANK.NS': Sector.BANKING,
            'ICICIBANK.NS': Sector.BANKING,
            'SBIN.NS': Sector.BANKING,
            'AXISBANK.NS': Sector.BANKING,
            'KOTAKBANK.NS': Sector.BANKING,
            'MARUTI.NS': Sector.AUTO,
            'TATAMOTORS.NS': Sector.AUTO,
            'BAJAJ-AUTO.NS': Sector.AUTO,
            'RELIANCE.NS': Sector.AUTO,
        }

        # Sector weights for signal confidence
        self.sector_weights = {
            Sector.FMCG: 1.0,
            Sector.IT: 0.9,
            Sector.BANKING: 0.6,
            Sector.AUTO: 0.3,
            Sector.PHARMA: 0.7,
            Sector.METALS: 0.5,
            Sector.REALTY: 0.4
        }

        # Real-time data tracking
        self.live_quotes: Dict[str, LiveQuote] = {}

        # Add data callback
        self.websocket_service.add_data_callback(self._on_live_data_update)

    async def initialize(self) -> bool:
        """Initialize strategy and WebSocket connection"""
        try:
            # Connect to WebSocket
            if not self.websocket_service.connect():
                logger.error("Failed to connect to WebSocket")
                return False

            # Subscribe to all symbols
            symbols = list(self.stock_sectors.keys())
            if not self.websocket_service.subscribe_symbols(symbols):
                logger.error("Failed to subscribe to symbols")
                return False

            logger.info(f"Gap-Up Strategy initialized with {len(symbols)} symbols")
            return True

        except Exception as e:
            logger.error(f"Strategy initialization failed: {e}")
            return False

    def _on_live_data_update(self, symbol: str, live_quote: LiveQuote):
        """Handle real-time data updates"""
        try:
            # Update internal storage
            self.live_quotes[symbol] = live_quote

            # Log significant price movements
            if abs(live_quote.change_pct) > 2.0:
                logger.info(f"{symbol}: {live_quote.change_pct:+.2f}% - Rs.{live_quote.ltp:.2f}")

        except Exception as e:
            logger.error(f"Error handling live data update for {symbol}: {e}")

    async def run_strategy_cycle(self) -> None:
        """Run one strategy cycle using live WebSocket data"""
        try:
            if not self.timing_service.is_trading_time():
                return

            # Monitor existing positions using live data
            await self._monitor_positions()

            # Generate new signals if in signal generation window
            if self.timing_service.is_signal_generation_time():
                await self._generate_and_execute_signals()

            # Log current status
            self._log_status()

        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")

    async def _monitor_positions(self):
        """Monitor existing positions using live WebSocket data"""
        try:
            positions_to_close = []

            for symbol, position in self.positions.items():
                if symbol in self.live_quotes:
                    live_quote = self.live_quotes[symbol]
                    current_price = live_quote.ltp

                    # Calculate unrealized P&L
                    if position.quantity > 0:  # Long position
                        unrealized_pnl = (current_price - position.entry_price) * position.quantity
                    else:  # Short position
                        unrealized_pnl = (position.entry_price - current_price) * abs(position.quantity)

                    # Check stop loss
                    if ((position.quantity > 0 and current_price <= position.stop_loss) or
                            (position.quantity < 0 and current_price >= position.stop_loss)):

                        positions_to_close.append((symbol, "STOP_LOSS", unrealized_pnl))

                    # Check target
                    elif ((position.quantity > 0 and current_price >= position.target_price) or
                          (position.quantity < 0 and current_price <= position.target_price)):

                        positions_to_close.append((symbol, "TARGET", unrealized_pnl))

            # Close positions that hit stop loss or target
            for symbol, reason, pnl in positions_to_close:
                await self._close_position(symbol, reason, pnl)

        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")

    async def _close_position(self, symbol: str, reason: str, pnl: float):
        """Close a position and update P&L"""
        try:
            if symbol in self.positions:
                position = self.positions[symbol]

                # Update P&L
                self.daily_pnl += pnl
                self.total_pnl += pnl

                # Log closure
                logger.info(f"Position closed: {symbol} - {reason} - P&L: Rs.{pnl:.2f}")

                # Remove from positions
                del self.positions[symbol]

                # Here you would place actual closing order via Fyers API
                # self.place_closing_order(position)

        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")

    async def _generate_and_execute_signals(self):
        """Generate signals using live WebSocket data"""
        try:
            # Check available position slots
            available_slots = self.strategy_config.max_positions - len(self.positions)
            if available_slots <= 0:
                return

            signals = await self._generate_signals()

            # Execute top signals
            executed_count = 0
            for signal in signals[:available_slots]:
                if signal.confidence >= self.strategy_config.min_confidence:
                    if await self._execute_signal(signal):
                        executed_count += 1
                        await asyncio.sleep(2)  # Small delay between executions

            if executed_count > 0:
                logger.info(f"Executed {executed_count} new gap-up trades")

        except Exception as e:
            logger.error(f"Error in signal generation/execution: {e}")

    async def _generate_signals(self) -> List[TradingSignal]:
        """Generate trading signals using live WebSocket data"""
        signals = []

        try:
            # Check if we have a general market gap-up (using Nifty or index)
            market_gap_up = self._check_market_gap_up()

            if not market_gap_up:
                logger.info("No significant market gap-up detected")
                return signals

            # Analyze each stock using live data
            for symbol, sector in self.stock_sectors.items():
                if symbol not in self.live_quotes:
                    continue

                live_quote = self.live_quotes[symbol]

                # Calculate gap percentage
                gap_percentage = live_quote.change_pct

                if gap_percentage < self.strategy_config.min_gap_percentage:
                    continue

                # Calculate technical indicators
                selling_pressure = self.analysis_service.calculate_selling_pressure_score(symbol)
                volume_ratio = self.analysis_service.calculate_volume_ratio(symbol, live_quote)

                # Check entry criteria
                if (selling_pressure >= self.strategy_config.min_selling_pressure and
                        volume_ratio >= self.strategy_config.min_volume_ratio):
                    # Calculate confidence score
                    sector_preference = self.sector_weights.get(sector, 0.5)
                    confidence = (
                            (selling_pressure / 100) * 0.4 +
                            min(volume_ratio / 3, 1) * 0.3 +
                            (gap_percentage / 5) * 0.2 +
                            sector_preference * 0.1
                    )

                    # Calculate stop loss and target using live price
                    current_price = live_quote.ltp
                    stop_loss = current_price * (1 + self.strategy_config.stop_loss_pct / 100)
                    target_price = current_price * (1 - self.strategy_config.target_pct / 100)

                    signal = TradingSignal(
                        symbol=symbol,
                        sector=sector,
                        signal_type='SHORT',
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        target_price=target_price,
                        confidence=confidence,
                        gap_percentage=gap_percentage,
                        selling_pressure_score=selling_pressure,
                        volume_ratio=volume_ratio,
                        timestamp=datetime.now()
                    )

                    signals.append(signal)
                    logger.info(f"Signal: {symbol} - Gap: {gap_percentage:.2f}%, "
                                f"Pressure: {selling_pressure:.1f}, Confidence: {confidence:.2f}")

            # Sort by confidence
            signals.sort(key=lambda x: x.confidence, reverse=True)
            return signals

        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return []

    def _check_market_gap_up(self) -> bool:
        """Check if market has significant gap-up"""
        try:
            # Look for gap-up in major stocks
            gap_up_count = 0
            total_checked = 0

            for symbol in ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS']:
                if symbol in self.live_quotes:
                    live_quote = self.live_quotes[symbol]
                    if live_quote.change_pct > 0.3:  # 0.3% gap up
                        gap_up_count += 1
                    total_checked += 1

            # If majority of large caps are gapping up
            return gap_up_count / total_checked > 0.6 if total_checked > 0 else False

        except Exception as e:
            logger.error(f"Error checking market gap-up: {e}")
            return False

    async def _execute_signal(self, signal: TradingSignal) -> bool:
        """Execute a trading signal"""
        try:
            # Calculate position size
            quantity = self._calculate_position_size(signal)

            if quantity <= 0:
                logger.warning(f"Invalid quantity calculated for {signal.symbol}")
                return False

            # Create position record (simulation mode)
            position = Position(
                symbol=signal.symbol,
                entry_price=signal.entry_price,
                quantity=-quantity,  # Negative for short position
                stop_loss=signal.stop_loss,
                target_price=signal.target_price,
                entry_time=datetime.now(),
                sector=signal.sector,
                order_id=f"SIM_{signal.symbol}_{int(datetime.now().timestamp())}"
            )

            self.positions[signal.symbol] = position

            logger.info(f"New gap-up short position: {signal.symbol} - "
                        f"Qty: {quantity}, Entry: Rs.{signal.entry_price:.2f}")

            return True

        except Exception as e:
            logger.error(f"Error executing signal for {signal.symbol}: {e}")
            return False

    def _calculate_position_size(self, signal: TradingSignal) -> int:
        """Calculate position size based on risk management"""
        try:
            risk_amount = self.strategy_config.portfolio_value * (self.strategy_config.risk_per_trade_pct / 100)
            price_risk = abs(signal.stop_loss - signal.entry_price)

            if price_risk <= 0:
                return 0

            quantity = int(risk_amount / price_risk)
            return max(quantity, 0)

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

    def _log_status(self):
        """Log current strategy status"""
        total_unrealized = 0

        for symbol, position in self.positions.items():
            if symbol in self.live_quotes:
                current_price = self.live_quotes[symbol].ltp
                if position.quantity < 0:  # Short position
                    unrealized = (position.entry_price - current_price) * abs(position.quantity)
                else:  # Long position
                    unrealized = (current_price - position.entry_price) * position.quantity
                total_unrealized += unrealized

        logger.info(f"Strategy Status - Active: {len(self.positions)}, "
                    f"Daily P&L: Rs.{self.daily_pnl:.2f}, "
                    f"Unrealized: Rs.{total_unrealized:.2f}, "
                    f"Total P&L: Rs.{self.total_pnl:.2f}")

    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        return {
            'strategy_name': 'Gap-Up Short WebSocket',
            'total_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'active_positions': len(self.positions),
            'websocket_connected': self.websocket_service.is_connected,
            'subscribed_symbols': len(self.websocket_service.subscribed_symbols),
            'live_quotes_count': len(self.live_quotes),
            'positions_detail': [
                {
                    'symbol': pos.symbol,
                    'sector': pos.sector.value,
                    'entry_price': pos.entry_price,
                    'quantity': pos.quantity,
                    'entry_time': pos.entry_time.strftime('%H:%M:%S'),
                    'current_price': self.live_quotes.get(symbol, {}).ltp if symbol in self.live_quotes else 0,
                    'unrealized_pnl': self._calculate_unrealized_pnl(symbol, pos)
                }
                for symbol, pos in self.positions.items()
            ]
        }

    def _calculate_unrealized_pnl(self, symbol: str, position: Position) -> float:
        """Calculate unrealized P&L for a position"""
        if symbol not in self.live_quotes:
            return 0.0

        current_price = self.live_quotes[symbol].ltp

        if position.quantity < 0:  # Short position
            return (position.entry_price - current_price) * abs(position.quantity)
        else:  # Long position
            return (current_price - position.entry_price) * position.quantity

    async def run(self):
        """Main strategy execution loop"""
        logger.info("Starting Gap-Up Strategy with WebSocket")

        if not await self.initialize():
            logger.error("Strategy initialization failed")
            return

        try:
            while True:
                # Check trading hours
                if not self.timing_service.is_trading_time():
                    logger.info("Outside trading hours, sleeping...")
                    await asyncio.sleep(300)  # 5 minutes
                    continue

                # Run strategy cycle
                await self.run_strategy_cycle()

                # Sleep until next cycle
                await asyncio.sleep(self.trading_config.monitoring_interval)

        except KeyboardInterrupt:
            logger.info("Strategy stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in strategy: {e}")
        finally:
            # Cleanup
            self.websocket_service.disconnect()
            logger.info("WebSocket disconnected and cleanup completed")