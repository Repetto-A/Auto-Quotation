#!/usr/bin/env python3
"""
Script para ejecutar migraciones de Alembic
"""

import os
import subprocess
import sys

def run_migration():
    """Ejecuta las migraciones de Alembic"""
    try:
        # Verificar si alembic está instalado
        result = subprocess.run([sys.executable, "-m", "alembic", "--version"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("Error: Alembic no está instalado. Instalando...")
            subprocess.run([sys.executable, "-m", "pip", "install", "alembic"], check=True)
        
        # Ejecutar migraciones
        print("Ejecutando migraciones...")
        result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migraciones ejecutadas exitosamente")
            print(result.stdout)
        else:
            print("❌ Error ejecutando migraciones:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def create_initial_migration():
    """Crea la migración inicial si no existe"""
    try:
        # Verificar si ya existe la migración inicial
        if not os.path.exists("alembic/versions/0001_add_options_tables.py"):
            print("Creando migración inicial...")
            subprocess.run([sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", "Add options tables"], 
                          check=True)
            print("✅ Migración inicial creada")
        else:
            print("✅ Migración inicial ya existe")
            
    except Exception as e:
        print(f"❌ Error creando migración: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Iniciando proceso de migraciones...")
    
    # Crear migración inicial si es necesario
    if create_initial_migration():
        # Ejecutar migraciones
        if run_migration():
            print("\n🎉 Proceso completado exitosamente!")
        else:
            print("\n💥 Error en el proceso de migraciones")
            sys.exit(1)
    else:
        print("\n💥 Error creando migración inicial")
        sys.exit(1) 