#!/usr/bin/env python3
r"""
Gráfico dumbbell: brecha entre el mercado online y el mercado real.

Fuentes de datos:
  - Mercado Online (Revolico / redes): menciones de migración = 0 (0 %).
    n = 135 anuncios de Playa analizados en el dataset unificado.
  - Mercado Real (Entrevistas Pilar 4): menciones de migración = 10 de 30
    entrevistados (33.3 %).

Salida: graficos/1_brecha_migracion.png

Uso:  .venv\Scripts\python.exe scripts/grafico_brecha_migracion.py
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SALIDA = "graficos/1_brecha_migracion.png"

# Valores (porcentaje de menciones de migración)
VALORES = {
    "Mercado Online (Revolico/Redes)": 0.0,
    "Mercado Real (Entrevistas)": 33.33,
}


def main() -> None:
    fig, ax = plt.subplots(figsize=(12, 7))

    categorias = list(VALORES.keys())
    porcentajes = [VALORES[c] for c in categorias]

    # Línea gruesa que une los dos puntos
    ax.plot(
        [1, 2],
        [0.0, 33.33],
        color="grey",
        linewidth=6.5,
        marker="o",
        markersize=14,
        markeredgecolor="black",
        markeredgewidth=1.5,
        linestyle="-",
        zorder=3,
    )
    ax.scatter([1], [0.0], s=300, color="grey", edgecolors="black", linewidths=3, zorder=4)
    ax.scatter([2], [33.33], s=360, color="red", edgecolors="black", linewidths=3, zorder=4)

    # Etiquetas grandes
    ax.annotate("0%", (1, 0.0), textcoords="offset points", xytext=(0, 18), ha="center",
                fontsize=34, fontweight="bold", color="black")
    ax.annotate("33.3%", (2, 33.33), textcoords="offset points", xytext=(0, 18), ha="center",
                fontsize=34, fontweight="bold", color="red")

    # Ejes / etiquetas
    ax.set_xticks([1, 2])
    ax.set_xticklabels(categorias, fontsize=13, fontweight="bold")
    ax.set_ylim(0, 45)
    ax.set_ylabel("Porcentaje de menciones de migración", fontsize=14, fontweight="bold")
    ax.set_title(
        "La migración invisible: Brecha entre el discurso online y la realidad callejera",
        fontsize=17,
        fontweight="bold",
    )
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig("graficos/1_brecha_migracion.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
