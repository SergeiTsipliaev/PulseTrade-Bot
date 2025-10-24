import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
import os


class CryptoLSTMPredictor:
    """LSTM модель для прогнозирования цен криптовалют"""

    def __init__(self, sequence_length=60):
        self.sequence_length = sequence_length
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.model = None

    def create_model(self, input_shape):
        """Создание архитектуры LSTM модели"""
        model = Sequential([
            LSTM(units=50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(units=50, return_sequences=True),
            Dropout(0.2),
            LSTM(units=50, return_sequences=False),
            Dropout(0.2),
            Dense(units=25),
            Dense(units=1)
        ])

        model.compile(optimizer='adam', loss='mean_squared_error')
        return model

    def prepare_data(self, prices):
        """Подготовка данных для обучения"""
        # Нормализация данных
        scaled_data = self.scaler.fit_transform(prices.reshape(-1, 1))

        X_train = []
        y_train = []

        for i in range(self.sequence_length, len(scaled_data)):
            X_train.append(scaled_data[i - self.sequence_length:i, 0])
            y_train.append(scaled_data[i, 0])

        X_train = np.array(X_train)
        y_train = np.array(y_train)

        X_train = np.reshape(X_train, (X_train.shape[0], X_train.shape[1], 1))

        return X_train, y_train

    def train(self, prices, epochs=50, batch_size=32):
        """Обучение модели"""
        X_train, y_train = self.prepare_data(prices)

        if self.model is None:
            self.model = self.create_model((X_train.shape[1], 1))

        early_stop = EarlyStopping(monitor='loss', patience=5, restore_best_weights=True)

        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=[early_stop],
            verbose=0
        )

        return history

    def predict_future(self, prices, days=7):
        """Прогнозирование будущих цен"""
        # Подготовка последних данных
        scaled_data = self.scaler.transform(prices.reshape(-1, 1))
        last_sequence = scaled_data[-self.sequence_length:]

        predictions = []
        current_sequence = last_sequence.copy()

        for _ in range(days):
            # Подготовка входных данных
            X_pred = current_sequence.reshape(1, self.sequence_length, 1)

            # Прогноз
            predicted_price = self.model.predict(X_pred, verbose=0)
            predictions.append(predicted_price[0, 0])

            # Обновление последовательности
            current_sequence = np.append(current_sequence[1:], predicted_price)

        # Денормализация прогнозов
        predictions = np.array(predictions).reshape(-1, 1)
        predictions = self.scaler.inverse_transform(predictions)

        return predictions.flatten()

    def calculate_metrics(self, actual_prices, predicted_prices):
        """Расчет метрик точности"""
        mse = np.mean((actual_prices - predicted_prices) ** 2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(actual_prices - predicted_prices))
        mape = np.mean(np.abs((actual_prices - predicted_prices) / actual_prices)) * 100

        return {
            'mse': float(mse),
            'rmse': float(rmse),
            'mae': float(mae),
            'mape': float(mape)
        }

    def save_model(self, filepath):
        """Сохранение модели"""
        if self.model:
            self.model.save(filepath)

    def load_model(self, filepath):
        """Загрузка модели"""
        if os.path.exists(filepath):
            self.model = load_model(filepath)