from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import asyncio
import os
from services.crypto_service import CryptoService
from models.lstm_model import CryptoLSTMPredictor
from config import CRYPTOS, SEQUENCE_LENGTH, PREDICTION_DAYS, EPOCHS, BATCH_SIZE
import numpy as np

app = Flask(__name__, static_folder='../static')
CORS(app)

crypto_service = CryptoService()
predictors = {}


def run_async(coro):
    """Запуск асинхронной функции"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Главная страница (Mini App)
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


# JavaScript файл
@app.route('/app.js')
def app_js():
    return send_from_directory(app.static_folder, 'app.js')


@app.route('/api/cryptos', methods=['GET'])
def get_cryptos():
    """Получить список доступных криптовалют"""
    return jsonify({
        'success': True,
        'data': CRYPTOS
    })


@app.route('/api/crypto/<crypto_id>', methods=['GET'])
def get_crypto_data(crypto_id):
    """Получить данные криптовалюты"""
    try:
        current_data = run_async(crypto_service.get_current_price(crypto_id))

        if not current_data:
            return jsonify({'success': False, 'error': 'Data not found'}), 404

        history = run_async(crypto_service.get_price_history(crypto_id, days=90))

        if not history:
            return jsonify({'success': False, 'error': 'History not found'}), 404

        indicators = crypto_service.calculate_technical_indicators(history['prices'])

        return jsonify({
            'success': True,
            'data': {
                'current': current_data,
                'history': history,
                'indicators': indicators
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/predict/<crypto_id>', methods=['POST'])
def predict_price(crypto_id):
    """Прогнозирование цены с помощью LSTM"""
    try:
        data = request.json or {}
        days = data.get('days', PREDICTION_DAYS)

        history = run_async(crypto_service.get_price_history(crypto_id, days=90))

        if not history:
            return jsonify({'success': False, 'error': 'History not found'}), 404

        prices = np.array(history['prices'])

        if crypto_id not in predictors:
            predictors[crypto_id] = CryptoLSTMPredictor(sequence_length=SEQUENCE_LENGTH)

        predictor = predictors[crypto_id]

        if predictor.model is None:
            predictor.train(prices, epochs=EPOCHS, batch_size=BATCH_SIZE)

        predictions = predictor.predict_future(prices, days=days)

        test_size = min(30, len(prices) // 4)
        actual_test = prices[-test_size:]

        test_predictions = []
        for i in range(test_size):
            test_data = prices[-(SEQUENCE_LENGTH + test_size - i):-(test_size - i)]
            pred = predictor.predict_future(test_data, days=1)
            test_predictions.append(pred[0])

        test_predictions = np.array(test_predictions)
        metrics = predictor.calculate_metrics(actual_test, test_predictions)

        volatility = np.std(prices[-30:])
        confidence_upper = predictions + (volatility * 1.96)
        confidence_lower = predictions - (volatility * 1.96)

        current_price = prices[-1]
        avg_prediction = np.mean(predictions)
        price_change = ((avg_prediction - current_price) / current_price) * 100

        if price_change > 5:
            signal = 'STRONG_BUY'
            signal_text = '🟢 Сильная покупка'
        elif price_change > 2:
            signal = 'BUY'
            signal_text = '🟢 Покупка'
        elif price_change < -5:
            signal = 'STRONG_SELL'
            signal_text = '🔴 Сильная продажа'
        elif price_change < -2:
            signal = 'SELL'
            signal_text = '🔴 Продажа'
        else:
            signal = 'HOLD'
            signal_text = '🟡 Удержание'

        return jsonify({
            'success': True,
            'data': {
                'predictions': predictions.tolist(),
                'confidence_upper': confidence_upper.tolist(),
                'confidence_lower': confidence_lower.tolist(),
                'current_price': float(current_price),
                'predicted_change': float(price_change),
                'signal': signal,
                'signal_text': signal_text,
                'metrics': metrics,
                'days': days
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности API"""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)