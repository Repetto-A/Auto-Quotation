import React, { useState, useRef } from 'react';
import { Upload, CheckCircle, AlertCircle, Eye, Save, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react';
import { getApiUrl, getAuthHeaders } from '../config/api';

interface ParsedOptional {
  name: string;
  price: number | null;
}

interface ParsedProduct {
  code: string;
  product_title: string;
  model_name: string;
  name: string;
  category: string;
  price: number | null;
  price_currency: string;
  specs: string[];
  optionals: ParsedOptional[];
  // UI state
  _selected?: boolean;
  _expanded?: boolean;
}

interface ParsedCondition {
  name: string;
  discount_percent: number;
  description: string;
  sort_order: number;
}

interface PreviewData {
  products: ParsedProduct[];
  payment_conditions: ParsedCondition[];
  total_products: number;
  total_with_price: number;
}

interface ConfirmResult {
  imported: number;
  updated: number;
  errors: string[];
  payment_conditions_imported: number;
}

interface Props {
  onImportComplete?: () => void;
}

export default function PriceListImport({ onImportComplete }: Props) {
  const [step, setStep] = useState<'idle' | 'loading' | 'preview' | 'confirming' | 'done'>('idle');
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [products, setProducts] = useState<ParsedProduct[]>([]);
  const [conditions, setConditions] = useState<ParsedCondition[]>([]);
  const [replaceExisting, setReplaceExisting] = useState(true);
  const [result, setResult] = useState<ConfirmResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('El archivo debe ser un PDF');
      return;
    }

    setStep('loading');
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(getApiUrl('/admin/price-list/preview'), {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Error al procesar el PDF');
      }

      const data: PreviewData = await response.json();
      const prods = data.products.map(p => ({ ...p, _selected: p.price !== null, _expanded: false }));
      setPreview(data);
      setProducts(prods);
      setConditions(data.payment_conditions);
      setStep('preview');
    } catch (err: any) {
      setError(err.message || 'Error inesperado');
      setStep('idle');
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const handleConfirm = async () => {
    const selectedProducts = products.filter(p => p._selected);
    if (selectedProducts.length === 0) {
      setError('Seleccioná al menos un producto para importar');
      return;
    }

    setStep('confirming');
    setError(null);

    // Clean UI state before sending
    const cleanProducts = selectedProducts.map(({ _selected, _expanded, ...p }) => p);

    try {
      const response = await fetch(getApiUrl('/admin/price-list/confirm'), {
        method: 'POST',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          products: cleanProducts,
          payment_conditions: conditions,
          replace_existing: replaceExisting,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Error al confirmar importación');
      }

      const res: ConfirmResult = await response.json();
      setResult(res);
      setStep('done');
      onImportComplete?.();
    } catch (err: any) {
      setError(err.message || 'Error inesperado');
      setStep('preview');
    }
  };

  const toggleProduct = (idx: number) => {
    setProducts(prev => prev.map((p, i) => i === idx ? { ...p, _selected: !p._selected } : p));
  };

  const toggleExpand = (idx: number) => {
    setProducts(prev => prev.map((p, i) => i === idx ? { ...p, _expanded: !p._expanded } : p));
  };

  const updateProduct = (idx: number, field: keyof ParsedProduct, value: any) => {
    setProducts(prev => prev.map((p, i) => i === idx ? { ...p, [field]: value } : p));
  };

  const reset = () => {
    setStep('idle');
    setPreview(null);
    setProducts([]);
    setConditions([]);
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const selectedCount = products.filter(p => p._selected).length;

  // ---- RENDER ----

  if (step === 'done' && result) {
    return (
      <div className="space-y-4">
        <div className="bg-green-50 border border-green-200 rounded-xl p-6">
          <div className="flex items-center space-x-3 mb-4">
            <CheckCircle className="w-8 h-8 text-green-600" />
            <h3 className="text-lg font-semibold text-green-800">Importación completada</h3>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="bg-white rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-green-600">{result.imported}</div>
              <div className="text-gray-600">Productos nuevos</div>
            </div>
            <div className="bg-white rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-blue-600">{result.updated}</div>
              <div className="text-gray-600">Productos actualizados</div>
            </div>
          </div>
          {result.payment_conditions_imported > 0 && (
            <p className="mt-3 text-sm text-green-700">
              ✓ {result.payment_conditions_imported} condiciones de pago importadas
            </p>
          )}
          {result.errors.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-medium text-red-700 mb-1">Errores ({result.errors.length}):</p>
              <ul className="text-sm text-red-600 list-disc list-inside space-y-1">
                {result.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}
        </div>
        <button onClick={reset} className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-900">
          <RotateCcw className="w-4 h-4" />
          <span>Importar otro archivo</span>
        </button>
      </div>
    );
  }

  if (step === 'idle' || step === 'loading') {
    return (
      <div className="space-y-4">
        <div
          onDrop={handleDrop}
          onDragOver={e => e.preventDefault()}
          className="border-2 border-dashed border-gray-300 rounded-xl p-12 text-center hover:border-green-400 transition-colors cursor-pointer"
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={e => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
          />
          {step === 'loading' ? (
            <div className="flex flex-col items-center space-y-3">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-green-600" />
              <p className="text-gray-600">Procesando PDF...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center space-y-3">
              <Upload className="w-12 h-12 text-gray-400" />
              <div>
                <p className="text-gray-700 font-medium">Arrastrá el PDF o hacé clic para seleccionar</p>
                <p className="text-sm text-gray-500 mt-1">LISTADEPRECIOS.pdf · formato Agromaq</p>
              </div>
            </div>
          )}
        </div>
        {error && (
          <div className="flex items-center space-x-2 bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>
    );
  }

  // Preview step
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Eye className="w-5 h-5 text-green-600" />
          <div>
            <h3 className="font-semibold text-gray-900">
              Preview: {preview?.total_products} productos detectados
            </h3>
            <p className="text-sm text-gray-500">
              {preview?.total_with_price} con precio · {selectedCount} seleccionados para importar
            </p>
          </div>
        </div>
        <button onClick={reset} className="text-sm text-gray-500 hover:text-gray-700 flex items-center space-x-1">
          <RotateCcw className="w-3 h-3" />
          <span>Otro archivo</span>
        </button>
      </div>

      {/* Options */}
      <div className="flex items-center space-x-2 bg-yellow-50 border border-yellow-200 rounded-lg p-3">
        <input
          id="replace"
          type="checkbox"
          checked={replaceExisting}
          onChange={e => setReplaceExisting(e.target.checked)}
          className="rounded border-gray-300 text-green-600"
        />
        <label htmlFor="replace" className="text-sm text-yellow-800">
          Eliminar máquinas existentes antes de importar (recomendado para actualización completa)
        </label>
      </div>

      {/* Products table */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
          <span className="text-xs font-medium text-gray-500 uppercase">Productos</span>
          <div className="flex space-x-2 text-xs text-gray-500">
            <button onClick={() => setProducts(p => p.map(x => ({ ...x, _selected: true })))} className="hover:text-green-600">Todos</button>
            <span>·</span>
            <button onClick={() => setProducts(p => p.map(x => ({ ...x, _selected: false })))} className="hover:text-red-600">Ninguno</button>
          </div>
        </div>
        <div className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
          {products.map((product, idx) => (
            <div key={idx} className={`${product._selected ? 'bg-white' : 'bg-gray-50 opacity-60'}`}>
              <div className="flex items-center px-4 py-2 space-x-3">
                <input
                  type="checkbox"
                  checked={product._selected ?? false}
                  onChange={() => toggleProduct(idx)}
                  className="rounded border-gray-300 text-green-600 flex-shrink-0"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono text-gray-400 flex-shrink-0">[{product.code}]</span>
                    <input
                      type="text"
                      value={product.name}
                      onChange={e => updateProduct(idx, 'name', e.target.value)}
                      className="flex-1 text-sm text-gray-900 bg-transparent border-0 focus:ring-0 focus:outline-none min-w-0 truncate"
                      title={product.name}
                    />
                  </div>
                  <div className="flex items-center space-x-3 mt-0.5">
                    <span className="text-xs text-gray-400">{product.category}</span>
                    {product.price !== null ? (
                      <div className="flex items-center space-x-1">
                        <span className="text-xs text-gray-400">USD</span>
                        <input
                          type="number"
                          value={product.price ?? ''}
                          onChange={e => updateProduct(idx, 'price', parseFloat(e.target.value) || null)}
                          className="w-24 text-xs font-medium text-green-700 bg-transparent border-0 focus:ring-0 focus:outline-none"
                        />
                      </div>
                    ) : (
                      <span className="text-xs text-orange-500">Sin precio</span>
                    )}
                    {product.specs.length > 0 && (
                      <span className="text-xs text-gray-400">{product.specs.length} specs</span>
                    )}
                    {product.optionals.length > 0 && (
                      <span className="text-xs text-blue-500">{product.optionals.length} opcionales</span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => toggleExpand(idx)}
                  className="text-gray-400 hover:text-gray-600 flex-shrink-0"
                >
                  {product._expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
              </div>
              {product._expanded && (
                <div className="px-10 pb-3 space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-gray-500">Código</label>
                      <input
                        type="text"
                        value={product.code}
                        onChange={e => updateProduct(idx, 'code', e.target.value)}
                        className="w-full text-xs border border-gray-200 rounded px-2 py-1"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500">Categoría</label>
                      <input
                        type="text"
                        value={product.category}
                        onChange={e => updateProduct(idx, 'category', e.target.value)}
                        className="w-full text-xs border border-gray-200 rounded px-2 py-1"
                      />
                    </div>
                  </div>
                  {product.specs.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Especificaciones ({product.specs.length}):</p>
                      <ul className="text-xs text-gray-600 space-y-0.5 max-h-24 overflow-y-auto">
                        {product.specs.map((s, si) => <li key={si} className="truncate">• {s}</li>)}
                      </ul>
                    </div>
                  )}
                  {product.optionals.length > 0 && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Opcionales:</p>
                      <ul className="text-xs text-gray-600 space-y-0.5">
                        {product.optionals.map((o, oi) => (
                          <li key={oi} className="flex justify-between">
                            <span className="truncate">{o.name}</span>
                            <span className="text-green-700 ml-2 flex-shrink-0">
                              {o.price ? `USD ${o.price.toLocaleString()}` : 'Consultar'}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Payment conditions */}
      {conditions.length > 0 && (
        <div className="border border-gray-200 rounded-xl overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
            <span className="text-xs font-medium text-gray-500 uppercase">Condiciones de Pago detectadas</span>
          </div>
          <div className="divide-y divide-gray-100">
            {conditions.map((c, i) => (
              <div key={i} className="flex items-center justify-between px-4 py-2">
                <span className="text-sm text-gray-700">{c.name}</span>
                {c.discount_percent > 0 && (
                  <span className="text-sm font-medium text-green-700">-{c.discount_percent}%</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-center space-x-2 bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Confirm button */}
      <button
        onClick={handleConfirm}
        disabled={step === 'confirming' || selectedCount === 0}
        className="w-full flex items-center justify-center space-x-2 bg-green-600 text-white py-3 rounded-xl font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {step === 'confirming' ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
            <span>Importando...</span>
          </>
        ) : (
          <>
            <Save className="w-4 h-4" />
            <span>Confirmar importación de {selectedCount} productos</span>
          </>
        )}
      </button>
    </div>
  );
}
