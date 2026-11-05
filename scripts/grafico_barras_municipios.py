#!/usr/bin/env python3
r"""
Gráfico de barras apiladas por municipio con nombres descriptivos de clúster.

Lee data/processed/habana_clusterizado_texto.jsonl (que ya tiene
nombre_cluster_texto asignado por perfilar_clusters.py) y genera:

  graficos/clusters_texto_habana_municipios.png       (conteo absoluto)
  graficos/clusters_texto_habana_municipios_pct.png   (composicion al 100 %)

Uso:  .venv\Scripts\python.exe scripts\grafico_barras_municipios.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ORIGEN = Path("data/processed/habana_clusterizado_texto.jsonl")
SALIDA = Path("graficos/clusters_texto_habana_municipios.png")
SALIDA_PCT = Path("graficos/clusters_texto_habana_municipios_pct.png")


def main() -> None:
    SALIDA.parent.mkdir(exist_ok=True)

    filas = [json.loads(l) for l in ORIGEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    df = pd.DataFrame(filas)

    print(f"Datos: {len(df)} anuncios")
    print(f"Columnas disponibles: {list(df.columns)}")

    # Verificar que nombre_cluster_texto existe
    if "nombre_cluster_texto" not in df.columns:
        raise ValueError(
            "La columna 'nombre_cluster_texto' no existe. "
            "Ejecuta primero scripts/perfilar_clusters.py"
        )

    # Ordenar clústeres por tamaño total para que la barra más grande quede abajo
    orden_clusters = df["nombre_cluster_texto"].value_counts().index.tolist()

    # Crosstab con nombres descriptivos
    crosstab = pd.crosstab(df["municipio"], df["nombre_cluster_texto"])
    # Reordenar columnas según frecuencia global
    crosstab = crosstab.reindex(columns=orden_clusters, fill_value=0)

    print(f"\nClústeres: {orden_clusters}")
    print(f"Municipios: {crosstab.shape[0]}")

    # Colores consistentes con el resto del proyecto
    colores = {
        "Anuncios de Agencias": "#e74c3c",
        "Apartamentos en Edificio": "#3498db",
        "Casas Económicas": "#2ecc71",
        "Entrega Inmediata": "#f39c12",
        "Venta con Trámites Pendientes": "#9b59b6",
    }
    # Asignar colores (los que no estén en el diccionario reciben uno genérico)
    palette = [colores.get(c, f"C{i}") for i, c in enumerate(orden_clusters)]

    # ── Gráfico ──────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(16, 9))

    crosstab.plot(
        kind="bar", stacked=True, ax=ax, color=palette, width=0.75,
        edgecolor="white", linewidth=0.5,
    )

    ax.set_xlabel("Municipio", fontsize=12)
    ax.set_ylabel("Cantidad de anuncios", fontsize=12)
    ax.set_title("Clústeres de texto por municipio — La Habana", fontsize=14)

    # Leyenda con nombres descriptivos
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles, labels,
        title="Perfil de texto",
        bbox_to_anchor=(1.02, 1), loc="upper left",
        fontsize=10, title_fontsize=11,
    )

    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()

    fig.savefig(SALIDA, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"\nGráfico guardado: {SALIDA}")

    # ── Gráfico 2: composición porcentual (barras al 100 %) ─────────────────
    crosstab_pct = crosstab.div(crosstab.sum(axis=1), axis=0) * 100
    totales = crosstab.sum(axis=1).astype(int)

    fig2, ax2 = plt.subplots(figsize=(16, 9))
    crosstab_pct.plot(
        kind="bar", stacked=True, ax=ax2, color=palette, width=0.75,
        edgecolor="white", linewidth=0.5,
    )

    ax2.set_xlabel("Municipio", fontsize=12)
    ax2.set_ylabel("Porcentaje de anuncios (%)", fontsize=12)
    ax2.set_ylim(0, 100)
    ax2.set_yticks(range(0, 101, 10))
    ax2.set_title(
        "Composición porcentual de los perfiles de texto por municipio — La Habana\n"
        "(cada barra suma 100 %; el n se indica sobre cada municipio)",
        fontsize=14, pad=32,
    )

    # Etiqueta con el n total sobre cada barra
    for i, muni in enumerate(crosstab_pct.index):
        ax2.text(
            i, 101.5, f"n={totales[muni]}",
            ha="center", va="bottom", fontsize=9, fontweight="bold",
        )

    # Porcentaje dentro de cada segmento (solo si ocupa al menos 8 %)
    for i, muni in enumerate(crosstab_pct.index):
        acumulado = 0.0
        for col in crosstab_pct.columns:
            valor = crosstab_pct.loc[muni, col]
            if valor >= 8:
                ax2.text(
                    i, acumulado + valor / 2, f"{valor:.0f}%",
                    ha="center", va="center", fontsize=8,
                    color="white", fontweight="bold",
                )
            acumulado += valor

    # Misma leyenda que el gráfico absoluto
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(
        handles2, labels2,
        title="Perfil de texto",
        bbox_to_anchor=(1.02, 1), loc="upper left",
        fontsize=10, title_fontsize=11,
    )

    plt.xticks(rotation=45, ha="right")
    fig2.tight_layout()

    fig2.savefig(SALIDA_PCT, dpi=150, bbox_inches="tight")
    plt.close(fig2)

    print(f"Gráfico porcentual guardado: {SALIDA_PCT}")

    # Aviso metodológico: municipios con n muy bajo
    pequenos = totales[totales < 5]
    if len(pequenos) > 0:
        print("\nAviso: municipios con n<5 (porcentajes poco estables):")
        for muni, n in pequenos.items():
            print(f"  - {muni}: n={n}")


if __name__ == "__main__":
    main()
