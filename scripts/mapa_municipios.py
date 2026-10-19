#!/usr/bin/env python3
r"""
Mapa coroplético de La Habana: cantidad de anuncios por municipio.

Entradas:
  geojson la habana.json   (15 municipios de La Habana, DPA)
  data/processed/habana_limpio.jsonl

Salidas:
  graficos/mapa_municipios_habana.png      (mapa estático)
  graficos/mapa_municipios_habana.html     (mapa interactivo con Leaflet)

Colores:
  ROJO  -> municipio con MÁS anuncios
  AZUL  -> municipio con MENOS anuncios
  El resto usa una escala secuencial por cantidad.

Mejoras implementadas:
  - Representative point en vez de centroide (evita etiquetas en municipios
    cóncavos como Habana del Este).
  - Flechas hacia afuera para municipios pequeños cuyas etiquetas no caben
    dentro del contorno (Centro Habana, La Habana Vieja, Regla).
  - Recuadro de "no identificados" dentro del mapa, chiquito, con popup
    interactivo en la versión HTML.
  - Nombres y números más grandes.

No requiere geopandas: los polígonos del GeoJSON se dibujan directamente
con matplotlib. En una conexión lenta evita instalar fiona, shapely y pyproj.

Uso:  .venv\Scripts\python.exe scripts\mapa_municipios.py
"""

import json
import math
import unicodedata
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.lines import Line2D

GEOJSON = Path("geojson la habana.json")
DATOS = Path("data/processed/habana_limpio.jsonl")
SALIDA_PNG = Path("graficos/mapa_municipios_habana.png")
SALIDA_HTML = Path("graficos/mapa_municipios_habana.html")

COLOR_MAX = "#c0392b"   # rojo intenso
COLOR_MIN = "#e8e8e8"   # gris claro
COLOR_CERO = "#dddddd"  # gris para municipios sin anuncios

# Escala intermedia: de gris claro a rojo intenso
ESCALA_COLORES = ["#fde0dd", "#fa9fb5", "#f768a1", "#c51b8a", "#7a0177"]

# Municipios pequeños cuya etiqueta no cabe dentro del contorno.
# Se dibuja el número dentro y una flecha hacia afuera con el nombre.
MUNICIPIOS_CON_FLECHA = {"Centro Habana", "La Habana Vieja", "Regla"}

# Posición de la etiqueta externa para cada municipio con flecha (lon, lat).
# Ajustado manualmente para que no tape otros municipios.
POSICION_EXTERNA = {
    "Centro Habana":     (-82.390, 23.160),
    "La Habana Vieja":   (-82.395, 23.105),
    "Regla":             (-82.290, 23.170),
}


def normalizar(t: str | None) -> str:
    """Minúsculas, sin acentos, sin guiones, espacios colapsados."""
    if not t:
        return ""
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.replace("-", " ").split())


def variantes(t: str) -> list[str]:
    """
    Claves candidatas para emparejar el GeoJSON con el dataset.

    El GeoJSON usa "La Habana Vieja" y el dataset "Habana Vieja"; ambos
    casos aparecen en la misma lista junto a "La Lisa", que sí existe con
    el prefijo en ambas fuentes. Por eso se prueban las tres formas.
    """
    k = normalizar(t)
    return [k, k[3:] if k.startswith("la ") else "la " + k]


def punto_en_poligono(x: float, y: float, anillo: list) -> bool:
    """Algoritmo ray-casting para determinar si un punto está dentro de un anillo."""
    n = len(anillo)
    dentro = False
    j = n - 1
    for i in range(n):
        xi, yi = anillo[i]
        xj, yj = anillo[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            dentro = not dentro
        j = i
    return dentro


def distancia_a_segmento(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    """Distancia euclidiana de un punto a un segmento."""
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def representative_point(anillo: list, n_grid: int = 60) -> tuple[float, float]:
    """
    Encuentra el punto dentro del polígono más alejado de sus bordes.
    Evita etiquetas en municipios cóncavos (ej. Habana del Este).
    """
    xs = [p[0] for p in anillo]
    ys = [p[1] for p in anillo]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)

    mejor = ((minx + maxx) / 2, (miny + maxy) / 2)
    mejor_dist = 0.0

    for i in range(n_grid):
        for j in range(n_grid):
            x = minx + (maxx - minx) * (i + 0.5) / n_grid
            y = miny + (maxy - miny) * (j + 0.5) / n_grid
            if not punto_en_poligono(x, y, anillo):
                continue
            # distancia mínima al borde
            dist = float("inf")
            for k in range(len(anillo)):
                a = anillo[k]
                b = anillo[(k + 1) % len(anillo)]
                d = distancia_a_segmento(x, y, a[0], a[1], b[0], b[1])
                if d < dist:
                    dist = d
            if dist > mejor_dist:
                mejor_dist = dist
                mejor = (x, y)

    return mejor


def anillos(geom):
    """Normaliza Polygon / MultiPolygon a una lista de anillos."""
    tipo = geom.get("type")
    if tipo == "Polygon":
        return geom["coordinates"]
    if tipo == "MultiPolygon":
        return [anillo for poligono in geom["coordinates"] for anillo in poligono]
    return []


def cargar():
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    filas = [json.loads(l) for l in DATOS.read_text(encoding="utf-8").splitlines() if l.strip()]
    conteo = Counter(normalizar(r["municipio"]) for r in filas)

    por_municipio = {}
    for f in gj["features"]:
        nombre = f["properties"]["municipality"]
        n = 0
        for k in variantes(nombre):
            if k in conteo:
                n = conteo[k]
                break
        por_municipio[nombre] = n

    no_identificados = (conteo.get("otro", 0) + conteo.get("no identificado", 0))

    return gj["features"], por_municipio, conteo, len(filas), no_identificados


def main() -> None:
    features, por_mun, conteo, total, no_identificados = cargar()
    identificados = total - no_identificados

    con_datos = {m: n for m, n in por_mun.items() if n > 0}
    municipio_max = max(con_datos, key=con_datos.get)
    municipio_min = min(con_datos, key=con_datos.get)
    municipio_cero = [m for m, n in por_mun.items() if n == 0]

    print("=" * 72)
    print("MAPA DE LA HABANA — ANUNCIOS POR MUNICIPIO")
    print("=" * 72)
    print(f"Total de anuncios      : {total}")
    print(f"Con municipio (mapa)   : {identificados}")
    print(f"Sin municipio (ajeno)  : {no_identificados}")
    print()
    print(f"  MÁS anuncios  : {municipio_max} ({con_datos[municipio_max]})  -> ROJO")
    print(f"  MENOS anuncios : {municipio_min} ({con_datos[municipio_min]})  -> AZUL")
    if municipio_cero:
        print(f"  Sin ningún anuncio: {', '.join(municipio_cero)}  -> gris")
    print()

    # ── Figura ─────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(22, 22))
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0.06, 0.24, 0.88, 0.70])

    escala = Normalize(vmin=0, vmax=max(con_datos.values()))
    cmap = LinearSegmentedColormap.from_list("playa", ESCALA_COLORES)

    puntos_etiqueta = {}

    for f in features:
        nombre = f["properties"]["municipality"]
        n = por_mun.get(nombre, 0)
        if nombre == municipio_max:
            color, borde, lw = COLOR_MAX, "#7f1414", 2.0
        elif nombre == municipio_min:
            color, borde, lw = COLOR_MIN, "#0d3b66", 2.0
        elif n == 0:
            color, borde, lw = COLOR_CERO, "#999999", 1.0
        else:
            color, borde, lw = cmap(escala(n)), "#555555", 0.8

        anillos_list = anillos(f["geometry"])
        for anillo in anillos_list:
            xs = [p[0] for p in anillo]
            ys = [p[1] for p in anillo]
            ax.add_patch(
                MplPolygon(list(zip(xs, ys)), closed=True, facecolor=color,
                           edgecolor=borde, linewidth=lw, zorder=2)
            )

        # Representative point para el centro de etiquetado
        rp = representative_point(anillos_list[0])
        puntos_etiqueta[nombre] = rp

        # ── Etiquetas ──────────────────────────────────────────────────────
        if nombre in MUNICIPIOS_CON_FLECHA and nombre in POSICION_EXTERNA:
            # Número dentro del contorno
            ax.text(rp[0], rp[1], str(n), ha="center", va="center", zorder=6,
                    fontsize=16, fontweight="bold", color="#000000")
            # Nombre fuera, con flecha
            ex, ey = POSICION_EXTERNA[nombre]
            ax.annotate(
                nombre,
                xy=(rp[0], rp[1]),
                xytext=(ex, ey),
                fontsize=11, fontweight="bold", color="#000000",
                ha="center", va="center",
                arrowprops=dict(arrowstyle="->", color="#333333", lw=1.8,
                                connectionstyle="arc3,rad=0.15"),
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#666666", alpha=0.9),
                zorder=7,
            )
        else:
            # Número + nombre dentro del contorno
            ax.text(rp[0], rp[1] + 0.0035, str(n), ha="center", va="center", zorder=6,
                    fontsize=16, fontweight="bold", color="#000000")
            ax.text(rp[0], rp[1] - 0.0075, nombre, ha="center", va="center", zorder=6,
                    fontsize=10.5, fontweight="normal", color="#000000",
                    style="italic")

    ax.set_xlim(-82.56, -82.05)
    ax.set_ylim(22.92, 23.20)
    ax.set_aspect(1 / math.cos(math.radians(23.05)))
    ax.set_xlabel("Longitud (°)")
    ax.set_ylabel("Latitud (°)")
    ax.set_title(
        "Anuncios de venta de vivienda por municipio — La Habana\n"
        f"{identificados} anuncios con municipio identificado de {total} · "
        f"escala por cantidad",
        fontsize=16, pad=16,
    )
    ax.grid(alpha=0.15, linestyle=":")
    ax.set_axisbelow(True)

    # Leyenda de los dos extremos
    leyenda = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor=COLOR_MAX,
               markersize=16, label=f"Más anuncios: {municipio_max} ({con_datos[municipio_max]})"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor=COLOR_MIN,
               markersize=16, label=f"Menos anuncios: {municipio_min} ({con_datos[municipio_min]})"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#fdd9b5",
               markersize=16, label="Escala secuencial (menos → más)"),
    ]
    if municipio_cero:
        leyenda.append(
            Line2D([0], [0], marker="s", color="w", markerfacecolor=COLOR_CERO,
                   markersize=16, label=f"Sin anuncios: {', '.join(municipio_cero)}")
        )
    ax.legend(handles=leyenda, loc="lower left", fontsize=10,
              framealpha=0.95, borderpad=0.9)

    # ── Apartado FUERA del mapa: franja inferior de la figura ──────────────
    pct = 100 * no_identificados / total
    fig.text(0.06, 0.175, "MUNICIPIOS NO IDENTIFICADOS", fontsize=13,
             fontweight="bold", color="#7a5c00", ha="left", va="center")
    fig.text(0.06, 0.128,
             f"Anuncios sin municipio asignado: {no_identificados} de {total}  ({pct:.1f}%)",
             fontsize=12, ha="left", va="center", color="#333333")
    fig.text(0.06, 0.092,
             "Motivo: el portal publica 'Plaza' (nombre coloquial) y el campo municipio\n"
             "queda vacio en 3 casos con contradiccion entre la API y el texto del anuncio.\n"
             "Esos 3 se excluyeron del conteo municipal para no inflar el municipio.",
             fontsize=9.5, ha="left", va="center", color="#555555", style="italic")
    fig.text(0.06, 0.030,
             f"Comprobación: {identificados} identificados + {no_identificados} no identificados "
             f"= {total} anuncios del dataset.",
             fontsize=10, ha="left", va="center", color="#7a5c00", family="monospace")

    SALIDA_PNG.parent.mkdir(exist_ok=True)
    fig.savefig(SALIDA_PNG, dpi=150, facecolor="white")
    plt.close(fig)
    print(f"Mapa PNG guardado: {SALIDA_PNG}")

    # ── HTML interactivo con Leaflet ───────────────────────────────────────
    generar_html(features, por_mun, total, no_identificados, identificados,
                 municipio_max, municipio_min, municipio_cero, con_datos)
    print(f"Mapa HTML guardado: {SALIDA_HTML}")


def generar_html(features, por_mun, total, no_identificados, identificados,
                 municipio_max, municipio_min, municipio_cero, con_datos) -> None:
    """Genera un HTML interactivo con Leaflet.js (popup al hacer clic)."""
    # Preparar datos GeoJSON con conteos
    geo_data = json.loads(GEOJSON.read_text(encoding="utf-8"))
    for f in geo_data["features"]:
        nombre = f["properties"]["municipality"]
        n = por_mun.get(nombre, 0)
        f["properties"]["anuncios"] = n

    geo_json_str = json.dumps(geo_data, ensure_ascii=False)

    # Texto del popup
    pct = 100 * no_identificados / total
    popup_text = (
        f"<b>Municipios no identificados</b><br>"
        f"Anuncios sin municipio asignado: {no_identificados} de {total} ({pct:.1f}%)<br>"
        f"<i>Motivo: el portal publica 'Plaza' (nombre coloquial) y el campo municipio "
        f"queda vacio en 3 casos con contradiccion entre la API y el texto del anuncio. "
        f"Esos 3 se excluyeron del conteo municipal para no inflar el municipio.</i><br>"
        f"<br>Comprobación: {identificados} identificados + {no_identificados} no identificados "
        f"= {total} anuncios del dataset."
    )

    # Color del máximo (rojo intenso) y del mínimo (gris claro)
    color_max = "#c0392b"
    color_min = "#e8e8e8"
    # Puntos intermedios de la escala (de más claro a más intenso)
    puntos_escala = ["#fde0dd", "#fa9fb5", "#f768a1", "#c51b8a", "#7a0177"]

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mapa de Anuncios por Municipio — La Habana</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  body {{ margin: 0; padding: 0; }}
  #map {{ width: 100vw; height: 100vh; }}
  .map-label {{
    background: transparent;
    border: none;
    box-shadow: none;
    font-size: 11px;
    font-weight: bold;
    color: #1a1a1a;
    text-align: center;
    text-shadow: 1px 1px 2px #fff, -1px -1px 2px #fff, 1px -1px 2px #fff, -1px 1px 2px #fff;
    pointer-events: none;
  }}
  .map-label-max {{
    color: #7b1b1b;
    font-size: 13px;
  }}
  .map-label-min {{
    color: #555;
    font-size: 13px;
  }}
  .info-box {{
    position: absolute;
    bottom: 20px;
    right: 20px;
    z-index: 1000;
    background: #fdf6e3;
    border: 1.5px solid #b58900;
    border-radius: 8px;
    padding: 8px 12px;
    max-width: 200px;
    cursor: pointer;
    font-family: monospace;
    font-size: 11px;
    transition: all 0.3s ease;
  }}
  .info-box.expanded {{
    max-width: 450px;
    padding: 16px 20px;
    font-size: 13px;
  }}
  .info-box h3 {{
    margin: 0 0 4px 0;
    color: #7a5c00;
    font-size: 12px;
  }}
  .info-box.expanded h3 {{
    font-size: 15px;
  }}
  .info-detail {{
    display: none;
  }}
  .info-box.expanded .info-detail {{
    display: block;
  }}
  .info-toggle {{
    color: #999;
    font-size: 10px;
    margin-top: 4px;
  }}
  .legend {{
    position: absolute;
    bottom: 20px;
    left: 20px;
    z-index: 1000;
    background: white;
    border: 1px solid #999;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 12px;
    font-family: monospace;
  }}
  .legend h4 {{
    margin: 0 0 6px 0;
    font-size: 12px;
  }}
  .legend-row {{
    display: flex;
    align-items: center;
    margin: 3px 0;
  }}
  .legend-swatch {{
    width: 18px;
    height: 14px;
    border: 1px solid #666;
    margin-right: 8px;
  }}
</style>
</head>
<body>
<div id="map"></div>
<div class="legend">
  <h4>Anuncios por municipio</h4>
  <div class="legend-row"><div class="legend-swatch" style="background:{color_max}"></div>Más: {municipio_max} ({max(con_datos.values())})</div>
  <div class="legend-row"><div class="legend-swatch" style="background:{color_min}"></div>Menos: {municipio_min} ({min(con_datos.values())})</div>
  <div class="legend-row"><div class="legend-swatch" style="background:#dddddd"></div>Sin anuncios</div>
</div>
<div class="info-box" id="infoBox" onclick="this.classList.toggle('expanded')">
  <h3>MUNICIPIOS NO IDENTIFICADOS</h3>
  <div>{no_identificados} de {total} ({pct:.1f}%)</div>
  <div class="info-detail">{popup_text}</div>
  <div class="info-toggle">Clic para ampliar</div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const geoData = {geo_json_str};

// Centrar en La Habana con zoom 11 y limitar navegacion
const map = L.map('map', {{
  center: [23.1136, -82.3666],
  zoom: 11,
  minZoom: 9,
  maxZoom: 15,
  maxBounds: [[22.80, -82.80], [23.45, -81.80]],
  maxBoundsViscosity: 0.8
}});

L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '&copy; OpenStreetMap contributors'
}}).addTo(map);

const maxVal = {max(con_datos.values())};
const minVal = {min(con_datos.values())};
const maxName = "{municipio_max}";
const minName = "{municipio_min}";

// Escala de colores: gris claro (min) -> rojo intenso (max)
const escala = {puntos_escala};

function getColor(n) {{
  if (n === 0) return '#dddddd';
  if (n === maxVal) return '{color_max}';
  if (n === minVal) return '{color_min}';
  // interpolacion lineal en la escala
  const t = (n - minVal) / (maxVal - minVal);
  const idx = Math.min(Math.floor(t * escala.length), escala.length - 1);
  return escala[idx];
}}

function style(feature) {{
  return {{
    fillColor: getColor(feature.properties.anuncios),
    weight: 1.5,
    opacity: 1,
    color: '#666',
    fillOpacity: 0.8
  }};
}}

L.geoJSON(geoData, {{
  style: style,
  onEachFeature: function(feature, layer) {{
    const n = feature.properties.anuncios;
    const name = feature.properties.municipality;
    // Popup al hacer clic
    layer.bindPopup(`<b>${{name}}</b><br>Anuncios: ${{n}}`);
    // Etiqueta PERMANENTE con el nombre (sin hover)
    const center = layer.getBounds().getCenter();
    let cssClass = 'map-label';
    if (name === maxName) cssClass += ' map-label-max';
    if (name === minName) cssClass += ' map-label-min';
    L.marker(center, {{
      icon: L.divIcon({{
        className: cssClass,
        html: name,
        iconSize: null,
        iconAnchor: [0, 0]
      }}),
      interactive: false
    }}).addTo(map);
  }}
}}).addTo(map);
</script>
</body>
</html>
"""
    SALIDA_HTML.parent.mkdir(exist_ok=True)
    SALIDA_HTML.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
