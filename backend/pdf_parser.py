"""
Parser de lista de precios en PDF para Agromaq.

Formato del PDF:
- Pag 1: Portada (se omite)
- Pag 2-15: Productos con titulo ALL-CAPS, descripcion/specs, precio "U$S X.XXX.="
- Pag 16: Condiciones comerciales

Patron tipico por pagina:
  TITULO DE PRODUCTO (ALL CAPS)          <- titulo real
  Modelo: X                              <- nombre del modelo (mixed case)
  • spec 1                               <- specs con bullet \uf0d8
  • spec 2
  RESUMEN DEL TIPO (ALL CAPS)            <- bloque de precio (se detecta por tener "PRECIO")
  PRECIO
  MODELO: X - descripcion ... U$S X.XXX.=
  OPCIONALES PRECIO                      <- seccion de opcionales
  item 1 ... U$S X.=
"""
import re
import logging
from typing import Optional

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

BULLET = '\uf0d8'

PRICE_RE = re.compile(r'U\$S\s*([\d.,]+)\.=', re.IGNORECASE)
PRICE_CONSULTAR_RE = re.compile(r'U\$S\s*consultar', re.IGNORECASE)
MODEL_CAPS_RE = re.compile(r'^MODELO:\s*(.+)', re.IGNORECASE)
MODEL_LOWER_RE = re.compile(r'^Modelo:\s*(.+)')
PAGE_HEADER_RE = re.compile(r'^P[\s\S]{0,12}g[\s\S]{0,5}ina\s*\|\s*\d+', re.IGNORECASE)

# Palabras que NO pueden iniciar un titulo de producto (conjunciones/preposiciones/continuaciones)
CONTINUATION_STARTS = {
    'SE', 'QUE', 'PARA', 'LOS', 'LAS', 'CON', 'EN', 'EL', 'LA',
    'UN', 'UNA', 'SIN', 'POR', 'NI', 'O', 'U', 'E', 'AL', 'DEL',
    'EXTENSION', 'HIDRAULICO', 'HIDRAULICA', 'NEUMATICOS', 'IMPIDE',
    'BRUSCAMENTE', 'ACCIDENTES',
}

OPTIONAL_SECTION_RE = re.compile(
    r'^OPCIONAL(?:ES)?\s*(?:PARA\s+\w+)?\s*(?:PRECIO)?\s*:?\s*$',
    re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _parse_price(text: str) -> Optional[float]:
    m = PRICE_RE.search(text)
    if not m:
        return None
    raw = m.group(1).strip().replace('.', '').replace(',', '.')
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_variant_name(price_line: str) -> Optional[str]:
    """
    Extrae el nombre de variante de una línea de precio como:
      'VUELCO MANUAL. . . . . . . U$S 6.087.='  →  'VUELCO MANUAL'
      '. . . . . . . . . . . . . U$S 10.777.=' →  None  (sin prefijo)
    Retorna None si no hay prefijo significativo.
    """
    without_price = PRICE_RE.sub('', price_line).strip()
    # Quitar leader de puntos al final
    without_dots = re.sub(r'[\s.]+$', '', without_price).strip()
    if not without_dots or len(without_dots) < 4:
        return None
    if re.match(r'^MODELO\b', without_dots, re.IGNORECASE):
        return None
    return without_dots


def _is_product_title(line: str) -> bool:
    """True si la linea parece un titulo de producto (mayusculas, sustancial)."""
    line = line.strip()
    if not line or len(line) < 8:
        return False
    if PAGE_HEADER_RE.match(line):
        return False
    if re.match(r'^(MODELO|OPCIONAL|OPCIONALES|PRECIO|LOS PRECIOS|FORMA DE)\b', line, re.IGNORECASE):
        return False
    if PRICE_RE.search(line):
        return False
    if line.startswith(BULLET):
        return False
    # Excluir lineas de continuacion
    first_word = line.split()[0].rstrip('.,;:') if line.split() else ''
    if first_word.upper() in CONTINUATION_STARTS:
        return False
    # Debe ser mayoritariamente MAYUSCULAS
    alpha = [c for c in line if c.isalpha()]
    if not alpha or len(alpha) < 5:
        return False
    upper_ratio = sum(1 for c in alpha if c.isupper()) / len(alpha)
    return upper_ratio >= 0.75


def _is_optional_section(line: str) -> bool:
    """True si la linea marca el inicio de una seccion de opcionales."""
    return bool(OPTIONAL_SECTION_RE.match(line.strip()))


def _clean_spec(line: str) -> str:
    line = line.strip()
    if line.startswith(BULLET):
        line = line[1:].strip()
    return line


def _extract_category(title: str) -> str:
    t = title.upper()
    if 'TOLVA' in t:
        return 'Tolvas'
    if 'TRIVUELCO' in t:
        return 'Volcadores Trivuelco'
    if 'VOLCADOR' in t:
        return 'Volcadores'
    if 'PLAYO' in t or ('BARANDAS' in t and 'VOLCAD' not in t):
        return 'Acoplados Playos'
    if 'BALANCIN' in t or 'TRAILER' in t:
        return 'Trailers'
    if 'VAQUERO' in t:
        return 'Vaqueros'
    if 'ROLLO' in t:
        return 'Transportadores de Rollos'
    if 'SIN FIN' in t:
        return 'Sinfines'
    if 'NIVELADORA' in t or 'HOJA' in t:
        return 'Hojas Niveladoras'
    if 'GRUA' in t:
        return 'Gruas'
    if 'PALA' in t:
        return 'Palas'
    if 'ELEVADOR' in t:
        return 'Elevadores'
    return 'Maquinaria Agricola'


def _generate_code(product_title: str, model_name: str, idx: int) -> str:
    model_clean = re.sub(r'[^A-Z0-9]', '', model_name.upper())
    if model_clean and len(model_clean) >= 2:
        return model_clean[:14]
    words = re.findall(r'[A-ZÁÉÍÓÚ]{2,}', product_title.upper())
    acronym = ''.join(w[0] for w in words)[:6]
    return f"{acronym}{idx:02d}" if acronym else f"PROD{idx:03d}"


def _parse_optionals(opt_lines: list[str]) -> list[dict]:
    """Parsea lineas de opcionales en [{name, price}]."""
    optionals = []
    buffer: list[str] = []

    def flush():
        if not buffer:
            return
        text = ' '.join(buffer)
        price = _parse_price(text)
        name = PRICE_RE.sub('', text).strip()
        name = re.sub(r'\.{2,}', '', name).strip().rstrip('.')
        if name and len(name) > 3:
            optionals.append({'name': name, 'price': price})
        buffer.clear()

    for line in opt_lines:
        line = line.strip()
        if not line:
            continue
        has_price = bool(PRICE_RE.search(line))
        is_bullet = line.startswith(BULLET)
        if is_bullet:
            flush()
            buffer.append(_clean_spec(line))
            if has_price:
                flush()
        elif has_price and buffer:
            buffer.append(line)
            flush()
        elif has_price:
            price = _parse_price(line)
            name = PRICE_RE.sub('', line).strip()
            name = re.sub(r'\.{2,}', '', name).strip().rstrip('.')
            if name and len(name) > 3:
                optionals.append({'name': name, 'price': price})
        else:
            buffer.append(line)

    flush()
    return optionals


def _split_specs_opts(lines: list[str]) -> tuple[list[str], list[str], list[str]]:
    """
    Divide una lista de lineas en (spec_lines, price_lines, optional_lines).
    El corte en opcionales se produce cuando aparece una linea de seccion opcional.
    """
    spec_lines: list[str] = []
    price_lines: list[str] = []
    opt_lines: list[str] = []
    in_optional = False

    for line in lines:
        if _is_optional_section(line):
            in_optional = True
            continue
        # "OPCIONAL: contenido..." → inicio de sección + primer item en misma línea
        if re.match(r'^OPCIONAL(?:ES)?:', line, re.IGNORECASE) and not in_optional:
            in_optional = True
            after_colon = re.sub(r'^OPCIONAL(?:ES)?:\s*', '', line, flags=re.IGNORECASE).strip()
            if after_colon:
                opt_lines.append(after_colon)
            continue
        if in_optional:
            opt_lines.append(line)
        elif PRICE_RE.search(line) or PRICE_CONSULTAR_RE.search(line):
            price_lines.append(line)
        else:
            spec_lines.append(line)

    return spec_lines, price_lines, opt_lines


# ---------------------------------------------------------------------------
# Parseo de bloque de producto
# ---------------------------------------------------------------------------

def _parse_product_block(title: str, body_lines: list[str], idx: int) -> list[dict]:
    """
    Convierte un bloque (titulo + cuerpo) en 1 o mas productos.
    """
    # --- Buscar MODELO: (ALL CAPS) como sub-secciones ---
    segments_caps: list[tuple] = []
    preamble: list[str] = []
    current_model: Optional[str] = None
    current_lines: list[str] = []

    for line in body_lines:
        m = MODEL_CAPS_RE.match(line)
        if m:
            model_str = PRICE_RE.sub('', m.group(1)).strip()
            # Remover guiones de lider de puntos "G.H.G. 6 . . . ." → "G.H.G. 6"
            model_str = re.sub(r'(\s+\.){2,}.*$', '', model_str).strip().rstrip('-–.').strip()
            has_price = bool(PRICE_RE.search(line))
            # Si mismo modelo y tiene precio → es la linea de precio del segmento actual
            if model_str == current_model and has_price:
                current_lines.append(line)
            else:
                if current_model is not None:
                    segments_caps.append((current_model, current_lines))
                else:
                    preamble = current_lines[:]
                current_model = model_str
                current_lines = []
                if has_price:
                    current_lines.append(line)
        else:
            current_lines.append(line)

    if current_model is not None:
        segments_caps.append((current_model, current_lines))

    if segments_caps:
        return _build_products(title, preamble, segments_caps, idx)

    # --- Sin MODELO: ALL CAPS → buscar "Modelo:" inline ---
    segments_inline: list[tuple] = []
    common_specs: list[str] = []
    cur_model_inline: Optional[str] = None
    cur_inline_specs: list[str] = []
    cur_inline_price_lines: list[str] = []
    cur_inline_optionals: list[str] = []
    in_optional = False

    for line in preamble if not body_lines else body_lines:
        if _is_optional_section(line):
            in_optional = True
            # Si "OPCIONAL: contenido ..." la misma linea puede tener un item
            after_colon = re.sub(r'^OPCIONAL(?:ES)?\s*(?:PARA\s+\w+)?\s*:', '', line, flags=re.IGNORECASE).strip()
            if after_colon and len(after_colon) > 3:
                cur_inline_optionals.append(after_colon)
            continue
        if in_optional:
            cur_inline_optionals.append(line)
            continue
        mi = MODEL_LOWER_RE.match(line)
        if mi:
            raw_model = mi.group(1).strip()
            new_model = raw_model.split(' - ')[0].split(' – ')[0].strip()
            has_price = PRICE_RE.search(line)
            # Si el modelo es el mismo que el actual y tiene precio → es la linea de precio, no nuevo modelo
            if new_model == cur_model_inline and has_price:
                cur_inline_price_lines.append(line)
            else:
                if cur_model_inline is not None:
                    segments_inline.append((cur_model_inline, cur_inline_specs, cur_inline_price_lines, cur_inline_optionals))
                    cur_inline_specs = []
                    cur_inline_price_lines = []
                    cur_inline_optionals = []
                    in_optional = False
                cur_model_inline = new_model
                if has_price:
                    cur_inline_price_lines.append(line)
        elif re.match(r'^OPCIONAL(?:ES)?:', line, re.IGNORECASE):
            # "OPCIONAL: item ... U$S X.=" → inicio de sección + primer item en la misma línea
            in_optional = True
            after_colon = re.sub(r'^OPCIONAL(?:ES)?:\s*', '', line, flags=re.IGNORECASE).strip()
            if after_colon and len(after_colon) > 3:
                cur_inline_optionals.append(after_colon)
        elif PRICE_RE.search(line) or PRICE_CONSULTAR_RE.search(line):
            cur_inline_price_lines.append(line)
        elif cur_model_inline is not None:
            cur_inline_specs.append(line)
        else:
            common_specs.append(line)

    if cur_model_inline is not None:
        segments_inline.append((cur_model_inline, cur_inline_specs, cur_inline_price_lines, cur_inline_optionals))
    elif cur_inline_price_lines:
        segments_inline.append(('', cur_inline_specs, cur_inline_price_lines, cur_inline_optionals))
        common_specs = []

    if segments_inline:
        return _build_products(title, common_specs, segments_inline, idx)

    # --- Fallback: sin ningun modelo identificable ---
    fallback_specs, fallback_prices, fallback_opts = _split_specs_opts(body_lines)
    price = _parse_price(' '.join(fallback_prices)) if fallback_prices else None
    specs_clean = [_clean_spec(l) for l in fallback_specs
                   if l.strip() and l != 'PRECIO' and not re.match(r'^(ACOPLADOS?|CARGADOR)\b', l)]

    return [{
        'code': _generate_code(title, '', idx),
        'product_title': title,
        'model_name': '',
        'name': title,
        'category': _extract_category(title),
        'price': price,
        'price_currency': 'USD',
        'specs': specs_clean,
        'optionals': _parse_optionals(fallback_opts),
    }]


def _build_products(
    title: str,
    preamble: list[str],
    segments: list[tuple],
    start_idx: int,
) -> list[dict]:
    """Construye lista de productos desde segmentos."""
    common_specs = [_clean_spec(l) for l in preamble
                    if not PRICE_RE.search(l)
                    and l.strip() and l != 'PRECIO'
                    and not re.match(r'^(ACOPLADOS?|CARGADOR|SIN FINES)\b', l, re.IGNORECASE)]

    products = []
    product_counter = 0  # índice propio para códigos únicos

    for segment in segments:
        if len(segment) == 4:
            model, seg_lines, price_lines_ext, opt_lines_ext = segment
            seg_specs, seg_prices, seg_opts = _split_specs_opts(seg_lines)
            price_lines = price_lines_ext + seg_prices
            opt_lines = opt_lines_ext + seg_opts
        else:
            model, seg_lines = segment
            seg_specs, price_lines, opt_lines = _split_specs_opts(seg_lines)

        all_specs = common_specs + [_clean_spec(l) for l in seg_specs
                                     if l.strip() and l != 'PRECIO']

        # Detectar variantes de precio con prefijo descriptivo
        # ej: "VUELCO MANUAL... U$S 6.087.=" y "VUELCO HIDRAULICO... U$S 6.814.="
        valid_prices = [(pl, _parse_price(pl)) for pl in price_lines if _parse_price(pl) is not None]
        named_variants = [(pl, pv, _extract_variant_name(pl)) for pl, pv in valid_prices]
        named_variants = [(pl, pv, vn) for pl, pv, vn in named_variants if vn]

        if len(named_variants) > 1:
            # Múltiples variantes → un producto por variante
            for pl, pv, vn in named_variants:
                var_model = f"{model} – {vn}" if model else vn
                products.append({
                    'code': _generate_code(title, var_model, start_idx + product_counter),
                    'product_title': title,
                    'model_name': var_model,
                    'name': f"{title} – {var_model}",
                    'category': _extract_category(title),
                    'price': pv,
                    'price_currency': 'USD',
                    'specs': [s for s in all_specs if s],
                    'optionals': _parse_optionals(opt_lines),
                })
                product_counter += 1
        else:
            # Precio único (comportamiento normal)
            price = valid_prices[0][1] if valid_prices else None
            name = f"{title} – {model}" if model else title
            products.append({
                'code': _generate_code(title, model, start_idx + product_counter),
                'product_title': title,
                'model_name': model,
                'name': name,
                'category': _extract_category(title),
                'price': price,
                'price_currency': 'USD',
                'specs': [s for s in all_specs if s],
                'optionals': _parse_optionals(opt_lines),
            })
            product_counter += 1

    return products


# ---------------------------------------------------------------------------
# Parseo por pagina
# ---------------------------------------------------------------------------

def _parse_page(text: str, start_idx: int) -> list[dict]:
    """Parsea el texto de una pagina en lista de productos."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Dividir en bloques por titulo ALL-CAPS
    # Un bloque cuyo body empieza con "PRECIO" es un bloque de resumen (precio summary)
    blocks: list[tuple[str, list[str], bool]] = []   # (title, body, is_summary)
    current_title: Optional[str] = None
    current_body: list[str] = []

    for line in lines:
        if _is_product_title(line) and line not in ('PRECIO',):
            if current_title:
                is_summary = (current_body and current_body[0] == 'PRECIO')
                blocks.append((current_title, current_body, is_summary))
            current_title = line
            current_body = []
        else:
            current_body.append(line)

    if current_title:
        is_summary = (current_body and current_body[0] == 'PRECIO')
        blocks.append((current_title, current_body, is_summary))

    # Procesar bloques: los summary transfieren precio/opcionales al producto anterior
    products: list[dict] = []
    idx = start_idx

    for title, body, is_summary in blocks:
        # Ignorar seccion global de opcionales
        if re.match(r'^OPCIONAL(?:ES)?\s+PARA\b', title, re.IGNORECASE):
            continue

        if is_summary:
            # Extraer precio y opcionales del bloque de resumen
            price = None
            opt_lines: list[str] = []
            in_opt = False
            for line in body:
                if _is_optional_section(line):
                    in_opt = True
                    continue
                if in_opt:
                    opt_lines.append(line)
                elif PRICE_RE.search(line):
                    if price is None:
                        price = _parse_price(line)
                # else: ignore summary header lines

            # Asignar al ultimo producto
            if products:
                last = products[-1]
                if last['price'] is None and price is not None:
                    last['price'] = price
                if opt_lines:
                    last['optionals'].extend(_parse_optionals(opt_lines))
            # else: crear un producto placeholder (caso raro)
        else:
            block_products = _parse_product_block(title, body, idx)
            products.extend(block_products)
            idx += len(block_products)

    return products


# ---------------------------------------------------------------------------
# Funcion principal
# ---------------------------------------------------------------------------

def parse_price_list_pdf(pdf_path: str) -> list[dict]:
    """
    Parsea el PDF de lista de precios y retorna lista de productos para preview admin.

    Cada producto:
        code, product_title, model_name, name, category,
        price, price_currency, specs (list[str]), optionals (list[{name, price}])
    """
    if not HAS_PDFPLUMBER:
        raise RuntimeError("pdfplumber no instalado. Ejecutar: pip install pdfplumber")

    products: list[dict] = []
    product_idx = 1

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if page_num == 0:
                continue  # portada

            text = page.extract_text() or ''

            if 'CONDICIONES COMERCIALES' in text:
                continue  # pagina de condiciones

            # Quitar encabezado de pagina
            text = re.sub(r'^P[\s\S]{0,12}g[\s\S]{0,5}ina\s*\|\s*\d+\n?', '', text, flags=re.MULTILINE)

            page_products = _parse_page(text, product_idx)
            products.extend(page_products)
            product_idx += len(page_products)

    # Garantizar codigos unicos
    seen: dict[str, int] = {}
    for p in products:
        code = p['code']
        if code in seen:
            seen[code] += 1
            p['code'] = f"{code}-{seen[code]}"
        else:
            seen[code] = 0

    return products


# ---------------------------------------------------------------------------
# Condiciones de pago
# ---------------------------------------------------------------------------

def parse_payment_conditions(pdf_path: str) -> list[dict]:
    """
    Extrae condiciones de pago del PDF.
    Retorna [{name, discount_percent, description, sort_order}].
    """
    if not HAS_PDFPLUMBER:
        return []

    conditions: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            if 'CONDICIONES COMERCIALES' not in text:
                continue

            label: Optional[str] = None
            buffer: list[str] = []
            sort_order = 0

            for line in text.split('\n'):
                line = line.strip()
                m = re.match(r'^([a-e])\)\s+(.+)', line)
                if m:
                    if label and buffer:
                        _append_condition(conditions, buffer, sort_order)
                        sort_order += 1
                        buffer = []
                    label = m.group(1)
                    buffer.append(m.group(2))
                elif label and line:
                    buffer.append(line)

            if label and buffer:
                _append_condition(conditions, buffer, sort_order)

    return conditions


def _append_condition(conditions: list, lines: list[str], sort_order: int):
    text = ' '.join(lines).strip()
    pct_m = re.search(r'-\s*(\d+)\s*%', text)
    discount = float(pct_m.group(1)) if pct_m else 0.0
    name_part = text.split(':')[0].strip() if ':' in text else text
    name_part = re.sub(r'\s*[-–]\s*\d+\s*%.*$', '', name_part).strip()
    conditions.append({
        'name': name_part,
        'discount_percent': discount,
        'description': text,
        'sort_order': sort_order,
    })
