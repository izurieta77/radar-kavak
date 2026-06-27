# Radar Kavak Design

## Objetivo

Construir una app web llamada Radar Kavak para detectar oportunidades de arbitraje en autos seminuevos. La primera version debe tomar el inventario BMW del PDF adjunto, excluir solo filas naranjas completas, comparar cada unidad contra referencias de Kavak y mercado local, y producir un ranking accionable de oportunidades.

## Alcance

- Inventario base: PDF `INVENTARIO GENERAL SEMINUEVOS BMW CEVER - SEMINUEVOS BMW SANTA FE`.
- Regla de exclusion: solo se excluyen filas con sombreado naranja completo. Las filas con solo la celda de numero en rosa siguen incluidas.
- Conteo esperado de la extraccion actual: 48 filas detectadas, 10 excluidas, 38 analizables.
- Regla comercial de fin de mes: el precio del PDF es precio de lista. Para oportunidades se modela una compra objetivo con descuento de 50,000 MXN y una compra agresiva con descuento de 70,000 MXN.
- Zonas de mercado: Toluca, CDMX y Metepec.
- Fuentes:
  - Kavak: flujo asistido por navegador para cotizar ano, marca, modelo y continuar con kilometraje/version cuando el sitio lo permita.
  - Mercado: Seminuevos como fuente scrapeable directa; MercadoLibre como fuente secundaria asistida porque el acceso directo automatizado devolvio error.
  - PDF: extraccion local con PyMuPDF y deteccion visual del sombreado.

## Producto

La app sera una herramienta operativa, no landing page. La pantalla principal muestra:

- Sidebar con pasos: Inventario, Kavak, Mercado, Oportunidades.
- Header compacto con estado GitHub y Netlify.
- KPIs: autos analizables, excluidos, oportunidades, margen estimado.
- Tabla priorizada de oportunidades con auto, precio de inventario, referencia Kavak/mercado, spread, confianza y accion.
- Panel derecho de detalle con evidencia, links, notas y pasos siguientes.

Concepto visual aprobado: `docs/concepts/radar-kavak-dashboard-concept.png`.

## Datos y Flujo

1. `scripts/extract_inventory.py` lee el PDF, extrae filas y detecta sombreados.
2. `data/inventario.json` guarda autos normalizados, con `excluded_orange`.
3. `scripts/score_opportunities.py` genera puntajes iniciales usando referencias de mercado disponibles, flags de confianza y gaps por capturar.
   - El spread principal usa `precio_objetivo = precio_lista - 50,000`.
   - El spread agresivo usa `precio_agresivo = precio_lista - 70,000`.
4. `data/opportunities.json` alimenta la app.
5. `scripts/kavak_probe.py` abre Kavak en modo asistido para registrar oferta o rango cuando el flujo llegue a ese dato. Si aparece captcha, OTP, login o telefono, pausa para accion humana.
6. `scripts/market_scan.py` genera links de busqueda y captura referencias scrapeables. MercadoLibre queda como link/evidencia asistida si bloquea scraping.

## App y Deployment

- Frontend: React + Vite.
- Hosting: Netlify.
- Repo: Git local y GitHub cuando quede creado/conectado desde Chrome o remoto.
- Build output: `dist`.
- Configuracion Netlify: `netlify.toml`.

## Restricciones

- No guardar telefono ni codigos OTP en archivos.
- No evadir captchas. Si aparece captcha, el usuario lo resuelve en Chrome y el flujo continua.
- No crear citas ni aceptar ventas en Kavak.
- No inventar ofertas Kavak. Si no hay oferta capturada, marcarla como `pendiente`.
- No afirmar que MercadoLibre fue scrapeado si el sitio bloqueo el acceso.
- La app debe distinguir evidencia real, estimacion y pendiente.

## Verificacion

- Pruebas unitarias para exclusion naranja, normalizacion de precio/kilometraje y scoring.
- Build Vite exitoso.
- Render local verificado en desktop y mobile.
- Conteos visibles en app: 48 total, 10 excluidos, 38 analizables.
- Netlify deploy probado cuando el sitio este linkeado.
- GitHub remoto reportado o bloqueo claro si no se pudo crear/conectar repo.
