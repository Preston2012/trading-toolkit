#!/bin/bash
echo "Copying data to hunter and scout..."
SRC=/root/freqtrade-sniper/user_data/data/kraken
cp -r $SRC /root/freqtrade-hunter/user_data/data/
cp -r $SRC /root/freqtrade-scout/user_data/data/
echo "Data copied to all bots!"
