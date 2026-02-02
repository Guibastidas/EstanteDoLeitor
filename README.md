# HQ Manager - Gerenciador de Quadrinhos v2.0

Sistema completo para gerenciar sua coleção de HQs com interface moderna, busca e visualização por edições.

## 🎨 Novidades da Versão 2.0

### ✨ Principais Mudanças

1. **Visualização por Série**: Agora cada título aparece apenas uma vez na página inicial
2. **Página de Detalhes**: Clique em qualquer HQ para ver todas as edições
3. **Busca em Tempo Real**: Campo de busca integrado no header
4. **Status Automático**: O status é calculado automaticamente baseado nas edições lidas
5. **Gestão de Edições**: Adicione, marque como lida ou delete edições individualmente
6. **Três Contadores**: 
   - **Lendo**: Quantas edições você já leu
   - **Baixadas**: Quantas edições você tem baixadas
   - **Total**: Total de edições da série

### 📊 Como o Status Funciona

O sistema calcula automaticamente o status baseado nas edições:

- **Para Ler**: 0 edições lidas
- **Lendo**: Leu algumas edições, mas não todas
- **Concluída**: Leu todas as edições do total

## 🚀 Como Usar

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Iniciar o Backend

```bash
python main.py
```

O servidor estará rodando em `http://localhost:8000`

### 3. Abrir o Frontend

Em outro terminal:

```bash
python -m http.server 8080
```

Acesse: `http://localhost:8080`

## 📖 Guia de Uso

### Página Inicial

- **Ver todas as séries**: Cada série aparece uma vez com progresso de leitura
- **Buscar**: Use o campo de busca para encontrar HQs por título, autor ou editora
- **Filtrar**: Use as abas para filtrar por status (Para Ler, Lendo, Concluídas)
- **Adicionar Nova**: Clique em "+ Nova HQ" para adicionar uma série

### Página de Detalhes

Clique em qualquer série para:

- **Ver todas as edições** listadas com números
- **Marcar edições como lidas** com checkbox
- **Adicionar novas edições** individualmente
- **Editar a série** (título, autor, editora, etc)
- **Acompanhar progresso** visual com barra de progresso

### Adicionar Nova HQ

No formulário você informa:

- **Título** (obrigatório)
- **Autor** e **Editora** (opcional)
- **Edições Lendo**: Quantas você já leu (ex: 5)
- **Edições Baixadas**: Quantas você tem (ex: 10)
- **Total de Edições**: Total da série (ex: 50)
- **URL da Capa**: Link para imagem da capa
- **Notas**: Observações pessoais

> O status será calculado automaticamente!

### Gerenciar Edições

Na página de detalhes:

1. Clique em **"+ Adicionar Edição"**
2. Informe o **número da edição** (ex: #1, #2, #3...)
3. Opcionalmente adicione um **título** (ex: "A Origem")
4. Marque se já leu essa edição
5. Clique em **Adicionar**

Para marcar como lida/não lida, use o checkbox ao lado de cada edição.

## 🔍 Funcionalidades

- ✅ Busca em tempo real
- ✅ Filtros por status
- ✅ Visualização agrupada por série
- ✅ Página de detalhes com todas as edições
- ✅ Status automático baseado no progresso
- ✅ Adicionar/editar/deletar séries
- ✅ Adicionar/marcar/deletar edições
- ✅ Barra de progresso visual
- ✅ Estatísticas em tempo real
- ✅ Interface responsiva
- ✅ Suporte para capas de HQs

## 📁 Estrutura de Arquivos

```
hq-manager-v2/
├── main.py              # Backend FastAPI com nova estrutura
├── index.html           # Frontend com duas views (lista + detalhes)
├── styles.css           # Estilos atualizados
├── script.js            # Lógica de navegação e gerenciamento
├── requirements.txt     # Dependências Python
├── README.md           # Este arquivo
└── hq_manager.db       # Banco de dados (criado automaticamente)
```

## 🗄️ Estrutura do Banco de Dados

### Tabela: `series`

Armazena informações das séries:

- `id`: ID único
- `title`: Título da série
- `author`: Autor
- `publisher`: Editora
- `total_issues`: Total de edições da série
- `downloaded_issues`: Edições que você tem
- `read_issues`: Edições que você leu
- `cover_url`: URL da capa
- `notes`: Notas pessoais
- `date_added`: Data de adição
- `date_updated`: Última atualização

### Tabela: `issues`

Armazena as edições individuais:

- `id`: ID único
- `series_id`: ID da série (FK)
- `issue_number`: Número da edição (#1, #2, etc)
- `title`: Título da edição (opcional)
- `is_read`: Se foi lida (true/false)
- `is_downloaded`: Se foi baixada (true/false)
- `date_added`: Data de adição
- `date_read`: Data de leitura

## 🎯 Dicas de Uso

1. **Organize por séries**: Mesmo que você tenha várias edições soltas, cadastre-as como parte de uma série
2. **Use a busca**: Digite qualquer parte do título, autor ou editora
3. **Acompanhe progresso**: A barra de progresso mostra visualmente quanto falta ler
4. **Marque conforme lê**: Use os checkboxes para marcar edições como lidas
5. **Adicione capas**: URLs de capas melhoram a visualização

## 🆕 Migração de Dados Antigos

Se você tem dados na versão antiga, eles precisarão ser migrados para a nova estrutura. A nova versão usa um modelo diferente que separa séries de edições individuais.

## 🐛 Solução de Problemas

### Erro de CORS

Certifique-se de:
1. O backend está rodando (`python main.py`)
2. Está acessando via servidor HTTP (`python -m http.server 8080`)
3. Não está abrindo o HTML diretamente (file://)

### Banco de dados vazio

O banco é criado automaticamente na primeira execução. Se precisar recomeçar, delete o arquivo `hq_manager.db`.

### Frontend não conecta

Verifique se a URL da API em `script.js` está correta:
```javascript
const API_URL = 'http://localhost:8000';
```

## 📝 API Endpoints

### Séries

- `GET /series` - Listar todas as séries (use `?search=` para buscar)
- `GET /series/{id}` - Obter uma série específica
- `POST /series` - Criar nova série
- `PUT /series/{id}` - Atualizar série
- `DELETE /series/{id}` - Deletar série

### Edições

- `GET /series/{id}/issues` - Listar edições de uma série
- `POST /series/{id}/issues` - Adicionar edição
- `PUT /issues/{id}` - Marcar edição como lida/não lida
- `DELETE /issues/{id}` - Deletar edição

### Estatísticas

- `GET /stats` - Obter estatísticas gerais

## 🎨 Personalização

### Cores

Edite em `styles.css`:

```css
:root {
    --color-primary: #0d6efd;    /* Cor principal */
    --color-success: #198754;    /* Cor de sucesso */
    /* ... */
}
```

### URL da API

Edite em `script.js`:

```javascript
const API_URL = 'http://localhost:8000';
```

## 📄 Licença

Projeto de código aberto. Use livremente!

---

**Versão 2.0** - Atualizado com navegação por séries e edições individuais
