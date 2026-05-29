"""
==============================================================
  API CONTADOR X — Railway Deployment
  Recibe imágenes del frontend (Vercel) y cuenta marcas X
  usando un modelo YOLO entrenado (modelo_jigs_marcas_x.pt)
==============================================================
"""

import os
import io
import time
import base64
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from ultralytics import YOLO

# ==============================================================
#  CONFIGURACIÓN
# ==============================================================

MODEL_PATH = Path(__file__).parent / "modelo_jigs_marcas_x.pt"

# Umbral de confianza: solo cuenta detecciones con esta confianza o más
# Ajustable vía variable de entorno en Railway
CONFIDENCE_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.25"))

# IoU para Non-Max Suppression (descarta cajas muy solapadas)
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.45"))

# Tamaño máximo de inferencia (px). YOLO trabaja en cuadrados.
# 640 es el default. Bajar a 480 si va lento en Railway.
INFERENCE_SIZE = int(os.getenv("INFERENCE_SIZE", "640"))

# ==============================================================
#  CARGA DEL MODELO (al iniciar el servidor, NO en cada request)
# ==============================================================

print(f"🔄 Cargando modelo desde: {MODEL_PATH}")
if not MODEL_PATH.exists():
    raise RuntimeError(
        f"❌ No se encontró el modelo en {MODEL_PATH}. "
        "Asegúrate de subir 'modelo_jigs_marcas_x.pt' al repo."
    )

model = YOLO(str(MODEL_PATH))
print(f"✅ Modelo cargado. Clases detectadas: {model.names}")

# ==============================================================
#  APP FASTAPI
# ==============================================================

app = FastAPI(
    title="Contador X API",
    description="API de inferencia YOLO para contar marcas X",
    version="1.0.0",
)

# CORS — permitir llamadas desde el frontend Vercel
# En producción, reemplaza "*" por tu dominio específico para más seguridad:
#   allow_origins=["https://contador-marcas.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ==============================================================
#  MODELOS DE REQUEST / RESPONSE
# ==============================================================

class CountRequest(BaseModel):
    image: str          # base64 sin prefijo "data:image/..."
    mime: str = "image/jpeg"   # opcional, informativo


class Detection(BaseModel):
    x: float
    y: float
    width: float
    height: float
    confidence: float
    class_name: str


class CountResponse(BaseModel):
    count: int
    avgConfidence: float
    predictions: list[Detection]
    modelTime: float
    imageSize: dict


# ==============================================================
#  ENDPOINTS
# ==============================================================

@app.get("/")
def root():
    """Health check para Railway."""
    return {
        "status": "ok",
        "service": "Contador X API",
        "model_classes": model.names,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
    }


@app.get("/health")
def health():
    """Endpoint específico para checks de salud."""
    return {"status": "healthy"}


@app.post("/count", response_model=CountResponse)
def count_marks(req: CountRequest):
    """
    Cuenta marcas X en la imagen recibida.

    Body JSON:
        {
            "image": "<base64 sin prefijo data:>",
            "mime":  "image/jpeg"   // opcional
        }

    Devuelve el conteo, confianza promedio y las detecciones individuales.
    """
    # 1) Decodificar base64 → PIL Image
    try:
        image_bytes = base64.b64decode(req.image)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo decodificar la imagen: {e}",
        )

    # 2) Ejecutar inferencia
    t0 = time.time()
    try:
        results = model.predict(
            source=image,
            conf=CONFIDENCE_THRESHOLD,
            iou=IOU_THRESHOLD,
            imgsz=INFERENCE_SIZE,
            verbose=False,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en inferencia YOLO: {e}",
        )
    elapsed = (time.time() - t0) * 1000  # ms

    # 3) Procesar resultados
    result = results[0]  # primera (y única) imagen
    boxes = result.boxes

    detections = []
    confidences = []

    if boxes is not None and len(boxes) > 0:
        # xywh = centro_x, centro_y, ancho, alto (en pixels)
        xywh = boxes.xywh.cpu().numpy()
        confs = boxes.conf.cpu().numpy()
        clss = boxes.cls.cpu().numpy().astype(int)

        for (x, y, w, h), conf, cls_id in zip(xywh, confs, clss):
            detections.append(
                Detection(
                    x=float(x),
                    y=float(y),
                    width=float(w),
                    height=float(h),
                    confidence=float(conf),
                    class_name=model.names.get(int(cls_id), str(cls_id)),
                )
            )
            confidences.append(float(conf))

    count = len(detections)
    avg_conf = sum(confidences) / count if count > 0 else 0.0

    return CountResponse(
        count=count,
        avgConfidence=round(avg_conf, 4),
        predictions=detections,
        modelTime=round(elapsed, 2),
        imageSize={"width": image.width, "height": image.height},
    )
