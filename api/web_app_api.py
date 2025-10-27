from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os

from services.crypto_service import BybitService
from models.lstm_model import LSTMPredictor
from config import WebConfig

app = Flask(__name__)
CORS(app)

# Global services
bybit_service = BybitService()
predictor = LSTMPredictor()


@app.route('/')
def index():
    return jsonify({
        'message': 'PulseTrade Bot API',
        'version': '1.0.0',
        'endpoints': {
            'search': '/api/v1/crypto/search?q=BTC',
            'info': '/api/v1/crypto/BTC',
            'prediction': '/api/v1/crypto/BTC/predict',
            'portfolio': '/api/v1/portfolio'
        }
    })


@app.route('/api/v1/crypto/search', methods=['GET'])
def search_crypto():
    query = request.args.get('q', '').upper()
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        symbols = loop.run_until_complete(bybit_service.search_symbols(query))
        loop.close()

        return jsonify({
            'success': True,
            'query': query,
            'results': symbols
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/crypto/<symbol>', methods=['GET'])
def get_crypto_info(symbol: str):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ticker = loop.run_until_complete(bybit_service.get_ticker(symbol))
        loop.close()

        return jsonify({
            'success': True,
            'data': ticker
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/crypto/<symbol>/predict', methods=['GET'])
def get_price_prediction(symbol: str):
    days = request.args.get('days', default=7, type=int)

    try:
        # Получаем исторические данные
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        historical_data = loop.run_until_complete(bybit_service.get_klines(symbol))

        # Получаем прогноз
        prediction = loop.run_until_complete(
            predictor.get_price_prediction(symbol, historical_data, days)
        )
        loop.close()

        return jsonify({
            'success': True,
            'data': prediction
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/portfolio', methods=['GET'])
def get_portfolio():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        balance = loop.run_until_complete(bybit_service.get_wallet_balance())
        loop.close()

        return jsonify({
            'success': True,
            'data': balance
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_web_server():
    """Запуск веб-сервера"""
    app.run(
        host=WebConfig.HOST,
        port=WebConfig.PORT,
        debug=WebConfig.DEBUG
    )


if __name__ == '__main__':
    run_web_server()