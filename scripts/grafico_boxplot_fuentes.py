#!/usr/bin/env python3
r"""
Gráfico boxplot: comparación de precios por fuente (Pilar 2 vs Pilar 1 vs Pilar 4).

Fuentes:
  - Revolico  → data/processed/habana_limpio.jsonl        (municipio == "Playa", precio_usd)
  - Redes     → data/processed/redes_sociales_limpias.jsonl (municipio == "Playa", precio)
  - Agencias → data/processed/agencias_online.jsonl         (municipio == "Playa", precio)
  - Entrevistas → data/raw/entrevistas_playa.jsonl         (precio_lista)

Salida: graficos/4_boxplot_fuentes.png

Uso:  .venv\Scripts\python.exe scripts/grafico_boxplot_fuentes.py
"""

import json
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ARCHIVOS = {
    "Revolico": ("data/processed/habana_limpio.jsonl", "municipio", "precio_usd", "Playa"),
    "Redes": ("data/processed/redes_sociales_limpias.jsonl", "municipio", "precio", "Playa"),
    "Agencias": ("data/processed/agencias_online.jsonl", "municipio", "precio", "Playa"),
    "Entrevistas": ("data/raw/entrevistas_playa.jsonl", None, "precio_lista", None),
}


def leer_registros(ruta: str) -> list[dict]:
    lineas = [
        l
        for l in open(ruta, encoding="utf-8").read().splitlines()
        if l.strip()
    ]
    return [json.loads(l) for l in lineas]


def recoger(ruta: str, campo: str, municipio: str | None) -> list[float]:
    registros = leer_registros(ruta)
    valores = []
    for r in registros:
        precio = r.get(campo)
        if precio is None:
            continue
        if municipio is not None and r.get("municipio") != municipio:
            continue
        valores.append(float(precio))
    return valores


def main() -> None:
    datos = {}
    for nombre, (ruta, campo, precio_campo, municipio) in ARCHIVOS.items():
        if nombre == "Entrevistas":
            valores = [
                float(r["precio_lista"])
                for r in leer_registros(ruta)
                if r.get("precio_lista") is not None
            ]
        else:
            valores = recoger(ruta, precio_campo, municipio)
        datos[nombre] = valores
        print(f"{nombre}: n={len(valores)}")

    nombres = list(datos.keys())
    valores = [datos[n] for n in nombres]

    fig, ax = plt.subplots(figsize=(12, 7))
    box = ax.boxplot(
        valores,
        tick_labels=nombres,
        patch_artist=True,
        medianprops=dict(color="black", linewidth=2),
        boxprops=dict(facecolor="lightgrey", edgecolor="black", linewidth=1.5),
        whiskerprops=dict(color="black", linewidth=1.5),
        capprops=dict(color="black", linewidth=1.5),
        flierprops=dict(color="grey", linewidth=1.5),
        showfliers=False,
    )
    ax.set_ylabel("Precio (USD)", fontsize=14, fontweight="bold")
    ax.set_title(
        "Comparación de precios por fuente",
        fontsize=17,
        fontweight="bold",
    )
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig("graficos/4_boxplot_fuentes.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
