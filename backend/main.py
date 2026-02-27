import sys
import os
sys.path.append(os.path.dirname(__file__))
from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import jwt
import os
import secrets
from typing import List, Optional, Dict
from pdf_generator import PDFGenerator
import json
from db import engine, SessionLocal, Base, Machine, Quotation, Option, MachineSpec, PaymentCondition, ExchangeRate
from sqlalchemy.orm import joinedload
from afip_ws import afip_ws, AFIPPersonaData
from dotenv import load_dotenv
load_dotenv()

# ConfiguraciÃ³n JWT
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 15

# Pydantic models
class OptionCreate(BaseModel):
    name: str
    price: float
    description: str

class OptionUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    active: Optional[bool] = None

class MachineCreate(BaseModel):
    code: str
    name: str
    price: float
    category: str
    description: str
    option_ids: Optional[List[int]] = []

class MachineUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None
    option_ids: Optional[List[int]] = None

# Nuevos modelos para cotizaciones mÃºltiples
class QuotationOption(BaseModel):
    id: int
    quantity: int = Field(ge=1, description="Cantidad del opcional")
    unit_price: float = Field(ge=0, description="Precio unitario del opcional")

class QuotationItem(BaseModel):
    machine_code: str = Field(..., description="CÃ³digo de la mÃ¡quina")
    quantity: int = Field(ge=1, description="Cantidad de mÃ¡quinas")
    unit_price: float = Field(ge=0, description="Precio unitario de la mÃ¡quina")
    discount_percent: float = Field(ge=0, le=100, description="Porcentaje de descuento aplicado")
    options: List[QuotationOption] = Field(default_factory=list, description="Lista de opcionales")

class QuotationCreateMultiple(BaseModel):
    items: List[QuotationItem] = Field(..., min_items=1, description="Lista de items de la cotizaciÃ³n")
    client_cuit: str = Field(..., description="CUIT del cliente")
    client_name: str = Field(..., description="Nombre del cliente")
    client_phone: Optional[str] = Field(None, description="TelÃ©fono del cliente")
    client_email: Optional[str] = None
    client_company: Optional[str] = None
    client_address: Optional[str] = None
    notes: Optional[str] = None
    client_discount_percent: float = Field(default=0.0, ge=0, le=100)
    additional_discount_percent: float = Field(default=0.0, ge=0, le=100)

# Modelo legacy para compatibilidad
class QuotationCreate(BaseModel):
    machineCode: str
    clientCuit: str
    clientName: str
    clientPhone: Optional[str] = None
    clientEmail: Optional[str] = None
    clientCompany: Optional[str] = None
    notes: Optional[str] = None
    clientDiscountPercent: float = 0.0  # Descuento por tipo de cliente
    additionalDiscountPercent: float = 0.0  # Descuento adicional
    option_ids: Optional[List[int]] = []  # Opcionales globales
    options_by_machine: Optional[Dict[str, List[int]]] = {}  # Opcionales por mÃ¡quina

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

# FastAPI app
app = FastAPI(title="Cotizador Agromaq API", version="1.0.0")


def serialize_machine(machine: Machine) -> dict:
    """Serialize machine with explicit options payload for admin/frontend."""
    return {
        "id": machine.id,
        "code": machine.code,
        "name": machine.name,
        "price": machine.price,
        "category": machine.category,
        "description": machine.description,
        "active": machine.active,
        "model_name": machine.model_name,
        "product_title": machine.product_title,
        "price_currency": machine.price_currency,
        "options": [
            {
                "id": opt.id,
                "name": opt.name,
                "price": opt.price,
                "description": opt.description,
                "active": opt.active,
            }
            for opt in machine.options
        ],
    }

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBasic()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# JWT Token functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token invÃ¡lido")

# Authentication dependency
def get_current_admin(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    # Verificar que es un admin
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    return payload

# Admin authentication endpoints
@app.post("/admin/login", response_model=AdminToken)
def admin_login(login_data: AdminLogin):
    """Login para administradores"""
    admin_username = os.getenv("ADMIN_USER", "Torocojo")
    admin_password = os.getenv("ADMIN_PASS", "ar2810AR")
    
    if login_data.username == admin_username and login_data.password == admin_password:
        access_token_expires = timedelta(minutes=JWT_EXPIRATION_MINUTES)
        access_token = create_access_token(
            data={"sub": login_data.username, "role": "admin"},
            expires_delta=access_token_expires
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": JWT_EXPIRATION_MINUTES * 60
        }
    else:
        raise HTTPException(status_code=401, detail="Credenciales invÃ¡lidas")

@app.post("/admin/logout")
def admin_logout():
    """Logout para administradores (el token se invalida en el frontend)"""
    return {"message": "Logout exitoso"}

@app.get("/admin/verify")
def verify_admin_token(admin: dict = Depends(get_current_admin)):
    """Verificar si el token de admin es vÃ¡lido"""
    return {"valid": True, "user": admin.get("sub")}

# Initialize components
pdf_generator = PDFGenerator()
# Telegram bot desactivado - pendiente migracion a WhatsApp

# Machinery catalog
MACHINERY_CATALOG = [
    {
        "categoria": "Acoplados rurales",
        "productos": [
            "Acoplado rural playo",
            "Acoplado rural vaquero desmontable",
            "Acoplado rural vaquero desmontable 2",
            "Acoplado rural vaquero fijo",
            "Acoplado totalmente desmontable",
            "Acoplado volcador manual o hidrÃ¡ulico",
            "Acoplado volcador trivuelo de uso rural"
        ]
    },
    {
        "categoria": "Acoplados tanque",
        "productos": [
            "Acoplado tanque 3000 Lts.",
            "Acoplado tanque de 1500 Lts.",
            "Acoplado tanque de plÃ¡stico 12.000 Lts.",
            "Acoplado tanque de plÃ¡stico 1500 Lts.",
            "Acoplado tanque de plÃ¡stico 3500 Lts.",
            "Acoplado tanque de plÃ¡stico 7000 Lts.",
            "Acoplado tanques rurales"
        ]
    },
    {
        "categoria": "Tolvas",
        "productos": [
            "Acoplado tolva cerealero 4 TT.",
            "Acoplado tolva cerealero 8 TT.",
            "Acoplado Tolva para semillas y fertilizantes de uso rural",
            "Acoplado Tolva Para Semillas Y Fertilizantes De Uso Rural",
            "Acoplado tolva para semillas y fertilizantes modelo A.T.F. 10",
            "Acoplado tolva para semillas y fertilizantes modelo A.T.F. 14",
            "Acoplado tolva para semillas y fertilizantes Modelo A.T.F. 24",
            "Acoplados tolvas para semillas y fertilizantes Modelo A.T.F. 12"
        ]
    },
    {
        "categoria": "Cargadores y elevadores",
        "productos": [
            "Cargador y transportador de rollos hidrÃ¡ulico T.R.A. 6000",
            "Elevador de rollos",
            "GrÃºa giratoria hidrÃ¡ulica multipropÃ³sito de uso rural"
        ]
    },
]

@app.on_event("startup")
async def startup_event():
    # Initialize machinery catalog in database
    db = SessionLocal()
    if db.query(Machine).count() == 0:
        # Leer el catÃ¡logo desde el backup JSON
        backup_path = os.path.join(os.path.dirname(__file__), "data_machinery_backup.json")
        with open(backup_path, "r", encoding="utf-8") as f:
            MACHINERY_CATALOG = json.load(f)
        id_counter = 1
        for category in MACHINERY_CATALOG:
            for producto in category["productos"]:
                code = f"{category['categoria'][:3].upper()}{str(id_counter).zfill(3)}"
                machine = Machine(
                    code=code,
                    name=producto,
                    price=float(10000 + (id_counter * 1000)),  # Sample pricing
                    category=category["categoria"],
                    description=f"DescripciÃ³n de {producto}",
                    active=True
                )
                db.add(machine)
                id_counter += 1
        db.commit()
    db.close()

@app.get("/")
def read_root():
    return {"message": "Agromaq Enhanced Quotation System API", "version": "2.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/machines")
def get_machines(db: Session = Depends(get_db)):
    return db.query(Machine).filter(Machine.active == True).all()

@app.get("/admin/machines")
def get_machines_admin(
    skip: int = 0, 
    limit: int = 100, 
    active: Optional[bool] = None,
    category: Optional[str] = None,
    admin: dict = Depends(get_current_admin), 
    db: Session = Depends(get_db)
):
    """Obtener todas las mÃ¡quinas con filtros y paginaciÃ³n - solo admin"""
    query = db.query(Machine)
    
    # Aplicar filtros
    if active is not None:
        query = query.filter(Machine.active == active)
    if category:
        query = query.filter(Machine.category == category)
    
    # Aplicar paginaciÃ³n
    total = query.count()
    machines = query.options(joinedload(Machine.options)).offset(skip).limit(limit).all()
    
    return {
        "machines": [serialize_machine(machine) for machine in machines],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@app.get("/machines/catalog")
def get_machinery_catalog():
    return MACHINERY_CATALOG

@app.get("/machines/{machine_code}")
def get_machine_by_code(machine_code: str, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.code == machine_code, Machine.active == True).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    return machine

@app.get("/admin/machines/{machine_id}")
def get_machine_admin(machine_id: int, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Obtener una mÃ¡quina especÃ­fica con sus opcionales - solo admin"""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Incluir opcionales asociados
    return serialize_machine(machine)

@app.put("/machines/{machine_code}")
def update_machine_price(machine_code: str, machine_update: MachineUpdate, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.code == machine_code).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    machine.price = machine_update.price
    db.commit()
    db.refresh(machine)
    return machine

@app.post("/generate-quote")
async def generate_quote(quotation: QuotationCreate, db: Session = Depends(get_db)):
    print(f"Received quotation data: {quotation}")
    print(f"Machine code: {quotation.machineCode}")
    print(f"Option IDs: {quotation.option_ids}")
    print(f"Options by machine: {quotation.options_by_machine}")
    
    # Get machine details (con specs para el PDF)
    machine = db.query(Machine).options(
        joinedload(Machine.specs)
    ).filter(Machine.code == quotation.machineCode, Machine.active == True).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Procesar opcionales
    selected_options = []
    options_total = 0.0
    
    # Opcionales globales (aplicados a todas las mÃ¡quinas)
    if quotation.option_ids:
        global_options = db.query(Option).filter(
            Option.id.in_(quotation.option_ids), 
            Option.active == True
        ).all()
        for option in global_options:
            selected_options.append({
                "option_id": option.id,
                "name": option.name,
                "price": option.price
            })
            options_total += option.price
    
    # Opcionales especÃ­ficos por mÃ¡quina
    print(f"Processing machine-specific options for {quotation.machineCode}")
    print(f"Available options_by_machine: {quotation.options_by_machine}")
    if quotation.options_by_machine and quotation.machineCode in quotation.options_by_machine:
        machine_option_ids = quotation.options_by_machine[quotation.machineCode]
        print(f"Machine option IDs: {machine_option_ids}")
        machine_specific_options = db.query(Option).filter(
            Option.id.in_(machine_option_ids), 
            Option.active == True
        ).all()
        print(f"Found machine-specific options: {[opt.name for opt in machine_specific_options]}")
        for option in machine_specific_options:
            selected_options.append({
                "option_id": option.id,
                "name": option.name,
                "price": option.price
            })
            options_total += option.price
    else:
        print("No machine-specific options found")
    
    # Calcular descuentos y precio final
    original_price = machine.price + options_total
    client_discount = quotation.clientDiscountPercent or 0.0
    additional_discount = quotation.additionalDiscountPercent or 0.0
    
    # Calcular descuento total (no acumulativo, sino combinado)
    total_discount_percent = client_discount + additional_discount
    if total_discount_percent > 100:
        total_discount_percent = 100  # MÃ¡ximo 100%
    
    # Calcular precio final
    final_price = original_price * (1 - total_discount_percent / 100)
    
    # Save quotation to database
    db_quotation = Quotation(
        machine_code=quotation.machineCode,
        client_cuit=quotation.clientCuit,
        client_name=quotation.clientName,
        client_phone=quotation.clientPhone,
        client_email=quotation.clientEmail,
        client_company=quotation.clientCompany,
        notes=quotation.notes,
        client_discount_percent=client_discount,
        additional_discount_percent=additional_discount,
        total_discount_percent=total_discount_percent,
        original_price=original_price,
        final_price=final_price,
        options_data=json.dumps(selected_options),
        options_total=options_total
    )
    db.add(db_quotation)
    db.commit()
    
    # Generate PDF
    pdf_path = await pdf_generator.generate_quotation_pdf(machine, quotation, final_price, selected_options)
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"cotizacion-{quotation.clientName.replace(' ', '-')}-{quotation.machineCode}.pdf"
    )

@app.post("/quotations")
async def create_quotation_multiple(quotation: QuotationCreateMultiple, db: Session = Depends(get_db)):
    """Crear cotizaciÃ³n con mÃºltiples items"""
    print(f"Received multiple quotation data: {quotation}")
    
    # Validar que todas las mÃ¡quinas existen
    machine_codes = [item.machine_code for item in quotation.items]
    machines = db.query(Machine).options(
        joinedload(Machine.specs)
    ).filter(
        Machine.code.in_(machine_codes),
        Machine.active == True
    ).all()
    
    if len(machines) != len(machine_codes):
        found_codes = [m.code for m in machines]
        missing_codes = [code for code in machine_codes if code not in found_codes]
        raise HTTPException(status_code=404, detail=f"MÃ¡quinas no encontradas: {missing_codes}")
    
    # Crear diccionario de mÃ¡quinas para acceso rÃ¡pido
    machines_dict = {m.code: m for m in machines}
    
    # Procesar cada item
    all_selected_options = []
    total_machines_subtotal = 0.0
    total_options_subtotal = 0.0
    
    for item in quotation.items:
        machine = machines_dict[item.machine_code]
        
        # Calcular subtotal de la mÃ¡quina
        machine_subtotal = machine.price * item.quantity
        total_machines_subtotal += machine_subtotal
        
        # Procesar opcionales del item
        item_options = []
        for option_data in item.options:
            option = db.query(Option).filter(
                Option.id == option_data.id, 
                Option.active == True
            ).first()
            
            if not option:
                raise HTTPException(status_code=404, detail=f"Opcional {option_data.id} no encontrado")
            
            option_subtotal = option_data.unit_price * option_data.quantity
            total_options_subtotal += option_subtotal
            
            item_options.append({
                "option_id": option.id,
                "name": option.name,
                "price": option_data.unit_price,
                "quantity": option_data.quantity,
                "subtotal": option_subtotal
            })
        
        all_selected_options.extend(item_options)
    
    # Calcular descuentos
    subtotal_before_discounts = total_machines_subtotal + total_options_subtotal
    client_discount = quotation.client_discount_percent or 0.0
    additional_discount = quotation.additional_discount_percent or 0.0
    
    # Calcular descuento total (no acumulativo, sino combinado)
    total_discount_percent = client_discount + additional_discount
    if total_discount_percent > 100:
        total_discount_percent = 100
    
    # Calcular precio final
    final_price = subtotal_before_discounts * (1 - total_discount_percent / 100)
    
    # Crear cotizaciÃ³n en la base de datos
    db_quotation = Quotation(
        machine_code="MULTIPLE",  # Indicador de cotizaciÃ³n mÃºltiple
        client_cuit=quotation.client_cuit,
        client_name=quotation.client_name,
        client_phone=quotation.client_phone,
        client_email=quotation.client_email,
        client_company=quotation.client_company,
        notes=quotation.notes,
        client_discount_percent=client_discount,
        additional_discount_percent=additional_discount,
        total_discount_percent=total_discount_percent,
        original_price=subtotal_before_discounts,
        final_price=final_price,
        options_data=json.dumps({
            "items": [
                {
                    "machine_code": item.machine_code,
                    "machine_name": machines_dict[item.machine_code].name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "discount_percent": item.discount_percent,
                    "machine_subtotal": machines_dict[item.machine_code].price * item.quantity,
                    "options": [
                        {
                            "id": opt["option_id"],
                            "name": opt["name"],
                            "price": opt["price"],
                            "quantity": opt["quantity"],
                            "subtotal": opt["subtotal"]
                        } for opt in all_selected_options if any(
                            machines_dict[item.machine_code].options and 
                            opt["option_id"] == option.id for option in machines_dict[item.machine_code].options
                        )
                    ]
                } for item in quotation.items
            ],
            "totals": {
                "machines_subtotal": total_machines_subtotal,
                "options_subtotal": total_options_subtotal,
                "subtotal_before_discounts": subtotal_before_discounts,
                "total_discount_percent": total_discount_percent,
                "final_price": final_price
            }
        }),
        options_total=total_options_subtotal
    )
    
    db.add(db_quotation)
    db.commit()
    db.refresh(db_quotation)
    
    # Construir items para el generador de PDF
    payment_conditions = db.query(PaymentCondition).filter(
        PaymentCondition.active == True
    ).order_by(PaymentCondition.sort_order).all()

    pdf_items = []
    for item in quotation.items:
        machine = machines_dict[item.machine_code]
        item_final_price = item.unit_price * item.quantity * (1 - item.discount_percent / 100)
        # Obtener los Option objects para este item
        opt_ids = [opt_data.id for opt_data in item.options]
        opts = db.query(Option).filter(Option.id.in_(opt_ids)).all() if opt_ids else []
        pdf_items.append({
            "machine": machine,
            "final_price": item_final_price,
            "selected_options": opts,
        })

    # Generar PDF
    pdf_path = await pdf_generator.generate_multiple_quotation_pdf(
        pdf_items,
        quotation,
        payment_conditions,
    )
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"cotizacion-multiple-{quotation.client_name.replace(' ', '-')}.pdf"
    )

@app.get("/quotations")
def get_quotations(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Quotation).order_by(Quotation.created_at.desc()).all()

@app.get("/quotations/stats")
def get_quotation_stats(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    total_quotations = db.query(Quotation).count()
    total_with_discount = db.query(Quotation).filter(Quotation.total_discount_percent > 0).count()

    return {
        "total_quotations": total_quotations,
        "quotations_with_discount": total_with_discount,
        "discount_percentage": (total_with_discount / total_quotations * 100) if total_quotations > 0 else 0
    }

# Endpoints para opcionales
@app.get("/options")
def get_options(db: Session = Depends(get_db)):
    """Obtener todos los opcionales activos"""
    return db.query(Option).filter(Option.active == True).all()

@app.get("/admin/options")
def get_options_admin(admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Obtener todos los opcionales (incluyendo inactivos) - solo admin"""
    return db.query(Option).all()

@app.post("/admin/options")
def create_option(option: OptionCreate, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Crear un nuevo opcional - solo admin"""
    db_option = Option(
        name=option.name,
        price=option.price,
        description=option.description,
        active=True
    )
    db.add(db_option)
    db.commit()
    db.refresh(db_option)
    return db_option

@app.put("/admin/options/{option_id}")
def update_option(option_id: int, option_update: OptionUpdate, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Actualizar un opcional - solo admin"""
    db_option = db.query(Option).filter(Option.id == option_id).first()
    if not db_option:
        raise HTTPException(status_code=404, detail="Option not found")
    
    if option_update.name is not None:
        db_option.name = option_update.name
    if option_update.price is not None:
        db_option.price = option_update.price
    if option_update.description is not None:
        db_option.description = option_update.description
    if option_update.active is not None:
        db_option.active = option_update.active
    
    db.commit()
    db.refresh(db_option)
    return db_option

@app.delete("/admin/options/{option_id}")
def deactivate_option(option_id: int, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Desactivar un opcional (no borrar fÃ­sicamente) - solo admin"""
    db_option = db.query(Option).filter(Option.id == option_id).first()
    if not db_option:
        raise HTTPException(status_code=404, detail="Option not found")
    
    db_option.active = False
    db.commit()
    return {"message": "Option deactivated successfully"}

# Endpoints CRUD completos para mÃ¡quinas
@app.post("/admin/machines")
def create_machine(machine: MachineCreate, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Crear una nueva mÃ¡quina - solo admin"""
    # Verificar si el cÃ³digo ya existe
    existing_machine = db.query(Machine).filter(Machine.code == machine.code).first()
    if existing_machine:
        raise HTTPException(status_code=400, detail="Machine code already exists")
    
    # Crear la mÃ¡quina
    db_machine = Machine(
        code=machine.code,
        name=machine.name,
        price=machine.price,
        category=machine.category,
        description=machine.description,
        active=True
    )
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)
    
    # Asignar opcionales si se proporcionan
    if machine.option_ids:
        options = db.query(Option).filter(
            Option.id.in_(machine.option_ids), 
            Option.active == True
        ).all()
        db_machine.options = options
        db.commit()
        db.refresh(db_machine)
    
    db.refresh(db_machine)
    return serialize_machine(db_machine)

@app.put("/admin/machines/{machine_id}")
def update_machine(machine_id: int, machine_update: MachineUpdate, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Actualizar una mÃ¡quina - solo admin"""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Verificar si el cÃ³digo ya existe (si se estÃ¡ cambiando)
    if machine_update.code and machine_update.code != db_machine.code:
        existing_machine = db.query(Machine).filter(Machine.code == machine_update.code).first()
        if existing_machine:
            raise HTTPException(status_code=400, detail="Machine code already exists")
    
    # Actualizar campos
    if machine_update.code is not None:
        db_machine.code = machine_update.code
    if machine_update.name is not None:
        db_machine.name = machine_update.name
    if machine_update.price is not None:
        db_machine.price = machine_update.price
    if machine_update.category is not None:
        db_machine.category = machine_update.category
    if machine_update.description is not None:
        db_machine.description = machine_update.description
    if machine_update.active is not None:
        db_machine.active = machine_update.active
    
    # Actualizar opcionales si se proporcionan
    if machine_update.option_ids is not None:
        options = db.query(Option).filter(
            Option.id.in_(machine_update.option_ids), 
            Option.active == True
        ).all()
        db_machine.options = options
    
    db.commit()
    db.refresh(db_machine)
    db.refresh(db_machine)
    return serialize_machine(db_machine)

@app.delete("/admin/machines/{machine_id}")
def deactivate_machine(machine_id: int, admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Desactivar una mÃ¡quina (no borrar fÃ­sicamente) - solo admin"""
    db_machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not db_machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    db_machine.active = False
    db.commit()
    return {"message": "Machine deactivated successfully"}

@app.get("/machines/{machine_code}/options")
def get_machine_options(machine_code: str, db: Session = Depends(get_db)):
    """Obtener opcionales de una mÃ¡quina especÃ­fica"""
    machine = db.query(Machine).filter(Machine.code == machine_code, Machine.active == True).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    return machine.options

@app.put("/admin/machines/{machine_code}/options")
def update_machine_options(machine_code: str, option_ids: List[int], admin: dict = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Actualizar opcionales de una mÃ¡quina - solo admin"""
    machine = db.query(Machine).filter(Machine.code == machine_code).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    
    # Obtener los opcionales por IDs
    options = db.query(Option).filter(Option.id.in_(option_ids), Option.active == True).all()
    if len(options) != len(option_ids):
        raise HTTPException(status_code=400, detail="Some option IDs are invalid or inactive")
    
    machine.options = options
    db.commit()
    db.refresh(machine)
    return machine

# ---------------------------------------------------------------------------
# Tipo de cambio USD/ARS
# ---------------------------------------------------------------------------

@app.get("/admin/exchange-rate")
def get_exchange_rate(db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    """Retorna el tipo de cambio vigente (Ãºltimo guardado en DB)."""
    rate = db.query(ExchangeRate).order_by(ExchangeRate.fetched_at.desc()).first()
    if not rate:
        return {"rate": None, "source": None, "fetched_at": None}
    return {
        "id": rate.id,
        "rate": rate.rate,
        "source": rate.source,
        "currency_from": rate.currency_from,
        "currency_to": rate.currency_to,
        "fetched_at": rate.fetched_at.isoformat() if rate.fetched_at else None,
    }


@app.post("/admin/exchange-rate/manual")
def set_exchange_rate_manual(
    payload: dict,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Guarda manualmente el tipo de cambio USD/ARS."""
    rate_value = payload.get("rate")
    if not rate_value or float(rate_value) <= 0:
        raise HTTPException(status_code=400, detail="Valor de tipo de cambio invÃ¡lido")
    new_rate = ExchangeRate(
        rate=float(rate_value),
        source="manual",
        currency_from="USD",
        currency_to="ARS",
    )
    db.add(new_rate)
    db.commit()
    db.refresh(new_rate)
    return {"rate": new_rate.rate, "source": "manual", "fetched_at": new_rate.fetched_at.isoformat()}


@app.post("/admin/exchange-rate/bna")
def fetch_exchange_rate_bna(
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Consulta el tipo de cambio en BNA y lo guarda en DB."""
    from bna_scraper import get_usd_ars_rate
    result = get_usd_ars_rate()
    if result["rate"] is None:
        # Fallback: devolver ultimo tipo de cambio guardado para evitar cortar la operacion.
        cached_rate = db.query(ExchangeRate).order_by(ExchangeRate.fetched_at.desc()).first()
        if cached_rate:
            return {
                "rate": cached_rate.rate,
                "source": f"{cached_rate.source or 'manual'} (cache)",
                "fetched_at": cached_rate.fetched_at.isoformat() if cached_rate.fetched_at else None,
                "warning": result.get("error") or "No se pudo consultar BNA, se usa valor en cache",
            }
        raise HTTPException(status_code=503, detail=result["error"])
    new_rate = ExchangeRate(
        rate=result["rate"],
        source="BNA",
        currency_from="USD",
        currency_to="ARS",
    )
    db.add(new_rate)
    db.commit()
    db.refresh(new_rate)
    return {"rate": new_rate.rate, "source": "BNA", "fetched_at": new_rate.fetched_at.isoformat()}


# ---------------------------------------------------------------------------
# Condiciones de pago
# ---------------------------------------------------------------------------

class PaymentConditionCreate(BaseModel):
    name: str
    discount_percent: float = 0.0
    description: Optional[str] = None
    sort_order: int = 0


@app.get("/admin/payment-conditions")
def get_payment_conditions(
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Lista todas las condiciones de pago."""
    conditions = db.query(PaymentCondition).order_by(PaymentCondition.sort_order).all()
    return [
        {
            "id": c.id, "name": c.name, "discount_percent": c.discount_percent,
            "description": c.description, "active": c.active, "sort_order": c.sort_order,
        }
        for c in conditions
    ]


@app.get("/payment-conditions")
def get_payment_conditions_public(db: Session = Depends(get_db)):
    """Lista las condiciones de pago activas (endpoint pÃºblico para el formulario)."""
    conditions = db.query(PaymentCondition).filter(
        PaymentCondition.active == True
    ).order_by(PaymentCondition.sort_order).all()
    return [
        {"id": c.id, "name": c.name, "discount_percent": c.discount_percent}
        for c in conditions
    ]


@app.post("/admin/payment-conditions")
def create_payment_condition(
    cond: PaymentConditionCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Crea una nueva condiciÃ³n de pago."""
    new_cond = PaymentCondition(**cond.dict(), active=True)
    db.add(new_cond)
    db.commit()
    db.refresh(new_cond)
    return {"id": new_cond.id, "name": new_cond.name, "discount_percent": new_cond.discount_percent}


@app.put("/admin/payment-conditions/{cond_id}")
def update_payment_condition(
    cond_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Actualiza una condiciÃ³n de pago."""
    cond = db.query(PaymentCondition).filter(PaymentCondition.id == cond_id).first()
    if not cond:
        raise HTTPException(status_code=404, detail="CondiciÃ³n no encontrada")
    for field in ("name", "discount_percent", "description", "active", "sort_order"):
        if field in payload:
            setattr(cond, field, payload[field])
    db.commit()
    return {"ok": True}


@app.delete("/admin/payment-conditions/{cond_id}")
def delete_payment_condition(
    cond_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Elimina una condiciÃ³n de pago."""
    cond = db.query(PaymentCondition).filter(PaymentCondition.id == cond_id).first()
    if not cond:
        raise HTTPException(status_code=404, detail="CondiciÃ³n no encontrada")
    db.delete(cond)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# ImportaciÃ³n de lista de precios desde PDF
# ---------------------------------------------------------------------------

@app.post("/admin/price-list/preview")
async def preview_price_list(
    file: UploadFile = File(...),
    admin: dict = Depends(get_current_admin)
):
    """
    Paso 1: Sube el PDF de lista de precios y retorna los productos parseados para revisar.
    No escribe nada en la DB.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")

    try:
        from pdf_parser import parse_price_list_pdf, parse_payment_conditions, HAS_PDFPLUMBER
        if not HAS_PDFPLUMBER:
            raise HTTPException(status_code=500, detail="pdfplumber no instalado en el servidor")
    except ImportError:
        raise HTTPException(status_code=500, detail="MÃ³dulo pdf_parser no disponible")

    # Guardar temporalmente
    import tempfile, shutil
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        products = parse_price_list_pdf(tmp_path)
        payment_conditions = parse_payment_conditions(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error parseando PDF: {e}")
    finally:
        os.unlink(tmp_path)

    return {
        "products": products,
        "payment_conditions": payment_conditions,
        "total_products": len(products),
        "total_with_price": sum(1 for p in products if p["price"] is not None),
    }


@app.post("/admin/price-list/confirm")
async def confirm_price_list(
    payload: dict,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """
    Paso 2: Confirma la importaciÃ³n. Recibe la lista (posiblemente editada) del paso 1
    y la escribe en la DB.

    Payload:
      {
        "products": [...],           # lista de productos del preview (editados)
        "payment_conditions": [...], # condiciones de pago
        "replace_existing": true     # si true, desactiva mÃ¡quinas existentes primero
      }
    """
    products = payload.get("products", [])
    payment_conditions = payload.get("payment_conditions", [])
    replace_existing = payload.get("replace_existing", False)

    if not products:
        raise HTTPException(status_code=400, detail="No hay productos para importar")

    if replace_existing:
        # Borrar specs primero (no hay cascade automÃ¡tico en SQLite)
        db.query(MachineSpec).delete()
        db.query(Machine).delete()
        db.commit()

    imported = 0
    updated = 0
    errors = []

    for p in products:
        code = (p.get("code") or "").strip()
        if not code:
            errors.append(f"Producto sin cÃ³digo: {p.get('name', '?')}")
            continue

        try:
            existing = db.query(Machine).filter(Machine.code == code).first()
            if existing:
                existing.name = p.get("name", existing.name)
                existing.price = p.get("price") or 0.0
                existing.category = p.get("category", existing.category)
                existing.model_name = p.get("model_name", "")
                existing.product_title = p.get("product_title", "")
                existing.price_currency = p.get("price_currency", "USD")
                existing.active = True
                machine = existing
                updated += 1
            else:
                machine = Machine(
                    code=code,
                    name=p.get("name", code),
                    price=p.get("price") or 0.0,
                    category=p.get("category", ""),
                    description="",
                    model_name=p.get("model_name", ""),
                    product_title=p.get("product_title", ""),
                    price_currency=p.get("price_currency", "USD"),
                    active=True,
                )
                db.add(machine)
                db.flush()  # para obtener machine.id
                imported += 1

            # Reemplazar specs
            db.query(MachineSpec).filter(MachineSpec.machine_id == machine.id).delete()
            for i, spec_text in enumerate(p.get("specs", [])):
                if spec_text.strip():
                    db.add(MachineSpec(
                        machine_id=machine.id,
                        spec_text=spec_text.strip(),
                        sort_order=i,
                    ))

            # Importar opcionales como Option global si no existen
            for opt in p.get("optionals", []):
                opt_name = opt.get("name", "").strip()
                opt_price = opt.get("price") or 0.0
                if not opt_name:
                    continue
                existing_opt = db.query(Option).filter(Option.name == opt_name).first()
                if not existing_opt:
                    db.add(Option(name=opt_name, price=opt_price, description="", active=True))

            db.commit()

        except Exception as e:
            db.rollback()
            errors.append(f"Error importando {code}: {e}")

    # Importar condiciones de pago
    if payment_conditions:
        db.query(PaymentCondition).delete()
        for cond in payment_conditions:
            db.add(PaymentCondition(
                name=cond.get("name", ""),
                discount_percent=cond.get("discount_percent", 0.0),
                description=cond.get("description", ""),
                sort_order=cond.get("sort_order", 0),
                active=True,
            ))
        db.commit()

    return {
        "imported": imported,
        "updated": updated,
        "errors": errors,
        "payment_conditions_imported": len(payment_conditions),
    }


@app.get("/admin/price-list/machines")
def list_machines_admin(
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin)
):
    """Lista todas las mÃ¡quinas (incluyendo inactivas) con specs y opcionales."""
    machines = db.query(Machine).order_by(Machine.category, Machine.name).all()
    result = []
    for m in machines:
        result.append({
            "id": m.id,
            "code": m.code,
            "name": m.name,
            "price": m.price,
            "category": m.category,
            "model_name": m.model_name,
            "product_title": m.product_title,
            "price_currency": m.price_currency,
            "active": m.active,
            "specs": [{"text": s.spec_text, "order": s.sort_order} for s in m.specs],
            "options": [{"id": o.id, "name": o.name, "price": o.price} for o in m.options],
        })
    return result


@app.get("/api/afip/client/{cuit}", response_model=AFIPPersonaData)
async def get_client_data(cuit: str):
    """
    Obtiene los datos de un cliente desde AFIP por su CUIT usando WS directo
    """
    try:
        # Usar el nuevo servicio WS directo
        persona_data = await afip_ws.get_persona_data(cuit)
        return persona_data
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

