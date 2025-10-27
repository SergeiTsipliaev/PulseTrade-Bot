from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
import asyncio

from services.crypto_service import BybitService
from models.lstm_model import LSTMPredictor


class TelegramBotHandlers:
    def __init__(self):
        self.bybit_service = BybitService()
        self.predictor = LSTMPredictor()

    def get_main_menu(self):
        keyboard = [
            [InlineKeyboardButton("🔍 Поиск криптовалюты", callback_data="search")],
            [InlineKeyboardButton("📈 Прогноз цены", callback_data="predict")],
            [InlineKeyboardButton("💼 Мой портфель", callback_data="portfolio")],
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome_text = """
🤖 Добро пожаловать в PulseTrade Bot!

Я помогу вам:
• 🔍 Найти криптовалюты
• 📈 Получить прогноз цен с помощью AI (LSTM)
• 💼 Управлять портфелем

Выберите действие:
        """
        await update.message.reply_text(welcome_text, reply_markup=self.get_main_menu())

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == "search":
            await self.show_search(update, context)
        elif data == "predict":
            await self.show_prediction(update, context)
        elif data == "portfolio":
            await self.show_portfolio(update, context)
        elif data.startswith("symbol_"):
            symbol = data.replace("symbol_", "")
            await self.show_symbol_info(update, context, symbol)

    async def show_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.edit_message_text(
            "Введите название криптовалюты для поиска (например: BTC, ETH, ADA):"
        )

    async def show_prediction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.edit_message_text(
            "Введите символ криптовалюты для прогноза (например: BTCUSDT):"
        )

    async def show_symbol_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str):
        query = update.callback_query

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ticker = loop.run_until_complete(self.bybit_service.get_ticker(symbol))
            loop.close()

            text = f"""
💎 {ticker['symbol']}
💵 Цена: ${ticker['last_price']:.2f}
📊 Изменение 24ч: {ticker['price_change_percent_24h']:+.2f}%
📈 Объем: {ticker['volume_24h']:,.0f}

Хотите получить прогноз цены?
            """

            keyboard = [
                [InlineKeyboardButton("📈 Получить прогноз", callback_data=f"predict_{symbol}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="search")]
            ]

            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.upper()

        if any(cmd in text.lower() for cmd in ['btc', 'eth', 'ada', 'dot', 'link']):
            # Поиск криптовалюты
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                symbols = loop.run_until_complete(self.bybit_service.search_symbols(text))
                loop.close()

                if symbols:
                    keyboard = []
                    for symbol in symbols[:5]:
                        keyboard.append([InlineKeyboardButton(
                            f"{symbol['symbol']} ({symbol['base_coin']})",
                            callback_data=f"symbol_{symbol['symbol']}"
                        )])

                    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="search")])

                    await update.message.reply_text(
                        "🔍 Результаты поиска:",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await update.message.reply_text("❌ Криптовалюты не найдены")

            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка поиска: {str(e)}")

        elif 'USDT' in text or len(text) <= 6:
            # Прогноз цены
            try:
                await update.message.reply_text("🔄 Строю прогноз...")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Получаем данные и прогноз
                historical_data = loop.run_until_complete(self.bybit_service.get_klines(text))
                prediction = loop.run_until_complete(
                    self.predictor.get_price_prediction(text, historical_data)
                )
                loop.close()

                prediction_text = f"""
📈 Прогноз для *{prediction['symbol']}*

💵 Текущая цена: `${prediction['current_price']:.2f}`
📊 Среднее изменение: {prediction['average_change_percent']:+.2f}%
🎯 Рекомендация: *{prediction['recommendation']}*
🤝 Уверенность: {prediction['confidence']:.1f}%

Прогноз на 7 дней:
"""
                for pred in prediction['predictions']:
                    trend = "📈" if pred['change_percent'] > 0 else "📉"
                    prediction_text += f"День {pred['day']}: `${pred['predicted_price']:.2f}` ({pred['change_percent']:+.2f}%) {trend}\n"

                await update.message.reply_text(prediction_text, parse_mode='Markdown')

            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка прогноза: {str(e)}")

    async def show_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            balance = loop.run_until_complete(self.bybit_service.get_wallet_balance())
            loop.close()

            total_equity = float(balance['result']['list'][0]['totalEquity'])

            portfolio_text = f"""
💼 Ваш портфель:

💰 Общий баланс: ${total_equity:.2f}

Для торговли используйте веб-интерфейс или API.
            """

            await query.edit_message_text(portfolio_text, reply_markup=self.get_main_menu())

        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")


def setup_handlers(application):
    handlers = TelegramBotHandlers()

    application.add_handler(CallbackQueryHandler(handlers.handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text_message))