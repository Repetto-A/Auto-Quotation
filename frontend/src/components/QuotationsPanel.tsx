import React, { useEffect, useMemo, useState } from 'react';
import { Search, Trash2, RotateCcw } from 'lucide-react';
import { API_CONFIG, getApiUrl, getAuthHeaders } from '../config/api';
import { AdminQuotation } from '../types';

type QuotationsResponse = {
  items: AdminQuotation[];
  total: number;
  limit: number;
  offset: number;
};

const PAGE_SIZE = 20;

export default function QuotationsPanel() {
  const [items, setItems] = useState<AdminQuotation[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);
  const currentPage = useMemo(() => Math.floor(offset / PAGE_SIZE) + 1, [offset]);

  const notify = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 3000);
  };

  const fetchQuotations = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        include_deleted: includeDeleted ? 'true' : 'false',
        limit: String(PAGE_SIZE),
        offset: String(offset),
        sort: 'created_at_desc',
      });
      const term = search.trim();
      if (term) params.set('q', term);

      const response = await fetch(
        getApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_QUOTATIONS_LIST}?${params.toString()}`),
        { headers: getAuthHeaders() }
      );

      if (!response.ok) throw new Error(`Error ${response.status}`);
      const data = (await response.json()) as QuotationsResponse | AdminQuotation[];

      if (Array.isArray(data)) {
        setItems(data);
        setTotal(data.length);
      } else {
        setItems(data.items || []);
        setTotal(data.total || 0);
      }
    } catch (err) {
      setError('No se pudo cargar el historial de cotizaciones.');
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuotations();
  }, [offset, includeDeleted]);

  useEffect(() => {
    const id = setTimeout(() => {
      setOffset(0);
      fetchQuotations();
    }, 350);
    return () => clearTimeout(id);
  }, [search]);

  const deleteQuotation = async (id: number) => {
    if (!confirm('Seguro que queres ocultar esta cotizacion del historial?')) return;
    try {
      const path = API_CONFIG.ENDPOINTS.ADMIN_QUOTATION_DELETE.replace('{id}', String(id));
      const response = await fetch(getApiUrl(path), {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error();
      notify('success', 'Cotizacion ocultada.');
      fetchQuotations();
    } catch {
      notify('error', 'No se pudo ocultar la cotizacion.');
    }
  };

  const restoreQuotation = async (id: number) => {
    try {
      const path = API_CONFIG.ENDPOINTS.ADMIN_QUOTATION_RESTORE.replace('{id}', String(id));
      const response = await fetch(getApiUrl(path), {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error();
      notify('success', 'Cotizacion restaurada.');
      fetchQuotations();
    } catch {
      notify('error', 'No se pudo restaurar la cotizacion.');
    }
  };

  const formatDate = (value: string) =>
    new Date(value).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' });

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Historial de Cotizaciones</h2>
        <p className="text-sm text-gray-500 mt-1">Siempre se muestran primero las mas recientes.</p>
      </div>

      <div className="px-6 py-4 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por cliente, CUIT, maquina o empresa..."
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
          />
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={includeDeleted}
            onChange={(e) => {
              setIncludeDeleted(e.target.checked);
              setOffset(0);
            }}
            className="rounded border-gray-300 text-green-600 focus:ring-green-500"
          />
          Mostrar eliminadas
        </label>
      </div>

      {message && (
        <div
          className={`mx-6 mt-4 p-3 rounded-lg text-sm ${
            message.type === 'success'
              ? 'bg-green-50 border border-green-200 text-green-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}
        >
          {message.text}
        </div>
      )}

      {error && <div className="mx-6 mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">{error}</div>}

      <div className="overflow-x-auto">
        <table className="w-full table-fixed divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="w-[7%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
              <th className="w-[16%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
              <th className="w-[20%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cliente</th>
              <th className="w-[15%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">CUIT</th>
              <th className="w-[14%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Maquina</th>
              <th className="w-[12%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Precio final</th>
              <th className="w-[8%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
              <th className="w-[8%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading ? (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-sm text-gray-500">
                  Cargando cotizaciones...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-8 text-center text-sm text-gray-500">
                  No hay cotizaciones para los filtros actuales.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id}>
                  <td className="px-3 py-3 text-sm text-gray-900">{item.id}</td>
                  <td className="px-3 py-3 text-sm text-gray-600">{formatDate(item.created_at)}</td>
                  <td className="px-3 py-3 text-sm text-gray-900 truncate" title={item.client_name}>
                    {item.client_name}
                  </td>
                  <td className="px-3 py-3 text-sm text-gray-600 truncate" title={item.client_cuit}>
                    {item.client_cuit}
                  </td>
                  <td className="px-3 py-3 text-sm text-gray-600 truncate" title={item.machine_code}>
                    {item.machine_code}
                  </td>
                  <td className="px-3 py-3 text-sm font-medium text-gray-900">
                    ${Number(item.final_price || 0).toLocaleString('es-AR')}
                  </td>
                  <td className="px-3 py-3 text-sm">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        item.is_deleted ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                      }`}
                    >
                      {item.is_deleted ? 'Eliminada' : 'Activa'}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-sm">
                    {item.is_deleted ? (
                      <button
                        onClick={() => restoreQuotation(item.id)}
                        className="text-green-600 hover:text-green-800"
                        title="Restaurar"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    ) : (
                      <button
                        onClick={() => deleteQuotation(item.id)}
                        className="text-red-600 hover:text-red-800"
                        title="Eliminar"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="px-6 py-4 border-t border-gray-100 flex items-center justify-between">
        <p className="text-sm text-gray-500">
          Pagina {currentPage} de {totalPages} ({total} resultados)
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
            disabled={offset === 0}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Anterior
          </button>
          <button
            onClick={() => setOffset((prev) => (prev + PAGE_SIZE < total ? prev + PAGE_SIZE : prev))}
            disabled={offset + PAGE_SIZE >= total}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>
  );
}
