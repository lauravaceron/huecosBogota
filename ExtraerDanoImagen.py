import os
import csv
import cv2
import warnings
import numpy as np
import matplotlib.pyplot as plt
from ultralytics import YOLO

warnings.filterwarnings('ignore')


#modelo

post_training_files_path = "ModeloAnalisisImagenYolo"
best_model_path = os.path.join(post_training_files_path, "best.pt")
best_model = YOLO(best_model_path)


# Rutas

custom_images_path = "DataSetHuecosBogota"
output_path = "AnalisisDañoHueco"
csv_path = "resultados_huecos.csv"

os.makedirs(output_path, exist_ok=True)


# Crea CSV, si no existe




# Cargar imágenes

image_files = [
    file for file in os.listdir(custom_images_path)
    if file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp",
    ".JPG", ".JPEG", ".PNG", ".HEIC", ".heic"))
]

selected_images = image_files


# Leer imágenes ya registradas en el CSV
#evitar duplicados



# Función de clasificación

def clasificar_gravedad(area_pixeles, area_imagen):
    porcentaje = area_pixeles / area_imagen

    if porcentaje < 0.02:
        return "leve"
    elif porcentaje < 0.05:
        return "mediano"
    else:
        return "grave"


# Figura para mostrar resultados

fig, axes = plt.subplots(3, 3, figsize=(20, 21))
fig.suptitle("Bogotá pothole test images", fontsize=24)

# ---------------------------
# Procesamiento
# ---------------------------
# ---------------------------
# Procesar TODAS las imágenes y guardar TODAS
# ---------------------------
for i, image_name in enumerate(selected_images):

    image_path = os.path.join(custom_images_path, image_name)

    original_image = cv2.imread(image_path)

    if original_image is None:
        print(f"No se pudo leer: {image_name}")
        continue

    h, w = original_image.shape[:2]
    area_imagen = h * w

    results = best_model.predict(
        source=image_path,
        imgsz=640,
        conf=0.1,
        verbose=False
    )

    r = results[0]

    gravedad_final = "sin deteccion"

    if r.masks is not None:
        masks = r.masks.data.cpu().numpy()
        areas = []

        for mask in masks:
            mask_bin = (mask > 0.5).astype(np.uint8)
            area = int(mask_bin.sum())
            areas.append(area)

        if len(areas) > 0:
            area_max = max(areas)
            gravedad_final = clasificar_gravedad(area_max, area_imagen)

    # guardar imagen detectada
    annotated_image = r.plot()

    save_path = os.path.join(output_path, f"resultado_{image_name}")
    cv2.imwrite(save_path, annotated_image)

    print(f"{i+1}/{len(selected_images)} guardada: {image_name} -> {gravedad_final}")

    # Guardar imagen 
    annotated_image = r.plot()
    save_path = os.path.join(output_path, f"resultado_{image_name}")
    cv2.imwrite(save_path, annotated_image)

   

