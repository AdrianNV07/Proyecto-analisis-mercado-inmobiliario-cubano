#!/usr/bin/env python3
r"""
Resumen estadístico del dataset de Revolico.

No usa pandas a propósito: el .venv solo tiene requests, beautifulsoup4 y
lxml instalados, y la instalación de pandas excedió el tiempo disponible.
Se calcula con la librería estándar, que basta para estos recuentos.

Uso:  .venv\Scripts\python.exe scripts\resumen_revolico.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

ARCHIVO = Path("data/raw/revolico_ventas.jsonl")


def cargar() -> list[dict]:
    if not ARCHIVO.exists():
        sys.exit(f"No existe {ARCHIVO}")
    filas = []
    corruptas = 0
    for linea in ARCHIVO.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            continue
        try:
            filas.append(json.loads(linea))
        except json.JSONDecodeError:
            corruptas += 1
    if corruptas:
        print(f"[aviso] {corruptas} linea(s) corrupta(s) ignorada(s)")
    return filas


def pct(n: int, total: int) -> str:
    return f"{100 * n / total:5.1f}%" if total else "  n/a"


def barra(n: int, total: int, ancho: int = 24) -> str:
    if not total:
        return ""
    return "#" * max(0, round(ancho * n / total))


def main() -> None:
    filas = cargar()
    total = len(filas)
    print("=" * 68)
    print("RESUMEN DEL DATASET DE REVOLICO")
    print("=" * 68)
    print(f"Archivo          : {ARCHIVO}")
    print(f"Registros        : {total}")
    print(f"URLs únicas      : {len(set(r.get('url') for r in filas))}")
    print(f"Campos por reg.  : {len(filas[0]) if filas else 0}")
    print()

    # --- Integridad de duplicados ---
    duplicados = total - len(set(r.get("url") for r in filas))
    print("-" * 68)
    print("INTEGRIDAD")
    print("-" * 68)
    print(f"Duplicados residuales : {duplicados}")
    print()

    # --- Cobertura de subcategorías ---
    print("-" * 68)
    print("SUBCATEGORÍAS (de dónde viene cada anuncio)")
    print("-" * 68)
    subs = Counter((r.get("subcategoria") or "(null)").strip() for r in filas)
    for k, v in subs.most_common():
        print(f"  {k:34} {v:5}  {pct(v, total)}  {barra(v, total)}")
    print()

    # --- tipo_inmueble ---
    print("-" * 68)
    print("TIPO DE INMUEBLE")
    print("-" * 68)
    tipos = Counter((r.get("tipo_inmueble") or "(null)") for r in filas)
    for k, v in tipos.most_common():
        print(f"  {k:34} {v:5}  {pct(v, total)}  {barra(v, total)}")
    print()

    # --- urgencia de viaje ---
    print("-" * 68)
    print("URGENCIA DE VIAJE (menciona_urgencia_viaje)")
    print("-" * 68)
    urg = sum(1 for r in filas if r.get("menciona_urgencia_viaje"))
    print(f"  True  {urg:5}  {pct(urg, total)}  {barra(urg, total)}")
    print(f"  False {total - urg:5}  {pct(total - urg, total)}")
    print()
    print("  Desglose por subcategoría:")
    for sub, n in subs.most_common():
        grupo = [r for r in filas if ((r.get("subcategoria") or "(null)").strip()) == sub]
        u = sum(1 for r in grupo if r.get("menciona_urgencia_viaje"))
        print(f"    {sub:32} {u:4}/{n:4}  {pct(u, len(grupo))}")
    print()

    # --- problemas estructurales ---
    prob = sum(1 for r in filas if r.get("menciona_problemas_estructurales"))
    print("-" * 68)
    print("PROBLEMAS ESTRUCTURALES")
    print("-" * 68)
    print(f"  True  {prob:5}  {pct(prob, total)}  {barra(prob, total)}")
    print()

    # --- baños ---
    print("-" * 68)
    print("BAÑOS")
    print("-" * 68)
    nulos_b = sum(1 for r in filas if r.get("banos") is None)
    inf_b = sum(1 for r in filas if r.get("banos_inferido"))
    exp_b = sum(1 for r in filas if r.get("banos") is not None and not r.get("banos_inferido"))
    print(f"  Nulos            {nulos_b:5}  {pct(nulos_b, total)}")
    print(f"  Con dato (total) {total - nulos_b:5}  {pct(total - nulos_b, total)}")
    print(f"    explícitos     {exp_b:5}  {pct(exp_b, total)}   <- dato sólido")
    print(f"    inferidos (=1) {inf_b:5}  {pct(inf_b, total)}   <- supuesto por singular")
    print()
    valores = Counter(r["banos"] for r in filas if r.get("banos") is not None)
    print("  Distribución:")
    for k, v in sorted(valores.items()):
        print(f"    {k:3} baños  {v:5}  {pct(v, total - nulos_b)}  {barra(v, total - nulos_b)}")
    print()

    # --- habitaciones ---
    print("-" * 68)
    print("HABITACIONES")
    print("-" * 68)
    nulos_h = sum(1 for r in filas if r.get("habitaciones") is None)
    print(f"  Nulos       {nulos_h:5}  {pct(nulos_h, total)}")
    print(f"  Con dato    {total - nulos_h:5}  {pct(total - nulos_h, total)}")
    valores_h = Counter(r["habitaciones"] for r in filas if r.get("habitaciones") is not None)
    print("  Distribución:")
    for k, v in sorted(valores_h.items()):
        print(f"    {k:3} hab   {v:5}  {pct(v, total - nulos_h)}  {barra(v, total - nulos_h)}")
    print()

    # --- precio y moneda ---
    print("-" * 68)
    print("PRECIO")
    print("-" * 68)
    nulos_p = sum(1 for r in filas if r.get("precio") is None)
    print(f"  Nulos    {nulos_p:5}  {pct(nulos_p, total)}")
    print(f"  Con dato {total - nulos_p:5}  {pct(total - nulos_p, total)}")
    monedas = Counter((r.get("moneda") or "(null)") for r in filas)
    print("  Monedas:")
    for k, v in monedas.most_common():
        print(f"    {k:10} {v:5}  {pct(v, total)}")
    usd = [r["precio"] for r in filas if r.get("moneda") == "USD" and r.get("precio")]
    if usd:
        usd.sort()
        print(f"\n  Precio USD (n={len(usd)}):")
        print(f"    minimo  {usd[0]:>12,.0f}")
        print(f"    mediana {usd[len(usd) // 2]:>12,.0f}")
        print(f"    maximo  {usd[-1]:>12,.0f}")
    print()

    # --- municipio ---
    print("-" * 68)
    print("MUNICIPIO")
    print("-" * 68)
    nulos_m = sum(1 for r in filas if r.get("municipio") is None)
    print(f"  Nulos   {nulos_m:5}  {pct(nulos_m, total)}")
    print(f"  Con dato{total - nulos_m:5}  {pct(total - nulos_m, total)}")
    munis = Counter((r.get("municipio") or "(sin municipio)") for r in filas)
    print("  Distribución:")
    for k, v in munis.most_common():
        print(f"    {k:22} {v:5}  {pct(v, total)}  {barra(v, total)}")
    print("=" * 68)


if __name__ == "__main__":
    main()
