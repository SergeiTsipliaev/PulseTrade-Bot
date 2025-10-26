import os
import sys

print("🧪 Тестирование импортов...")

# Добавляем корневую директорию
sys.path.insert(0, os.path.abspath('.'))

try:
    from services.coinbase_service import coinbase_service
    print("✅ services.coinbase_service - OK")
except ImportError as e:
    print(f"❌ services.coinbase_service - {e}")

try:
    from models.database import db
    print("✅ models.database - OK")
except ImportError as e:
    print(f"❌ models.database - {e}")

try:
    from api.web_app_api import app
    print("✅ api.web_app_api - OK")
except ImportError as e:
    print(f"❌ api.web_app_api - {e}")

print("🎯 Проверка завершена")