#!/usr/bin/env python3
"""
Создание файлов для развертывания в Railway
"""

import os

def create_start_script():
    """Создает скрипт запуска для Railway"""
    startup_script = '''#!/bin/bash
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
'''
    
    with open('start.sh', 'w', encoding='utf-8') as f:
        f.write(startup_script)
    
    # Make executable
    os.chmod('start.sh', 0o755)
    print("✅ Created start.sh")

def create_procfile():
    """Создает Procfile для Railway"""
    with open('Procfile', 'w', encoding='utf-8') as f:
        f.write('web: bash start.sh\n')
    print("✅ Created Procfile")

def create_railway_json():
    """Создает railway.json"""
    import json
    
    config = {
        "$schema": "https://railway.app/railway.schema.json",
        "build": {
            "builder": "NIXPACKS"
        },
        "deploy": {
            "startCommand": "bash start.sh",
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 3
        }
    }
    
    with open('railway.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print("✅ Created railway.json")

def main():
    """Основная функция"""
    print("Creating Railway deployment files...")
    
    create_start_script()
    create_procfile()
    create_railway_json()
    
    print("\n🎉 Railway files created successfully!")
    print("\nNext steps:")
    print("1. git add .")
    print("2. git commit -m 'Railway: Enhanced effects system'")
    print("3. git push origin master")

if __name__ == "__main__":
    main()
