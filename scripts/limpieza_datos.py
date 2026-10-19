#!/usr/bin/env python3
r"""
Limpieza y filtrado del dataset de Revolico para el estudio de Playa.

Lee data/raw/revolico_ventas.jsonl (NUNCA lo modifica) y produce
data/processed/playa_limpio.csv.

Pipeline:
  1. Descarta anuncios que no son viviendas (servicios, alquiler,eous).
  2. Descarta anuncios cuya moneda no es USD (no convertible con fiabilidad).
  3. Descarta precios basura (< 1.000 USD) y outliers altos (> 2.000.000 USD).
  4. Filtra municipio == "Playa".
  5. Clasifica el segmento de mercado: popular / medio / lujo.

Uso:  .venv\Scripts\python.exe scripts\limpieza_datos.py
"""

import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ORIGEN = Path("data/raw/revolico_ventas.jsonl")
DESTINO = Path("data/processed/playa_limpio.csv")

# Palabras que indican que el anuncio NO es una vivienda en venta.
#
# IMPORTANTE: se evaluan el TITULO y la DESCRIPCION conriterios distintos.
# En la descripcion, un anuncio de venta legitimo puede decir "construccion de
# calidad", "inmobiliaria Casas Habana" o "muebles incluidos", asi que ahi
# solo se excluyen terms inequivocos (alquiler,cementerio, etc.).
#
# Un filtro uniforme sobre la descripcion descarto 59 viviendas legitimas de
# Playa, incluidas las casas de lujo. Por eso el titulo manda.
PALABRAS_TITULO = [
    "constructora", "servicios", "reparaciones", "materiales", "renta",
    "alquiler", "alquilo", "busco local", "compra venta", "compra-venta",
    "inmobiliaria", "herrero", "electricista", "plomero", "pintor",
    "carpinteria", "fotografia", "grabacion", "eventos", "catering",
    "taxi", "cursos", "equipos", "muebles", "electrodomesticos",
    "puzles", "trampolin", "boveda", "osario", "panteon", "cementerio",
    "usufructo", "permuta", "marqueteria", "marmol", "azulejos",
    "pinturas", "reparto de paneles", "foodtruck", "cocina de regimen",
    "plastico", "bebes", "zapatos", "mascotas", "libreria", "camas",
    "mesas", "repisa", "espejo", "sillon", "panel solar", "cristal",
    "plomeria", "electricidad",
]

# Solo en descripcion: terminos que nunca aparecen en una venta de vivienda.
PALABRAS_DESCRIPCION = [
    "se renta", "se alquila", "renta de espacio", "renta de portal",
    "renta de garage", "renta de oficinas", "renta de almacen",
    "cementerio de colon", "renta mensual", "alquiler vacacional",
    "tengo espacio para rentar", "arrendamiento",
]

# Anuncios que son Demand, no Oferta.
PATRONES_DEMANDA = [
    r"\bse busca\b",
    r"\bbusco\b",
    r"\bnecesito (?:vender|buscar|comprar)\b",
    r"\bcompro\b",
    r"\bquiero (?:vender|comprar)\b",
]

# Rangos de precio en USD. Debajo del minimo no hay vivienda.
PRECIO_MINIMO_USD = 1_000
PRECIO_MAXIMO_USD = 2_000_000

# Segmentos de mercado (USD)
SEGMENTOS = [
    ("popular", 0, 70_000),
    ("medio", 70_000, 200_000),
    ("lujo", 200_000, float("inf")),
]

CAMPOS_SALIDA = [
    "titulo", "precio_usd", "moneda", "segmento_mercado", "municipio",
    "subcategoria", "tipo_inmueble", "habitaciones", "banos", "banos_inferido",
    "cantidad_palabras", "menciona_urgencia_viaje",
    "menciona_problemas_estructurales", "descripcion", "url",
]


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar palabras clave."""
    if not texto:
        return ""
    import unicodedata
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.lower()


def clasificar_segmento(precio: float) -> str:
    for nombre, minimo, maximo in SEGMENTOS:
        if minimo <= precio < maximo:
            return nombre
    return "lujo"


def es_no_vivienda(registro: dict) -> tuple[bool, str | None]:
    """
    Determina si el anuncio no es una vivienda en venta.

    El TITULO manda: si aparece un termino inequivoco ahi, se excluye.
    En la DESCRIPCION solo se excluyen terminos de alquiler, porque un
    anuncio de venta legitimo puede mencionar "construccion", "inmobiliaria"
    o "muebles" sin dejar de ser una casa en venta.

    Retorna (es_no_vivienda, motivo).
    """
    import re

    titulo = normalizar(registro.get("titulo") or "")
    descripcion = normalizar(registro.get("descripcion") or "")

    for palabra in PALABRAS_TITULO:
        if palabra in titulo:
            return True, f"titulo:{palabra}"

    for palabra in PALABRAS_DESCRIPCION:
        if palabra in descripcion:
            return True, f"descripcion:{palabra}"

    for patron in PATRONES_DEMANDA:
        if re.search(patron, titulo):
            return True, f"demanda:{patron}"

    return False, None


def cargar() -> list[dict]:
    if not ORIGEN.exists():
        sys.exit(f"No existe {ORIGEN}")
    filas = []
    for linea in ORIGEN.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        try:
            filas.append(json.loads(linea))
        except json.JSONDecodeError:
            continue
    return filas


def main() -> None:
    filas = cargar()
    total_inicial = len(filas)
    print("=" * 78)
    print("LIMPIEZA DE DATOS — Revolico / Playa")
    print("=" * 78)
    print(f"Origen        : {ORIGEN}")
    print(f"Destino       : {DESTINO}")
    print(f"Registros leídos: {total_inicial}")
    print()

    # Contadores de eliminación por motivo
    eliminados = Counter()
    detalle_motivos = Counter()
    supervivientes = []

    for f in filas:
        # 1. No es vivienda
        es_no_viv, motivo = es_no_vivienda(f)
        if es_no_viv:
            eliminados["no_vivienda_o_demanda"] += 1
            detalle_motivos[motivo] += 1
            continue

        # 2. Precio ausente
        precio = f.get("precio")
        if not isinstance(precio, (int, float)):
            eliminados["precio_ausente"] += 1
            continue

        # 3. Moneda no USD (no convertible con fiabilidad: los valores en CUP
        #    del dataset son artefactos de scraping, p.ej. teléfonos)
        moneda = f.get("moneda")
        if moneda != "USD":
            eliminados["moneda_no_usd"] += 1
            continue

        # 4. Precio basura
        if precio < PRECIO_MINIMO_USD:
            eliminados["precio_irreal_bajo"] += 1
            continue

        if precio > PRECIO_MAXIMO_USD:
            eliminados["precio_irreal_alto"] += 1
            continue

        # 5. Filtro Playa
        if f.get("municipio") != "Playa":
            eliminados["fuera_de_playa"] += 1
            continue

        supervivientes.append(f)

    # --- Escritura del CSV ---
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CAMPOS_SALIDA, extrasaction="ignore")
        writer.writeheader()
        for f in supervivientes:
            precio = f["precio"]
            fila = {c: f.get(c) for c in CAMPOS_SALIDA}
            fila["precio_usd"] = precio
            fila["segmento_mercado"] = clasificar_segmento(precio)
            writer.writerow(fila)

    # --- Resumen ---
    print("ELIMINACIONES POR MOTIVO")
    print("-" * 78)
    for motivo, n in eliminados.most_common():
        print(f"  {motivo:30} {n:>5}")

    total_eliminados = sum(eliminados.values())
    print(f"  {'TOTAL ELIMINADOS':30} {total_eliminados:>5}")
    print(f"  {'SUPERVIVIENTES (Playa)':30} {len(supervivientes):>5}")
    print()

    print("MOTIVOS DE EXCLUSIÓN (detalle de no_vivienda)")
    print("-" * 78)
    for motivo, n in detalle_motivos.most_common(20):
        print(f"  {motivo:40} {n:>4}")
    print()

    # --- Segmentos ---
    print("SEGMENTOS DE MERCADO (Playa limpio)")
    print("-" * 78)
    if not supervivientes:
        print("  Sin datos.")
        return

    por_seg = {}
    for nombre, _, _ in SEGMENTOS:
        grupo = [f for f in supervivientes if clasificar_segmento(f["precio"]) == nombre]
        if grupo:
            precios = sorted(f["precio"] for f in grupo)
            por_seg[nombre] = (len(grupo), precios)

    print(f'{"segmento":12} {"n":>5} {"promedio":>14} {"mediana":>14} {"min":>12} {"max":>14}')
    for nombre, _, _ in SEGMENTOS:
        if nombre not in por_seg:
            print(f"{nombre:12} {0:>5}")
            continue
        n, precios = por_seg[nombre]
        print(
            f"{nombre:12} {n:>5} {statistics.mean(precios):>14,.0f} "
            f"{statistics.median(precios):>14,.0f} {precios[0]:>12,.0f} {precios[-1]:>14,.0f}"
        )
    print()

    total_playa = len(supervivientes)
    print(f"  Total Playa: {total_playa}")
    print(f"  Porcentaje del dataset original: {100*total_playa/total_inicial:.1f}%")
    print("=" * 78)


if __name__ == "__main__":
    main()
