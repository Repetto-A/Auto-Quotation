"""Add options tables

Revision ID: 0001
Revises: 
Create Date: 2025-01-08 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear tabla options
    op.create_table('options',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_options_id'), 'options', ['id'], unique=False)
    op.create_index(op.f('ix_options_name'), 'options', ['name'], unique=True)

    # Crear tabla intermedia machine_option
    op.create_table('machine_option',
        sa.Column('machine_id', sa.Integer(), nullable=False),
        sa.Column('option_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
        sa.ForeignKeyConstraint(['option_id'], ['options.id'], ),
        sa.PrimaryKeyConstraint('machine_id', 'option_id')
    )

    # Añadir columnas a quotations
    op.add_column('quotations', sa.Column('options_data', sa.Text(), nullable=True))
    op.add_column('quotations', sa.Column('options_total', sa.Float(), nullable=True))


def downgrade() -> None:
    # Eliminar columnas de quotations
    op.drop_column('quotations', 'options_total')
    op.drop_column('quotations', 'options_data')

    # Eliminar tabla intermedia
    op.drop_table('machine_option')

    # Eliminar tabla options
    op.drop_index(op.f('ix_options_name'), table_name='options')
    op.drop_index(op.f('ix_options_id'), table_name='options')
    op.drop_table('options') 