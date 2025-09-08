#!/bin/bash
truncate -s 0 /var/log/gapup.log
cd /root/FyersGapUp
source venv/bin/activate
python main.py run >> /var/log/gapup.log 2>&1