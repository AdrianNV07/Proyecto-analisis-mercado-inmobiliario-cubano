#!/usr/bin/env python3
r"""
Gráfico lollipop: margen de negociación promedio por motivo de venta.

Datos:
  - Migrantes: 7.82 %
  - No migrantes: 4.96 %

Salida: graficos/2_margen_negociacion.png

Uso:  .venv\Scripts\python.exe scripts/grafico_margen_negociacion.py
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SALIDA = "graficos/2_margen_negociacion.png"

MIGRANTES = 7.82
NO_MIGRANTES = 4.96


def main() -> None:
    fig, ax = plt.subplots(figsize=(10, 7))

    # Lollipop: línea vertical desde 0 hasta el valor + punto en la punta
    ax.plot([1, 1], [0, MIGRANTES], color="grey", linewidth=1.5, linestyle="-", zorder=3)
    ax.plot([1.25, 1.25], [0, NO_MIGRANTES], color="grey", linewidth=1.5, linestyle="-", zorder=3)
    ax.scatter([1], [MIGRANTES], s=320, color="red", edgecolors="black", linewidths=3, zorder=4)
    ax.scatter([1.25], [NO_MIGRANTES], s=320, color="steelblue", edgecolors="black", linewidths=3, zorder=4)

    # Etiquetas grandes
    ax.annotate(f"{MIGRANTES:.2f}%", (1, MIGRANTES), textcoords="offset points", xytext=(0, 14), ha="center",
                fontsize=28, fontweight="bold", color="red")
    ax.annotate(f"{NO_MIGRANTES:.2f}%", (1.25, NO_MIGRANTES), textcoords="offset points", xytext=(0, 14), ha="center",
                fontsize=28, fontweight="bold", color="steelblue")

    # Ejes / etiquetas
    ax.set_xticks([1, 1.25])
    ax.set_xticklabels(["Migrantes", "No Migrantes"], fontsize=13, fontweight="bold")
    ax.set_ylim(0, 10)
    ax.set_ylabel("Porcentaje de margen de negociación (%)", fontsize=14, fontweight="bold")
    ax.set_title(
        "El costo de la urgencia: Margen de negociación promedio",
        fontsize=17,
        fontweight="bold",
    )
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(SALIDA, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
