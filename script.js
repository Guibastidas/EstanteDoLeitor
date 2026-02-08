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
    
    // ✅ CORREÇÃO 1: ORDENAR ALFABETICAMENTE
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
    
    // ✅ CORREÇÃO 2: Event listeners corretos para os botões
    // Adicionar event listener para o card (abrir detalhes)
    card.addEventListener('click', (e) => {
        // Só abre detalhes se não clicou em um botão
        if (!e.target.closest('.btn-icon-small')) {
            showSeriesDetail(series.id);
        }
    });
    
    // Adicionar event listeners para os botões
    const btnEdit = card.querySelector('.btn-edit');
    const btnDelete = card.querySelector('.btn-delete');
    
    if (btnEdit) {
        btnEdit.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('✏️ Botão editar clicado - ID:', series.id);
            editSeries(series.id);
        });
    }
    
    if (btnDelete) {
        btnDelete.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('🗑️ Botão excluir clicado - ID:', series.id);
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
        
        // Carregar dados da série
        const series = await fetchAPI(`/series/${seriesId}`);
        currentSeries = series;
        console.log('📊 Dados da série:', series);
        
        // Atualizar informações da série
        document.getElementById('detail-title').textContent = series.title;
        
        // Author e Publisher
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
        console.log('📚 Carregando edições...');
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
    
    // Ordenar por número da edição
    issues.sort((a, b) => a.issue_number - b.issue_number);
    
    issues.forEach(issue => {
        const issueCard = createIssueCard(issue);
        issuesList.appendChild(issueCard);
    });
}

function createIssueCard(issue) {
    const card = document.createElement('div');
    card.className = `issue-card ${issue.is_read ? 'read' : 'unread'}`;
    
    card.innerHTML = `
        <div class="issue-number">#${issue.issue_number}</div>
        <div class="issue-info">
            ${issue.title ? `<div class="issue-title">${issue.title}</div>` : ''}
            <div class="issue-status">
                ${issue.is_downloaded ? '<span class="badge badge-downloaded">📥 Baixada</span>' : ''}
                ${issue.is_read ? '<span class="badge badge-read">✅ Lida</span>' : ''}
            </div>
        </div>
        <div class="issue-actions">
            <label class="checkbox-label" title="${issue.is_read ? 'Marcar como não lida' : 'Marcar como lida'}">
                <input type="checkbox" ${issue.is_read ? 'checked' : ''} 
                       onchange="toggleIssueRead(${issue.id}, this.checked)">
                <span>${issue.is_read ? '✓' : ''}</span>
            </label>
            <button class="btn-icon-mini btn-delete-issue" 
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
    
    // Update active tab
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

// ==================== FUNÇÕES DE SINCRONIZAÇÃO ====================

// ✅ NOVA FUNÇÃO: Recalcular edições baseado nos valores da planilha
async function recalcularEdicoes() {
    if (!currentSeriesId || !currentSeries) {
        alert('Erro: Série não identificada');
        return;
    }
    
    const confirmacao = confirm(
        `⚠️ ATENÇÃO: Esta ação vai RECRIAR todas as edições baseado nos valores da planilha!\n\n` +
        `Série: ${currentSeries.title}\n` +
        `Lendo (planilha): ${currentSeries.read_issues}\n` +
        `Baixadas (planilha): ${currentSeries.downloaded_issues}\n` +
        `Total (planilha): ${currentSeries.total_issues}\n\n` +
        `Isso vai:\n` +
        `• Deletar TODAS as edições cadastradas\n` +
        `• Criar novas edições de 1 até ${currentSeries.total_issues}\n` +
        `• Marcar ${currentSeries.read_issues} edições como lidas\n\n` +
        `Deseja continuar?`
    );
    
    if (!confirmacao) return;
    
    try {
        console.log('🔄 Recalculando edições baseado na planilha...');
        
        // 1. Buscar e deletar todas as edições existentes
        const issuesExistentes = await fetchAPI(`/series/${currentSeriesId}/issues`);
        console.log(`📝 ${issuesExistentes.length} edições existentes serão deletadas`);
        
        for (const issue of issuesExistentes) {
            await fetchAPI(`/series/${currentSeriesId}/issues/${issue.id}`, {
                method: 'DELETE'
            });
        }
        
        console.log('✅ Edições antigas deletadas');
        
        // 2. Criar novas edições de 1 até total_issues
        const total = currentSeries.total_issues;
        const lidas = currentSeries.read_issues;
        
        console.log(`📝 Criando ${total} edições (${lidas} marcadas como lidas)...`);
        
        for (let i = 1; i <= total; i++) {
            const isLida = i <= lidas;
            
            await fetchAPI(`/series/${currentSeriesId}/issues`, {
                method: 'POST',
                body: JSON.stringify({
                    issue_number: i,
                    is_read: isLida
                })
            });
        }
        
        console.log('✅ Edições recriadas com sucesso!');
        
        // 3. Recarregar a página de detalhes
        alert(`✅ Edições recalculadas com sucesso!\n\n${total} edições criadas (${lidas} marcadas como lidas)`);
        
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
        
    } catch (error) {
        console.error('❌ Erro ao recalcular edições:', error);
        alert('Erro ao recalcular edições: ' + error.message);
    }
}

// Sincronizar edições automaticamente (mantém a função existente)
async function sincronizarEdicoesAutomaticamente() {
    if (!currentSeriesId || !currentSeries) {
        alert('Erro: Série não identificada');
        return;
    }
    
    const confirmacao = confirm(
        `🔄 Sincronizar Edições\n\n` +
        `Isso vai criar automaticamente ${currentSeries.total_issues} edições para a série "${currentSeries.title}".\n\n` +
        `• Edições 1 a ${currentSeries.read_issues}: Marcadas como LIDAS\n` +
        `• Edições ${currentSeries.read_issues + 1} a ${currentSeries.total_issues}: Não lidas\n\n` +
        `Deseja continuar?`
    );
    
    if (!confirmacao) return;
    
    try {
        console.log('🔄 Sincronizando edições...');
        
        // Deletar edições existentes primeiro
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
        
        console.log('✅ Edições sincronizadas!');
        alert(`✅ Edições sincronizadas com sucesso!\n\n${currentSeries.total_issues} edições criadas`);
        
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
        
    } catch (error) {
        console.error('❌ Erro ao sincronizar:', error);
        alert('Erro ao sincronizar edições: ' + error.message);
    }
}

// Verificar sincronização do contador "Lendo"
async function verificarSincronizacaoLendo() {
    if (!currentSeriesId) {
        alert('Erro: Série não identificada');
        return;
    }
    
    try {
        const issues = await fetchAPI(`/series/${currentSeriesId}/issues`);
        const lidas = issues.filter(i => i.is_read).length;
        const valorMostrado = currentSeries.read_issues;
        
        if (lidas === valorMostrado) {
            alert(`✅ Contador "Lendo" está correto!\n\nEdições lidas: ${lidas}\nValor mostrado: ${valorMostrado}`);
        } else {
            const confirmacao = confirm(
                `⚠️ Dessincronização detectada!\n\n` +
                `Edições marcadas como lidas: ${lidas}\n` +
                `Valor mostrado no contador: ${valorMostrado}\n\n` +
                `Deseja recalcular as edições para corrigir?`
            );
            
            if (confirmacao) {
                await recalcularEdicoes();
            }
        }
    } catch (error) {
        console.error('❌ Erro ao verificar:', error);
        alert('Erro ao verificar sincronização');
    }
}

// ==================== NOVA EDIÇÃO PUBLICADA ====================

// ✅ CORRIGIDO: Aumentar total_issues (não criar edição)
async function aumentarTotalIssues() {
    if (!currentSeriesId || !currentSeries) {
        alert('Erro: Série não identificada');
        return;
    }
    
    const novoTotal = currentSeries.total_issues + 1;
    
    const confirmacao = confirm(
        `📚 Aumentar Total de Edições Publicadas\n\n` +
        `Série: ${currentSeries.title}\n` +
        `Total atual: ${currentSeries.total_issues}\n` +
        `Novo total: ${novoTotal}\n\n` +
        `Isso significa que mais uma edição foi PUBLICADA pela editora.\n` +
        `(A edição ainda não estará baixada ou lida)\n\n` +
        `Confirmar?`
    );
    
    if (!confirmacao) return;
    
    try {
        console.log('📚 Aumentando total_issues...');
        
        // Atualizar a série
        await fetchAPI(`/series/${currentSeriesId}`, {
            method: 'PUT',
            body: JSON.stringify({
                ...currentSeries,
                total_issues: novoTotal
            })
        });
        
        console.log('✅ Total de edições atualizado!');
        
        // Recarregar
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
        
    } catch (error) {
        console.error('❌ Erro ao aumentar total:', error);
        alert('Erro ao aumentar total de edições: ' + error.message);
    }
}

// Toggle issue read status
async function toggleIssueRead(issueId, isRead) {
    try {
        console.log(`🔄 Alterando status da edição ${issueId} para ${isRead ? 'LIDA' : 'NÃO LIDA'}`);
        
        await fetchAPI(`/series/${currentSeriesId}/issues/${issueId}`, {
            method: 'PATCH',
            body: JSON.stringify({ is_read: isRead })
        });
        
        console.log('✅ Status alterado com sucesso');
        
        loadSeriesDetail(currentSeriesId);
        loadStats();
        loadSeries();
    } catch (error) {
        console.error('❌ Error toggling issue read status:', error);
        
        // Reverter checkbox se der erro
        const checkbox = event.target;
        if (checkbox) {
            checkbox.checked = !isRead;
        }
        
        alert('⚠️ Erro ao atualizar status da edição.\n\nPossíveis causas:\n• A edição não existe no banco de dados\n• Problema de conexão com o servidor\n\nTente recarregar a página ou sincronizar as edições novamente.');
    }
}

// Delete issue
async function deleteIssue(issueId, issueNumber) {
    if (!confirm(`Tem certeza que deseja deletar a edição #${issueNumber}?`)) {
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
            console.log('✅ Dados preenchidos no modal:', series);
        } else {
            console.error('❌ Série não encontrada em allSeries:', seriesId);
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

// Edit series (função necessária para o botão de editar)
function editSeries(seriesId) {
    console.log('✏️ Editando série:', seriesId);
    openModal(seriesId);
}

// Delete series
async function deleteSeries(seriesId, seriesTitle = 'esta HQ') {
    if (!confirm(`Tem certeza que deseja deletar "${seriesTitle}"? Esta ação não pode ser desfeita.`)) {
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

// ✅ CORRIGIDO: Modal para adicionar edição baixada
// Issue Modal
function openAddIssueModal() {
    console.log('🔵 openAddIssueModal chamada!');
    console.log('🔵 currentSeriesId:', currentSeriesId);
    
    if (!currentSeriesId) {
        console.error('❌ currentSeriesId está null!');
        alert('Erro: Série não identificada. Tente recarregar a página.');
        return;
    }
    
    const modal = document.getElementById('issue-modal');
    const form = document.getElementById('issue-form');
    
    if (!modal) {
        console.error('❌ Modal não encontrado!');
        alert('Erro: Modal não encontrado no HTML.');
        return;
    }
    
    if (!form) {
        console.error('❌ Form não encontrado!');
        alert('Erro: Formulário não encontrado no HTML.');
        return;
    }
    
    form.reset();
    
    // Sugerir próximo número de edição
    const series = currentSeries;
    if (series && series.downloaded_issues > 0) {
        const nextIssue = series.downloaded_issues + 1;
        document.getElementById('issue_number').value = nextIssue;
        console.log(`📝 Sugerindo próxima edição: #${nextIssue}`);
    }
    
    modal.classList.add('active');
    console.log('✅ Modal de edição aberto');
}

function closeIssueModal() {
    const modal = document.getElementById('issue-modal');
    modal.classList.remove('active');
}

async function submitIssueForm(e) {
    e.preventDefault();
    
    console.log('📝 Submetendo formulário de edição...');
    console.log('📝 currentSeriesId:', currentSeriesId);
    
    if (!currentSeriesId) {
        alert('Erro: Série não identificada');
        return;
    }
    
    const issueNumber = parseInt(document.getElementById('issue_number').value);
    const isRead = document.getElementById('is_read').checked;
    
    console.log('📝 Dados:', { issueNumber, isRead });
    
    try {
        await fetchAPI(`/series/${currentSeriesId}/issues`, {
            method: 'POST',
            body: JSON.stringify({
                issue_number: issueNumber,
                is_read: isRead
            })
        });
        
        console.log('✅ Edição adicionada com sucesso!');
        
        closeIssueModal();
        await loadSeriesDetail(currentSeriesId);
        await loadStats();
        await loadSeries();
        
    } catch (error) {
        console.error('❌ Error adding issue:', error);
        alert('Erro ao adicionar edição: ' + error.message);
    }
}
