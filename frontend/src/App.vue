<script setup>
/**
 * App.vue - Componente Raiz da Aplicação
 * 
 * Layout principal com header, navegação e área de conteúdo.
 * Usa Composition API do Vue 3.
 */
import { ref } from 'vue'
import OperadorasList from './components/OperadorasList.vue'
import EstatisticasDashboard from './components/EstatisticasDashboard.vue'

// Tab ativa (operadoras ou estatísticas)
const activeTab = ref('estatisticas')
</script>

<template>
  <div class="app">
    <!-- Header -->
    <header class="header">
      <div class="container">
        <div class="header-content">
          <div class="logo">
            <span class="logo-icon">🏥</span>
            <div class="logo-text">
              <h1>Intuitive Care</h1>
              <span class="logo-subtitle">Análise de Despesas</span>
            </div>
          </div>
          
          <!-- Navigation Tabs -->
          <nav class="nav-tabs">
            <button 
              :class="['nav-tab', { active: activeTab === 'estatisticas' }]"
              @click="activeTab = 'estatisticas'"
            >
              📊 Dashboard
            </button>
            <button 
              :class="['nav-tab', { active: activeTab === 'operadoras' }]"
              @click="activeTab = 'operadoras'"
            >
              🏢 Operadoras
            </button>
          </nav>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="main">
      <div class="container">
        <!-- Dashboard Tab -->
        <EstatisticasDashboard v-if="activeTab === 'estatisticas'" />
        
        <!-- Operadoras Tab -->
        <OperadorasList v-else-if="activeTab === 'operadoras'" />
      </div>
    </main>

    <!-- Footer -->
    <footer class="footer">
      <div class="container">
        <p>Desenvolvido para o Teste de Estágio • Intuitive Care</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* Header */
.header {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: var(--color-text-inverse);
  padding: var(--space-4) 0;
  box-shadow: var(--shadow-lg);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-4);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.logo-icon {
  font-size: 2rem;
}

.logo-text h1 {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-inverse);
  margin: 0;
}

.logo-subtitle {
  font-size: var(--font-size-xs);
  opacity: 0.8;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* Navigation Tabs */
.nav-tabs {
  display: flex;
  gap: var(--space-2);
}

.nav-tab {
  padding: var(--space-2) var(--space-4);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-full);
  color: var(--color-text-inverse);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.nav-tab:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
}

.nav-tab.active {
  background: var(--color-accent);
  border-color: var(--color-accent);
}

/* Main */
.main {
  flex: 1;
  padding: var(--space-8) 0;
}

/* Footer */
.footer {
  background: var(--color-bg-elevated);
  padding: var(--space-4) 0;
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  border-top: 1px solid var(--color-border);
}

/* Responsive */
@media (max-width: 640px) {
  .header-content {
    flex-direction: column;
    text-align: center;
  }
  
  .nav-tabs {
    width: 100%;
    justify-content: center;
  }
}
</style>
