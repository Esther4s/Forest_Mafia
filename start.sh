#!/bin/bash
echo "Starting Forest Mafia Bot with enhanced effects..."

# Update database structure
python3 -c "
try:
    from improve_active_effects_table import improve_active_effects_table
    improve_active_effects_table()
    print('Database updated successfully')
except Exception as e:
    print(f'Database update error: {e}')
"

# Start the bot
python3 bot.py
