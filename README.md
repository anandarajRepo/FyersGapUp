# Gap-Up Trading Strategy with WebSocket

A high-performance gap-up short selling strategy that uses WebSocket connections for real-time market data, eliminating API rate limit issues.

## 🌟 Key Features

### WebSocket Integration
- **Real-time Data**: Live price feeds via WebSocket eliminates rate limiting
- **Auto-reconnection**: Robust reconnection logic with exponential backoff
- **Multi-symbol Support**: Subscribe to multiple stocks simultaneously
- **Low Latency**: Sub-second data updates for faster signal generation

### Strategy Features
- **Gap-Up Detection**: Identifies stocks gapping up with selling pressure
- **Technical Analysis**: RSI, volume analysis, and momentum indicators
- **Risk Management**: Portfolio-level stop losses and position sizing
- **Sector Diversification**: Weighted allocation across different sectors

### Performance Monitoring
- **Real-time P&L**: Live tracking of realized and unrealized profits
- **Position Management**: Automatic stop loss and target management
- **Performance Metrics**: Comprehensive performance analytics

## 📋 Prerequisites

- Python 3.9 or higher
- Fyers Trading Account with API access
- Valid Fyers API credentials (Client ID, Secret Key, Access Token)

## 🚀 Quick Start

### 1. Installation
```bash
# Clone or create the project
mkdir gap_up_strategy_ws
cd gap_up_strategy_ws

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copy and edit environment file
cp .env.template .env
nano .env  # Add your Fyers API credentials
```

### 3. Test WebSocket Connection
```bash
python main.py test
```

### 4. Run Strategy
```bash
python main.py run
```

## ⚙️ Configuration

### Environment Variables

```bash
# Required - Fyers API Credentials
FYERS_CLIENT_ID=your_client_id
FYERS_SECRET_KEY=your_secret_key  
FYERS_ACCESS_TOKEN=your_access_token

# Portfolio Settings
PORTFOLIO_VALUE=1000000      # Total portfolio value
RISK_PER_TRADE=1.0          # Risk per trade (%)
MAX_POSITIONS=3             # Maximum concurrent positions

# Strategy Parameters
MIN_GAP_PERCENTAGE=0.5      # Minimum gap-up %
MIN_SELLING_PRESSURE=40.0   # Minimum selling pressure score
MIN_VOLUME_RATIO=1.2        # Minimum volume vs average
MIN_CONFIDENCE=0.6          # Minimum signal confidence
STOP_LOSS_PCT=1.5          # Stop loss %
TARGET_PCT=3.0             # Profit target %
```

### WebSocket Settings

The strategy uses optimized WebSocket settings:
- **Auto-reconnection**: 5-second intervals, max 10 attempts
- **Ping interval**: 30 seconds to maintain connection
- **Buffer size**: 8KB for efficient data handling
- **Connection timeout**: 30 seconds

## 📊 Strategy Logic

### Signal Generation
1. **Market Gap-Up Check**: Verify overall market is gapping up
2. **Individual Stock Analysis**: 
   - Gap percentage > minimum threshold
   - High selling pressure score (bearish indicators)
   - Volume above average
3. **Technical Confirmation**:
   - RSI analysis
   - Price momentum
   - Sector weighting
4. **Risk Assessment**: Position sizing based on stop loss distance

### Position Management
- **Entry**: Short positions when gap-up shows selling pressure
- **Stop Loss**: Automatic stop loss at configured percentage
- **Target**: Profit taking at target percentage
- **Time-based**: Position monitoring during trading hours only

### Real-time Monitoring
- **Live P&L**: Continuous P&L calculation using WebSocket prices
- **Auto-exit**: Automatic position closure on stop loss/target
- **Performance tracking**: Real-time strategy metrics

## 🛡️ Risk Management

### Portfolio Level
- Maximum position limit (default: 3)
- Risk per trade capped at 1% of portfolio
- Daily P&L monitoring

### Position Level  
- Tight stop losses (1.5% default)
- Clear profit targets (3% default)
- Sector diversification

### Technical Safeguards
- WebSocket reconnection logic
- Error handling and logging
- Market hours validation

## 📈 Expected Performance

### Conservative Estimates
- **Daily Trades**: 1-3 signals per day
- **Win Rate**: 60-65% expected
- **Risk-Reward**: 1:2 ratio (1.5% risk, 3% target)
- **Monthly Target**: 8-12% portfolio growth

### Performance Tracking
- Real-time P&L updates
- Position-by-position analysis
- Strategy performance metrics
- WebSocket connection health

## 🔧 Troubleshooting

### Common Issues

#### WebSocket Connection Failed
```bash
# Check credentials
echo $FYERS_ACCESS_TOKEN

# Test connection
python main.py test
```

#### No Live Data Received
- Verify access token is valid and not expired
- Check if market is open
- Ensure symbols are correctly mapped

#### Strategy Not Generating Signals
- Check minimum gap percentage setting
- Verify market has gap-up conditions
- Review selling pressure thresholds

### Logs and Debugging
- All activity logged to `gap_up_strategy_websocket.log`
- Set `LOG_LEVEL=DEBUG` for detailed logging
- Monitor WebSocket connection status

## 🚦 Running in Production

### Recommended Setup
1. **VPS/Cloud Server**: For 24/7 operation
2. **Process Management**: Use systemd or PM2
3. **Monitoring**: Set up alerts for disconnections
4. **Backup**: Regular configuration backups

### Production Checklist
- [ ] Valid API credentials configured
- [ ] WebSocket connection tested
- [ ] Risk parameters validated
- [ ] Logging configured
- [ ] Performance monitoring setup
- [ ] Backup strategy in place

## 📞 Support

### Logs Location
- Main log: `gap_up_strategy_websocket.log`
- Error details included in logs
- WebSocket connection status tracked

### Common Solutions
1. **Token Expiry**: Refresh access token in Fyers portal
2. **Network Issues**: Check internet connectivity
3. **Market Hours**: Strategy only active during trading hours
4. **Symbol Issues**: Verify symbol mapping in code

## ⚠️ Important Notes

### Risk Disclaimer
- This is educational software for learning algorithmic trading
- Always test with small amounts first
- Past performance doesn't guarantee future results
- Trading involves risk of loss

### API Limitations
- WebSocket eliminates rate limiting issues
- Ensure stable internet connection
- Monitor API status on Fyers website

### Market Conditions
- Strategy works best in trending markets
- Gap-up conditions required for signals
- Performance varies with market volatility

---

**Happy Trading! 📈**