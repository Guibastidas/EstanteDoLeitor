// API Configuration
const API_URL = window.location.origin;;

// State
let currentFilter = 'all';
let currentSeriesId = null;
let allSeries = [];
let searchTimeout = null;
let currentSeries = null;

// Paginação
let currentPage = 1;
let perPage = 20;  // 20 HQs por página
let totalPages = 1;
let totalItems = 0;
let paginationInfo = null;

// Pilha de ações para desfazer
let undoStack = [];

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Iniciando aplicação...');
    console.log('📡 API URL:', API_URL);
    
    loadSeries();
    loadStats();
    
    // Inicializar scroll behavior
    initScrollBehavior();
    
    // Restaurar view de detalhes se estava aberta
    const savedView = localStorage.getItem('currentView');
    const savedSeriesId = localStorage.getItem('currentSeriesId');
    
    if (savedView === 'detail' && savedSeriesId) {
        console.log('🔄 Restaurando view de detalhes:', savedSeriesId);
        setTimeout(() => {
            showSeriesDetail(parseInt(savedSeriesId));
        }, 100);
    }
});

// ==================== SCROLL BEHAVIOR ====================

let lastScrollTop = 0;
let scrollTimeout = null;

function initScrollBehavior() {
    const header = document.getElementById('main-header');
    const scrollToTopBtn = document.getElementById('scroll-to-top');
    let ticking = false;
    
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                const currentScroll = window.pageYOffset || document.documentElement.scrollTop;
                
                // Mostrar/esconder botão voltar ao topo
                if (currentScroll > 300) {
                    scrollToTopBtn.classList.add('visible');
                } else {
                    scrollToTopBtn.classList.remove('visible');
                }
                
                // Comportamento do header no mobile - CORRIGIDO
                if (window.innerWidth <= 768) {
                    // Scroll para baixo - compactar header
                    if (currentScroll > lastScrollTop && currentScroll > 100) {
                        header.classList.add('header-compact-scroll');
                    } 
                    // Scroll para cima - expandir header
                    else if (currentScroll < lastScrollTop) {
                        header.classList.remove('header-compact-scroll');
                    }
                    
                    // No topo - sempre mostrar completo
                    if (currentScroll < 50) {
                        header.classList.remove('header-compact-scroll');
                    }
                }
                
                lastScrollTop = currentScroll <= 0 ? 0 : currentScroll;
                ticking = false;
            });
            
            ticking = true;
        }
    }, { passive: true });
    
    // Remover classe ao redimensionar
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            header.classList.remove('header-compact-scroll');
            lastScrollTop = 0;
        }
    });
}

function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Função para obter o label do tipo de série
function getSeriesTypeLabel(seriesType) {
    const types = {
        'finalizada': { text: 'Finalizada', class: 'type-finalizada', emoji: '✓' },
        'em_andamento': { text: 'Em Andamento', class: 'type-andamento', emoji: '📖' },
        'lancamento': { text: 'Lançamento', class: 'type-lancamento', emoji: '🆕' },
        'edicao_especial': { text: 'Edição Especial', class: 'type-especial', emoji: '⭐' },
        'saga': { text: 'Saga', class: 'type-saga', emoji: '🎭' }
    };
    
    return types[seriesType] || types['em_andamento'];
}

// Função para criar o badge de tipo de série
function createSeriesTypeBadge(seriesType) {
    const typeInfo = getSeriesTypeLabel(seriesType);
    return `<span class="series-type-badge ${typeInfo.class}">${typeInfo.emoji} ${typeInfo.text}</span>`;
}

// API Functions
async function fetchAPI(endpoint, options = {}) {
    try {
        console.log('🔄 API Request:', endpoint, options.method || 'GET');
        
        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });
        
        console.log('📥 API Response:', response.status, endpoint);
        
        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}`;
            try {
                const error = await response.json();
                errorMessage = error.detail || errorMessage;
            } catch (e) {
                // Se não conseguir ler JSON, usa mensagem padrão
            }
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        console.log('📦 Dados recebidos:', data);
        return data;
    } catch (error) {
        console.error('❌ API Error:', error);
        throw error;
    }
}

// Load Functions
async function loadSeries(filterQuery = '', page = 1) {
    try {
        console.log('📚 Carregando séries...', filterQuery ? `(filtro: ${filterQuery})` : '', `(página: ${page})`);
        
        // CORREÇÃO: Quando não há busca, carregar TODAS as séries para permitir filtros locais
        // Quando há busca, usar paginação normal
        let perPageToUse = filterQuery ? perPage : 1000; // 1000 é suficiente para carregar todas
        
        // Construir URL com paginação
        let endpoint = `/series?page=${page}&per_page=${perPageToUse}`;
        if (filterQuery) {
            endpoint += `&search=${encodeURIComponent(filterQuery)}`;
        }
        
        console.log(`📡 Endpoint: ${endpoint} (per_page: ${perPageToUse})`);
        
        const response = await fetchAPI(endpoint);
        
        // Verificar se a resposta tem paginação
        if (response.items && response.pagination) {
            // Nova estrutura com paginação
            allSeries = response.items;
            paginationInfo = response.pagination;
            currentPage = response.pagination.page;
            totalPages = response.pagination.total_pages;
            totalItems = response.pagination.total_items;
            
            console.log(`✅ ${allSeries.length} séries carregadas (página ${currentPage} de ${totalPages})`);
            console.log(`📊 Total de séries no banco: ${totalItems}`);
        } else {
            // Fallback para estrutura antiga (sem paginação)
            allSeries = response;
            totalPages = 1;
            totalItems = allSeries.length;
            console.log(`✅ ${allSeries.length} séries carregadas (sem paginação)`);
        }
        
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
        console.log('📊 Carregando estatísticas...');
        const stats = await fetchAPI('/stats');
        
        console.log('📊 Estatísticas recebidas:', stats);
        
        document.getElementById('stat-total').textContent = stats.total || 0;
        document.getElementById('stat-para-ler').textContent = stats.para_ler || 0;
        document.getElementById('stat-lendo').textContent = stats.lendo || 0;
        document.getElementById('stat-concluidas').textContent = stats.concluidas || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Display Functions
function displaySeries() {
    const grid = document.getElementById('series-grid');
    const emptyState = document.getElementById('empty-state');
    
    console.log('🔍 displaySeries() chamado');
    console.log('📊 Filtro atual:', currentFilter);
    console.log('📚 Total de séries carregadas:', allSeries.length);
    
    // MOSTRAR TODAS AS SÉRIES EM FORMATO DE TABELA
    console.log('📋 TODAS AS SÉRIES (TABELA):');
    console.table(allSeries.map(s => ({
        'ID': s.id,
        'Título': s.title,
        'Tipo (series_type)': s.series_type,
        'Total': s.total_issues,
        'Lidas': s.read_issues
    })));
    
    // Filtrar séries
    let filteredSeries = allSeries;
    
    if (currentFilter === 'para_ler') {
        filteredSeries = allSeries.filter(s => s.read_issues === 0);
    } else if (currentFilter === 'lendo') {
        filteredSeries = allSeries.filter(s => s.read_issues > 0 && s.read_issues < s.total_issues);
    } else if (currentFilter === 'concluida') {
        filteredSeries = allSeries.filter(s => s.read_issues >= s.total_issues && s.total_issues > 0);
    } else if (currentFilter === 'saga') {
        console.log('🎭 FILTRO SAGA ATIVADO!');
        console.log('📋 Testando cada série:');
        allSeries.forEach(s => {
            const isSaga = s.series_type === 'saga';
            console.log(`  - "${s.title}": series_type = "${s.series_type}" | É saga? ${isSaga ? '✅ SIM' : '❌ NÃO'}`);
        });
        
        filteredSeries = allSeries.filter(s => s.series_type === 'saga');
        
        console.log('✅ Sagas encontradas:', filteredSeries.length);
        if (filteredSeries.length > 0) {
            console.log('📜 Lista de sagas:');
            filteredSeries.forEach(s => {
                console.log(`  - ${s.title} (ID: ${s.id})`);
            });
        } else {
            console.warn('⚠️ NENHUMA SAGA ENCONTRADA!');
            console.warn('Verifique se suas sagas têm series_type = "saga" no banco de dados');
            console.warn('Tipos encontrados:', [...new Set(allSeries.map(s => s.series_type))]);
        }
    }
    
    console.log(`✅ Séries após filtro "${currentFilter}":`, filteredSeries.length);
    
    // Ordenar alfabeticamente
    filteredSeries.sort((a, b) => {
        return a.title.localeCompare(b.title, 'pt-BR', { sensitivity: 'base' });
    });
    
    console.log(`🔍 Filtro "${currentFilter}": ${filteredSeries.length} séries (ordenadas alfabeticamente)`);
    
    if (filteredSeries.length === 0) {
        showEmptyState();
        return;
    }
    
    emptyState.style.display = 'none';
    grid.style.display = 'grid';
    grid.innerHTML = '';
    
    filteredSeries.forEach(series => {
        const card = createSeriesCard(series);
        grid.appendChild(card);
    });
}

function createSeriesCard(series) {
    const card = document.createElement('div');
    card.className = 'comic-card';
    
    // Calcular progresso
    const progress = series.total_issues > 0 
        ? Math.round((series.read_issues / series.total_issues) * 100)
        : 0;
    
    // Status
    let statusClass = 'para-ler';
    let statusText = 'Para Ler';
    
    if (series.read_issues >= series.total_issues && series.total_issues > 0) {
        statusClass = 'concluida';
        statusText = 'Concluída';
    } else if (series.read_issues > 0) {
        statusClass = 'lendo';
        statusText = 'Lendo';
    }
    
    // Escapar título para uso seguro em atributos
    const escapedTitle = series.title.replace(/'/g, "\\'").replace(/"/g, '&quot;');
    
    // Badge de tipo
    const typeInfo = getSeriesTypeLabel(series.series_type);
    const typeBadge = `<span class="series-type-badge ${typeInfo.class}">${typeInfo.emoji} ${typeInfo.text}</span>`;
    
    card.innerHTML = `
        <div class="comic-cover">
            <div class="series-type-overlay">
                ${typeBadge}
            </div>
            ${series.cover_url 
                ? `<img src="${series.cover_url}" alt="${series.title}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                   <div class="comic-cover-placeholder" style="display:none;">📖</div>`
                : `<div class="comic-cover-placeholder">📖</div>`
            }
        </div>
        <div class="comic-info">
            <div class="comic-progress-header">
                <span class="progress-label">Progresso</span>
                <span class="progress-value">${series.read_issues}/${series.total_issues} (${progress}%)</span>
            </div>
            <div class="progress-bar-container">
                <div class="progress-bar" style="width: ${progress}%"></div>
            </div>
            
            <h3 class="comic-title">${series.title}</h3>
            ${series.author ? `<p class="comic-author">✍️ ${series.author}</p>` : ''}
            ${series.publisher ? `<p class="comic-publisher">📚 ${series.publisher}</p>` : ''}
            
            <div class="comic-stats">
                <span>Lendo: <strong>${series.read_issues}</strong></span>
                <span>Baixadas: <strong>${series.downloaded_issues}</strong></span>
                <span>Total: <strong>${series.total_issues}</strong></span>
            </div>
            
            <div class="comic-status-row">
                <div class="comic-status ${statusClass}">${statusText}</div>
                <div class="comic-actions">
                    <button class="btn-icon-small btn-edit" data-series-id="${series.id}" title="Editar HQ">
                        ✏️
                    </button>
                    <button class="btn-icon-small btn-delete" data-series-id="${series.id}" data-series-title="${escapedTitle}" title="Excluir HQ">
                        🗑️
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Event listeners
    card.addEventListener('click', (e) => {
        if (!e.target.closest('.btn-icon-small')) {
            showSeriesDetail(series.id);
        }
    });
    
    const btnEdit = card.querySelector('.btn-edit');
    const btnDelete = card.querySelector('.btn-delete');
    
    if (btnEdit) {
        btnEdit.addEventListener('click', (e) => {
            e.stopPropagation();
            editSeries(series.id);
        });
    }
    
    if (btnDelete) {
        btnDelete.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteSeries(series.id, series.title);
        });
    }
    
    return card;
}

function showEmptyState() {
    const grid = document.getElementById('series-grid');
    const emptyState = document.getElementById('empty-state');
    
    grid.style.display = 'none';
    emptyState.style.display = 'flex';
}

// Show series detail view
async function showSeriesDetail(seriesId) {
    console.log('📖 Abrindo detalhes da série:', seriesId);
    currentSeriesId = seriesId;
    
    // Salvar no localStorage para persistir ao recarregar
    localStorage.setItem('currentView', 'detail');
    localStorage.setItem('currentSeriesId', seriesId);
    
    // Switch views
    document.getElementById('home-view').style.display = 'none';
    const filtersSection = document.getElementById('filters-section');
    filtersSection.style.display = 'none';
    filtersSection.style.visibility = 'hidden';
    document.getElementById('detail-view').style.display = 'block';
    document.getElementById('btn-back').style.display = 'inline-flex';
    
    // Adicionar classe ao body para esconder filtros
    document.body.classList.add('detail-page');
    
    // Scroll para o topo
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    await loadSeriesDetail(seriesId);
}

async function loadSeriesDetail(seriesId) {
    try {
        console.log('🔄 Carregando detalhes da série:', seriesId);
        
        const series = await fetchAPI(`/series/${seriesId}`);
        currentSeries = series;
        console.log('📊 Dados da série:', series);
        
        // Atualizar informações
        document.getElementById('detail-title').textContent = series.title;
        
        // Badge de tipo
        const typeBadgeEl = document.getElementById('detail-type-badge');
        const typeInfo = getSeriesTypeLabel(series.series_type);
        typeBadgeEl.innerHTML = `<span class="series-type-badge ${typeInfo.class}">${typeInfo.emoji} ${typeInfo.text}</span>`;
        typeBadgeEl.style.display = 'block';
        typeBadgeEl.style.marginBottom = '0.75rem';
        
        const authorEl = document.getElementById('detail-author');
        const publisherEl = document.getElementById('detail-publisher');
        
        if (series.author) {
            authorEl.textContent = `✍️ ${series.author}`;
            authorEl.style.display = 'block';
        } else {
            authorEl.style.display = 'none';
        }
        
        if (series.publisher) {
            publisherEl.textContent = `📚 ${series.publisher}`;
            publisherEl.style.display = 'block';
        } else {
            publisherEl.style.display = 'none';
        }
        
        // Mostrar edições da saga (se for uma saga)
        const sagaEditionsDisplay = document.getElementById('saga-editions-display');
        const sagaEditionsList = document.getElementById('saga-editions-list');
        
        if (series.series_type === 'saga' && series.saga_editions) {
            const editions = series.saga_editions.split('\n').filter(e => e.trim());
            sagaEditionsList.innerHTML = editions.map(edition => 
                `<div class="saga-edition-item">• ${edition.trim()}</div>`
            ).join('');
            sagaEditionsDisplay.style.display = 'block';
        } else {
            sagaEditionsDisplay.style.display = 'none';
        }
        
        // Capa
        const coverImg = document.getElementById('detail-cover');
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
            ? Math.round((series.read_issues / series.total_issues) * 100)
            : 0;
        
        document.getElementById('detail-progress').textContent = 
            `${series.read_issues}/${series.total_issues} edições (${progress}%)`;
        document.getElementById('detail-progress-bar').style.width = `${progress}%`;
        
        // Contadores
        document.getElementById('detail-reading').textContent = series.read_issues;
        document.getElementById('detail-downloaded').textContent = series.downloaded_issues;
        document.getElementById('detail-total').textContent = series.total_issues;
        
        // Mostrar divisão de edições para sagas
        const sagaDivisionStats = document.getElementById('saga-division-stats');
        if (series.series_type === 'saga' && (series.main_issues || series.tie_in_issues)) {
            document.getElementById('detail-main-issues').textContent = series.main_issues || 0;
            document.getElementById('detail-tie-in-issues').textContent = series.tie_in_issues || 0;
            sagaDivisionStats.style.display = 'flex';
        } else {
            sagaDivisionStats.style.display = 'none';
        }
        
        // Mostrar botão de notas (se existirem)
        const btnViewNotes = document.getElementById('btn-view-notes');
        if (series.notes && series.notes.trim()) {
            btnViewNotes.style.display = 'flex';
        } else {
            btnViewNotes.style.display = 'none';
        }
        
        // Carregar edições
        const issues = await fetchAPI(`/series/${seriesId}/issues`);
        console.log(`✅ ${issues.length} edições carregadas`);
        
        displayIssues(issues);
        
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
    
    // Criar um mapa de edições existentes
    const issuesMap = {};
    issues.forEach(issue => {
        issuesMap[issue.issue_number] = issue;
    });
    
    // Criar badges para todas as edições até o total
    for (let i = 1; i <= currentSeries.total_issues; i++) {
        let issue = issuesMap[i];
        
        // Se a edição não existe, criar uma virtual (não baixada)
        if (!issue) {
            issue = {
                id: null,
                issue_number: i,
                is_read: false,
                is_downloaded: false,
                series_id: currentSeriesId
            };
        }
        
        const issueCard = createIssueCard(issue);
        issuesList.appendChild(issueCard);
    }
}

function createIssueCard(issue) {
    const badge = document.createElement('div');
    
    // Determinar classe de cor
    let colorClass = 'issue-faltante'; // Padrão: cinza (não baixada)
    let icon = '❌';
    
    if (issue.is_read) {
        colorClass = 'issue-lida'; // Verde: lida
        icon = '✅';
    } else if (issue.is_downloaded) {
        colorClass = 'issue-baixada'; // Amarelo: baixada mas não lida
        icon = '📥';
    }
    
    badge.className = `issue-badge ${colorClass}`;
    badge.title = issue.is_read ? 'Lida' : (issue.is_downloaded ? 'Baixada' : 'Não baixada');
    
    badge.innerHTML = `
        <div class="issue-badge-number">#${issue.issue_number}</div>
        <div class="issue-badge-icon">${icon}</div>
        ${issue.id ? '<button class="issue-badge-undownload" title="Marcar como não baixada">↩️</button>' : ''}
        ${issue.id ? '<button class="issue-badge-delete" title="Deletar">×</button>' : ''}
    `;
    
    // Event listener para o badge inteiro - comportamento depende do estado
    badge.addEventListener('click', (e) => {
        // Não fazer nada se clicar nos botões
        if (e.target.closest('.issue-badge-delete') || e.target.closest('.issue-badge-undownload')) {
            return;
        }
        
        // Se for um badge cinza (não baixado), adicionar como baixada
        if (!issue.id) {
            addIssueDownloaded(issue.issue_number);
        } else {
            // Se já existe, alternar status lida/não lida
            toggleIssueRead(issue.id, !issue.is_read);
        }
    });
    
    // Event listener para o botão de marcar como não baixada
    if (issue.id) {
        const undownloadBtn = badge.querySelector('.issue-badge-undownload');
        if (undownloadBtn) {
            undownloadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                marcarComoNaoBaixada(issue.id, issue.issue_number);
            });
        }
        
        // Event listener para o botão de deletar
        const deleteBtn = badge.querySelector('.issue-badge-delete');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteIssue(issue.id, issue.issue_number);
            });
        }
    }
    
    return badge;
}

function goToHome() {
    console.log('🏠 Voltando para home...');
    
    // Limpar localStorage
    localStorage.removeItem('currentView');
    localStorage.removeItem('currentSeriesId');
    
    // Esconder detail view
    document.getElementById('detail-view').style.display = 'none';
    document.getElementById('btn-back').style.display = 'none';
    
    // Remover classe do body
    document.body.classList.remove('detail-page');
    
    // Mostrar home view
    document.getElementById('home-view').style.display = 'block';
    
    // Mostrar filtros
    const filtersSection = document.getElementById('filters-section');
    filtersSection.style.display = 'flex';
    filtersSection.style.visibility = 'visible';
    filtersSection.style.alignItems = 'center';
    filtersSection.style.justifyContent = 'space-between';
    
    // Scroll para o topo
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    // Resetar variáveis
    currentSeriesId = null;
    currentSeries = null;
    
    // Recarregar dados
    loadSeries();
    loadStats();
}

// Filter series
function filterSeries(filter, element) {
    console.log('🎯 filterSeries() chamado com filtro:', filter);
    console.log('📍 Elemento clicado:', element);
    
    currentFilter = filter;
    
    // Atualizar ambos os tipos de filtros (se existirem)
    document.querySelectorAll('.filter-tab, .filter-tab-compact').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Se element foi passado, usar ele; senão tentar event.target (fallback)
    const targetElement = element || (typeof event !== 'undefined' ? event.target : null);
    if (targetElement) {
        targetElement.classList.add('active');
        console.log('✅ Classe "active" adicionada ao elemento');
    } else {
        console.error('❌ Nenhum elemento encontrado para adicionar classe "active"');
    }
    
    console.log('🔄 Chamando displaySeries()...');
    displaySeries();
    updatePaginationControls();
    console.log('✅ filterSeries() concluído');
}

// Search
function handleSearch() {
    const query = document.getElementById('search-input').value;
    const clearBtn = document.getElementById('search-clear');
    
    clearBtn.style.display = query ? 'block' : 'none';
    
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        currentPage = 1; // Resetar para página 1 ao buscar
        loadSeries(query, 1);
    }, 300);
}

function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('search-clear').style.display = 'none';
    currentPage = 1; // Resetar para página 1
    loadSeries('', 1);
}

// ==================== UNDO/REDO ====================

function addToUndoStack(action) {
    undoStack.push(action);
    // Manter apenas últimas 10 ações
    if (undoStack.length > 10) {
        undoStack.shift();
    }
    updateUndoButton();
}

function updateUndoButton() {
    const undoBtn = document.getElementById('btn-undo');
    if (undoBtn) {
        undoBtn.disabled = undoStack.length === 0;
        undoBtn.textContent = `↶ Desfazer${undoStack.length > 0 ? ` (${undoStack.length})` : ''}`;
    }
}

async function desfazerUltimaAcao() {
    if (undoStack.length === 0) {
        alert('Nenhuma ação para desfazer');
        return;
    }
    
    const lastAction = undoStack.pop();
    
    try {
        console.log('↶ Desfazendo:', lastAction);
        
        switch (lastAction.type) {
            case 'add_issue':
                // Deletar a edição adicionada
                await fetchAPI(`/series/${lastAction.seriesId}/issues/${lastAction.issueId}`, {
                    method: 'DELETE'
                });
                alert(`Edição #${lastAction.issueNumber} removida`);
                break;
                
            case 'increase_total':
                // Diminuir total_issues
                const series = await fetchAPI(`/series/${lastAction.seriesId}`);
                await fetchAPI(`/series/${lastAction.seriesId}`, {
                    method: 'PUT',
                    body: JSON.stringify({
                        ...series,
                        total_issues: lastAction.oldTotal
                    })
                });
                alert(`Total voltou de ${lastAction.newTotal} para ${lastAction.oldTotal}`);
                break;
        }
        
        updateUndoButton();
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
        
    } catch (error) {
        console.error('❌ Erro ao desfazer:', error);
        alert('Erro ao desfazer ação: ' + error.message);
        // Recoloca na pilha se der erro
        undoStack.push(lastAction);
        updateUndoButton();
    }
}

// ==================== NOVA EDIÇÃO PUBLICADA (AUMENTA TOTAL) ====================

async function aumentarTotalIssues() {
    if (!currentSeriesId || !currentSeries) {
        alert('Erro: Série não identificada');
        return;
    }
    
    const novoTotal = currentSeries.total_issues + 1;
    
    const confirmacao = confirm(
        `📚 AUMENTAR TOTAL DE EDIÇÕES PUBLICADAS\n\n` +
        `Série: ${currentSeries.title}\n` +
        `Total atual: ${currentSeries.total_issues}\n` +
        `Novo total: ${novoTotal}\n\n` +
        `Isso significa que a EDITORA publicou mais uma edição.\n` +
        `(Você ainda não baixou essa edição)\n\n` +
        `Confirmar?`
    );
    
    if (!confirmacao) return;
    
    try {
        console.log('📚 Aumentando total_issues...');
        
        const oldTotal = currentSeries.total_issues;
        
        await fetchAPI(`/series/${currentSeriesId}`, {
            method: 'PUT',
            body: JSON.stringify({
                ...currentSeries,
                total_issues: novoTotal
            })
        });
        
        // Adicionar ao undo stack
        addToUndoStack({
            type: 'increase_total',
            seriesId: currentSeriesId,
            oldTotal: oldTotal,
            newTotal: novoTotal
        });
        
        console.log('✅ Total aumentado!');
        
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
        
    } catch (error) {
        console.error('❌ Erro ao aumentar total:', error);
        alert('Erro ao aumentar total: ' + error.message);
    }
}

// ==================== ADICIONAR EDIÇÃO BAIXADA ====================

function openAddIssueModal() {
    if (!currentSeriesId) {
        alert('Erro: Série não identificada');
        return;
    }
    
    const modal = document.getElementById('issue-modal');
    const form = document.getElementById('issue-form');
    
    form.reset();
    
    // Sugerir próximo número baseado em downloaded_issues
    if (currentSeries && currentSeries.downloaded_issues >= 0) {
        const nextIssue = currentSeries.downloaded_issues + 1;
        document.getElementById('issue_number').value = nextIssue;
    }
    
    modal.classList.add('active');
}

function closeIssueModal() {
    const modal = document.getElementById('issue-modal');
    modal.classList.remove('active');
}

async function submitIssueForm(e) {
    e.preventDefault();
    
    if (!currentSeriesId) {
        alert('Erro: Série não identificada');
        return;
    }
    
    const issueNumber = parseInt(document.getElementById('issue_number').value);
    const isRead = document.getElementById('is_read').checked;
    
    try {
        const result = await fetchAPI(`/series/${currentSeriesId}/issues`, {
            method: 'POST',
            body: JSON.stringify({
                issue_number: issueNumber,
                is_read: isRead
            })
        });
        
        // Adicionar ao undo stack
        addToUndoStack({
            type: 'add_issue',
            seriesId: currentSeriesId,
            issueId: result.id,
            issueNumber: issueNumber
        });
        
        closeIssueModal();
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
        
    } catch (error) {
        console.error('❌ Error adding issue:', error);
        alert('Erro ao adicionar edição: ' + error.message);
    }
}

// ==================== RECALCULAR EDIÇÕES ====================

async function recalcularEdicoes() {
    if (!currentSeriesId || !currentSeries) {
        alert('Erro: Série não identificada');
        return;
    }
    
    const confirmacao = confirm(
        `⚠️ RECALCULAR EDIÇÕES BASEADO NA PLANILHA\n\n` +
        `Série: ${currentSeries.title}\n` +
        `Total (planilha): ${currentSeries.total_issues}\n\n` +
        `Isso vai:\n` +
        `• Deletar TODAS as edições atuais\n` +
        `• Criar edições de 1 até ${currentSeries.total_issues}\n` +
        `• Marcar as primeiras ${currentSeries.read_issues} como lidas\n\n` +
        `Confirmar?`
    );
    
    if (!confirmacao) return;
    
    // Mostrar loading no botão
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Recalculando...';
    button.disabled = true;
    
    try {
        // Deletar edições existentes
        const issuesExistentes = await fetchAPI(`/series/${currentSeriesId}/issues`);
        for (const issue of issuesExistentes) {
            await fetchAPI(`/series/${currentSeriesId}/issues/${issue.id}`, {
                method: 'DELETE'
            });
        }
        
        // Criar novas edições
        for (let i = 1; i <= currentSeries.total_issues; i++) {
            const isLida = i <= currentSeries.read_issues;
            
            await fetchAPI(`/series/${currentSeriesId}/issues`, {
                method: 'POST',
                body: JSON.stringify({
                    issue_number: i,
                    is_read: isLida
                })
            });
        }
        
        alert(`✅ ${currentSeries.total_issues} edições recriadas!`);
        
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
        
    } catch (error) {
        console.error('❌ Erro ao recalcular:', error);
        alert('Erro ao recalcular edições: ' + error.message);
    } finally {
        // Restaurar botão
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Sincronizar edições
async function sincronizarEdicoesAutomaticamente() {
    if (!currentSeriesId || !currentSeries) {
        alert('Erro: Série não identificada');
        return;
    }
    
    const confirmacao = confirm(
        `🔄 Sincronizar Edições\n\n` +
        `Criar ${currentSeries.total_issues} edições automaticamente?\n` +
        `• Edições 1 a ${currentSeries.read_issues}: Marcadas como LIDAS\n` +
        `• Edições ${currentSeries.read_issues + 1} a ${currentSeries.total_issues}: Não lidas\n\n` +
        `Confirmar?`
    );
    
    if (!confirmacao) return;
    
    // Mostrar loading no botão
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Sincronizando...';
    button.disabled = true;
    
    try {
        // Deletar existentes
        const issuesExistentes = await fetchAPI(`/series/${currentSeriesId}/issues`);
        for (const issue of issuesExistentes) {
            await fetchAPI(`/series/${currentSeriesId}/issues/${issue.id}`, {
                method: 'DELETE'
            });
        }
        
        // Criar novas
        for (let i = 1; i <= currentSeries.total_issues; i++) {
            await fetchAPI(`/series/${currentSeriesId}/issues`, {
                method: 'POST',
                body: JSON.stringify({
                    issue_number: i,
                    is_read: i <= currentSeries.read_issues
                })
            });
        }
        
        alert(`✅ ${currentSeries.total_issues} edições sincronizadas!`);
        
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
        
    } catch (error) {
        console.error('❌ Erro:', error);
        alert('Erro ao sincronizar: ' + error.message);
    } finally {
        // Restaurar botão
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Verificar sincronização
async function verificarSincronizacaoLendo() {
    if (!currentSeriesId) return;
    
    try {
        const issues = await fetchAPI(`/series/${currentSeriesId}/issues`);
        const lidas = issues.filter(i => i.is_read).length;
        const valorMostrado = currentSeries.read_issues;
        
        if (lidas === valorMostrado) {
            alert(`✅ Contador correto!\n\nEdições lidas: ${lidas}`);
        } else {
            const confirmacao = confirm(
                `⚠️ Dessincronização!\n\n` +
                `Edições lidas: ${lidas}\n` +
                `Contador: ${valorMostrado}\n\n` +
                `Recalcular?`
            );
            
            if (confirmacao) {
                await recalcularEdicoes();
            }
        }
    } catch (error) {
        alert('Erro ao verificar');
    }
}

// Toggle issue read status
async function toggleIssueRead(issueId, isRead) {
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues/${issueId}`, {
            method: 'PATCH',
            body: JSON.stringify({ is_read: isRead })
        });
        
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('❌ Error:', error);
        const checkbox = event.target;
        if (checkbox) {
            checkbox.checked = !isRead;
        }
        alert('Erro ao atualizar status');
    }
}

// Delete issue
async function deleteIssue(issueId, issueNumber) {
    if (!confirm(`Deletar edição #${issueNumber}?`)) return;
    
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues/${issueId}`, {
            method: 'DELETE',
        });
        
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('Error:', error);
        alert('Erro ao deletar edição');
    }
}

// Marcar todas as edições como lidas
async function marcarTodasComoLidas() {
    if (!currentSeriesId) {
        alert('Erro: Série não identificada');
        return;
    }
    
    if (!confirm('Marcar TODAS as edições como lidas?')) return;
    
    // Mostrar loading no botão
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Marcando...';
    button.disabled = true;
    
    try {
        const issues = await fetchAPI(`/series/${currentSeriesId}/issues`);
        
        for (const issue of issues) {
            if (!issue.is_read) {
                await fetchAPI(`/series/${currentSeriesId}/issues/${issue.id}`, {
                    method: 'PATCH',
                    body: JSON.stringify({ is_read: true })
                });
            }
        }
        
        alert('✅ Todas as edições marcadas como lidas!');
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('Error:', error);
        alert('Erro ao marcar edições como lidas');
    } finally {
        // Restaurar botão
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Marcar todas as edições como não lidas
async function marcarTodasComoNaoLidas() {
    if (!currentSeriesId) {
        alert('Erro: Série não identificada');
        return;
    }
    
    if (!confirm('Marcar TODAS as edições como NÃO lidas?')) return;
    
    // Mostrar loading no botão
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Marcando...';
    button.disabled = true;
    
    try {
        const issues = await fetchAPI(`/series/${currentSeriesId}/issues`);
        
        for (const issue of issues) {
            if (issue.is_read) {
                await fetchAPI(`/series/${currentSeriesId}/issues/${issue.id}`, {
                    method: 'PATCH',
                    body: JSON.stringify({ is_read: false })
                });
            }
        }
        
        alert('✅ Todas as edições marcadas como não lidas!');
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('Error:', error);
        alert('Erro ao marcar edições como não lidas');
    } finally {
        // Restaurar botão
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Marcar todas as edições como não baixadas (deletar todas)
async function marcarTodasComoNaoBaixadas() {
    if (!currentSeriesId) {
        alert('Erro: Série não identificada');
        return;
    }
    
    if (!confirm('⚠️ ATENÇÃO!\n\nIsso vai DELETAR TODAS as edições baixadas.\n\nTodas as edições ficarão cinzas (não baixadas).\n\nConfirma?')) return;
    
    // Mostrar loading no botão
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Deletando...';
    button.disabled = true;
    
    try {
        const issues = await fetchAPI(`/series/${currentSeriesId}/issues`);
        
        for (const issue of issues) {
            await fetchAPI(`/series/${currentSeriesId}/issues/${issue.id}`, {
                method: 'DELETE'
            });
        }
        
        alert('✅ Todas as edições marcadas como não baixadas!');
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('Error:', error);
        alert('Erro ao marcar edições como não baixadas');
    } finally {
        // Restaurar botão
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Adicionar edição como baixada (quando clicar no badge cinza)
async function addIssueDownloaded(issueNumber) {
    if (!currentSeriesId) {
        alert('Erro: Série não identificada');
        return;
    }
    
    try {
        const newIssue = await fetchAPI(`/series/${currentSeriesId}/issues`, {
            method: 'POST',
            body: JSON.stringify({
                issue_number: issueNumber,
                is_read: false
            })
        });
        
        console.log(`✅ Edição #${issueNumber} adicionada como baixada`);
        
        // Adicionar à pilha de undo
        addToUndoStack({
            type: 'add_issue',
            seriesId: currentSeriesId,
            issueId: newIssue.id,
            issueNumber: issueNumber
        });
        
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('Error:', error);
        alert('Erro ao adicionar edição');
    }
}

// Marcar edição como não baixada (transformar em badge cinza)
async function marcarComoNaoBaixada(issueId, issueNumber) {
    if (!confirm(`Marcar edição #${issueNumber} como NÃO baixada?\n\nIsso vai deletar a edição do sistema.`)) return;
    
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues/${issueId}`, {
            method: 'DELETE',
        });
        
        console.log(`✅ Edição #${issueNumber} marcada como não baixada`);
        
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('Error:', error);
        alert('Erro ao marcar edição como não baixada');
    }
}

// Toggle campos específicos de Saga
function toggleSagaFields() {
    const seriesType = document.getElementById('series_type').value;
    const sagaEditionsField = document.getElementById('saga-editions-field');
    const sagaIssuesDivision = document.getElementById('saga-issues-division');
    const seriesTotalField = document.getElementById('series-total-field');
    const completedLabelText = document.getElementById('completed-label-text');
    
    if (seriesType === 'saga') {
        sagaEditionsField.style.display = 'block';
        sagaIssuesDivision.style.display = 'block';
        seriesTotalField.style.display = 'none';
        completedLabelText.textContent = 'Saga completa (todas as edições já foram lançadas)';
    } else {
        sagaEditionsField.style.display = 'none';
        sagaIssuesDivision.style.display = 'none';
        seriesTotalField.style.display = 'block';
        completedLabelText.textContent = 'Série finalizada (não sairão mais edições)';
    }
}

// Atualizar total da saga automaticamente
function updateSagaTotal() {
    const mainIssues = parseInt(document.getElementById('main_issues').value) || 0;
    const tieInIssues = parseInt(document.getElementById('tie_in_issues').value) || 0;
    const total = mainIssues + tieInIssues;
    
    document.getElementById('saga-total-calculated').textContent = total;
    document.getElementById('total_issues').value = total;
}

// Modal Functions
function openModal(seriesId = null) {
    console.log('🔓 Abrindo modal...', seriesId ? `(editar ID: ${seriesId})` : '(novo)');
    
    const modal = document.getElementById('series-modal');
    const form = document.getElementById('series-form');
    const title = document.getElementById('modal-title');
    
    form.reset();
    
    if (seriesId) {
        title.textContent = 'Editar HQ';
        const series = allSeries.find(s => s.id === seriesId);
        if (series) {
            document.getElementById('series-id').value = series.id;
            document.getElementById('title').value = series.title;
            document.getElementById('author').value = series.author || '';
            document.getElementById('publisher').value = series.publisher || '';
            document.getElementById('total_issues').value = series.total_issues || 0;
            document.getElementById('series_type').value = series.series_type || 'em_andamento';
            document.getElementById('is_completed').checked = series.is_completed || false;
            document.getElementById('cover_url').value = series.cover_url || '';
            document.getElementById('notes').value = series.notes || '';
            document.getElementById('saga_editions').value = series.saga_editions || '';
            document.getElementById('main_issues').value = series.main_issues || 0;
            document.getElementById('tie_in_issues').value = series.tie_in_issues || 0;
            console.log('✅ Dados preenchidos');
        } else {
            console.error('❌ Série não encontrada:', seriesId);
        }
    } else {
        title.textContent = 'Nova HQ';
        document.getElementById('series-id').value = '';
    }
    
    // Mostrar/esconder campos de saga
    toggleSagaFields();
    
    // Atualizar total da saga se for edição
    if (seriesId) {
        updateSagaTotal();
    }
    
    modal.classList.add('active');
    console.log('✅ Modal aberto');
}

function closeModal() {
    const modal = document.getElementById('series-modal');
    modal.classList.remove('active');
}

async function submitSeriesForm(e) {
    e.preventDefault();
    
    const seriesId = document.getElementById('series-id').value;
    const data = {
        title: document.getElementById('title').value,
        author: document.getElementById('author').value || null,
        publisher: document.getElementById('publisher').value || null,
        total_issues: parseInt(document.getElementById('total_issues').value) || 0,
        series_type: document.getElementById('series_type').value,
        is_completed: document.getElementById('is_completed').checked,
        cover_url: document.getElementById('cover_url').value || null,
        notes: document.getElementById('notes').value || null,
        saga_editions: document.getElementById('saga_editions').value || null,
        main_issues: parseInt(document.getElementById('main_issues').value) || 0,
        tie_in_issues: parseInt(document.getElementById('tie_in_issues').value) || 0,
    };
    
    try {
        if (seriesId) {
            await fetchAPI(`/series/${seriesId}`, {
                method: 'PUT',
                body: JSON.stringify(data),
            });
        } else {
            await fetchAPI('/series', {
                method: 'POST',
                body: JSON.stringify(data),
            });
        }
        
        closeModal();
        loadSeries();
        loadStats();
    } catch (error) {
        console.error('Error:', error);
        alert('Erro ao salvar HQ: ' + error.message);
    }
}

function editSeries(seriesId) {
    openModal(seriesId);
}

function editarSerieAtual() {
    if (!currentSeriesId) {
        console.error('Nenhuma série selecionada');
        return;
    }
    openModal(currentSeriesId);
}

async function deleteSeries(seriesId, seriesTitle = 'esta HQ') {
    if (!confirm(`Deletar "${seriesTitle}"?`)) return;
    
    try {
        await fetchAPI(`/series/${seriesId}`, {
            method: 'DELETE',
        });
        
        goToHome();
        loadSeries();
        loadStats();
    } catch (error) {
        console.error('Error:', error);
        alert('Erro ao deletar HQ');
    }
}

// ==================== PAGINAÇÃO ====================

function updatePaginationControls() {
    const paginationContainer = document.getElementById('pagination-controls');
    if (!paginationContainer) return;
    
    // Se só tem uma página, esconder paginação
    if (totalPages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }
    
    paginationContainer.style.display = 'flex';
    
    // Atualizar informações
    const paginationInfo = document.getElementById('pagination-info');
    if (paginationInfo) {
        const startItem = (currentPage - 1) * perPage + 1;
        const endItem = Math.min(currentPage * perPage, totalItems);
        paginationInfo.textContent = `Mostrando ${startItem}-${endItem} de ${totalItems}`;
    }
    
    // Atualizar botões
    const btnFirst = document.getElementById('btn-first-page');
    const btnPrev = document.getElementById('btn-prev-page');
    const btnNext = document.getElementById('btn-next-page');
    const btnLast = document.getElementById('btn-last-page');
    
    if (btnFirst) btnFirst.disabled = currentPage === 1;
    if (btnPrev) btnPrev.disabled = currentPage === 1;
    if (btnNext) btnNext.disabled = currentPage === totalPages;
    if (btnLast) btnLast.disabled = currentPage === totalPages;
    
    // Atualizar páginas numéricas
    updatePageNumbers();
}

function updatePageNumbers() {
    const pageNumbersContainer = document.getElementById('page-numbers');
    if (!pageNumbersContainer) return;
    
    pageNumbersContainer.innerHTML = '';
    
    // Calcular quais páginas mostrar
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, currentPage + 2);
    
    // Ajustar se estiver no início ou fim
    if (currentPage <= 3) {
        endPage = Math.min(5, totalPages);
    }
    if (currentPage >= totalPages - 2) {
        startPage = Math.max(1, totalPages - 4);
    }
    
    // Adicionar primeira página e reticências
    if (startPage > 1) {
        addPageButton(1);
        if (startPage > 2) {
            addEllipsis();
        }
    }
    
    // Adicionar páginas do meio
    for (let i = startPage; i <= endPage; i++) {
        addPageButton(i);
    }
    
    // Adicionar reticências e última página
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            addEllipsis();
        }
        addPageButton(totalPages);
    }
}

function addPageButton(pageNum) {
    const pageNumbersContainer = document.getElementById('page-numbers');
    const button = document.createElement('button');
    button.className = 'page-number' + (pageNum === currentPage ? ' active' : '');
    button.textContent = pageNum;
    button.onclick = () => goToPage(pageNum);
    pageNumbersContainer.appendChild(button);
}

function addEllipsis() {
    const pageNumbersContainer = document.getElementById('page-numbers');
    const span = document.createElement('span');
    span.className = 'page-ellipsis';
    span.textContent = '...';
    pageNumbersContainer.appendChild(span);
}

function goToPage(page) {
    if (page < 1 || page > totalPages || page === currentPage) return;
    
    currentPage = page;
    
    // Obter o termo de busca atual
    const searchInput = document.getElementById('search-input');
    const searchTerm = searchInput ? searchInput.value : '';
    
    loadSeries(searchTerm, currentPage);
    
    // Scroll para o topo
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goToFirstPage() {
    goToPage(1);
}

function goToPrevPage() {
    goToPage(currentPage - 1);
}

function goToNextPage() {
    goToPage(currentPage + 1);
}

function goToLastPage() {
    goToPage(totalPages);
}

// ==================== RECALCULAR TODAS AS HQS ====================

async function recalcularTodasHQs(event) {
    if (!confirm('⚠️ ATENÇÃO!\n\nEsta ação irá recalcular TODAS as HQs, criando edições baseadas nos valores da planilha.\n\nIsso é útil após importar dados da planilha.\n\nAs HQs que já têm edições cadastradas serão ignoradas.\n\nDeseja continuar?')) {
        return;
    }
    
    // Pegar o botão que foi clicado
    const button = event ? event.target : document.querySelector('[onclick*="recalcularTodasHQs"]');
    
    if (!button) {
        console.error('Botão não encontrado');
        return;
    }
    
    // Mostrar loading
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Recalculando...';
    button.disabled = true;
    
    try {
        console.log('🔄 Iniciando recálculo de todas as HQs...');
        
        const result = await fetchAPI('/recalculate-all', {
            method: 'POST'
        });
        
        console.log('✅ Recálculo concluído:', result);
        
        // Mostrar resultado
        alert(`✅ Recálculo concluído!\n\n` +
              `📊 Total de HQs: ${result.total}\n` +
              `✅ Recalculadas: ${result.recalculated}\n` +
              `❌ Erros: ${result.errors}\n\n` +
              `As edições foram criadas baseadas nos valores da planilha.`);
        
        // Recarregar dados
        loadSeries();
        loadStats();
        
    } catch (error) {
        console.error('❌ Erro ao recalcular:', error);
        alert('❌ Erro ao recalcular HQs: ' + error.message);
    } finally {
        // Restaurar botão
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// ==================== STATS PANEL (FLUTUANTE) ====================

function toggleStatsPanel() {
    const panel = document.getElementById('stats-panel');
    const overlay = document.getElementById('stats-panel-overlay');
    
    if (panel && overlay) {
        if (panel.classList.contains('open')) {
            closeStatsPanel();
        } else {
            openStatsPanel();
        }
    }
}

function openStatsPanel() {
    const panel = document.getElementById('stats-panel');
    const overlay = document.getElementById('stats-panel-overlay');
    
    if (panel && overlay) {
        panel.classList.add('open');
        overlay.classList.add('open');
    }
}

function closeStatsPanel() {
    const panel = document.getElementById('stats-panel');
    const overlay = document.getElementById('stats-panel-overlay');
    
    if (panel && overlay) {
        panel.classList.remove('open');
        overlay.classList.remove('open');
    }
}

function updateStatsBadge(total) {
    const badge = document.getElementById('stats-fab-badge');
    if (badge) {
        badge.textContent = total || '0';
    }
}

// ==================== MODAL DE NOTAS ====================

function openNotesModal() {
    if (!currentSeries || !currentSeries.notes) {
        console.error('❌ Sem notas para exibir');
        return;
    }
    
    console.log('📝 Abrindo modal de notas...');
    
    const modal = document.getElementById('notes-modal');
    const notesContent = document.getElementById('notes-display-content');
    
    // Preencher conteúdo das notas
    notesContent.textContent = currentSeries.notes;
    
    // Abrir modal
    modal.style.display = 'flex';
}

function closeNotesModal() {
    console.log('🔒 Fechando modal de notas...');
    
    const modal = document.getElementById('notes-modal');
    modal.style.display = 'none';
}
