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
        # Нормализация данных
        prices_array = np.array(prices).reshape(-1, 1)
        scaled_data = self.scaler.fit_transform(prices_array)

        # Создание последовательностей
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i - self.sequence_length:i, 0])
            y.append(scaled_data[i, 0])

        return np.array(X), np.array(y)

    async def train(self, prices: List[float], epochs: int = 50, batch_size: int = 32) -> dict:
        """Обучение модели на исторических данных"""
        if len(prices) < self.sequence_length + 100:
            raise ValueError(f"Need at least {self.sequence_length + 100} data points for training")

        # Подготовка данных
        X, y = await self.prepare_data(prices)

        # Reshape данных для LSTM
        X = X.reshape(X.shape[0], X.shape[1], 1)

        # Разделение на train/test
        split = int(0.8 * len(X))
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        # Создание и обучение модели
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
            'val_loss': history.history['val_loss'][-1],
            'epochs': len(history.history['loss'])
        }

    async def predict(self, prices: List[float], future_steps: int = 10) -> List[float]:
        """Прогнозирование будущих цен"""
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained")

        # Используем последние sequence_length цен для прогноза
        last_sequence = prices[-self.sequence_length:]
        scaled_sequence = self.scaler.transform(np.array(last_sequence).reshape(-1, 1))

        predictions = []
        current_sequence = scaled_sequence.reshape(1, self.sequence_length, 1)

        for _ in range(future_steps):
            # Прогноз следующего значения
            next_pred = self.model.predict(current_sequence, verbose=0)
            predictions.append(float(next_pred[0, 0]))

            # Обновление последовательности
            current_sequence = np.append(current_sequence[:, 1:, :], next_pred.reshape(1, 1, 1), axis=1)

        # Обратное преобразование к нормальным ценам
        predictions = self.scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
        return [float(p[0]) for p in predictions]

    async def save_model(self, symbol: str, directory: str = "data/models"):
        """Сохранение модели"""
        if not self.is_trained or self.model is None:
            raise ValueError("No model to save")

        os.makedirs(directory, exist_ok=True)
        model_path = os.path.join(directory, f"{symbol}_lstm.h5")
        scaler_path = os.path.join(directory, f"{symbol}_scaler.json")

        # Сохранение модели
        self.model.save(model_path)

        # Сохранение scaler
        scaler_data = {
            'min_': self.scaler.min_.tolist(),
            'scale_': self.scaler.scale_.tolist(),
            'data_min_': self.scaler.data_min_.tolist(),
            'data_max_': self.scaler.data_max_.tolist(),
            'data_range_': self.scaler.data_range_.tolist()
        }

        with open(scaler_path, 'w') as f:
            json.dump(scaler_data, f)

    async def load_model(self, symbol: str, directory: str = "data/models"):
        """Загрузка модели"""
        model_path = os.path.join(directory, f"{symbol}_lstm.h5")
        scaler_path = os.path.join(directory, f"{symbol}_scaler.json")

        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Model for {symbol} not found")

        # Загрузка модели
        self.model = load_model(model_path)

        # Загрузка scaler
        with open(scaler_path, 'r') as f:
            scaler_data = json.load(f)

        self.scaler.min_ = np.array(scaler_data['min_'])
        self.scaler.scale_ = np.array(scaler_data['scale_'])
        self.scaler.data_min_ = np.array(scaler_data['data_min_'])
        self.scaler.data_max_ = np.array(scaler_data['data_max_'])
        self.scaler.data_range_ = np.array(scaler_data['data_range_'])

        self.is_trained = True