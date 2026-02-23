// API Configuration
const API_URL = window.location.origin;

// State
let currentFilter = 'all';
let currentPublisherFilter = '';   // FIX #20
let currentSort = 'alpha';         // FIX #13
let currentSeriesId = null;
let allSeries = [];
let searchTimeout = null;
let currentSeries = null;

// Paginação
let currentPage = 1;
let perPage = 32;
let totalPages = 1;
let totalItems = 0;
let paginationInfo = null;

// Pilha de ações para desfazer — FIX #11: expandida
let undoStack = [];

// FIX #14: Dark mode
let isDarkMode = localStorage.getItem('darkMode') === 'true';

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    // FIX #14: aplicar dark mode salvo
    if (isDarkMode) document.body.classList.add('dark-mode');

    loadSeries();
    loadStats();
    initScrollBehavior();

    // FIX #20: popular filtro de editoras após carregar
    // (será chamado dentro de loadSeries ao final)

    // Restaurar view de detalhes se estava aberta
    const savedView     = localStorage.getItem('currentView');
    const savedSeriesId = localStorage.getItem('currentSeriesId');
    if (savedView === 'detail' && savedSeriesId) {
        setTimeout(() => showSeriesDetail(parseInt(savedSeriesId)), 100);
    }
});

// ==================== SCROLL BEHAVIOR ====================

let lastScrollTop = 0;

function initScrollBehavior() {
    const header        = document.getElementById('main-header');
    const scrollToTopBtn = document.getElementById('scroll-to-top');
    let ticking = false;

    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
                if (currentScroll > 300) scrollToTopBtn.classList.add('visible');
                else scrollToTopBtn.classList.remove('visible');

                if (window.innerWidth <= 768) {
                    if (currentScroll > lastScrollTop && currentScroll > 100)
                        header.classList.add('header-compact-scroll');
                    else if (currentScroll < lastScrollTop)
                        header.classList.remove('header-compact-scroll');
                    if (currentScroll < 50)
                        header.classList.remove('header-compact-scroll');
                }
                lastScrollTop = currentScroll <= 0 ? 0 : currentScroll;
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            header.classList.remove('header-compact-scroll');
            lastScrollTop = 0;
        }
    });
}

function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// FIX #14: Dark mode toggle
function toggleDarkMode() {
    isDarkMode = !isDarkMode;
    document.body.classList.toggle('dark-mode', isDarkMode);
    localStorage.setItem('darkMode', isDarkMode);
    const btn = document.getElementById('btn-dark-mode');
    if (btn) btn.textContent = isDarkMode ? '☀️' : '🌙';
}

// Função para obter o label do tipo de série
function getSeriesTypeLabel(seriesType) {
    const types = {
        'finalizada':    { text: 'Finalizada',     class: 'type-finalizada', emoji: '✓'  },
        'em_andamento':  { text: 'Em Andamento',   class: 'type-andamento',  emoji: '📖' },
        'lancamento':    { text: 'Lançamento',     class: 'type-lancamento', emoji: '🆕' },
        'edicao_especial': { text: 'Edição Especial', class: 'type-especial', emoji: '⭐' },
        'saga':          { text: 'Saga',           class: 'type-saga',       emoji: '🎭' }
    };
    return types[seriesType] || types['em_andamento'];
}

function createSeriesTypeBadge(seriesType) {
    const typeInfo = getSeriesTypeLabel(seriesType);
    return `<span class="series-type-badge ${typeInfo.class}">${typeInfo.emoji} ${typeInfo.text}</span>`;
}

// ==================== API ====================

async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers: { 'Content-Type': 'application/json', ...options.headers },
        });

        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}`;
            try { const err = await response.json(); errorMessage = err.detail || errorMessage; } catch {}
            throw new Error(errorMessage);
        }
        return await response.json();
    } catch (error) {
        console.error('❌ API Error:', error);
        throw error;
    }
}

// ==================== LOADING (FIX #10) ====================

function showLoading() {
    const grid      = document.getElementById('series-grid');
    const emptyState = document.getElementById('empty-state');
    if (emptyState) emptyState.style.display = 'none';
    if (grid) {
        grid.style.display = 'grid';
        // Gerar 8 skeleton cards
        grid.innerHTML = Array(8).fill(0).map(() => `
            <div class="comic-card skeleton-card">
                <div class="skeleton-cover"></div>
                <div class="skeleton-body">
                    <div class="skeleton-line skeleton-line-short"></div>
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line skeleton-line-short"></div>
                </div>
            </div>
        `).join('');
    }
}

function hideLoading() {
    // O displaySeries() vai substituir o grid, não precisa fazer nada aqui
}

// ==================== LOAD ====================

async function loadSeries(filterQuery = '', page = 1) {
    try {
        showLoading(); // FIX #10
        let perPageToUse = filterQuery ? perPage : 1000;
        let endpoint = `/series?page=${page}&per_page=${perPageToUse}`;
        if (filterQuery) endpoint += `&search=${encodeURIComponent(filterQuery)}`;

        const response = await fetchAPI(endpoint);

        if (response.items && response.pagination) {
            allSeries    = response.items;
            paginationInfo = response.pagination;
            currentPage  = response.pagination.page;
            totalPages   = response.pagination.total_pages;
            totalItems   = response.pagination.total_items;
        } else {
            allSeries  = response;
            totalPages = 1;
            totalItems = allSeries.length;
        }

        // FIX #20: atualizar lista de editoras
        updatePublisherFilter();

        displaySeries();
        updatePaginationControls();
    } catch (error) {
        console.error('Error loading series:', error);
        alert('Erro ao carregar HQs. Verifique se o servidor está online.');
        showEmptyState();
    }
}

async function loadStats() {
    try {
        const stats = await fetchAPI('/stats');

        document.getElementById('stat-total').textContent      = stats.total      || 0;
        document.getElementById('stat-para-ler').textContent   = stats.para_ler   || 0;
        document.getElementById('stat-lendo').textContent      = stats.lendo      || 0;
        document.getElementById('stat-concluidas').textContent = stats.concluidas || stats.concluida || 0;

        // FIX #15: atualizar stat de sagas
        const sagaEl = document.getElementById('stat-sagas');
        if (sagaEl) sagaEl.textContent = stats.sagas || 0;

        updateMobileStats();
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// ==================== FIX #20: FILTRO POR EDITORA ====================

function updatePublisherFilter() {
    const select = document.getElementById('publisher-filter');
    if (!select) return;

    const publishers = [...new Set(
        allSeries.map(s => s.publisher).filter(Boolean)
    )].sort((a, b) => a.localeCompare(b, 'pt-BR'));

    const current = select.value;
    select.innerHTML = '<option value="">📚 Todas as editoras</option>';
    publishers.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = p;
        if (p === current) opt.selected = true;
        select.appendChild(opt);
    });
}

function filterByPublisher(value) {
    currentPublisherFilter = value;
    currentPage = 1;
    displaySeries();
    updatePaginationControls();
}

// ==================== FIX #13: ORDENAÇÃO ====================

function sortSeries(value) {
    currentSort = value;
    currentPage = 1;
    displaySeries();
    updatePaginationControls();
}

function applySorting(series) {
    const arr = [...series];
    switch (currentSort) {
        case 'alpha':
            return arr.sort((a, b) => a.title.localeCompare(b.title, 'pt-BR', { sensitivity: 'base' }));
        case 'alpha_desc':
            return arr.sort((a, b) => b.title.localeCompare(a.title, 'pt-BR', { sensitivity: 'base' }));
        case 'progress':
            return arr.sort((a, b) => {
                const pa = a.total_issues > 0 ? a.read_issues / a.total_issues : 0;
                const pb = b.total_issues > 0 ? b.read_issues / b.total_issues : 0;
                return pb - pa;
            });
        case 'progress_asc':
            return arr.sort((a, b) => {
                const pa = a.total_issues > 0 ? a.read_issues / a.total_issues : 0;
                const pb = b.total_issues > 0 ? b.read_issues / b.total_issues : 0;
                return pa - pb;
            });
        case 'publisher':
            return arr.sort((a, b) =>
                (a.publisher || '').localeCompare(b.publisher || '', 'pt-BR', { sensitivity: 'base' })
            );
        case 'date_added':
            return arr.sort((a, b) => (b.date_added || '').localeCompare(a.date_added || ''));
        case 'almost_done':
            return arr.sort((a, b) => {
                const ra = a.total_issues > 0 ? a.read_issues / a.total_issues : 0;
                const rb = b.total_issues > 0 ? b.read_issues / b.total_issues : 0;
                // Quase concluídas primeiro (entre 50% e 99%)
                const inRangeA = ra >= 0.5 && ra < 1 ? 1 : 0;
                const inRangeB = rb >= 0.5 && rb < 1 ? 1 : 0;
                if (inRangeA !== inRangeB) return inRangeB - inRangeA;
                return rb - ra;
            });
        default:
            return arr.sort((a, b) => a.title.localeCompare(b.title, 'pt-BR', { sensitivity: 'base' }));
    }
}

// ==================== DISPLAY ====================

function displaySeries() {
    const grid       = document.getElementById('series-grid');
    const emptyState = document.getElementById('empty-state');

    // Filtrar por status
    let filteredSeries = allSeries;
    if (currentFilter === 'para_ler') {
        filteredSeries = allSeries.filter(s => s.read_issues === 0);
    } else if (currentFilter === 'lendo') {
        filteredSeries = allSeries.filter(s => s.read_issues > 0 && s.read_issues < s.total_issues);
    } else if (currentFilter === 'concluida') {
        filteredSeries = allSeries.filter(s => s.read_issues >= s.total_issues && s.total_issues > 0);
    } else if (currentFilter === 'saga') {
        filteredSeries = allSeries.filter(s => s.series_type === 'saga');
    }

    // FIX #20: filtrar por editora
    if (currentPublisherFilter) {
        filteredSeries = filteredSeries.filter(s => s.publisher === currentPublisherFilter);
    }

    // FIX #13: aplicar ordenação
    filteredSeries = applySorting(filteredSeries);

    // FIX #9: REMOVIDO console.table com todos os dados

    if (filteredSeries.length === 0) {
        showEmptyState();
        totalItems = 0;
        totalPages = 1;
        updatePaginationControls();
        return;
    }

    // Paginação local
    totalItems = filteredSeries.length;
    totalPages = Math.ceil(totalItems / perPage);
    if (totalPages < 1) totalPages = 1;
    if (currentPage > totalPages) currentPage = 1;

    const startIdx  = (currentPage - 1) * perPage;
    const pageItems = filteredSeries.slice(startIdx, startIdx + perPage);

    emptyState.style.display = 'none';
    grid.style.display = 'grid';
    grid.innerHTML = '';

    pageItems.forEach(series => {
        const card = createSeriesCard(series);
        grid.appendChild(card);
    });

    updatePaginationControls();
}

function createSeriesCard(series) {
    const card = document.createElement('div');
    card.className = 'comic-card';

    const progress = series.total_issues > 0
        ? Math.round((series.read_issues / series.total_issues) * 100)
        : 0;

    let statusClass = 'para-ler';
    let statusText  = 'Para Ler';
    if (series.read_issues >= series.total_issues && series.total_issues > 0) {
        statusClass = 'concluida'; statusText = 'Concluída';
    } else if (series.read_issues > 0) {
        statusClass = 'lendo'; statusText = 'Lendo';
    }

    const escapedTitle = series.title.replace(/'/g, "\\'").replace(/"/g, '&quot;');
    const typeInfo     = getSeriesTypeLabel(series.series_type);
    const typeBadge    = `<span class="series-type-badge ${typeInfo.class}">${typeInfo.emoji} ${typeInfo.text}</span>`;

    // FIX #16: mostrar anos se existirem
    const yearStr = series.year_start
        ? `<p class="comic-year">📅 ${series.year_start}${series.year_end ? ' – ' + series.year_end : ''}</p>`
        : '';

    card.innerHTML = `
        <div class="comic-cover">
            <div class="series-type-overlay">${typeBadge}</div>
            ${series.cover_url
                ? `<img src="${series.cover_url}" alt="${series.title}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                   <div class="comic-cover-placeholder" style="display:none;">📖</div>`
                : `<div class="comic-cover-placeholder">📖</div>`
            }
            <div class="cover-progress-footer">
                <div class="cover-prog-pct">${series.read_issues} / ${series.total_issues} &middot; ${progress}%</div>
                <div class="cover-prog-track">
                    <div class="cover-prog-fill" style="width: ${progress}%"></div>
                </div>
            </div>
        </div>
        <div class="comic-info">
            <h3 class="comic-title">${series.title}</h3>
            ${series.author    ? `<p class="comic-author">✍️ ${series.author}</p>`    : ''}
            ${series.publisher ? `<p class="comic-publisher">📚 ${series.publisher}</p>` : ''}
            ${yearStr}
            <div class="comic-stats">
                <span>Lendo: <strong>${series.read_issues}</strong></span>
                <span>Baixadas: <strong>${series.downloaded_issues}</strong></span>
                <span>Total: <strong>${series.total_issues}</strong></span>
            </div>
            <div class="comic-status-row">
                <div class="comic-status ${statusClass}">${statusText}</div>
                <div class="comic-actions">
                    <button class="btn-icon-small btn-edit"   data-series-id="${series.id}" title="Editar HQ">✏️</button>
                    <button class="btn-icon-small btn-delete" data-series-id="${series.id}" data-series-title="${escapedTitle}" title="Excluir HQ">🗑️</button>
                </div>
            </div>
        </div>
    `;

    card.addEventListener('click', (e) => {
        if (!e.target.closest('.btn-icon-small')) showSeriesDetail(series.id);
    });
    card.querySelector('.btn-edit').addEventListener('click', (e) => {
        e.stopPropagation(); editSeries(series.id);
    });
    card.querySelector('.btn-delete').addEventListener('click', (e) => {
        e.stopPropagation(); deleteSeries(series.id, series.title);
    });

    return card;
}

function showEmptyState() {
    document.getElementById('series-grid').style.display = 'none';
    document.getElementById('empty-state').style.display = 'flex';
}

// ==================== DETAIL VIEW ====================

async function showSeriesDetail(seriesId) {
    currentSeriesId = seriesId;
    localStorage.setItem('currentView', 'detail');
    localStorage.setItem('currentSeriesId', seriesId);

    document.getElementById('home-view').style.display = 'none';
    const filtersSection = document.getElementById('filters-section');
    filtersSection.style.display = 'none';
    filtersSection.style.visibility = 'hidden';
    document.getElementById('detail-view').style.display = 'block';
    document.getElementById('btn-back').style.display = 'inline-flex';
    document.body.classList.add('detail-page');
    window.scrollTo({ top: 0, behavior: 'smooth' });

    await loadSeriesDetail(seriesId);
}

async function loadSeriesDetail(seriesId) {
    try {
        const series = await fetchAPI(`/series/${seriesId}`);
        currentSeries = series;

        document.getElementById('detail-title').textContent = series.title;

        const typeBadgeEl  = document.getElementById('detail-type-badge');
        const typeInfo     = getSeriesTypeLabel(series.series_type);
        typeBadgeEl.innerHTML  = `<span class="series-type-badge ${typeInfo.class}">${typeInfo.emoji} ${typeInfo.text}</span>`;
        typeBadgeEl.style.display    = 'block';
        typeBadgeEl.style.marginBottom = '0.75rem';

        const authorEl    = document.getElementById('detail-author');
        const publisherEl = document.getElementById('detail-publisher');
        if (series.author) { authorEl.textContent = `✍️ ${series.author}`; authorEl.style.display = 'block'; }
        else authorEl.style.display = 'none';
        if (series.publisher) { publisherEl.textContent = `📚 ${series.publisher}`; publisherEl.style.display = 'block'; }
        else publisherEl.style.display = 'none';

        // FIX #16: anos
        const yearEl = document.getElementById('detail-years');
        if (yearEl) {
            if (series.year_start) {
                yearEl.textContent = `📅 ${series.year_start}${series.year_end ? ' – ' + series.year_end : ''}`;
                yearEl.style.display = 'block';
            } else {
                yearEl.style.display = 'none';
            }
        }

        // Edições da saga
        const sagaEditionsDisplay = document.getElementById('saga-editions-display');
        const sagaEditionsList    = document.getElementById('saga-editions-list');
        if (series.series_type === 'saga' && series.saga_editions) {
            const editions = series.saga_editions.split('\n').filter(e => e.trim());
            sagaEditionsList.innerHTML = editions.map(e =>
                `<div class="saga-edition-item">• ${e.trim()}</div>`
            ).join('');
            sagaEditionsDisplay.style.display = 'block';
        } else {
            sagaEditionsDisplay.style.display = 'none';
        }

        // Capa
        const coverImg         = document.getElementById('detail-cover');
        const coverPlaceholder = coverImg.nextElementSibling;
        if (series.cover_url) {
            coverImg.src = series.cover_url;
            coverImg.style.display = 'block';
            coverPlaceholder.style.display = 'none';
        } else {
            coverImg.style.display = 'none';
            coverPlaceholder.style.display = 'flex';
        }

        // Progresso
        const progress = series.total_issues > 0
            ? Math.round((series.read_issues / series.total_issues) * 100) : 0;
        document.getElementById('detail-progress').textContent =
            `${series.read_issues}/${series.total_issues} edições (${progress}%)`;
        document.getElementById('detail-progress-bar').style.width = `${progress}%`;
        const coverProgBar = document.getElementById('detail-cover-prog-bar');
        if (coverProgBar) coverProgBar.style.width = `${progress}%`;
        document.getElementById('detail-reading').textContent    = series.read_issues;
        document.getElementById('detail-downloaded').textContent = series.downloaded_issues;
        document.getElementById('detail-total').textContent      = series.total_issues;

        // Stats saga
        const sagaDivisionStats = document.getElementById('saga-division-stats');
        if (series.series_type === 'saga' && (series.main_issues || series.tie_in_issues)) {
            document.getElementById('detail-main-issues').textContent    = series.main_issues   || 0;
            document.getElementById('detail-tie-in-issues').textContent  = series.tie_in_issues || 0;
            sagaDivisionStats.style.display = 'flex';
        } else {
            sagaDivisionStats.style.display = 'none';
        }

        // Botão notas
        const btnViewNotes = document.getElementById('btn-view-notes');
        if (series.notes && series.notes.trim()) btnViewNotes.style.display = 'flex';
        else btnViewNotes.style.display = 'none';

        // Carregar edições
        const issues = await fetchAPI(`/series/${seriesId}/issues`);
        displayIssues(issues);
        updateUndoButton();

    } catch (error) {
        console.error('❌ Erro ao carregar detalhes:', error);
        alert('Erro ao carregar detalhes da série');
        goToHome();
    }
}

function displayIssues(issues) {
    const issuesList = document.getElementById('issues-list');
    const emptyIssues = document.getElementById('empty-issues');

    if (!currentSeries) {
        issuesList.innerHTML = '';
        emptyIssues.style.display = 'flex';
        return;
    }

    emptyIssues.style.display = 'none';
    issuesList.innerHTML = '';

    const issuesMap = {};
    issues.forEach(issue => { issuesMap[issue.issue_number] = issue; });

    for (let i = 1; i <= currentSeries.total_issues; i++) {
        let issue = issuesMap[i] || {
            id: null, issue_number: i,
            is_read: false, is_downloaded: false,
            series_id: currentSeriesId, date_read: null
        };
        issuesList.appendChild(createIssueCard(issue));
    }
}

function createIssueCard(issue) {
    const badge = document.createElement('div');

    let colorClass = 'issue-faltante';
    let icon = '❌';
    if (issue.is_read)        { colorClass = 'issue-lida';   icon = '✅'; }
    else if (issue.is_downloaded) { colorClass = 'issue-baixada'; icon = '📥'; }

    badge.className = `issue-badge ${colorClass}`;

    // FIX #17: mostrar data de leitura no title se disponível
    let titleText = issue.is_read ? 'Lida' : (issue.is_downloaded ? 'Baixada' : 'Não baixada');
    if (issue.is_read && issue.date_read) {
        try {
            const d = new Date(issue.date_read);
            titleText += ` em ${d.toLocaleDateString('pt-BR')}`;
        } catch {}
    }
    badge.title = titleText;

    badge.innerHTML = `
        <div class="issue-badge-number">#${issue.issue_number}</div>
        <div class="issue-badge-icon">${icon}</div>
        ${issue.id ? '<button class="issue-badge-undownload" title="Marcar como não baixada">↩️</button>' : ''}
        ${issue.id ? '<button class="issue-badge-delete" title="Deletar">×</button>' : ''}
    `;

    badge.addEventListener('click', (e) => {
        if (e.target.closest('.issue-badge-delete') || e.target.closest('.issue-badge-undownload')) return;
        if (!issue.id) addIssueDownloaded(issue.issue_number);
        else toggleIssueRead(issue.id, !issue.is_read);
    });

    if (issue.id) {
        const undownloadBtn = badge.querySelector('.issue-badge-undownload');
        if (undownloadBtn) undownloadBtn.addEventListener('click', (e) => {
            e.stopPropagation(); marcarComoNaoBaixada(issue.id, issue.issue_number);
        });
        const deleteBtn = badge.querySelector('.issue-badge-delete');
        if (deleteBtn) deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation(); deleteIssue(issue.id, issue.issue_number);
        });
    }

    return badge;
}

function goToHome() {
    localStorage.removeItem('currentView');
    localStorage.removeItem('currentSeriesId');

    document.getElementById('detail-view').style.display = 'none';
    document.getElementById('btn-back').style.display    = 'none';
    document.body.classList.remove('detail-page');
    document.getElementById('home-view').style.display   = 'block';

    const filtersSection = document.getElementById('filters-section');
    filtersSection.style.display     = 'flex';
    filtersSection.style.visibility  = 'visible';
    filtersSection.style.alignItems  = 'center';
    filtersSection.style.justifyContent = 'space-between';

    window.scrollTo({ top: 0, behavior: 'smooth' });
    currentSeriesId = null;
    currentSeries   = null;

    loadSeries();
    loadStats();
}

// ==================== FILTROS ====================

function filterSeries(filter, element) {
    currentFilter = filter;
    currentPage   = 1;

    document.querySelectorAll('.filter-tab, .filter-tab-compact').forEach(t => t.classList.remove('active'));
    const targetElement = element || (typeof event !== 'undefined' ? event.target : null);
    if (targetElement) targetElement.classList.add('active');

    displaySeries();
    updatePaginationControls();
}

// ==================== BUSCA ====================

function handleSearch() {
    const query    = document.getElementById('search-input').value;
    const clearBtn = document.getElementById('search-clear');
    clearBtn.style.display = query ? 'block' : 'none';

    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        currentPage = 1;
        loadSeries(query, 1);
    }, 300);
}

function clearSearch() {
    document.getElementById('search-input').value  = '';
    document.getElementById('search-clear').style.display = 'none';
    currentPage = 1;
    loadSeries('', 1);
}

// ==================== UNDO (FIX #11) ====================

function addToUndoStack(action) {
    undoStack.push(action);
    if (undoStack.length > 20) undoStack.shift();
    updateUndoButton();
}

function updateUndoButton() {
    const undoBtn = document.getElementById('btn-undo');
    if (undoBtn) {
        undoBtn.disabled    = undoStack.length === 0;
        undoBtn.textContent = `↶${undoStack.length > 0 ? ` (${undoStack.length})` : ''}`;
    }
}

async function desfazerUltimaAcao() {
    if (undoStack.length === 0) { alert('Nenhuma ação para desfazer'); return; }
    const lastAction = undoStack.pop();
    try {
        switch (lastAction.type) {
            case 'add_issue':
                await fetchAPI(`/series/${lastAction.seriesId}/issues/${lastAction.issueId}`, { method: 'DELETE' });
                alert(`Edição #${lastAction.issueNumber} removida`);
                break;
            case 'increase_total': {
                const series = await fetchAPI(`/series/${lastAction.seriesId}`);
                await fetchAPI(`/series/${lastAction.seriesId}`, {
                    method: 'PUT',
                    body: JSON.stringify({ ...series, total_issues: lastAction.oldTotal })
                });
                alert(`Total voltou de ${lastAction.newTotal} para ${lastAction.oldTotal}`);
                break;
            }
            // FIX #11: undo de toggle de leitura
            case 'toggle_read':
                await fetchAPI(`/series/${lastAction.seriesId}/issues/${lastAction.issueId}`, {
                    method: 'PATCH',
                    body: JSON.stringify({ is_read: lastAction.oldState })
                });
                alert(`Edição #${lastAction.issueNumber} voltou ao estado anterior`);
                break;
            // FIX #11: undo de deletar série
            case 'delete_series':
                alert('Não é possível desfazer a exclusão de uma série.');
                break;
        }
        updateUndoButton();
        if (currentSeriesId) await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
    } catch (error) {
        console.error('❌ Erro ao desfazer:', error);
        alert('Erro ao desfazer: ' + error.message);
        undoStack.push(lastAction);
        updateUndoButton();
    }
}

// ==================== AUMENTAR TOTAL ====================

async function aumentarTotalIssues() {
    if (!currentSeriesId || !currentSeries) { alert('Erro: Série não identificada'); return; }

    const novoTotal = currentSeries.total_issues + 1;
    if (!confirm(
        `📚 AUMENTAR TOTAL\n\nSérie: ${currentSeries.title}\n` +
        `Total atual: ${currentSeries.total_issues} → Novo total: ${novoTotal}\n\nConfirmar?`
    )) return;

    try {
        const oldTotal = currentSeries.total_issues;
        await fetchAPI(`/series/${currentSeriesId}`, {
            method: 'PUT',
            body: JSON.stringify({ ...currentSeries, total_issues: novoTotal })
        });
        addToUndoStack({ type: 'increase_total', seriesId: currentSeriesId, oldTotal, newTotal: novoTotal });
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
    } catch (error) {
        alert('Erro ao aumentar total: ' + error.message);
    }
}

// ==================== ADICIONAR EDIÇÃO BAIXADA ====================

function openAddIssueModal() {
    if (!currentSeriesId) { alert('Erro: Série não identificada'); return; }
    const modal = document.getElementById('issue-modal');
    document.getElementById('issue-form').reset();
    if (currentSeries && currentSeries.downloaded_issues >= 0)
        document.getElementById('issue_number').value = currentSeries.downloaded_issues + 1;
    modal.classList.add('active');
}

function closeIssueModal() {
    document.getElementById('issue-modal').classList.remove('active');
}

async function submitIssueForm(e) {
    e.preventDefault();
    if (!currentSeriesId) { alert('Erro: Série não identificada'); return; }
    const issueNumber = parseInt(document.getElementById('issue_number').value);
    const isRead      = document.getElementById('is_read').checked;
    try {
        const result = await fetchAPI(`/series/${currentSeriesId}/issues`, {
            method: 'POST',
            body: JSON.stringify({ issue_number: issueNumber, is_read: isRead })
        });
        addToUndoStack({ type: 'add_issue', seriesId: currentSeriesId, issueId: result.id, issueNumber });
        closeIssueModal();
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
    } catch (error) {
        alert('Erro ao adicionar edição: ' + error.message);
    }
}

// ==================== FIX #1: RECALCULAR (UMA REQUISIÇÃO) ====================

async function recalcularEdicoes(event) {
    if (!currentSeriesId || !currentSeries) { alert('Erro: Série não identificada'); return; }

    if (!confirm(
        `⚠️ RECALCULAR EDIÇÕES\n\nSérie: ${currentSeries.title}\n` +
        `Isso vai deletar TODAS as edições e recriar de 1 a ${currentSeries.total_issues},\n` +
        `marcando as primeiras ${currentSeries.read_issues} como lidas.\n\nConfirmar?`
    )) return;

    const button = event ? event.target : document.querySelector('[onclick*="recalcularEdicoes"]');
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Recalculando...';
    button.disabled  = true;

    try {
        // FIX #1: UMA requisição bulk ao invés de loop de N DELETE + N POST
        await fetchAPI(`/series/${currentSeriesId}/issues/bulk`, {
            method: 'POST',
            body: JSON.stringify({
                total_issues:    currentSeries.total_issues,
                read_issues:     currentSeries.read_issues,
                replace_existing: true
            })
        });
        alert(`✅ ${currentSeries.total_issues} edições recriadas!`);
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
    } catch (error) {
        alert('Erro ao recalcular edições: ' + error.message);
    } finally {
        button.innerHTML = originalText;
        button.disabled  = false;
    }
}

// FIX #1: Sincronizar também com bulk
async function sincronizarEdicoesAutomaticamente(event) {
    if (!currentSeriesId || !currentSeries) { alert('Erro: Série não identificada'); return; }

    if (!confirm(
        `🔄 Sincronizar Edições\n\nCriar ${currentSeries.total_issues} edições automaticamente?\n` +
        `• Edições 1 a ${currentSeries.read_issues}: LIDAS\n` +
        `• Edições ${currentSeries.read_issues + 1} a ${currentSeries.total_issues}: Não lidas\n\nConfirmar?`
    )) return;

    const button = event ? event.target : document.querySelector('[onclick*="sincronizarEdicoes"]');
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Sincronizando...';
    button.disabled  = true;

    try {
        // FIX #1: UMA requisição bulk
        await fetchAPI(`/series/${currentSeriesId}/issues/bulk`, {
            method: 'POST',
            body: JSON.stringify({
                total_issues:    currentSeries.total_issues,
                read_issues:     currentSeries.read_issues,
                replace_existing: true
            })
        });
        alert(`✅ ${currentSeries.total_issues} edições sincronizadas!`);
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
    } catch (error) {
        alert('Erro ao sincronizar: ' + error.message);
    } finally {
        button.innerHTML = originalText;
        button.disabled  = false;
    }
}

async function verificarSincronizacaoLendo() {
    if (!currentSeriesId) return;
    try {
        const issues = await fetchAPI(`/series/${currentSeriesId}/issues`);
        const lidas  = issues.filter(i => i.is_read).length;
        const valorMostrado = currentSeries.read_issues;
        if (lidas === valorMostrado) {
            alert(`✅ Contador correto!\n\nEdições lidas: ${lidas}`);
        } else {
            if (confirm(`⚠️ Dessincronização!\n\nEdições lidas: ${lidas}\nContador: ${valorMostrado}\n\nRecalcular?`))
                await recalcularEdicoes();
        }
    } catch { alert('Erro ao verificar'); }
}

// Toggle issue read — FIX #11: registra no undo
async function toggleIssueRead(issueId, isRead) {
    const oldState = !isRead;
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues/${issueId}`, {
            method: 'PATCH',
            body: JSON.stringify({ is_read: isRead })
        });
        // FIX #11: undo de toggle
        addToUndoStack({ type: 'toggle_read', seriesId: currentSeriesId, issueId, oldState, issueNumber: issueId });
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        alert('Erro ao atualizar status');
    }
}

async function deleteIssue(issueId, issueNumber) {
    if (!confirm(`Deletar edição #${issueNumber}?`)) return;
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues/${issueId}`, { method: 'DELETE' });
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch { alert('Erro ao deletar edição'); }
}

// FIX #2: marcar todas como lidas — UMA requisição
async function marcarTodasComoLidas() {
    if (!currentSeriesId) { alert('Erro: Série não identificada'); return; }
    if (!confirm('Marcar TODAS as edições como lidas?')) return;
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Marcando...'; button.disabled = true;
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues/bulk-read`, {
            method: 'PATCH',
            body: JSON.stringify({ is_read: true })
        });
        alert('✅ Todas as edições marcadas como lidas!');
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch { alert('Erro ao marcar edições como lidas'); }
    finally { button.innerHTML = originalText; button.disabled = false; }
}

// FIX #2: marcar todas como não lidas — UMA requisição
async function marcarTodasComoNaoLidas() {
    if (!currentSeriesId) { alert('Erro: Série não identificada'); return; }
    if (!confirm('Marcar TODAS as edições como NÃO lidas?')) return;
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Marcando...'; button.disabled = true;
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues/bulk-read`, {
            method: 'PATCH',
            body: JSON.stringify({ is_read: false })
        });
        alert('✅ Todas as edições marcadas como não lidas!');
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch { alert('Erro ao marcar edições como não lidas'); }
    finally { button.innerHTML = originalText; button.disabled = false; }
}

// FIX #2: deletar todas as edições — UMA requisição
async function marcarTodasComoNaoBaixadas() {
    if (!currentSeriesId) { alert('Erro: Série não identificada'); return; }
    if (!confirm('⚠️ Isso vai DELETAR TODAS as edições baixadas.\n\nConfirma?')) return;
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Deletando...'; button.disabled = true;
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues`, { method: 'DELETE' });
        alert('✅ Todas as edições marcadas como não baixadas!');
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch { alert('Erro ao marcar edições como não baixadas'); }
    finally { button.innerHTML = originalText; button.disabled = false; }
}

async function addIssueDownloaded(issueNumber) {
    if (!currentSeriesId) { alert('Erro: Série não identificada'); return; }
    try {
        const newIssue = await fetchAPI(`/series/${currentSeriesId}/issues`, {
            method: 'POST',
            body: JSON.stringify({ issue_number: issueNumber, is_read: false })
        });
        addToUndoStack({ type: 'add_issue', seriesId: currentSeriesId, issueId: newIssue.id, issueNumber });
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch { alert('Erro ao adicionar edição'); }
}

async function marcarComoNaoBaixada(issueId, issueNumber) {
    if (!confirm(`Marcar edição #${issueNumber} como NÃO baixada?\nIsso vai deletar a edição do sistema.`)) return;
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues/${issueId}`, { method: 'DELETE' });
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch { alert('Erro ao marcar edição como não baixada'); }
}

// ==================== FIELDS SAGA ====================

function toggleSagaFields() {
    const seriesType        = document.getElementById('series_type').value;
    const sagaEditionsField = document.getElementById('saga-editions-field');
    const sagaIssuesDivision = document.getElementById('saga-issues-division');
    const seriesTotalField  = document.getElementById('series-total-field');
    const completedLabelText = document.getElementById('completed-label-text');

    if (seriesType === 'saga') {
        sagaEditionsField.style.display  = 'block';
        sagaIssuesDivision.style.display = 'block';
        seriesTotalField.style.display   = 'none';
        completedLabelText.textContent   = 'Saga completa (todas as edições já foram lançadas)';
    } else {
        sagaEditionsField.style.display  = 'none';
        sagaIssuesDivision.style.display = 'none';
        seriesTotalField.style.display   = 'block';
        completedLabelText.textContent   = 'Série finalizada (não sairão mais edições)';
    }
}

function updateSagaTotal() {
    const mainIssues   = parseInt(document.getElementById('main_issues').value)   || 0;
    const tieInIssues  = parseInt(document.getElementById('tie_in_issues').value) || 0;
    const total = mainIssues + tieInIssues;
    document.getElementById('saga-total-calculated').textContent = total;
    document.getElementById('total_issues').value = total;
}

// ==================== FIX #19: PREVIEW DE CAPA ====================

function previewCoverUrl() {
    const url     = document.getElementById('cover_url').value.trim();
    const preview = document.getElementById('cover-url-preview');
    const img     = document.getElementById('cover-url-preview-img');
    const warn    = document.getElementById('cover-url-warning');

    if (!preview || !img) return;

    if (!url) {
        preview.style.display = 'none';
        if (warn) warn.style.display = 'none';
        return;
    }

    // FIX #8: validação básica de URL
    try {
        new URL(url);
    } catch {
        preview.style.display = 'none';
        if (warn) { warn.textContent = '⚠️ URL inválida'; warn.style.display = 'block'; }
        return;
    }

    img.src = url;
    preview.style.display = 'block';
    if (warn) warn.style.display = 'none';

    img.onload  = () => { if (warn) warn.style.display = 'none'; };
    img.onerror = () => {
        if (warn) { warn.textContent = '⚠️ URL não carregou imagem'; warn.style.display = 'block'; }
    };
}

// ==================== MODAL SÉRIE ====================

async function openModal(seriesId = null) {
    const modal = document.getElementById('series-modal');
    const form  = document.getElementById('series-form');
    const title = document.getElementById('modal-title');
    form.reset();

    // Limpar preview de capa
    const preview = document.getElementById('cover-url-preview');
    const warn    = document.getElementById('cover-url-warning');
    if (preview) preview.style.display = 'none';
    if (warn)    warn.style.display    = 'none';

    if (seriesId) {
        title.textContent = 'Editar HQ';
        try {
            const series = await fetchAPI(`/series/${seriesId}`);
            document.getElementById('series-id').value    = series.id;
            document.getElementById('title').value        = series.title;
            document.getElementById('author').value       = series.author    || '';
            document.getElementById('publisher').value    = series.publisher || '';
            document.getElementById('total_issues').value = series.total_issues || 0;
            document.getElementById('series_type').value  = series.series_type || 'em_andamento';
            document.getElementById('is_completed').checked = series.is_completed || false;
            document.getElementById('cover_url').value    = series.cover_url || '';
            document.getElementById('notes').value        = series.notes     || '';
            document.getElementById('saga_editions').value = series.saga_editions || '';
            document.getElementById('main_issues').value  = series.main_issues   || 0;
            document.getElementById('tie_in_issues').value = series.tie_in_issues || 0;
            // FIX #16
            const ysEl = document.getElementById('year_start');
            const yeEl = document.getElementById('year_end');
            if (ysEl) ysEl.value = series.year_start || '';
            if (yeEl) yeEl.value = series.year_end   || '';
            // FIX #19: mostrar preview se já tiver URL
            if (series.cover_url) previewCoverUrl();
        } catch (error) {
            alert('Erro ao carregar dados da série'); return;
        }
    } else {
        title.textContent = 'Nova HQ';
        document.getElementById('series-id').value = '';
    }

    toggleSagaFields();
    if (seriesId) updateSagaTotal();
    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('series-modal').classList.remove('active');
}

async function submitSeriesForm(e) {
    e.preventDefault();
    const seriesId = document.getElementById('series-id').value;

    // FIX #8: validar URL da capa
    const coverUrlVal = document.getElementById('cover_url').value.trim();
    if (coverUrlVal) {
        try { new URL(coverUrlVal); }
        catch {
            alert('⚠️ A URL da capa é inválida. Por favor corrija ou deixe em branco.');
            return;
        }
    }

    const data = {
        title:         document.getElementById('title').value,
        author:        document.getElementById('author').value    || null,
        publisher:     document.getElementById('publisher').value || null,
        total_issues:  parseInt(document.getElementById('total_issues').value) || 0,
        series_type:   document.getElementById('series_type').value,
        is_completed:  document.getElementById('is_completed').checked,
        cover_url:     coverUrlVal || null,
        notes:         document.getElementById('notes').value         || null,
        saga_editions: document.getElementById('saga_editions').value || null,
        main_issues:   parseInt(document.getElementById('main_issues').value)   || 0,
        tie_in_issues: parseInt(document.getElementById('tie_in_issues').value) || 0,
        // FIX #16
        year_start: parseInt(document.getElementById('year_start')?.value) || null,
        year_end:   parseInt(document.getElementById('year_end')?.value)   || null,
    };

    if (seriesId) {
        try {
            const seriesAtual = await fetchAPI(`/series/${seriesId}`);
            data.downloaded_issues = seriesAtual.downloaded_issues || 0;
            data.read_issues       = seriesAtual.read_issues       || 0;
            if (!data.total_issues) data.total_issues = seriesAtual.total_issues || 0;
        } catch {
            alert('Erro ao buscar dados atuais da série'); return;
        }
    }

    try {
        if (seriesId) {
            await fetchAPI(`/series/${seriesId}`, { method: 'PUT',  body: JSON.stringify(data) });
        } else {
            await fetchAPI('/series',             { method: 'POST', body: JSON.stringify(data) });
        }
        closeModal();
        await loadSeries();
        await loadStats();
        if (seriesId && currentSeriesId == seriesId) await loadSeriesDetail(seriesId);
    } catch (error) {
        alert('Erro ao salvar HQ: ' + error.message);
    }
}

async function editSeries(seriesId) { await openModal(seriesId); }

async function editarSerieAtual() {
    if (!currentSeriesId) return;
    await openModal(currentSeriesId);
}

async function deleteSeries(seriesId, seriesTitle = 'esta HQ') {
    if (!confirm(`Deletar "${seriesTitle}"?`)) return;
    try {
        await fetchAPI(`/series/${seriesId}`, { method: 'DELETE' });
        // FIX #11: registrar no undo (não é reversível, mas loga no stack)
        addToUndoStack({ type: 'delete_series', seriesId, title: seriesTitle });
        goToHome();
        loadSeries();
        loadStats();
    } catch { alert('Erro ao deletar HQ'); }
}

// ==================== PAGINAÇÃO ====================

function updatePaginationControls() {
    const paginationContainer = document.getElementById('pagination-controls');
    if (!paginationContainer) return;

    if (totalPages <= 1) { paginationContainer.style.display = 'none'; return; }
    paginationContainer.style.display = 'flex';

    const paginationInfoEl = document.getElementById('pagination-info');
    if (paginationInfoEl) {
        const startItem = (currentPage - 1) * perPage + 1;
        const endItem   = Math.min(currentPage * perPage, totalItems);
        paginationInfoEl.textContent = `Mostrando ${startItem}-${endItem} de ${totalItems}`;
    }

    const btnFirst = document.getElementById('btn-first-page');
    const btnPrev  = document.getElementById('btn-prev-page');
    const btnNext  = document.getElementById('btn-next-page');
    const btnLast  = document.getElementById('btn-last-page');

    if (btnFirst) btnFirst.disabled = currentPage === 1;
    if (btnPrev)  btnPrev.disabled  = currentPage === 1;
    if (btnNext)  btnNext.disabled  = currentPage === totalPages;
    if (btnLast)  btnLast.disabled  = currentPage === totalPages;

    updatePageNumbers();
}

function updatePageNumbers() {
    const pageNumbersContainer = document.getElementById('page-numbers');
    if (!pageNumbersContainer) return;
    pageNumbersContainer.innerHTML = '';

    let startPage = Math.max(1, currentPage - 2);
    let endPage   = Math.min(totalPages, currentPage + 2);
    if (currentPage <= 3)            endPage   = Math.min(5, totalPages);
    if (currentPage >= totalPages-2) startPage = Math.max(1, totalPages - 4);

    if (startPage > 1) { addPageButton(1); if (startPage > 2) addEllipsis(); }
    for (let i = startPage; i <= endPage; i++) addPageButton(i);
    if (endPage < totalPages) { if (endPage < totalPages - 1) addEllipsis(); addPageButton(totalPages); }
}

function addPageButton(pageNum) {
    const btn = document.createElement('button');
    btn.className   = 'page-number' + (pageNum === currentPage ? ' active' : '');
    btn.textContent = pageNum;
    btn.onclick     = () => goToPage(pageNum);
    document.getElementById('page-numbers').appendChild(btn);
}

function addEllipsis() {
    const span       = document.createElement('span');
    span.className   = 'page-ellipsis';
    span.textContent = '...';
    document.getElementById('page-numbers').appendChild(span);
}

function goToPage(page) {
    if (page < 1 || page > totalPages || page === currentPage) return;
    currentPage = page;
    const searchTerm = document.getElementById('search-input')?.value.trim() || '';
    if (searchTerm) loadSeries(searchTerm, currentPage);
    else displaySeries();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goToFirstPage() { goToPage(1); }
function goToPrevPage()  { goToPage(currentPage - 1); }
function goToNextPage()  { goToPage(currentPage + 1); }
function goToLastPage()  { goToPage(totalPages); }

// ==================== RECALCULAR TUDO ====================

async function recalcularTodasHQs(event) {
    if (!confirm(
        '⚠️ ATENÇÃO!\n\nEsta ação irá recalcular TODAS as HQs.\n\n' +
        'As HQs que já têm edições cadastradas serão ignoradas.\n\nDeseja continuar?'
    )) return;

    const button = event ? event.target : document.querySelector('[onclick*="recalcularTodasHQs"]');
    if (!button) return;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Recalculando...';
    button.disabled  = true;

    try {
        const result = await fetchAPI('/recalculate-all', { method: 'POST' });
        alert(`✅ Recálculo concluído!\n\n📊 Total: ${result.total}\n✅ Recalculadas: ${result.recalculated}\n❌ Erros: ${result.errors}`);
        loadSeries();
        loadStats();
    } catch (error) {
        alert('❌ Erro ao recalcular HQs: ' + error.message);
    } finally {
        button.innerHTML = originalText;
        button.disabled  = false;
    }
}

// ==================== FIX #12: EXPORTAÇÃO ====================

async function exportarDados() {
    try {
        const response = await fetch(`${API_URL}/export`);
        if (!response.ok) throw new Error('Erro ao exportar');
        const blob = await response.blob();
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        const cd   = response.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename=([^;]+)/);
        a.download = match ? match[1] : 'hq_backup.csv';
        a.href  = url;
        a.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        alert('Erro ao exportar: ' + error.message);
    }
}

// ==================== FIX #18: IMPORTAÇÃO ====================

function openImportModal() {
    const modal = document.getElementById('import-modal');
    if (modal) modal.style.display = 'flex';
}

function closeImportModal() {
    const modal = document.getElementById('import-modal');
    if (modal) modal.style.display = 'none';
}

async function submitImport(e) {
    if (e) e.preventDefault();
    const fileInput = document.getElementById('import-file');
    if (!fileInput || !fileInput.files[0]) { alert('Selecione um arquivo CSV ou XLSX'); return; }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    const btn = document.getElementById('btn-import-submit');
    const originalText = btn ? btn.innerHTML : '';
    if (btn) { btn.innerHTML = '⏳ Importando...'; btn.disabled = true; }

    try {
        const response = await fetch(`${API_URL}/import`, { method: 'POST', body: formData });
        const result   = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Erro na importação');
        alert(`✅ Importação concluída!\n\n📥 Criadas: ${result.created}\n⏭️ Ignoradas: ${result.skipped}\n❌ Erros: ${result.errors}`);
        closeImportModal();
        loadSeries();
        loadStats();
    } catch (error) {
        alert('Erro ao importar: ' + error.message);
    } finally {
        if (btn) { btn.innerHTML = originalText; btn.disabled = false; }
    }
}

// ==================== STATS / MOBILE ====================

function toggleStatsPanel() {
    const panel   = document.getElementById('stats-panel');
    const overlay = document.getElementById('stats-panel-overlay');
    if (panel && overlay) {
        if (panel.classList.contains('open')) closeStatsPanel();
        else openStatsPanel();
    }
}

function openStatsPanel() {
    document.getElementById('stats-panel')?.classList.add('open');
    document.getElementById('stats-panel-overlay')?.classList.add('open');
}

function closeStatsPanel() {
    document.getElementById('stats-panel')?.classList.remove('open');
    document.getElementById('stats-panel-overlay')?.classList.remove('open');
}

function updateStatsBadge(total) {
    const badge = document.getElementById('stats-fab-badge');
    if (badge) badge.textContent = total || '0';
}

// ==================== MODAL NOTAS ====================

function openNotesModal() {
    if (!currentSeries?.notes) return;
    const modal = document.getElementById('notes-modal');
    document.getElementById('notes-display-content').textContent = currentSeries.notes;
    modal.style.display = 'flex';
}

function closeNotesModal() {
    document.getElementById('notes-modal').style.display = 'none';
}

// ==================== MOBILE MENU ====================

function toggleMobileMenu() {
    const menu    = document.getElementById('mobile-menu');
    const overlay = document.getElementById('mobile-menu-overlay');
    menu.classList.toggle('active');
    overlay.classList.toggle('active');
    document.body.style.overflow = menu.classList.contains('active') ? 'hidden' : '';
}

function filterSeriesFromMobile(filter, button) {
    document.querySelectorAll('.mobile-filter-btn').forEach(b => b.classList.remove('active'));
    button.classList.add('active');
    document.querySelectorAll('.filter-tab-compact').forEach(b => {
        b.classList.toggle('active', b.dataset.filter === filter);
    });
    toggleMobileMenu();
    currentFilter = filter;
    currentPage   = 1;
    loadSeries();
}

function updateMobileStats() {
    const pairs = [
        ['stat-total',      'mobile-stat-total'],
        ['stat-para-ler',   'mobile-stat-para-ler'],
        ['stat-lendo',      'mobile-stat-lendo'],
        ['stat-concluidas', 'mobile-stat-concluidas'],
    ];
    pairs.forEach(([src, dst]) => {
        const srcEl = document.getElementById(src);
        const dstEl = document.getElementById(dst);
        if (srcEl && dstEl) dstEl.textContent = srcEl.textContent;
    });
}
