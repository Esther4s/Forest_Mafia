
import asyncio
import logging
from telegram import Bot
from config import BOT_TOKEN

async def pin_welcome_message(chat_id: int):
    """Отправляет и закрепляет приветственное сообщение"""
    bot = Bot(token=BOT_TOKEN)
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("🎮 Начать игру", callback_data="welcome_start_game")],
        [InlineKeyboardButton("📖 Правила игры", callback_data="welcome_rules")],
        [InlineKeyboardButton("📊 Статус игры", callback_data="welcome_status")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🌲 **Добро пожаловать в Лес и Волки!** 🌲\n\n"
        "🎭 Это захватывающая ролевая игра в стиле 'Мафия' с лесными зверушками!\n\n"
        "🐺 **Хищники:** Волки и Лиса\n"
        "🐰 **Травоядные:** Зайцы, Крот и Бобёр\n\n"
        "🎯 **Цель:** Уничтожить команду противника!\n\n"
        "👥 Для игры нужно минимум 6 игроков\n"
        "⏰ Игра состоит из ночных и дневных фаз\n\n"
        "Нажмите кнопку ниже, чтобы начать!"
    )
    
    try:
        # Отправляем сообщение
        message = await bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Закрепляем сообщение
        await bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message.message_id,
            disable_notification=True
        )
        
        print(f"✅ Приветственное сообщение отправлено и закреплено в чате {chat_id}")
        return message.message_id
        
    except Exception as e:
        print(f"❌ Ошибка при отправке/закреплении сообщения: {e}")
        return None

if __name__ == "__main__":
    # Замените на ID вашего чата
    chat_id = input("Введите ID чата для закрепления приветственного сообщения: ")
    try:
        chat_id = int(chat_id)
        asyncio.run(pin_welcome_message(chat_id))
    except ValueError:
        print("❌ Неверный формат ID чата")
