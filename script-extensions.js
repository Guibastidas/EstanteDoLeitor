// Funções adicionais para tipos de série e exportação

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

// Adicionar ao script principal - sobrescrever createSeriesCard
const originalCreateSeriesCard = window.createSeriesCard;

window.createSeriesCard = function(series) {
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
};

// Sobrescrever submitSeriesForm para incluir series_type
const originalSubmitSeriesForm = window.submitSeriesForm;

window.submitSeriesForm = async function(event) {
    event.preventDefault();
    
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
        
        if (currentSeriesId && seriesId === currentSeriesId.toString()) {
            loadSeriesDetail(currentSeriesId);
        } else {
            loadSeries();
        }
        loadStats();
    } catch (error) {
        console.error('Error submitting form:', error);
    }
};

// Sobrescrever editSeriesById para incluir series_type
const originalEditSeriesById = window.editSeriesById;

window.editSeriesById = async function(seriesId) {
    try {
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
    }
};

// Atualizar loadSeriesDetail para mostrar o tipo
const originalLoadSeriesDetail = window.loadSeriesDetail;

window.loadSeriesDetail = async function(seriesId) {
    try {
        const series = await fetchAPI(`/series/${seriesId}`);
        const issues = await fetchAPI(`/series/${seriesId}/issues`);
        
        // Título
        document.getElementById('detail-title').textContent = series.title;
        
        // Badge de tipo
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
    }
};

console.log('✓ Extensões de tipo de série carregadas!');
