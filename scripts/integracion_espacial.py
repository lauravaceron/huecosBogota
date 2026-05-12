"""
Integración espacial de daños viales con datasets urbanos de Bogotá
Toma coordenadas_fotos.csv y lo cruza con datos abiertos de la ciudad.
Uso: python integracion_espacial.py (desde carpeta scripts/)
"""

import re
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


# ──────────────────────────────────────────
# Rutas
# ──────────────────────────────────────────

RUTA_CSV         = "../datos/coordenadas_fotos.csv"
RUTA_LOCALIDADES = "../datosAbiertos/localidades.geojson"
RUTA_ALCALDIAS   = "../datosAbiertos/alcaldias.json"
RUTA_TRONCALES   = "../datosAbiertos/rutas_troncales.geojson"
RUTA_CAMARAS     = "../datosAbiertos/camaras.csv"
RUTA_SALIDA      = "../datos/datos_integrados.csv"

CRS        = "EPSG:4326"
CRS_METROS = "EPSG:3116"



def limpiar_coord(valor):
    """Limpia coordenadas con formatos inconsistentes y devuelve float o None."""
    if pd.isna(valor):
        return None
    s = str(valor).strip()
    s = s.rstrip("NSEWnsew").strip()
    s = re.sub(r"(\d)\s+(\d)", r"\1.\2", s)
    s = re.sub(r"(?<=\d)-(?=\d)", ".", s)
    s = s.replace(" ", "")
    try:
        v = float(s)
        return v if v != 0.0 else None
    except Exception:
        return None

print("\n[1/5] Cargando coordenadas...")
df = pd.read_csv(RUTA_CSV, dtype=str, index_col=0)
df.columns = [c.strip() for c in df.columns]

total_original = len(df)

df["latitud"]  = df["latitud"].apply(limpiar_coord)
df["longitud"] = df["longitud"].apply(limpiar_coord)

df = df.dropna(subset=["latitud", "longitud"])

df.loc[df["longitud"] > 0, "longitud"] = -df.loc[df["longitud"] > 0, "longitud"]

# Filtrar rango geográfico de Bogotá
df = df[
    (df["latitud"].between(3.5, 5.5)) &
    (df["longitud"].between(-75.5, -73.5))
]

descartadas = total_original - len(df)
print(f"      Total original   : {total_original}")
print(f"      Válidas          : {len(df)}")
print(f"      Descartadas      : {descartadas} (coordenadas inválidas o fuera de Bogotá)")


# Cruzar con localidades

print("\n[2/5] Cruzando con localidades...")

gdf_danos = gpd.GeoDataFrame(
    df,
    geometry=[Point(lon, lat) for lon, lat in zip(df["longitud"], df["latitud"])],
    crs=CRS
)

localidades = gpd.read_file(RUTA_LOCALIDADES).to_crs(CRS)

gdf_danos = gpd.sjoin(
    gdf_danos,
    localidades[["LOCNOMBRE", "geometry"]],
    how="left",
    predicate="within"
)
gdf_danos = gdf_danos.rename(columns={"LOCNOMBRE": "localidad"})
gdf_danos = gdf_danos.drop(columns=["index_right"], errors="ignore")

sin_loc = gdf_danos["localidad"].isna().sum()
print(f"      Con localidad    : {len(gdf_danos) - sin_loc}")
if sin_loc > 0:
    print(f"      Sin localidad    : {sin_loc} (fuera del perímetro)")


# Distancia a alcaldía más cercana


print("\n[3/5] Calculando distancia a alcaldías...")

with open(RUTA_ALCALDIAS, encoding="utf-8") as f:
    alcaldias_raw = json.load(f)

features = alcaldias_raw.get("features", alcaldias_raw)
alcaldias_registros = []
for feat in features:
    atributos = feat.get("attributes", {})
    geom      = feat.get("geometry", {})
    x, y      = geom.get("x"), geom.get("y")
    if x is not None and y is not None:
        alcaldias_registros.append({
            "nombre":   atributos.get("NOM_ALCALDIA", ""),
            "geometry": Point(x, y)
        })

gdf_alcaldias = gpd.GeoDataFrame(alcaldias_registros, crs=CRS).to_crs(CRS_METROS)
gdf_metros    = gdf_danos.to_crs(CRS_METROS)

distancias_alc = []
nombres_alc    = []
for punto in gdf_metros.geometry:
    dists = gdf_alcaldias.geometry.distance(punto)
    idx   = dists.idxmin()
    distancias_alc.append(round(dists[idx]))
    nombres_alc.append(gdf_alcaldias.loc[idx, "nombre"])

gdf_danos["alcaldia_cercana"] = nombres_alc
gdf_danos["dist_alcaldia_m"]  = distancias_alc
print(f"      Distancia promedio: {pd.Series(distancias_alc).mean():.0f} m")


# Distancia a ruta troncal más cercana
print("\n[4/5] Calculando distancia a rutas troncales...")

troncales    = gpd.read_file(RUTA_TRONCALES).to_crs(CRS_METROS)
dist_troncal = []
for punto in gdf_metros.geometry:
    dists = troncales.geometry.distance(punto)
    dist_troncal.append(round(dists.min()))

gdf_danos["dist_troncal_m"] = dist_troncal
print(f"      Distancia promedio: {pd.Series(dist_troncal).mean():.0f} m")


#Distancia a cámara más cercana
print("\n[5/5] Calculando distancia a cámaras...")

camaras_df = pd.read_csv(RUTA_CAMARAS, encoding="utf-8-sig").dropna(subset=["LATITUD", "LONGITUD"])
gdf_camaras = gpd.GeoDataFrame(
    camaras_df,
    geometry=[Point(lon, lat) for lon, lat in zip(camaras_df["LONGITUD"], camaras_df["LATITUD"])],
    crs=CRS
).to_crs(CRS_METROS)

dist_camara = []
for punto in gdf_metros.geometry:
    dists = gdf_camaras.geometry.distance(punto)
    dist_camara.append(round(dists.min()))

gdf_danos["dist_camara_m"] = dist_camara
print(f"      Distancia promedio: {pd.Series(dist_camara).mean():.0f} m")


#csv final
columnas_finales = [
    "archivo", "latitud", "longitud",
    "localidad", "alcaldia_cercana", "dist_alcaldia_m",
    "dist_troncal_m", "dist_camara_m"
]

df_final = pd.DataFrame(gdf_danos[[c for c in columnas_finales if c in gdf_danos.columns]])
df_final.to_csv(RUTA_SALIDA, index=False, encoding="utf-8")

print(f"\nRESUMEN FINAL")
print(f"  Total daños integrados : {len(df_final)}")
print(f"  Localidades únicas     : {df_final['localidad'].nunique()}")
print(f"  Archivo guardado en    : {RUTA_SALIDA}\n")
print(df_final[["archivo", "localidad", "dist_troncal_m", "dist_alcaldia_m", "dist_camara_m"]].to_string(index=False))