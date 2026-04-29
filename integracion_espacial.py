"""
Integración espacial de daños viales con datasets urbanos de Bogotá
Proyecto: Detección automática de daños en la malla vial de Bogotá
Uso: python integracion_espacial.py
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point



RUTA_CSV        = "prueba.csv"
RUTA_LOCALIDADES = "localidades.geojson"
RUTA_ALCALDIAS   = "alcaldias.json"
RUTA_TRONCALES   = "rutas_troncales.geojson"
RUTA_CAMARAS     = "camaras.csv"
RUTA_SALIDA      = "datos_integrados.csv"

CRS = "EPSG:4326"       # Sistema de coordenadas geográficas estándar
CRS_METROS = "EPSG:3116"  # Proyección Colombia para calcular distancias en metros


# ──────────────────────────────────────────
# 1. Cargar el CSV de daños y convertir a GeoDataFrame
# ──────────────────────────────────────────

print("\n[1/5] Cargando datos de daños...")
df = pd.read_csv(RUTA_CSV)

# Filtrar solo filas con GPS válido
df = df.dropna(subset=["lat", "lon"])
print(f"      {len(df)} fotos con coordenadas válidas")

# Convertir a GeoDataFrame
gdf_danos = gpd.GeoDataFrame(
    df,
    geometry=[Point(lon, lat) for lat, lon in zip(df["lat"], df["lon"])],
    crs=CRS
)


# ──────────────────────────────────────────
# 2. Cruzar con localidades
# ──────────────────────────────────────────

print("[2/5] Cruzando con localidades...")
localidades = gpd.read_file(RUTA_LOCALIDADES).to_crs(CRS)

gdf_danos = gpd.sjoin(
    gdf_danos,
    localidades[["LOCNOMBRE", "geometry"]],
    how="left",
    predicate="within"
)
gdf_danos = gdf_danos.rename(columns={"LOCNOMBRE": "localidad"})
gdf_danos = gdf_danos.drop(columns=["index_right"], errors="ignore")

sin_localidad = gdf_danos["localidad"].isna().sum()
print(f"      {len(gdf_danos) - sin_localidad} daños asignados a una localidad")
if sin_localidad > 0:
    print(f"      {sin_localidad} daños fuera del perímetro de Bogotá")


# ──────────────────────────────────────────
# 3. Calcular distancia a la alcaldía local más cercana
# ──────────────────────────────────────────

print("[3/5] Calculando distancia a alcaldías...")
alcaldias = gpd.read_file(RUTA_ALCALDIAS).to_crs(CRS_METROS)

# Proyectar daños a metros para calcular distancias reales
gdf_metros = gdf_danos.to_crs(CRS_METROS)

distancias = []
alcaldias_cercanas = []

for punto in gdf_metros.geometry:
    if punto is None:
        distancias.append(None)
        alcaldias_cercanas.append(None)
        continue
    dists = alcaldias.geometry.distance(punto)
    idx_min = dists.idxmin()
    distancias.append(round(dists[idx_min]))
    nombre_col = "NOMBRE" if "NOMBRE" in alcaldias.columns else alcaldias.columns[0]
    alcaldias_cercanas.append(alcaldias.loc[idx_min, nombre_col])

gdf_danos["alcaldia_cercana"] = alcaldias_cercanas
gdf_danos["dist_alcaldia_m"] = distancias
print(f"      Distancia promedio a alcaldía: {pd.Series(distancias).mean():.0f} m")


# ──────────────────────────────────────────
# 4. Calcular distancia a ruta troncal más cercana
# ──────────────────────────────────────────

print("[4/5] Calculando distancia a rutas troncales...")
troncales = gpd.read_file(RUTA_TRONCALES).to_crs(CRS_METROS)

dist_troncal = []
for punto in gdf_metros.geometry:
    if punto is None:
        dist_troncal.append(None)
        continue
    dists = troncales.geometry.distance(punto)
    dist_troncal.append(round(dists.min()))

gdf_danos["dist_troncal_m"] = dist_troncal
print(f"      Distancia promedio a troncal: {pd.Series(dist_troncal).mean():.0f} m")


# ──────────────────────────────────────────
# 5. Cruzar con cámaras de fotodetección
# ──────────────────────────────────────────

print("[5/5] Cruzando con cámaras de fotodetección...")
camaras_df = pd.read_csv(RUTA_CAMARAS)

# Detectar columnas de coordenadas automáticamente
lat_col = next((c for c in camaras_df.columns if "lat" in c.lower()), None)
lon_col = next((c for c in camaras_df.columns if "lon" in c.lower() or "lng" in c.lower()), None)

if lat_col and lon_col:
    camaras_df = camaras_df.dropna(subset=[lat_col, lon_col])
    gdf_camaras = gpd.GeoDataFrame(
        camaras_df,
        geometry=[Point(lon, lat) for lat, lon in zip(camaras_df[lat_col], camaras_df[lon_col])],
        crs=CRS
    ).to_crs(CRS_METROS)

    dist_camara = []
    for punto in gdf_metros.geometry:
        if punto is None:
            dist_camara.append(None)
            continue
        dists = gdf_camaras.geometry.distance(punto)
        dist_camara.append(round(dists.min()))

    gdf_danos["dist_camara_m"] = dist_camara
    print(f"      Distancia promedio a cámara: {pd.Series(dist_camara).mean():.0f} m")
else:
    print("      No se encontraron columnas de coordenadas en camaras.csv")
    gdf_danos["dist_camara_m"] = None


# ──────────────────────────────────────────
# Guardar resultado final
# ──────────────────────────────────────────

columnas_finales = [
    "archivo", "lat", "lon", "altitud", "fecha_hora",
    "localidad", "alcaldia_cercana", "dist_alcaldia_m",
    "dist_troncal_m", "dist_camara_m"
]

df_final = pd.DataFrame(gdf_danos[[c for c in columnas_finales if c in gdf_danos.columns]])
df_final.to_csv(RUTA_SALIDA, index=False, encoding="utf-8")

print(f"\nRESUMEN FINAL")
print(f"  Total daños procesados : {len(df_final)}")
print(f"  Localidades únicas     : {df_final['localidad'].nunique()}")
print(f"  Archivo guardado en    : {RUTA_SALIDA}\n")
print(df_final[["archivo", "localidad", "dist_troncal_m", "dist_alcaldia_m"]].to_string(index=False))