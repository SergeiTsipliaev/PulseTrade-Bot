// ======================== КОНФИГУРАЦИЯ ========================
const API_URL = '/api';
let selectedCrypto = null;
let priceChart = null;
let predictionChart = null;
let searchTimeout = null;

// ======================== ИНИЦИАЛИЗАЦИЯ ========================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Приложение загружается...');
    await init();
});

async function init() {
    try {
        await renderCryptoGrid();
        setupEventListeners();
        setupSearch();
        console.log('✅ Приложение готово');
    } catch (error) {
        console.error('❌ Ошибка инициализации:', error);
        showError('Ошибка при загрузке приложения');
    }
}

// ======================== ПОИСК ========================

function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();

        if (searchTimeout) clearTimeout(searchTimeout);

        if (query.length === 0) {
            searchResults.classList.remove('show');
            return;
        }

        searchResults.innerHTML = '<div class="search-result-item">🔍 Поиск...</div>';
        searchResults.classList.add('show');

        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.remove('show');
        }
    });
}

async function performSearch(query) {
    if (query.length < 1) return;

    const searchResults = document.getElementById('searchResults');

    try {
        console.log(`🔍 Поиск: ${query}`);
        const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.success && data.data.length > 0) {
            displaySearchResults(data.data);
        } else {
            searchResults.innerHTML = '<div class="search-result-item">❌ Не найдено</div>';
        }
    } catch (error) {
        console.error('❌ Ошибка поиска:', error);
        searchResults.innerHTML = '<div class="search-result-item">⚠️ Ошибка поиска</div>';
    }
}

function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');

    searchResults.innerHTML = results.map(crypto => `
        <div class="search-result-item" onclick="selectCryptoFromSearch('${crypto.symbol}')">
            <div class="search-result-info">
                <div class="search-result-symbol">${crypto.symbol}</div>
                <div class="search-result-name">${crypto.name}</div>
            </div>
        </div>
    `).join('');
}

async function selectCryptoFromSearch(symbol) {
    selectNewCrypto(symbol);
}

// ======================== ВЫБОР НОВОЙ КРИПТОВАЛЮТЫ ========================

async function selectNewCrypto(symbol) {
    selectedCrypto = symbol;
    document.getElementById('searchResults').classList.remove('show');
    document.getElementById('searchInput').value = '';

    // СКРЫВАЕМ ПРОГНОЗ при смене валюты
    hidePrediction();

    updateCryptoGrid();
    showLoading('Загрузка данных...');
    await loadCryptoData(symbol);
}

function hidePrediction() {
    const predictionSection = document.getElementById('predictionSection');
    predictionSection.classList.remove('show');

    if (predictionChart) {
        predictionChart.destroy();
        predictionChart = null;
    }
}

// ======================== СЕТКА КРИПТОВАЛЮТ ========================

async function renderCryptoGrid() {
    const grid = document.getElementById('cryptoGrid');
    grid.innerHTML = '';

    try {
        const response = await fetch(`${API_URL}/cryptos/all`);
        const data = await response.json();

        if (data.success) {
            const cryptos = data.data.slice(0, 6);

            cryptos.forEach(crypto => {
                const card = document.createElement('div');
                card.className = 'crypto-card';
                card.onclick = () => selectNewCrypto(crypto.symbol);

                card.innerHTML = `
                    <div class="crypto-emoji">${crypto.emoji || '💰'}</div>
                    <div class="crypto-symbol">${crypto.display_name || crypto.symbol}</div>
                `;

                grid.appendChild(card);
            });
        }
    } catch (error) {
        console.error('❌ Ошибка загрузки сетки:', error);
    }
}

function updateCryptoGrid() {
    document.querySelectorAll('.crypto-card').forEach((card) => {
        card.classList.remove('active');
    });

    if (selectedCrypto) {
        document.querySelectorAll('.crypto-card').forEach(card => {
            const symbol = card.querySelector('.crypto-symbol').textContent;
            if (selectedCrypto.includes(symbol)) {
                card.classList.add('active');
            }
        });
    }
}

// ======================== СКЕЛЕТОН ЗАГРУЗКА ========================

function showChartSkeleton() {
    const container = document.getElementById('chartContainer');
    container.classList.add('show');
    container.innerHTML = `
        <div class="chart-skeleton">
            <div class="skeleton-line skeleton-line-1"></div>
            <div class="skeleton-line skeleton-line-2"></div>
            <div class="skeleton-line skeleton-line-3"></div>
        </div>
    `;
}

function showIndicatorsSkeleton() {
    const grid = document.getElementById('indicatorsGrid');
    grid.classList.add('show');
    grid.innerHTML = '';

    for (let i = 0; i < 4; i++) {
        const card = document.createElement('div');
        card.className = 'indicator-card skeleton-indicator';
        card.innerHTML = `
            <div class="skeleton-text skeleton-label"></div>
            <div class="skeleton-text skeleton-value"></div>
        `;
        grid.appendChild(card);
    }
}

// ======================== ЗАГРУЗКА ДАННЫХ ========================

async function loadCryptoData(symbol) {
    console.log(`📊 Загрузка данных для: ${symbol}`);
    selectedCrypto = symbol;
    updateCryptoGrid();

    // Показываем скелеты
    showChartSkeleton();
    showIndicatorsSkeleton();

    try {
        // Параллельная загрузка - берём klines сразу для графика с поддержкой/сопротивлением
        const [cryptoResponse, klinesResponse] = await Promise.all([
            fetch(`${API_URL}/crypto/${symbol}`),
            fetch(`${API_URL}/klines/${symbol}?interval=240&limit=100`)
        ]);

        const data = await cryptoResponse.json();
        const klinesData = await klinesResponse.json();

        if (data.success) {
            displayCryptoData(data.data);

            // Если klines загружены, отображаем расширенный график с поддержкой/сопротивлением
            if (klinesData.success && klinesData.data.length > 0) {
                displayAdvancedChart(klinesData.data, data.data.current.price);
            } else {
                displayPriceChart(data.data.history);
            }

            document.getElementById('predictBtn').classList.remove('hidden');
        } else {
            showError('Ошибка загрузки данных: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('❌ Ошибка:', error);
        showError('Ошибка подключения к серверу');
    } finally {
        hideLoading();
    }
}

function displayCryptoData(data) {
    console.log(`🎯 Отображение данных для: ${data.symbol}`);

    const priceCard = document.getElementById('priceCard');
    priceCard.classList.add('show');

    document.getElementById('cryptoName').textContent = data.symbol;

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

    displayIndicators(data.indicators);

    console.log(`✅ Данные отображены`);
}

// ======================== РАСЧЕТ УРОВНЕЙ ПОДДЕРЖКИ/СОПРОТИВЛЕНИЯ ========================

function calculateSupportResistance(klines) {
    const closes = klines.map(k => parseFloat(k.close));

    // Находим локальные максимумы и минимумы за последние 20 свечей
    const recentKlines = klines.slice(-20);
    const recentCloses = recentKlines.map(k => parseFloat(k.close));

    const resistance = Math.max(...recentCloses);
    const support = Math.min(...recentCloses);

    // Средний уровень
    const midline = (resistance + support) / 2;

    // Дополнительные уровни
    const resistance2 = resistance + (resistance - support) * 0.5;
    const support2 = support - (resistance - support) * 0.5;

    return {
        resistance2,
        resistance,
        midline,
        support,
        support2
    };
}

// ======================== РАСШИРЕННЫЙ ГРАФИК С ПОДДЕРЖКОЙ/СОПРОТИВЛЕНИЕМ ========================

function displayAdvancedChart(klines, currentPrice) {
    const container = document.getElementById('chartContainer');
    container.classList.add('show');

    let ctx = document.getElementById('priceChart');

    // Создаём новый canvas если его нет
    if (!ctx) {
        const canvas = document.createElement('canvas');
        canvas.id = 'priceChart';
        container.innerHTML = '';
        container.appendChild(canvas);
        ctx = canvas;
    }

    if (priceChart) {
        priceChart.destroy();
    }

    // Расчитываем уровни поддержки/сопротивления
    const levels = calculateSupportResistance(klines);

    const labels = klines.map(k => {
        const date = new Date(parseInt(k.timestamp));
        return `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}`;
    });

    const prices = klines.map(k => parseFloat(k.close));

    // Создаем линии для уровней
    const chartData = {
        labels: labels,
        datasets: [
            {
                label: 'Цена (USDT)',
                data: prices,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 4,
                borderWidth: 2,
                pointBackgroundColor: '#667eea',
                order: 2
            },
            {
                label: 'Сопротивление 2',
                data: Array(labels.length).fill(levels.resistance2),
                borderColor: '#ef4444',
                borderDash: [5, 5],
                pointRadius: 0,
                borderWidth: 1.5,
                fill: false,
                order: 3
            },
            {
                label: 'Сопротивление',
                data: Array(labels.length).fill(levels.resistance),
                borderColor: '#f59e0b',
                borderDash: [3, 3],
                pointRadius: 0,
                borderWidth: 2,
                fill: false,
                order: 3
            },
            {
                label: 'Средняя линия',
                data: Array(labels.length).fill(levels.midline),
                borderColor: '#3390ec',
                borderDash: [2, 2],
                pointRadius: 0,
                borderWidth: 1.5,
                fill: false,
                order: 3
            },
            {
                label: 'Поддержка',
                data: Array(labels.length).fill(levels.support),
                borderColor: '#10b981',
                borderDash: [3, 3],
                pointRadius: 0,
                borderWidth: 2,
                fill: false,
                order: 3
            },
            {
                label: 'Поддержка 2',
                data: Array(labels.length).fill(levels.support2),
                borderColor: '#06b6d4',
                borderDash: [5, 5],
                pointRadius: 0,
                borderWidth: 1.5,
                fill: false,
                order: 3
            }
        ]
    };

    priceChart = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        padding: 15,
                        font: { size: 11 },
                        usePointStyle: true
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: (context) => {
                            const label = context.dataset.label || '';
                            const value = formatPrice(context.parsed.y);

                            // Показываем дистанцию от текущей цены
                            const distance = ((context.parsed.y - currentPrice) / currentPrice * 100).toFixed(2);
                            return `${label}: $${value} (${distance > 0 ? '+' : ''}${distance}%)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: (value) => `$${formatNumber(value)}`
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 8
                    }
                }
            }
        }
    });

    ctx.style.height = '300px';

    // Отображаем информацию об уровнях
    displayLevelsInfo(levels, currentPrice);
}

function displayLevelsInfo(levels, currentPrice) {
    const container = document.getElementById('levelsInfo');
    if (!container) return;

    const distance = (level) => {
        const diff = ((level - currentPrice) / currentPrice * 100);
        return diff > 0 ? `+${diff.toFixed(2)}%` : `${diff.toFixed(2)}%`;
    };

    container.innerHTML = `
        <div class="levels-grid">
            <div class="level-item level-resistance2">
                <div class="level-label">R2</div>
                <div class="level-price">$${formatPrice(levels.resistance2)}</div>
                <div class="level-distance">${distance(levels.resistance2)}</div>
            </div>
            <div class="level-item level-resistance">
                <div class="level-label">R</div>
                <div class="level-price">$${formatPrice(levels.resistance)}</div>
                <div class="level-distance">${distance(levels.resistance)}</div>
            </div>
            <div class="level-item level-support">
                <div class="level-label">S</div>
                <div class="level-price">$${formatPrice(levels.support)}</div>
                <div class="level-distance">${distance(levels.support)}</div>
            </div>
            <div class="level-item level-support2">
                <div class="level-label">S2</div>
                <div class="level-price">$${formatPrice(levels.support2)}</div>
                <div class="level-distance">${distance(levels.support2)}</div>
            </div>
        </div>
    `;
}

// ======================== ПРОСТОЙ ГРАФИК (ЕСЛИ KLINES НЕ ЗАГРУЖЕНЫ) ========================

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
                label: 'Цена (USDT)',
                data: history.prices,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 4,
                borderWidth: 2,
                pointBackgroundColor: '#667eea'
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
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    padding: 10,
                    cornerRadius: 8,
                    callbacks: {
                        label: (context) => {
                            return `Цена: $${formatPrice(context.parsed.y)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    ticks: {
                        callback: (value) => `$${formatNumber(value)}`
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 8
                    }
                }
            }
        }
    });

    ctx.style.height = '250px';
}

// ======================== ИНДИКАТОРЫ ========================

function displayIndicators(indicators) {
    const grid = document.getElementById('indicatorsGrid');
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
            label: 'Волатильность',
            value: `${indicators.volatility.toFixed(2)}%`,
            color: indicators.volatility > 5 ? '#ef4444' : '#10b981'
        },
        {
            label: 'Тренд',
            value: `${indicators.trend_strength > 0 ? '+' : ''}${indicators.trend_strength.toFixed(1)}%`,
            color: indicators.trend_strength > 0 ? '#10b981' : '#ef4444'
        }
    ];

    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'indicator-card';
        card.innerHTML = `
            <div class="indicator-label">${item.label}</div>
            <div class="indicator-value" style="color: ${item.color || '#3390ec'}">${item.value}</div>
        `;
        grid.appendChild(card);
    });
}

function getRSIColor(rsi) {
    if (rsi > 70) return '#ef4444';
    if (rsi < 30) return '#10b981';
    return '#f59e0b';
}

// ======================== ПРОГНОЗ ========================

async function makePrediction() {
    if (!selectedCrypto) {
        showError('Сначала выберите криптовалюту');
        return;
    }

    const btn = document.getElementById('predictBtn');
    btn.disabled = true;
    btn.textContent = '🧠 Обучение...';

    showLoading('Обучение нейросети...');

    try {
        const response = await fetch(`${API_URL}/predict/${selectedCrypto}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            displayPrediction(data.data);
        } else {
            showError('Ошибка прогноза: ' + (data.error || 'Неизвестная ошибка'));
        }
    } catch (error) {
        console.error('❌ Ошибка:', error);
        showError('Ошибка подключения к серверу');
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

    document.getElementById('accuracy').textContent = prediction.metrics.accuracy.toFixed(1) + '%';
    document.getElementById('rmse').textContent = `$${formatPrice(prediction.metrics.rmse)}`;

    displayPredictionChart(prediction);

    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function displayPredictionChart(prediction) {
    const ctx = document.getElementById('predictionChart');

    if (predictionChart) {
        predictionChart.destroy();
    }

    const labels = Array.from({ length: prediction.days }, (_, i) => `День ${i + 1}`);

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
                    pointBackgroundColor: '#10b981',
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
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: (context) => {
                            return `${context.dataset.label}: $${formatPrice(context.parsed.y)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    ticks: {
                        callback: (value) => `$${formatNumber(value)}`
                    }
                }
            }
        }
    });

    ctx.style.height = '300px';
}

// ======================== ОБРАБОТЧИКИ ========================

function setupEventListeners() {
    document.getElementById('predictBtn').onclick = makePrediction;
}

// ======================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ========================

function showLoading(text = 'Загрузка...') {
    const loading = document.getElementById('loading');
    document.getElementById('loadingText').textContent = text;
    loading.classList.add('show');
}

function hideLoading() {
    document.getElementById('loading').classList.remove('show');
}

function showError(message) {
    alert(message);
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

console.log('✅ App.js загружен');