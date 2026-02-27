#!/usr/bin/env python3
"""
Script para migrar la base de datos existente y añadir las nuevas columnas de opcionales
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from db import SQLALCHEMY_DATABASE_URL, Base, engine

def migrate_database():
    """Migra la base de datos existente para añadir las nuevas columnas"""
    
    print("🔧 Iniciando migración de base de datos...")
    
    # Crear conexión directa a la base de datos
    db_engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    try:
        with db_engine.connect() as connection:
            # Verificar si las columnas ya existen
            result = connection.execute(text("PRAGMA table_info(quotations)"))
            columns = [row[1] for row in result.fetchall()]
            
            print(f"Columnas existentes en quotations: {columns}")
            
            # Añadir columnas si no existen
            if 'options_data' not in columns:
                print("➕ Añadiendo columna options_data...")
                connection.execute(text("ALTER TABLE quotations ADD COLUMN options_data TEXT"))
                print("✅ Columna options_data añadida")
            
            if 'options_total' not in columns:
                print("➕ Añadiendo columna options_total...")
                connection.execute(text("ALTER TABLE quotations ADD COLUMN options_total FLOAT DEFAULT 0.0"))
                print("✅ Columna options_total añadida")
            
            # Verificar si la tabla options existe
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='options'"))
            if not result.fetchone():
                print("➕ Creando tabla options...")
                connection.execute(text("""
                    CREATE TABLE options (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR UNIQUE,
                        price FLOAT,
                        description TEXT,
                        active BOOLEAN DEFAULT 1
                    )
                """))
                print("✅ Tabla options creada")
                
                # Crear índices
                connection.execute(text("CREATE INDEX ix_options_id ON options (id)"))
                connection.execute(text("CREATE INDEX ix_options_name ON options (name)"))
                print("✅ Índices de options creados")
            
            # Verificar si la tabla machine_option existe
            result = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='machine_option'"))
            if not result.fetchone():
                print("➕ Creando tabla machine_option...")
                connection.execute(text("""
                    CREATE TABLE machine_option (
                        machine_id INTEGER,
                        option_id INTEGER,
                        PRIMARY KEY (machine_id, option_id),
                        FOREIGN KEY (machine_id) REFERENCES machines (id),
                        FOREIGN KEY (option_id) REFERENCES options (id)
                    )
                """))
                print("✅ Tabla machine_option creada")
            
            # Commit los cambios
            connection.commit()
            
            print("\n🎉 Migración completada exitosamente!")
            print("✅ Base de datos actualizada con las nuevas columnas y tablas")
            
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        return False
    
    finally:
        db_engine.dispose()
    
    return True

if __name__ == "__main__":
    migrate_database() 