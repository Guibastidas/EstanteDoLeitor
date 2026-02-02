// API Configuration
const API_URL = 'https://estantedoleitor.up.railway.app/';

// State
let currentFilter = 'all';
let currentSeriesId = null;
let allSeries = [];
let searchTimeout = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
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
        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        alert('Erro ao conectar com o servidor. Certifique-se de que o backend está rodando.');
        throw error;
    }
}

// Navigation
function goToHome() {
    document.getElementById('home-view').style.display = 'block';
    document.getElementById('detail-view').style.display = 'none';
    document.getElementById('filters-section').style.display = 'block';
    document.getElementById('stats-section').style.display = 'block';
    document.getElementById('btn-back').style.display = 'none';
    document.getElementById('header-actions').style.display = 'flex';
    currentSeriesId = null;
    loadSeries();
}

function goToDetail(seriesId) {
    currentSeriesId = seriesId;
    document.getElementById('home-view').style.display = 'none';
    document.getElementById('detail-view').style.display = 'block';
    document.getElementById('filters-section').style.display = 'none';
    document.getElementById('stats-section').style.display = 'none';
    document.getElementById('btn-back').style.display = 'inline-flex';
    document.getElementById('header-actions').style.display = 'none';
    loadSeriesDetail(seriesId);
}

// Search
function handleSearch() {
    clearTimeout(searchTimeout);
    const query = document.getElementById('search-input').value;
    const clearBtn = document.getElementById('search-clear');
    
    // Mostrar ou ocultar botão X
    if (query.trim()) {
        clearBtn.style.display = 'block';
    } else {
        clearBtn.style.display = 'none';
    }
    
    searchTimeout = setTimeout(() => {
        if (query.trim()) {
            loadSeries(query);
        } else {
            loadSeries();
        }
    }, 300);
}

function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('search-clear').style.display = 'none';
    loadSeries();
}

// Stats
async function loadStats() {
    try {
        const stats = await fetchAPI('/stats');
        document.getElementById('stat-para-ler').textContent = stats.para_ler;
        document.getElementById('stat-lendo').textContent = stats.lendo;
        document.getElementById('stat-concluidas').textContent = stats.concluidas;
        document.getElementById('stat-total').textContent = stats.total;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Series List
async function loadSeries(search = null) {
    try {
        const endpoint = search ? `/series?search=${encodeURIComponent(search)}` : '/series';
        const series = await fetchAPI(endpoint);
        allSeries = series;
        displaySeries(series);
    } catch (error) {
        console.error('Error loading series:', error);
    }
}

function displaySeries(series) {
    const grid = document.getElementById('series-grid');
    const emptyState = document.getElementById('empty-state');
    
    grid.innerHTML = '';
    
    if (series.length === 0) {
        emptyState.classList.add('show');
        return;
    }
    
    emptyState.classList.remove('show');
    
    series.forEach((s) => {
        const card = createSeriesCard(s);
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
    const statusTexts = {
        'para_ler': 'Para Ler',
        'lendo': 'Lendo',
        'concluida': 'Concluída'
    };
    return statusTexts[status] || status;
}

function filterSeries(filter) {
    currentFilter = filter;
    
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');
    
    if (filter === 'all') {
        displaySeries(allSeries);
    } else {
        const filtered = allSeries.filter(s => s.status === filter);
        displaySeries(filtered);
    }
}

// Series Detail
async function loadSeriesDetail(seriesId) {
    try {
        const series = await fetchAPI(`/series/${seriesId}`);
        const issues = await fetchAPI(`/series/${seriesId}/issues`);
        
        displaySeriesDetail(series, issues);
    } catch (error) {
        console.error('Error loading series detail:', error);
    }
}

function displaySeriesDetail(series, issues) {
    // Título com badge de tipo
    const typeInfo = getSeriesTypeLabel(series.series_type || 'em_andamento');
    const titleElement = document.getElementById('detail-title');
    titleElement.innerHTML = `
        ${series.title}
        <span class="series-type-badge ${typeInfo.class}" style="margin-left: 10px; font-size: 0.5em; vertical-align: middle;">
            ${typeInfo.emoji} ${typeInfo.text}
        </span>
    `;
    
    if (series.cover_url) {
        document.getElementById('detail-cover').src = series.cover_url;
        document.getElementById('detail-cover').style.display = 'block';
        document.getElementById('detail-cover').nextElementSibling.style.display = 'none';
    } else {
        document.getElementById('detail-cover').style.display = 'none';
        document.getElementById('detail-cover').nextElementSibling.style.display = 'flex';
    }
    
    document.getElementById('detail-author').textContent = series.author ? `✏️ ${series.author}` : '';
    document.getElementById('detail-publisher').textContent = series.publisher ? `📚 ${series.publisher}` : '';
    
    const progressPercent = series.total_issues > 0 
        ? Math.min((series.read_issues / series.total_issues) * 100, 100) 
        : 0;
    
    document.getElementById('detail-progress').textContent = 
        `${series.read_issues}/${series.total_issues} edições (${Math.round(progressPercent)}%)`;
    
    const progressBar = document.getElementById('detail-progress-bar');
    progressBar.style.width = `${progressPercent}%`;
    progressBar.className = 'progress-bar';
    if (progressPercent === 100) progressBar.classList.add('completed');
    else if (progressPercent === 0) progressBar.classList.add('not-started');
    
    document.getElementById('detail-reading').textContent = series.read_issues;
    document.getElementById('detail-downloaded').textContent = series.downloaded_issues;
    document.getElementById('detail-total').textContent = series.total_issues;
    
    displayIssues(issues, series);
}

function displayIssues(issues, series) {
    const list = document.getElementById('issues-list');
    const emptyState = document.getElementById('empty-issues');
    
    list.innerHTML = '';
    
    // Criar cards baseado no total_issues, não no downloaded
    const totalIssues = series.total_issues || 0;
    
    if (totalIssues === 0) {
        emptyState.style.display = 'block';
        return;
    }
    
    emptyState.style.display = 'none';
    
    // Mapear as issues existentes por número
    const issuesMap = {};
    issues.forEach(issue => {
        issuesMap[issue.issue_number] = issue;
    });
    
    // Descobrir qual é a edição atual sendo lida
    const readIssuesNumbers = issues.filter(i => i.is_read).map(i => i.issue_number);
    const currentReadingIssue = readIssuesNumbers.length > 0 ? Math.max(...readIssuesNumbers) + 1 : 0;
    
    // Criar cards para todas as edições até o total
    for (let i = 1; i <= totalIssues; i++) {
        const existingIssue = issuesMap[i];
        const isDownloaded = existingIssue ? existingIssue.is_downloaded : (i <= series.downloaded_issues);
        const isRead = existingIssue ? existingIssue.is_read : false;
        
        const issueData = existingIssue || {
            id: null,
            issue_number: i,
            is_read: isRead,
            is_downloaded: isDownloaded
        };
        
        const item = createIssueItem(issueData, series, currentReadingIssue);
        list.appendChild(item);
    }
}

function createIssueItem(issue, series, currentReadingIssue) {
    const item = document.createElement('div');
    
    // Determinar a classe baseada no status
    let statusClass = '';
    if (issue.is_read) {
        statusClass = 'read'; // Verde - já lida
    } else if (currentReadingIssue > 0 && issue.issue_number === currentReadingIssue && issue.is_downloaded) {
        statusClass = 'reading'; // Amarelo - lendo agora (e baixada)
    } else if (issue.issue_number > series.downloaded_issues) {
        statusClass = 'not-downloaded'; // Cinza - não baixada (número maior que downloaded)
    } else if (issue.is_downloaded) {
        statusClass = 'not-read'; // Vermelho - baixada mas não lida
    } else {
        statusClass = 'not-downloaded'; // Cinza - não baixada
    }
    
    item.className = `issue-item ${statusClass}`;
    
    // Se a edição não existe no banco (id null), criar botões desabilitados
    if (issue.id === null) {
        item.innerHTML = `
            <div class="issue-number-medium">#${issue.issue_number}</div>
            <div class="issue-buttons">
                <button class="btn-status-issue" disabled title="Adicione esta edição primeiro">
                    ○
                </button>
                <button class="btn-delete-issue" disabled title="Edição não adicionada">
                    🗑️
                </button>
            </div>
        `;
    } else {
        item.innerHTML = `
            <div class="issue-number-medium">#${issue.issue_number}</div>
            <div class="issue-buttons">
                <button class="btn-status-issue" onclick="event.stopPropagation(); toggleIssueRead(${issue.id}, ${!issue.is_read})" title="${issue.is_read ? 'Marcar como não lida' : 'Marcar como lida'}">
                    ${issue.is_read ? '✓' : '○'}
                </button>
                <button class="btn-delete-issue" onclick="event.stopPropagation(); deleteIssue(${issue.id})" title="Deletar edição">
                    🗑️
                </button>
            </div>
        `;
    }
    
    return item;
}

async function toggleIssueRead(issueId, isRead) {
    try {
        await fetchAPI(`/issues/${issueId}?is_read=${isRead}`, {
            method: 'PUT',
        });
        
        loadSeriesDetail(currentSeriesId);
        loadStats();
    } catch (error) {
        console.error('Error toggling issue:', error);
    }
}

async function deleteIssue(issueId) {
    if (!confirm('Tem certeza que deseja deletar esta edição?')) {
        return;
    }
    
    try {
        await fetchAPI(`/issues/${issueId}`, {
            method: 'DELETE',
        });
        
        loadSeriesDetail(currentSeriesId);
        loadStats();
    } catch (error) {
        console.error('Error deleting issue:', error);
    }
}

// Series Modal
function openModal() {
    document.getElementById('modal-title').textContent = 'Nova HQ';
    document.getElementById('series-form').reset();
    document.getElementById('series-id').value = '';
    document.getElementById('series_type').value = 'em_andamento'; // Valor padrão
    document.getElementById('series-modal').classList.add('show');
}

function closeModal() {
    document.getElementById('series-modal').classList.remove('show');
}

function editSeries() {
    editSeriesById(currentSeriesId);
}

async function editSeriesById(seriesId) {
    try {
        const series = await fetchAPI(`/series/${seriesId}`);
        
        document.getElementById('modal-title').textContent = 'Editar HQ';
        document.getElementById('series-id').value = series.id;
        document.getElementById('title').value = series.title || '';
        document.getElementById('author').value = series.author || '';
        document.getElementById('publisher').value = series.publisher || '';
        document.getElementById('read_issues').value = series.read_issues || 0;
        document.getElementById('downloaded_issues').value = series.downloaded_issues || 0;
        document.getElementById('total_issues').value = series.total_issues || 0;
        document.getElementById('is_completed').checked = series.is_completed || false;
        document.getElementById('series_type').value = series.series_type || 'em_andamento';
        document.getElementById('cover_url').value = series.cover_url || '';
        document.getElementById('notes').value = series.notes || '';
        
        document.getElementById('series-modal').classList.add('show');
    } catch (error) {
        console.error('Error loading series:', error);
    }
}

async function submitSeriesForm(event) {
    event.preventDefault();
    
    const seriesId = document.getElementById('series-id').value;
    
    const formData = {
        title: document.getElementById('title').value,
        author: document.getElementById('author').value || null,
        publisher: document.getElementById('publisher').value || null,
        read_issues: parseInt(document.getElementById('read_issues').value) || 0,
        downloaded_issues: parseInt(document.getElementById('downloaded_issues').value) || 0,
        total_issues: parseInt(document.getElementById('total_issues').value) || 0,
        is_completed: document.getElementById('is_completed').checked,
        series_type: document.getElementById('series_type').value,
        cover_url: document.getElementById('cover_url').value || null,
        notes: document.getElementById('notes').value || null,
    };
    
    try {
        if (seriesId) {
            await fetchAPI(`/series/${seriesId}`, {
                method: 'PUT',
                body: JSON.stringify(formData),
            });
        } else {
            await fetchAPI('/series', {
                method: 'POST',
                body: JSON.stringify(formData),
            });
        }
        
        closeModal();
        loadSeries();
        loadStats();
        
        if (currentSeriesId) {
            loadSeriesDetail(currentSeriesId);
        }
    } catch (error) {
        console.error('Error saving series:', error);
    }
}

async function deleteSeries(seriesId, title) {
    if (!confirm(`Tem certeza que deseja deletar "${title}" e todas as suas edições?`)) {
        return;
    }
    
    try {
        await fetchAPI(`/series/${seriesId}`, {
            method: 'DELETE',
        });
        
        loadSeries();
        loadStats();
    } catch (error) {
        console.error('Error deleting series:', error);
    }
}

// Issue Modal
function openAddIssueModal() {
    document.getElementById('issue-form').reset();
    document.getElementById('issue-modal').classList.add('show');
}

function closeIssueModal() {
    document.getElementById('issue-modal').classList.remove('show');
}

async function submitIssueForm(event) {
    event.preventDefault();
    
    const issueNumber = parseInt(document.getElementById('issue_number').value);
    const isRead = document.getElementById('is_read').checked;
    
    const formData = {
        issue_number: issueNumber,
        is_read: isRead,
        is_downloaded: true,
    };
    
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues`, {
            method: 'POST',
            body: JSON.stringify(formData),
        });
        
        closeIssueModal();
        loadSeriesDetail(currentSeriesId);
        loadStats();
    } catch (error) {
        console.error('Error adding issue:', error);
        alert('Erro ao adicionar edição. Verifique se o número já não existe.');
    }
}

// Função para exportar dados para Excel
async function exportToExcel() {
    const btn = event.target;
    const originalText = btn.innerHTML;
    btn.innerHTML = '⏳ Exportando...';
    btn.disabled = true;
    
    try {
        const response = await fetch(`${API_URL}/export-excel`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Erro ao exportar dados');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Planilha_de_HQs_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        alert('✓ Planilha exportada com sucesso!');
    } catch (error) {
        console.error('Error exporting:', error);
        alert('❌ Erro ao exportar planilha. Tente novamente.');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

console.log('✓ HQ Manager v2.1 carregado com sucesso!');
