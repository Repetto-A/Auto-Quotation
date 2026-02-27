// Configuración de la API
const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV
    ? 'http://localhost:8000'
    : 'https://backend-production-75ca.up.railway.app');

export const API_CONFIG = {
  BASE_URL: API_BASE_URL,
  ENDPOINTS: {
    MACHINES: '/machines',
    ADMIN_MACHINES: '/admin/machines',
    QUOTATIONS: '/quotations',
    QUOTATION_STATS: '/quotations/stats',
    CREATE_QUOTATION: '/quotations',
    GENERATE_QUOTE: '/generate-quote',
    OPTIONS: '/options',
    ADMIN_OPTIONS: '/admin/options',
    ADMIN_LOGIN: '/admin/login',
    ADMIN_LOGOUT: '/admin/logout',
    ADMIN_VERIFY: '/admin/verify',
    AFIP_CLIENT: '/api/afip/client',
    MACHINE_OPTIONS: '/machines/{machine_code}/options',
    EXCHANGE_RATE: '/admin/exchange-rate',
    EXCHANGE_RATE_MANUAL: '/admin/exchange-rate/manual',
    EXCHANGE_RATE_BNA: '/admin/exchange-rate/bna',
    PAYMENT_CONDITIONS: '/payment-conditions',
    ADMIN_PAYMENT_CONDITIONS: '/admin/payment-conditions',
    PRICE_LIST_PREVIEW: '/admin/price-list/preview',
    PRICE_LIST_CONFIRM: '/admin/price-list/confirm',
    ADMIN_PRICE_LIST_MACHINES: '/admin/price-list/machines'
  }
};

export const getApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// Función para obtener el token de autenticación
export const getAuthToken = (): string | null => {
  return localStorage.getItem('admin_token');
};

// Función para establecer el token de autenticación
export const setAuthToken = (token: string): void => {
  localStorage.setItem('admin_token', token);
};

// Función para eliminar el token de autenticación
export const removeAuthToken = (): void => {
  localStorage.removeItem('admin_token');
};

// Función para obtener headers de autenticación
export const getAuthHeaders = (): Record<string, string> => {
  const token = getAuthToken();
  return token ? { 'Authorization': `Bearer ${token}` } : {};
};

// Función para verificar si el usuario está autenticado
export const isAuthenticated = (): boolean => {
  const token = getAuthToken();
  if (!token) return false;
  
  try {
    // Verificar si el token no ha expirado (verificación básica)
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // Convertir a milisegundos
    return Date.now() < exp;
  } catch {
    return false;
  }
}; 
