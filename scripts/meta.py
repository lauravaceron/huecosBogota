import os
import csv
import re
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import pytesseract

# ========================
# CONFIGURACIÓN
# ========================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CARPETA_FOTOS = os.path.join(BASE_DIR, "DataSetHuecosBogota")
CSV_SALIDA = os.path.join(BASE_DIR, "datos", "coordenadas_fotos.csv")

# pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"

# ========================
# FUNCIONES
# ========================

def convertir_a_grados(valor):
    d = float(valor[0])
    m = float(valor[1])
    s = float(valor[2])
    return d + (m / 60.0) + (s / 3600.0)


def obtener_gps_exif(ruta_imagen):
    try:
        imagen = Image.open(ruta_imagen)
        exif = imagen._getexif()

        if not exif:
            return None, None

        gps_info = {}

        for tag_id, valor in exif.items():
            tag = TAGS.get(tag_id, tag_id)

            if tag == "GPSInfo":
                for key in valor:
                    gps_tag = GPSTAGS.get(key, key)
                    gps_info[gps_tag] = valor[key]

        lat = gps_info.get("GPSLatitude")
        lat_ref = gps_info.get("GPSLatitudeRef")
        lon = gps_info.get("GPSLongitude")
        lon_ref = gps_info.get("GPSLongitudeRef")

        if not lat or not lon:
            return None, None

        lat = convertir_a_grados(lat)
        lon = convertir_a_grados(lon)

        if lat_ref == "S":
            lat = -lat
        if lon_ref == "W":
            lon = -lon

        return lat, lon

    except Exception:
        return None, None


def obtener_gps_ocr(ruta_imagen):
    try:
        imagen = Image.open(ruta_imagen)
        texto = pytesseract.image_to_string(imagen)

        patron = r"(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)"
        coincidencias = re.findall(patron, texto)

        for lat, lon in coincidencias:
            lat = float(lat)
            lon = float(lon)

            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon

        return None, None

    except Exception:
        return None, None


# ========================
# LEER CSV EXISTENTE
# ========================

campos = ["index", "archivo", "latitud", "longitud", "metodo"]

registros_existentes = []
archivos_ya_procesados = set()

if os.path.exists(CSV_SALIDA):
    with open(CSV_SALIDA, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for fila in reader:
            registros_existentes.append(fila)
            archivos_ya_procesados.add(fila["archivo"])

print(f"📌 Fotos ya registradas en el CSV: {len(archivos_ya_procesados)}")


# ========================
# PROCESAR SOLO FOTOS NUEVAS
# ========================

extensiones = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic")

archivos = sorted(
    [f for f in os.listdir(CARPETA_FOTOS) if f.lower().endswith(extensiones)],
    key=lambda x: os.path.getmtime(os.path.join(CARPETA_FOTOS, x))
)

nuevos_resultados = []

ultimo_index = len(registros_existentes)

for archivo in archivos:

    if archivo in archivos_ya_procesados:
        print(f"⏭️ Ya existe, se omite: {archivo}")
        continue

    ruta = os.path.join(CARPETA_FOTOS, archivo)

    lat, lon = obtener_gps_exif(ruta)
    metodo = "EXIF"

    if lat is None or lon is None:
        lat, lon = obtener_gps_ocr(ruta)
        metodo = "OCR"

    if lat is None or lon is None:
        metodo = "SIN_COORDENADAS"

    nuevos_resultados.append({
        "index": ultimo_index,
        "archivo": archivo,
        "latitud": lat,
        "longitud": lon,
        "metodo": metodo
    })

    print(f"✅ Nueva foto procesada: {archivo} | {metodo}")

    ultimo_index += 1


# ========================
# GUARDAR SIN BORRAR LO ANTERIOR
# ========================

todos_los_resultados = registros_existentes + nuevos_resultados

with open(CSV_SALIDA, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=campos)
    writer.writeheader()
    writer.writerows(todos_los_resultados)

print("✅ Listo.")
print(f"📄 CSV actualizado: {CSV_SALIDA}")
print(f"➕ Nuevas fotos agregadas: {len(nuevos_resultados)}")
print(f"📌 Total en CSV: {len(todos_los_resultados)}")