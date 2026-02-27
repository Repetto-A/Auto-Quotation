#!/usr/bin/env python3
"""
Script para inicializar opcionales de ejemplo en la base de datos
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from db import SessionLocal, Option

def init_options():
    """Inicializa opcionales de ejemplo en la base de datos"""
    db = SessionLocal()
    
    # Verificar si ya existen opcionales
    existing_options = db.query(Option).count()
    if existing_options > 0:
        print(f"Ya existen {existing_options} opcionales en la base de datos. Saltando inicialización.")
        db.close()
        return
    
    # Opcionales de ejemplo
    sample_options = [
        {
            "name": "Sistema de Frenos Hidráulicos",
            "price": 2500.0,
            "description": "Sistema de frenos hidráulicos de alta calidad para mayor seguridad"
        },
        {
            "name": "Luces LED",
            "price": 800.0,
            "description": "Kit completo de luces LED para mejor visibilidad nocturna"
        },
        {
            "name": "Pintura Especial",
            "price": 1200.0,
            "description": "Pintura especial resistente a la corrosión y rayos UV"
        },
        {
            "name": "Sistema de Suspensión Mejorado",
            "price": 3500.0,
            "description": "Sistema de suspensión neumática para mayor confort"
        },
        {
            "name": "GPS Integrado",
            "price": 1500.0,
            "description": "Sistema GPS integrado con pantalla táctil"
        },
        {
            "name": "Cubiertas Premium",
            "price": 2000.0,
            "description": "Cubiertas premium de alta durabilidad"
        },
        {
            "name": "Sistema de Monitoreo",
            "price": 1800.0,
            "description": "Sistema de monitoreo de temperatura y presión"
        },
        {
            "name": "Accesorios de Seguridad",
            "price": 900.0,
            "description": "Kit completo de accesorios de seguridad adicionales"
        }
    ]
    
    # Crear opcionales
    for option_data in sample_options:
        option = Option(
            name=option_data["name"],
            price=option_data["price"],
            description=option_data["description"],
            active=True
        )
        db.add(option)
    
    try:
        db.commit()
        print(f"Se crearon {len(sample_options)} opcionales de ejemplo exitosamente.")
        print("\nOpcionales creados:")
        for option in sample_options:
            print(f"- {option['name']}: ${option['price']:,.2f}")
    except Exception as e:
        db.rollback()
        print(f"Error al crear opcionales: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_options() 