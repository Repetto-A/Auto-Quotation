import os
import base64
import stat
import time
import json
import datetime
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from pydantic import BaseModel
from zeep import Client, Settings
from lxml import etree
import logging
from dotenv import load_dotenv

os.makedirs(".cache", exist_ok=True)
load_dotenv()

# Configurar logging solo para errores
logging.getLogger('zeep.transports').setLevel(logging.ERROR)

# Entorno AFIP
AFIP_ENV = os.getenv("AFIP_ENV", "homo")  # "homo" o "prod"
AFIP_CUIT_REPRESENTADA = os.getenv("AFIP_CUIT_REPRESENTADA")
SERVICE = os.getenv("SERVICE", "ws_sr_constancia_inscripcion")

# URLs según ambiente
WSAA_URLS = {
    "homo": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?WSDL",
    "prod": "https://wsaa.afip.gov.ar/ws/services/LoginCms?WSDL"
}
WSCI_URLS = {
    "homo": "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL",
    "prod": "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?WSDL"
}

# Cache y TTL
CACHE_FILE = Path(os.getenv('AFIP_CACHE_FILE', '.cache/afip_tokens.json'))
TOKEN_TTL = int(os.getenv('AFIP_TOKEN_TTL', 12 * 3600))  # segundos

class AFIPPersonaData(BaseModel):
    cuit: str
    nombre: Optional[str] = None
    razon_social: Optional[str] = None
    domicilio_fiscal: Optional[str] = None

class AFIPWebService:
    def __init__(self, environment: str = None):
        self.environment = environment or AFIP_ENV
        self.cuit_representada = AFIP_CUIT_REPRESENTADA
        self.wsaa_url = WSAA_URLS[self.environment]
        self.wsci_url = WSCI_URLS[self.environment]
        self._token_cache: Optional[str] = None
        self._sign_cache: Optional[str] = None

    def _write_cert_and_key(self) -> Tuple[str, str]:
        cert_b64 = os.getenv("AFIP_CERT_B64")
        key_b64 = os.getenv("AFIP_KEY_B64")
        if not cert_b64 or not key_b64:
            raise RuntimeError("Faltan AFIP_CERT_B64 o AFIP_KEY_B64 en el entorno")

        cert = base64.b64decode(cert_b64)
        key = base64.b64decode(key_b64)

        cache_dir = Path(".cache")
        cache_dir.mkdir(exist_ok=True)

        p_crt = cache_dir / "afip.crt"
        p_key = cache_dir / "afip.key"

        # En Windows, si quedaron read-only de una corrida previa, falla al sobrescribir.
        for p in (p_crt, p_key):
            try:
                if p.exists():
                    os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
            except Exception:
                pass

        with open(p_crt, "wb") as f:
            f.write(cert)
        with open(p_key, "wb") as f:
            f.write(key)

        # En POSIX restringimos a solo lectura; en Windows dejamos rw para evitar bloqueos.
        if os.name != "nt":
            os.chmod(p_crt, stat.S_IRUSR)
            os.chmod(p_key, stat.S_IRUSR)

        return str(p_crt), str(p_key)

    def _clear_cache(self):
        """Borra el cache de tokens y limpia variables internas."""
        self._token_cache = None
        self._sign_cache = None
        try:
            if CACHE_FILE.exists():
                CACHE_FILE.unlink()
                logging.info("Cache AFIP eliminado")
        except PermissionError:
            logging.warning(f"No pude borrar {CACHE_FILE}")

    def _clear_temp_credentials(self):
        """Borra credenciales temporales (crt/key) para forzar su recreacion."""
        temp_files = [Path(".cache") / "afip.crt", Path(".cache") / "afip.key"]
        for temp_file in temp_files:
            try:
                if temp_file.exists():
                    try:
                        os.chmod(temp_file, stat.S_IWRITE | stat.S_IREAD)
                    except Exception:
                        pass
                    temp_file.unlink()
                    logging.info("Archivo temporal AFIP eliminado: %s", temp_file)
            except PermissionError:
                logging.warning("No pude borrar %s", temp_file)

    def _clear_afip_state(self):
        """Limpia todo el estado local AFIP borrando la carpeta .cache completa."""
        self._token_cache = None
        self._sign_cache = None
        cache_dir = Path(".cache")
        try:
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                logging.info("Directorio .cache AFIP eliminado")
        except PermissionError:
            logging.warning("No pude borrar el directorio .cache")
        finally:
            try:
                cache_dir.mkdir(exist_ok=True)
            except Exception:
                pass

    def _load_cache(self) -> Optional[Tuple[str, str]]:
        try:
            if not CACHE_FILE.exists():
                return None
            data = json.loads(CACHE_FILE.read_text())
            if time.time() - data.get("fetched_at", 0) < TOKEN_TTL:
                return data.get("token"), data.get("sign")
            # venció: borramos el archivo y devolvemos None
            CACHE_FILE.unlink()
        except PermissionError:
            logging.warning(f"No pude leer/borrar {CACHE_FILE}, regenerando credenciales")
        return None


    def _save_cache(self, token: str, sign: str):
        cache_dir = CACHE_FILE.parent
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(cache_dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        
        CACHE_FILE.write_text(json.dumps({
            "token": token,
            "sign": sign,
            "fetched_at": time.time()
        }))
        # Dar permiso sólo al usuario actual (rw-------)
        os.chmod(CACHE_FILE, stat.S_IRUSR | stat.S_IWUSR)


    def _generate_ltr(self, service: str) -> str:
        now = datetime.datetime.now()
        unique_id = now.strftime("%y%m%d%H%M")
        gen = (now - datetime.timedelta(minutes=10)).isoformat()
        exp = (now + datetime.timedelta(minutes=10)).isoformat()
        return f"""<loginTicketRequest version="1.0">
  <header>
    <uniqueId>{unique_id}</uniqueId>
    <generationTime>{gen}</generationTime>
    <expirationTime>{exp}</expirationTime>
  </header>
  <service>{service}</service>
</loginTicketRequest>"""


    def _sign_cms(self, xml_str: str, cert_file: str, key_file: str) -> str:
        proc = subprocess.run(
            [
                "openssl", "cms", "-sign",
                "-signer", cert_file,
                "-inkey", key_file,
                "-nodetach",
                "-outform", "DER"
            ],
            input=xml_str.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return base64.b64encode(proc.stdout).decode("ascii")

    def _call_wsaa(self, cms_b64: str) -> Tuple[str, str]:
        # Cache
        creds = self._load_cache()
        if creds:
            return creds
        # Regenerar
        try:
            crt, key = self._write_cert_and_key()
            ltr = self._generate_ltr(SERVICE)
            cms_b64 = self._sign_cms(ltr, crt, key)
            client = Client(self.wsaa_url)
            resp = client.service.loginCms(cms_b64)
            # Normalizar a bytes
            xml_bytes = resp.encode('utf-8') if isinstance(resp, str) else etree.tostring(resp)
            root = etree.fromstring(xml_bytes)
            token = root.findtext('.//credentials/token')
            sign = root.findtext('.//credentials/sign')
            if not token or not sign:
                raise RuntimeError("Error extrayendo token/sign de AFIP")
            self._save_cache(token, sign)
            return token, sign
        except Exception:
            self._clear_afip_state()
            raise

    async def get_persona_data(self, cuit: str) -> AFIPPersonaData:
        clean_cuit = cuit.replace("-", "").replace(" ", "").strip()

        if not clean_cuit.isdigit() or len(clean_cuit) != 11:
            raise ValueError("El CUIT debe tener 11 dígitos")

        last_error = None
        for attempt in range(2):
            try:
                token, sign = self._call_wsaa(SERVICE)

                settings = Settings(strict=False, xml_huge_tree=True)
                client = Client(wsdl=self.wsci_url, settings=settings)

                respuesta = client.service.getPersona_v2(
                    token,
                    sign,
                    self.cuit_representada,
                    clean_cuit
                )

                datos_generales = getattr(respuesta, 'datosGenerales', None)
                if not datos_generales:
                    raise Exception(f"No se encontraron datos generales para el CUIT {cuit}")

                nombre_completo = f"{datos_generales.apellido} {datos_generales.nombre}" if datos_generales.apellido and datos_generales.nombre else None

                domicilio_fiscal = self._format_address(getattr(datos_generales, 'domicilioFiscal', None))

                return AFIPPersonaData(
                    cuit=clean_cuit,
                    nombre=nombre_completo,
                    domicilio_fiscal=domicilio_fiscal
                )

            except Exception as e:
                last_error = e
                msg = str(e).lower()

                if "no se encontró información" in msg:
                    raise e

                is_auth_error = "token" in msg or "sign" in msg or "autenticación" in msg or "expired" in msg
                is_permission_error = "permission denied" in msg or "permiso denegado" in msg
                if is_auth_error and attempt == 0:
                    logging.warning(f"Error de autenticación AFIP (intento {attempt + 1}), limpiando cache y reintentando: {e}")
                    self._clear_afip_state()
                    continue

                if is_permission_error and attempt == 0:
                    logging.warning(f"Error de permisos AFIP (intento {attempt + 1}), limpiando cache/credenciales y reintentando: {e}")
                    self._clear_afip_state()
                    continue

                if "conexion" in msg or "connection" in msg:
                    raise Exception(f"Error de conectividad con AFIP: {e}")
                elif is_auth_error:
                    raise Exception(f"Error de autenticación AFIP: {e}. Token/sign expirado, cache limpiado.")
                else:
                    raise Exception(f"Error consultando AFIP WS: {e}")

        raise Exception(f"Error consultando AFIP tras 2 intentos: {last_error}")

    def _format_address(self, dom) -> Optional[str]:
        if not dom:
            return None
        parts = []
        if getattr(dom, 'codPostal', None): parts.append(f"( {dom.codPostal} )")
        if getattr(dom, 'descripcionProvincia', None): parts.append(dom.descripcionProvincia.upper())
        if getattr(dom, 'direccion', None): parts.append(dom.direccion.upper())
        return " - ".join(parts) if parts else None

# Instancia global
afip_ws = AFIPWebService()
