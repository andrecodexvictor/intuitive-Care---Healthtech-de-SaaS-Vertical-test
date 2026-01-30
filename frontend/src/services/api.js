/**
 * API Service - Comunicação com Backend FastAPI
 * 
 * Centraliza todas as chamadas HTTP para a API.
 * Usa Axios com interceptors para tratamento de erros.
 */
import axios from 'axios'

// Base URL da API (ajustar conforme ambiente)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Instância Axios configurada
const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Interceptor de resposta para tratamento de erros
api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('API Error:', error.response?.data || error.message)
        return Promise.reject(error)
    }
)

/**
 * Serviço de Operadoras
 */
export const operadorasService = {
    /**
     * Lista operadoras com paginação e filtros
     */
    async list({ page = 1, limit = 20, razaoSocial = '', cnpj = '' } = {}) {
        const params = { page, limit }
        if (razaoSocial) params.razao_social = razaoSocial
        if (cnpj) params.cnpj = cnpj

        const response = await api.get('/api/operadoras', { params })
        return response.data
    },

    /**
     * Busca detalhes de uma operadora
     */
    async getById(cnpj) {
        const response = await api.get(`/api/operadoras/${cnpj}`)
        return response.data
    },

    /**
     * Lista despesas de uma operadora
     */
    async getDespesas(cnpj, { ano, trimestre } = {}) {
        const params = {}
        if (ano) params.ano = ano
        if (trimestre) params.trimestre = trimestre

        const response = await api.get(`/api/operadoras/${cnpj}/despesas`, { params })
        return response.data
    },
}

/**
 * Serviço de Estatísticas
 */
export const estatisticasService = {
    /**
     * Busca estatísticas gerais
     */
    async getGerais() {
        const response = await api.get('/api/estatisticas')
        return response.data
    },

    /**
     * Busca distribuição por UF
     */
    async getDistribuicaoUF() {
        const response = await api.get('/api/estatisticas/distribuicao-uf')
        return response.data
    },
}

export default api
