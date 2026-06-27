# Radar Kavak

App operativa para detectar oportunidades de arbitraje entre inventario seminuevo, Kavak y mercado local Toluca/CDMX/Metepec.

## Datos actuales

- PDF extraido: 48 filas.
- Excluidos: 10 filas naranjas completas.
- Analizables: 38 filas.
- Precio de lista ajustado por fin de mes:
  - compra objetivo: lista - 50,000 MXN
  - compra agresiva: lista - 70,000 MXN

## Comandos

```powershell
npm install
python scripts/extract_inventory.py
python scripts/score_opportunities.py
python scripts/market_scan.py
npm test -- --run
npm run build
npm run dev
```

Para intentar referencias vivas de Seminuevos en el scoring:

```powershell
$env:RADAR_KAVAK_LIVE_MARKET_LIMIT='8'
python scripts/score_opportunities.py
```

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

