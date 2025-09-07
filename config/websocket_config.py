from dataclasses import dataclass

@dataclass
class WebSocketConfig:
    # Fyers WebSocket endpoints
    websocket_url: str = "wss://api-t1.fyers.in/socket/v2/dataSock"

    # Connection settings
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    ping_interval: int = 30
    connection_timeout: int = 30

    # Data subscription settings
    subscription_mode: str = "quotes"  # quotes, depth, or full
    enable_heartbeat: bool = True
    buffer_size: int = 8192