#!/usr/bin/env python3
r"""
Limpieza del Pilar 1 para toda La Habana (no solo Playa).

Aplica exactamente las mismas reglas que scripts/limpieza_datos.py, pero
sin el filtro de municipio: aquí entra toda la ciudad.

Entrada : data/raw/revolico_ventas.jsonl
Salida  : data/processed/habana_limpio.jsonl

Segmentos de mercado (umbros de La Habana, distintos a los de Playa):
    popular  < 50,000 USD
    medio    50,000 - 200,000 USD
    lujo     > 200,000 USD

Uso:  .venv\Scripts\python.exe scripts\limpiar_habana.py
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from extraer_variables import extraer_barrio  # noqa: E402
from limpieza_datos import es_no_vivienda  # noqa: E402  (titulo manda)
from scraper_revolico import inferir_tipo_inmueble, normalizar_texto  # noqa: E402

ORIGEN = Path("data/raw/revolico_ventas.jsonl")
DESTINO = Path("data/processed/habana_limpio.jsonl")

PRECIO_MINIMO_USD = 1_000
PRECIO_LUXO_TOP_USD = 500_000   # a partir de aqui se conserva como "lujo_top"

SEGMENTOS = [
    ("popular",  0,       50_000),
    ("medio",    50_000,  200_000),
    ("lujo",     200_000, 500_000),
    ("lujo_top", 500_000, float("inf")),
]

MUNICIPIOS_LA_HABANA = [
    "la lisa", "diez de octubre", "marianao", "boyeros", "plaza de la revolucion",
    "arroyo naranjo", "playa", "centro habana", "habana vieja", "cotorro",
    "habana del este", "san miguel del padron", "guanabacoa", "cerro", "regla",
]

COLUMNAS = [
    "titulo", "precio_usd", "moneda", "municipio", "barrio", "municipio_bruto",
    "provincia", "subcategoria", "segmento_mercado", "tipo_inmueble",
    "habitaciones", "banos", "banos_inferido", "cantidad_palabras",
    "es_intermediario", "menciona_urgencia_viaje",
    "menciona_problemas_estructurales", "descripcion", "url",
]


def clasificar_segmento(precio: float) -> str:
    for nombre, minimo, maximo in SEGMENTOS:
        if minimo <= precio < maximo:
            return nombre
    return "lujo"


def normalizar_municipio(bruto: str | None) -> str:
    """Normaliza a uno de los 15 municipios; si no, 'otro'."""
    if not bruto:
        return "otro"
    n = normalizar_texto(bruto).strip()
    for m in MUNICIPIOS_LA_HABANA:
        if m in n:
            return m.title()
    return "otro"


def es_intermediario(f: dict) -> bool:
    t = normalizar_texto(f"{f.get('titulo') or ''} {f.get('descripcion') or ''}")
    return any(normalizar_texto(k) in t
               for k in ("inmobiliaria", "agencia", "gestor", "realtor"))


def main() -> None:
    print("=" * 84)
    print("LIMPIEZA DEL PILAR 1 — TODA LA HABANA")
    print("=" * 84)
    print(f"Origen : {ORIGEN}")
    print(f"Destino: {DESTINO}")
    print(f"Umbral de descarte: precio < {PRECIO_MINIMO_USD:,} USD o sin precio")
    print(f"Segmento lujo_top  : precio >= {PRECIO_LUXO_TOP_USD:,} USD (se conserva)")
    print()

    filas = [json.loads(l) for l in ORIGEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    total_inicial = len(filas)

    eliminados = Counter()
    motivos = Counter()
    outliers_alto = []
    supervivientes = []

    for f in filas:
        # 1) No es vivienda (el título manda)
        no_viv, motivo = es_no_vivienda(f)
        if no_viv:
            eliminados["no_vivienda_o_demanda"] += 1
            motivos[motivo] += 1
            continue

        # 2) Precio ausente
        precio = f.get("precio")
        if not isinstance(precio, (int, float)):
            eliminados["precio_ausente"] += 1
            continue

        # 3) Moneda no USD: en este dataset los valores en CUP son
        #    artefactos de scraping (números de teléfono), no precios.
        if f.get("moneda") != "USD":
            eliminados["moneda_no_usd"] += 1
            continue

        # 4) Precio fuera de rango
        if precio < PRECIO_MINIMO_USD:
            eliminados["precio_irreal_bajo"] += 1
            continue

        # 5) Reclasificar tipo con la lógica corregida (orden de claves)
        texto = normalizar_texto(
            f"{f.get('titulo') or ''} {f.get('subcategoria') or ''} "
            f"{f.get('descripcion') or ''}"
        )
        registro = {
            "titulo": f.get("titulo"),
            "precio_usd": float(precio),
            "moneda": f.get("moneda"),
            "municipio": normalizar_municipio(f.get("municipio_bruto") or f.get("municipio")),
            "barrio": extraer_barrio(f.get("titulo") or "", f.get("descripcion") or ""),
            "municipio_bruto": f.get("municipio_bruto"),
            "provincia": f.get("provincia"),
            "subcategoria": f.get("subcategoria"),
            "segmento_mercado": clasificar_segmento(precio),
            "tipo_inmueble": inferir_tipo_inmueble(texto),
            "habitaciones": f.get("habitaciones"),
            "banos": f.get("banos"),
            "banos_inferido": f.get("banos_inferido", False),
            "cantidad_palabras": f.get("cantidad_palabras"),
            "es_intermediario": es_intermediario(f),
            "menciona_urgencia_viaje": f.get("menciona_urgencia_viaje", False),
            "menciona_problemas_estructurales": f.get("menciona_problemas_estructurales", False),
            "descripcion": f.get("descripcion"),
            "url": f.get("url"),
        }
        supervivientes.append(registro)

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8") as fh:
        for r in supervivientes:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # ── Resumen ────────────────────────────────────────────────────────────
    n = len(supervivientes)
    print("ELIMINACIONES POR MOTIVO")
    print("-" * 84)
    for m, c in eliminados.most_common():
        print(f"  {m:28} {c:>5}  {100*c/total_inicial:>5.1f}%")
    print(f"  {'TOTAL ELIMINADOS':28} {sum(eliminados.values()):>5}")
    print(f"  {'SUPERVIVIENTES':28} {n:>5}  {100*n/total_inicial:>5.1f}%")
    print()

    print("MOTIVOS DE EXCLUSIÓN (top 15)")
    print("-" * 84)
    for m, c in motivos.most_common(15):
        print(f"  {str(m):44} {c:>4}")
    print()

    print("MUESTRAS PEQUEÑAS: ESTADÍSTICA DESCRIPTIVA SOLAMENTE")
    print("-" * 84)
    print("Los segmentos con n < 30 no admiten inferencia estadística. No se")
    print("aplican pruebas de significancia ni clustering: solo descripción.")
    print()
    N_MIN = 30
    for nombre, _, _ in SEGMENTOS:
        grupo = [r for r in supervivientes if r["segmento_mercado"] == nombre]
        if len(grupo) >= N_MIN or not grupo:
            continue
        ps = sorted(r["precio_usd"] for r in grupo)
        print(f"  SEGMENTO {nombre.upper()}   n = {len(grupo)}   (n < {N_MIN}: descriptivo)")
        print(f'    {"cantidad":22} {len(grupo)}')
        print(f'    {"mediana":22} {statistics.median(ps):>12,.0f} USD')
        print(f'    {"promedio":22} {statistics.mean(ps):>12,.0f} USD')
        print(f'    {"precio minimo":22} {ps[0]:>12,.0f} USD')
        print(f'    {"precio maximo":22} {ps[-1]:>12,.0f} USD')
        pers = sorted(r["precio_usd"] / len(ps) * 100 for r in grupo)
        print(f'    {"participacion":22} {100*len(grupo)/n:>11.1f}% del total')
        print(f'    {"tipo de inmueble":22}')
        for t, c in Counter(r["tipo_inmueble"] for r in grupo).most_common():
            print(f'      {t:20} {c:>3}  ({100*c/len(grupo):.0f}%)')
        print(f'    {"barrios donde se concentran":22}')
        b = Counter(r["barrio"] for r in grupo).most_common()
        for barrio, c in b:
            print(f'      {barrio:20} {c:>3}  ({100*c/len(grupo):.0f}%)')
        print()

    print("SEGMENTOS DE MERCADO")
    print("-" * 84)
    print(f'{"segmento":12} {"n":>5} {"mediana":>12} {"promedio":>12} {"min":>10} {"max":>12}')
    for nombre, _, _ in SEGMENTOS:
        grupo = [r for r in supervivientes if r["segmento_mercado"] == nombre]
        if not grupo:
            print(f"{nombre:12} {0:>5}")
            continue
        ps = sorted(r["precio_usd"] for r in grupo)
        print(f"{nombre:12} {len(grupo):>5} {statistics.median(ps):>12,.0f} "
              f"{statistics.mean(ps):>12,.0f} {ps[0]:>10,.0f} {ps[-1]:>12,.0f}")
    print(f"{'TOTAL':12} {n:>5}")
    print()

    print("TIPO DE INMUEBLE")
    print("-" * 84)
    for t, c in Counter(r["tipo_inmueble"] for r in supervivientes).most_common():
        print(f"  {t:26} {c:>5}  {100*c/n:>5.1f}%  {'#' * round(30*c/n)}")
    print()

    print("MUNICIPIO")
    print("-" * 84)
    for m, c in Counter(r["municipio"] for r in supervivientes).most_common():
        print(f"  {m:26} {c:>5}  {100*c/n:>5.1f}%  {'#' * round(30*c/n)}")
    print()

    inter = sum(1 for r in supervivientes if r["es_intermediario"])
    print("INTERMEDIARIOS")
    print("-" * 84)
    print(f"  es_intermediario=True : {inter:>5}  ({100*inter/n:.1f}%)")
    print(f"  es_intermediario=False: {n - inter:>5}  ({100*(n-inter)/n:.1f}%)")
    print()
    print("=" * 84)
    print(f"Archivo generado: {DESTINO}  ({n} líneas, {len(COLUMNAS)} columnas)")


if __name__ == "__main__":
    main()