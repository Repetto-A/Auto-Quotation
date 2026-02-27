# Cotizador Agromaq

Sistema interno de cotizaciones para maquinaria agricola Agromaq (Las Parejas, Santa Fe).

## Arquitectura

```
Frontend (React/Vite/TS) --> API (FastAPI) --> SQLite (dev) / PostgreSQL (prod)
                                  |
                            AFIP WS (consulta CUIT)
                            ReportLab (generacion PDF)
```

## Setup local

### Requisitos
- Python 3.11+
- Node.js 18+
- OpenSSL (para firma de certificados AFIP)

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Configurar .env con credenciales (ver tabla abajo)
python main.py
```
API disponible en `http://localhost:8000` (docs en `/docs`)

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Disponible en `http://localhost:5173`

### Inicio rapido (Windows)
```bash
start.bat
```

## Variables de entorno (.env)

| Variable | Descripcion |
|----------|-------------|
| `ADMIN_USER` | Usuario admin del panel |
| `ADMIN_PASS` | Password admin |
| `JWT_SECRET` | Secret para tokens JWT |
| `AFIP_ENV` | `homo` o `prod` |
| `AFIP_CUIT_REPRESENTADA` | CUIT de la empresa |
| `AFIP_CERT_B64` | Certificado AFIP en base64 |
| `AFIP_KEY_B64` | Clave privada AFIP en base64 |
| `DATABASE_URL` | URL de PostgreSQL (solo prod) |
| `VITE_API_URL` | URL del backend (solo frontend en prod) |

## Estructura del proyecto

```
backend/
  main.py              # FastAPI app, endpoints, auth JWT
  db.py                # Modelos SQLAlchemy
  pdf_generator.py     # Generacion de PDFs de cotizacion
  afip_ws.py           # Integracion AFIP (consulta CUIT)
  pdf_parser.py        # Parser de lista de precios PDF
  bna_scraper.py       # Consulta tipo de cambio BNA
frontend/
  src/
    App.tsx            # Formulario principal de cotizacion
    AdminPanel.tsx     # Panel de administracion
    components/        # Componentes React
    config/api.ts      # Configuracion de endpoints
docs/
  STATUS.md            # Estado actual del proyecto
  ROADMAP.md           # Plan a corto y mediano plazo
```

## Endpoints principales

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/machines` | Listar maquinas activas |
| POST | `/quotations` | Crear cotizacion (multi-maquina) |
| POST | `/generate-quote` | Crear cotizacion (legacy, una maquina) |
| GET | `/api/afip/client/{cuit}` | Consultar datos AFIP |
| POST | `/admin/login` | Login admin (JWT) |
| GET | `/admin/machines` | Listar maquinas (admin) |
| POST | `/admin/import/preview` | Previsualizar importacion de lista de precios |
| POST | `/admin/import/confirm` | Confirmar importacion |

Documentacion completa: `http://localhost:8000/docs`

## Documentacion

- [Estado del proyecto](docs/STATUS.md)
- [Roadmap](docs/ROADMAP.md)
