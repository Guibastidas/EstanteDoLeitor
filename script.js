// API Configuration
const API_URL = window.location.origin;

// State
let currentFilter = 'all';
let currentSeriesId = null;
let allSeries = [];
let searchTimeout = null;
let currentSeries = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Iniciando aplicação...');
    console.log('📡 API URL:', API_URL);
    
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
    
    // Filtrar séries
    let filteredSeries = allSeries;
    
    if (currentFilter === 'para_ler') {
        filteredSeries = allSeries.filter(s => s.read_issues === 0);
    } else if (currentFilter === 'lendo') {
        filteredSeries = allSeries.filter(s => s.read_issues > 0 && s.read_issues < s.total_issues);
    } else if (currentFilter === 'concluida') {
        filteredSeries = allSeries.filter(s => s.read_issues >= s.total_issues && s.total_issues > 0);
    }
    
    console.log(`🔍 Filtro "${currentFilter}": ${filteredSeries.length} séries`);
    
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
    card.onclick = () => showSeriesDetail(series.id);
    
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
    
    card.innerHTML = `
        <div class="comic-cover">
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
            ${series.publisher ? `<p class="comic-publisher">📚 ${series.publisher}</p>` : ''}
            
            <div class="comic-stats">
                <span>Lendo: <strong>${series.read_issues}</strong></span>
                <span>Baixadas: <strong>${series.downloaded_issues}</strong></span>
                <span>Total: <strong>${series.total_issues}</strong></span>
            </div>
            
            <div class="comic-status-row">
                <div class="comic-status ${statusClass}">${statusText}</div>
            </div>
        </div>
    `;
    
    return card;
}

function showEmptyState() {
    const grid = document.getElementById('series-grid');
    const emptyState = document.getElementById('empty-state');
    
    grid.style.display = 'none';
    emptyState.style.display = 'block';
}

// Filter Functions
function filterSeries(filter) {
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
    clearTimeout(searchTimeout);
    const searchInput = document.getElementById('search-input');
    const query = searchInput.value.trim();
    
    // Mostrar/esconder botão de limpar
    const clearBtn = document.getElementById('search-clear');
    if (query) {
        clearBtn.style.display = 'block';
    } else {
        clearBtn.style.display = 'none';
    }
    
    // Debounce
    searchTimeout = setTimeout(() => {
        loadSeries(query);
    }, 300);
}

function clearSearch() {
    const searchInput = document.getElementById('search-input');
    searchInput.value = '';
    document.getElementById('search-clear').style.display = 'none';
    loadSeries();
}

// Series Detail
async function showSeriesDetail(seriesId) {
    currentSeriesId = seriesId;
    await loadSeriesDetail(seriesId);
}

async function loadSeriesDetail(seriesId) {
    try {
        console.log('📖 Carregando detalhes da série:', seriesId);
        
        const [series, issues] = await Promise.all([
            fetchAPI(`/series/${seriesId}`),
            fetchAPI(`/series/${seriesId}/issues`)
        ]);
        
        currentSeries = series;
        
        // CONFIGURAÇÃO DE EXCEÇÕES - Edições antigas que você NÃO leu inicialmente
        const excecoesLeitura = {
            'asa noturna': 121,
            'nightwing': 121,
            'action comics': 1075,
            'detective comics': 1090
        };
        
        // Verificar se a série tem exceção
        let edicaoMinimaLida = 1;
        for (const [nomeSerie, edicaoMinima] of Object.entries(excecoesLeitura)) {
            if (series.title.toLowerCase().includes(nomeSerie)) {
                edicaoMinimaLida = edicaoMinima;
                console.log(`⚠️ EXCEÇÃO: ${series.title} - Mostrando progresso a partir da #${edicaoMinima}`);
                break;
            }
        }
        
        // Calcular progresso considerando APENAS as edições LIDAS
        const totalLidas = issues.filter(i => i.is_read).length;
        const totalBaixado = issues.length;
        const totalPublicado = series.total_issues;
        
        const progressPercent = totalPublicado > 0 
            ? Math.round((totalLidas / totalPublicado) * 100)
            : 0;
        
        console.log('📊 Progresso:', {
            lidas: totalLidas,
            baixadas: totalBaixado,
            publicadas: totalPublicado,
            percentual: progressPercent
        });
        
        // Atualizar UI
        document.getElementById('detail-cover').src = series.cover_url || '';
        document.getElementById('detail-title').textContent = series.title;
        document.getElementById('detail-author').textContent = series.author ? `✍️ ${series.author}` : '';
        document.getElementById('detail-publisher').textContent = series.publisher ? `📚 ${series.publisher}` : '';
        
        // Progresso
        let progressText = `${totalLidas}/${totalPublicado} edições (${progressPercent}%)`;
        if (edicaoMinimaLida > 1) {
            progressText += ` - Contando todas as edições lidas`;
        }
        document.getElementById('detail-progress').textContent = progressText;
        document.getElementById('detail-progress-bar').style.width = `${progressPercent}%`;
        
        document.getElementById('detail-reading').textContent = totalLidas;
        document.getElementById('detail-downloaded').textContent = totalBaixado;
        document.getElementById('detail-total').textContent = totalPublicado;
        
        // Mostrar detail view
        document.getElementById('home-view').style.display = 'none';
        document.getElementById('detail-view').style.display = 'block';
        document.getElementById('stats-section').style.display = 'none';
        document.getElementById('filters-section').style.display = 'none';
        document.getElementById('btn-back').style.display = 'inline-block';
        document.getElementById('header-actions').style.display = 'none';
        
        displayIssues(issues, totalBaixado, totalPublicado);
    } catch (error) {
        console.error('Error loading series detail:', error);
        alert('Erro ao carregar detalhes da série');
    }
}

function displayIssues(issues, totalBaixado, totalPublicado) {
    const issuesList = document.getElementById('issues-list');
    const emptyIssues = document.getElementById('empty-issues');
    
    console.log('📖 Exibindo edições');
    console.log('📊 Total baixado:', totalBaixado, '| Total publicado:', totalPublicado);
    
    if (!totalPublicado || totalPublicado === 0) {
        issuesList.innerHTML = '';
        emptyIssues.style.display = 'block';
        return;
    }
    
    emptyIssues.style.display = 'none';
    issuesList.innerHTML = '';
    
    // CONFIGURAÇÃO DE EXCEÇÕES
    const serieAtual = allSeries.find(s => s.id === currentSeriesId);
    const nomeSerieAtual = serieAtual ? serieAtual.title.toLowerCase() : '';
    
    const excecoesLeitura = {
        'asa noturna': 121,
        'nightwing': 121,
        'action comics': 1075,
        'detective comics': 1090
    };
    
    let edicaoMinimaLida = 1;
    for (const [nomeSerie, edicaoMinima] of Object.entries(excecoesLeitura)) {
        if (nomeSerieAtual.includes(nomeSerie)) {
            edicaoMinimaLida = edicaoMinima;
            console.log(`⚠️ EXCEÇÃO detectada: ${nomeSerieAtual} - Edições antes da #${edicaoMinima} aparecem em vermelho por padrão`);
            break;
        }
    }
    
    // Criar todas as edições até o total publicado
    const allIssueCards = [];
    
    for (let numero = 1; numero <= totalPublicado; numero++) {
        const issue = (issues || []).find(i => i.issue_number === numero);
        
        const issueCard = document.createElement('div');
        
        // 🎨 SISTEMA DE CORES:
        // 🟢 VERDE = Lida (is_read = true)
        // 🟡 AMARELO = Baixada mas não lida (existe no sistema, is_read = false)
        // 🔴 VERMELHO = Não baixada (não existe) OU edição antiga não lida
        
        let colorClass = '';
        let titleText = '';
        let actionsHTML = '';
        
        if (issue) {
            // Edição EXISTE no sistema
            if (issue.is_read) {
                // 🟢 LIDA = VERDE
                colorClass = 'issue-lida';
                titleText = `Edição #${numero}`;
                actionsHTML = `
                    <label class="checkbox-icon" title="Marcar como não lida">
                        <input type="checkbox" checked onchange="toggleIssueRead(${issue.id}, this.checked)">
                        <span class="checkmark">✓</span>
                    </label>
                    <button class="btn-icon btn-delete" onclick="deleteIssue(${issue.id}, ${numero})" title="Deletar edição">
                        🗑️
                    </button>
                `;
            } else if (numero < edicaoMinimaLida) {
                // 🔴 Edição antiga NÃO lida = VERMELHO (mas pode marcar como lida!)
                colorClass = 'issue-faltante';
                titleText = `Edição #${numero} - Não lida (anterior ao início)`;
                actionsHTML = `
                    <label class="checkbox-icon" title="Marcar como lida">
                        <input type="checkbox" onchange="toggleIssueRead(${issue.id}, this.checked)">
                        <span class="checkmark"></span>
                    </label>
                    <button class="btn-icon btn-delete" onclick="deleteIssue(${issue.id}, ${numero})" title="Deletar edição">
                        🗑️
                    </button>
                `;
            } else {
                // 🟡 AMARELO = Baixada mas NÃO lida
                colorClass = 'issue-baixada';
                titleText = `Edição #${numero}`;
                actionsHTML = `
                    <label class="checkbox-icon" title="Marcar como lida">
                        <input type="checkbox" onchange="toggleIssueRead(${issue.id}, this.checked)">
                        <span class="checkmark"></span>
                    </label>
                    <button class="btn-icon btn-delete" onclick="deleteIssue(${issue.id}, ${numero})" title="Deletar edição">
                        🗑️
                    </button>
                `;
            }
        } else {
            // 🔴 Edição NÃO existe no sistema = VERMELHO
            colorClass = 'issue-faltante';
            if (numero < edicaoMinimaLida) {
                titleText = `Edição #${numero} - Não baixada (anterior)`;
            } else {
                titleText = `Edição #${numero} - Não baixada`;
            }
            actionsHTML = `
                <button class="btn-icon btn-add-quick" onclick="adicionarEdicaoRapida(${numero})" title="Adicionar esta edição">
                    ➕
                </button>
            `;
        }
        
        issueCard.className = `issue-card ${colorClass}`;
        
        issueCard.innerHTML = `
            <div class="issue-number">#${numero}</div>
            <div class="issue-info">
                <div class="issue-title">${titleText}</div>
                ${issue && issue.date_read ? `<div class="issue-date">Lida em ${new Date(issue.date_read).toLocaleDateString('pt-BR')}</div>` : ''}
            </div>
            <div class="issue-actions">
                ${actionsHTML}
            </div>
        `;
        
        allIssueCards.push(issueCard);
    }
    
    allIssueCards.forEach(card => issuesList.appendChild(card));
}

// Função para adicionar edição rapidamente
async function adicionarEdicaoRapida(numero) {
    if (!currentSeriesId) return;
    
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues`, {
            method: 'POST',
            body: JSON.stringify({
                issue_number: numero,
                is_read: false,
            }),
        });
        
        console.log(`✅ Edição #${numero} adicionada!`);
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('Error adding issue:', error);
        alert('Erro ao adicionar edição: ' + error.message);
    }
}

async function sincronizarEdicoesAutomaticamente() {
    if (!currentSeriesId) return;
    
    const btnSync = event.target;
    btnSync.disabled = true;
    btnSync.innerHTML = '⏳ Sincronizando...';
    
    try {
        const series = await fetchAPI(`/series/${currentSeriesId}`);
        const existingIssues = await fetchAPI(`/series/${currentSeriesId}/issues`);
        
        const totalPublicado = series.total_issues;
        const existingNumbers = new Set(existingIssues.map(i => i.issue_number));
        
        console.log(`📊 Total publicado: ${totalPublicado}`);
        console.log(`📊 Edições existentes: ${existingNumbers.size}`);
        
        const missingIssues = [];
        for (let i = 1; i <= totalPublicado; i++) {
            if (!existingNumbers.has(i)) {
                missingIssues.push(i);
            }
        }
        
        if (missingIssues.length === 0) {
            alert('✅ Todas as edições já estão sincronizadas!');
            btnSync.disabled = false;
            btnSync.innerHTML = '🔄 Sincronizar Edições';
            return;
        }
        
        console.log(`🔄 Adicionando ${missingIssues.length} edições faltantes...`);
        
        let adicionadas = 0;
        for (const numero of missingIssues) {
            try {
                await fetchAPI(`/series/${currentSeriesId}/issues`, {
                    method: 'POST',
                    body: JSON.stringify({
                        issue_number: numero,
                        is_read: false
                    })
                });
                adicionadas++;
            } catch (error) {
                console.error(`❌ Erro ao adicionar edição #${numero}:`, error);
            }
        }
        
        console.log(`✅ ${adicionadas} edições adicionadas com sucesso!`);
        
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
        
        alert(`✅ Sincronização completa!\n${adicionadas} edições adicionadas.`);
        
    } catch (error) {
        console.error('Erro na sincronização:', error);
        alert('❌ Erro ao sincronizar edições: ' + error.message);
    } finally {
        btnSync.disabled = false;
        btnSync.innerHTML = '🔄 Sincronizar Edições';
    }
}

async function verificarSincronizacaoLendo() {
    if (!currentSeriesId) return;
    
    try {
        const [series, issues] = await Promise.all([
            fetchAPI(`/series/${currentSeriesId}`),
            fetchAPI(`/series/${currentSeriesId}/issues`)
        ]);
        
        const readIssuesReal = issues.filter(i => i.is_read).length;
        const readIssuesRegistrado = series.read_issues;
        
        console.log('🔍 Verificação:', {
            'Registrado no banco': readIssuesRegistrado,
            'Real (contando edições)': readIssuesReal,
            'Diferença': readIssuesReal - readIssuesRegistrado
        });
        
        if (readIssuesReal === readIssuesRegistrado) {
            alert(`✅ Tudo certo!\n\nEdições lidas registradas: ${readIssuesRegistrado}\nEdições realmente lidas: ${readIssuesReal}\n\nOs valores estão sincronizados!`);
        } else {
            const diferenca = readIssuesReal - readIssuesRegistrado;
            alert(`⚠️ Desincronizado!\n\nEdições lidas registradas: ${readIssuesRegistrado}\nEdições realmente lidas: ${readIssuesReal}\nDiferença: ${diferenca > 0 ? '+' : ''}${diferenca}`);
        }
        
    } catch (error) {
        console.error('Erro ao verificar:', error);
        alert('Erro ao verificar sincronização: ' + error.message);
    }
}

function goToHome() {
    currentSeriesId = null;
    document.getElementById('home-view').style.display = 'block';
    document.getElementById('detail-view').style.display = 'none';
    document.getElementById('stats-section').style.display = 'block';
    document.getElementById('filters-section').style.display = 'block';
    document.getElementById('btn-back').style.display = 'none';
    document.getElementById('header-actions').style.display = 'flex';
    loadSeries();
    loadStats();
}

// Toggle issue read status
async function toggleIssueRead(issueId, isRead) {
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues/${issueId}`, {
            method: 'PATCH',
            body: JSON.stringify({ is_read: isRead }),
        });
        
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('Error updating issue:', error);
        alert('Erro ao atualizar edição');
    }
}

// Delete issue
async function deleteIssue(issueId, issueNumber) {
    if (!confirm(`Tem certeza que deseja deletar a Edição #${issueNumber}?`)) {
        return;
    }
    
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues/${issueId}`, {
            method: 'DELETE',
        });
        
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('Error deleting issue:', error);
        alert('Erro ao deletar edição');
    }
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
        }
    } else {
        title.textContent = 'Nova HQ';
        document.getElementById('series-id').value = '';
    }
    
    modal.classList.add('active');
    console.log('✅ Modal aberto');
}

function closeModal() {
    console.log('🔒 Fechando modal...');
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
        console.error('Error saving series:', error);
        alert('Erro ao salvar HQ: ' + error.message);
    }
}

// Delete series
async function deleteSeries(seriesId) {
    if (!confirm('Tem certeza que deseja deletar esta HQ? Esta ação não pode ser desfeita.')) {
        return;
    }
    
    try {
        await fetchAPI(`/series/${seriesId}`, {
            method: 'DELETE',
        });
        
        goToHome();
        loadSeries();
        loadStats();
    } catch (error) {
        console.error('Error deleting series:', error);
        alert('Erro ao deletar HQ');
    }
}

// Issue Modal
function openAddIssueModal() {
    const modal = document.getElementById('issue-modal');
    const form = document.getElementById('issue-form');
    form.reset();
    modal.classList.add('active');
}

function closeIssueModal() {
    const modal = document.getElementById('issue-modal');
    modal.classList.remove('active');
}

async function submitIssueForm(e) {
    e.preventDefault();
    
    const data = {
        issue_number: parseInt(document.getElementById('issue_number').value),
        is_read: document.getElementById('is_read').checked,
    };
    
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
        
        const series = await fetchAPI(`/series/${currentSeriesId}`);
        if (data.issue_number > series.total_issues) {
            await fetchAPI(`/series/${currentSeriesId}`, {
                method: 'PUT',
                body: JSON.stringify({
                    ...series,
                    total_issues: data.issue_number
                }),
            });
        }
        
        closeIssueModal();
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('Error adding issue:', error);
        alert('Erro ao adicionar edição: ' + error.message);
    }
}
