import os
import csv
import re
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import pytesseract

# ========================
# CONFIGURACIÓN
# ========================

CARPETA_FOTOS = "../DataSetHuecosBogota"
CSV_SALIDA = "../datos/coordenadas_fotos.csv"

# En Mac normalmente no necesitas esto, pero por si acaso:
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

    except:
        return None, None


def obtener_gps_ocr(ruta_imagen):
    try:
        imagen = Image.open(ruta_imagen)
        texto = pytesseract.image_to_string(imagen)

        # Busca coordenadas tipo: 4.736736, -74.066002
        patron = r"(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)"
        coincidencias = re.findall(patron, texto)

        for lat, lon in coincidencias:
            lat = float(lat)
            lon = float(lon)

            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon

        return None, None

    except:
        return None, None


# ========================
# PROCESAMIENTO
# ========================

extensiones = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")

# 🔥 ORDENAR POR FECHA (como Finder)
archivos = sorted(
    [f for f in os.listdir(CARPETA_FOTOS) if f.lower().endswith(extensiones)],
    key=lambda x: os.path.getmtime(os.path.join(CARPETA_FOTOS, x))
)

resultados = []

for i, archivo in enumerate(archivos):
    ruta = os.path.join(CARPETA_FOTOS, archivo)

    lat, lon = obtener_gps_exif(ruta)
    metodo = "EXIF"

    if lat is None or lon is None:
        lat, lon = obtener_gps_ocr(ruta)
        metodo = "OCR"

    if lat is None or lon is None:
        metodo = "SIN_COORDENADAS"

    resultados.append({
        "index": i,
        "archivo": archivo,
        "latitud": lat,
        "longitud": lon,
        "metodo": metodo
    })

# ========================
# GUARDAR CSV
# ========================

with open(CSV_SALIDA, "w", newline="", encoding="utf-8") as f:
    campos = ["index", "archivo", "latitud", "longitud", "metodo"]
    writer = csv.DictWriter(f, fieldnames=campos)

    writer.writeheader()
    writer.writerows(resultados)

print("✅ Listo. CSV generado en orden por fecha:", CSV_SALIDA)