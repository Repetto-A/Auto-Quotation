import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Search, Check, Layers3, Tag } from 'lucide-react';
import { MachineInfo } from '../utils/machineUtils';

interface MachinerySelectorProps {
  selectedMachine: string;
  onMachineSelect: (machine: string) => void;
  machines: MachineInfo[];
  isLoadingMachines?: boolean;
  isMultipleSelection?: boolean;
  isMachineSelected?: (machineCode: string) => boolean;
}

const MachinerySelector: React.FC<MachinerySelectorProps> = ({
  selectedMachine,
  onMachineSelect,
  machines,
  isLoadingMachines = false,
  isMultipleSelection = false,
  isMachineSelected
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});

  const formatMachinePrice = (machine: MachineInfo) => {
    const symbol = machine.price_currency === 'ARS' ? '$' : 'U$S';
    return `${symbol} ${machine.price.toLocaleString('es-AR')}`;
  };

  const filteredMachines = searchTerm
    ? machines.filter(
        (machine) =>
          machine.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          machine.category.toLowerCase().includes(searchTerm.toLowerCase()) ||
          machine.code.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : machines;

  const categories = React.useMemo<Record<string, MachineInfo[]>>(() => {
    const cats: Record<string, MachineInfo[]> = {};
    filteredMachines.forEach((machine) => {
      if (!cats[machine.category]) {
        cats[machine.category] = [];
      }
      cats[machine.category].push(machine);
    });
    return cats;
  }, [filteredMachines]);

  useEffect(() => {
    if (searchTerm) {
      const expanded: Record<string, boolean> = {};
      Object.keys(categories).forEach((cat) => {
        expanded[cat] = true;
      });
      setExpandedCategories(expanded);
    } else {
      setExpandedCategories({});
    }
  }, [searchTerm, categories]);

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  const handleMachineClick = (machineCode: string) => {
    if (isMultipleSelection) {
      onMachineSelect(machineCode);
      return;
    }
    if (selectedMachine !== machineCode) {
      onMachineSelect(machineCode);
    }
  };

  const isSelected = (machineCode: string) => {
    if (isMultipleSelection && isMachineSelected) {
      return isMachineSelected(machineCode);
    }
    return selectedMachine === machineCode;
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-gradient-to-b from-gray-50 to-white p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center">
            <Layers3 className="w-4 h-4 text-green-700" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-900">Catalogo de Maquinas</h4>
            <p className="text-xs text-gray-500">{filteredMachines.length} resultados</p>
          </div>
        </div>
      </div>

      {isLoadingMachines && (
        <div className="text-center py-3">
          <div className="inline-flex items-center space-x-2 text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span className="text-sm">Cargando maquinaria...</span>
          </div>
        </div>
      )}

      <div className="relative w-full">
        <div className="relative flex rounded-xl shadow-sm w-full">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-gray-400" aria-hidden="true" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-10 py-2.5 border border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-green-500 focus:border-transparent sm:text-sm"
            placeholder="Buscar por nombre, codigo o categoria..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none"
            >
              <span className="sr-only">Limpiar busqueda</span>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {Object.entries(categories).map(([category, categoryMachines]) => {
          const isExpanded = expandedCategories[category];
          return (
            <div key={category} className="border border-gray-200 rounded-xl overflow-hidden bg-white">
              <button
                type="button"
                onClick={() => toggleCategory(category)}
                className="w-full flex items-center justify-between p-3 text-left hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Tag className="w-4 h-4 text-gray-400" />
                  <h3 className="font-medium text-gray-900">{category}</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200">
                    {categoryMachines.length}
                  </span>
                </div>
                {isExpanded ? (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                )}
              </button>
              {isExpanded && (
                <div className="border-t border-gray-100 p-2 bg-gray-50/50">
                  <div className="space-y-2">
                    {categoryMachines.map((machine) => {
                      const selected = isSelected(machine.code);
                      return (
                        <button
                          key={machine.code}
                          type="button"
                          onClick={() => handleMachineClick(machine.code)}
                          className={`w-full text-left p-3 rounded-lg transition-all border ${
                            selected
                              ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-300 shadow-sm'
                              : 'bg-white border-gray-200 hover:border-green-200 hover:shadow-sm'
                          }`}
                        >
                          <div className="flex justify-between items-start gap-3">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2">
                                {isMultipleSelection && (
                                  <div
                                    className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                                      selected ? 'bg-green-500 border-green-500' : 'border-gray-300 bg-white'
                                    }`}
                                  >
                                    {selected && <Check className="w-3 h-3 text-white" />}
                                  </div>
                                )}
                                <div>
                                  <p className={`font-medium ${selected ? 'text-green-900' : 'text-gray-900'}`}>
                                    {machine.name}
                                  </p>
                                  <p className="text-xs text-gray-500 mt-1">Codigo: {machine.code}</p>
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                              <p className={`font-bold ${selected ? 'text-green-700' : 'text-gray-900'}`}>
                                {formatMachinePrice(machine)}
                              </p>
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {filteredMachines.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No se encontraron productos que coincidan con "{searchTerm}"</p>
        </div>
      )}
    </div>
  );
};

export default MachinerySelector;
