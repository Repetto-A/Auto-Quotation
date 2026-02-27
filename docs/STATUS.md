# Estado del Proyecto - Cotizador Agromaq

**Ultima actualizacion:** 2026-02-20

## Que funciona

- **Frontend web** (React + Vite + Tailwind): Formulario de cotizacion con seleccion de maquinas, opcionales, descuentos globales, consulta CUIT via AFIP
- **Backend API** (FastAPI): CRUD completo de maquinas y opcionales, autenticacion JWT para admin, generacion de cotizaciones
- **Panel de administracion**: Login JWT, gestion de maquinas, opcionales, cotizaciones, importacion de lista, configuracion
- **Consulta AFIP**: Busqueda de cliente por CUIT via WS con cache auto-cleanup y retry en error de token
- **Base de datos**: SQLite en desarrollo / PostgreSQL en produccion. Modelos: Machine (+MachineSpec, +model_name, +product_title), Option, Quotation, MachineSpec, PaymentCondition, ExchangeRate
- **Importacion de lista de precios PDF**: Parser pdfplumber + endpoint preview/confirm + UI en AdminPanel (tab "Importar Lista")
- **PDFs dinamicos**: `pdf_generator.py` usa specs, modelo y titulo de DB (no hardcodeado). Implementado `generate_multiple_quotation_pdf`
- **Tipo de cambio**: Scraping BNA automatico + ingreso manual. Guardado en DB tabla ExchangeRate
- **Condiciones de pago**: CRUD completo (admin) + endpoint publico. Se importan desde PDF o se crean manualmente. Aparecen en PDFs
- **Telegram Bot**: Desconectado (bugs, pendiente migracion a WhatsApp)

## Que NO funciona / pendiente

- **Tipo de cambio en cotizacion**: El endpoint publico `/payment-conditions` y el tipo de cambio actual no se muestran todavia en el formulario de cotizacion (App.tsx). El admin puede configurarlos pero no se aplican automaticamente a los precios
- **Descuento concesionario en PDF**: La bonificacion -15% para concesionarios esta hardcodeada en condiciones, no es configurable
- **SFT (sinfines) sin opcionales en PDF**: El parser no captura los opcionales globales de pagina 9 (OPCIONALES PARA TOLVAS) ligados a las ATF. Se puede agregar manualmente desde el admin
- **Telegram Bot**: Pendiente migracion a WhatsApp

## Stack

| Componente | Tecnologia |
|------------|-----------|
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS |
| Backend | FastAPI + SQLAlchemy + Pydantic |
| DB local | SQLite |
| DB prod | PostgreSQL (Render) |
| PDF | ReportLab |
| AFIP | zeep (SOAP) + openssl (CMS signing) |
| Auth | JWT (PyJWT) |
| PDF Parse | pdfplumber |
| BNA Scraping | curl / urllib |
| Deploy | Vercel (frontend) + Render (backend) |

## Archivos clave

| Archivo | Rol |
|---------|-----|
| `backend/main.py` | FastAPI app, todos los endpoints |
| `backend/db.py` | Modelos SQLAlchemy (Machine, MachineSpec, PaymentCondition, ExchangeRate...) |
| `backend/pdf_generator.py` | Generacion de PDFs dinamicos con ReportLab |
| `backend/pdf_parser.py` | Parser de LISTADEPRECIOS.pdf con pdfplumber |
| `backend/bna_scraper.py` | Scraping tipo de cambio USD/ARS desde BNA |
| `backend/afip_ws.py` | WS AFIP para lookup de CUIT (con cache y retry) |
| `frontend/src/AdminPanel.tsx` | Panel admin con tabs: Maquinas, Opcionales, Importar Lista, Configuracion |
| `frontend/src/components/PriceListImport.tsx` | UI de importacion de lista de precios (preview + confirm) |
| `frontend/src/components/SettingsPanel.tsx` | UI de tipo de cambio y condiciones de pago |
