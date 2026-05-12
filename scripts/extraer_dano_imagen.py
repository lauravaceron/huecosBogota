import os
import csv
import cv2
import warnings
import numpy as np
from ultralytics import YOLO

warnings.filterwarnings('ignore')


# ──────────────────────────────────────────
# Rutas
# ──────────────────────────────────────────

post_training_files_path = "../ModeloAnalisisImagenYolo"
best_model_path          = os.path.join(post_training_files_path, "best.pt")
custom_images_path       = "../DataSetHuecosBogota"
output_path              = "../AnalisisDañoHueco"
csv_path                 = "../datos/resultados_huecos.csv"

os.makedirs(output_path, exist_ok=True)

best_model = YOLO(best_model_path)


# ──────────────────────────────────────────
# Cargar imágenes
# ──────────────────────────────────────────

image_files = [
    f for f in os.listdir(custom_images_path)
    if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp", ".heic"))
]


# ──────────────────────────────────────────
# Función de clasificación de gravedad
# ──────────────────────────────────────────

def clasificar_gravedad(area_pixeles, area_imagen):
    porcentaje = area_pixeles / area_imagen
    if porcentaje < 0.01:
        return "leve"
    elif porcentaje < 0.03:
        return "mediano"
    else:
        return "grave"


# ──────────────────────────────────────────
# Procesamiento
# ──────────────────────────────────────────

resultados = []

for i, image_name in enumerate(image_files):
    image_path     = os.path.join(custom_images_path, image_name)
    original_image = cv2.imread(image_path)

    if original_image is None:
        print(f"  No se pudo leer: {image_name}")
        continue

    h, w        = original_image.shape[:2]
    area_imagen = h * w

    results = best_model.predict(
        source=image_path,
        imgsz=640,
        conf=0.1,
        verbose=False
    )

    r               = results[0]
    gravedad_final  = "sin deteccion"

    if r.masks is not None:
        masks = r.masks.data.cpu().numpy()
        areas = [int((mask > 0.5).astype(np.uint8).sum()) for mask in masks]
        if areas:
            gravedad_final = clasificar_gravedad(max(areas), area_imagen)

    # Guardar imagen anotada
    annotated_image = r.plot()
    save_path       = os.path.join(output_path, f"resultado_{image_name}")
    cv2.imwrite(save_path, annotated_image)

    resultados.append({"imagen": image_name, "gravedad": gravedad_final})
    print(f"  [{i+1}/{len(image_files)}] {image_name} → {gravedad_final}")


# ──────────────────────────────────────────
# Guardar CSV
# ──────────────────────────────────────────

with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["imagen", "gravedad"])
    writer.writeheader()
    writer.writerows(resultados)

# Resumen
from collections import Counter
conteo = Counter(r["gravedad"] for r in resultados)
print(f"\nRESUMEN")
print(f"  Total procesadas : {len(resultados)}")
print(f"  Grave            : {conteo.get('grave', 0)}")
print(f"  Mediano          : {conteo.get('mediano', 0)}")
print(f"  Leve             : {conteo.get('leve', 0)}")
print(f"  Sin detección    : {conteo.get('sin deteccion', 0)}")
print(f"  CSV guardado en  : {csv_path}")