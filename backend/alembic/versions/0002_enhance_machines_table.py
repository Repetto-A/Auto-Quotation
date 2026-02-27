"""Enhance machines table

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-08 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Verificar si las columnas ya existen antes de añadirlas
    conn = op.get_bind()
    
    # Verificar columnas existentes en machines
    result = conn.execute(sa.text("PRAGMA table_info(machines)"))
    columns = [row[1] for row in result.fetchall()]
    
    # Añadir columnas si no existen
    if 'id' not in columns:
        op.add_column('machines', sa.Column('id', sa.Integer(), nullable=False, primary_key=True))
    
    if 'active' not in columns:
        op.add_column('machines', sa.Column('active', sa.Boolean(), nullable=True, default=True))
    
    # Crear índices si no existen
    try:
        op.create_index('ix_machines_id', 'machines', ['id'], unique=False)
    except:
        pass  # El índice ya existe
    
    try:
        op.create_index('ix_machines_code', 'machines', ['code'], unique=True)
    except:
        pass  # El índice ya existe


def downgrade() -> None:
    # Eliminar índices
    op.drop_index('ix_machines_code', table_name='machines')
    op.drop_index('ix_machines_id', table_name='machines')
    
    # Eliminar columnas (solo si es seguro)
    op.drop_column('machines', 'active') 