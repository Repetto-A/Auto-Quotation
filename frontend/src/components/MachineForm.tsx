import React, { useState, useEffect } from 'react';
import { getApiUrl, API_CONFIG, getAuthHeaders } from '../config/api';
import { Save, X, Package } from 'lucide-react';
import { Machine, Option } from '../types';

interface MachineFormProps {
  machine?: Machine;
  onSave: (machine: Machine) => void;
  onCancel: () => void;
  isEditing?: boolean;
}

const MachineForm: React.FC<MachineFormProps> = ({ 
  machine, 
  onSave, 
  onCancel, 
  isEditing = false 
}) => {
  const [formData, setFormData] = useState<Machine>({
    id: machine?.id || 0,
    code: machine?.code || '',
    name: machine?.name || '',
    price: machine?.price || 0,
    category: machine?.category || '',
    description: machine?.description || '',
    active: machine?.active ?? true
  });

  const [options, setOptions] = useState<Option[]>([]);
  const [selectedOptionIds, setSelectedOptionIds] = useState<number[]>(
    machine?.options?.map(opt => opt.id) || []
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cargar opcionales disponibles
  useEffect(() => {
    const loadOptions = async () => {
      try {
        const response = await fetch(getApiUrl(API_CONFIG.ENDPOINTS.ADMIN_OPTIONS), {
          headers: getAuthHeaders()
        });
        if (response.ok) {
          const data = await response.json();
          setOptions(data.filter((opt: Option) => opt.active));
        }
      } catch (err) {
        console.error('Error cargando opcionales:', err);
      }
    };

    loadOptions();
  }, []);

  const handleInputChange = (field: keyof Machine, value: string | number | boolean) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleOptionToggle = (optionId: number) => {
    setSelectedOptionIds(prev => 
      prev.includes(optionId)
        ? prev.filter(id => id !== optionId)
        : [...prev, optionId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const machineData = {
        ...formData,
        option_ids: selectedOptionIds
      };

      const url = isEditing 
        ? getApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_MACHINES}/${machine?.id}`)
        : getApiUrl(API_CONFIG.ENDPOINTS.ADMIN_MACHINES);

      const response = await fetch(url, {
        method: isEditing ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(machineData)
      });

      if (response.ok) {
        const savedMachine = await response.json();
        onSave(savedMachine);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Error al guardar la máquina');
      }
    } catch (err) {
      setError('Error de conexión');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900">
              {isEditing ? 'Editar Máquina' : 'Nueva Máquina'}
            </h3>
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Código *
              </label>
              <input
                type="text"
                value={formData.code}
                onChange={(e) => handleInputChange('code', e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="Código de la máquina"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nombre *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="Nombre de la máquina"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Precio *
              </label>
              <input
                type="number"
                value={formData.price}
                onChange={(e) => handleInputChange('price', parseFloat(e.target.value) || 0)}
                required
                min="0"
                step="0.01"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="0.00"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Categoría *
              </label>
              <input
                type="text"
                value={formData.category}
                onChange={(e) => handleInputChange('category', e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="Categoría"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Descripción
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => handleInputChange('description', e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
              placeholder="Descripción de la máquina"
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="active"
              checked={formData.active}
              onChange={(e) => handleInputChange('active', e.target.checked)}
              className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
            />
            <label htmlFor="active" className="ml-2 text-sm text-gray-700">
              Activa
            </label>
          </div>

          {/* Sección de Opcionales */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <Package className="w-4 h-4 inline mr-2" />
              Opcionales Disponibles
            </label>
            <div className="border border-gray-200 rounded-lg p-4 max-h-60 overflow-y-auto">
              {options.length === 0 ? (
                <p className="text-gray-500 text-sm">No hay opcionales disponibles</p>
              ) : (
                <div className="space-y-2">
                  {options.map(option => (
                    <label key={option.id} className="flex items-center space-x-3 p-2 hover:bg-gray-50 rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedOptionIds.includes(option.id)}
                        onChange={() => handleOptionToggle(option.id)}
                        className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500"
                      />
                      <div className="flex-1">
                        <div className="flex justify-between items-center">
                          <span className="font-medium text-gray-900">{option.name}</span>
                          <span className="text-sm font-semibold text-green-600">
                            ${option.price.toLocaleString()}
                          </span>
                        </div>
                        {option.description && (
                          <p className="text-xs text-gray-500 mt-1">{option.description}</p>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              {selectedOptionIds.length} opcional(es) seleccionado(s)
            </p>
          </div>

          <div className="flex space-x-3 pt-4">
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {isLoading ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Guardando...
                </div>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  {isEditing ? 'Actualizar' : 'Crear'}
                </>
              )}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 bg-gray-300 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-400 transition-colors"
            >
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default MachineForm; 
