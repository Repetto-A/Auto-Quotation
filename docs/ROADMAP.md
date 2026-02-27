# Roadmap - Cotizador Agromaq

**Ultima actualizacion:** 2026-02-19

## Corto plazo (en progreso)

### Fundacion
- [x] Limpiar documentacion excesiva
- [ ] Desactivar Telegram Bot (bugs, migrara a WhatsApp)
- [ ] Fix auto-limpieza de cache AFIP (retry automatico en error de token)
- [ ] Enriquecer modelo de datos: specs por maquina, condiciones de pago, tipo de cambio
- [ ] Fix bug `CREATE_QUOTATION` faltante en config frontend

### Importacion de lista de precios
- [ ] Parser de PDF para extraer maquinas, modelos, specs, precios y opcionales
- [ ] Endpoint admin para subir PDF y previsualizar antes de importar
- [ ] UI en panel admin con tabla editable para verificar/corregir datos parseados

### PDFs dinamicos
- [ ] Refactorizar `pdf_generator.py`: usar datos de DB en vez de texto hardcodeado
- [ ] Implementar `generate_multiple_quotation_pdf` (cotizacion con varias maquinas)
- [ ] Agregar opcionales y condiciones de pago al PDF

### Moneda y condiciones comerciales
- [ ] Tipo de cambio configurable (manual + consulta automatica BNA)
- [ ] CRUD condiciones de pago (Contado -12%, Financiado -9%, etc.)
- [ ] Mostrar precios en USD y/o ARS segun configuracion

## Mediano plazo

- [ ] Plantillas de PDF por categoria de maquina (tolvas, volcadores, vaqueros, etc.)
- [ ] Historial de listas de precios importadas (versionado)
- [ ] Reportes: cotizaciones por periodo, maquinas mas cotizadas
- [ ] Notificaciones por email al generar cotizacion
- [ ] Integacion WhatsApp Business (reemplazo del bot Telegram)
- [ ] Multi-usuario admin con roles
- [ ] Deploy automatizado con CI/CD
