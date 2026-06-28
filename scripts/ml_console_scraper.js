// ─── RADAR KAVAK — MercadoLibre Console Scraper ───────────────
// Pégalo en DevTools > Console mientras estás en una página de
// búsqueda de autos en MercadoLibre, ordenada por precio ascendente.
//
// URLs sugeridas (pega cada una, corre el script, copia el output):
//
//   CDMX:
//   https://autos.mercadolibre.com.mx/distrito-federal/autos-camionetas/_OrderId_PRICE_ITEM_CONDITION_2230284
//
//   Edomex:
//   https://autos.mercadolibre.com.mx/estado-de-mexico/autos-camionetas/_OrderId_PRICE_ITEM_CONDITION_2230284
//
//   Morelos:
//   https://autos.mercadolibre.com.mx/morelos/autos-camionetas/_OrderId_PRICE_ITEM_CONDITION_2230284
//
//   Puebla:
//   https://autos.mercadolibre.com.mx/puebla/autos-camionetas/_OrderId_PRICE_ITEM_CONDITION_2230284
//
//   Querétaro:
//   https://autos.mercadolibre.com.mx/queretaro/autos-camionetas/_OrderId_PRICE_ITEM_CONDITION_2230284
//
// ──────────────────────────────────────────────────────────────

(function () {
  const today = new Date().toISOString().slice(0, 10);

  // Detecta el estado desde la URL
  function detectRegion() {
    const url = location.href;
    if (url.includes('distrito-federal'))  return 'CDMX';
    if (url.includes('estado-de-mexico'))  return 'Edomex';
    if (url.includes('morelos'))           return 'Morelos';
    if (url.includes('puebla'))            return 'Puebla';
    if (url.includes('queretaro'))         return 'Queretaro';
    return 'Desconocida';
  }

  function cleanPrice(text) {
    if (!text) return null;
    const n = parseInt(text.replace(/[^\d]/g, ''), 10);
    return isNaN(n) || n < 10000 ? null : n;
  }

  function parseKm(text) {
    const m = text && text.match(/([\d,]+)\s*km/i);
    if (!m) return null;
    return parseInt(m[1].replace(',', ''), 10);
  }

  function parseYear(text) {
    const m = text && text.match(/\b(20\d{2})\b/);
    return m ? parseInt(m[1], 10) : null;
  }

  const region = detectRegion();
  const cards = document.querySelectorAll(
    'li.ui-search-layout__item, div.poly-card, article.poly-card'
  );

  const results = [];

  cards.forEach((card, i) => {
    try {
      // Título
      const titleEl = card.querySelector(
        'a.poly-component__title, h2.poly-box a, .ui-search-item__title, h2 a, h3 a'
      );
      const title = titleEl ? titleEl.innerText.trim() : '';

      // URL
      const linkEl = card.querySelector('a[href*="MLM"]');
      let url = linkEl ? linkEl.href : '';
      if (url.includes('?')) url = url.split('?')[0];

      // Precio
      const priceEl = card.querySelector(
        '.andes-money-amount__fraction, .price-tag-fraction'
      );
      const price = cleanPrice(priceEl ? priceEl.innerText : '');

      // Atributos (km, año)
      const attrText = Array.from(
        card.querySelectorAll(
          '.poly-attributes-list__item, .poly-attributes-list li, .ui-search-item__attribute'
        )
      ).map(el => el.innerText).join(' ');

      const km   = parseKm(attrText);
      const year = parseYear(title + ' ' + attrText);

      // Ciudad (aparece en algunos layouts)
      const locEl = card.querySelector('.poly-component__location, .ui-search-item__location');
      const city  = locEl ? locEl.innerText.trim() : region;

      if (!title || !price || !url) return;

      results.push({
        id:              `ml-${Math.abs(url.split('MLM')[1]?.split('-')[0] | 0) || i}`,
        source:          'MercadoLibre',
        observedAt:      today,
        region:          region,
        city:            city,
        year:            year,
        brand:           null,         // llena a mano si quieres filtrar
        model:           null,         // idem
        version:         title,
        km:              km,
        publishedPrice:  price,
        url:             url,
        kavakSellOffer:  null,         // llenar tras cotizar en Kavak
        kavakQuoteUrl:   null,
        kavakCapturedAt: null,
        kavakValidUntil: null,
        notes:           `Barrido ${today} — ${region} — precio más bajo`,
      });
    } catch (_) {}
  });

  if (results.length === 0) {
    console.warn('No se encontraron cards. ¿Está cargada la página?');
    return;
  }

  // Ordena por precio ascendente
  results.sort((a, b) => a.publishedPrice - b.publishedPrice);

  console.log(`✅ ${results.length} autos extraídos de ${region}`);
  console.log('');
  console.log('Precios encontrados:');
  results.forEach((r, i) => {
    console.log(`  #${i+1} $${r.publishedPrice?.toLocaleString()} — ${r.version?.slice(0,60)} — ${r.km ? r.km.toLocaleString()+' km' : 'km ?'}`);
  });

  console.log('');
  console.log('JSON para pegar en data/arbitrage_candidates.json:');
  console.log('─'.repeat(60));
  console.log(JSON.stringify(results, null, 2));
  console.log('─'.repeat(60));
  console.log('Copia todo lo de arriba y pégalo en el array del JSON.');
})();
