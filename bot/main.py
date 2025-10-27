from telegram.ext import Application
import asyncio
import threading
from api.web_app_api import run_web_server
from bot.handlers import setup_handlers
from config import TelegramConfig


def run_telegram_bot():
    """Запуск Telegram бота"""
    application = Application.builder().token(TelegramConfig.BOT_TOKEN).build()
    setup_handlers(application)

    print("Starting Telegram bot...")
    application.run_polling()


def run_web_app():
    """Запуск веб-сервера"""
    print("Starting web server...")
    run_web_server()


if __name__ == '__main__':
    # Запускаем оба сервиса в разных потоках
    telegram_thread = threading.Thread(target=run_telegram_bot)
    web_thread = threading.Thread(target=run_web_app)

    telegram_thread.start()
    web_thread.start()

    telegram_thread.join()
    web_thread.join()