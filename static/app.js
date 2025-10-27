// ======================== КОНФИГУРАЦИЯ ========================
const API_URL = '/api';
let selectedCrypto = null;
let priceChart = null;
let predictionChart = null;
let searchTimeout = null;
let currentCryptoData = null;

// ======================== ИНИЦИАЛИЗАЦИЯ ========================

document.addEventListener('DOMContentLoaded', async () => {
    await init();
});

async function init() {
    try {
        await renderCryptoGrid();
        setupEventListeners();
        setupSearch();
    } catch (error) {
        console.error('Error:', error);
        showError('Error loading app');
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

        searchResults.innerHTML = '<div class="search-result-item">🔍 Searching...</div>';
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
        const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.success && data.data.length > 0) {
            displaySearchResults(data.data);
        } else {
            searchResults.innerHTML = '<div class="search-result-item">Not found</div>';
        }
    } catch (error) {
        console.error('Error:', error);
        searchResults.innerHTML = '<div class="search-result-item">Search error</div>';
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
    selectedCrypto = symbol;
    document.getElementById('searchResults').classList.remove('show');
    document.getElementById('searchInput').value = '';

    showLoading('Loading...');
    await loadCryptoData(symbol);
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
                card.onclick = () => {
                    selectedCrypto = crypto.symbol;
                    updateCryptoGrid();
                    showLoading('Loading...');
                    loadCryptoData(crypto.symbol);
                };

                card.innerHTML = `
                    <div class="crypto-emoji">${crypto.emoji || '💰'}</div>
                    <div class="crypto-symbol">${crypto.display_name || crypto.symbol}</div>
                `;

                grid.appendChild(card);
            });
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

function updateCryptoGrid() {
    document.querySelectorAll('.crypto-card').forEach((card, index) => {
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

// ======================== ЗАГРУЗКА ДАННЫХ ========================

async function loadCryptoData(symbol) {
    selectedCrypto = symbol;
    updateCryptoGrid();

    try {
        const response = await fetch(`${API_URL}/crypto/${symbol}`);
        const data = await response.json();

        if (data.success) {
            currentCryptoData = data.data;
            displayCryptoData(data.data);
            document.getElementById('predictBtn').classList.remove('hidden');
        } else {
            showError('Error: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Connection error');
    } finally {
        hideLoading();
    }
}

function displayCryptoData(data) {
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

    displayPriceChart(data.history);
}

// ======================== ГРАФИК ЦЕНЫ ========================

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
                label: 'Price (USDT)',
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
                            return `Price: $${formatPrice(context.parsed.y)}`;
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

// ======================== ПРОГНОЗ ========================

async function makePrediction() {
    if (!selectedCrypto) {
        showError('Select crypto first');
        return;
    }

    const btn = document.getElementById('predictBtn');
    btn.disabled = true;
    btn.textContent = '🧠 Learning...';

    showLoading('Processing...');

    try {
        const response = await fetch(`${API_URL}/predict/${selectedCrypto}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success) {
            displayPrediction(data.data);
        } else {
            showError('Error: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Connection error');
    } finally {
        hideLoading();
        btn.disabled = false;
        btn.textContent = '🔮 Predict 7 days';
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

    document.getElementById('rmse').textContent = `$${formatPrice(prediction.metrics.rmse)}`;

    // Новые данные
    document.getElementById('expectedPrice').textContent = `$${formatPrice(prediction.expected_price)}`;
    document.getElementById('support').textContent = `$${formatPrice(prediction.support)}`;
    document.getElementById('resistance').textContent = `$${formatPrice(prediction.resistance)}`;
    document.getElementById('actionValue').textContent = prediction.action;
    document.getElementById('confidence').textContent = `${prediction.confidence.toFixed(0)}%`;
    
    // Обновляем ширину confidence bar
    document.getElementById('confidenceFill').style.width = `${prediction.confidence}%`;

    const actionEl = document.getElementById('actionValue');
    if (prediction.action === 'BUY') {
        actionEl.style.color = '#10b981';
    } else if (prediction.action === 'SELL') {
        actionEl.style.color = '#ef4444';
    } else {
        actionEl.style.color = '#f59e0b';
    }

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
            label: 'Volatility',
            value: `${indicators.volatility.toFixed(2)}%`,
            color: indicators.volatility > 5 ? '#ef4444' : '#10b981'
        },
        {
            label: 'Trend',
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

function displayPredictionChart(prediction) {
    const ctx = document.getElementById('predictionChart');

    if (predictionChart) {
        predictionChart.destroy();
    }

    const labels = Array.from({ length: prediction.days }, (_, i) => `Day ${i + 1}`);

    predictionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Prediction',
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

function showLoading(text = 'Loading...') {
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