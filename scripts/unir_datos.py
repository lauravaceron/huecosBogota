import pandas as pd

print("\n[1/3] Cargando archivos...")
df_integrados = pd.read_csv("../datos/datos_integrados.csv")
df_gravedad   = pd.read_csv("../datos/resultados_huecos.csv")

print(f"      datos_integrados  : {len(df_integrados)} filas")
print(f"      resultados_huecos : {len(df_gravedad)} filas")


print("\n[2/3] Uniendo por nombre de archivo...")

# Renombrar columna para que coincidan
df_gravedad = df_gravedad.rename(columns={"imagen": "archivo"})

df_final = pd.merge(
    df_integrados,
    df_gravedad[["archivo", "gravedad"]],
    on="archivo",
    how="left"
)

sin_gravedad = df_final["gravedad"].isna().sum()
print(f"      Con gravedad      : {len(df_final) - sin_gravedad}")
print(f"      Sin gravedad      : {sin_gravedad} (no procesadas por YOLO)")


# Guardar CSV final
print("\n[3/3] Guardando dataset_final.csv...")
df_final.to_csv("../datos/dataset_final.csv", index=False, encoding="utf-8")


conteo = df_final["gravedad"].value_counts()
print(f"\nRESUMEN FINAL")
print(f"  Total registros  : {len(df_final)}")
print(f"  Grave            : {conteo.get('grave', 0)}")
print(f"  Mediano          : {conteo.get('mediano', 0)}")
print(f"  Leve             : {conteo.get('leve', 0)}")
print(f"  Sin detección    : {conteo.get('sin deteccion', 0)}")
print(f"  Localidades      : {df_final['localidad'].nunique()}")
print(f"\n  Archivo guardado : dataset_final.csv\n")
print(df_final[["archivo", "localidad", "gravedad", "dist_troncal_m", "dist_alcaldia_m"]].to_string(index=False))