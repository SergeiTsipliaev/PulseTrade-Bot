from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from config import WEB_APP_URL

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📱 Открыть приложение",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )],
        [InlineKeyboardButton(
            text="ℹ️ О приложении",
            callback_data="about"
        )]
    ])

    await message.answer(
        "🚀 <b>Crypto LSTM Predictor</b>\n\n"
        "Искусственный интеллект для прогнозирования криптовалют!\n\n"
        "🧠 <b>Технология:</b> LSTM нейронная сеть\n"
        "📊 <b>Точность:</b> До 85%\n"
        "⏰ <b>Прогноз:</b> До 7 дней\n\n"
        "Нажмите кнопку ниже, чтобы открыть приложение:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "about")
async def about_callback(callback):
    """Информация о приложении"""
    await callback.message.answer(
        "📱 <b>Crypto LSTM Predictor</b>\n\n"
        "<b>Возможности:</b>\n"
        "• 📈 Прогноз цен на 1-7 дней\n"
        "• 🧠 LSTM нейронная сеть\n"
        "• 📊 Технический анализ (RSI, MA, волатильность)\n"
        "• 📉 Интерактивные графики\n"
        "• 🎯 Торговые сигналы\n"
        "• 📱 Адаптивный дизайн\n\n"
        "<b>Поддерживаемые криптовалюты:</b>\n"
        "Bitcoin (BTC), Ethereum (ETH), Binance Coin (BNB), "
        "Solana (SOL), Ripple (XRP)\n\n"
        "<b>Разработчик:</b> @your_username",
        parse_mode="HTML"
    )
    await callback.answer()