import os
import uuid

# Ruta de la carpeta con las fotos
carpeta = r"DataSetHuecosBogota"

# Extensiones válidas de imágenes
extensiones = [".jpg", ".jpeg", ".png", ".bmp", ".webp"]

for archivo in os.listdir(carpeta):
    ruta_vieja = os.path.join(carpeta, archivo)

    if os.path.isfile(ruta_vieja):
        nombre, ext = os.path.splitext(archivo)

        if ext.lower() in extensiones:
            nuevo_nombre = f"{uuid.uuid4().hex}{ext}"
            ruta_nueva = os.path.join(carpeta, nuevo_nombre)

            os.rename(ruta_vieja, ruta_nueva)
            print(f"{archivo} → {nuevo_nombre}")

print("Renombrado terminado.")