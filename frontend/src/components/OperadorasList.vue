<script setup>
/**
 * OperadorasList.vue
 * Lista de operadoras com busca e paginação
 */
import { ref, onMounted, computed } from 'vue'
import { operadorasService } from '../services/api'

const loading = ref(true)
const error = ref(null)
const operadoras = ref([])
const total = ref(0)
const page = ref(1)
const limit = ref(20)
const searchQuery = ref('')
let searchTimeout = null

const totalPages = computed(() => Math.ceil(total.value / limit.value))
const canPrev = computed(() => page.value > 1)
const canNext = computed(() => page.value < totalPages.value)

function formatCnpj(cnpj) {
  if (!cnpj || cnpj.length !== 14) return cnpj
  return `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.${cnpj.slice(5, 8)}/${cnpj.slice(8, 12)}-${cnpj.slice(12)}`
}

async function fetchOperadoras() {
  loading.value = true
  error.value = null
  try {
    const data = await operadorasService.list({
      page: page.value,
      limit: limit.value,
      razaoSocial: searchQuery.value,
    })
    operadoras.value = data.data
    total.value = data.total
  } catch (err) {
    error.value = 'Erro ao carregar operadoras. Verifique se a API está rodando.'
  } finally {
    loading.value = false
  }
}

function onSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    page.value = 1
    fetchOperadoras()
  }, 400)
}

function prevPage() { if (canPrev.value) { page.value--; fetchOperadoras() } }
function nextPage() { if (canNext.value) { page.value++; fetchOperadoras() } }
function clearSearch() { searchQuery.value = ''; page.value = 1; fetchOperadoras() }

onMounted(fetchOperadoras)
</script>

<template>
  <div class="operadoras">
    <div class="page-header">
      <h2>🏢 Operadoras de Saúde</h2>
      <p class="text-muted">Lista de operadoras registradas na ANS</p>
    </div>
    
    <div class="search-bar card">
      <div class="search-input-wrapper">
        <span class="search-icon">🔍</span>
        <input v-model="searchQuery" type="text" class="input search-input" placeholder="Buscar por razão social..." @input="onSearch" />
        <button v-if="searchQuery" class="clear-btn" @click="clearSearch">✕</button>
      </div>
      <div class="search-meta">
        <span v-if="!loading">{{ total }} operadora(s)</span>
      </div>
    </div>
    
    <div v-if="loading" class="loading"><div class="spinner"></div></div>
    
    <div v-else-if="error" class="card error-card">
      <p class="text-error">{{ error }}</p>
      <button class="btn btn-primary mt-4" @click="fetchOperadoras">Tentar novamente</button>
    </div>
    
    <div v-else class="card">
      <div class="table-container">
        <table class="table">
          <thead>
            <tr>
              <th>CNPJ</th>
              <th>Razão Social</th>
              <th>Registro ANS</th>
              <th>Modalidade</th>
              <th>UF</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="op in operadoras" :key="op.cnpj">
              <td class="cnpj-cell">{{ formatCnpj(op.cnpj) }}</td>
              <td class="razao-cell">{{ op.razao_social }}</td>
              <td>{{ op.registro_ans || '—' }}</td>
              <td>{{ op.modalidade || '—' }}</td>
              <td><span v-if="op.uf" class="uf-badge">{{ op.uf }}</span><span v-else>—</span></td>
            </tr>
            <tr v-if="operadoras.length === 0">
              <td colspan="5" class="text-center text-muted">Nenhuma operadora encontrada</td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div v-if="totalPages > 1" class="pagination">
        <button class="pagination-btn" :disabled="!canPrev" @click="prevPage">← Anterior</button>
        <span class="pagination-info">Página {{ page }} de {{ totalPages }}</span>
        <button class="pagination-btn" :disabled="!canNext" @click="nextPage">Próxima →</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header { margin-bottom: var(--space-6); }
.page-header h2 { margin-bottom: var(--space-1); }
.search-bar { display: flex; justify-content: space-between; align-items: center; gap: var(--space-4); margin-bottom: var(--space-6); padding: var(--space-4); }
.search-input-wrapper { position: relative; flex: 1; max-width: 500px; }
.search-icon { position: absolute; left: 16px; top: 50%; transform: translateY(-50%); opacity: 0.5; }
.search-input { padding-left: 48px; padding-right: 40px; }
.clear-btn { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); background: none; border: none; cursor: pointer; opacity: 0.5; }
.clear-btn:hover { opacity: 1; }
.search-meta { color: var(--color-text-muted); font-size: var(--font-size-sm); }
.cnpj-cell { font-family: 'Consolas', monospace; font-size: var(--font-size-sm); color: var(--color-text-muted); }
.razao-cell { font-weight: 500; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.uf-badge { display: inline-block; padding: 2px 8px; background: var(--color-accent); color: white; border-radius: 4px; font-size: 12px; font-weight: 600; }
.error-card { text-align: center; padding: var(--space-12); }
</style>
