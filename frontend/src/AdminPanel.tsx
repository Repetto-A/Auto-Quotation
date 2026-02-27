import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getApiUrl, API_CONFIG, getAuthHeaders, removeAuthToken, isAuthenticated as checkAuth } from './config/api';
import { X, Plus, LogOut, Settings, Package, Edit, Truck, FileUp } from 'lucide-react';
import AdminLogin from './components/AdminLogin';
import MachineForm from './components/MachineForm';
import PriceListImport from './components/PriceListImport';
import SettingsPanel from './components/SettingsPanel';
import { Machine, Option } from './types';

function AdminPanel() {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [options, setOptions] = useState<Option[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticatedState] = useState(false);

  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | null;
    message: string;
  }>({ type: null, message: '' });

  // Estados para opcionales
  const [activeTab, setActiveTab] = useState<'machines' | 'options' | 'import' | 'settings'>('machines');
  const [showOptionForm, setShowOptionForm] = useState(false);
  const [editingOption, setEditingOption] = useState<Option | null>(null);
  const [optionForm, setOptionForm] = useState({
    name: '',
    price: '',
    description: ''
  });

  // Estados para máquinas
  const [showMachineForm, setShowMachineForm] = useState(false);
  const [editingMachineData, setEditingMachineData] = useState<Machine | null>(null);


  // Verificar autenticación al cargar
  useEffect(() => {
    const checkAuthStatus = async () => {
      if (checkAuth()) {
        try {
          const response = await fetch(getApiUrl(API_CONFIG.ENDPOINTS.ADMIN_VERIFY), {
            headers: getAuthHeaders()
          });
          if (response.ok) {
            setIsAuthenticatedState(true);
            loadData();
          } else {
            handleLogout();
          }
        } catch (err) {
          handleLogout();
        }
      }
    };

    checkAuthStatus();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [machinesResponse, optionsResponse] = await Promise.all([
        fetch(getApiUrl(API_CONFIG.ENDPOINTS.ADMIN_MACHINES), {
          headers: getAuthHeaders()
        }),
        fetch(getApiUrl(API_CONFIG.ENDPOINTS.ADMIN_OPTIONS), {
          headers: getAuthHeaders()
        })
      ]);

      if (machinesResponse.ok && optionsResponse.ok) {
        const [machinesData, optionsData] = await Promise.all([
          machinesResponse.json(),
          optionsResponse.json()
        ]);
        setMachines(machinesData.machines || machinesData);
        setOptions(optionsData);
      } else {
        setError('Error al cargar los datos');
      }
    } catch (err) {
      setError('Error de conexión');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoginSuccess = () => {
    setIsAuthenticatedState(true);
    loadData();
  };

  const navigate = useNavigate();

  const handleLogout = () => {
    removeAuthToken();
    setIsAuthenticatedState(false);
    setMachines([]);
    setOptions([]);
    navigate('/');
  };



  const handleCreateMachine = (machine: Machine) => {
    setMachines(prev => [machine, ...prev]);
    setShowMachineForm(false);
    setEditingMachineData(null);
    showNotification('Máquina creada exitosamente', 'success');
  };

  const handleUpdateMachine = (updatedMachine: Machine) => {
    setMachines(prev => prev.map(m => m.id === updatedMachine.id ? updatedMachine : m));
    setShowMachineForm(false);
    setEditingMachineData(null);
    showNotification('Máquina actualizada exitosamente', 'success');
  };

  const handleDeleteMachine = async (machineId: number) => {
    if (!confirm('¿Estás seguro de que quieres desactivar esta máquina?')) return;

    try {
      const response = await fetch(getApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_MACHINES}/${machineId}`), {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        setMachines(prev => prev.map(m => 
          m.id === machineId ? { ...m, active: false } : m
        ));
        showNotification('Máquina desactivada exitosamente', 'success');
      } else {
        showNotification('Error al desactivar la máquina', 'error');
      }
    } catch (err) {
      showNotification('Error de conexión', 'error');
    }
  };

  const handleCreateOption = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!optionForm.name || !optionForm.price) return;

    try {
      const response = await fetch(getApiUrl(API_CONFIG.ENDPOINTS.ADMIN_OPTIONS), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          name: optionForm.name,
          price: parseFloat(optionForm.price),
          description: optionForm.description
        })
      });

      if (response.ok) {
        const newOption = await response.json();
        setOptions(prev => [newOption, ...prev]);
        setShowOptionForm(false);
        setOptionForm({ name: '', price: '', description: '' });
        showNotification('Opcional creado exitosamente', 'success');
      } else {
        showNotification('Error al crear el opcional', 'error');
      }
    } catch (err) {
      showNotification('Error de conexión', 'error');
    }
  };

  const handleUpdateOption = async (optionId: number) => {
    if (!optionForm.name || !optionForm.price) return;

    try {
      const response = await fetch(getApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_OPTIONS}/${optionId}`), {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          name: optionForm.name,
          price: parseFloat(optionForm.price),
          description: optionForm.description
        })
      });

      if (response.ok) {
        const updatedOption = await response.json();
        setOptions(prev => prev.map(opt => opt.id === optionId ? updatedOption : opt));
        setShowOptionForm(false);
        setEditingOption(null);
        setOptionForm({ name: '', price: '', description: '' });
        showNotification('Opcional actualizado exitosamente', 'success');
      } else {
        showNotification('Error al actualizar el opcional', 'error');
      }
    } catch (err) {
      showNotification('Error de conexión', 'error');
    }
  };

  const handleDeleteOption = async (optionId: number) => {
    if (!confirm('¿Estás seguro de que quieres desactivar este opcional?')) return;

    try {
      const response = await fetch(getApiUrl(`${API_CONFIG.ENDPOINTS.ADMIN_OPTIONS}/${optionId}`), {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        setOptions(prev => prev.map(opt => 
          opt.id === optionId ? { ...opt, active: false } : opt
        ));
        showNotification('Opcional desactivado exitosamente', 'success');
      } else {
        showNotification('Error al desactivar el opcional', 'error');
      }
    } catch (err) {
      showNotification('Error de conexión', 'error');
    }
  };

  const startEditingOption = (option: Option) => {
    setEditingOption(option);
    setOptionForm({
      name: option.name,
      price: option.price.toString(),
      description: option.description
    });
    setShowOptionForm(true);
  };

  const cancelOptionForm = () => {
    setShowOptionForm(false);
    setEditingOption(null);
    setOptionForm({ name: '', price: '', description: '' });
  };

  const showNotification = (message: string, type: 'success' | 'error') => {
    setNotification({ type, message });
    setTimeout(() => setNotification({ type: null, message: '' }), 3000);
  };

  if (!isAuthenticated) {
    return <AdminLogin onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <Settings className="h-8 w-8 text-green-600" />
              <h1 className="text-2xl font-bold text-gray-900">Panel de Administración</h1>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              >
                <LogOut className="w-4 h-4" />
                Cerrar Sesión
              </button>
            </div>
          </div>
        </div>
      </header>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {notification.type && (
          <div className={`mb-6 p-4 rounded-lg ${
            notification.type === 'success' 
              ? 'bg-green-50 border border-green-200 text-green-800' 
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}>
            {notification.message}
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Pestañas */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('machines')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'machines'
                    ? 'border-green-500 text-green-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Truck className="w-4 h-4 inline mr-2" />
                Máquinas ({machines.length})
              </button>
              <button
                onClick={() => setActiveTab('options')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'options'
                    ? 'border-green-500 text-green-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Package className="w-4 h-4 inline mr-2" />
                Opcionales ({options.length})
              </button>
              <button
                onClick={() => setActiveTab('import')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'import'
                    ? 'border-green-500 text-green-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <FileUp className="w-4 h-4 inline mr-2" />
                Importar Lista
              </button>
              <button
                onClick={() => setActiveTab('settings')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'settings'
                    ? 'border-green-500 text-green-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Settings className="w-4 h-4 inline mr-2" />
                Configuración
              </button>
            </nav>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
          </div>
        )}

        {/* Contenido de Máquinas */}
        {activeTab === 'machines' && !isLoading && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">
                Gestión de Máquinas ({machines.length} máquinas)
            </h2>
              <button
                onClick={() => setShowMachineForm(true)}
                className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>Nueva Máquina</span>
              </button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full table-fixed divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="w-[16%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Código
                  </th>
                  <th className="w-[24%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Nombre
                  </th>
                  <th className="w-[16%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Categoría
                  </th>
                  <th className="w-[12%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Precio
                    </th>
                    <th className="w-[10%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Estado
                    </th>
                    <th className="w-[14%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Opcionales
                  </th>
                  <th className="w-[8%] px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {machines.map((machine) => (
                    <tr key={machine.id}>
                    <td className="px-3 py-3 text-sm font-medium text-gray-900">
                      <div className="truncate" title={machine.code}>{machine.code}</div>
                    </td>
                    <td className="px-3 py-3 text-sm text-gray-900">
                      <div className="truncate" title={machine.name}>{machine.name}</div>
                    </td>
                    <td className="px-3 py-3 text-sm text-gray-500">
                      <div className="truncate" title={machine.category}>{machine.category}</div>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap text-sm text-gray-900">
                      ${machine.price.toLocaleString()}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap text-sm text-gray-500">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          machine.active 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {machine.active ? 'Activa' : 'Inactiva'}
                        </span>
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-gray-500">
                        {machine.options?.length || 0} opcionales
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => {
                              setEditingMachineData(machine);
                              setShowMachineForm(true);
                            }}
                            className="text-blue-600 hover:text-blue-900"
                            title="Editar"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteMachine(machine.id)}
                            className="text-red-600 hover:text-red-900"
                            title="Desactivar"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Configuración: tipo de cambio + condiciones de pago */}
        {activeTab === 'settings' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Configuración</h2>
              <p className="text-sm text-gray-500 mt-1">Tipo de cambio y condiciones de pago para los PDFs.</p>
            </div>
            <SettingsPanel />
          </div>
        )}

        {/* Contenido de Importar Lista */}
        {activeTab === 'import' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Importar Lista de Precios</h2>
              <p className="text-sm text-gray-500 mt-1">
                Subí el PDF de lista de precios Agromaq para actualizar la base de datos de máquinas.
              </p>
            </div>
            <PriceListImport onImportComplete={loadData} />
          </div>
        )}

        {/* Contenido de Opcionales */}
        {activeTab === 'options' && !isLoading && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-lg font-semibold text-gray-900">
                Gestión de Opcionales ({options.length} opcionales)
              </h2>
              <button
                onClick={() => setShowOptionForm(true)}
                className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
              >
                + Nuevo Opcional
              </button>
            </div>
            
            <div className="overflow-x-auto">
              <table className="min-w-full table-fixed divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="w-[30%] px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Nombre
                    </th>
                    <th className="w-[15%] px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Precio
                    </th>
                    <th className="w-[35%] px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Descripción
                    </th>
                    <th className="w-[10%] px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Estado
                    </th>
                    <th className="w-[10%] px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {options.map((option) => (
                    <tr key={option.id}>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        <div className="truncate" title={option.name}>{option.name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        ${option.price.toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        <div className="truncate" title={option.description}>{option.description}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          option.active 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {option.active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="flex items-center space-x-2">
                        <button
                            onClick={() => startEditingOption(option)}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                          <button
                            onClick={() => handleDeleteOption(option.id)}
                            className="text-red-600 hover:text-red-900"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        )}

        {/* Modal para crear/editar opcional */}
        {showOptionForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
              <div className="p-6 border-b border-gray-200">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {editingOption ? 'Editar Opcional' : 'Nuevo Opcional'}
                  </h3>
                  <button
                    onClick={cancelOptionForm}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    ✕
                  </button>
                </div>
              </div>
              <form onSubmit={editingOption ? (e) => { e.preventDefault(); handleUpdateOption(editingOption.id); } : handleCreateOption} className="p-6 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Nombre
                  </label>
                  <input
                    type="text"
                    value={optionForm.name}
                    onChange={(e) => setOptionForm(prev => ({ ...prev, name: e.target.value }))}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="Nombre del opcional"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Precio
                  </label>
                  <input
                    type="number"
                    value={optionForm.price}
                    onChange={(e) => setOptionForm(prev => ({ ...prev, price: e.target.value }))}
                    required
                    min="0"
                    step="0.01"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Descripción
                  </label>
                  <textarea
                    value={optionForm.description}
                    onChange={(e) => setOptionForm(prev => ({ ...prev, description: e.target.value }))}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    placeholder="Descripción del opcional"
                  />
                </div>
                <div className="flex space-x-3 pt-4">
                  <button
                    type="submit"
                    className="flex-1 bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors"
                  >
                    {editingOption ? 'Actualizar' : 'Crear'}
                  </button>
                  <button
                    type="button"
                    onClick={cancelOptionForm}
                    className="flex-1 bg-gray-300 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-400 transition-colors"
                  >
                    Cancelar
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal para crear/editar máquina */}
        {showMachineForm && (
          <MachineForm
            machine={editingMachineData || undefined}
            onSave={editingMachineData ? handleUpdateMachine : handleCreateMachine}
            onCancel={() => {
              setShowMachineForm(false);
              setEditingMachineData(null);
            }}
            isEditing={!!editingMachineData}
          />
        )}
      </div>
    </div>
  );
}

export default AdminPanel; 
