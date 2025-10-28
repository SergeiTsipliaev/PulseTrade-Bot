const API_URL = '/api';
let searchTimeout = null;

document.addEventListener('DOMContentLoaded', async () => {
    await init();
});

async function init() {
    try {
        await renderCryptoGrid();
        setupSearch();
    } catch (error) {
        console.error('Error:', error);
    }
}

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
        const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.success && data.data.length > 0) {
            displaySearchResults(data.data);
        } else {
            searchResults.innerHTML = '<div class="search-result-item">Не найдено</div>';
        }
    } catch (error) {
        console.error('Error:', error);
        searchResults.innerHTML = '<div class="search-result-item">Ошибка поиска</div>';
    }
}

function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');

    searchResults.innerHTML = results.map(crypto => `
        <div class="search-result-item" onclick="openCrypto('${crypto.symbol}')">
            <div class="search-result-info">
                <div class="search-result-symbol">${crypto.symbol}</div>
                <div class="search-result-name">${crypto.name}</div>
            </div>
        </div>
    `).join('');
}

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
                card.onclick = () => openCrypto(crypto.symbol);

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

function openCrypto(symbol) {
    // Переходим на страницу деталей с параметром символа
    window.location.href = `/crypto-detail.html?symbol=${symbol}`;
}