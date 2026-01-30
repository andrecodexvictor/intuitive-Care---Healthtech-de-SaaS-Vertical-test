<script setup>
/**
 * EstatisticasDashboard.vue
 * 
 * Dashboard principal com:
 * - Cards de estatísticas (total, média, quantidade)
 * - Top 5 operadoras por despesa
 * - Gráfico de distribuição por UF
 */
import { ref, onMounted, computed } from 'vue'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js'
import { Doughnut, Bar } from 'vue-chartjs'
import { estatisticasService } from '../services/api'

// Registrar componentes do Chart.js
ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement)

// Estado reativo
const loading = ref(true)
const error = ref(null)
const stats = ref(null)
const distribuicaoUF = ref([])

// Opções do gráfico de donut
const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right',
      labels: {
        padding: 15,
        usePointStyle: true,
      },
    },
  },
}

// Opções do gráfico de barras
const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false,
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        callback: (value) => formatCurrency(value, true),
      },
    },
  },
}

// Dados do gráfico de UF
const ufChartData = computed(() => {
  const top10 = distribuicaoUF.value.slice(0, 10)
  return {
    labels: top10.map(item => item.uf),
    datasets: [
      {
        label: 'Total por UF',
        data: top10.map(item => item.total),
        backgroundColor: [
          '#1a365d', '#2c5282', '#0d9488', '#14b8a6', '#0f766e',
          '#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#d946ef',
        ],
        borderRadius: 6,
      },
    ],
  }
})

// Dados do gráfico de top operadoras
const topOperadorasChartData = computed(() => {
  if (!stats.value?.top_5_operadoras) return null
  
  const operadoras = stats.value.top_5_operadoras
  return {
    labels: operadoras.map(o => truncateText(o.razao_social, 25)),
    datasets: [
      {
        data: operadoras.map(o => o.total),
        backgroundColor: [
          '#1a365d', '#0d9488', '#3b82f6', '#8b5cf6', '#f59e0b',
        ],
        borderWidth: 2,
        borderColor: '#ffffff',
      },
    ],
  }
})

// Formatar moeda
function formatCurrency(value, compact = false) {
  if (compact && value >= 1e9) {
    return `R$ ${(value / 1e9).toFixed(1)}B`
  }
  if (compact && value >= 1e6) {
    return `R$ ${(value / 1e6).toFixed(1)}M`
  }
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

// Formatar número
function formatNumber(value) {
  return new Intl.NumberFormat('pt-BR').format(value)
}

// Truncar texto
function truncateText(text, maxLength) {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

// Buscar dados
async function fetchData() {
  loading.value = true
  error.value = null
  
  try {
    const [statsData, ufData] = await Promise.all([
      estatisticasService.getGerais(),
      estatisticasService.getDistribuicaoUF(),
    ])
    
    stats.value = statsData
    distribuicaoUF.value = ufData
  } catch (err) {
    error.value = 'Não foi possível carregar os dados. Verifique se a API está rodando.'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="dashboard">
    <!-- Loading State -->
    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="card error-card">
      <p class="text-error">{{ error }}</p>
      <button class="btn btn-primary mt-4" @click="fetchData">
        Tentar novamente
      </button>
    </div>
    
    <!-- Dashboard Content -->
    <template v-else-if="stats">
      <!-- Stats Cards -->
      <div class="grid grid-cols-3 mb-6">
        <div class="stat-card">
          <div class="stat-value">{{ formatCurrency(stats.total_despesas, true) }}</div>
          <div class="stat-label">Total de Despesas</div>
        </div>
        
        <div class="stat-card accent">
          <div class="stat-value">{{ formatCurrency(stats.media_despesas, true) }}</div>
          <div class="stat-label">Média por Registro</div>
        </div>
        
        <div class="stat-card dark">
          <div class="stat-value">{{ formatNumber(stats.quantidade_registros) }}</div>
          <div class="stat-label">Registros Processados</div>
        </div>
      </div>
      
      <!-- Charts Row -->
      <div class="grid grid-cols-2">
        <!-- Top 5 Operadoras -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">🏆 Top 5 Operadoras por Despesa</h3>
          </div>
          
          <div v-if="topOperadorasChartData" class="chart-container">
            <Doughnut :data="topOperadorasChartData" :options="doughnutOptions" />
          </div>
          
          <ul class="top-list">
            <li v-for="(op, index) in stats.top_5_operadoras" :key="index" class="top-item">
              <span class="top-rank">{{ index + 1 }}º</span>
              <span class="top-name">{{ truncateText(op.razao_social, 40) }}</span>
              <span class="top-value">{{ formatCurrency(op.total, true) }}</span>
            </li>
          </ul>
        </div>
        
        <!-- Distribuição por UF -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">📊 Distribuição por UF (Top 10)</h3>
          </div>
          
          <div v-if="distribuicaoUF.length" class="chart-container chart-bar">
            <Bar :data="ufChartData" :options="barOptions" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.dashboard {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.stat-card.accent {
  background: linear-gradient(135deg, var(--color-accent) 0%, var(--color-accent-dark) 100%);
}

.stat-card.dark {
  background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
}

.chart-container {
  height: 200px;
  margin-bottom: var(--space-4);
}

.chart-bar {
  height: 280px;
}

.top-list {
  list-style: none;
  margin-top: var(--space-4);
}

.top-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border);
}

.top-item:last-child {
  border-bottom: none;
}

.top-rank {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-elevated);
  border-radius: var(--radius-full);
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-primary);
}

.top-name {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--color-text);
}

.top-value {
  font-weight: 600;
  color: var(--color-accent);
}

.error-card {
  text-align: center;
  padding: var(--space-12);
}
</style>
