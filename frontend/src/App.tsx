import React, { useState, useEffect } from 'react';
import {
  Download, Share2, Phone, Mail, User, Building, Package,
  AlertCircle, Tractor, Settings, Plus, Minus,
  Percent, RotateCcw, FileText, Calculator, MapPin,
  MessageSquare, Trash2, X, Search
} from 'lucide-react';
import MachinerySelector from './components/MachinerySelector';
import { findMachineByCode } from './utils/machineUtils';
import { getApiUrl, API_CONFIG } from './config/api';
import { Link } from 'react-router-dom';

// ─── Types ──────────────────────────────────────────────────────────────────

interface QuotationForm {
  clientName: string;
  clientCuit: string;
  clientPhone: string;
  clientEmail: string;
  clientCompany: string;
  clientAddress: string;
  notes: string;
  discountPercent: number;
}

interface LineItem {
  id: string;
  machineCode: string;
  quantity: number;
}

interface MachineFromAPI {
  id: number;
  code: string;
  name: string;
  price: number;
  category: string;
  description: string;
  active: boolean;
}

interface AFIPPersonaData {
  cuit: string;
  nombre?: string;
  razon_social?: string;
  domicilio_fiscal?: string;
}

// ─── Component ──────────────────────────────────────────────────────────────

function App() {
  const [machines, setMachines] = useState<MachineFromAPI[]>([]);
  const [isLoadingMachines, setIsLoadingMachines] = useState(true);
  const [machineError, setMachineError] = useState<string | null>(null);

  useEffect(() => {
    const loadMachines = async () => {
      try {
        setIsLoadingMachines(true);
        setMachineError(null);
        const response = await fetch(getApiUrl(API_CONFIG.ENDPOINTS.MACHINES));
        if (response.ok) {
          const data: MachineFromAPI[] = await response.json();
          setMachines(data.filter(m => m.active));
        } else {
          throw new Error(`Error ${response.status}`);
        }
      } catch {
        setMachineError('No se pudieron cargar las máquinas desde el servidor.');
        setMachines([]);
      } finally {
        setIsLoadingMachines(false);
      }
    };
    loadMachines();
  }, []);

  const [form, setForm] = useState<QuotationForm>({
    clientName: '',
    clientCuit: '',
    clientPhone: '',
    clientEmail: '',
    clientCompany: '',
    clientAddress: '',
    notes: '',
    discountPercent: 0,
  });

  const [lineItems, setLineItems] = useState<LineItem[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [lastQuotation, setLastQuotation] = useState<string | null>(null);
  const [showMachineSelector, setShowMachineSelector] = useState(false);
  const [isLoadingAfip, setIsLoadingAfip] = useState(false);
  const [afipError, setAfipError] = useState<string | null>(null);

  // ─── Form handlers ────────────────────────────────────────────────────────

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setForm(prev => ({
      ...prev,
      [name]: name === 'discountPercent' ? parseFloat(value) || 0 : value,
    }));
  };

  const setQuickDiscount = (pct: number) => {
    setForm(prev => ({
      ...prev,
      discountPercent: prev.discountPercent === pct ? 0 : pct,
    }));
  };

  const fetchClientData = async () => {
    if (!form.clientCuit.trim()) {
      setAfipError('Por favor ingresá un CUIT');
      return;
    }

    setIsLoadingAfip(true);
    setAfipError(null);

    try {
      const response = await fetch(
        getApiUrl(`/api/afip/client/${encodeURIComponent(form.clientCuit.trim())}`)
      );
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al consultar AFIP');
      }

      const personaData: AFIPPersonaData = await response.json();
      setForm(prev => ({
        ...prev,
        clientName: personaData.nombre || prev.clientName,
        clientAddress: personaData.domicilio_fiscal || prev.clientAddress,
        clientCompany: personaData.razon_social || prev.clientCompany,
      }));
    } catch (error) {
      setAfipError(error instanceof Error ? error.message : 'Error desconocido al consultar AFIP');
    } finally {
      setIsLoadingAfip(false);
    }
  };

  // ─── Line item handlers ───────────────────────────────────────────────────

  const handleMachineSelect = (code: string) => {
    setLineItems(prev => {
      const existing = prev.find(item => item.machineCode === code);
      if (existing) {
        // Already in list → increment quantity
        return prev.map(item =>
          item.machineCode === code
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }
      return [...prev, { id: `${code}-${Date.now()}`, machineCode: code, quantity: 1 }];
    });
    setShowMachineSelector(false);
  };

  const removeLineItem = (id: string) => {
    setLineItems(prev => prev.filter(item => item.id !== id));
  };

  const adjustQuantity = (id: string, delta: number) => {
    setLineItems(prev =>
      prev.map(item =>
        item.id === id
          ? { ...item, quantity: Math.max(1, item.quantity + delta) }
          : item
      )
    );
  };

  const updateQuantityInput = (id: string, value: number) => {
    setLineItems(prev =>
      prev.map(item =>
        item.id === id ? { ...item, quantity: Math.max(1, value || 1) } : item
      )
    );
  };

  // ─── Computed values ──────────────────────────────────────────────────────

    const lineItemDetails = lineItems.map(item => {
      const machine = findMachineByCode(item.machineCode, machines);
      const unitPrice = machine?.price ?? 0;
    const subtotal = unitPrice * item.quantity;
    return { ...item, machine, unitPrice, subtotal };
  });

  const grandSubtotal = lineItemDetails.reduce((sum, i) => sum + i.subtotal, 0);
  const discountAmount = (grandSubtotal * form.discountPercent) / 100;
  const grandTotal = grandSubtotal - discountAmount;

  // ─── Submit & share ───────────────────────────────────────────────────────

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (lineItems.length === 0) {
      alert('Seleccioná al menos una máquina antes de generar la cotización.');
      return;
    }
    setIsGenerating(true);
    try {
      const primaryItem = lineItemDetails[0];
      const extraLines = lineItemDetails
        .map(
          (i, idx) =>
            `${idx + 1}. ${i.machine?.name ?? i.machineCode} (${i.machineCode}) x${i.quantity} — $${i.subtotal.toLocaleString()}`
        )
        .join('\n');

      const notesText = [
        lineItemDetails.length > 1 && `Productos cotizados:\n${extraLines}`,
        form.clientAddress && `Domicilio: ${form.clientAddress}`,
        form.discountPercent > 0 && `Descuento global: ${form.discountPercent}%`,
        form.notes && `Observaciones: ${form.notes}`,
      ]
        .filter(Boolean)
        .join('\n');

      const quotationData = {
        machineCode: primaryItem.machineCode,
        clientCuit: form.clientCuit,
        clientName: form.clientName,
        clientPhone: form.clientPhone,
        clientEmail: form.clientEmail,
        clientCompany: form.clientCompany,
        notes: notesText,
        applyDiscount: form.discountPercent > 0,
      };

      const response = await fetch(getApiUrl(API_CONFIG.ENDPOINTS.GENERATE_QUOTE), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(quotationData),
      });

      if (response.ok) {
        const pdfBlob = await response.blob();
        setLastQuotation(URL.createObjectURL(pdfBlob));
      } else {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error generating quotation:', error);
      alert('Error al generar la cotización. Por favor, inténtalo de nuevo.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleShare = async () => {
    if (!lastQuotation) return;
    const shareText = `Cotización Agromaq\n\nCliente: ${form.clientName}\nTotal: $${grandTotal.toLocaleString()}`;
    try {
      const response = await fetch(lastQuotation);
      const pdfBlob = await response.blob();
      const pdfFile = new File(
        [pdfBlob],
        `cotizacion-${form.clientName.replace(' ', '-')}.pdf`,
        { type: 'application/pdf' }
      );
      if (navigator.share && navigator.canShare && navigator.canShare({ files: [pdfFile] })) {
        await navigator.share({ title: 'Cotización Agromaq', text: shareText, files: [pdfFile] });
      } else {
        window.open(`https://wa.me/?text=${encodeURIComponent(shareText)}`, '_blank');
      }
    } catch {
      window.open(`https://wa.me/?text=${encodeURIComponent(shareText)}`, '_blank');
    }
  };

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Header ── */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14 sm:h-16">
            <img src="/test.png" alt="Logo Agromaq" className="w-28 sm:w-32 h-auto" />
            <Link
              to="/admin"
              className="flex items-center gap-1.5 text-gray-400 hover:text-green-600 transition-colors"
            >
              <Settings className="w-4 h-4" />
              <span className="text-sm hidden sm:inline">Administración</span>
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-8">
        <form onSubmit={handleSubmit}>
          {/*
            Grid layout:
            - Mobile  → 1 col, right column renders FIRST via order-first
            - Desktop → 3 col, left=2/3 right=1/3
          */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">

            {/* ── RIGHT COLUMN — Maquinaria + Resumen (first on mobile) ── */}
            <div className="lg:col-span-1 order-first lg:order-last">
              <div className="lg:sticky lg:top-8 space-y-4 sm:space-y-6">

                {/* Machine cards */}
                <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
                  <div className="flex items-center justify-between mb-4 sm:mb-5">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 sm:w-8 sm:h-8 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
                        <Package className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-500" />
                      </div>
                      <h2 className="text-base sm:text-lg font-semibold text-gray-900">
                        Maquinaria
                      </h2>
                    </div>
                    {lineItems.length > 0 && (
                      <button
                        type="button"
                        onClick={() => setShowMachineSelector(true)}
                        className="flex items-center gap-1.5 text-sm font-medium text-green-600 hover:text-green-700 transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        Agregar
                      </button>
                    )}
                  </div>

                  {lineItems.length === 0 ? (
                    <button
                      type="button"
                      onClick={() => setShowMachineSelector(true)}
                      className="w-full py-10 sm:py-12 border-2 border-dashed border-gray-200 rounded-lg hover:border-green-400 hover:bg-green-50/30 transition-all group"
                    >
                      <Tractor className="w-8 h-8 text-gray-300 group-hover:text-green-400 mx-auto mb-2.5 transition-colors" />
                      <p className="text-sm font-medium text-gray-500 group-hover:text-green-600 transition-colors">
                        Seleccionar Maquinaria
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        +50 productos · 10 categorías
                      </p>
                    </button>
                  ) : (
                    <div className="space-y-4">
                      {lineItemDetails.map((item, idx) => (
                        <div
                          key={item.id}
                          className={`rounded-lg border border-gray-100 p-3 sm:p-4 space-y-3 ${
                            idx < lineItemDetails.length - 1
                              ? 'pb-4 border-b border-gray-100'
                              : ''
                          }`}
                        >
                          {/* Machine name + remove */}
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="text-sm font-semibold text-gray-900 leading-snug">
                                {item.machine?.name ?? item.machineCode}
                              </p>
                              <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                                <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded font-mono">
                                  {item.machineCode}
                                </span>
                                <span className="text-xs text-gray-400">
                                  {item.machine?.category}
                                </span>
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() => removeLineItem(item.id)}
                              className="p-1 text-gray-300 hover:text-red-400 transition-colors shrink-0 mt-0.5"
                              aria-label="Eliminar"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>

                          {/* Price grid */}
                          <div className="grid grid-cols-3 gap-px bg-gray-100 rounded-lg overflow-hidden">
                            <div className="bg-white p-2.5 sm:p-3">
                              <p className="text-xs text-gray-400 font-medium mb-0.5">Base</p>
                              <p className="text-xs sm:text-sm font-semibold text-gray-900">
                                ${item.unitPrice.toLocaleString()}
                              </p>
                            </div>
                            <div className="bg-white p-2.5 sm:p-3">
                              <p className="text-xs text-gray-400 font-medium mb-0.5">Desc.</p>
                              <p className="text-xs sm:text-sm font-semibold text-red-500">
                                {form.discountPercent > 0
                                  ? `−$${((item.unitPrice * form.discountPercent) / 100).toLocaleString()}`
                                  : '—'}
                              </p>
                            </div>
                            <div className="bg-white p-2.5 sm:p-3">
                              <p className="text-xs text-gray-400 font-medium mb-0.5">Final</p>
                              <p className="text-xs sm:text-sm font-bold text-green-600">
                                ${(item.unitPrice * (1 - form.discountPercent / 100)).toLocaleString()}
                              </p>
                            </div>
                          </div>

                          {/* Quantity + subtotal */}
                          <div className="flex items-center justify-between">
                            <div className="inline-flex items-center">
                              <button
                                type="button"
                                onClick={() => adjustQuantity(item.id, -1)}
                                disabled={item.quantity <= 1}
                                className="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-l-lg text-gray-500 hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                              >
                                <Minus className="w-3 h-3" />
                              </button>
                              <input
                                type="number"
                                value={item.quantity}
                                onChange={e =>
                                  updateQuantityInput(item.id, parseInt(e.target.value))
                                }
                                min="1"
                                className="w-11 h-8 text-center text-sm font-semibold border-y border-gray-200 focus:ring-2 focus:ring-green-500 focus:border-transparent [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                              />
                              <button
                                type="button"
                                onClick={() => adjustQuantity(item.id, 1)}
                                className="w-8 h-8 flex items-center justify-center border border-gray-200 rounded-r-lg text-gray-500 hover:bg-gray-50 transition-colors"
                              >
                                <Plus className="w-3 h-3" />
                              </button>
                            </div>
                            <div className="text-right">
                              <span className="text-xs text-gray-400">Subtotal </span>
                              <span className="text-sm font-bold text-gray-900">
                                ${item.subtotal.toLocaleString()}
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}

                      {/* Add another machine */}
                      <button
                        type="button"
                        onClick={() => setShowMachineSelector(true)}
                        className="w-full py-2.5 border border-dashed border-gray-200 rounded-lg text-sm text-gray-400 hover:text-green-600 hover:border-green-400 hover:bg-green-50/20 transition-all flex items-center justify-center gap-1.5"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        Agregar otra máquina
                      </button>
                    </div>
                  )}
                </section>

                {/* Summary */}
                <section className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                  <div className="h-1 bg-green-500" />
                  <div className="p-4 sm:p-6">
                    <div className="flex items-center gap-2.5 mb-4 sm:mb-5">
                      <div className="w-7 h-7 sm:w-8 sm:h-8 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
                        <FileText className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-500" />
                      </div>
                      <h2 className="text-base sm:text-lg font-semibold text-gray-900">Resumen</h2>
                    </div>

                    {lineItems.length > 0 ? (
                      <div className="space-y-4">
                        {/* Per-machine subtotals */}
                        <div className="space-y-1.5">
                          {lineItemDetails.map(item => (
                            <div key={item.id} className="flex justify-between text-sm">
                              <span className="text-gray-500 truncate mr-2">
                                {item.machine?.name ?? item.machineCode}
                                {item.quantity > 1 && (
                                  <span className="text-gray-400"> ×{item.quantity}</span>
                                )}
                              </span>
                              <span className="text-gray-900 font-medium shrink-0">
                                ${item.subtotal.toLocaleString()}
                              </span>
                            </div>
                          ))}
                        </div>

                        {/* Discount row */}
                        {form.discountPercent > 0 && (
                          <div className="pt-2 border-t border-gray-100 space-y-1.5">
                            {lineItems.length > 1 && (
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-500">Subtotal</span>
                                <span className="text-gray-900 font-medium">
                                  ${grandSubtotal.toLocaleString()}
                                </span>
                              </div>
                            )}
                            <div className="flex justify-between text-sm">
                              <span className="text-gray-500">
                                Descuento ({form.discountPercent}%)
                              </span>
                              <span className="text-red-500 font-medium">
                                −${discountAmount.toLocaleString()}
                              </span>
                            </div>
                          </div>
                        )}

                        {/* Grand total */}
                        <div className="pt-3 border-t border-gray-200">
                          <div className="flex justify-between items-baseline">
                            <span className="text-sm font-semibold text-gray-700">
                              Total a pagar
                            </span>
                            <span className="text-2xl font-bold text-green-600">
                              ${grandTotal.toLocaleString()}
                            </span>
                          </div>
                        </div>

                        {/* Submit */}
                        <button
                          type="submit"
                          disabled={isGenerating}
                          className="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 active:bg-green-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium text-sm"
                        >
                          {isGenerating ? 'Generando…' : 'Generar Cotización'}
                        </button>

                        {/* Post-generation actions */}
                        {lastQuotation && (
                          <div className="pt-3 border-t border-gray-100 space-y-2">
                            <p className="text-xs font-medium text-green-600">
                              ✓ Cotización lista
                            </p>
                            <button
                              type="button"
                              onClick={async () => {
                                try {
                                  const res = await fetch(lastQuotation);
                                  const blob = await res.blob();
                                  const url = URL.createObjectURL(blob);
                                  const a = document.createElement('a');
                                  a.href = url;
                                  a.download = `cotizacion-${form.clientName.replace(/\s+/g, '-')}.pdf`;
                                  document.body.appendChild(a);
                                  a.click();
                                  document.body.removeChild(a);
                                  URL.revokeObjectURL(url);
                                } catch {
                                  window.open(lastQuotation, '_blank');
                                }
                              }}
                              className="w-full flex items-center justify-center gap-2 bg-gray-900 text-white px-4 py-2.5 rounded-lg hover:bg-gray-800 active:bg-gray-950 transition-colors text-sm font-medium"
                            >
                              <Download className="w-4 h-4" />
                              Descargar PDF
                            </button>
                            <button
                              type="button"
                              onClick={handleShare}
                              className="w-full flex items-center justify-center gap-2 border border-gray-200 text-gray-700 px-4 py-2.5 rounded-lg hover:bg-gray-50 active:bg-gray-100 transition-colors text-sm font-medium"
                            >
                              <Share2 className="w-4 h-4" />
                              Compartir
                            </button>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-6">
                        <Calculator className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                        <p className="text-sm text-gray-400">
                          Seleccioná una máquina para ver el resumen
                        </p>
                      </div>
                    )}
                  </div>
                </section>

              </div>
            </div>

            {/* ── LEFT COLUMN — Datos del Cliente + Bonificación ── */}
            <div className="lg:col-span-2 order-last lg:order-first space-y-4 sm:space-y-6">

              {/* Client Data */}
              <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
                <div className="flex items-center gap-2.5 mb-4 sm:mb-5">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
                    <User className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-500" />
                  </div>
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <h2 className="text-base sm:text-lg font-semibold text-gray-900">
                      Datos del Cliente
                    </h2>
                    {isLoadingMachines && (
                      <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full animate-pulse">
                        Cargando precios…
                      </span>
                    )}
                  </div>
                </div>

                {machineError && (
                  <div className="flex items-center gap-2 mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <AlertCircle className="w-4 h-4 text-amber-500 shrink-0" />
                    <p className="text-sm text-amber-700">{machineError}</p>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                  {/* CUIT + Buscar AFIP (prioritario) */}
                  <div className="sm:col-span-2">
                    <label className="block text-xs sm:text-sm font-semibold text-gray-700 mb-1.5">
                      CUIT
                    </label>
                    <div className="flex items-stretch gap-2">
                      <div className="relative flex-1">
                        <FileText className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                        <input
                          type="text"
                          name="clientCuit"
                          value={form.clientCuit}
                          onChange={(e) => {
                            handleInputChange(e);
                            if (afipError) setAfipError(null);
                          }}
                          className="w-full h-12 pl-11 pr-3 border border-gray-300 rounded-lg text-base focus:ring-2 focus:ring-green-500 focus:border-transparent transition-shadow placeholder:text-gray-300"
                          placeholder="20-12345678-9"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={fetchClientData}
                        disabled={isLoadingAfip || !form.clientCuit.trim()}
                        className="h-12 px-5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm font-semibold inline-flex items-center gap-2 whitespace-nowrap"
                        title="Buscar datos del cliente por CUIT"
                      >
                        {isLoadingAfip ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                        ) : (
                          <>
                            <Search className="w-4 h-4" />
                            Buscar por CUIT
                          </>
                        )}
                      </button>
                    </div>
                    {afipError && (
                      <p className="mt-2 text-sm text-red-600 flex items-center gap-1.5">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        {afipError}
                      </p>
                    )}
                  </div>

                  {/* Nombre */}
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-gray-500 mb-1.5">
                      Nombre Completo <span className="text-red-400">*</span>
                    </label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        name="clientName"
                        value={form.clientName}
                        onChange={handleInputChange}
                        required
                        className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent transition-shadow placeholder:text-gray-300"
                        placeholder="Juan Pérez"
                      />
                    </div>
                  </div>

                  {/* Empresa */}
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-gray-500 mb-1.5">
                      Empresa / Razón Social
                    </label>
                    <div className="relative">
                      <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        name="clientCompany"
                        value={form.clientCompany}
                        onChange={handleInputChange}
                        className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent transition-shadow placeholder:text-gray-300"
                        placeholder="Agro SRL"
                      />
                    </div>
                  </div>

                  {/* Teléfono */}
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-gray-500 mb-1.5">
                      Teléfono
                    </label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="tel"
                        name="clientPhone"
                        value={form.clientPhone}
                        onChange={handleInputChange}
                        className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent transition-shadow placeholder:text-gray-300"
                        placeholder="+54 9 11 1234-5678"
                      />
                    </div>
                  </div>

                  {/* Email */}
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-gray-500 mb-1.5">
                      Email
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="email"
                        name="clientEmail"
                        value={form.clientEmail}
                        onChange={handleInputChange}
                        className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent transition-shadow placeholder:text-gray-300"
                        placeholder="juan@empresa.com"
                      />
                    </div>
                  </div>

                  {/* Domicilio */}
                  <div>
                    <label className="block text-xs sm:text-sm font-medium text-gray-500 mb-1.5">
                      Domicilio
                    </label>
                    <div className="relative">
                      <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        name="clientAddress"
                        value={form.clientAddress}
                        onChange={handleInputChange}
                        className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent transition-shadow placeholder:text-gray-300"
                        placeholder="Av. Corrientes 1234, CABA"
                      />
                    </div>
                  </div>

                  {/* Notas — full width */}
                  <div className="sm:col-span-2">
                    <label className="block text-xs sm:text-sm font-medium text-gray-500 mb-1.5">
                      Notas / Observaciones
                    </label>
                    <div className="relative">
                      <MessageSquare className="absolute left-3 top-3 w-4 h-4 text-gray-400" />
                      <textarea
                        name="notes"
                        value={form.notes}
                        onChange={handleInputChange}
                        rows={3}
                        className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent transition-shadow placeholder:text-gray-300 resize-none"
                        placeholder="Condiciones especiales, plazos de entrega, observaciones…"
                      />
                    </div>
                  </div>
                </div>
              </section>

              {/* Bonificación */}
              <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
                <div className="flex items-center justify-between mb-3 sm:mb-4">
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 sm:w-8 sm:h-8 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
                      <Percent className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-500" />
                    </div>
                    <h2 className="text-base sm:text-lg font-semibold text-gray-900">
                      Bonificación
                    </h2>
                  </div>
                  {form.discountPercent > 0 && (
                    <button
                      type="button"
                      onClick={() => setForm(prev => ({ ...prev, discountPercent: 0 }))}
                      className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
                    >
                      <RotateCcw className="w-3 h-3" />
                      Limpiar
                    </button>
                  )}
                </div>

                <div className="flex flex-col sm:flex-row sm:items-end gap-3">
                  <div className="flex-1">
                    <label className="block text-xs sm:text-sm font-medium text-gray-500 mb-1.5">
                      Descuento global
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        name="discountPercent"
                        value={form.discountPercent}
                        onChange={handleInputChange}
                        min="0"
                        max="100"
                        step="0.1"
                        className="w-full pr-8 pl-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-500 focus:border-transparent transition-shadow [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                        placeholder="0"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-medium">
                        %
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-1.5 flex-wrap">
                    {[5, 10, 15, 20].map(pct => (
                      <button
                        key={pct}
                        type="button"
                        onClick={() => setQuickDiscount(pct)}
                        className={`px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                          form.discountPercent === pct
                            ? 'bg-green-600 text-white shadow-sm'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {pct}%
                      </button>
                    ))}
                  </div>
                </div>
              </section>

            </div>
          </div>
        </form>
      </main>

      {/* ── Machine Selector Modal ── */}
      {showMachineSelector && (
        <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center p-0 sm:p-4 z-50">
          <div className="bg-white rounded-t-2xl sm:rounded-xl shadow-xl w-full sm:max-w-2xl max-h-[90vh] sm:max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 sm:p-6 border-b border-gray-200 flex items-center justify-between shrink-0">
              <h3 className="text-base sm:text-lg font-semibold text-gray-900">
                Seleccionar Maquinaria
              </h3>
              <button
                type="button"
                onClick={() => setShowMachineSelector(false)}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 sm:p-6 overflow-y-auto flex-1">
              <MachinerySelector
                selectedMachine={lineItems[lineItems.length - 1]?.machineCode ?? ''}
                onMachineSelect={handleMachineSelect}
                machines={machines}
                isLoadingMachines={isLoadingMachines}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

