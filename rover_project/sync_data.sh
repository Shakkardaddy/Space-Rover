#!/bin/bash
# Auto-sync data from Pi every 5 seconds

while true; do
    scp -q pi@raspberrypi.local:~/rover_project/rover_data_log.json .
    echo "✓ Data synced at $(date +%H:%M:%S)"
    sleep 5
done