// API Configuration
const API_URL = window.location.origin;

// State
let currentFilter = 'all';
let currentSeriesId = null;
let allSeries = [];
let searchTimeout = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Iniciando aplicação...');
    console.log('📡 API URL:', API_URL);
    
    // Adicionar listener aos botões para debug
    const btnNova = document.querySelector('.btn-primary');
    if (btnNova) {
        console.log('✅ Botão "Nova HQ" encontrado');
    } else {
        console.error('❌ Botão "Nova HQ" NÃO encontrado!');
    }
    
    loadSeries();
    loadStats();
});

// Função para obter o label do tipo de série
function getSeriesTypeLabel(seriesType) {
    const types = {
        'finalizada': { text: 'Finalizada', class: 'type-finalizada', emoji: '✓' },
        'em_andamento': { text: 'Em Andamento', class: 'type-andamento', emoji: '📖' },
        'lancamento': { text: 'Lançamento', class: 'type-lancamento', emoji: '🆕' },
        'edicao_especial': { text: 'Edição Especial', class: 'type-especial', emoji: '⭐' }
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
async function loadSeries(filterQuery = '') {
    try {
        console.log('📚 Carregando séries...', filterQuery ? `(filtro: ${filterQuery})` : '');
        const endpoint = filterQuery ? `/series?search=${encodeURIComponent(filterQuery)}` : '/series';
        allSeries = await fetchAPI(endpoint);
        console.log(`✅ ${allSeries.length} séries carregadas`);
        displaySeries();
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
        
        // Atualizar com verificação
        const totalEl = document.getElementById('stat-total');
        const paraLerEl = document.getElementById('stat-para-ler');
        const lendoEl = document.getElementById('stat-lendo');
        const concluidasEl = document.getElementById('stat-concluidas');
        
        if (totalEl) totalEl.textContent = stats.total || 0;
        if (paraLerEl) paraLerEl.textContent = stats.para_ler || 0;
        if (lendoEl) lendoEl.textContent = stats.lendo || 0;
        if (concluidasEl) concluidasEl.textContent = stats.concluida || 0;
        
        console.log('✅ Estatísticas atualizadas:');
        console.log('   Total:', stats.total);
        console.log('   Para Ler:', stats.para_ler);
        console.log('   Lendo:', stats.lendo);
        console.log('   Concluídas:', stats.concluida);
    } catch (error) {
        console.error('❌ Error loading stats:', error);
        // Não mostrar erro pro usuário, apenas no console
    }
}

// Display Functions
function displaySeries() {
    const grid = document.getElementById('series-grid');
    const emptyState = document.getElementById('empty-state');
    
    // Filter series
    let filtered = allSeries;
    if (currentFilter !== 'all') {
        filtered = allSeries.filter(s => s.status === currentFilter);
    }
    
    if (filtered.length === 0) {
        grid.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }
    
    emptyState.style.display = 'none';
    grid.innerHTML = '';
    
    filtered.forEach(series => {
        const card = createSeriesCard(series);
        grid.appendChild(card);
    });
}

function createSeriesCard(series) {
    const card = document.createElement('div');
    card.className = 'comic-card';
    card.style.cursor = 'pointer';
    
    const statusClass = `status-${series.status}`;
    const statusText = getStatusText(series.status);
    
    const coverHTML = series.cover_url 
        ? `<img src="${series.cover_url}" alt="${series.title}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
           <div class="comic-cover-placeholder" style="display:none;">📖</div>`
        : `<div class="comic-cover-placeholder">📖</div>`;
    
    const progressPercent = series.total_issues > 0 
        ? Math.min((series.read_issues / series.total_issues) * 100, 100) 
        : 0;
    
    const progressClass = progressPercent === 100 ? 'completed' : 
                          progressPercent === 0 ? 'not-started' : '';
    
    const metaItems = [];
    if (series.author) metaItems.push(`✏️ ${series.author}`);
    if (series.publisher) metaItems.push(`📚 ${series.publisher}`);
    
    const metaHTML = metaItems.length > 0 
        ? metaItems.map(item => `<div>${item}</div>`).join('')
        : '';
    
    // Badge de tipo de série
    const typeBadge = createSeriesTypeBadge(series.series_type || 'em_andamento');
    
    card.innerHTML = `
        <div class="comic-cover" onclick="goToDetail(${series.id})">
            ${coverHTML}
            <div class="series-type-overlay">
                ${typeBadge}
            </div>
        </div>
        <div class="comic-info">
            <div class="comic-progress">
                <div class="progress-label">
                    <span>Progresso</span>
                    <span>${series.read_issues}/${series.total_issues} (${Math.round(progressPercent)}%)</span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar ${progressClass}" style="width: ${progressPercent}%"></div>
                </div>
            </div>
            <div class="comic-header" onclick="goToDetail(${series.id})">
                <h3 class="comic-title">${series.title}</h3>
                <div class="comic-meta">
                    ${metaHTML}
                </div>
            </div>
            <div class="series-stats-mini">
                <div class="stat-mini">
                    <span>Lendo:</span> <strong>${series.read_issues}</strong>
                </div>
                <div class="stat-mini">
                    <span>Baixadas:</span> <strong>${series.downloaded_issues}</strong>
                </div>
                <div class="stat-mini">
                    <span>Total:</span> <strong>${series.total_issues}</strong>
                </div>
            </div>
            <div class="comic-status-row">
                <span class="comic-status ${statusClass}">${statusText}</span>
                <div class="comic-actions">
                    <button class="btn-icon" onclick="event.stopPropagation(); editSeriesById(${series.id})" title="Editar">
                        ✏️
                    </button>
                    <button class="btn-icon" onclick="event.stopPropagation(); deleteSeries(${series.id}, '${series.title.replace(/'/g, "\\'")}');" title="Deletar">
                        🗑️
                    </button>
                </div>
            </div>
        </div>
    `;
    
    return card;
}

function getStatusText(status) {
    const statusMap = {
        'para_ler': 'Para Ler',
        'lendo': 'Lendo',
        'concluida': 'Concluída'
    };
    return statusMap[status] || status;
}

function showEmptyState() {
    const grid = document.getElementById('series-grid');
    const emptyState = document.getElementById('empty-state');
    
    grid.innerHTML = '';
    emptyState.style.display = 'block';
}

// Navigation
function goToHome() {
    console.log('🏠 Voltando para home');
    
    // Hide detail view
    document.getElementById('detail-view').style.display = 'none';
    document.getElementById('home-view').style.display = 'block';
    
    // Show stats and filters
    document.getElementById('stats-section').style.display = 'block';
    document.getElementById('filters-section').style.display = 'block';
    
    // Hide back button
    document.getElementById('btn-back').style.display = 'none';
    
    // Reload series
    currentSeriesId = null;
    loadSeries();
    loadStats();
}

async function goToDetail(seriesId) {
    console.log('📖 Abrindo detalhes da série:', seriesId);
    currentSeriesId = seriesId;
    
    // Hide home view
    document.getElementById('home-view').style.display = 'none';
    document.getElementById('detail-view').style.display = 'block';
    
    // Hide stats and filters
    document.getElementById('stats-section').style.display = 'none';
    document.getElementById('filters-section').style.display = 'none';
    
    // Show back button
    document.getElementById('btn-back').style.display = 'block';
    
    // Load series detail
    await loadSeriesDetail(seriesId);
}

async function loadSeriesDetail(seriesId) {
    try {
        console.log('📥 Carregando detalhes da série:', seriesId);
        const series = await fetchAPI(`/series/${seriesId}`);
        const issues = await fetchAPI(`/series/${seriesId}/issues`);
        
        console.log('✅ Série carregada:', series);
        console.log('✅ Edições carregadas:', issues.length);
        
        // Título
        const typeInfo = getSeriesTypeLabel(series.series_type || 'em_andamento');
        const titleElement = document.getElementById('detail-title');
        titleElement.innerHTML = `
            ${series.title}
            <span class="series-type-badge ${typeInfo.class}" style="margin-left: 10px; font-size: 0.5em; vertical-align: middle;">
                ${typeInfo.emoji} ${typeInfo.text}
            </span>
        `;
        
        // Autor e editora
        document.getElementById('detail-author').textContent = series.author ? `✏️ ${series.author}` : '';
        document.getElementById('detail-publisher').textContent = series.publisher ? `📚 ${series.publisher}` : '';
        
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
        const progressPercent = series.total_issues > 0 
            ? Math.min((series.read_issues / series.total_issues) * 100, 100) 
            : 0;
        
        document.getElementById('detail-progress').textContent = 
            `${series.read_issues}/${series.total_issues} edições (${Math.round(progressPercent)}%)`;
        document.getElementById('detail-progress-bar').style.width = `${progressPercent}%`;
        
        // Stats
        document.getElementById('detail-reading').textContent = series.read_issues;
        document.getElementById('detail-downloaded').textContent = series.downloaded_issues;
        document.getElementById('detail-total').textContent = series.total_issues;
        
        // Edições
        displayIssues(issues);
    } catch (error) {
        console.error('Error loading series detail:', error);
        alert('Erro ao carregar detalhes da série.');
        goToHome();
    }
}

function displayIssues(issues) {
    const issuesList = document.getElementById('issues-list');
    const emptyIssues = document.getElementById('empty-issues');
    
    console.log('📖 Exibindo', issues.length, 'edições');
    
    if (!issues || issues.length === 0) {
        issuesList.innerHTML = '';
        emptyIssues.style.display = 'block';
        return;
    }
    
    emptyIssues.style.display = 'none';
    issuesList.innerHTML = '';
    
    // Ordenar por número
    const sortedIssues = [...issues].sort((a, b) => a.issue_number - b.issue_number);
    
    sortedIssues.forEach(issue => {
        const issueCard = document.createElement('div');
        issueCard.className = `issue-card ${issue.is_read ? 'read' : ''}`;
        
        issueCard.innerHTML = `
            <div class="issue-number">#${issue.issue_number}</div>
            <div class="issue-info">
                <div class="issue-title">${issue.title || `Edição #${issue.issue_number}`}</div>
                ${issue.date_read ? `<div class="issue-date">Lida em ${new Date(issue.date_read).toLocaleDateString('pt-BR')}</div>` : ''}
            </div>
            <div class="issue-actions">
                <label class="checkbox-icon" title="${issue.is_read ? 'Marcar como não lida' : 'Marcar como lida'}">
                    <input type="checkbox" ${issue.is_read ? 'checked' : ''} onchange="toggleIssueRead(${issue.id}, this.checked)">
                    <span class="checkmark">${issue.is_read ? '✓' : ''}</span>
                </label>
                <button class="btn-icon btn-delete" onclick="deleteIssue(${issue.id}, ${issue.issue_number})" title="Deletar edição">
                    🗑️
                </button>
            </div>
        `;
        
        issuesList.appendChild(issueCard);
    });
}

// Filter
function filterSeries(filter) {
    console.log('🔍 Filtrando por:', filter);
    currentFilter = filter;
    
    // Update active tab
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.filter === filter) {
            tab.classList.add('active');
        }
    });
    
    displaySeries();
}

// Search
function handleSearch() {
    const searchInput = document.getElementById('search-input');
    const searchClear = document.getElementById('search-clear');
    const query = searchInput.value.trim();
    
    // Show/hide clear button
    searchClear.style.display = query ? 'block' : 'none';
    
    // Debounce search
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        console.log('🔍 Buscando:', query);
        loadSeries(query);
    }, 300);
}

function clearSearch() {
    console.log('🔍 Limpando busca');
    document.getElementById('search-input').value = '';
    document.getElementById('search-clear').style.display = 'none';
    loadSeries();
}

// Modal Functions
function openModal() {
    console.log('📝 Abrindo modal de série');
    const modal = document.getElementById('series-modal');
    if (!modal) {
        console.error('❌ Modal não encontrado!');
        return;
    }
    modal.classList.add('active');
    document.getElementById('series-form').reset();
    document.getElementById('series-id').value = '';
    document.getElementById('modal-title').textContent = 'Nova HQ';
}

function closeModal() {
    console.log('❌ Fechando modal de série');
    document.getElementById('series-modal').classList.remove('active');
}

function openAddIssueModal() {
    console.log('📝 Abrindo modal de edição');
    const modal = document.getElementById('issue-modal');
    if (!modal) {
        console.error('❌ Modal de edição não encontrado!');
        return;
    }
    modal.classList.add('active');
    document.getElementById('issue-form').reset();
}

function closeIssueModal() {
    console.log('❌ Fechando modal de edição');
    document.getElementById('issue-modal').classList.remove('active');
}

// Form Submissions
async function submitSeriesForm(event) {
    event.preventDefault();
    
    console.log('💾 Salvando série...');
    
    const seriesId = document.getElementById('series-id').value;
    const formData = {
        title: document.getElementById('title').value,
        author: document.getElementById('author').value || null,
        publisher: document.getElementById('publisher').value || null,
        total_issues: parseInt(document.getElementById('total_issues').value) || 0,
        downloaded_issues: parseInt(document.getElementById('downloaded_issues').value) || 0,
        read_issues: parseInt(document.getElementById('read_issues').value) || 0,
        is_completed: document.getElementById('is_completed').checked,
        series_type: document.getElementById('series_type').value,
        cover_url: document.getElementById('cover_url').value || null,
        notes: document.getElementById('notes').value || null,
    };
    
    try {
        if (seriesId) {
            console.log('📝 Atualizando série:', seriesId);
            await fetchAPI(`/series/${seriesId}`, {
                method: 'PUT',
                body: JSON.stringify(formData),
            });
        } else {
            console.log('➕ Criando nova série');
            await fetchAPI('/series', {
                method: 'POST',
                body: JSON.stringify(formData),
            });
        }
        
        console.log('✅ Série salva!');
        closeModal();
        
        if (currentSeriesId && seriesId === currentSeriesId.toString()) {
            loadSeriesDetail(currentSeriesId);
        } else {
            loadSeries();
        }
        loadStats();
    } catch (error) {
        console.error('Error submitting form:', error);
        alert('Erro ao salvar HQ: ' + error.message);
    }
}

async function submitIssueForm(event) {
    event.preventDefault();
    
    if (!currentSeriesId) {
        console.error('❌ Nenhuma série selecionada!');
        return;
    }
    
    console.log('💾 Adicionando edição...');
    
    const formData = {
        issue_number: parseInt(document.getElementById('issue_number').value),
        is_read: document.getElementById('is_read').checked,
    };
    
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues`, {
            method: 'POST',
            body: JSON.stringify(formData),
        });
        
        console.log('✅ Edição adicionada!');
        closeIssueModal();
        loadSeriesDetail(currentSeriesId);
        loadStats();
    } catch (error) {
        console.error('Error adding issue:', error);
        alert('Erro ao adicionar edição: ' + error.message);
    }
}

// Edit/Delete Functions
async function editSeriesById(seriesId) {
    try {
        console.log('✏️ Editando série:', seriesId);
        const series = await fetchAPI(`/series/${seriesId}`);
        
        document.getElementById('series-id').value = series.id;
        document.getElementById('modal-title').textContent = 'Editar HQ';
        document.getElementById('title').value = series.title;
        document.getElementById('author').value = series.author || '';
        document.getElementById('publisher').value = series.publisher || '';
        document.getElementById('total_issues').value = series.total_issues;
        document.getElementById('downloaded_issues').value = series.downloaded_issues;
        document.getElementById('read_issues').value = series.read_issues;
        document.getElementById('is_completed').checked = series.is_completed;
        document.getElementById('series_type').value = series.series_type || 'em_andamento';
        document.getElementById('cover_url').value = series.cover_url || '';
        document.getElementById('notes').value = series.notes || '';
        
        openModal();
    } catch (error) {
        console.error('Error loading series for edit:', error);
        alert('Erro ao carregar série para edição.');
    }
}

function editSeries() {
    if (currentSeriesId) {
        editSeriesById(currentSeriesId);
    }
}

async function deleteSeries(seriesId, title) {
    if (!confirm(`Tem certeza que deseja deletar "${title}"?`)) {
        return;
    }
    
    try {
        console.log('🗑️ Deletando série:', seriesId);
        await fetchAPI(`/series/${seriesId}`, {
            method: 'DELETE',
        });
        
        console.log('✅ Série deletada!');
        
        if (currentSeriesId === seriesId) {
            goToHome();
        } else {
            loadSeries();
            loadStats();
        }
    } catch (error) {
        console.error('Error deleting series:', error);
        alert('Erro ao deletar HQ: ' + error.message);
    }
}

async function deleteIssue(issueId, issueNumber) {
    if (!confirm(`Tem certeza que deseja deletar a edição #${issueNumber}?`)) {
        return;
    }
    
    try {
        console.log('🗑️ Deletando edição:', issueId);
        await fetchAPI(`/issues/${issueId}`, {
            method: 'DELETE',
        });
        
        console.log('✅ Edição deletada!');
        
        if (currentSeriesId) {
            loadSeriesDetail(currentSeriesId);
            loadStats();
        }
    } catch (error) {
        console.error('Error deleting issue:', error);
        alert('Erro ao deletar edição: ' + error.message);
    }
}

async function toggleIssueRead(issueId, isRead) {
    try {
        console.log('✓ Marcando edição como', isRead ? 'lida' : 'não lida');
        await fetchAPI(`/issues/${issueId}`, {
            method: 'PUT',
            body: JSON.stringify({ is_read: isRead }),
        });
        
        if (currentSeriesId) {
            loadSeriesDetail(currentSeriesId);
            loadStats();
        }
    } catch (error) {
        console.error('Error toggling issue:', error);
        alert('Erro ao atualizar edição.');
    }
}

console.log('✅ Script carregado! API URL:', API_URL);
console.log('🔧 Versão: 2.1 - Debug completo');
