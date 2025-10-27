// API URL
const API_URL = window.location.origin + '/api';

// Популярные криптовалюты
const CRYPTOS = {
    'BTC': { id: 'BTC', symbol: 'BTC', name: 'Bitcoin', emoji: '₿' },
    'ETH': { id: 'ETH', symbol: 'ETH', name: 'Ethereum', emoji: 'Ξ' },
    'BNB': { id: 'BNB', symbol: 'BNB', name: 'Binance Coin', emoji: '🔶' },
    'SOL': { id: 'SOL', symbol: 'SOL', name: 'Solana', emoji: '◎' },
    'XRP': { id: 'XRP', symbol: 'XRP', name: 'Ripple', emoji: '✕' },
    'ADA': { id: 'ADA', symbol: 'ADA', name: 'Cardano', emoji: '₳' },
    'DOGE': { id: 'DOGE', symbol: 'DOGE', name: 'Dogecoin', emoji: '🐕' }
};

let selectedCrypto = null;
let priceChart = null;
let predictionChart = null;
let searchTimeout = null;

// Инициализация Telegram WebApp
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

// Инициализация
function init() {
    renderCryptoGrid();
    setupEventListeners();
    setupSearch();
    console.log("✅ Приложение инициализировано");
}

// Настройка поиска
function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');

    searchInput.addEventListener('input', function(e) {
        const query = e.target.value.trim();

        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        if (query.length === 0) {
            searchResults.style.display = 'none';
            return;
        }

        // Показываем индикатор поиска через Coinbase API
        searchResults.innerHTML = '<div class="search-result-item">🔍 Поиск в Coinbase API...</div>';
        searchResults.style.display = 'block';

        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 500); // Увеличена задержка для API запросов
    });

    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });
}

// Поиск криптовалют через Coinbase API
async function performSearch(query) {
    if (query.length < 1) return;

    const searchResults = document.getElementById('searchResults');

    try {
        console.log(`🔍 Поиск через Coinbase API: ${query}`);
        const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        console.log('🔍 Результаты поиска:', data);

        if (data.success && data.data.length > 0) {
            displaySearchResults(data.data, data.source);
        } else {
            searchResults.innerHTML = '<div class="search-result-item">❌ Ничего не найдено в Coinbase</div>';
            searchResults.style.display = 'block';
        }
    } catch (error) {
        console.error('Ошибка поиска:', error);
        searchResults.innerHTML = '<div class="search-result-item">⚠️ Ошибка подключения к Coinbase API</div>';
        searchResults.style.display = 'block';
    }
}

// Отображение результатов поиска
function displaySearchResults(results, source) {
    const searchResults = document.getElementById('searchResults');

    const sourceText = source === 'coinbase_api' ? '🌐 Coinbase API' :
                       source === 'database' ? '💾 База данных' :
                       source === 'local' ? '📦 Локально' : '';

    let html = `<div class="search-result-item" style="background: var(--tg-theme-hint-color, #eee); font-size: 11px; padding: 6px 16px;">${sourceText}</div>`;

    html += results.map(crypto => `
        <div class="search-result-item" onclick="selectCryptoFromSearch('${crypto.id}', '${crypto.symbol}', '${crypto.name}')">
            <div class="crypto-symbol">${crypto.symbol}</div>
            <div class="crypto-name">${crypto.name}</div>
        </div>
    `).join('');

    searchResults.innerHTML = html;
    searchResults.style.display = 'block';
}

// Выбор криптовалюты из поиска
function selectCryptoFromSearch(id, symbol, name) {
    selectedCrypto = id;

    document.getElementById('searchResults').style.display = 'none';
    document.getElementById('searchInput').value = '';

    showLoading(`Загрузка данных ${symbol} из Coinbase...`);
    loadCryptoData(id, symbol, name);
}

// Загрузка всех криптовалют
async function loadAllCryptocurrencies() {
    showLoading('Загрузка списка...');

    try {
        const response = await fetch(`${API_URL}/cryptos/all`);
        const data = await response.json();

        if (data.success) {
            displayAllCryptocurrencies(data.data);
        } else {
            tg.showAlert('Ошибка загрузки списка');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        tg.showAlert('Ошибка подключения');
    } finally {
        hideLoading();
    }
}

// Отображение всех криптовалют
function displayAllCryptocurrencies(cryptos) {
    const cryptoList = document.getElementById('cryptoList');
    const modal = document.getElementById('allCryptosModal');

    cryptoList.innerHTML = cryptos.map(crypto => `
        <div class="crypto-list-item" onclick="selectCryptoFromList('${crypto.id}', '${crypto.symbol}', '${crypto.name}')">
            <div class="crypto-symbol">${crypto.symbol}</div>
            <div class="crypto-name">${crypto.name}</div>
        </div>
    `).join('');

    modal.classList.add('show');
}

// Выбор криптовалюты из списка
function selectCryptoFromList(id, symbol, name) {
    selectedCrypto = id;

    document.getElementById('allCryptosModal').classList.remove('show');

    showLoading(`Загрузка данных ${symbol}...`);
    loadCryptoData(id, symbol, name);
}

// Отрисовка сетки криптовалют
function renderCryptoGrid() {
    const grid = document.getElementById('cryptoGrid');
    grid.innerHTML = '';

    Object.entries(CRYPTOS).forEach(([id, data]) => {
        const card = document.createElement('div');
        card.className = 'crypto-card';
        card.innerHTML = `
            <div class="crypto-emoji">${data.emoji}</div>
            <div class="crypto-symbol-small">${data.symbol}</div>
        `;
        card.onclick = () => loadCryptoData(data.id, data.symbol, data.name);
        grid.appendChild(card);
    });
}

// Настройка обработчиков
function setupEventListeners() {
    document.getElementById('predictBtn').onclick = makePrediction;
    document.getElementById('allCryptosBtn').onclick = loadAllCryptocurrencies;
    document.getElementById('closeModal').onclick = () => {
        document.getElementById('allCryptosModal').classList.remove('show');
    };
}

// ЗАГРУЗКА ДАННЫХ КРИПТОВАЛЮТЫ
async function loadCryptoData(cryptoId, symbol, name) {
    console.log(`📊 Загрузка данных для: ${cryptoId} (${symbol})`);
    selectedCrypto = cryptoId;
    showLoading(`Получение данных ${symbol} из Coinbase...`);

    try {
        const response = await fetch(`${API_URL}/crypto/${cryptoId}`);
        console.log(`📡 Ответ API:`, response.status);

        const data = await response.json();
        console.log(`📊 Данные получены:`, data);

        if (data.success) {
            displayCryptoData(data.data, symbol, name);
            document.getElementById('predictBtn').classList.remove('hidden');
        } else {
            showError(`Ошибка: ${data.error || 'Криптовалюта не найдена в Coinbase'}`);
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Ошибка подключения к Coinbase API');
    } finally {
        hideLoading();
    }
}

// Отображение данных криптовалюты
function displayCryptoData(data, symbol, name) {
    console.log(`🎯 Отображение данных для: ${symbol}`);

    const crypto = CRYPTOS[selectedCrypto] || { symbol: symbol, name: name };

    // Цена
    const priceCard = document.getElementById('priceCard');
    priceCard.classList.add('show');
    document.getElementById('cryptoName').textContent = `${crypto.name} (${crypto.symbol})`;
    document.getElementById('currentPrice').textContent =
        `$${data.current.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    // Изменение за 24 часа
    const change = data.current.change_24h || 0;
    const changeEl = document.getElementById('priceChange');
    const changeIcon = change >= 0 ? '↑' : '↓';
    const changeColor = change >= 0 ? '#10b981' : '#ef4444';

    changeEl.textContent = `${changeIcon} ${Math.abs(change).toFixed(2)}% за 24ч`;
    changeEl.style.color = changeColor;

    console.log(`💰 Цена: ${data.current.price.toFixed(2)}, Изменение: ${change.toFixed(2)}%`);

    // График
    displayPriceChart(data.history);

    // Индикаторы
    displayIndicators(data.indicators);

    // Показываем секции
    document.getElementById('indicatorsSection').classList.remove('hidden');

    console.log(`✅ Данные отображены успешно`);
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
                pointRadius: 0,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `Цена: ${context.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: function(value) {
                            return ' + value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
                        }
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 10
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
            value: `${(indicators.ma_7 || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
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

// УЛУЧШЕННОЕ ОТОБРАЖЕНИЕ ПРОГНОЗА С ЦИФРАМИ
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

    // ЦИФРЫ ВМЕСТО КВАДРАТИКОВ - Метрики с конкретными значениями
    const metricsGrid = document.getElementById('metricsGrid');
    metricsGrid.innerHTML = '';

    const metrics = [
        {
            label: 'Прогноз (7 дней)',
            value: `${prediction.prediction_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            color: change > 0 ? '#10b981' : change < 0 ? '#ef4444' : '#f59e0b'
        },
        {
            label: 'Верхняя граница',
            value: `${prediction.upper_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            color: '#ef4444'
        },
        {
            label: 'Нижняя граница',
            value: `${prediction.lower_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            color: '#3b82f6'
        },
        {
            label: 'Точность модели',
            value: `${(100 - (prediction.metrics?.mape || 5)).toFixed(1)}%`,
            color: '#10b981'
        }
    ];

    metrics.forEach(metric => {
        const card = document.createElement('div');
        card.className = 'metric-card';
        card.innerHTML = `
            <div class="metric-label">${metric.label}</div>
            <div class="metric-value" style="color: ${metric.color}">${metric.value}</div>
        `;
        metricsGrid.appendChild(card);
    });

    // График прогноза
    displayPredictionChart(prediction);

    // Прокрутка к прогнозу
    section.scrollIntoView({ behavior: 'smooth' });
}

// График прогноза с легендой
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
                    pointRadius: 5,
                    pointBackgroundColor: '#10b981',
                    borderWidth: 3
                },
                {
                    label: 'Верхняя граница (+5%)',
                    data: prediction.confidence_upper,
                    borderColor: '#ef4444',
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 3,
                    pointBackgroundColor: '#ef4444',
                    borderWidth: 2
                },
                {
                    label: 'Нижняя граница (-5%)',
                    data: prediction.confidence_lower,
                    borderColor: '#3b82f6',
                    borderDash: [5, 5],
                    fill: false,
                    pointRadius: 3,
                    pointBackgroundColor: '#3b82f6',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: function(value) {
                            return ' + value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
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
    if (rsi > 70) return '#ef4444';  // Перекупленность
    if (rsi < 30) return '#10b981';  // Перепроданность
    return '#f59e0b';  // Нейтрально
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

// Запуск приложения
init();