#!/usr/bin/env python3
r"""
Procesa el JSONL del Pilar 2 (inmobiliarias, recolección manual).

Entrada : data/raw/inmobiliarias_fisicas_manual.jsonl
          Un objeto JSON por línea. El usuario lo llena a mano.
Salida  : resumen por pantalla. No escribe archivos de datos.

Columnas esperadas (una por objeto JSON):
  nombre_agencia, direccion_fisica, titulo, precio, moneda, barrio,
  tipo_inmueble, habitaciones, banos, metros_cuadrados, descripcion

Uso:  .venv\Scripts\python.exe scripts\resumen_inmobiliarias.py
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ORIGEN = Path("data/raw/inmobliarias_fisicas_manual.jsonl")

COLUMNAS = [
    "nombre_agencia", "direccion_fisica", "titulo", "precio", "moneda",
    "barrio", "tipo_inmueble", "habitaciones", "banos",
    "metros_cuadrados", "descripcion",
]


def _es_ejemplo(d: dict) -> bool:
    """
    Detecta la línea de ejemplo de la plantilla.

    Se marca con 'EJEMPLO' en varios campos, y detectarla evita que
    contamine las estadísticas cuando el usuario aun no la ha borrado.
    """
    return "EJEMPLO" in (str(d.get("titulo", "")).upper()
                         + str(d.get("nombre_agencia", "")).upper()
                         + str(d.get("descripcion", "")).upper())


def _num(v):
    """Convierte a float tolerando '30 000', '30.000', 30000, null."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    limpio = str(v).replace(" ", "").replace("\u00a0", "")
    for sep in (",", "."):
        if limpio.count(sep) > 1:  # separador de miles
            ultimo = max(limpio.rfind(","), limpio.rfind("."))
            miles = "," if limpio.rfind(",") == ultimo else "."
            dec = "." if miles == "," else ","
            limpio = limpio.replace(miles, "").replace(dec, ".")
            break
    else:
        limpio = limpio.replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return None


def main() -> None:
    print("=" * 84)
    print("PILAR 2 — RESUMEN DE INMOBILIARIAS (recolección manual)")
    print("=" * 84)
    print(f"Archivo: {ORIGEN}")

    if not ORIGEN.exists():
        sys.exit(f"\nNo existe {ORIGEN}.\nCree el archivo a partir de la plantilla "
                 f"con una línea JSON por anuncio.")

    filas, corruptas, ejemplos = [], 0, 0
    for num, linea in enumerate(ORIGEN.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        try:
            d = json.loads(linea)
        except json.JSONDecodeError as e:
            corruptas += 1
            print(f"  LÍNEA {num} inválida: {e}")
            continue
        if _es_ejemplo(d):
            ejemplos += 1
            continue
        filas.append(d)

    n = len(filas)
    print(f"Anuncios reales      : {n}")
    print(f"Líneas corruptas    : {corruptas}")
    print(f"Líneas de ejemplo   : {ejemplos}" + ("  <-- BORRAR antes de usar los datos" if ejemplos else ""))
    print()

    if n == 0:
        print("No hay datos reales todavía.")
        print("El archivo contiene solo la plantilla o está vacío.")
        print()
        print("Para llenarlo: un objeto JSON por línea, por ejemplo:")
        print('  {"nombre_agencia": "Casas Habana", "direccion_fisica": "23 y L, Vedado",')
        print('   "titulo": "Casa en venta Miramar", "precio": 150000, "moneda": "USD",')
        print('   "barrio": "Miramar", "tipo_inmueble": "casa", "habitaciones": 4,')
        print('   "banos": 3, "metros_cuadrados": 300, "descripcion": "..."}')
        return

    # ── Calidad ────────────────────────────────────────────────────────────
    print("CALIDAD DE LOS DATOS")
    print("-" * 84)
    for col in COLUMNAS:
        ok = sum(1 for d in filas if d.get(col) not in (None, ""))
        pct = 100 * ok / n
        barra = "#" * round(30 * ok / n)
        print(f"  {col:22} {ok:>4}/{n:<4} {pct:>5.1f}%  {barra}")
    faltantes = set(COLUMNAS) - set().union(*(d.keys() for d in filas))
    if faltantes:
        print(f"\n  Columnas ausentes en el archivo: {sorted(faltantes)}")
    extra = set().union(*(d.keys() for d in filas)) - set(COLUMNAS)
    if extra:
        print(f"  Columnas no esperadas (se ignoran): {sorted(extra)}")
    print()

    # ── Precio ──────────────────────────────────────────────────────────────
    precios = [_num(d.get("precio")) for d in filas]
    precios = [p for p in precios if p is not None]
    print("PRECIO")
    print("-" * 84)
    if precios:
        ps = sorted(precios)
        print(f"  con precio : {len(ps)}/{n}")
        print(f"  promedio   : {statistics.mean(ps):,.0f}")
        print(f"  mediana    : {statistics.median(ps):,.0f}")
        print(f"  mínimo     : {ps[0]:,.0f}")
        print(f"  máximo     : {ps[-1]:,.0f}")
        for m, c in Counter(d.get("moneda") for d in filas).most_common():
            print(f"  moneda {str(m):6} {c:>4}")
    else:
        print("  sin precios válidos")
    print()

    # ── Por agencia ─────────────────────────────────────────────────────────
    print("POR AGENCIA")
    print("-" * 84)
    por_agencia = {}
    for d, p in zip(filas, [_num(x.get("precio")) for x in filas]):
        por_agencia.setdefault(d.get("nombre_agencia") or "(sin nombre)", []).append(p)
    for ag, ps in sorted(por_agencia.items(), key=lambda x: -len(x[1])):
        validos = [p for p in ps if p is not None]
        med = f"{statistics.median(validos):,.0f}" if validos else "  --"
        print(f"  {ag[:34]:36} n={len(ps):>3}  mediana={med}")
    print()

    # ── Por barrio ──────────────────────────────────────────────────────────
    print("POR BARRIO")
    print("-" * 84)
    for b, c in Counter(d.get("barrio") or "(sin barrio)" for d in filas).most_common():
        print(f"  {str(b)[:34]:36} {c:>4}  {100*c/n:>5.1f}%  {'#' * round(28*c/n)}")
    print()

    # ── Características ─────────────────────────────────────────────────────
    print("CARACTERÍSTICAS")
    print("-" * 84)
    tipos = Counter(d.get("tipo_inmueble") or "(sin tipo)" for d in filas)
    print("  tipo de inmueble:")
    for t, c in tipos.most_common():
        print(f"    {str(t)[:32]:34} {c:>4}  {100*c/n:>5.1f}%")

    m2 = [p for p in (_num(d.get("metros_cuadrados")) for d in filas) if p]
    if m2:
        m2s = sorted(m2)
        print(f"\n  m²: con dato {len(m2)}/{n}  mediana={m2s[len(m2s)//2]:,.0f}  "
              f"min={m2s[0]:,.0f}  max={m2s[-1]:,.0f}")

    hab = [p for p in (_num(d.get("habitaciones")) for d in filas) if p]
    if hab:
        print(f"  habitaciones: con dato {len(hab)}/{n}  mediana={statistics.median(hab):,.0f}")

    # ── Precio por m² ───────────────────────────────────────────────────────
    print()
    print("PRECIO POR m² (requiere precio y superficie)")
    print("-" * 84)
    ratios = []
    for d in filas:
        p, m = _num(d.get("precio")), _num(d.get("metros_cuadrados"))
        if p and m and m > 0:
            ratios.append(p / m)
    if ratios:
        rs = sorted(ratios)
        print(f"  con dato : {len(rs)}/{n}")
        print(f"  mediana  : {statistics.median(rs):,.0f} USD/m²")
        print(f"  mínimo   : {rs[0]:,.0f} USD/m²")
        print(f"  máximo   : {rs[-1]:,.0f} USD/m²")
    else:
        print("  sin datos suficientes (necesita precio y metros_cuadrados)")
    print("=" * 84)


if __name__ == "__main__":
    main()