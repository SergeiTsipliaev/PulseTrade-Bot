// Загрузка данных криптовалюты
async function loadCryptoData(cryptoId, symbol, name) {
    selectedCrypto = cryptoId;
    showLoading('Загрузка данных...');

    try {
        const response = await fetch(`${API_URL}/crypto/${cryptoId}`);
        const data = await response.json();

        if (data.success) {
            displayCryptoData(data.data, symbol, name);
            document.getElementById('predictBtn').classList.remove('hidden');
        } else {
            showError('Ошибка загрузки данных: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Ошибка подключения к серверу');
    } finally {
        hideLoading();
    }
}

// Отображение данных криптовалюты
function displayCryptoData(data, symbol, name) {
    const crypto = CRYPTOS[selectedCrypto] || { symbol: symbol, name: name };

    // Цена
    const priceCard = document.getElementById('priceCard');
    priceCard.classList.add('show');
    document.getElementById('cryptoName').textContent = `${crypto.name} (${crypto.symbol})`;
    document.getElementById('currentPrice').textContent =
        `$${data.current.price.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;

    const change = data.current.change_24h || 0;
    const changeEl = document.getElementById('priceChange');
    changeEl.textContent = `${change > 0 ? '↑' : '↓'} ${Math.abs(change).toFixed(2)}% за 24ч`;
    changeEl.style.color = change > 0 ? '#10b981' : '#ef4444';

    // График
    displayPriceChart(data.history);

    // Индикаторы
    displayIndicators(data.indicators);

    // Показываем секции
    document.getElementById('indicatorsSection').classList.remove('hidden');
}

// График цены
function displayPriceChart(history) {
    const container = document.getElementById('chartContainer');
    container.classList.add('show');

    const ctx = document.getElementById('priceChart');

    if (priceChart) {
        priceChart.destroy();
    }

    const labels = history.timestamps.map(ts => {
        const date = new Date(ts);
        return `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}`;
    });

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Цена USD',
                data: history.prices,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });

    ctx.style.height = '200px';
}

// Индикаторы
function displayIndicators(indicators) {
    const section = document.getElementById('indicatorsSection');
    section.classList.remove('hidden');

    const grid = document.getElementById('indicatorsGrid');
    grid.innerHTML = '';

    const items = [
        {
            label: 'RSI',
            value: (indicators.rsi || 50).toFixed(1),
            color: getRSIColor(indicators.rsi || 50)
        },
        {
            label: 'MA-7',
            value: `$${(indicators.ma_7 || 0).toFixed(0)}`
        },
        {
            label: 'Волатильность',
            value: `${(indicators.volatility || 0).toFixed(2)}%`,
            color: (indicators.volatility || 0) > 5 ? '#ef4444' : '#10b981'
        },
        {
            label: 'Тренд',
            value: `${(indicators.trend_strength || 0) > 0 ? '+' : ''}${(indicators.trend_strength || 0).toFixed(1)}%`,
            color: (indicators.trend_strength || 0) > 0 ? '#10b981' : '#ef4444'
        }
    ];

    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'indicator-card';
        card.innerHTML = `
            <div class="indicator-label">${item.label}</div>
            <div class="indicator-value" style="color: ${item.color || 'inherit'}">${item.value}</div>
        `;
        grid.appendChild(card);
    });
}

// Функция прогноза
async function makePrediction() {
    if (!selectedCrypto) {
        showError('Сначала выберите криптовалюту');
        return;
    }

    const btn = document.getElementById('predictBtn');
    btn.disabled = true;
    btn.textContent = '🧠 Обучение модели...';

    showLoading('Обучение LSTM нейросети...');

    try {
        const response = await fetch(`${API_URL}/predict/${selectedCrypto}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ days: 7 })
        });

        const data = await response.json();

        if (data.success) {
            displayPrediction(data.data);
        } else {
            showError('Ошибка создания прогноза: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Ошибка подключения к серверу');
    } finally {
        hideLoading();
        btn.disabled = false;
        btn.textContent = '🔮 Сделать прогноз LSTM';
    }
}

// Отображение прогноза
function displayPrediction(prediction) {
    const section = document.getElementById('predictionSection');
    section.classList.add('show');

    // Сигнал
    const signalEmojis = {
        'STRONG_BUY': '🟢',
        'BUY': '🟢',
        'HOLD': '🟡',
        'SELL': '🔴',
        'STRONG_SELL': '🔴'
    };

    document.getElementById('signalEmoji').textContent = signalEmojis[prediction.signal] || '🟡';
    document.getElementById('signalText').textContent = prediction.signal_text;

    const change = prediction.predicted_change;
    const changeEl = document.getElementById('predictedChange');
    changeEl.textContent = `${change > 0 ? '+' : ''}${change.toFixed(2)}%`;
    changeEl.style.color = change > 0 ? '#10b981' : '#ef4444';

    // Метрики
    document.getElementById('accuracy').textContent =
        `${(100 - (prediction.metrics?.mape || 5)).toFixed(1)}%`;
    document.getElementById('rmse').textContent =
        (prediction.metrics?.rmse || 100).toFixed(2);

    // График прогноза
    displayPredictionChart(prediction);

    // Прокрутка к прогнозу
    section.scrollIntoView({ behavior: 'smooth' });
}

// График прогноза
function displayPredictionChart(prediction) {
    const ctx = document.getElementById('predictionChart');

    if (predictionChart) {
        predictionChart.destroy();
    }

    const labels = Array.from({length: prediction.days}, (_, i) => `День ${i + 1}`);

    predictionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Прогноз',
                    data: prediction.predictions,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 4,
                    pointBackgroundColor: '#10b981'
                },
                {
                    label: 'Верхняя граница',
                    data: prediction.confidence_upper || prediction.predictions.map(p => p * 1.05),
                    borderColor: '#ef4444',
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: 'Нижняя граница',
                    data: prediction.confidence_lower || prediction.predictions.map(p => p * 0.95),
                    borderColor: '#3b82f6',
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });

    ctx.style.height = '250px';
}

// Вспомогательные функции
function getRSIColor(rsi) {
    if (rsi > 70) return '#ef4444';
    if (rsi < 30) return '#10b981';
    return '#f59e0b';
}

function showLoading(text) {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('loadingText').textContent = text;
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
}

function showError(message) {
    tg.showAlert(message);
}

// Обновите setupEventListeners
function setupEventListeners() {
    document.getElementById('predictBtn').onclick = makePrediction;
    document.getElementById('allCryptosBtn').onclick = loadAllCryptocurrencies;
    document.getElementById('closeModal').onclick = () => {
        document.getElementById('allCryptosModal').classList.remove('show');
    };
}