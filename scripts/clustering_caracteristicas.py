#!/usr/bin/env python3
r"""
Clustering exploratorio de Playa por características del inmueble.

NO usa el precio: el objetivo es encontrar tipos de vivienda, no
re-descubrir los segmentos de mercado (popular/medio/lujo) que ya
están definidos en la limpieza.

Variables: tipo_inmueble (dummies), barrio (dummies), habitaciones,
banos, metros_cuadrados, menciona_problemas_estructurales,
cantidad_palabras.

Salidas:
  graficos/codo_caracteristicas.png
  graficos/clusters_caracteristicas.png
  resultados/clustering_caracteristicas.txt

Uso:  .venv\Scripts\python.exe scripts\clustering_caracteristicas.py
"""

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin display: genera PNG, no ventanas
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ORIGEN = Path("data/processed/playa_limpio_v2.csv")
DIR_GRAFICOS = Path("graficos")
DIR_RESULTADOS = Path("resultados")
RANDOM_STATE = 42

VARIABLES = [
    "habitaciones",
    "banos",
    "metros_cuadrados",
    "menciona_problemas_estructurales",
    "cantidad_palabras",
]
CATEGORICAS = ["tipo_inmueble", "barrio"]


def imputar_por_tipo(df: pd.DataFrame, columna: str) -> pd.Series:
    """
    Imputa nulos con la mediana de su tipo_inmueble.
    Si un tipo no tiene ninguno, cae a la mediana global.
    """
    original = df[columna]
    if original.notna().sum() == 0:
        return original.fillna(0.0)

    mediana_global = original.median()
    relleno = original.copy()

    for tipo in df["tipo_inmueble"].unique():
        mascara = df["tipo_inmueble"] == tipo
        mediana_tipo = original[mascara].median()
        if pd.isna(mediana_tipo):
            relleno = relleno.fillna(
                {i: mediana_global for i in original[mascara].isna().index}
            )
        else:
            relleno = relleno.fillna(
                {i: mediana_tipo for i in original[mascara].isna().index}
            )
    return relleno


def main() -> None:
    DIR_GRAFICOS.mkdir(exist_ok=True)
    DIR_RESULTADOS.mkdir(exist_ok=True)

    df = pd.read_csv(ORIGEN, encoding="utf-8-sig")
    lineas = []
    def p(t=""):
        print(t)
        lineas.append(t)

    p("=" * 78)
    p("CLUSTERING EXPLORATORIO DE PLAYA (sin usar el precio)")
    p("=" * 78)
    p(f"Origen: {ORIGEN}  ({len(df)} filas)")
    p()

    # ── 1. IMPUTACIÓN ────────────────────────────────────────────────────────
    p("1) IMPUTACIÓN DE NULOS")
    p("-" * 78)
    p(f'{"columna":32} {"nulos":>7} {"mediana global":>16}  método')
    for col in ["habitaciones", "banos", "metros_cuadrados"]:
        n = int(df[col].isna().sum())
        med = df[col].median()
        df[col] = imputar_por_tipo(df, col)
        restantes = int(df[col].isna().sum())
        nota = "mediana por tipo_inmueble" if restantes == 0 else f"QUEDAN {restantes} nulos"
        p(f"{col:32} {n:>7} {med:>16.1f}  {nota}")

    n_bar = int((df["barrio"] == "Desconocido").sum())
    p(f'{"barrio":32} {n_bar:>7} {"-":>16}  rellenado con "Desconocido"')
    p()

    # ── 2. CODIFICACIÓN ──────────────────────────────────────────────────────
    p("2) CODIFICACIÓN")
    p("-" * 78)
    df["menciona_problemas_estructurales"] = (
        df["menciona_problemas_estructurales"].astype(int)
    )
    dummies = pd.get_dummies(df[CATEGORICAS], prefix=CATEGORICAS, dtype=int)
    p(f"tipo_inmueble -> {dummies.shape[1]} dummies "
      f"({df['tipo_inmueble'].nunique()} categorías)")
    p(f"barrio         -> {dummies.shape[1] - df['tipo_inmueble'].nunique()} dummies "
      f"({df['barrio'].nunique()} categorías)")
    p(f"problemas_estructurales: {df['menciona_problemas_estructurales'].value_counts().to_dict()}")
    p()

    X = pd.concat([df[VARIABLES].reset_index(drop=True), dummies], axis=1)
    p(f"Variables totales para el clustering: {X.shape[1]}")
    p(f"  continuas : {VARIABLES}")
    p(f"  dummies    : {list(dummies.columns)}")
    p()

    # ── 3. ESTANDARIZACIÓN ───────────────────────────────────────────────────
    escalador = StandardScaler()
    X_scaled = escalador.fit_transform(X)
    p("3) ESTANDARIZACIÓN (StandardScaler, media 0 y varianza 1)")
    p("-" * 78)
    p("  Medias post-escalado (deben ser ~0):")
    for col, m in zip(X.columns, X_scaled.mean(axis=0)):
        p(f"    {col:34} {m:>10.6f}")
    p()

    # ── 4. MÉTODO DEL CODO ───────────────────────────────────────────────────
    p("4) MÉTODO DEL CODO")
    p("-" * 78)
    ks = list(range(2, 7))
    inercias = []
    for k in ks:
        km = KMeans(n_clusters=k, n_init=20, random_state=RANDOM_STATE)
        km.fit(X_scaled)
        inercias.append(km.inertia_)
    p(f'{"K":>3} {"inercia":>14} {"caida":>14} {"% varianza":>12}')
    for i, k in enumerate(ks):
        caida = inercias[i - 1] - inercias[i] if i > 0 else 0.0
        pct = 100 * caida / inercias[i - 1] if i > 0 and inercias[i - 1] else 0.0
        p(f"{k:>3} {inercias[i]:>14,.0f} {caida:>14,.0f} {pct:>11.1f}%")

    k_optimo = ks[int(np.argmax(np.diff(inercias)))]
    p()
    p(f"  K óptimo (mayor caída de inercia): K = {k_optimo}")
    p()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ks, inercias, "o-", color="#f16724", linewidth=2.5, markersize=9)
    for k, ine in zip(ks, inercias):
        ax.annotate(f"K={k}\n{ine:,.0f}", (k, ine),
                    textcoords="offset points", xytext=(8, 10), fontsize=9)
    ax.axvline(k_optimo, color="#2c3e50", linestyle="--", linewidth=1.5,
               label=f"K óptimo = {k_optimo}")
    ax.set_xlabel("Número de clústeres (K)")
    ax.set_ylabel("Inercia (suma de distancias cuadradas al centroide)")
    ax.set_title("Método del codo — Playa, variables características (sin precio)")
    ax.legend()
    ax.grid(alpha=0.3)
    sns.despine()
    ruta_codo = DIR_GRAFICOS / "codo_caracteristicas.png"
    fig.tight_layout()
    fig.savefig(ruta_codo, dpi=150)
    plt.close(fig)
    p(f"  Gráfico guardado: {ruta_codo}")
    p()

    # ── 5. K-MEANS ───────────────────────────────────────────────────────────
    p("5) K-MEANS")
    p("-" * 78)
    modelo = KMeans(n_clusters=k_optimo, n_init=20, random_state=RANDOM_STATE)
    df["cluster_caracteristicas"] = modelo.fit_predict(X_scaled)
    p(f"  Modelo entrenado con K = {k_optimo}, n_init=20, seed={RANDOM_STATE}")
    p(f"  Inercia final: {modelo.inertia_:,.0f}")
    p(f"  Distribución de clústeres: {df['cluster_caracteristicas'].value_counts().sort_index().to_dict()}")
    p()

    # ── 6. PCA ───────────────────────────────────────────────────────────────
    p("6) VISUALIZACIÓN PCA")
    p("-" * 78)
    pca = PCA(n_components=2)
    coords = pca.fit_transform(X_scaled)
    varianza = pca.explained_variance_ratio_ * 100
    p(f"  PC1 explica {varianza[0]:.1f}% de la varianza")
    p(f"  PC2 explica {varianza[1]:.1f}% de la varianza")
    p(f"  Total explicado: {varianza.sum():.1f}%")
    p()
    p("  Cargas principales (contribución a cada componente):")
    cargas = pd.DataFrame(pca.components_.T, index=X.columns, columns=["PC1", "PC2"])
    cargas["PC1_abs"] = cargas["PC1"].abs()
    for col in cargas.sort_values("PC1_abs", ascending=False).head(8).index:
        p(f"    {col:34} PC1={cargas.loc[col,'PC1']:>7.3f}  PC2={cargas.loc[col,'PC2']:>7.3f}")
    p()

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.scatterplot(
        x=coords[:, 0], y=coords[:, 1],
        hue=df["cluster_caracteristicas"].astype(str),
        palette="Set2", s=110, alpha=0.85, ax=ax,
    )
    # Centroides en el espacio del PCA
    for i, centroide in enumerate(modelo.cluster_centers_):
        pc = pca.transform(centroide.reshape(1, -1))[0]
        ax.scatter(*pc, marker="X", s=420, c="black",
                   edgecolors="white", linewidths=2, zorder=5)
        ax.annotate(f"Centroide {i}", pc, textcoords="offset points",
                    xytext=(14, 12), fontsize=10, fontweight="bold")
    ax.set_xlabel(f"PC1 ({varianza[0]:.1f}% de la varianza)")
    ax.set_ylabel(f"PC2 ({varianza[1]:.1f}% de la varianza)")
    ax.set_title(f"Clústeres de Playa por características (K={k_optimo}, sin precio)")
    ax.legend(title="Clúster", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(alpha=0.25)
    sns.despine()
    fig.tight_layout()
    ruta_pca = DIR_GRAFICOS / "clusters_caracteristicas.png"
    fig.savefig(ruta_pca, dpi=150)
    plt.close(fig)
    p(f"  Gráfico guardado: {ruta_pca}")
    p()

    # ── 7. INTERPRETACIÓN ────────────────────────────────────────────────────
    p("7) INTERPRETACIÓN POR CLÚSTER")
    p("=" * 78)
    for c in sorted(df["cluster_caracteristicas"].unique()):
        g = df[df["cluster_caracteristicas"] == c]
        p()
        p(f"  +-- CLUSTER {c}  (n = {len(g)}, {100*len(g)/len(df):.1f}% del total)")
        p("  |")
        tipo_modo = g["tipo_inmueble"].mode()[0]
        tipo_n = int((g["tipo_inmueble"] == tipo_modo).sum())
        barrio_modo = g["barrio"].mode()[0]
        barrio_n = int((g["barrio"] == barrio_modo).sum())
        p(f"  |  Tipo mas comun     : {tipo_modo} ({tipo_n}/{len(g)})")
        p(f"  |  Barrio mas comun   : {barrio_modo} ({barrio_n}/{len(g)})")
        p(f"  |  Habitaciones prom.  : {g['habitaciones'].mean():.1f}")
        p(f"  |  Banos prom.        : {g['banos'].mean():.1f}")
        p(f"  |  m2 promedio        : {g['metros_cuadrados'].mean():.0f}")
        p(f"  |  Con problemas      : {100*g['menciona_problemas_estructurales'].mean():.1f}%")
        p(f"  |  Palabras prom.     : {g['cantidad_palabras'].mean():.0f}")
        p(f"  |  Precio mediana     : {g['precio_usd'].median():,.0f} USD  (solo referencia)")
        p("  +")
    p()

    p("TABLA COMPARATIVA")
    p("-" * 78)
    resumen = df.groupby("cluster_caracteristicas").agg(
        n=("url", "size"),
        tipo_modo=("tipo_inmueble", lambda s: s.mode()[0]),
        barrio_modo=("barrio", lambda s: s.mode()[0]),
        hab_prom=("habitaciones", "mean"),
        banos_prom=("banos", "mean"),
        m2_prom=("metros_cuadrados", "mean"),
        pct_problemas=("menciona_problemas_estructurales", lambda s: 100 * s.mean()),
        palabras_prom=("cantidad_palabras", "mean"),
        precio_mediana=("precio_usd", "median"),
    ).round(1)
    p(resumen.to_string())
    p()

    # Calidad del m2: se separan los que lo tenían del que se imputó
    df["m2_imputado"] = pd.read_csv(ORIGEN, encoding="utf-8-sig")["metros_cuadrados"].isna()
    p("NOTA SOBRE CALIDAD DE DATOS")
    p("-" * 78)
    n_imp = int(df["m2_imputado"].sum())
    p(f"  m² era nulo y se imputó: {n_imp}/{len(df)} ({100*n_imp/len(df):.1f}%)")
    p(f"  m² real observado      : {len(df)-n_imp}/{len(df)} ({100*(len(df)-n_imp)/len(df):.1f}%)")
    n_desc = int((df["barrio"] == "Desconocido").sum())
    p(f"  barrio 'Desconocido'   : {n_desc}/{len(df)} ({100*n_desc/len(df):.1f}%)")
    p()
    p("  ADVERTENCIA: el dummy de barrio 'Desconocido' domina el conjunto,")
    p("  por lo que esa variable aporta poca información al clustering.")
    p("=" * 78)

    # Guardar informe
    ruta_txt = DIR_RESULTADOS / "clustering_caracteristicas.txt"
    ruta_txt.write_text("\n".join(lineas), encoding="utf-8")
    print(f"\nInforme guardado: {ruta_txt}")

    # Guardar dataset con el cluster
    salida = Path("data/processed/playa_clusterizado.csv")
    df.drop(columns=["m2_imputado"]).to_csv(salida, index=False, encoding="utf-8-sig")
    print(f"Dataset con cluster: {salida}")


if __name__ == "__main__":
    main()
