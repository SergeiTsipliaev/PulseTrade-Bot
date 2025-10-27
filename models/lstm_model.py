import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
import json
import os
from typing import List, Tuple, Optional
import asyncio


class LSTMPredictor:
    def __init__(self, sequence_length: int = 60):
        self.sequence_length = sequence_length
        self.model: Optional[Sequential] = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.is_trained = False

    def create_model(self, input_shape: Tuple[int, int]) -> Sequential:
        """Создание LSTM модели"""
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])

        model.compile(optimizer='adam', loss='mean_squared_error')
        return model

    async def prepare_data(self, prices: List[float]) -> Tuple[np.ndarray, np.ndarray]:
        """Подготовка данных для обучения"""
        prices_array = np.array(prices).reshape(-1, 1)
        scaled_data = self.scaler.fit_transform(prices_array)

        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i - self.sequence_length:i, 0])
            y.append(scaled_data[i, 0])

        return np.array(X), np.array(y)

    async def train(self, prices: List[float], epochs: int = 50, batch_size: int = 32) -> dict:
        """Обучение модели на исторических данных"""
        if len(prices) < self.sequence_length + 100:
            raise ValueError(f"Need at least {self.sequence_length + 100} data points for training")

        X, y = await self.prepare_data(prices)
        X = X.reshape(X.shape[0], X.shape[1], 1)

        split = int(0.8 * len(X))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        self.model = self.create_model((X.shape[1], 1))

        history = self.model.fit(
            X_train, y_train,
            batch_size=batch_size,
            epochs=epochs,
            validation_data=(X_test, y_test),
            verbose=0
        )

        self.is_trained = True

        return {
            'train_loss': history.history['loss'][-1],
            'val_loss': history.history['val_loss'][-1]
        }

    async def predict(self, prices: List[float], future_steps: int = 10) -> List[float]:
        """Прогнозирование будущих цен"""
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained")

        last_sequence = prices[-self.sequence_length:]
        scaled_sequence = self.scaler.transform(np.array(last_sequence).reshape(-1, 1))

        predictions = []
        current_sequence = scaled_sequence.reshape(1, self.sequence_length, 1)

        for _ in range(future_steps):
            next_pred = self.model.predict(current_sequence, verbose=0)
            predictions.append(float(next_pred[0, 0]))
            current_sequence = np.append(current_sequence[:, 1:, :], next_pred.reshape(1, 1, 1), axis=1)

        predictions = self.scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
        return [float(p[0]) for p in predictions]

    async def get_price_prediction(self, symbol: str, historical_data: List[float], days: int = 7) -> dict:
        """Полный процесс прогнозирования для символа"""
        try:
            # Обучение или загрузка модели
            if not self.is_trained:
                await self.train(historical_data)

            # Прогнозирование
            predictions = await self.predict(historical_data, days)
            current_price = historical_data[-1]

            # Расчет изменений
            price_changes = []
            for i, pred_price in enumerate(predictions):
                change = ((pred_price - current_price) / current_price) * 100
                price_changes.append({
                    'day': i + 1,
                    'predicted_price': pred_price,
                    'change_percent': change
                })

            # Рекомендация
            avg_change = sum(p['change_percent'] for p in price_changes) / len(price_changes)

            if avg_change > 2:
                recommendation = "STRONG_BUY"
            elif avg_change > 0:
                recommendation = "BUY"
            elif avg_change > -2:
                recommendation = "HOLD"
            else:
                recommendation = "SELL"

            return {
                'symbol': symbol,
                'current_price': current_price,
                'predictions': price_changes,
                'average_change_percent': avg_change,
                'recommendation': recommendation,
                'confidence': min(95, 100 - abs(avg_change) * 2)
            }

        except Exception as e:
            raise Exception(f"Prediction error: {str(e)}")