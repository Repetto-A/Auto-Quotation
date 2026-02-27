"""
Scraper del tipo de cambio USD/ARS desde Banco Nacion Argentina (BNA).

Incluye 3 estrategias:
1) Pipeline curl compatible con Linux (equivalente al compartido por usuario).
2) Descarga HTML con curl y parseo robusto de la fila "Dolar U.S.A".
3) Fallback urllib + parseo robusto.
"""

from __future__ import annotations

import html
import logging
import os
import re
import subprocess
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

BNA_URLS = [
    "https://www.bna.com.ar/Personas",
    "https://www.bna.com.ar/personas",
    "https://www.bna.com.ar/",
    "https://www.nativanacion.com.ar/Personas",
]


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return normalized.lower().strip()


def _clean_cell_text(cell_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", cell_html)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_arg_number(raw: str) -> Optional[float]:
    """
    Convierte formatos argentinos a float:
      1.234,56 -> 1234.56
      1234,56  -> 1234.56
    """
    if not raw:
        return None
    candidate = raw.strip()
    candidate = re.sub(r"[^\d,.\-]", "", candidate)
    if not candidate:
        return None

    if "," in candidate and "." in candidate:
        # Miles con punto + decimales con coma
        candidate = candidate.replace(".", "").replace(",", ".")
    elif "," in candidate:
        candidate = candidate.replace(",", ".")

    try:
        return float(candidate)
    except ValueError:
        return None


def _extract_rate_from_dolar_row(html_content: str) -> Optional[float]:
    """Busca la fila de 'Dolar U.S.A' y toma el valor vendedor."""
    if not html_content:
        return None

    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html_content, flags=re.IGNORECASE | re.DOTALL)
    for row in rows:
        row_text = _clean_cell_text(row)
        normalized = _normalize_text(row_text)

        if "dolar u.s.a" not in normalized and "dolar usa" not in normalized:
            continue

        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.IGNORECASE | re.DOTALL)
        if not cells:
            # fallback: extraer numeros de texto de fila
            numbers = re.findall(r"\d[\d\.\,]*", row_text)
            parsed = [_parse_arg_number(n) for n in numbers]
            parsed = [n for n in parsed if n and n > 0]
            if parsed:
                return parsed[-1]
            continue

        cell_values = [_clean_cell_text(c) for c in cells]
        numeric_cells = []
        for cell in cell_values:
            value = _parse_arg_number(cell)
            if value and value > 0:
                numeric_cells.append(value)

        # Estructura usual: [nombre, compra, venta] -> queremos venta
        if len(numeric_cells) >= 2:
            return numeric_cells[-1]
        if len(numeric_cells) == 1:
            return numeric_cells[0]

    return None


def _parse_html(html_content: str) -> Optional[float]:
    # Intento principal: parsear fila exacta de la tabla
    rate = _extract_rate_from_dolar_row(html_content)
    if rate:
        return rate

    # Fallback de texto completo (incluye casos con estructura HTML distinta)
    text = _clean_cell_text(html.unescape(html_content))
    text = re.sub(r"\s+", " ", text)
    norm_text = _normalize_text(text)

    # Buscar patron de fila textual: Dolar U.S.A <compra> <venta>
    line_match = re.search(
        r"dolar\s*u\.?s\.?a\.?\s+(\d[\d\.\,]*)\s+(\d[\d\.\,]*)",
        norm_text,
        flags=re.IGNORECASE,
    )
    if line_match:
        venta = _parse_arg_number(line_match.group(2))
        if venta and venta > 0:
            return venta

    idx = norm_text.find("dolar u.s.a")
    if idx == -1:
        idx = norm_text.find("dolar usa")
    if idx == -1:
        idx = norm_text.find("dolar")
    if idx == -1:
        return None

    fragment = norm_text[idx : idx + 900]
    numbers = re.findall(r"\d[\d\.\,]*", fragment)
    parsed = [_parse_arg_number(n) for n in numbers]
    parsed = [n for n in parsed if n and n > 0]
    if len(parsed) >= 2:
        return parsed[1]
    if parsed:
        return parsed[-1]
    return None


def _scrape_via_linux_pipeline() -> Optional[float]:
    """
    Replica del pipeline compartido por usuario (Linux):
      curl -s ... | grep -A 2 'Dolar U.S.A' | head -3 | tail -1 | ...
    """
    if os.name == "nt":
        return None

    try:
        cmd = (
            "curl -s https://www.bna.com.ar/Personas | "
            "grep -A 2 'Dolar U.S.A' | head -3 | tail -1 | "
            "sed 's/<//g' | sed 's/>//g' | sed 's/td//g' | sed 's/,/./g' | sed 's/ //g' | "
            "rev | cut -b 3- | rev"
        )
        result = subprocess.run(
            ["bash", "-lc", cmd],
            capture_output=True,
            text=True,
            timeout=20,
        )
        output = (result.stdout or "").strip()
        return _parse_arg_number(output)
    except Exception as exc:
        logger.warning("Pipeline Linux BNA fallo: %s", exc)
        return None


def _scrape_via_curl_html() -> Optional[float]:
    for url in BNA_URLS:
        try:
            result = subprocess.run(
                ["curl", "-sL", "--max-time", "15", url],
                capture_output=True,
                text=True,
                timeout=20,
            )
            html_content = result.stdout or ""
            rate = _parse_html(html_content)
            if rate:
                return rate
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            logger.warning("curl no disponible o timeout para %s: %s", url, exc)
            return None
        except Exception as exc:
            logger.warning("curl html fallo para %s: %s", url, exc)
    return None


def _scrape_via_urllib() -> Optional[float]:
    try:
        import urllib.request
        for url in BNA_URLS:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    html_content = resp.read().decode("utf-8", errors="ignore")
                rate = _parse_html(html_content)
                if rate:
                    return rate
            except Exception as exc:
                logger.warning("urllib intento fallo para %s: %s", url, exc)
                continue
    except Exception as exc:
        logger.warning("urllib fallback fallo: %s", exc)
    return None


def get_usd_ars_rate() -> dict:
    """
    Obtiene tipo de cambio vendedor USD/ARS desde BNA.
    """
    strategies = (
        ("linux-pipeline", _scrape_via_linux_pipeline),
        ("curl-html", _scrape_via_curl_html),
        ("urllib-html", _scrape_via_urllib),
    )

    for source_name, strategy in strategies:
        rate = strategy()
        if rate is not None and rate > 0:
            logger.info("Tipo de cambio BNA obtenido (%s): USD 1 = ARS %s", source_name, rate)
            return {"rate": rate, "source": "BNA", "error": None}

    msg = "No se pudo obtener el tipo de cambio desde BNA"
    logger.error(msg)
    return {"rate": None, "source": "error", "error": msg}
