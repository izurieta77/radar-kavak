# Radar Kavak

App operativa para detectar oportunidades de arbitraje entre inventario seminuevo, Kavak y mercado local Toluca/CDMX/Metepec.

Regla central: no inventar valores. El ranking solo suma spread cuando hay una cotizacion real de Kavak capturada o una publicacion real de mercado guardada con precio y URL.

## Datos actuales

- PDF extraido: 48 filas.
- Excluidos: 10 filas naranjas completas.
- Analizables: 38 filas.
- Publicaciones reales capturadas en `data/market_listings.json`: Facebook Marketplace con URL, precio visible y hora de consulta.
- Cotizaciones Kavak capturadas en `data/kavak_quotes.json`: URL Kavak, oferta de venta directa, prestamo y vigencia. El score y la app usan solo venta directa. No contiene PII.
- Precio de lista ajustado por fin de mes:
  - compra objetivo: lista - 50,000 MXN
  - compra agresiva: lista - 70,000 MXN

## Comandos

```powershell
npm install
python scripts/extract_inventory.py
python scripts/score_opportunities.py
python scripts/market_scan.py
python scripts/scrape_ml_candidates.py
npm test -- --run
npm run build
npm run dev
```

`scripts/score_opportunities.py` no usa promedios ni precios guia. Lee `data/market_listings.json` y solo activa oportunidades con publicaciones reales por misma familia y anio.
Tambien lee `data/kavak_quotes.json`; si una fila tiene oferta Kavak real, marca `kavakStatus: capturado` y conserva `kavakOffer`.

## Kavak asistido

Abrir instrucciones para una fila:

```powershell
python scripts/kavak_probe.py --no 5 --open
```

Reglas:

- No guardar telefono, OTP ni credenciales.
- No evadir captcha.
- No crear citas ni aceptar ventas.
- Si Kavak pide captcha u OTP, se resuelve manualmente y luego se captura la oferta.
- En el formulario Kavak, usar los datos personales indicados por el operador en Chrome; no versionarlos en el repo.
- Para el origen del auto, elegir siempre seminuevo.
- Para tipo de persona, elegir siempre persona fisica.

## Mercado real

Las publicaciones externas deben guardarse con:

- fuente
- URL directa
- titulo visible
- anio/familia
- precio publicado
- ubicacion
- fecha/hora de consulta

Los links de busqueda Toluca/CDMX/Metepec son solo asistidos; ayudan a abrir busquedas, pero no cuentan como evidencia hasta capturar una publicacion concreta.

### Barrido MercadoLibre vs Kavak

```powershell
pip install playwright
python -m playwright install chromium
python scripts/scrape_ml_candidates.py
```

El scraper lee `data/kavak_quotes.json` y solo compara contra `sellOffer` real de Kavak. Filtra CDMX, Estado de Mexico, Morelos, Puebla y Queretaro, excluye Michoacan, bloquea vendedor Kavak y escribe:

- `data/ml_candidates.json`
- `src/data/direct_sale_market_targets.json`
- `output/evidence/ml_candidates_<fecha>.csv`

Si MercadoLibre muestra captcha, corre:

```powershell
python scripts/scrape_ml_candidates.py --headed --stop-on-captcha
```

## Deploy

Netlify usa:

- build command: `npm run build`
- publish directory: `dist`

```powershell
npx netlify status
npx netlify init
npx netlify deploy
npx netlify deploy --prod
```
