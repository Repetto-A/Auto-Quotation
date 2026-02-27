import { Machine } from '../types';

export type MachineInfo = Machine;

export const findMachineByCode = (code: string, machines: MachineInfo[]): MachineInfo | null => {
  return machines.find((machine) => machine.code === code) || null;
};

export const getMachinesByCategory = (categoryName: string, machines: MachineInfo[]): MachineInfo[] => {
  return machines.filter((machine) => machine.category === categoryName);
};

export const searchMachines = (searchTerm: string, machines: MachineInfo[]): MachineInfo[] => {
  const term = searchTerm.toLowerCase();
  return machines.filter(
    (machine) =>
      machine.name.toLowerCase().includes(term) ||
      machine.category.toLowerCase().includes(term) ||
      machine.code.toLowerCase().includes(term)
  );
};
