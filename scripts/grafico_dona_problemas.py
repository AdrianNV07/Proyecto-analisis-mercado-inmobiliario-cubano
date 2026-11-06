#!/usr/bin/env python3
r"""
Gráfico de dona: ocultamiento de problemas en viviendas con problemas.

Datos (Pilar 4):
  - Total de personas con problemas en la casa: n = 4
  - Ocultaron el problema: 75 % (3 de 4)
  - Declararon el problema: 25 % (1 de 4)

Salida: graficos/3_dona_problemas.png

Uso:  .venv\Scripts\python.exe scripts/grafico_dona_problemas.py
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SALIDA = "graficos/3_dona_problemas.png"

OCULTARON = 0.75
DECLARARON = 0.25


def main() -> None:
    fig, ax = plt.subplots(figsize=(8, 8))

    sizes = [OCULTARON, DECLARARON]
    labels = ["personas que ocultaron los problemas", "personas que declararon el problema"]
    colors = ["#d62728", "#2196f3"]  # rojo = ocultaron, azul = declararon

    wedges = ax.pie(
        sizes,
        labels=labels,
        autopct="%1.0f%%",
        pctdistance=0.85,
        startangle=90,
        colors=colors,
        textprops=dict(fontsize=14, fontweight="bold"),
    )

    ax.set_title(
        "Ocultamiento de problemas: viviendas con problemas",
        fontsize=17,
        fontweight="bold",
    )

    fig.tight_layout()
    fig.savefig(SALIDA, dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
