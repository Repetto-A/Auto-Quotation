"""
Generador de PDFs de cotización para Agromaq.
Genera cotizaciones con datos dinámicos de la DB (specs, modelo, precio, condiciones).
"""
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import tempfile
import os
from timezone_utils import get_arg_tz

AGROMAQ_GREEN = Color(0.176, 0.314, 0.086)   # #2D5016
AGROMAQ_YELLOW = Color(0.957, 0.816, 0.247)  # #F4D03F

MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, './assets/pdflogo.png')
ARG_TZ = get_arg_tz()


def _build_styles():
    styles = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('Title', parent=styles['Heading1'], fontSize=22,
                                alignment=TA_CENTER, textColor=AGROMAQ_GREEN,
                                spaceAfter=10, fontName='Helvetica-Bold'),
        'subtitle': ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=15,
                                   alignment=TA_CENTER, textColor=AGROMAQ_GREEN,
                                   spaceAfter=8, fontName='Helvetica-Bold'),
        'normal': ParagraphStyle('NormalX', parent=styles['Normal'], fontSize=11,
                                 alignment=TA_LEFT, fontName='Helvetica', spaceAfter=4),
        'bullet': ParagraphStyle('Bullet', parent=styles['Normal'], fontSize=11,
                                 leftIndent=15, bulletIndent=5, fontName='Helvetica', spaceAfter=2),
        'price': ParagraphStyle('Price', parent=styles['Normal'], alignment=TA_RIGHT,
                                fontSize=13, fontName='Helvetica'),
        'footer': ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9,
                                 alignment=TA_CENTER, textColor=AGROMAQ_GREEN),
        'center': ParagraphStyle('Center', parent=styles['Normal'], fontSize=11,
                                 alignment=TA_CENTER),
        'cotizacion': ParagraphStyle('Cotizacion', parent=styles['Heading2'], fontSize=13,
                                     alignment=TA_CENTER, textColor=Color(0, 0, 0),
                                     fontName='Helvetica', spaceAfter=4),
        'producto': ParagraphStyle('Producto', parent=styles['Heading2'], fontSize=15,
                                   alignment=TA_CENTER, textColor=Color(0, 0, 0),
                                   fontName='Helvetica-Bold', spaceAfter=8),
    }


def _add_header(story, styles):
    """Agrega logo + fecha + 'COTIZACION'."""
    if os.path.exists(LOGO_PATH):
        logo_img = Image(LOGO_PATH, width=300, height=None)
        logo_img.hAlign = 'CENTER'
        story.append(logo_img)
    else:
        story.append(Spacer(1, 80))
    story.append(Spacer(1, 20))

    hoy = datetime.now(ARG_TZ)
    fecha_str = f"Las Parejas; {hoy.day} de {MESES[hoy.month - 1]} del {hoy.year}"
    story.append(Paragraph(fecha_str, ParagraphStyle(
        'Fecha', parent=styles['normal'], alignment=TA_RIGHT, fontSize=11, spaceAfter=6)))


def _add_client(story, styles, quotation_data):
    """Agrega bloque de datos del cliente."""
    client_name = getattr(quotation_data, 'client_name', None) or getattr(quotation_data, 'clientName', '') or ''
    client_cuit = getattr(quotation_data, 'client_cuit', None) or getattr(quotation_data, 'clientCuit', '') or ''
    client_address = getattr(quotation_data, 'client_address', None) or getattr(quotation_data, 'clientAddress', '') or ''
    client_phone = getattr(quotation_data, 'client_phone', None) or getattr(quotation_data, 'clientPhone', '') or ''

    story.append(Paragraph('Sr.:', styles['normal']))
    if client_name:
        story.append(Paragraph(f'<b>{client_name}</b>', styles['normal']))
    if client_cuit:
        story.append(Paragraph(f'<b>CUIT: {client_cuit}</b>', styles['normal']))
    if client_address:
        story.append(Paragraph(f'<b>{client_address}</b>', styles['normal']))
    if client_phone:
        story.append(Paragraph(f'<b>Tel: {client_phone}</b>', styles['normal']))
    story.append(Spacer(1, 10))


def _add_machine_block(story, styles, machine, final_price, selected_options=None):
    """
    Agrega un bloque de máquina: título, modelo, specs, opcionales, precio.
    machine: objeto SQLAlchemy Machine (con .specs, .product_title, .model_name, etc.)
    final_price: precio final calculado (con descuentos)
    selected_options: lista de Option objects seleccionados (o None)
    """
    # Título del producto
    product_title = getattr(machine, 'product_title', None) or machine.name
    model_name = getattr(machine, 'model_name', None) or ''

    story.append(Paragraph(f'<u>{product_title.upper()}</u>', styles['producto']))
    story.append(Spacer(1, 5))
    if model_name:
        story.append(Paragraph(f'<b>MODELO {model_name}:</b>', styles['normal']))
        story.append(Spacer(1, 8))

    # Especificaciones desde la DB
    specs = getattr(machine, 'specs', [])
    if specs:
        for spec in specs:
            spec_text = getattr(spec, 'spec_text', '') if hasattr(spec, 'spec_text') else str(spec)
            if spec_text.strip():
                story.append(Paragraph(f'• {spec_text}', styles['bullet']))
                story.append(Spacer(1, 5))
    else:
        # Fallback: description
        if machine.description:
            story.append(Paragraph(machine.description, styles['normal']))
    story.append(Spacer(1, 10))

    # Opcionales seleccionados
    if selected_options:
        story.append(Paragraph('<b>Opcionales incluidos:</b>', styles['normal']))
        for opt in selected_options:
            opt_name = getattr(opt, 'name', str(opt))
            opt_price = getattr(opt, 'price', 0)
            currency = getattr(machine, 'price_currency', 'USD')
            price_str = f"U$S {opt_price:,.2f}".replace(',', '.') if currency == 'USD' else f"${opt_price:,.2f}".replace(',', '.')
            story.append(Paragraph(f'• {opt_name} ........... {price_str}', styles['bullet']))
        story.append(Spacer(1, 8))

    # Precio
    currency = getattr(machine, 'price_currency', 'USD')
    if final_price is not None:
        if currency == 'USD':
            price_display = f"U$S {int(final_price):,}".replace(',', '.')
        else:
            price_display = f"${int(final_price):,}".replace(',', '.')
    else:
        price_display = 'Consultar'

    total_length = 130
    puntos = '.' * max(1, total_length - len(price_display) - 2)
    price_line = f"{puntos}{price_display}.="
    story.append(Paragraph(price_line, styles['price']))
    story.append(Spacer(1, 15))


def _add_conditions(story, styles, payment_conditions=None):
    """Agrega bloque de condiciones comerciales."""
    story.append(Paragraph('<b>LOS PRECIOS COTIZADOS SON NETOS A CONCESIONARIOS</b>', styles['center']))
    story.append(Paragraph('NO INCLUYEN EL 10,5% DE I.V.A.', styles['center']))
    story.append(Paragraph('Los precios cotizados son puestos en fábrica sobre camión.', styles['center']))
    story.append(Paragraph('Esta cotización se mantendrá por 1 día; luego caducará sin previo aviso.', styles['center']))

    if payment_conditions:
        story.append(Spacer(1, 10))
        story.append(Paragraph('<b>FORMA DE PAGO:</b>', styles['normal']))
        for cond in payment_conditions:
            name = cond.name if hasattr(cond, 'name') else cond.get('name', '')
            disc = cond.discount_percent if hasattr(cond, 'discount_percent') else cond.get('discount_percent', 0)
            desc = f" – {disc:.0f}% de descuento" if disc > 0 else ""
            story.append(Paragraph(f'• {name}{desc}', styles['bullet']))

    story.append(Spacer(1, 15))


def _add_footer(story, styles):
    """Agrega pie de página."""
    story.append(Spacer(1, 30))
    story.append(Paragraph('Ruta Nacional 178 N° 545 – CP (2505) – Las Parejas, Santa Fe, Argentina', styles['footer']))
    story.append(Paragraph('Tel/Fax: 03471 – 471388 | WhatsApp: +54-3471-671390', styles['footer']))
    story.append(Paragraph('E-mail: ventas@agromaq.com.ar – Web: www.agromaq.com.ar', styles['footer']))


class PDFGenerator:
    def __init__(self):
        self.agromaq_green = AGROMAQ_GREEN
        self.agromaq_yellow = AGROMAQ_YELLOW

    async def generate_quotation_pdf(self, machine, quotation_data, final_price,
                                     selected_options=None, payment_conditions=None):
        """
        Genera PDF de cotización para UNA máquina.

        Args:
            machine: objeto Machine de SQLAlchemy
            quotation_data: objeto con datos del cliente (client_name, client_cuit, etc.)
            final_price: precio final calculado
            selected_options: lista de Option objects seleccionados (opcional)
            payment_conditions: lista de PaymentCondition objects (opcional)
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name

        doc = SimpleDocTemplate(
            pdf_path, pagesize=A4,
            rightMargin=10 * mm, leftMargin=10 * mm,
            topMargin=8 * mm, bottomMargin=20 * mm,
        )
        styles = _build_styles()
        story = []

        _add_header(story, styles)
        _add_client(story, styles, quotation_data)
        story.append(Paragraph('<u>COTIZACION</u>', styles['cotizacion']))
        story.append(Spacer(1, 1))
        _add_machine_block(story, styles, machine, final_price, selected_options)
        _add_conditions(story, styles, payment_conditions)
        _add_footer(story, styles)

        doc.build(story)
        return pdf_path

    async def generate_multiple_quotation_pdf(self, items, quotation_data, payment_conditions=None):
        """
        Genera PDF de cotización para MÚLTIPLES máquinas en un solo documento.

        Args:
            items: lista de dicts con keys:
                   { machine, final_price, selected_options }
            quotation_data: objeto con datos del cliente
            payment_conditions: lista de PaymentCondition (opcional)
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name

        doc = SimpleDocTemplate(
            pdf_path, pagesize=A4,
            rightMargin=10 * mm, leftMargin=10 * mm,
            topMargin=8 * mm, bottomMargin=20 * mm,
        )
        styles = _build_styles()
        story = []

        _add_header(story, styles)
        _add_client(story, styles, quotation_data)
        story.append(Paragraph('<u>COTIZACION</u>', styles['cotizacion']))
        story.append(Spacer(1, 5))

        for i, item in enumerate(items):
            machine = item['machine']
            final_price = item['final_price']
            selected_options = item.get('selected_options')
            _add_machine_block(story, styles, machine, final_price, selected_options)

        _add_conditions(story, styles, payment_conditions)
        _add_footer(story, styles)

        doc.build(story)
        return pdf_path
