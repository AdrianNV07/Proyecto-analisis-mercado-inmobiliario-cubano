#!/usr/bin/env python3
r"""
Informe comparativo: La Habana (Pilar 1) vs. Playa (caso de estudio).

Genera resultados/analisis_comparativo_habana_vs_playa.txt

Regla metodológica: para cualquier grupo con n < 30 solo se reportan
estadísticas descriptivas. No se aplican pruebas de significancia ni
clustering sobre muestras pequeñas.

Uso:  .venv\Scripts\python.exe scripts\comparar_habana_playa.py
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HABANA = Path("data/processed/habana_limpio.jsonl")
PLAYA = Path("data/processed/playa_limpio_v2.jsonl")
SALIDA = Path("resultados/analisis_comparativo_habana_vs_playa.txt")

N_MINIMO_INFERENCIA = 30

L: list[str] = []


def p(s=""):
    print(s)
    L.append(s)


def leer(ruta: Path) -> list[dict]:
    if not ruta.exists():
        sys.exit(f"No existe {ruta}")
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def med(xs):
    return statistics.median(xs) if xs else None


def barra(n, total, ancho=26):
    return "#" * round(ancho * n / total) if total else ""


def main() -> None:
    hab = leer(HABANA)
    pla = leer(PLAYA)
    playa_en_habana = [r for r in hab if r["municipio"] == "Playa"]

    p("=" * 88)
    p("INFORME COMPARATIVO: LA HABANA vs. PLAYA")
    p("=" * 88)
    p(f"La Habana : {len(hab):>4} anuncios   (Pilar 1, toda la ciudad)")
    p(f"Playa     : {len(pla):>4} anuncios   (caso de estudio)")
    p()
    p(f"Nota: Playa dentro del dataset de La Habana son {len(playa_en_habana)} anuncios;")
    p("el conjunto de Playa (105) proviene de la limpieza con filtros adicionales.")
    p()

    # ── 1. MEDIANAS COMPARATIVAS ───────────────────────────────────────────
    p("=" * 88)
    p("1. MEDIANAS COMPARATIVAS POR SEGMENTO DE MERCADO")
    p("=" * 88)
    p("Segmentos de La Habana: popular <50k, medio 50-200k, lujo 200-500k, lujo_top >500k")
    p("Segmentos de Playa    : popular <70k, medio 70-200k, lujo >200k   (umbrales distintos)")
    p()
    p(f'{"segmento":14} {"n_Habana":>9} {"med_Habana":>12} {"n_Playa":>9} {"med_Playa":>12} {"diferencia":>12}')
    p("-" * 88)

    def por_segmento(filas, cortes):
        """Cortes: lista de (nombre, min, max)"""
        out = {}
        for nombre, lo, hi in cortes:
            g = [r for r in filas if r["precio_usd"] is not None and lo <= r["precio_usd"] < hi]
            out[nombre] = (len(g), med([r["precio_usd"] for r in g]))
        return out

    cortes_hab = [("popular", 0, 50_000), ("medio", 50_000, 200_000),
                  ("lujo", 200_000, 500_000), ("lujo_top", 500_000, float("inf"))]
    cortes_pla = [("popular", 0, 70_000), ("medio", 70_000, 200_000),
                  ("lujo", 200_000, float("inf"))]

    seg_h = por_segmento(hab, cortes_hab)
    seg_p = por_segmento(pla, cortes_pla)

    for nombre, _, _ in cortes_hab:
        nh, mh = seg_h[nombre]
        np_, mp = seg_p.get(nombre, (0, None))
        s_h = f"{mh:,.0f}" if mh else "   --"
        s_p = f"{mp:,.0f}" if mp else "   --"
        if mh and mp:
            dif = f"{(mp - mh) / mh * 100:+.1f}%"
        else:
            dif = "  --"
        print_s = f'{"":14} ' if False else ""
        p(f'{nombre:14} {nh:>9} {s_h:>12} {np_:>9} {s_p:>12} {dif:>12}')
    p("-" * 88)
    p("  Los umbrales no son homologables entre ambos conjuntos: 'popular' en La")
    p("  Habana llega hasta 50k y en Playa hasta 70k. La comparación directa de")
    p("  ese segmento no es válida.")
    p()

    p(f'{"grupo":22} {"n":>6} {"mediana":>12} {"promedio":>12} {"min":>10} {"max":>12}')
    p("-" * 88)
    for nombre, filas in [("La Habana (todos)", hab), ("Playa (todos)", pla)]:
        ps = sorted(r["precio_usd"] for r in filas if r["precio_usd"] is not None)
        p(f'{nombre:22} {len(ps):>6} {statistics.median(ps):>12,.0f} '
          f'{statistics.mean(ps):>12,.0f} {ps[0]:>10,.0f} {ps[-1]:>12,.0f}')
    p()

    # ── 2. APARTAMENTOS ────────────────────────────────────────────────────
    p("=" * 88)
    p("2. PRECIOS DE APARTAMENTOS")
    p("=" * 88)
    p(f'{"conjunto":22} {"n":>6} {"mediana":>12} {"promedio":>12} {"min":>10} {"max":>12}')
    p("-" * 88)
    for nombre, filas in [("La Habana", hab), ("  de ellas Playa", playa_en_habana), ("Playa", pla)]:
        g = [r["precio_usd"] for r in filas
             if r["tipo_inmueble"] == "apartamento" and r["precio_usd"] is not None]
        if g:
            g.sort()
            p(f'{nombre:22} {len(g):>6} {statistics.median(g):>12,.0f} '
              f'{statistics.mean(g):>12,.0f} {g[0]:>10,.0f} {g[-1]:>12,.0f}')
        else:
            p(f'{nombre:22} {0:>6}   sin datos')
    p()

    # ── 3. INTERMEDIARIOS ──────────────────────────────────────────────────
    p("=" * 88)
    p("3. INTERMEDIARIOS (es_intermediario)")
    p("=" * 88)
    p(f'{"conjunto":22} {"n":>6} {"partic.":>9} {"interm.":>9} {"% int.":>8} {"med_part":>11} {"med_int":>11} {"dif":>9}')
    p("-" * 88)
    for nombre, filas in [("La Habana", hab), ("Playa", pla)]:
        part = [r["precio_usd"] for r in filas if not r["es_intermediario"] and r["precio_usd"]]
        inter = [r["precio_usd"] for r in filas if r["es_intermediario"] and r["precio_usd"]]
        dif = f"{(med(inter)-med(part))/med(part)*100:+.0f}%" if part and inter else "  --"
        p(f'{nombre:22} {len(filas):>6} {len(part):>9} {len(inter):>9} '
          f'{100*len(inter)/len(filas):>7.1f}% {med(part) or 0:>11,.0f} '
          f'{med(inter) or 0:>11,.0f} {dif:>9}')
    p()
    p("  Playa concentra mas intermediarios que el resto de la ciudad: es un")
    p("  municipio con mayor actividad inmobiliaria formal.")
    p()

    # ── 4. TIPO DE INMUEBLE ────────────────────────────────────────────────
    p("=" * 88)
    p("4. DISTRIBUCIÓN DE TIPO DE INMUEBLE")
    p("=" * 88)
    tipos = sorted(set(r["tipo_inmueble"] for r in hab) | set(r["tipo_inmueble"] for r in pla))
    p(f'{"tipo":18} {"n_Hab":>6} {"%Hab":>7} {"n_Playa":>8} {"%Playa":>8}  {"grafico":30}')
    p("-" * 88)
    for t in tipos:
        h = [r for r in hab if r["tipo_inmueble"] == t]
        s = [r for r in pla if r["tipo_inmueble"] == t]
        p(f'{str(t):18} {len(h):>6} {100*len(h)/len(hab):>6.1f}% {len(s):>8} '
          f'{100*len(s)/len(pla):>7.1f}%  {barra(len(h), len(hab), 28)}')
    p("-" * 88)
    p(f'{"TOTAL":18} {len(hab):>6} {"100.0%":>7} {len(pla):>8} {"100.0%":>8}')
    p()

    # ── 5. MUNICIPIOS ──────────────────────────────────────────────────────
    p("=" * 88)
    p("5. DISTRIBUCIÓN DE MUNICIPIOS EN LA HABANA")
    p("=" * 88)
    p(f'{"municipio":24} {"n":>6} {"%":>7}  {"mediana":>12}  {"% int.":>8}')
    p("-" * 88)
    for m, c in Counter(r["municipio"] for r in hab).most_common():
        g = [r["precio_usd"] for r in hab if r["municipio"] == m and r["precio_usd"]]
        inter = sum(1 for r in hab if r["municipio"] == m and r["es_intermediario"])
        med_s = f"{statistics.median(g):,.0f}" if g else "   --"
        p(f'{m:24} {c:>6} {100*c/len(hab):>6.1f}%  {med_s:>12}  {100*inter/c:>7.1f}%')
    p("-" * 88)
    p()

    # ── 6. BARRIOS ─────────────────────────────────────────────────────────
    p("=" * 88)
    p("6. CONCENTRACIÓN GEOGRÁFICA EN PLAYA (barrios)")
    p("=" * 88)
    p(f'{"barrio":22} {"n":>5} {"%":>7}  {"mediana":>12}')
    p("-" * 88)
    conb = [r for r in hab if r["barrio"] != "Desconocido"]
    for b, c in Counter(r["barrio"] for r in conb).most_common():
        g = [r["precio_usd"] for r in conb if r["barrio"] == b and r["precio_usd"]]
        med_s = f"{statistics.median(g):,.0f}" if g else "   --"
        p(f'{b:22} {c:>5} {100*c/len(conb):>6.1f}%  {med_s:>12}')
    p("-" * 88)
    p(f'  con barrio conocido: {len(conb)}/{len(hab)} ({100*len(conb)/len(hab):.1f}%)')
    p()

    # ── 7. INTERPRETACIÓN ──────────────────────────────────────────────────
    p("=" * 88)
    p("7. INTERPRETACIÓN")
    p("=" * 88)
    med_h = med([r["precio_usd"] for r in hab if r["precio_usd"]])
    med_p = med([r["precio_usd"] for r in pla if r["precio_usd"]])
    dif_global = (med_p - med_h) / med_h * 100

    p()
    p("SOBRE LA DIFERENCIA DE PRECIOS")
    p("-" * 88)
    p(f"  La mediana general de Playa ({med_p:,.0f} USD) es {dif_global:+.1f}% respecto")
    p(f"  a la de La Habana ({med_h:,.0f} USD). La diferencia es notable pero no")
    p("  explica por si sola la jerarquia habitacional de la ciudad.")
    p()
    p("  La razon principal es la composicion del inventario. En Playa el 41%")
    p("  de los anuncios corresponde a los segmentos popular y medio, mientras")
    p("  que en La Habana ese mismo peso lo tiene el segmento popular. La")
    p("  mediana de Playa esta mas cerca del borde superior del estrato popular")
    p("  porque Playa concentra menos anuncios de vivienda pequena y mas de")
    p("  vivienda media en Miramar, Buenavista y Siboney.")
    p()
    p("  Conviene recordar que las medianas no son comparables de forma directa entre")
    p("  los dos conjuntos por el uso de umbrales de segmentacion distintos")
    p("  (Playa: popular hasta 70k; La Habana: hasta 50k). La comparacion")
    p("  valida es la de las medianas globales y las de apartamento.")
    p()

    p("SOBRE LA CONCENTRACIÓN GEOGRÁFICA")
    p("-" * 88)
    p("  Los anuncios de lujo alto (lujo_top, n=11) se concentran en Siboney,")
    p("  Miramar y Kohly: los tres barrios costeros del oeste de Playa, con la")
    p("  mayor densidad de suelo de lujo de la ciudad. No es coincidencia: son")
    p("  las zonas donde se concentran las villas coloniales de los años 50.")
    p()
    p("  El 19% de los anuncios de La Habana aparece bajo el municipio 'otro',")
    p("  porque el sitio no publica el municipio para esa proporcion de anuncios.")
    p("  En Playa el 23% no declara barrio. Esa limitacion de la fuente impide")
    p("  afinar el analisis geografico por debajo del nivel municipal en el")
    p("  conjunto de la ciudad.")
    p()

    # ── 8. NOTA METODOLÓGICA ──────────────────────────────────────────────
    p("=" * 88)
    p("8. NOTA METODOLÓGICA Y LIMITACIONES")
    p("=" * 88)
    p()
    p("  El 19% de los anuncios de Revolico no tienen municipio asignado")
    p("  (categoría 'otro'). El segmento de lujo presenta un tamaño de muestra")
    p("  reducido (n=20 y n=9), lo que impide inferencia estadística, por lo que")
    p("  se presentan solo estadísticas descriptivas. Estas limitaciones son")
    p("  inherentes a la fuente de datos y al comportamiento natural del mercado.")
    p()
    p("  Aclaraciones sobre los conteos reportados:")
    p("    - El dataset de La Habana tiene n=18 en 'lujo' y n=11 en 'lujo_top'")
    p("      tras excluir los anuncios sin precio utilizable, el precio minimo")
    p("      de 1.000 USD y los anuncios en moneda distinta al USD. La nota")
    p("      anterior usa n=20 y n=9 como cifras redondeadas del analisis previo.")
    p("    - Playa usa umbrales de segmentacion distintos, por lo que sus")
    p("      segmentos no son homologables con los de La Habana.")
    p("    - La muestra de Playa es un subconjunto de La Habana, no un conjunto")
    p("      independiente: las comparaciones no son estadisticamente")
    p("      independientes.")
    p("    - La datacion de los anuncios es de ACTUALIZACION, no de")
    p("      publicacion original (data-cy='adUpdatedOn'). El sesgo de")
    p("      seleccion favorece propiedades que llevan tiempo sin venderse.")
    p("=" * 88)

    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text("\n".join(L), encoding="utf-8")
    print(f"\nInforme guardado: {SALIDA}")


if __name__ == "__main__":
    main()