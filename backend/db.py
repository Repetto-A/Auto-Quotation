import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from timezone_utils import get_arg_tz

# Database setup
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agromaq_enhanced.db")
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
ARG_TZ = get_arg_tz()

# Tabla intermedia para relación muchos-a-muchos entre máquinas y opcionales
machine_option = Table(
    'machine_option',
    Base.metadata,
    Column('machine_id', Integer, ForeignKey('machines.id'), primary_key=True),
    Column('option_id', Integer, ForeignKey('options.id'), primary_key=True)
)

# Enhanced Models
def get_base():
    return Base

class Option(Base):
    __tablename__ = "options"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    price = Column(Float)
    description = Column(Text)
    active = Column(Boolean, default=True)

class Machine(Base):
    __tablename__ = "machines"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    name = Column(String)
    price = Column(Float)
    category = Column(String)
    description = Column(Text)
    active = Column(Boolean, default=True)
    model_name = Column(String, nullable=True)        # ej: "A.V.A. 4000"
    product_title = Column(String, nullable=True)      # ej: "ACOPLADO VOLCADOR TRIVUELCO DE USO RURAL"
    price_currency = Column(String, default="USD")     # "USD" o "ARS"
    options = relationship("Option", secondary=machine_option, backref="machines")
    specs = relationship("MachineSpec", back_populates="machine", order_by="MachineSpec.sort_order")


class MachineSpec(Base):
    __tablename__ = "machine_specs"
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    spec_text = Column(String, nullable=False)
    is_bold = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    machine = relationship("Machine", back_populates="specs")


class PaymentCondition(Base):
    __tablename__ = "payment_conditions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)              # ej: "Contado"
    discount_percent = Column(Float, default=0.0)      # ej: 12.0 para -12%
    description = Column(Text, nullable=True)          # ej: "Pago al contado con transferencia"
    active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    id = Column(Integer, primary_key=True, index=True)
    currency_from = Column(String, default="USD")
    currency_to = Column(String, default="ARS")
    rate = Column(Float, nullable=False)
    source = Column(String, nullable=True)             # "manual" o "BNA"
    fetched_at = Column(DateTime, default=lambda: datetime.now(ARG_TZ))

class Quotation(Base):
    __tablename__ = "quotations"
    id = Column(Integer, primary_key=True, index=True)
    machine_code = Column(String)
    client_cuit = Column(String)
    client_name = Column(String)
    client_phone = Column(String)
    client_email = Column(String, nullable=True)
    client_company = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    client_discount_percent = Column(Float, default=0.0)
    additional_discount_percent = Column(Float, default=0.0)
    total_discount_percent = Column(Float, default=0.0)
    original_price = Column(Float)
    final_price = Column(Float)
    options_data = Column(Text, nullable=True)  # JSON string con snapshot de opcionales
    options_total = Column(Float, default=0.0)  # Suma total de opcionales
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(ARG_TZ))

Base.metadata.create_all(bind=engine) 
