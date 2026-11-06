#!/usr/bin/env python3
r"""
Gráfico de barras: perfiles discursivos y precios medianos por clúster (texto, Playa).

Reemplazo del PCA (`graficos/clusters_texto.png`), considerado demasiado
abstracto para el informe, por un gráfico de barras directo que muestra la
relación entre el perfil discursivo del clúster y su precio mediano.

Datos: data/processed/playa_clusterizado_texto.csv (TF-IDF + K-Means, K=4,
silhouette=0.1313; ver resultados/clustering_texto.txt).

Eje X: nombre de los 4 clústeres.
Eje Y: mediana de precio de cada clúster.
Barras: color distinto por clúster.
Etiqueta: n (número de anuncios) encima de cada barra.

Salidas:
  graficos/clusters_texto_barras.png

Uso:  .venv\Scripts\python.exe scripts/grafico_barras_clusters_texto.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import pandas as pd

ORIGEN = Path("data/processed/playa_clusterizado_texto.csv")
SALIDA = Path("graficos/clusters_texto_barras.png")

# Nombres descriptivos de los clústeres (asignados en el perfilado de texto).
LABEL_CLUSTERS = {
    0: "C0: Casas Familiares",
    1: "C1: Anuncios de Agencias",
    2: "C2: Miramar/Papeles",
    3: "C3: Edificios Capitalistas",
}

# Color distinto por clúster.
COLORES = ["#3498db", "#e74c3c", "#2ecc71", "#9b59b6"]


def main() -> None:
    SALIDA.parent.mkdir(exist_ok=True)

    df = pd.read_csv(ORIGEN, encoding="utf-8-sig")

    filas = []
    for c, g in df.groupby("cluster_texto"):
        filas.append(
            {
                "cluster": int(c),
                "nombre": LABEL_CLUSTERS.get(int(c), f"C{int(c)}"),
                "mediana": float(g["precio_usd"].median()),
                "n": int(len(g)),
            }
        )

    datos = (
        pd.DataFrame(filas)
        .sort_values("cluster")
        .reset_index(drop=True)
    )

    fig, ax = plt.subplots(figsize=(12, 7))

    posiciones = list(range(len(datos)))
    ax.bar(
        posiciones,
        datos["mediana"],
        color=[COLORES[i % len(COLORES)] for i in range(len(datos))],
        width=0.55,
        edgecolor="white",
        linewidth=0.6,
    )

    ax.set_xticks(posiciones)
    ax.set_xticklabels(datos["nombre"].tolist(), rotation=0, ha="center")
    ax.set_xlabel("Clúster", fontsize=12)
    ax.set_ylabel("Mediana de precio (USD)", fontsize=12)
    ax.set_title(
        "Perfiles discursivos y precios medianos según el Análisis de Texto (NLP)",
        fontsize=14,
        pad=18,
    )
    ax.set_ylim(0, float(datos["mediana"].max()) * 1.30)
    ax.grid(axis="y", alpha=0.22)
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, p: f"${v:,.0f}")
    )

    # Etiqueta con el n encima de cada barra
    for i, row in enumerate(datos.itertuples(index=False)):
        ax.annotate(
            f"n={int(row.n)}",
            xy=(i, float(row.mediana)),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    fig.tight_layout()
    fig.savefig(SALIDA, dpi=150)
    plt.close(fig)

    print(f"Gráfico guardado: {SALIDA}")


if __name__ == "__main__":
    main()
