/* =========================================================
   /api/count — Vercel Serverless (proxy a la API de Railway)
   Recibe { image, mime } del frontend, lo reenvía al
   servidor de inferencia YOLO en Railway, y le devuelve
   el conteo al navegador.

   Variable de entorno requerida en Vercel:
     RAILWAY_API_URL → URL completa de tu API en Railway
                       ej: "https://contador-x-api.up.railway.app"
   ========================================================= */

export default async function handler(req, res) {
    // CORS para pruebas
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') return res.status(200).end();
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Método no permitido. Usa POST.' });
    }

    const RAILWAY_URL = process.env.RAILWAY_API_URL;
    if (!RAILWAY_URL) {
        return res.status(500).json({
            error: 'Falta configurar RAILWAY_API_URL en las variables de entorno de Vercel.',
        });
    }

    const { image, mime } = req.body || {};
    if (!image || typeof image !== 'string') {
        return res.status(400).json({ error: 'Falta el campo "image" (base64).' });
    }

    try {
        // Llamamos al endpoint /count de Railway
        const railwayRes = await fetch(`${RAILWAY_URL.replace(/\/$/, '')}/count`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image, mime: mime || 'image/jpeg' }),
        });

        if (!railwayRes.ok) {
            const text = await railwayRes.text();
            return res.status(railwayRes.status).json({
                error: `API Railway respondió ${railwayRes.status}: ${text.slice(0, 200)}`,
            });
        }

        const data = await railwayRes.json();
        // Railway ya devuelve { count, avgConfidence, predictions, modelTime, imageSize }
        return res.status(200).json(data);

    } catch (err) {
        console.error('[api/count] Error contactando Railway:', err);
        return res.status(502).json({
            error: 'No se pudo contactar el servidor de detección. Intenta de nuevo.',
        });
    }
}

export const config = {
    api: {
        bodyParser: {
            sizeLimit: '12mb',
        },
    },
};
