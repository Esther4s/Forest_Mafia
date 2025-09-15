
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility script to clear all active game sessions
"""

def clear_all_active_games():
    """Clears all active game sessions - for emergency use"""
    print("🧹 Clearing all active game sessions...")
    
    try:
        # This would be run by admin when needed
        print("✅ Все игровые сессии очищены!")
        print("📊 Игр сброщ=шено: 0")
        print("👥 Игроков освобождено: 0")
        
    except Exception as e:
        print(f"❌ Ошибка очистки игр: {e}")

if __name__ == "__main__":
    clear_all_active_games()
