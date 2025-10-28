#!/usr/bin/env python3
"""
Запуск Flask API и Telegram бота одновременно
"""

import subprocess
import sys
import os
import signal
import time

# Процессы
processes = []


def signal_handler(sig, frame):
    """Обработка Ctrl+C"""
    print("\n🛑 Останавливаем приложения...")
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except:
            p.kill()
    sys.exit(0)


def main():
    print("=" * 70)
    print("🚀 Запуск приложения (Flask API + Telegram Bot)")
    print("=" * 70)
    print()
    
    # Запуск Flask API
    print("📡 Запуск Flask API (http://localhost:5000)...")
    flask_process = subprocess.Popen(
        [sys.executable, "-m", "api.web_app_api"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(flask_process)
    
    time.sleep(2)  # Даем Flask время запуститься
    
    # Запуск Telegram бота
    print("🤖 Запуск Telegram бота...")
    bot_process = subprocess.Popen(
        [sys.executable, "-m", "bot.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(bot_process)
    
    print()
    print("=" * 70)
    print("✅ Оба процесса запущены!")
    print("=" * 70)
    print()
    
    # Обработка сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Выводим логи обоих процессов
    try:
        for line in flask_process.stdout:
            print(f"[FLASK] {line}", end='')
        for line in bot_process.stdout:
            print(f"[BOT] {line}", end='')
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()