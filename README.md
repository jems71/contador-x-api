# 🚂 API Contador X — Railway

API de inferencia YOLO que recibe imágenes y devuelve el conteo de marcas X detectadas. Se conecta con el frontend desplegado en Vercel.

## 🏗️ Arquitectura

```
┌─────────────────────┐                ┌─────────────────────────┐
│  Vercel (frontend)  │  ─── POST ───▶ │  Railway (esta API)     │
│  contador-marcas    │  base64 img    │  Python + FastAPI       │
│  .vercel.app        │                │  + modelo YOLO (.pt)    │
│                     │  ◀── JSON ──── │                         │
└─────────────────────┘   { count }    └─────────────────────────┘
```

## 📁 Estructura del proyecto

```
railway-api/
├── main.py                       # API FastAPI con la lógica de inferencia
├── requirements.txt              # Dependencias Python
├── Procfile                      # Comando de inicio para Railway
├── railway.json                  # Config explícita de Railway
├── runtime.txt                   # Versión de Python
├── .python-version               # Versión de Python (alternativa)
├── .gitignore
├── modelo_jigs_marcas_x.pt       # ⚠️ TÚ DEBES SUBIR ESTE ARCHIVO
└── README.md
```

## 🚀 Pasos para desplegar

### 1. Crear repositorio nuevo en GitHub

Cree un repo **distinto** al del frontend, por ejemplo `contador-x-api`.

```bash
git init
git add .
git commit -m "feat: API YOLO inicial"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/contador-x-api.git
git push -u origin main
```

### 2. Subir el modelo `.pt` al repositorio

⚠️ **PASO CRÍTICO**: copie su `modelo_jigs_marcas_x.pt` a la raíz del repo y súbalo.

```bash
cp /ruta/a/su/modelo_jigs_marcas_x.pt .
git add modelo_jigs_marcas_x.pt
git commit -m "add: modelo YOLO entrenado"
git push
```

> **Nota sobre tamaño**: si su modelo pesa más de **100 MB**, GitHub no lo permite por push normal. En ese caso use **Git LFS**:
> ```bash
> git lfs install
> git lfs track "*.pt"
> git add .gitattributes
> git add modelo_jigs_marcas_x.pt
> git commit -m "add: modelo via LFS"
> git push
> ```
> Modelos YOLOv8 nano pesan ~6 MB, small ~22 MB, medium ~52 MB — todos caben sin LFS.

### 3. Conectar el repo a Railway

1. Entre a [railway.app](https://railway.app) → su proyecto ya creado
2. Clic en **"+ New"** → **"GitHub Repo"**
3. Seleccione `contador-x-api`
4. Railway detectará automáticamente Python y empezará a buildear

### 4. (Opcional) Configurar variables de entorno

Si quiere ajustar el comportamiento del modelo, en Railway → su servicio → **Variables**:

| Variable | Default | Qué hace |
|---|---|---|
| `CONF_THRESHOLD` | `0.25` | Confianza mínima para contar una detección |
| `IOU_THRESHOLD` | `0.45` | Filtro de cajas solapadas |
| `INFERENCE_SIZE` | `640` | Tamaño de inferencia (480 = más rápido, menos preciso) |

### 5. Obtener la URL pública

1. Railway → su servicio → pestaña **"Settings"**
2. Sección **"Networking"** → **"Generate Domain"**
3. Le dará algo como: `contador-x-api-production-abc.up.railway.app`
4. **¡Copie esa URL!** La necesita para el siguiente paso.

### 6. Conectar el frontend (Vercel) a esta API

En el repo de **Vercel** (el frontend), reemplace `api/count.js` con el archivo `count.js` que está en este repo.

Luego, en Vercel → su proyecto → **Settings → Environment Variables**, agregue:

| Name | Value |
|---|---|
| `RAILWAY_API_URL` | `https://contador-x-api-production-abc.up.railway.app` (la URL que generó arriba) |

Haga **Redeploy** del frontend para que la variable se aplique.

## 🧪 Probar la API directamente

Antes de conectar con el frontend, puede probar Railway así:

**Health check (en el navegador)**:
```
https://su-app.up.railway.app/
```
Debería responder algo como:
```json
{
  "status": "ok",
  "service": "Contador X API",
  "model_classes": {"0": "marca_x"},
  "confidence_threshold": 0.25
}
```

**Si esto funciona, su modelo está cargado correctamente.** 🎉

**Test del endpoint /count** (usando curl en terminal):
```bash
# Codificar una imagen a base64
base64 -i foto.jpg | tr -d '\n' > foto.b64

# Llamar al endpoint
curl -X POST https://su-app.up.railway.app/count \
  -H "Content-Type: application/json" \
  -d "{\"image\": \"$(cat foto.b64)\"}"
```

Respuesta esperada:
```json
{
  "count": 34,
  "avgConfidence": 0.87,
  "predictions": [...],
  "modelTime": 245.6,
  "imageSize": {"width": 1280, "height": 960}
}
```

## 🩺 Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Error "No se encontró el modelo" | El `.pt` no se subió al repo | `git add modelo_jigs_marcas_x.pt && git push` |
| Build falla por memoria | requirements pesados | El `requirements.txt` ya usa CPU-only torch (liviano) |
| Inferencia muy lenta (>5s) | Imagen muy grande | Baja `INFERENCE_SIZE=480` en variables |
| `count: 0` siempre | Umbral muy alto o modelo no entrenado correctamente | Baja `CONF_THRESHOLD=0.15` y prueba |
| `502 Bad Gateway` | El servicio se durmió (plan gratis) o crasheó | Revisa Logs en Railway |
| El frontend dice "Sin conexión con el servidor" | URL mal configurada en Vercel | Verifica `RAILWAY_API_URL` |

## 💰 Notas sobre costos en Railway

Railway tiene **plan gratis con $5 USD de crédito al mes**. Para una API de inferencia YOLO:

- **Memoria**: ~1 GB RAM (suficiente para YOLOv8n/s)
- **CPU**: pico al cargar, bajo en reposo
- **Estimado**: $3-8 USD/mes con uso moderado (100-500 inferencias/día)

Si supera el plan gratis, considere:
- ✅ Plan Hobby ($5/mes fijo, incluye $5 de uso)
- ✅ Pro Plan ($20/mes, incluye más recursos)

## 📊 Notas técnicas

- El modelo se carga **una sola vez al iniciar** el servidor (no en cada request)
- Usa **CPU-only PyTorch** para mantener la imagen Docker pequeña
- El `ultralytics` detecta automáticamente la versión de YOLO (v5/v8/v11) del archivo `.pt`
- CORS está abierto a `*` para facilitar el desarrollo. **En producción**, restringe a tu dominio Vercel.

## 🔒 Producción (cuando quiera asegurar)

En `main.py`, cambie:
```python
allow_origins=["*"]
```
por:
```python
allow_origins=["https://contador-marcas.vercel.app"]
```

Y agregue una **API Key** opcional para que solo su frontend pueda llamar.
