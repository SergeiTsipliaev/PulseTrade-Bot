const API_URL = '/api';
let priceChart = null;
let predictionChart = null;
let currentCryptoData = null;
let priceUpdateInterval = null;
let selectedCrypto = null;

document.addEventListener('DOMContentLoaded', async () => {
    // Получаем символ из URL параметров
    const urlParams = new URLSearchParams(window.location.search);
    const symbol = urlParams.get('symbol');

    if (!symbol) {
        window.location.href = '/';
        return;
    }

    selectedCrypto = symbol;
    await loadCryptoData(symbol);
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('predictBtn').onclick = makePrediction;
}

async function loadCryptoData(symbol) {
    // Останавливаем предыдущее обновление
    if (priceUpdateInterval) {
        clearInterval(priceUpdateInterval);
        priceUpdateInterval = null;
    }

    showLoading('Загрузка...');

    try {
        const response = await fetch(`${API_URL}/crypto/${symbol}`);
        const data = await response.json();

        if (data.success) {
            currentCryptoData = data.data;
            displayCryptoData(data.data);

            // Запустить реалтайм обновление каждые 10 секунд
            priceUpdateInterval = setInterval(() => {
                updatePriceRealtime(symbol);
            }, 10000);
        } else {
            alert('Ошибка: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка подключения');
    } finally {
        hideLoading();
    }
}

async function updatePriceRealtime(symbol) {
    try {
        const response = await fetch(`${API_URL}/crypto/${symbol}`);
        const data = await response.json();

        if (data.success && data.data) {
            const newData = data.data;

            // Обновляем цену
            const currentPrice = newData.current.price;
            document.getElementById('currentPrice').textContent = `$${formatPrice(currentPrice)}`;

            // Обновляем изменение
            const change = newData.current.change_24h || 0;
            const changeEl = document.getElementById('priceChange');
            const changeIcon = change >= 0 ? '↑' : '↓';
            const changeColor = change >= 0 ? '#10b981' : '#ef4444';

            changeEl.textContent = `${changeIcon} ${Math.abs(change).toFixed(2)}%`;
            changeEl.style.color = changeColor;
            changeEl.style.background = changeColor + '20';

            // Обновляем high/low
            document.getElementById('high24h').textContent = `$${formatPrice(newData.current.high_24h)}`;
            document.getElementById('low24h').textContent = `$${formatPrice(newData.current.low_24h)}`;

            // Обновляем график
            if (priceChart && newData.history && newData.history.prices) {
                const newPrices = newData.history.prices;
                const newTimestamps = newData.history.timestamps;

                const maxPoints = 90;
                const startIdx = Math.max(0, newPrices.length - maxPoints);

                priceChart.data.datasets[0].data = newPrices.slice(startIdx);
                priceChart.data.labels = newTimestamps.slice(startIdx).map(ts => {
                    const date = new Date(ts);
                    return `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}`;
                });

                priceChart.update('none');
            }

            currentCryptoData = newData;
        }
    } catch (error) {
        console.error('Error updating price:', error);
    }
}

function displayCryptoData(data) {
    document.getElementById('cryptoName').textContent = data.symbol.slice(0, -4); // Убираем USDT
    document.getElementById('cryptoSymbol').textContent = data.symbol;

    const currentPrice = data.current.price;
    document.getElementById('currentPrice').textContent = `$${formatPrice(currentPrice)}`;

    const change = data.current.change_24h || 0;
    const changeEl = document.getElementById('priceChange');
    const changeIcon = change >= 0 ? '↑' : '↓';
    const changeColor = change >= 0 ? '#10b981' : '#ef4444';

    changeEl.textContent = `${changeIcon} ${Math.abs(change).toFixed(2)}%`;
    changeEl.style.color = changeColor;
    changeEl.style.background = changeColor + '20';

    document.getElementById('high24h').textContent = `$${formatPrice(data.current.high_24h)}`;
    document.getElementById('low24h').textContent = `$${formatPrice(data.current.low_24h)}`;

    displayPriceChart(data.history);
}

function displayPriceChart(history) {
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
                label: 'Цена (USDT)',
                data: history.prices,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 6,
                borderWidth: 2.5,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        padding: 15,
                        font: { size: 12, weight: '600' },
                        usePointStyle: true
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    padding: 12,
                    cornerRadius: 8,
                    titleFont: { size: 13, weight: 'bold' },
                    bodyFont: { size: 12 },
                    callbacks: {
                        label: (context) => `  Цена: $${formatPrice(context.parsed.y)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: (value) => `$${formatNumber(value)}`,
                        font: { size: 11 }
                    }
                },
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        maxTicksLimit: 8,
                        font: { size: 11 }
                    }
                }
            }
        }
    });

    ctx.style.height = '250px';
}

async function makePrediction() {
    if (!selectedCrypto) return;

    const btn = document.getElementById('predictBtn');
    btn.disabled = true;
    btn.textContent = '🧠 Обучение...';

    showLoading('Обработка...');

    try {
        const response = await fetch(`${API_URL}/predict/${selectedCrypto}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            displayPrediction(data.data);
        } else {
            alert('Ошибка: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка подключения');
    } finally {
        hideLoading();
        btn.disabled = false;
        btn.textContent = '🔮 Прогноз на 7 дней';
    }
}

function displayPrediction(prediction) {
    const section = document.getElementById('predictionSection');
    section.classList.add('show');

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
    changeEl.className = change > 0 ? 'predicted-change positive' : 'predicted-change negative';

    document.getElementById('expectedPrice').textContent = `$${formatPrice(prediction.expected_price)}`;
    document.getElementById('support').textContent = `$${formatPrice(prediction.support)}`;
    document.getElementById('resistance').textContent = `$${formatPrice(prediction.resistance)}`;

    document.getElementById('confidence').textContent = `${prediction.confidence.toFixed(0)}%`;
    document.getElementById('confidenceFill').style.width = `${prediction.confidence}%`;

    document.getElementById('rmse').textContent = `$${formatPrice(prediction.rmse)}`;

    if (currentCryptoData && currentCryptoData.indicators) {
        displayPredictionIndicators(currentCryptoData.indicators);
    }

    displayPredictionChart(prediction);

    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displayPredictionIndicators(indicators) {
    const grid = document.getElementById('predictionIndicators');
    if (!grid) return;

    grid.classList.add('show');
    grid.innerHTML = '';

    const items = [
        {
            label: 'RSI (14)',
            value: indicators.rsi.toFixed(1),
            color: getRSIColor(indicators.rsi)
        },
        {
            label: 'MA-7',
            value: `$${formatPrice(indicators.ma_7)}`
        },
        {
            label: 'MA-25',
            value: `$${formatPrice(indicators.ma_25)}`
        },
        {
            label: 'MA-50',
            value: `$${formatPrice(indicators.ma_50)}`
        },
        {
            label: 'Волатильность',
            value: `${indicators.volatility.toFixed(2)}%`,
            color: indicators.volatility > 5 ? '#ef4444' : '#57d231ff'
        },
        {
            label: 'Тренд',
            value: `${indicators.trend_strength > 0 ? '+' : ''}${indicators.trend_strength.toFixed(1)}%`,
            color: indicators.trend_strength > 0 ? '#20be28ff' : '#e43939e8'
        }
    ];

    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'indicator-card';
        card.innerHTML = `
            <div class="indicator-label">${item.label}</div>
            <div class="indicator-value" style="color: ${item.color || '#2f87dfff'}">${item.value}</div>
        `;
        grid.appendChild(card);
    });
}

function getRSIColor(rsi) {
    if (rsi > 70) return '#ef4444';
    if (rsi < 30) return '#10b981';
    return '#f59e0b';
}

function displayPredictionChart(prediction) {
    const ctx = document.getElementById('predictionChart');

    if (predictionChart) {
        predictionChart.destroy();
    }

    const labels = Array.from({ length: prediction.days }, (_, i) => `День ${i + 1}`);
    const trendColor = prediction.predicted_change > 0 ? '#6cc033ae' : '#dc2828ff';
    const bgColor = prediction.predicted_change > 0 ? 'rgba(171, 238, 130, 0.15)' : 'rgba(239, 68, 68, 0.15)';

    predictionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Прогноз цены',
                    data: prediction.predictions,
                    borderColor: trendColor,
                    backgroundColor: bgColor,
                    tension: 0.45,
                    fill: true,
                    pointRadius: 6,
                    pointBackgroundColor: trendColor,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2.5,
                    pointHoverRadius: 8,
                    borderWidth: 3,
                    borderCapStyle: 'round',
                    borderJoinStyle: 'round'
                },
                {
                    label: 'Текущая цена',
                    data: Array(prediction.days).fill(prediction.current_price),
                    borderColor: '#667eea',
                    borderDash: [5, 5],
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        padding: 15,
                        font: { size: 12, weight: '600' },
                        usePointStyle: true
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0,0,0,0.9)',
                    padding: 12,
                    cornerRadius: 10,
                    titleFont: { size: 13, weight: 'bold' },
                    bodyFont: { size: 12 },
                    borderColor: trendColor,
                    borderWidth: 2,
                    displayColors: true,
                    callbacks: {
                        title: (context) => context[0].label,
                        label: (context) => {
                            const value = context.parsed.y;
                            if (value === null) return '';
                            return `  ${context.dataset.label}: $${formatPrice(value)}`;
                        },
                        afterLabel: (context) => {
                            if (context.datasetIndex === 0) {
                                const current = prediction.current_price;
                                const value = context.parsed.y;
                                const diff = value - current;
                                const percent = (diff / current * 100).toFixed(2);
                                return `  Изменение: ${diff > 0 ? '+' : ''}${percent}%`;
                            }
                        }
                    }
                },
                filler: {
                    propagate: true
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    grid: {
                        color: 'rgba(0,0,0,0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        callback: (value) => `$${formatNumber(value)}`,
                        font: { size: 11 }
                    }
                },
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        font: { size: 11 }
                    }
                }
            }
        }
    });

    ctx.style.height = '350px';
}

function showLoading(text = 'Загрузка...') {
    const loading = document.getElementById('loading');
    document.getElementById('loadingText').textContent = text;
    loading.classList.add('show');
}

function hideLoading() {
    document.getElementById('loading').classList.remove('show');
}

function formatPrice(price) {
    if (price === undefined || price === null) return '0.00';

    if (price >= 1) {
        return parseFloat(price).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    } else {
        return parseFloat(price).toLocaleString('en-US', {
            minimumFractionDigits: 4,
            maximumFractionDigits: 8
        });
    }
}

function formatNumber(num) {
    if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toFixed(0);
}