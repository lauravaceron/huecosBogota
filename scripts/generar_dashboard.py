import json
import math
import csv
import pandas as pd
from pathlib import Path


RUTA_CSV         = "../datos/dataset_final.csv"
RUTA_LOCALIDADES = "../datosAbiertos/localidades.geojson"
RUTA_CAMARAS     = "../datosAbiertos/camaras.csv"
RUTA_SALIDA      = "../dashboard_bogota.html"
GITHUB_FOTOS     = "https://raw.githubusercontent.com/lauravaceron/huecosBogota/main/DataSetHuecosBogota/"

print("\n[1/4] Cargando datos...")
df = pd.read_csv(RUTA_CSV)
print(f"      Daños: {len(df)}")

def clean(obj):
    if isinstance(obj, float) and math.isnan(obj): return None
    if isinstance(obj, dict): return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, list): return [clean(i) for i in obj]
    return obj

puntos = clean(df[[
    'archivo','latitud','longitud','localidad','gravedad',
    'dist_troncal_m','dist_alcaldia_m','dist_camara_m','alcaldia_cercana'
]].to_dict('records'))

with open(RUTA_LOCALIDADES, encoding='utf-8') as f:
    gj = json.load(f)

def simplify(coords, tol=0.002):
    if not coords: return coords
    r = [coords[0]]
    for p in coords[1:]:
        if math.sqrt((p[0]-r[-1][0])**2+(p[1]-r[-1][1])**2) > tol:
            r.append(p)
    return r

loc_geojson = {'type':'FeatureCollection','features':[]}
for feat in gj['features']:
    geom = feat['geometry']
    geom2 = {'type':'Polygon','coordinates':[simplify(ring) for ring in geom['coordinates']]} if geom['type']=='Polygon' else geom
    loc_geojson['features'].append({'type':'Feature','properties':feat['properties'],'geometry':geom2})
print(f"      Localidades: {len(loc_geojson['features'])}")

with open(RUTA_CAMARAS, encoding='utf-8-sig') as f:
    camaras_raw = list(csv.DictReader(f))
camaras = [{'lat':float(c['LATITUD']),'lon':float(c['LONGITUD']),'id':c['ID_CÁMARA'],'nombre':c['NOMBRE_DEL'],'dir':c['DIRECCIÓN'],'vel':c['VELOCIDADM'],'loc':c['LOCALIDAD']} for c in camaras_raw]
print(f"      Cámaras: {len(camaras)}")

print("\n[2/4] Calculando estadísticas...")
loc_stats = {}
for _, row in df.groupby('localidad').agg(
    total=('archivo','count'),
    graves=('gravedad', lambda x:(x=='grave').sum()),
    medianos=('gravedad', lambda x:(x=='mediano').sum()),
    leves=('gravedad', lambda x:(x=='leve').sum()),
    dist_troncal=('dist_troncal_m','mean'),
    dist_alcaldia=('dist_alcaldia_m','mean'),
    dist_camara=('dist_camara_m','mean'),
).reset_index().iterrows():
    loc_stats[row['localidad']] = {
        'total':int(row['total']),'graves':int(row['graves']),
        'medianos':int(row['medianos']),'leves':int(row['leves']),
        'dist_troncal':round(float(row['dist_troncal'])),
        'dist_alcaldia':round(float(row['dist_alcaldia'])),
        'dist_camara':round(float(row['dist_camara'])),
    }

LOC_GJ  = json.dumps(loc_geojson, ensure_ascii=False)
CAMARAS = json.dumps(camaras, ensure_ascii=False)
STATS   = json.dumps(loc_stats, ensure_ascii=False)
PUNTOS  = json.dumps(puntos, ensure_ascii=False)

print("\n[3/4] Generando HTML...")

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Malla Vial Bogotá — Panel de Monitoreo</title>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.4.2/chroma.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#f5f3ef;--paper:#fffef9;--paper2:#f8f5ee;
  --ink:#1a1814;--ink2:#4a4640;--ink3:#8a8480;
  --rust:#c84b31;--amber:#d4820a;--sage:#3d6b4f;--sky:#2c5f8a;
  --border:#ddd9d0;--shadow:0 1px 3px rgba(0,0,0,.08),0 4px 16px rgba(0,0,0,.04);
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Sora',sans-serif;background:var(--bg);color:var(--ink);min-height:100vh}}
header{{background:var(--ink);color:var(--paper);padding:0 32px;height:52px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:1000}}
.logo-wrap{{display:flex;align-items:center;gap:14px}}
.logo-badge{{background:var(--rust);color:white;font-size:10px;font-weight:700;letter-spacing:1px;padding:4px 8px;border-radius:3px;text-transform:uppercase}}
.logo-name{{font-size:13px;font-weight:600;letter-spacing:.3px}}
.logo-sub{{font-size:10px;color:#888;margin-left:2px}}
.header-controls{{display:flex;align-items:center;gap:10px}}
.hsel{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);color:var(--paper);padding:5px 12px;border-radius:4px;font-family:'Sora',sans-serif;font-size:12px;cursor:pointer}}
.hsel option{{background:#1a1814;color:white}}
.hbtn{{background:var(--rust);color:white;border:none;padding:6px 14px;border-radius:4px;font-family:'Sora',sans-serif;font-size:12px;font-weight:600;cursor:pointer;transition:opacity .2s}}
.hbtn:hover{{opacity:.85}}
main{{padding:24px 28px;max-width:1440px;margin:0 auto}}

/* TABS DE VISTA */
.view-tabs{{display:flex;gap:8px;margin-bottom:20px;border-bottom:2px solid var(--border);padding-bottom:0}}
.view-tab{{font-size:12px;font-weight:600;color:var(--ink3);padding:8px 16px;cursor:pointer;border:none;background:none;font-family:'Sora',sans-serif;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .2s}}
.view-tab.active{{color:var(--rust);border-bottom-color:var(--rust)}}
.view-tab:hover:not(.active){{color:var(--ink2)}}
.view-panel{{display:none}}.view-panel.active{{display:block}}

.kpi-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}}
.kpi{{background:var(--paper);border:1px solid var(--border);border-radius:6px;padding:18px 20px;box-shadow:var(--shadow);position:relative;overflow:hidden}}
.kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px}}
.kpi.k-rust::before{{background:var(--rust)}}.kpi.k-amber::before{{background:var(--amber)}}
.kpi.k-sage::before{{background:var(--sage)}}.kpi.k-sky::before{{background:var(--sky)}}
.kpi-label{{font-size:10px;font-weight:600;color:var(--ink3);text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px}}
.kpi-val{{font-family:'JetBrains Mono',monospace;font-size:32px;font-weight:500;color:var(--ink);line-height:1}}
.kpi-sub{{font-size:11px;color:var(--ink3);margin-top:5px}}
.kpi-icon{{position:absolute;right:16px;top:50%;transform:translateY(-50%);font-size:32px;opacity:.12}}
.main-grid{{display:grid;grid-template-columns:1.8fr 1fr;gap:16px;margin-bottom:16px}}
.card{{background:var(--paper);border:1px solid var(--border);border-radius:6px;box-shadow:var(--shadow);overflow:hidden}}
.card-head{{padding:13px 18px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;background:var(--paper2)}}
.card-title{{font-size:11px;font-weight:700;color:var(--ink2);text-transform:uppercase;letter-spacing:.7px}}
.card-badge{{font-size:10px;color:var(--ink3);background:var(--bg);border:1px solid var(--border);padding:2px 8px;border-radius:12px}}
#map{{height:420px}}
#map2{{height:520px}}
.layer-btn{{font-size:11px;font-family:'Sora',sans-serif;border:1px solid var(--border);background:var(--paper);color:var(--ink2);padding:4px 10px;border-radius:3px;cursor:pointer;display:flex;align-items:center;gap:5px;transition:all .15s}}
.layer-btn.active{{background:var(--ink);color:white;border-color:var(--ink)}}
.layer-btn .dot{{width:8px;height:8px;border-radius:50%}}
.loc-detail{{padding:16px 18px}}
.loc-select{{width:100%;background:var(--bg);border:1px solid var(--border);color:var(--ink);padding:7px 10px;border-radius:4px;font-family:'Sora',sans-serif;font-size:12px;cursor:pointer;margin-bottom:12px}}
.loc-stat-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px}}
.loc-stat{{background:var(--bg);border-radius:4px;padding:10px 12px;border:1px solid var(--border)}}
.loc-stat-label{{font-size:9px;text-transform:uppercase;letter-spacing:.6px;color:var(--ink3);margin-bottom:3px}}
.loc-stat-val{{font-size:18px;font-weight:600;font-family:'JetBrains Mono',monospace}}
.loc-stat-val.rust{{color:var(--rust)}}.loc-stat-val.amber{{color:var(--amber)}}.loc-stat-val.sage{{color:var(--sage)}}
.loc-bar-row{{display:flex;align-items:center;gap:8px;margin-bottom:5px;font-size:11px}}
.loc-bar-label{{width:60px;color:var(--ink3);text-align:right}}
.loc-bar-track{{flex:1;height:6px;background:var(--border);border-radius:3px;overflow:hidden}}
.loc-bar-fill{{height:100%;border-radius:3px;transition:width .4s}}
.chart-row{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
.chart-wrap{{padding:16px 18px;height:220px;position:relative}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
thead th{{padding:9px 14px;text-align:left;font-size:10px;font-weight:700;color:var(--ink3);text-transform:uppercase;letter-spacing:.6px;border-bottom:2px solid var(--border);background:var(--paper2);white-space:nowrap}}
tbody tr{{border-bottom:1px solid var(--border);transition:background .1s}}
tbody tr:hover{{background:var(--paper2)}}
tbody tr:last-child{{border-bottom:none}}
td{{padding:10px 14px;color:var(--ink2)}}
td.mono{{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--sky)}}
.pill{{display:inline-block;padding:2px 8px;border-radius:3px;font-size:10px;font-weight:700;letter-spacing:.3px}}
.pill-grave{{background:#fde8e4;color:var(--rust)}}.pill-mediano{{background:#fef3dc;color:var(--amber)}}
.pill-leve{{background:#e4f0e8;color:var(--sage)}}.pill-sin{{background:#eee;color:var(--ink3)}}
.pag{{padding:10px 14px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;font-size:11px;color:var(--ink3);background:var(--paper2)}}
.pag-btns{{display:flex;gap:4px}}
.pag-btn{{background:var(--paper);border:1px solid var(--border);color:var(--ink2);padding:4px 10px;border-radius:3px;cursor:pointer;font-size:11px;font-family:'Sora',sans-serif;transition:all .1s}}
.pag-btn.on{{background:var(--ink);color:white;border-color:var(--ink)}}
.pag-btn:hover:not(.on){{border-color:var(--ink);color:var(--ink)}}
.popup-foto{{width:220px}}
.popup-img{{width:100%;height:140px;object-fit:cover;border-radius:4px;margin-bottom:8px;display:block;background:#f0ede6}}
.popup-title{{font-weight:700;font-size:13px;margin-bottom:4px}}
.popup-row{{font-size:11px;color:#555;margin-bottom:2px}}
.popup-pill{{display:inline-block;padding:2px 7px;border-radius:3px;font-size:10px;font-weight:700;margin-bottom:6px}}
.leaflet-popup-content-wrapper{{border-radius:6px;box-shadow:0 2px 16px rgba(0,0,0,.15)}}
.leaflet-popup-content{{margin:12px 14px;font-family:'Sora',sans-serif}}

/* LEYENDA COROPLÉTICO */
.coro-legend{{
  background:var(--paper);border:1px solid var(--border);
  border-radius:6px;padding:14px 16px;margin-bottom:16px;
  display:flex;align-items:center;gap:16px;flex-wrap:wrap;
}}
.coro-legend-title{{font-size:11px;font-weight:700;color:var(--ink2);text-transform:uppercase;letter-spacing:.6px}}
.coro-scale{{display:flex;align-items:center;gap:6px}}
.coro-bar{{width:160px;height:12px;border-radius:3px;background:linear-gradient(to right,#fff5f0,#c84b31);border:1px solid var(--border)}}
.coro-label{{font-size:10px;color:var(--ink3)}}
.coro-no-data{{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--ink3)}}
.coro-no-data-box{{width:14px;height:14px;background:#e8e4dc;border:1px solid var(--border);border-radius:2px}}
</style>
</head>
<body>
<header>
  <div class="logo-wrap">
    <span class="logo-badge">SMMV</span>
    <div><span class="logo-name">Malla Vial Bogotá</span><span class="logo-sub">Panel de Monitoreo</span></div>
  </div>
  <div class="header-controls">
    <select class="hsel" id="fLoc"><option value="">Todas las localidades</option></select>
    <select class="hsel" id="fGrav">
      <option value="">Toda gravedad</option>
      <option value="grave">Grave</option>
      <option value="mediano">Mediano</option>
      <option value="leve">Leve</option>
    </select>
    <button class="hbtn" onclick="aplicar()">Aplicar filtro</button>
  </div>
</header>

<main>
  <!-- TABS -->
  <div class="view-tabs">
    <button class="view-tab active" onclick="switchView('puntos')">📍 Vista por daños</button>
    <button class="view-tab" onclick="switchView('coro')">🗺 Vista por localidad</button>
  </div>

  <!-- ══════════════════════════════════════════
       VISTA 1 — PUNTOS
  ══════════════════════════════════════════ -->
  <div class="view-panel active" id="panel-puntos">
    <div class="kpi-row">
      <div class="kpi k-rust"><div class="kpi-label">Daños detectados</div><div class="kpi-val" id="k1">—</div><div class="kpi-sub" id="k1s"></div><div class="kpi-icon">⚠</div></div>
      <div class="kpi k-amber"><div class="kpi-label">Severidad promedio</div><div class="kpi-val" id="k2">—</div><div class="kpi-sub" id="k2s"></div><div class="kpi-icon">📊</div></div>
      <div class="kpi k-sage"><div class="kpi-label">Cerca de troncales</div><div class="kpi-val" id="k3">—</div><div class="kpi-sub" id="k3s"></div><div class="kpi-icon">🚌</div></div>
      <div class="kpi k-sky"><div class="kpi-label">Cámaras en Bogotá</div><div class="kpi-val">92</div><div class="kpi-sub">Red de fotodetección activa</div><div class="kpi-icon">📷</div></div>
    </div>
    <div class="main-grid">
      <div class="card">
        <div class="card-head">
          <span class="card-title">Vista espacial — Bogotá D.C.</span>
          <div style="display:flex;gap:6px">
            <button class="layer-btn active" id="lDanos" onclick="toggleLayer('danos')"><span class="dot" style="background:#c84b31"></span>Daños</button>
            <button class="layer-btn active" id="lCamaras" onclick="toggleLayer('camaras')"><span class="dot" style="background:#2c5f8a"></span>Cámaras</button>
            <button class="layer-btn active" id="lLocal" onclick="toggleLayer('local')"><span class="dot" style="background:#3d6b4f"></span>Localidades</button>
          </div>
        </div>
        <div id="map"></div>
      </div>
      <div class="card">
        <div class="card-head"><span class="card-title">Detalle por localidad</span></div>
        <div class="loc-detail">
          <select class="loc-select" id="locSel" onchange="renderLocPanel()">
            <option value="">— Selecciona una localidad —</option>
          </select>
          <div id="locStats"><div style="text-align:center;padding:30px 0;color:var(--ink3);font-size:12px">Selecciona una localidad para ver sus indicadores</div></div>
          <div id="locBar"></div>
        </div>
      </div>
    </div>
    <div class="chart-row">
      <div class="card">
        <div class="card-head"><span class="card-title">Daños por localidad</span><span class="card-badge" id="badgeLoc">Top 10</span></div>
        <div class="chart-wrap"><canvas id="cLoc"></canvas></div>
      </div>
      <div class="card">
        <div class="card-head"><span class="card-title">Distribución por gravedad</span><span class="card-badge">Global</span></div>
        <div class="chart-wrap"><canvas id="cGrav"></canvas></div>
      </div>
    </div>
    <div class="card">
      <div class="card-head"><span class="card-title">Bitácora de incidencias</span><span class="card-badge" id="badgeTbl"></span></div>
      <div style="overflow-x:auto">
        <table>
          <thead><tr><th>ID</th><th>Localidad</th><th>Alcaldía</th><th>Dist. troncal</th><th>Dist. alcaldía</th><th>Dist. cámara</th><th>Gravedad</th></tr></thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
      <div class="pag"><span id="pagInfo"></span><div class="pag-btns" id="pagBtns"></div></div>
    </div>
  </div>

  <!-- ══════════════════════════════════════════
       VISTA 2 — COROPLÉTICO
  ══════════════════════════════════════════ -->
  <div class="view-panel" id="panel-coro">
    <div class="coro-legend">
      <span class="coro-legend-title">Densidad de daños</span>
      <div class="coro-scale">
        <span class="coro-label">0</span>
        <div class="coro-bar"></div>
        <span class="coro-label" id="coro-max-label">máx</span>
      </div>
      <div class="coro-no-data"><div class="coro-no-data-box"></div><span>Sin datos registrados</span></div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-head">
        <span class="card-title">Concentración de daños por localidad</span>
        <span class="card-badge">Haz clic en una localidad para ver el detalle</span>
      </div>
      <div id="map2"></div>
    </div>
    <div class="chart-row">
      <div class="card">
        <div class="card-head"><span class="card-title">Ranking de localidades</span><span class="card-badge">Por total de daños</span></div>
        <div class="chart-wrap"><canvas id="cCoroBar"></canvas></div>
      </div>
      <div class="card">
        <div class="card-head"><span class="card-title">Graves por localidad</span><span class="card-badge">Solo daños graves</span></div>
        <div class="chart-wrap"><canvas id="cCoroGraves"></canvas></div>
      </div>
    </div>
  </div>
</main>

<script>
const GITHUB_BASE = "{GITHUB_FOTOS}";
const LOC_GJ    = {LOC_GJ};
const CAMARAS   = {CAMARAS};
const LOC_STATS = {STATS};
const PUNTOS    = {PUNTOS};

const palette=['#c84b31','#d4820a','#3d6b4f','#2c5f8a','#7b5ea7','#4a7c8f','#8b5e3c','#5a7a3a','#c06b3a','#3a6b7a'];
const colG={{grave:'#c84b31',mediano:'#d4820a',leve:'#3d6b4f','sin deteccion':'#aaa'}};

let filtrados=[...PUNTOS],pagina=1;
const POR_PAG=10;
let cLoc=null,cGrav=null,cCoroBar=null,cCoroGraves=null;
let layerDanos,layerCamaras,layerLocalidades;
let layerState={{danos:true,camaras:true,local:true}};
let map2Initialized=false;

// ── Filtros ──
const locs=[...new Set(PUNTOS.map(p=>p.localidad).filter(Boolean))].sort();
['fLoc','locSel'].forEach(id=>{{
  const sel=document.getElementById(id);
  locs.forEach(l=>{{const o=document.createElement('option');o.value=l;o.textContent=l;sel.appendChild(o)}});
}});

// ── MAPA 1 (puntos) ──
const map=L.map('map').setView([4.66,-74.08],11);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{attribution:'©OpenStreetMap ©CARTO',maxZoom:19}}).addTo(map);

const coloresLoc={{}};locs.forEach((l,i)=>coloresLoc[l]=palette[i%palette.length]);

layerLocalidades=L.geoJSON(LOC_GJ,{{
  style:feat=>{{const col=coloresLoc[feat.properties.LOCNOMBRE]||'#888';return{{fillColor:col,fillOpacity:.07,color:col,weight:1.5,opacity:.5}}}},
  onEachFeature:(feat,layer)=>{{
    const nom=feat.properties.LOCNOMBRE,st=LOC_STATS[nom];
    layer.bindTooltip(`<b>${{nom}}</b>${{st?'<br>'+st.total+' daños':''}}`,{{sticky:true}});
    layer.on('click',()=>{{document.getElementById('locSel').value=nom;renderLocPanel()}});
  }}
}}).addTo(map);

layerCamaras=L.layerGroup().addTo(map);
CAMARAS.forEach(c=>{{
  const m=L.circleMarker([c.lat,c.lon],{{radius:4,fillColor:'#2c5f8a',color:'white',weight:1,fillOpacity:.8}});
  m.bindPopup(`<div style="min-width:150px;font-family:Sora,sans-serif"><div style="font-weight:700;font-size:12px;margin-bottom:4px">${{c.id}}</div><div style="font-size:11px;color:#555">${{c.dir}}</div><div style="font-size:11px;color:#555">Vel. máx: ${{c.vel}} km/h</div><div style="font-size:10px;color:#999;margin-top:4px">${{c.loc}}</div></div>`);
  layerCamaras.addLayer(m);
}});

layerDanos=L.layerGroup().addTo(map);
function buildDanosLayer(datos){{
  layerDanos.clearLayers();
  datos.forEach(p=>{{
    const col=colG[p.gravedad]||'#aaa';
    const r=p.gravedad==='grave'?9:p.gravedad==='mediano'?6:4;
    const pillS=p.gravedad==='grave'?'background:#fde8e4;color:#c84b31':p.gravedad==='mediano'?'background:#fef3dc;color:#d4820a':p.gravedad==='leve'?'background:#e4f0e8;color:#3d6b4f':'background:#eee;color:#999';
    const m=L.circleMarker([p.latitud,p.longitud],{{radius:r,fillColor:col,color:'white',weight:1.5,fillOpacity:.85}});
    m.bindPopup(`<div class="popup-foto">
      <img class="popup-img" src="${{GITHUB_BASE}}${{p.archivo}}" alt="Foto del daño" onerror="this.style.display='none'" loading="lazy"/>
      <div class="popup-title">${{p.localidad||'Sin localidad'}}</div>
      <span class="popup-pill" style="${{pillS}}">${{p.gravedad.toUpperCase()}}</span>
      <div class="popup-row">📍 ${{p.alcaldia_cercana?p.alcaldia_cercana.replace('Alcaldía Local de ',''):'—'}}</div>
      <div class="popup-row">🚌 ${{p.dist_troncal_m}} m a troncal</div>
      <div class="popup-row">🏛 ${{p.dist_alcaldia_m}} m a alcaldía</div>
      <div class="popup-row">📷 ${{p.dist_camara_m}} m a cámara</div>
    </div>`,{{maxWidth:260}});
    layerDanos.addLayer(m);
  }});
}}

function toggleLayer(name){{
  const btn=document.getElementById('l'+name.charAt(0).toUpperCase()+name.slice(1));
  layerState[name]=!layerState[name];
  btn.classList.toggle('active',layerState[name]);
  const lyr=name==='danos'?layerDanos:name==='camaras'?layerCamaras:layerLocalidades;
  layerState[name]?map.addLayer(lyr):map.removeLayer(lyr);
}}

// ── MAPA 2 (coroplético) ──
function initMapCoro(){{
  if(map2Initialized) return;
  map2Initialized=true;

  const map2=L.map('map2').setView([4.66,-74.08],11);
  L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_nolabels/{{z}}/{{x}}/{{y}}{{r}}.png',{{attribution:'©OpenStreetMap ©CARTO',maxZoom:19}}).addTo(map2);

  const totales=Object.fromEntries(Object.entries(LOC_STATS).map(([k,v])=>[k,v.total]));
  const maxVal=Math.max(...Object.values(totales),1);
  document.getElementById('coro-max-label').textContent=maxVal+' daños';

  function getColor(nom){{
    const v=totales[nom];
    if(!v) return '#e8e4dc';
    const t=v/maxVal;
    if(t<0.2) return '#fff0ec';
    if(t<0.4) return '#fbbcaa';
    if(t<0.6) return '#f08060';
    if(t<0.8) return '#d95f35';
    return '#c84b31';
  }}

  L.geoJSON(LOC_GJ,{{
    style:feat=>{{
      const nom=feat.properties.LOCNOMBRE;
      return{{fillColor:getColor(nom),fillOpacity:.82,color:'white',weight:1.5,opacity:.9}};
    }},
    onEachFeature:(feat,layer)=>{{
      const nom=feat.properties.LOCNOMBRE;
      const st=LOC_STATS[nom];
      layer.bindTooltip(`
        <div style="font-family:Sora,sans-serif;min-width:160px">
          <div style="font-weight:700;font-size:13px;margin-bottom:6px">${{nom}}</div>
          ${{st ? `
            <div style="font-size:12px;color:#333">Total daños: <b>${{st.total}}</b></div>
            <div style="font-size:11px;color:#c84b31">Graves: ${{st.graves}}</div>
            <div style="font-size:11px;color:#d4820a">Medianos: ${{st.medianos}}</div>
            <div style="font-size:11px;color:#3d6b4f">Leves: ${{st.leves}}</div>
          ` : '<div style="font-size:11px;color:#999">Sin datos registrados</div>'}}
        </div>
      `,{{sticky:true,opacity:1,className:''}});
      layer.on('mouseover',e=>e.target.setStyle({{fillOpacity:.95,weight:2.5}}));
      layer.on('mouseout',e=>e.target.setStyle({{fillOpacity:.82,weight:1.5}}));
    }}
  }}).addTo(map2);

  // Etiquetas con nombre sobre cada localidad
  LOC_GJ.features.forEach(feat=>{{
    const nom=feat.properties.LOCNOMBRE;
    const st=LOC_STATS[nom];
    const coords=feat.geometry.coordinates[0];
    const lats=coords.map(c=>c[1]),lons=coords.map(c=>c[0]);
    const cLat=(Math.min(...lats)+Math.max(...lats))/2;
    const cLon=(Math.min(...lons)+Math.max(...lons))/2;
    if(nom==='SUMAPAZ') return; // muy grande, omitir
    L.marker([cLat,cLon],{{
      icon:L.divIcon({{
        className:'',
        html:`<div style="font-family:Sora,sans-serif;font-size:9px;font-weight:700;color:#1a1814;text-align:center;white-space:nowrap;text-shadow:0 0 3px white,0 0 3px white">${{nom.split(' ').slice(0,2).join(' ')}}<br><span style="font-weight:400;color:#c84b31">${{st?st.total+' daños':''}}</span></div>`,
        iconAnchor:[0,0]
      }})
    }}).addTo(map2);
  }});

  renderCoroCharts();
}}

function renderCoroCharts(){{
  const entries=Object.entries(LOC_STATS).sort((a,b)=>b[1].total-a[1].total);
  const labels=entries.map(e=>e[0]);
  const totales=entries.map(e=>e[1].total);
  const graves=entries.map(e=>e[1].graves);

  const coroColors=totales.map(v=>{{
    const t=v/Math.max(...totales,1);
    if(t<0.2) return '#fbbcaa';
    if(t<0.4) return '#f08060';
    if(t<0.6) return '#d95f35';
    return '#c84b31';
  }});

  if(cCoroBar) cCoroBar.destroy();
  cCoroBar=new Chart(document.getElementById('cCoroBar'),{{
    type:'bar',
    data:{{labels,datasets:[{{data:totales,backgroundColor:coroColors,borderRadius:3,borderSkipped:false}}]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:'#8a8480',font:{{size:9}},maxRotation:40}},grid:{{color:'#eeebe4'}}}},y:{{ticks:{{color:'#8a8480',font:{{size:10}}}},grid:{{color:'#eeebe4'}}}}}}}}
  }});

  if(cCoroGraves) cCoroGraves.destroy();
  cCoroGraves=new Chart(document.getElementById('cCoroGraves'),{{
    type:'bar',
    data:{{labels,datasets:[{{data:graves,backgroundColor:'#fde8e4',borderColor:'#c84b31',borderWidth:1.5,borderRadius:3,borderSkipped:false}}]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:'#8a8480',font:{{size:9}},maxRotation:40}},grid:{{color:'#eeebe4'}}}},y:{{ticks:{{color:'#8a8480',font:{{size:10}}}},grid:{{color:'#eeebe4'}}}}}}}}
  }});
}}

// ── Switch de vistas ──
function switchView(v){{
  document.querySelectorAll('.view-tab').forEach((t,i)=>t.classList.toggle('active',i===(v==='puntos'?0:1)));
  document.getElementById('panel-puntos').classList.toggle('active',v==='puntos');
  document.getElementById('panel-coro').classList.toggle('active',v==='coro');
  if(v==='coro') setTimeout(()=>initMapCoro(),50);
}}

// ── Panel localidad ──
function renderLocPanel(){{
  const nom=document.getElementById('locSel').value,st=LOC_STATS[nom];
  const el=document.getElementById('locStats'),bar=document.getElementById('locBar');
  if(!st){{el.innerHTML='<div style="text-align:center;padding:30px 0;color:var(--ink3);font-size:12px">Selecciona una localidad</div>';bar.innerHTML='';return}}
  el.innerHTML=`
    <div class="loc-stat-grid">
      <div class="loc-stat"><div class="loc-stat-label">Total daños</div><div class="loc-stat-val">${{st.total}}</div></div>
      <div class="loc-stat"><div class="loc-stat-label">Graves</div><div class="loc-stat-val rust">${{st.graves}}</div></div>
      <div class="loc-stat"><div class="loc-stat-label">Medianos</div><div class="loc-stat-val amber">${{st.medianos}}</div></div>
      <div class="loc-stat"><div class="loc-stat-label">Leves</div><div class="loc-stat-val sage">${{st.leves}}</div></div>
      <div class="loc-stat"><div class="loc-stat-label">Dist. troncal prom.</div><div class="loc-stat-val" style="font-size:14px">${{st.dist_troncal}} m</div></div>
      <div class="loc-stat"><div class="loc-stat-label">Dist. alcaldía prom.</div><div class="loc-stat-val" style="font-size:14px">${{st.dist_alcaldia}} m</div></div>
      <div class="loc-stat" style="grid-column:1/-1"><div class="loc-stat-label">Dist. cámara prom.</div><div class="loc-stat-val" style="font-size:14px">${{st.dist_camara}} m</div></div>
    </div>`;
  const mx=st.total;
  bar.innerHTML=`
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:.6px;color:var(--ink3);margin-bottom:8px;margin-top:4px">Distribución</div>
    <div class="loc-bar-row"><span class="loc-bar-label">Grave</span><div class="loc-bar-track"><div class="loc-bar-fill" style="width:${{mx?st.graves/mx*100:0}}%;background:#c84b31"></div></div><span style="font-size:11px;color:var(--ink3)">${{st.graves}}</span></div>
    <div class="loc-bar-row"><span class="loc-bar-label">Mediano</span><div class="loc-bar-track"><div class="loc-bar-fill" style="width:${{mx?st.medianos/mx*100:0}}%;background:#d4820a"></div></div><span style="font-size:11px;color:var(--ink3)">${{st.medianos}}</span></div>
    <div class="loc-bar-row"><span class="loc-bar-label">Leve</span><div class="loc-bar-track"><div class="loc-bar-fill" style="width:${{mx?st.leves/mx*100:0}}%;background:#3d6b4f"></div></div><span style="font-size:11px;color:var(--ink3)">${{st.leves}}</span></div>`;
  for(const feat of LOC_GJ.features){{
    if(feat.properties.LOCNOMBRE===nom){{map.fitBounds(L.geoJSON(feat).getBounds(),{{padding:[20,20]}});break}}
  }}
}}

// ── KPIs ──
function calcScore(g){{return g==='grave'?10:g==='mediano'?5:g==='leve'?1:0}}
function renderKPIs(datos){{
  const total=datos.length,avg=total?(datos.reduce((s,d)=>s+calcScore(d.gravedad),0)/total).toFixed(1):0;
  const sitp=datos.filter(d=>d.dist_troncal_m<=500).length,graves=datos.filter(d=>d.gravedad==='grave').length;
  document.getElementById('k1').textContent=total;
  document.getElementById('k1s').textContent=`${{graves}} graves · ${{datos.filter(d=>d.gravedad==='mediano').length}} medianos`;
  document.getElementById('k2').textContent=avg+'/10';
  document.getElementById('k2s').textContent=avg>=5?'Nivel alto':'Nivel moderado';
  document.getElementById('k3').textContent=sitp;
  document.getElementById('k3s').textContent=`${{total?Math.round(sitp/total*100):0}}% del total — ≤500 m`;
}}

// ── Charts vista 1 ──
function renderCharts(datos){{
  const locC={{}};datos.forEach(d=>{{if(d.localidad)locC[d.localidad]=(locC[d.localidad]||0)+1}});
  const sorted=Object.entries(locC).sort((a,b)=>b[1]-a[1]).slice(0,10);
  if(cLoc)cLoc.destroy();
  cLoc=new Chart(document.getElementById('cLoc'),{{type:'bar',data:{{labels:sorted.map(e=>e[0]),datasets:[{{data:sorted.map(e=>e[1]),backgroundColor:sorted.map((_,i)=>palette[i%palette.length]+'cc'),borderRadius:3,borderSkipped:false}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{color:'#8a8480',font:{{size:10}},maxRotation:35}},grid:{{color:'#eeebe4'}}}},y:{{ticks:{{color:'#8a8480',font:{{size:10}}}},grid:{{color:'#eeebe4'}}}}}}}}}});
  const gC={{grave:0,mediano:0,leve:0,'sin deteccion':0}};datos.forEach(d=>gC[d.gravedad]=(gC[d.gravedad]||0)+1);
  if(cGrav)cGrav.destroy();
  cGrav=new Chart(document.getElementById('cGrav'),{{type:'doughnut',data:{{labels:['Grave','Mediano','Leve','Sin det.'],datasets:[{{data:[gC.grave,gC.mediano,gC.leve,gC['sin deteccion']],backgroundColor:['#c84b31','#d4820a','#3d6b4f','#ccc'],borderWidth:2,borderColor:'#fffef9',hoverOffset:6}}]}},options:{{responsive:true,maintainAspectRatio:false,cutout:'60%',plugins:{{legend:{{position:'bottom',labels:{{color:'#4a4640',font:{{size:11}},padding:12,boxWidth:12}}}}}}}}}});
}}

// ── Tabla ──
function pill(g){{return g==='grave'?'<span class="pill pill-grave">GRAVE</span>':g==='mediano'?'<span class="pill pill-mediano">MEDIANO</span>':g==='leve'?'<span class="pill pill-leve">LEVE</span>':'<span class="pill pill-sin">S/D</span>'}}
function shortId(a){{return 'BV-'+a.slice(0,6).toUpperCase()}}
function renderTabla(datos){{
  const ini=(pagina-1)*POR_PAG,pag=datos.slice(ini,ini+POR_PAG);
  document.getElementById('tbody').innerHTML=pag.map(d=>`<tr><td class="mono">${{shortId(d.archivo)}}</td><td>${{d.localidad||'—'}}</td><td style="font-size:11px;color:var(--ink3)">${{d.alcaldia_cercana?d.alcaldia_cercana.replace('Alcaldía Local de ',''):'—'}}</td><td>${{d.dist_troncal_m}} m</td><td>${{d.dist_alcaldia_m}} m</td><td>${{d.dist_camara_m}} m</td><td>${{pill(d.gravedad)}}</td></tr>`).join('');
  const totalPags=Math.ceil(datos.length/POR_PAG);
  document.getElementById('pagInfo').textContent=`Mostrando ${{Math.min(ini+1,datos.length)}}–${{Math.min(ini+POR_PAG,datos.length)}} de ${{datos.length}}`;
  document.getElementById('badgeTbl').textContent=datos.length+' registros';
  const btns=document.getElementById('pagBtns');btns.innerHTML='';
  const pages=[];if(pagina>1)pages.push('‹');for(let i=1;i<=totalPags;i++)pages.push(i);if(pagina<totalPags)pages.push('›');
  pages.forEach(v=>{{const b=document.createElement('button');b.className='pag-btn'+(v===pagina?' on':'');b.textContent=v==='‹'?'Ant.':v==='›'?'Sig.':v;b.onclick=()=>{{if(v==='‹')pagina--;else if(v==='›')pagina++;else pagina=v;renderTabla(filtrados)}};btns.appendChild(b)}});
}}

// ── Filtros ──
function aplicar(){{
  const loc=document.getElementById('fLoc').value,grav=document.getElementById('fGrav').value;
  filtrados=PUNTOS.filter(d=>(!loc||d.localidad===loc)&&(!grav||d.gravedad===grav));
  pagina=1;renderKPIs(filtrados);buildDanosLayer(filtrados);renderCharts(filtrados);renderTabla(filtrados);
}}

renderKPIs(filtrados);buildDanosLayer(filtrados);renderCharts(filtrados);renderTabla(filtrados);
</script>
</body>
</html>"""

with open(RUTA_SALIDA, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"[4/4] Dashboard guardado en: {RUTA_SALIDA}")
print(f"      Tamaño: {Path(RUTA_SALIDA).stat().st_size // 1024} KB")
print(f"\n✓ Listo — abre dashboard_bogota.html en el navegador\n")