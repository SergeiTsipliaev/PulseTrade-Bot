// API URL
const API_URL = window.location.origin + '/api';

// Популярные криптовалюты по умолчанию
const POPULAR_CRYPTOS = {
    'BTC': { id: 'BTC', symbol: 'BTC', name: 'Bitcoin', emoji: '₿' },
    'ETH': { id: 'ETH', symbol: 'ETH', name: 'Ethereum', emoji: 'Ξ' },
    'BNB': { id: 'BNB', symbol: 'BNB', name: 'Binance Coin', emoji: '🔶' },
    'SOL': { id: 'SOL', symbol: 'SOL', name: 'Solana', emoji: '◎' },
    'XRP': { id: 'XRP', symbol: 'XRP', name: 'Ripple', emoji: '✕' },
    'ADA': { id: 'ADA', symbol: 'ADA', name: 'Cardano', emoji: '₳' },
    'DOGE': { id: 'DOGE', symbol: 'DOGE', name: 'Dogecoin', emoji: '🐕' },
    'DOT': { id: 'DOT', symbol: 'DOT', name: 'Polkadot', emoji: '●' }
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
}

// Настройка поиска
function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');

    searchInput.addEventListener('input', function(e) {
        const query = e.target.value.trim();

        // Очищаем предыдущий таймаут
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        // Скрываем результаты если запрос пустой
        if (query.length === 0) {
            searchResults.style.display = 'none';
            return;
        }

        // Запускаем поиск с задержкой
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    // Закрываем результаты при клике вне поиска
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });
}

// Поиск криптовалют
async function performSearch(query) {
    if (query.length < 1) return;

    const searchResults = document.getElementById('searchResults');

    try {
        const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.success) {
            displaySearchResults(data.data);
        } else {
            searchResults.style.display = 'none';
        }
    } catch (error) {
        console.error('Ошибка поиска:', error);
        searchResults.style.display = 'none';
    }
}

// Отображение результатов поиска
function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');

    if (results.length === 0) {
        searchResults.innerHTML = '<div class="search-result-item">Ничего не найдено</div>';
        searchResults.style.display = 'block';
        return;
    }

    searchResults.innerHTML = results.map(crypto => `
        <div class="search-result-item" onclick="selectCryptoFromSearch('${crypto.id}', '${crypto.symbol}', '${crypto.name}')">
            <div class="crypto-symbol">${crypto.symbol}</div>
            <div class="crypto-name">${crypto.name}</div>
        </div>
    `).join('');

    searchResults.style.display = 'block';
}

// Выбор криптовалюты из поиска
function selectCryptoFromSearch(id, symbol, name) {
    selectedCrypto = id;

    // Закрываем результаты поиска
    document.getElementById('searchResults').style.display = 'none';
    document.getElementById('searchInput').value = '';

    // Показываем данные
    showLoading('Загрузка данных...');
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

// Отображение всех криптовалют в модальном окне
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

    // Закрываем модальное окно
    document.getElementById('allCryptosModal').classList.remove('show');

    // Показываем данные
    showLoading('Загрузка данных...');
    loadCryptoData(id, symbol, name);
}

// Остальные функции (из предыдущей версии) остаются без изменений
function renderCryptoGrid() {
    const grid = document.getElementById('cryptoGrid');
    grid.innerHTML = '';

    Object.entries(POPULAR_CRYPTOS).forEach(([id, data]) => {
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

function setupEventListeners() {
    document.getElementById('predictBtn').onclick = makePrediction;
    document.getElementById('allCryptosBtn').onclick = loadAllCryptocurrencies;
    document.getElementById('closeModal').onclick = () => {
        document.getElementById('allCryptosModal').classList.remove('show');
    };
}

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

// Вспомогательные функции
function getRSIColor(rsi) {
    if (rsi > 70) return '#ef4444';
    if (rsi < 30) return '#10b981';
    return '#f59e0b';
}

// Запуск приложения
init();