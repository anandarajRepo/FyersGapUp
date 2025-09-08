#!/bin/bash

# Log the stop attempt
echo "$(date): Attempting to stop scalping process..." >> /var/log/scalping.log

# Method 1: Find and kill by script name
pkill -f "main_enhanced_scalping.py scalping"

# Method 2: Alternative - kill by python process running the specific script
# ps aux | grep "main_enhanced_scalping.py scalping" | grep -v grep | awk '{print $2}' | xargs kill -15

# Wait a moment for graceful shutdown
sleep 5

# Force kill if still running
pkill -9 -f "main_enhanced_scalping.py scalping"

# Log completion
echo "$(date): Stop script completed" >> /var/log/scalping.log

# Optional: Check if process is still running
if pgrep -f "main_enhanced_scalping.py scalping" > /dev/null; then
    echo "$(date): WARNING - Process still running!" >> /var/log/scalping.log
else
    echo "$(date): Process successfully stopped" >> /var/log/scalping.log
fi