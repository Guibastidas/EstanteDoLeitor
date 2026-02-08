// API Configuration
const API_URL = window.location.origin;

// State
let currentFilter = 'all';
let currentSeriesId = null;
let allSeries = [];
let searchTimeout = null;
let currentSeries = null;

// Pilha de ações para desfazer
let undoStack = [];

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
    
    // Switch views
    document.getElementById('home-view').style.display = 'none';
    document.getElementById('stats-section').style.display = 'none';
    document.getElementById('filters-section').style.display = 'none';
    document.getElementById('detail-view').style.display = 'block';
    document.getElementById('btn-back').style.display = 'inline-flex';
    
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
    
    if (!issues || issues.length === 0) {
        issuesList.innerHTML = '';
        emptyIssues.style.display = 'flex';
        return;
    }
    
    emptyIssues.style.display = 'none';
    issuesList.innerHTML = '';
    
    issues.sort((a, b) => a.issue_number - b.issue_number);
    
    issues.forEach(issue => {
        const issueCard = createIssueCard(issue);
        issuesList.appendChild(issueCard);
    });
}

function createIssueCard(issue) {
    const card = document.createElement('div');
    
    // 🎨 SISTEMA DE CORES:
    // 🟢 VERDE (issue-lida) = Edição lida
    // 🟡 AMARELO (issue-baixada) = Edição baixada mas não lida
    // 🔴 VERMELHO (issue-faltante) = Edição não baixada
    
    let colorClass = 'issue-faltante'; // Padrão: vermelho (não baixada)
    
    if (issue.is_read) {
        colorClass = 'issue-lida'; // Verde: lida
    } else if (issue.is_downloaded) {
        colorClass = 'issue-baixada'; // Amarelo: baixada mas não lida
    }
    
    card.className = `issue-card ${colorClass}`;
    
    card.innerHTML = `
        <div class="issue-info">
            <div class="issue-number">#${issue.issue_number}</div>
            ${issue.title ? `<div class="issue-title">${issue.title}</div>` : ''}
            <div class="issue-status">
                ${issue.is_downloaded ? '<span class="badge badge-downloaded">📥 Baixada</span>' : '<span class="badge badge-missing">❌ Falta baixar</span>'}
                ${issue.is_read ? '<span class="badge badge-read">✅ Lida</span>' : ''}
            </div>
        </div>
        <div class="issue-actions">
            <label class="checkbox-label" title="${issue.is_read ? 'Marcar como não lida' : 'Marcar como lida'}">
                <input type="checkbox" ${issue.is_read ? 'checked' : ''} 
                       onchange="toggleIssueRead(${issue.id}, this.checked)">
                <span></span>
            </label>
            <button class="btn-delete-issue" 
                    onclick="deleteIssue(${issue.id}, ${issue.issue_number})"
                    title="Deletar edição">
                🗑️
            </button>
        </div>
    `;
    
    return card;
}

function goToHome() {
    console.log('🏠 Voltando para home...');
    
    document.getElementById('detail-view').style.display = 'none';
    document.getElementById('home-view').style.display = 'block';
    document.getElementById('stats-section').style.display = 'block';
    document.getElementById('filters-section').style.display = 'block';
    document.getElementById('btn-back').style.display = 'none';
    
    currentSeriesId = null;
    currentSeries = null;
    
    loadSeries();
    loadStats();
}

// Filter series
function filterSeries(filter) {
    currentFilter = filter;
    
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');
    
    displaySeries();
}

// Search
function handleSearch() {
    const query = document.getElementById('search-input').value;
    const clearBtn = document.getElementById('search-clear');
    
    clearBtn.style.display = query ? 'block' : 'none';
    
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        loadSeries(query);
    }, 300);
}

function clearSearch() {
    document.getElementById('search-input').value = '';
    document.getElementById('search-clear').style.display = 'none';
    loadSeries();
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
            console.log('✅ Dados preenchidos');
        } else {
            console.error('❌ Série não encontrada:', seriesId);
        }
    } else {
        title.textContent = 'Nova HQ';
        document.getElementById('series-id').value = '';
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
