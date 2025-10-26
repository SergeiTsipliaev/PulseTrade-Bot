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
            showError('Ошибка загрузки данных');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Ошибка подключения к серверу');
    } finally {
        hideLoading();
    }
}

// Остальные функции (displayCryptoData, displayPriceChart, displayIndicators,
// makePrediction, displayPrediction и т.д.) остаются из предыдущей версии
// ... [здесь должен быть остальной код из предыдущего app.js]

// Вспомогательные функции
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