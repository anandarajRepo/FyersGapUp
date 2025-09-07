import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

from config.settings import FyersConfig, StrategyConfig, TradingConfig
from config.websocket_config import WebSocketConfig
from strategy.gap_up_strategy import GapUpStrategyWebSocket

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gap_up_strategy_websocket.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def load_configuration():
    """Load all configuration from environment variables"""

    # Fyers configuration
    fyers_config = FyersConfig(
        client_id=os.environ.get('FYERS_CLIENT_ID'),
        secret_key=os.environ.get('FYERS_SECRET_KEY'),
        access_token=os.environ.get('FYERS_ACCESS_TOKEN')
    )

    # Strategy configuration
    strategy_config = StrategyConfig(
        portfolio_value=float(os.environ.get('PORTFOLIO_VALUE', 1000000)),
        risk_per_trade_pct=float(os.environ.get('RISK_PER_TRADE', 1.0)),
        max_positions=int(os.environ.get('MAX_POSITIONS', 3)),
        min_gap_percentage=float(os.environ.get('MIN_GAP_PERCENTAGE', 0.5)),
        min_selling_pressure=float(os.environ.get('MIN_SELLING_PRESSURE', 40.0)),
        min_volume_ratio=float(os.environ.get('MIN_VOLUME_RATIO', 1.2)),
        min_confidence=float(os.environ.get('MIN_CONFIDENCE', 0.6)),
        stop_loss_pct=float(os.environ.get('STOP_LOSS_PCT', 1.5)),
        target_pct=float(os.environ.get('TARGET_PCT', 3.0))
    )

    # Trading configuration
    trading_config = TradingConfig(
        market_start_hour=9,
        market_start_minute=15,
        market_end_hour=15,
        market_end_minute=30,
        signal_generation_end_hour=10,
        signal_generation_end_minute=30,
        monitoring_interval=30
    )

    # WebSocket configuration
    ws_config = WebSocketConfig(
        reconnect_interval=5,
        max_reconnect_attempts=10,
        ping_interval=30,
        connection_timeout=30
    )

    return fyers_config, strategy_config, trading_config, ws_config


async def run_gap_up_strategy():
    """Main function to run the gap-up strategy"""

    try:
        # Load configuration
        fyers_config, strategy_config, trading_config, ws_config = load_configuration()

        # Validate required configuration
        if not all([fyers_config.client_id, fyers_config.secret_key, fyers_config.access_token]):
            logger.error("Missing required Fyers API credentials")
            logger.error("Please set FYERS_CLIENT_ID, FYERS_SECRET_KEY, and FYERS_ACCESS_TOKEN")
            return

        # Create and run strategy
        strategy = GapUpStrategyWebSocket(
            fyers_config=fyers_config,
            strategy_config=strategy_config,
            trading_config=trading_config,
            ws_config=ws_config
        )

        # Run strategy
        await strategy.run()

    except Exception as e:
        logger.error(f"Fatal error in main: {e}")


def test_websocket_connection():
    """Test WebSocket connection independently"""

    async def test():
        try:
            fyers_config, _, _, ws_config = load_configuration()

            # Test WebSocket service
            from services.fyers_websocket_service import FyersWebSocketService

            ws_service = FyersWebSocketService(fyers_config, ws_config)

            def on_data(symbol, quote):
                logger.info(f"{symbol}: Rs.{quote.ltp:.2f} ({quote.change_pct:+.2f}%)")

            ws_service.add_data_callback(on_data)

            if ws_service.connect():
                logger.info("WebSocket connected successfully")

                # Subscribe to test symbols
                test_symbols = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS']
                if ws_service.subscribe_symbols(test_symbols):
                    logger.info(f"Subscribed to {len(test_symbols)} symbols")

                    # Keep connection alive for test
                    await asyncio.sleep(60)  # 1 minute test

                else:
                    logger.error("Failed to subscribe to symbols")
            else:
                logger.error("Failed to connect to WebSocket")

            ws_service.disconnect()

        except Exception as e:
            logger.error(f"Test failed: {e}")

    asyncio.run(test())


def main():
    """Main entry point"""

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "run":
            logger.info("Starting Gap-Up Strategy with WebSocket")
            asyncio.run(run_gap_up_strategy())

        elif command == "test":
            logger.info("Testing WebSocket Connection")
            test_websocket_connection()

        else:
            print("Available commands:")
            print("  python main.py run   - Run the gap-up strategy")
            print("  python main.py test  - Test WebSocket connection")
    else:
        print("Gap-Up Trading Strategy with WebSocket")
        print("=" * 50)
        print("1. Run Strategy")
        print("2. Test WebSocket Connection")
        print("3. Exit")

        choice = input("\nSelect option (1/2/3): ").strip()

        if choice == "1":
            logger.info("Starting Gap-Up Strategy with WebSocket")
            asyncio.run(run_gap_up_strategy())
        elif choice == "2":
            logger.info("Testing WebSocket Connection")
            test_websocket_connection()
        elif choice == "3":
            print("Goodbye!")
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()