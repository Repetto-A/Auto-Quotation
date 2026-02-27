import React, { useState, useEffect } from 'react';
import { RefreshCw, Save, Plus, Trash2, AlertCircle, CheckCircle } from 'lucide-react';
import { getApiUrl, getAuthHeaders } from '../config/api';

interface ExchangeRate {
  id?: number;
  rate: number | null;
  source: string | null;
  fetched_at: string | null;
}

interface PaymentCondition {
  id?: number;
  name: string;
  discount_percent: number;
  description?: string;
  active: boolean;
  sort_order: number;
}

export default function SettingsPanel() {
  const [rate, setRate] = useState<ExchangeRate | null>(null);
  const [manualRate, setManualRate] = useState('');
  const [conditions, setConditions] = useState<PaymentCondition[]>([]);
  const [newCond, setNewCond] = useState({ name: '', discount_percent: '0', description: '' });
  const [loadingRate, setLoadingRate] = useState(false);
  const [loadingBna, setLoadingBna] = useState(false);
  const [savingCond, setSavingCond] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadRate();
    loadConditions();
  }, []);

  const notify = (type: 'success' | 'error', text: string) => {
    setMsg({ type, text });
    setTimeout(() => setMsg(null), 3500);
  };

  const loadRate = async () => {
    try {
      const res = await fetch(getApiUrl('/admin/exchange-rate'), { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setRate(data);
        if (data.rate) setManualRate(String(data.rate));
      }
    } catch {}
  };

  const loadConditions = async () => {
    try {
      const res = await fetch(getApiUrl('/admin/payment-conditions'), { headers: getAuthHeaders() });
      if (res.ok) setConditions(await res.json());
    } catch {}
  };

  const handleSaveManualRate = async () => {
    const val = parseFloat(manualRate);
    if (!val || val <= 0) { notify('error', 'Ingresá un valor válido'); return; }
    setLoadingRate(true);
    try {
      const res = await fetch(getApiUrl('/admin/exchange-rate/manual'), {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ rate: val }),
      });
      if (res.ok) {
        notify('success', `Tipo de cambio guardado: ARS ${val}`);
        loadRate();
      } else {
        notify('error', 'Error al guardar');
      }
    } finally {
      setLoadingRate(false);
    }
  };

  const handleFetchBna = async () => {
    setLoadingBna(true);
    try {
      const res = await fetch(getApiUrl('/admin/exchange-rate/bna'), {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        notify('success', `BNA: USD 1 = ARS ${data.rate}`);
        setManualRate(String(data.rate));
        loadRate();
      } else {
        const err = await res.json();
        notify('error', err.detail || 'Error consultando BNA');
      }
    } finally {
      setLoadingBna(false);
    }
  };

  const handleAddCondition = async () => {
    if (!newCond.name.trim()) { notify('error', 'El nombre es requerido'); return; }
    setSavingCond(true);
    try {
      const res = await fetch(getApiUrl('/admin/payment-conditions'), {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newCond.name.trim(),
          discount_percent: parseFloat(newCond.discount_percent) || 0,
          description: newCond.description.trim(),
          sort_order: conditions.length,
        }),
      });
      if (res.ok) {
        notify('success', 'Condición agregada');
        setNewCond({ name: '', discount_percent: '0', description: '' });
        loadConditions();
      } else {
        notify('error', 'Error al guardar');
      }
    } finally {
      setSavingCond(false);
    }
  };

  const handleToggleActive = async (cond: PaymentCondition) => {
    try {
      await fetch(getApiUrl(`/admin/payment-conditions/${cond.id}`), {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !cond.active }),
      });
      loadConditions();
    } catch {}
  };

  const handleDeleteCondition = async (id: number) => {
    if (!confirm('¿Eliminar esta condición?')) return;
    try {
      await fetch(getApiUrl(`/admin/payment-conditions/${id}`), {
        method: 'DELETE',
        headers: getAuthHeaders(),
      });
      loadConditions();
    } catch {}
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' });
  };

  return (
    <div className="space-y-6">
      {/* Notification */}
      {msg && (
        <div className={`flex items-center space-x-2 rounded-lg p-3 text-sm ${
          msg.type === 'success' ? 'bg-green-50 border border-green-200 text-green-800' : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          {msg.type === 'success'
            ? <CheckCircle className="w-4 h-4 flex-shrink-0" />
            : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
          <span>{msg.text}</span>
        </div>
      )}

      {/* Tipo de cambio */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Tipo de Cambio USD / ARS</h3>
        {rate?.rate && (
          <p className="text-sm text-gray-500 mb-4">
            Vigente: <span className="font-medium text-gray-800">ARS {rate.rate.toLocaleString('es-AR')}</span>
            {' '}· {rate.source} · {formatDate(rate.fetched_at)}
          </p>
        )}

        <div className="flex items-center space-x-3 mb-4">
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">Valor manual (ARS por 1 USD)</label>
            <input
              type="number"
              value={manualRate}
              onChange={e => setManualRate(e.target.value)}
              placeholder="ej: 1250"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={handleSaveManualRate}
            disabled={loadingRate}
            className="mt-5 flex items-center space-x-1 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Guardar</span>
          </button>
        </div>

        <button
          onClick={handleFetchBna}
          disabled={loadingBna}
          className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800 border border-blue-200 rounded-lg px-4 py-2 hover:bg-blue-50 transition-colors disabled:opacity-50"
        >
          {loadingBna
            ? <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-blue-600" />
            : <RefreshCw className="w-3.5 h-3.5" />}
          <span>Obtener desde BNA automáticamente</span>
        </button>
      </div>

      {/* Condiciones de pago */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Condiciones de Pago</h3>

        {/* Lista */}
        {conditions.length > 0 ? (
          <div className="divide-y divide-gray-100 mb-6 border border-gray-200 rounded-lg overflow-hidden">
            {conditions.map(cond => (
              <div key={cond.id} className={`flex items-center justify-between px-4 py-3 ${!cond.active ? 'bg-gray-50 opacity-60' : ''}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-900">{cond.name}</span>
                    {cond.discount_percent > 0 && (
                      <span className="text-xs font-medium text-green-700 bg-green-100 px-1.5 py-0.5 rounded">
                        -{cond.discount_percent}%
                      </span>
                    )}
                    {!cond.active && (
                      <span className="text-xs text-gray-400">inactiva</span>
                    )}
                  </div>
                  {cond.description && (
                    <p className="text-xs text-gray-500 mt-0.5 truncate">{cond.description}</p>
                  )}
                </div>
                <div className="flex items-center space-x-2 ml-3">
                  <button
                    onClick={() => handleToggleActive(cond)}
                    className={`text-xs px-2 py-1 rounded ${cond.active ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'}`}
                  >
                    {cond.active ? 'Desactivar' : 'Activar'}
                  </button>
                  <button
                    onClick={() => cond.id && handleDeleteCondition(cond.id)}
                    className="text-red-400 hover:text-red-600"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500 mb-4">No hay condiciones de pago configuradas. Podés importarlas desde el PDF de lista de precios.</p>
        )}

        {/* Agregar nueva */}
        <div className="border border-dashed border-gray-300 rounded-lg p-4">
          <p className="text-xs font-medium text-gray-500 mb-3">Agregar condición</p>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div className="col-span-2">
              <input
                type="text"
                value={newCond.name}
                onChange={e => setNewCond(p => ({ ...p, name: e.target.value }))}
                placeholder="Nombre (ej: Contado)"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
              />
            </div>
            <div>
              <div className="relative">
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={newCond.discount_percent}
                  onChange={e => setNewCond(p => ({ ...p, discount_percent: e.target.value }))}
                  placeholder="0"
                  className="w-full border border-gray-300 rounded-lg pl-3 pr-8 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
                />
                <span className="absolute right-3 top-2.5 text-sm text-gray-400">%</span>
              </div>
            </div>
          </div>
          <div className="mb-3">
            <input
              type="text"
              value={newCond.description}
              onChange={e => setNewCond(p => ({ ...p, description: e.target.value }))}
              placeholder="Descripción (opcional, ej: 5 cheques a 30 días)"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={handleAddCondition}
            disabled={savingCond}
            className="flex items-center space-x-1 bg-green-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Agregar</span>
          </button>
        </div>
      </div>
    </div>
  );
}
