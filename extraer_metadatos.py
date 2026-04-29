import csv
import argparse
from pathlib import Path
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
 
 
EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
 
COLUMNAS_CSV = [
    "archivo",
    "ruta_completa",
    "lat",
    "lon",
    "altitud",
    "fecha_hora",
]
 
 
def gps_a_decimal(coordenada, referencia):
    """Convierte coordenada GPS de formato DMS (grados, minutos, segundos) a decimal."""
    try:
        grados = float(coordenada[0])
        minutos = float(coordenada[1])
        segundos = float(coordenada[2])
        decimal = grados + (minutos / 60.0) + (segundos / 3600.0)
        if referencia in ("S", "W"):
            decimal = -decimal
        return round(decimal, 7)
    except Exception:
        return None
 
 
def extraer_gps(info_gps):
    """Extrae latitud, longitud y altitud de los tags GPS."""
    lat, lon, alt = None, None, None
 
    if not info_gps:
        return lat, lon, alt
 
    datos = {GPSTAGS.get(k, k): v for k, v in info_gps.items()}
 
    if "GPSLatitude" in datos and "GPSLatitudeRef" in datos:
        lat = gps_a_decimal(datos["GPSLatitude"], datos["GPSLatitudeRef"])
 
    if "GPSLongitude" in datos and "GPSLongitudeRef" in datos:
        lon = gps_a_decimal(datos["GPSLongitude"], datos["GPSLongitudeRef"])
 
    if "GPSAltitude" in datos:
        try:
            alt = round(float(datos["GPSAltitude"]), 1)
        except Exception:
            alt = None
 
    return lat, lon, alt
 
 
def extraer_metadatos(ruta_imagen):
    """Lee una imagen y extrae sus metadatos de ubicación y fecha."""
    try:
        img = Image.open(ruta_imagen)
        exif_raw = img._getexif()
 
        if not exif_raw:
            return {
                "archivo": Path(ruta_imagen).name,
                "ruta_completa": str(Path(ruta_imagen).resolve()),
                "lat": None,
                "lon": None,
                "altitud": None,
                "fecha_hora": None,
            }
 
        exif = {TAGS.get(k, k): v for k, v in exif_raw.items()}
 
        # GPS
        info_gps = exif.get("GPSInfo")
        lat, lon, alt = extraer_gps(info_gps) if info_gps else (None, None, None)
 
        # Fecha y hora
        fecha_raw = exif.get("DateTimeOriginal") or exif.get("DateTime")
        fecha_hora = None
        if fecha_raw:
            try:
                dt = datetime.strptime(str(fecha_raw), "%Y:%m:%d %H:%M:%S")
                fecha_hora = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                fecha_hora = str(fecha_raw)
 
        return {
            "archivo": Path(ruta_imagen).name,
            "ruta_completa": str(Path(ruta_imagen).resolve()),
            "lat": lat,
            "lon": lon,
            "altitud": alt,
            "fecha_hora": fecha_hora,
        }
 
    except Exception as e:
        return {
            "archivo": Path(ruta_imagen).name,
            "ruta_completa": str(ruta_imagen),
            "lat": None, "lon": None, "altitud": None, "fecha_hora": None,
        }
 
 
def procesar_carpeta(carpeta, archivo_salida):
    """Recorre una carpeta, extrae metadatos de cada imagen y guarda el CSV."""
    carpeta = "DataSetHuecosBogota"
    if not carpeta.exists():
        print(f"ERROR: La carpeta '{carpeta}' no existe.")
        return
 
    imagenes = [f for f in carpeta.rglob("*") if f.suffix.lower() in EXTENSIONES_VALIDAS]
 
    if not imagenes:
        print(f"No se encontraron imágenes en '{carpeta}'")
        return
 
    print(f"\nEncontradas {len(imagenes)} imágenes en '{carpeta}'")
    print(f"Guardando resultados en: {archivo_salida}\n")
 
    resultados = []
    sin_gps = 0
 
    for i, img_path in enumerate(imagenes, 1):
        print(f"  [{i}/{len(imagenes)}] {img_path.name}", end=" ")
        datos = extraer_metadatos(img_path)
 
        if datos["lat"] is not None:
            print(f"→ GPS: ({datos['lat']}, {datos['lon']})")
        else:
            print("→ sin GPS")
            sin_gps += 1
 
        resultados.append(datos)
 
    with open(archivo_salida, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNAS_CSV)
        writer.writeheader()
        writer.writerows(resultados)
 
    print(f"\nRESUMEN")
    print(f"  Total procesadas  : {len(resultados)}")
    print(f"  Con GPS           : {len(resultados) - sin_gps}")
    print(f"  Sin GPS           : {sin_gps}")
    print(f"  CSV guardado en   : {archivo_salida}\n")
 
 
def main():
    parser = argparse.ArgumentParser(
        description="Extrae metadatos EXIF de fotos de daños viales."
    )
    parser.add_argument("--carpeta", "-c", required=True, help="Carpeta con las imágenes")
    parser.add_argument("--salida", "-s", default="datos_danos.csv", help="Archivo CSV de salida")
 
    args = parser.parse_args()
    procesar_carpeta(args.carpeta, args.salida)
 
 
if __name__ == "__main__":
    main()