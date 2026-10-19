#!/usr/bin/env python3
r"""
Clustering de texto de los anuncios de Playa (TF-IDF + K-Means).

A diferencia del clustering numérico (que solo reetiquetaba
tipo_inmueble), aquí se trabaja sobre el TEXTO de las descripciones,
que es donde vive la información sobre urgencia, estado del inmueble y
motivo de venta que las variables numéricas no tocan.

Pipeline:
  1. Limpieza (minúsculas, sin puntuación, sin palabras vacías).
  2. TF-IDF con max_features=100.
  3. KMeans con K=3 y K=4; se elige por Silhouette Score.
  4. Top 10 palabras por clúster, según el peso en el centroide.
  5. PCA 2D para visualizar.

Salidas:
  graficos/clusters_texto.png
  resultados/clustering_texto.txt
  data/processed/playa_clusterizado_texto.csv

Uso:  .venv\Scripts\python.exe scripts\clustering_texto.py
"""

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score

warnings.filterwarnings("ignore")

ORIGEN = Path("data/processed/playa_limpio_v2.csv")
DIR_GRAFICOS = Path("graficos")
DIR_RESULTADOS = Path("resultados")
RANDOM_STATE = 42
MAX_FEATURES = 100
K_CANDIDATOS = [3, 4]

lineas: list[str] = []


def p(t=""):
    print(t)
    lineas.append(t)


def limpiar(texto: str) -> str:
    """
    Minúsculas, sin puntuación y sin palabras vacías del español.

    Se usa la lista de stop words de sklearn (español), ampliada con
    términos que aparecen en todos los anuncios de inmobiliaria y que no
    aportan nada: medidas, sustantivos genéricos del sector y unidades.
    """
    if not isinstance(texto, str):
        return ""
    texto = texto.lower()
    # Sustituye cualquier cosa que no sea letra o espacio (incluye acentos
    # convertidos a 'nfkd' antes de eliminar el diacrítico).
    import unicodedata

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = "".join(c if (c.isalpha() or c.isspace()) else " " for c in texto)
    return " ".join(texto.split())


# Stop words en español.
#
# sklearn NO incluye lista española para TfidfVectorizer (solo 'english'),
# y NLTK no esta instalado. Se usa una lista propia, ampliada con el
# vocabulario genérico del sector inmobiliario que aparece en casi todos
# los anuncios y por tanto no distingue entre clústeres.
STOP_WORDS = set("""
a al algo algunas algunos ante antes aqui aun aunque bajo bien cada casi como
con contra cual cuando de del desde donde dos durante e el ella ellas ellos en
entre era eran es esa esas ese eso esos esta estaba estan estas este esto estos
estoy fue fueron ha habia han hasta hay la las le les lo los mas me mi mientras
muy nada ni no nos nuestra nuestro o os otra otras otro otros para pero poco
por porque que quien quienes se sea segun ser si sido sin sobre solo son su sus
también tanto te tiene tienen toda todas todo todos tras tu un una uno unos y
ya yo
""".split())

# Terminología del sector que no aporta información discriminante
STOP_WORDS_INMOBILIARIO = set("""
m2 mts metros metro cuadrado cuadrados hab habs habitacion habitaciones bano
banos cuarto cuartos dormitorio dormitorios sala comedor salon planta plantas
piso niveles nivel medida superficie areaAREAS area total util construida
edificada habitable patios patio jardin balcon terraza porche garaje marquesina
portal puerta ventanas ventana marqueteria techo placa piso piso ELECTRICIDAD
agua luz gas calle avenida entre esquina cerca zona ubicacion municipio
provincia habana ciudad pueblo reparto reparto
venta vendo vende vender vendo precio usd euro euros dolar dolares peso pesos
cup mlc mongos
contacto contactos whatsapp wasap telefono tlf celular movil numero mas
favor preguntar preguntas informacion detalles caracteristica detalles
oportunidad oferta Rebaja rebajas precio Excelente excelente chino_clientista
""".split())

STOP = STOP_WORDS | STOP_WORDS_INMOBILIARIO


def main() -> None:
    DIR_GRAFICOS.mkdir(exist_ok=True)
    DIR_RESULTADOS.mkdir(exist_ok=True)

    df = pd.read_csv(ORIGEN, encoding="utf-8-sig")

    p("=" * 78)
    p("CLUSTERING DE TEXTO DE PLAYA (TF-IDF + K-Means)")
    p("=" * 78)
    p(f"Origen: {ORIGEN}  ({len(df)} anuncios)")
    p()

    # ── 1. LIMPIEZA ──────────────────────────────────────────────────────────
    p("1) LIMPIEZA DE TEXTO")
    p("-" * 78)
    df["texto_limpio"] = [limpiar(t) for t in df["descripcion"]]
    palabras = df["texto_limpio"].str.split().str.len()
    p(f"  longitud media : {palabras.mean():.0f} palabras por anuncio")
    p(f"  longitud mín/ máx: {palabras.min()} / {palabras.max()}")
    vacios = int((df["texto_limpio"].str.len() == 0).sum())
    p(f"  documentos vacíos tras limpiar: {vacios}")
    p("  ejemplo:")
    ejemplo = next((t for t in df["texto_limpio"] if len(t) > 120), "")
    p(f"    {ejemplo[:150]}...")
    p()

    # ── 2. TF-IDF ────────────────────────────────────────────────────────────
    p("2) VECTORIZACIÓN TF-IDF")
    p("-" * 78)
    vectorizador = TfidfVectorizer(
        stop_words=sorted(STOP),
        max_features=MAX_FEATURES,
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
    )
    matriz = vectorizador.fit_transform(df["texto_limpio"])
    nombres = vectorizador.get_feature_names_out()
    p(f"  documentos: {matriz.shape[0]}")
    p(f"  términos  : {matriz.shape[1]}  (max_features={MAX_FEATURES}, min_df=2)")
    p(f"  bigramas incluidos: ngram_range=(1, 2)")
    p(f"  densidad de la matriz: {matriz.nnz / (matriz.shape[0]*matriz.shape[1]):.4f}")
    p()
    p("  10 términos más frecuentes (mayor peso medio en el corpus):")
    pesos = np.asarray(matriz.mean(axis=0)).ravel()
    for i in np.argsort(pesos)[::-1][:10]:
        p(f"    {nombres[i]:28} {pesos[i]:.4f}")
    p()

    # ── 3. K-MEANS Y SELECCIÓN POR SILHOUETTE ───────────────────────────────
    p("3) K-MEANS — selección por Silhouette Score")
    p("-" * 78)
    resultados = {}
    for k in K_CANDIDATOS:
        km = KMeans(n_clusters=k, n_init=20, random_state=RANDOM_STATE)
        etiquetas = km.fit_predict(matriz)
        sil = silhouette_score(matriz, etiquetas)
        resultados[k] = (sil, etiquetas, km)
        p(f"  K={k}: silhouette={sil:.4f}  inercia={km.inertia_:,.2f}  "
          f"tamaños={dict(pd.Series(etiquetas).value_counts().sort_index())}")

    k_optimo = max(resultados, key=lambda k: resultados[k][0])
    sil_opt, etiquetas, modelo = resultados[k_optimo]
    p()
    p(f"  K óptimo por silhouette: K = {k_optimo}  (score={sil_opt:.4f})")
    if abs(resultados[3][0] - resultados[4][0]) < 0.05:
        p("  AVISO: la diferencia entre K=3 y K=4 es pequeña (<0.05);")
        p("          la elección de K es poco robusta.")
    p()

    df["cluster_texto"] = etiquetas

    # ── 4. TOP 10 PALABRAS POR CLÚSTER ──────────────────────────────────────
    p("4) TOP 10 PALABRAS POR CLÚSTER (peso en el centroide)")
    p("=" * 78)
    tops_por_cluster = {}
    for c in sorted(set(etiquetas)):
        # Centroide del clúster en el espacio TF-IDF
        centroide = modelo.cluster_centers_[c]
        orden = np.argsort(centroide)[::-1][:10]
        top = [(nombres[i], centroide[i]) for i in orden]
        tops_por_cluster[c] = top

        g = df[df["cluster_texto"] == c]
        p()
        p(f"  CLUSTER {c}  (n={len(g)}, {100*len(g)/len(df):.1f}% del total)")
        p(f"  {'término':30} {'peso':>8}")
        p("  " + "-" * 40)
        for palabra, peso in top:
            p(f"  {palabra:30} {peso:>8.4f}")
        p()
        p(f"    tipo más común  : {g['tipo_inmueble'].mode()[0]}")
        p(f"    precio mediana  : {g['precio_usd'].median():,.0f} USD")
        p(f"    palabras prom.  : {g['cantidad_palabras'].mean():.0f}")
        p(f"    con urgencia    : {100*g['menciona_urgencia_viaje'].mean():.1f}%")
        p(f"    con problemas   : {100*g['menciona_problemas_estructurales'].mean():.1f}%")

    # ── 5. PCA ───────────────────────────────────────────────────────────────
    p()
    p("5) PCA 2D")
    p("-" * 78)
    pca = PCA(n_components=2)
    coords = pca.fit_transform(matriz.toarray())
    var = pca.explained_variance_ratio_ * 100
    p(f"  PC1: {var[0]:.1f}%   PC2: {var[1]:.1f}%   total: {var.sum():.1f}%")

    fig, ax = plt.subplots(figsize=(11, 7.5))
    sns.scatterplot(
        x=coords[:, 0], y=coords[:, 1],
        hue=df["cluster_texto"].astype(str),
        palette="Set1", s=130, alpha=0.8, ax=ax,
    )
    for c in sorted(set(etiquetas)):
        idx = np.where(etiquetas == c)[0]
        cx, cy = coords[idx, 0].mean(), coords[idx, 1].mean()
        ax.scatter(cx, cy, marker="X", s=520, c="black",
                   edgecolors="white", linewidths=2.5, zorder=6)
        ax.annotate(f"C{c}\nn={len(idx)}", (cx, cy), textcoords="offset points",
                    xytext=(16, 14), fontsize=11, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", alpha=0.85))
    ax.set_xlabel(f"PC1 ({var[0]:.1f}% de la varianza)")
    ax.set_ylabel(f"PC2 ({var[1]:.1f}% de la varianza)")
    ax.set_title(f"Clústeres de texto en Playa (TF-IDF, K={k_optimo}, "
                 f"silhouette={sil_opt:.3f})")
    ax.legend(title="Clúster", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(alpha=0.22)
    sns.despine()
    fig.tight_layout()
    ruta = DIR_GRAFICOS / "clusters_texto.png"
    fig.savefig(ruta, dpi=150)
    plt.close(fig)
    p(f"  Gráfico guardado: {ruta}")
    p()

    # ── 6. RESUMEN INTERPRETATIVO ───────────────────────────────────────────
    p("6) INTERPRETACIÓN")
    p("=" * 78)
    for c in sorted(set(etiquetas)):
        top = [t for t, _ in tops_por_cluster[c][:6]]
        g = df[df["cluster_texto"] == c]
        p()
        p(f"  Cluster {c}: n={len(g)}")
        p(f"    Vocabulario dominante : {', '.join(top[:4])}")
        p(f"    Tipo de inmueble      : {g['tipo_inmueble'].mode()[0]}")
        p(f"    Precio mediana        : {g['precio_usd'].median():,.0f} USD")
        p(f"    Segmentos de mercado  : {dict(g['segmento_mercado'].value_counts())}")
    p()
    p("=" * 78)

    ruta_txt = DIR_RESULTADOS / "clustering_texto.txt"
    ruta_txt.write_text("\n".join(lineas), encoding="utf-8")
    print(f"\nInforme: {ruta_txt}")

    salida = Path("data/processed/playa_clusterizado_texto.csv")
    df.drop(columns=["texto_limpio"]).to_csv(salida, index=False, encoding="utf-8-sig")
    print(f"Dataset: {salida}")


if __name__ == "__main__":
    main()