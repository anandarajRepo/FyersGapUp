import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

from config.settings import FyersConfig, StrategyConfig, TradingConfig
from config.websocket_config import WebSocketConfig
from strategy.gap_up_strategy import GapUpStrategyWebSocket

# Import the enhanced authentication system
from utils.enhanced_auth_helper import (
    setup_auth_only,
    authenticate_fyers,
    test_authentication,
    update_pin_only
)

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
    """Main function to run the gap-up strategy with enhanced authentication"""

    try:
        # Load configuration
        fyers_config, strategy_config, trading_config, ws_config = load_configuration()

        # Validate basic configuration
        if not all([fyers_config.client_id, fyers_config.secret_key]):
            logger.error("Missing required Fyers API credentials")
            logger.error("Please set FYERS_CLIENT_ID and FYERS_SECRET_KEY")
            logger.error("Run 'python main.py auth' to setup authentication")
            return

        # Enhanced authentication with auto-refresh
        config_dict = {'fyers_config': fyers_config}
        if not authenticate_fyers(config_dict):
            logger.error("Authentication failed. Please run 'python main.py auth' to setup authentication")
            return

        # Create and run strategy
        strategy = GapUpStrategyWebSocket(
            fyers_config=config_dict['fyers_config'],
            strategy_config=strategy_config,
            trading_config=trading_config,
            ws_config=ws_config
        )

        # Run strategy
        await strategy.run()

    except Exception as e:
        logger.error(f"Fatal error in main: {e}")


def test_websocket_connection():
    """Test WebSocket connection independently with enhanced authentication"""

    async def test():
        try:
            fyers_config, _, _, ws_config = load_configuration()

            # Enhanced authentication
            config_dict = {'fyers_config': fyers_config}
            if not authenticate_fyers(config_dict):
                logger.error("Authentication failed for WebSocket test")
                return

            # Test WebSocket service
            from services.fyers_websocket_service import FyersWebSocketService

            ws_service = FyersWebSocketService(config_dict['fyers_config'], ws_config)

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


def show_authentication_help():
    """Show authentication help and status"""
    print("\n=== Fyers Authentication Status ===")

    # Check current credentials
    client_id = os.environ.get('FYERS_CLIENT_ID')
    secret_key = os.environ.get('FYERS_SECRET_KEY')
    access_token = os.environ.get('FYERS_ACCESS_TOKEN')
    refresh_token = os.environ.get('FYERS_REFRESH_TOKEN')
    pin = os.environ.get('FYERS_PIN')

    print(f"Client ID: {'✓ Set' if client_id else '✗ Missing'}")
    print(f"Secret Key: {'✓ Set' if secret_key else '✗ Missing'}")
    print(f"Access Token: {'✓ Set' if access_token else '✗ Missing'}")
    print(f"Refresh Token: {'✓ Set' if refresh_token else '✗ Missing'}")
    print(f"Trading PIN: {'✓ Set' if pin else '✗ Missing'}")

    print(f"\n=== Authentication Options ===")
    print(f"1. Full Setup: python main.py auth")
    print(f"2. Test Auth: python main.py test-auth")
    print(f"3. Update PIN: python main.py update-pin")

    if not access_token:
        print(f"\n⚠️  No access token found. Run setup first.")
    elif not refresh_token:
        print(f"\n⚠️  No refresh token found. Consider re-running setup for auto-refresh.")
    elif not pin:
        print(f"\n⚠️  No trading PIN found. Set PIN for automatic token refresh.")
    else:
        print(f"\n✅ Authentication setup appears complete.")


def show_authentication_status():
    """Show detailed authentication status"""
    print("\n=== Fyers Authentication Status ===")

    # Check current credentials
    client_id = os.environ.get('FYERS_CLIENT_ID')
    secret_key = os.environ.get('FYERS_SECRET_KEY')
    access_token = os.environ.get('FYERS_ACCESS_TOKEN')
    refresh_token = os.environ.get('FYERS_REFRESH_TOKEN')
    pin = os.environ.get('FYERS_PIN')

    print(f"Client ID: {'✓ Set' if client_id else '✗ Missing'}")
    print(f"Secret Key: {'✓ Set' if secret_key else '✗ Missing'}")
    print(f"Access Token: {'✓ Set' if access_token else '✗ Missing'}")
    print(f"Refresh Token: {'✓ Set' if refresh_token else '✗ Missing'}")
    print(f"Trading PIN: {'✓ Set' if pin else '✗ Missing'}")

    # Test token validity if available
    if access_token and client_id:
        from utils.enhanced_auth_helper import FyersAuthManager
        auth_manager = FyersAuthManager()

        print(f"\n=== Token Validation ===")
        if auth_manager.is_token_valid(access_token):
            print(f"Access Token: ✓ Valid")
        else:
            print(f"Access Token: ✗ Invalid or Expired")

    print(f"\n=== Authentication Commands ===")
    print(f"Setup: python main.py auth")
    print(f"Test: python main.py test-auth")
    print(f"Update PIN: python main.py update-pin")

    if not access_token:
        print(f"\n⚠️  No access token found. Run setup first.")
    elif not refresh_token:
        print(f"\n⚠️  No refresh token found. Consider re-running setup for auto-refresh.")
    elif not pin:
        print(f"\n⚠️  No trading PIN found. Set PIN for automatic token refresh.")
    else:
        print(f"\n✅ Authentication setup appears complete.")


def main():
    """Main entry point with enhanced authentication options"""

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "run":
            logger.info("Starting Gap-Up Strategy with Enhanced Authentication")
            asyncio.run(run_gap_up_strategy())

        elif command == "test":
            logger.info("Testing WebSocket Connection with Enhanced Authentication")
            test_websocket_connection()

        elif command == "auth":
            setup_auth_only()

        elif command == "test-auth":
            test_authentication()

        elif command == "update-pin":
            update_pin_only()

        elif command == "auth-status":
            show_authentication_help()

        else:
            print("Available commands:")
            print("  python main.py run         - Run the gap-up strategy")
            print("  python main.py test        - Test WebSocket connection")
            print("  python main.py auth        - Setup Fyers authentication")
            print("  python main.py test-auth   - Test authentication")
            print("  python main.py update-pin  - Update trading PIN")
            print("  python main.py auth-status - Show authentication status")

    else:
        print("Gap-Up Trading Strategy with Enhanced Authentication")
        print("=" * 60)
        print("1. Run Strategy")
        print("2. Test WebSocket Connection")
        print("3. Setup Authentication")
        print("4. Test Authentication")
        print("5. Update Trading PIN")
        print("6. Show Authentication Status")
        print("7. Exit")

        choice = input("\nSelect option (1-7): ").strip()

        if choice == "1":
            logger.info("Starting Gap-Up Strategy with Enhanced Authentication")
            asyncio.run(run_gap_up_strategy())

        elif choice == "2":
            logger.info("Testing WebSocket Connection with Enhanced Authentication")
            test_websocket_connection()

        elif choice == "3":
            setup_auth_only()

        elif choice == "4":
            test_authentication()

        elif choice == "5":
            update_pin_only()

        elif choice == "6":
            show_authentication_status()

        elif choice == "7":
            print("Goodbye!")

        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()