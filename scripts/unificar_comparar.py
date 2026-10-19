#!/usr/bin/env python3
r"""
Unifica los datasets de Playa (Pilar 1: Revolico, Pilar 3: Redes sociales)
y compara precios por barrio.

Pasos:
  1. Normaliza el campo `barrio` de AMBOS datasets con la misma función
     (normalizar_barrio en procesar_redes.py), para que sean comparables.
  2. Une los dos en data/processed/dataset_unificado.csv con una columna
     `fuente` que indica el canal.
  3. Tabla comparativa por barrio: n y mediana de precio por fuente.
  4. Gráfico de barras agrupadas.

Advertencia metodológica: los dos canales no cubren los mismos barrios.
Solo se comparan los que aparecen en ambos con n suficiente.

Uso:  .venv\Scripts\python.exe scripts\unificar_comparar.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent))
from procesar_redes import normalizar_barrio  # noqa: E402

REVOLICO = Path("data/processed/playa_limpio_v2.csv")
REDES = Path("data/processed/redes_sociales_limpias.csv")
DESTINO = Path("data/processed/dataset_unificado.csv")
GRAFICO = Path("graficos/comparacion_fuentes_barrio.png")

# N mínimo por barrio y fuente para que la mediana sea interpretable.
# Con n=1 la mediana es el propio valor: no es una estadística.
N_MINIMO = 3

# Esquema común
COLUMNAS_COMUNES = [
    "titulo", "precio_usd", "moneda", "barrio", "barrio_referencia",
    "tipo_inmueble", "habitaciones", "banos", "metros_cuadrados",
    "descripcion", "url", "fuente",
    "menciona_urgencia_viaje", "menciona_problemas_estructurales",
]


def normalizar(df: pd.DataFrame, etiqueta: str) -> pd.DataFrame:
    """Aplica normalizar_barrio() al campo barrio y crea barrio_referencia."""
    antes = df["barrio"].value_counts().to_dict()
    resultados = [normalizar_barrio(v) for v in df["barrio"]]
    df["barrio"] = [r[0] for r in resultados]
    if "barrio_referencia" not in df.columns:
        df["barrio_referencia"] = [r[1] for r in resultados]
    despues = df["barrio"].value_counts().to_dict()
    cambios = {k: (antes.get(k, 0), v) for k, v in despues.items() if antes.get(k, 0) != v}
    print(f"  {etiqueta}: {len(antes)} categorías -> {len(despues)}")
    if cambios:
        print(f"    cambios: {cambios}")
    return df


def main() -> None:
    print("=" * 86)
    print("UNIFICACIÓN Y COMPARACIÓN DE FUENTES — Playa")
    print("=" * 86)

    # ── 1. NORMALIZAR ───────────────────────────────────────────────────────
    print()
    print("1) NORMALIZACIÓN DE BARRIOS (misma función para ambas fuentes)")
    rev = pd.read_csv(REVOLICO, encoding="utf-8-sig")
    red = pd.read_csv(REDES, encoding="utf-8-sig")
    print(f"  Revolico: {len(rev)} filas")
    print(f"  Redes   : {len(red)} filas")
    rev = normalizar(rev, "Revolico")
    red = normalizar(red, "Redes")

    # ── 2. UNIFICAR ─────────────────────────────────────────────────────────
    print()
    print("2) UNIFICACIÓN DE ESQUEMAS")
    red = red.rename(columns={"precio": "precio_usd"})
    if "barrio_referencia" in red.columns:
        red["barrio_referencia"] = red["barrio_referencia"].fillna("")

    rev["fuente"] = "Revolico"
    red["fuente"] = "Redes"

    comunes = [c for c in COLUMNAS_COMUNES if c in rev.columns and c in red.columns]
    print(f"  columnas comunes: {len(comunes)}")
    for c in COLUMNAS_COMUNES:
        if c not in comunes:
            print(f"    (no presente en ambas: {c})")

    unificado = pd.concat(
        [rev[comunes], red[comunes]], ignore_index=True, sort=False
    )
    # Los campos que solo tiene una fuente quedan en blanco
    for c in COLUMNAS_COMUNES:
        if c not in unificado.columns:
            unificado[c] = None

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    unificado.to_csv(DESTINO, index=False, encoding="utf-8-sig")
    print(f"  filas unificadas: {len(unificado)} "
          f"(Revolico {len(rev)} + Redes {len(red)})")
    print(f"  archivo: {DESTINO}")
    print()

    # ── 3. TABLA COMPARATIVA ────────────────────────────────────────────────
    print("3) TABLA COMPARATIVA POR BARRIO")
    print("=" * 86)

    rev_b = rev[rev["barrio"] != "Desconocido"]
    red_b = red[red["barrio"] != "Desconocido"]

    b_rev = set(rev_b["barrio"])
    b_red = set(red_b["barrio"])
    comunes_barrios = sorted(b_rev & b_red)
    solo_rev = sorted(b_rev - b_red)
    solo_red = sorted(b_red - b_rev)

    print(f"  barrios en Revolico : {len(b_rev)}")
    print(f"  barrios en Redes    : {len(b_red)}")
    print(f"  en COMUN            : {len(comunes_barrios)}  {comunes_barrios}")
    print(f"  solo en Revolico    : {len(solo_rev)}  {solo_rev}")
    print(f"  solo en Redes       : {len(solo_red)}  {solo_red}")
    print()

    filas = []
    for barrio in sorted(b_rev | b_red):
        g_r = rev_b[rev_b["barrio"] == barrio]
        g_d = red_b[red_b["barrio"] == barrio]
        p_r = g_r[g_r["precio_usd"].notna()]["precio_usd"]
        p_d = g_d[g_d["precio_usd"].notna()]["precio_usd"]
        filas.append({
            "barrio": barrio,
            "n_rev": len(g_r),
            "n_red": len(g_d),
            "med_rev": p_r.median() if len(p_r) else np.nan,
            "med_red": p_d.median() if len(p_d) else np.nan,
            "dif_pct": ((p_d.median() - p_r.median()) / p_r.median() * 100)
                       if len(p_r) and len(p_d) and p_r.median() else np.nan,
        })
    tabla = pd.DataFrame(filas)

    print(f'{"barrio":22} {"n_rev":>6} {"n_red":>6} {"med_rev":>11} {"med_red":>11} {"dif%":>9}')
    print("-" * 86)
    for _, r in tabla.iterrows():
        mr = f"{r['med_rev']:,.0f}" if pd.notna(r["med_rev"]) else "  --"
        md = f"{r['med_red']:,.0f}" if pd.notna(r["med_red"]) else "  --"
        dif = f"{r['dif_pct']:+.0f}%" if pd.notna(r["dif_pct"]) else "  --"
        marca = "*" if (r["n_rev"] >= N_MINIMO and r["n_red"] >= N_MINIMO) else " "
        print(f'{marca}{r["barrio"]:21} {r["n_rev"]:>6} {r["n_red"]:>6} {mr:>11} {md:>11} {dif:>9}')
    print("-" * 86)
    print(f"  * = ambos canales con n >= {N_MINIMO} (mediana interpretable)")
    print()

    # ── 4. GRÁFICO ──────────────────────────────────────────────────────────
    print("4) GRÁFICO COMPARATIVO")
    grafico_barrios = tabla[
        (tabla["n_rev"] >= N_MINIMO) & (tabla["n_red"] >= N_MINIMO)
    ].copy()

    if grafico_barrios.empty:
        print(f"  NINGÚN barrio alcanza n >= {N_MINIMO} en ambas fuentes.")
        print("  Se grafica el top por tamaño combinado, marcando el umbral.")
        grafico_barrios = tabla.assign(
            total=lambda d: d["n_rev"] + d["n_red"]
        ).sort_values("total", ascending=False).head(8)

    x = np.arange(len(grafico_barrios))
    ancho = 0.38

    fig, ax = plt.subplots(figsize=(11, 6.5))
    b1 = ax.bar(x - ancho / 2, grafico_barrios["med_rev"], ancho,
                label="Revolico", color="#4C72B0")
    b2 = ax.bar(x + ancho / 2, grafico_barrios["med_red"], ancho,
                label="Redes sociales", color="#DD8452")

    for barras in (b1, b2):
        for barra in barras:
            h = barra.get_height()
            if pd.notna(h) and h > 0:
                ax.annotate(f"{h:,.0f}", (barra.get_x() + barra.get_width() / 2, h),
                            ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(grafico_barrios["barrio"], rotation=20, ha="right")
    ax.set_ylabel("Mediana del precio (USD)")
    ax.set_title(
        "Precio mediano por barrio: Revolico vs. redes sociales (Playa)\n"
        f"Barrios con n >= {N_MINIMO} en ambos canales"
        if len(grafico_barrios) >= 2 else
        f"Precio mediano por barrio (Playa) — sin barrio que alcance n>={N_MINIMO} en ambos canales"
    )
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    sns.despine()
    GRAFICO.parent.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(GRAFICO, dpi=150)
    plt.close(fig)
    print(f"  gráfico guardado: {GRAFICO}")
    print(f"  barrios graficados: {list(grafico_barrios['barrio'])}")
    print()

    # ── 5. HALLAZGOS ────────────────────────────────────────────────────────
    print("5) HALLAZGOS")
    print("=" * 86)

    print()
    print(f"  Cobertura geográfica")
    print(f"    Solo {len(comunes_barrios)} de los {len(b_rev | b_red)} barrios aparecen")
    print(f"    en ambos canales. Buenavista, La Ceiba, Flores, La Corbata, Fontanar,")
    print(f"    J. Manuel Márquez, Querejeta y Sierra NO aparecen en Revolico.")
    print(f"    Santa Fe y Atabey NO aparecen en redes sociales.")
    print(f"    -> La comparación por barrio es válida solo para: "
          f"{', '.join(comunes_barrios)}")

    print()
    print(f"  Tamaño de muestra")
    print(f"    Revolico: {len(rev)} anuncios, {len(rev_b)} con barrio conocido "
          f"({100*len(rev_b)/len(rev):.1f}%)")
    print(f"    Redes   : {len(red)} anuncios, {len(red_b)} con barrio conocido "
          f"({100*len(red_b)/len(red):.1f}%)")
    print(f"    Las redes sociales tienen MUCHO mayor precisión de ubicación.")

    print()
    print(f"  Precio global (todos los anuncios)")
    for etiqueta, d in [("Revolico", rev), ("Redes", red)]:
        p = d[d["precio_usd"].notna()]["precio_usd"]
        print(f"    {etiqueta:10} n={len(p):>3}  mediana={p.median():>9,.0f}  "
              f"promedio={p.mean():>9,.0f}")

    comp = grafico_barrios.dropna(subset=["med_rev", "med_red"])
    if len(comp):
        print()
        print(f"  Precio por barrio (solo comparable)")
        for _, r in comp.iterrows():
            d = r["dif_pct"]
            signo = "REDES MAS CARO" if d > 0 else "REDES MAS BARATO"
            print(f"    {r['barrio']:20} Revolico={r['med_rev']:>9,.0f}  "
                  f"Redes={r['med_red']:>9,.0f}  dif={d:+.0f}%  {signo}")

    print()
    print(f"  Detección de urgencia migratoria")
    for etiqueta, d in [("Revolico", rev), ("Redes", red)]:
        u = int(d["menciona_urgencia_viaje"].sum())
        print(f"    {etiqueta:10} {u}/{len(d)} = {100*u/len(d):.1f}%")
    print("    Consistente en ambos canales: la migración no se verbaliza online.")
    print("=" * 86)


if __name__ == "__main__":
    main()