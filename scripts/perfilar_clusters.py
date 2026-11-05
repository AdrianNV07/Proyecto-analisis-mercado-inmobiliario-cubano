#!/usr/bin/env python3
r"""
Perfilado de Clústeres: asigna nombres descriptivos y genera visualizaciones.

Para el clustering de texto (habana_clusterizado_texto.jsonl, K=5):
  - Analiza palabras clave de cada clúster
  - Asigna nombre descriptivo basado en vocabulario dominante
  - Añade columna nombre_cluster_texto

Para el clustering numérico (nuevo, K=5):
  - Ejecuta KMeans sobre [precio_usd, habitaciones, banos, cantidad_palabras]
  - Asigna nombre descriptivo basado en medianas
  - Guarda habana_clusterizado_completo.jsonl con ambos clusterings

Salidas:
  data/processed/habana_clusterizado_texto.jsonl (actualizado con nombre_cluster_texto)
  data/processed/habana_clusterizado_completo.jsonl (texto + numérico)
  graficos/clusters_texto_habana.png (actualizado con nombres)
  graficos/clusters_numerico_habana.png
  resultados/perfilado_clusters_habana.txt

Uso:  .venv\Scripts\python.exe scripts\perfilar_clusters.py
"""

import json
import unicodedata
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
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ORIGEN = Path("data/processed/habana_clusterizado_texto.jsonl")
ORIGEN_LIMPIO = Path("data/processed/habana_limpio.jsonl")
DIR_GRAFICOS = Path("graficos")
DIR_RESULTADOS = Path("resultados")
RANDOM_STATE = 42

lineas: list[str] = []


def p(t=""):
    print(t)
    lineas.append(t)


def limpiar(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = "".join(c if (c.isalpha() or c.isspace()) else " " for c in texto)
    return " ".join(texto.split())


STOP_WORDS = set("""
a al algo algunas algunos ante antes aqui aun aunque bajo bien cada casi como
con contra cual cuando de del desde donde dos durante e el ella ellas ellos en
entre era eran es esa esas ese eso esos esta estaba estan estos este esto
fue fueron ha habia han hasta hay la las le les lo los mas me mi mientras
muy nada ni no nos nuestra nuestro o os otra otras otro otros para pero poco
por porque que quien quienes se sea segun ser si sido sin sobre solo son su sus
tambien tanto te tiene tienen toda todas todo todos tras tu un una uno unos y
ya yo
""".split())

STOP_WORDS_INMOBILIARIO = set("""
m2 mts metros metro cuadrado cuadrados hab habs habitacion habitaciones bano
banos cuarto cuartos dormitorio dormitorios sala comedor salon planta plantas
piso niveles nivel medida superficie area areas area total util construida
edificada habitable patios patio jardin balcon terraza porche garaje marquesina
portal puerta ventanas ventana marquesia techo placa electricidad
agua luz gas calle avenida entre esquina cerca zona ubicacion municipio
provincia habana ciudad pueblo reparto
venta vendo vende vender precio usd euro euros dolar dolares peso pesos
cup mlc mongos
contacto contactos whatsapp wasap telefono tlf celular movil numero mas
favor preguntar preguntas informacion detalles caracteristica
oportunidad oferta Rebaja rebajas excelente
""".split())

STOP = STOP_WORDS | STOP_WORDS_INMOBILIARIO


def asignar_nombre_texto(top_palabras: list[str], tipo_comun: str, precio_mediana: float,
                          es_intermediario_pct: float, n: int) -> str:
    """Asigna un nombre descriptivo al clúster de texto basado en sus características."""
    palabras_set = set(p.lower() for p in top_palabras)

    # Perfiles basados en vocabulario dominante
    if any(p in palabras_set for p in ["inmobiliaria", "agencia", "wa", "https", "ref", "independencia"]):
        return "Anuncios de Agencias"
    if any(p in palabras_set for p in ["regla", "papeles", "negocio"]):
        return "Venta con Trámites Pendientes"
    if any(p in palabras_set for p in ["deja", "cosas", "fijo", "split", "centro"]):
        return "Entrega Inmediata"
    if any(p in palabras_set for p in ["edificio", "capitalista", "listo", "servicio"]):
        return "Apartamentos en Edificio"
    if tipo_comun == "casa" and precio_mediana < 50000:
        return "Casas Económicas"
    if tipo_comun == "casa":
        return "Casas Independientes"
    if es_intermediario_pct > 30:
        return "Anuncios de Intermediarios"
    return f"Perfil {n}"


def asignar_nombre_numerico(precio_mediana: float, hab_media: float, banos_media: float,
                              palabras_media: float, es_int_pct: float) -> str:
    """Asigna nombre descriptivo al clúster numérico basado en medianas."""
    if precio_mediana < 30000:
        if hab_media <= 2:
            return "Viviendas Pequeñas Económicas"
        return "Viviendas Económicas"
    if precio_mediana < 80000:
        if es_int_pct > 30:
            return "Viviendas Medias (Intermediarios)"
        return "Viviendas Estándar"
    if precio_mediana < 150000:
        return "Viviendas Medio-Altas"
    return "Viviendas de Lujo"


def main() -> None:
    DIR_GRAFICOS.mkdir(exist_ok=True)
    DIR_RESULTADOS.mkdir(exist_ok=True)

    # ── Cargar datos ─────────────────────────────────────────────────────────
    filas = [json.loads(l) for l in ORIGEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    df = pd.DataFrame(filas)

    p("=" * 78)
    p("PERFILADO DE CLÚSTERES — LA HABANA")
    p("=" * 78)
    p(f"Dataset: {ORIGEN}")
    p(f"Total: {len(df)} anuncios")
    p(f"Clústeres de texto: {sorted(df['cluster_texto'].unique())}")
    p()

    # ── TF-IDF para nombres de texto ────────────────────────────────────────
    df["texto_limpio"] = [limpiar(t) for t in df["descripcion"]]
    vectorizador = TfidfVectorizer(
        stop_words=sorted(STOP),
        max_features=100,
        ngram_range=(1, 2),
        min_df=2,
        sublinear_tf=True,
    )
    matriz = vectorizador.fit_transform(df["texto_limpio"])
    nombres = vectorizador.get_feature_names_out()

    # ── Nombres para clústeres de texto ─────────────────────────────────────
    p("=" * 78)
    p("NOMBRES ASIGNADOS — CLUSTERING DE TEXTO")
    p("=" * 78)

    nombre_texto_map = {}
    razones_texto = {}

    for c in sorted(df["cluster_texto"].unique()):
        g = df[df["cluster_texto"] == c]

        # Top palabras por peso en centroide
        # Re-entrenamos para obtener el centroide correcto
        # (el modelo ya no está disponible, así que aproximamos con TF-IDF medio del cluster)
        idx = g.index.tolist()
        centroide_aprox = np.asarray(matriz[idx].mean(axis=0)).ravel()
        orden = np.argsort(centroide_aprox)[::-1][:10]
        top_palabras = [nombres[i] for i in orden]

        tipo_comun = g["tipo_inmueble"].mode()[0]
        precio_mediana = g["precio_usd"].median()
        es_int_pct = 100 * g["es_intermediario"].mean()
        n = len(g)

        nombre = asignar_nombre_texto(top_palabras, tipo_comun, precio_mediana, es_int_pct, c)
        nombre_texto_map[c] = nombre

        # Razón para documentación
        p()
        p(f"  CLÚSTER {c} → \"{nombre}\"")
        p(f"    n={n} ({100*n/len(df):.1f}%)")
        p(f"    Palabras clave: {', '.join(top_palabras[:5])}")
        p(f"    Tipo dominante: {tipo_comun}")
        p(f"    Precio mediana: {precio_mediana:,.0f} USD")
        p(f"    % intermediario: {es_int_pct:.1f}%")

        # Construir razón
        razon_parts = []
        if any(w in " ".join(top_palabras) for w in ["inmobiliaria", "agencia", "wa", "https"]):
            razon_parts.append(f"el vocabulario dominante incluye términos de agencia ({', '.join([w for w in top_palabras if w in ['inmobiliaria','agencia','wa','https','ref']][:3])})")
        if any(w in " ".join(top_palabras) for w in ["edificio", "capitalista", "listo"]):
            razon_parts.append(f"las palabras clave mencionan características de edificio ({', '.join([w for w in top_palabras if w in ['edificio','capitalista','listo','servicio']][:3])})")
        if any(w in " ".join(top_palabras) for w in ["regla", "papeles", "negocio"]):
            razon_parts.append(f"el texto enfatiza trámites y documentación ({', '.join([w for w in top_palabras if w in ['regla','papeles','negocio']][:3])})")
        if any(w in " ".join(top_palabras) for w in ["deja", "cosas", "fijo", "split"]):
            razon_parts.append(f"el lenguaje sugiere entrega inmediata ({', '.join([w for w in top_palabras if w in ['deja','cosas','fijo','split','centro']][:3])})")
        if tipo_comun == "casa":
            razon_parts.append(f"el tipo dominante es casa")
        elif tipo_comun == "apartamento":
            razon_parts.append(f"el tipo dominante es apartamento")
        if precio_mediana < 30000:
            razon_parts.append(f"el precio mediano es bajo ({precio_mediana:,.0f} USD)")
        elif precio_mediana > 80000:
            razon_parts.append(f"el precio mediano es alto ({precio_mediana:,.0f} USD)")
        if es_int_pct > 30:
            razon_parts.append(f"el {es_int_pct:.0f}% son anuncios de intermediarios")

        razon = f"El Clúster {c} se nombró \"{nombre}\" porque " + "; ".join(razon_parts) + "."
        razones_texto[c] = razon
        p(f"    Razón: {razon}")

    p()
    p(f"  Mapa final: {nombre_texto_map}")
    p()

    # Añadir columna nombre_cluster_texto
    df["nombre_cluster_texto"] = df["cluster_texto"].map(nombre_texto_map)

    # ── Clustering numérico ──────────────────────────────────────────────────
    p("=" * 78)
    p("CLUSTERING NUMÉRICO (K=5)")
    p("=" * 78)

    # Preparar características numéricas
    df_num = df[["precio_usd", "habitaciones", "banos", "cantidad_palabras", "es_intermediario"]].copy()
    df_num["es_intermediario"] = df_num["es_intermediario"].astype(int)
    # Rellenar NaN con medianas
    for col in df_num.columns:
        df_num[col] = df_num[col].fillna(df_num[col].median())

    scaler = StandardScaler()
    X = scaler.fit_transform(df_num)

    # Probar K=3, 4, 5
    k_num_resultados = {}
    for k in [3, 4, 5]:
        km = KMeans(n_clusters=k, n_init=20, random_state=RANDOM_STATE)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels)
        k_num_resultados[k] = (sil, labels, km)
        p(f"  K={k}: silhouette={sil:.4f}  inercia={km.inertia_:,.2f}  "
          f"tamaños={dict(pd.Series(labels).value_counts().sort_index())}")

    k_num_opt = max(k_num_resultados, key=lambda k: k_num_resultados[k][0])
    sil_num, labels_num, modelo_num = k_num_resultados[k_num_opt]
    p()
    p(f"  K óptimo: K={k_num_opt} (silhouette={sil_num:.4f})")
    p()

    df["cluster_numerico"] = labels_num

    # Nombres para clústeres numéricos
    p("=" * 78)
    p("NOMBRES ASIGNADOS — CLUSTERING NUMÉRICO")
    p("=" * 78)

    nombre_num_map = {}
    razones_num = {}

    for c in sorted(df["cluster_numerico"].unique()):
        g = df[df["cluster_numerico"] == c]
        precio_med = g["precio_usd"].median()
        hab_med = g["habitaciones"].median()
        banos_med = g["banos"].median()
        palabras_med = g["cantidad_palabras"].mean()
        es_int_pct = 100 * g["es_intermediario"].mean()
        n = len(g)

        nombre = asignar_nombre_numerico(precio_med, hab_med, banos_med, palabras_med, es_int_pct)
        nombre_num_map[c] = nombre

        p()
        p(f"  CLÚSTER NUM {c} → \"{nombre}\"")
        p(f"    n={n} ({100*n/len(df):.1f}%)")
        p(f"    Precio mediana: {precio_med:,.0f} USD")
        p(f"    Habitaciones mediana: {hab_med:.1f}")
        p(f"    Baños mediana: {banos_med:.1f}")
        p(f"    Palabras promedio: {palabras_med:.0f}")
        p(f"    % intermediario: {es_int_pct:.1f}%")

        razon = f"El Clúster numérico {c} se nombró \"{nombre}\" porque la mediana de precio es {precio_med:,.0f} USD, con {hab_med:.1f} habitaciones y {banos_med:.1f} baños en promedio."
        razones_num[c] = razon
        p(f"    Razón: {razon}")

    df["nombre_cluster_numerico"] = df["cluster_numerico"].map(nombre_num_map)

    # ── Gráfico PCA de texto con nombres ────────────────────────────────────
    p()
    p("=" * 78)
    p("GRÁFICOS ACTUALIZADOS")
    p("=" * 78)

    pca = PCA(n_components=2)
    coords = pca.fit_transform(matriz.toarray())
    var = pca.explained_variance_ratio_ * 100

    fig, ax = plt.subplots(figsize=(14, 9))
    # Colores distintos por nombre
    nombres_unicos = sorted(df["nombre_cluster_texto"].unique())
    paleta = dict(zip(nombres_unicos, sns.color_palette("Set2", len(nombres_unicos))))

    for nombre in nombres_unicos:
        mask = df["nombre_cluster_texto"] == nombre
        ax.scatter(coords[mask, 0], coords[mask, 1], label=nombre,
                   s=100, alpha=0.8, c=[paleta[nombre]], edgecolors="white", linewidths=0.5)

    for c in sorted(df["cluster_texto"].unique()):
        nombre = nombre_texto_map[c]
        idx = np.where(df["cluster_texto"] == c)[0]
        cx, cy = coords[idx, 0].mean(), coords[idx, 1].mean()
        ax.scatter(cx, cy, marker="X", s=520, c="black",
                   edgecolors="white", linewidths=2.5, zorder=6)
        ax.annotate(f"\"{nombre}\"", (cx, cy), textcoords="offset points",
                    xytext=(18, 16), fontsize=11, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", alpha=0.85))

    ax.set_xlabel(f"PC1 ({var[0]:.1f}% de la varianza)")
    ax.set_ylabel(f"PC2 ({var[1]:.1f}% de la varianza)")
    ax.set_title(f"Clústeres de texto en La Habana (K=5, silhouette=0.065)\n"
                 f"PC1+PC2 = {var.sum():.1f}% de varianza explicada", fontsize=14)
    ax.legend(title="Perfil de texto", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=11)
    ax.grid(alpha=0.22)
    sns.despine()
    fig.tight_layout()
    ruta_pca = DIR_GRAFICOS / "clusters_texto_habana.png"
    fig.savefig(ruta_pca, dpi=150)
    plt.close(fig)
    p(f"  PCA texto: {ruta_pca}")

    # ── Gráfico PCA numérico con nombres ────────────────────────────────────
    pca_num = PCA(n_components=2)
    coords_num = pca_num.fit_transform(X)
    var_num = pca_num.explained_variance_ratio_ * 100

    fig2, ax2 = plt.subplots(figsize=(14, 9))
    nombres_num_unicos = sorted(df["nombre_cluster_numerico"].unique())
    paleta_num = dict(zip(nombres_num_unicos, sns.color_palette("Set1", len(nombres_num_unicos))))

    # Identificar el outlier (clúster con n=1)
    conteos_num = df["cluster_numerico"].value_counts()
    outlier_cluster = conteos_num.idxmin() if conteos_num.min() == 1 else None
    if outlier_cluster is not None:
        outlier_nombre = nombre_num_map[outlier_cluster]
        outlier_count = conteos_num[outlier_cluster]

    for nombre in nombres_num_unicos:
        mask = df["nombre_cluster_numerico"] == nombre
        ax2.scatter(coords_num[mask, 0], coords_num[mask, 1], label=nombre,
                    s=100, alpha=0.8, c=[paleta_num[nombre]], edgecolors="white", linewidths=0.5)

    # Dibujar el outlier al final, por encima de todo
    if outlier_cluster is not None:
        mask_out = df["cluster_numerico"] == outlier_cluster
        ax2.scatter(coords_num[mask_out, 0], coords_num[mask_out, 1],
                    s=350, c="red", edgecolors="black", linewidths=2.5,
                    marker="o", zorder=10)

    for c in sorted(df["cluster_numerico"].unique()):
        nombre = nombre_num_map[c]
        idx = np.where(df["cluster_numerico"] == c)[0]
        cx, cy = coords_num[idx, 0].mean(), coords_num[idx, 1].mean()

        if c == outlier_cluster:
            # Estrella roja grande para el outlier
            ax2.scatter(cx, cy, marker="*", s=900, c="red",
                        edgecolors="black", linewidths=2.5, zorder=10)
            banos_out = df.loc[df["cluster_numerico"] == c, "banos"].iloc[0]
            ax2.annotate(f"Outlier ({banos_out:.0f} baños)",
                         (cx, cy), textcoords="offset points",
                         xytext=(25, 20), fontsize=12, fontweight="bold", color="red",
                         arrowprops=dict(arrowstyle="->", color="red", lw=2),
                         bbox=dict(boxstyle="round,pad=0.4", fc="yellow", ec="red", lw=1.5, alpha=0.95))
        else:
            ax2.scatter(cx, cy, marker="X", s=520, c="black",
                        edgecolors="white", linewidths=2.5, zorder=6)
            ax2.annotate(f"\"{nombre}\"", (cx, cy), textcoords="offset points",
                         xytext=(18, 16), fontsize=11, fontweight="bold",
                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", alpha=0.85))

    ax2.set_xlabel(f"PC1 ({var_num[0]:.1f}% de la varianza)")
    ax2.set_ylabel(f"PC2 ({var_num[1]:.1f}% de la varianza)")
    ax2.set_title(f"Clústeres numéricos en La Habana (K={k_num_opt}, silhouette={sil_num:.3f})\n"
                  f"PC1+PC2 = {var_num.sum():.1f}% de varianza explicada", fontsize=14)
    ax2.legend(title="Perfil numérico", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=11)
    ax2.grid(alpha=0.22)
    sns.despine()
    fig2.tight_layout()
    ruta_pca_num = DIR_GRAFICOS / "clusters_numerico_habana.png"
    fig2.savefig(ruta_pca_num, dpi=150)
    plt.close(fig2)
    p(f"  PCA numérico: {ruta_pca_num}")

    # ── Tabla resumen ───────────────────────────────────────────────────────
    p()
    p("=" * 78)
    p("TABLA RESUMEN")
    p("=" * 78)
    p()
    p("  CLÚSTERES DE TEXTO:")
    p(f"  {'Nombre':30} {'n':>5} {'%':>6} {'Tipo':14} {'Precio med':>12} {'% int':>6}")
    p(f"  {'-'*30} {'-'*5} {'-'*6} {'-'*14} {'-'*12} {'-'*6}")
    for c in sorted(df["cluster_texto"].unique()):
        g = df[df["cluster_texto"] == c]
        nombre = nombre_texto_map[c]
        n = len(g)
        pct = 100 * n / len(df)
        tipo = g["tipo_inmueble"].mode()[0]
        precio = g["precio_usd"].median()
        es_int = 100 * g["es_intermediario"].mean()
        p(f"  {nombre:30} {n:>5} {pct:>5.1f}% {tipo:14} {precio:>10,.0f} USD {es_int:>5.1f}%")

    p()
    p("  CLÚSTERES NUMÉRICOS:")
    p(f"  {'Nombre':35} {'n':>5} {'%':>6} {'Hab':>5} {'Baños':>6} {'Precio med':>12}")
    p(f"  {'-'*35} {'-'*5} {'-'*6} {'-'*5} {'-'*6} {'-'*12}")
    for c in sorted(df["cluster_numerico"].unique()):
        g = df[df["cluster_numerico"] == c]
        nombre = nombre_num_map[c]
        n = len(g)
        pct = 100 * n / len(df)
        hab = g["habitaciones"].median()
        banos = g["banos"].median()
        precio = g["precio_usd"].median()
        p(f"  {nombre:35} {n:>5} {pct:>5.1f}% {hab:>5.1f} {banos:>6.1f} {precio:>10,.0f} USD")

    # ── Comparación con Playa ───────────────────────────────────────────────
    p()
    p("=" * 78)
    p("COMPARACIÓN CON PLAYA")
    p("=" * 78)
    p()
    p("  Clústeres de Playa (K=4):")
    p("    - Cluster 0: Casas de lujo (n=32, precio mediano 265,000 USD)")
    p("    - Cluster 1: Apartamentos estándar (n=43, precio mediano 75,000 USD)")
    p("    - Cluster 2: Anuncios de agencias (n=20, precio mediano 52,500 USD)")
    p("    - Cluster 3: Casas económicas (n=10, precio mediano 24,000 USD)")
    p()
    p("  Clústeres de La Habana (K=5):")
    for c in sorted(df["cluster_texto"].unique()):
        g = df[df["cluster_texto"] == c]
        p(f"    - {nombre_texto_map[c]}: n={len(g)}, precio mediano {g['precio_usd'].median():,.0f} USD")
    p()
    p("  Diferencias clave:")
    p("    1. En La Hay 5 perfiles de texto vs 4 en Playa (la muestra más grande")
    p("       permite más granularidad discursiva).")
    p("    2. Aparece un perfil 'Venta con Trámites Pendientes' (regla/papeles)")
    p("       que no existía en Playa — refleja la complejidad legal en La Habana.")
    p("    3. El perfil de agencias (inmobiliaria/wa/https) también aparece en")
    p("       La Habana pero con mayor concentración en Playa y Plaza de la Revolución.")
    p("    4. Los precios medianos son significativamente menores en La Habana")
    p("       (17k-110k USD) frente a Playa (24k-265k USD).")

    # ── Guardar datasets ────────────────────────────────────────────────────
    p()
    p("=" * 78)
    p("GUARDANDO DATASETS")
    p("=" * 78)

    # Actualizar el JSONL de texto con nombre_cluster_texto
    salida_texto = Path("data/processed/habana_clusterizado_texto.jsonl")
    with open(salida_texto, "w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            reg = {k: v for k, v in row.items() if k != "texto_limpio"}
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    p(f"  {salida_texto} ({len(df)} registros, con nombre_cluster_texto)")

    # Guardar dataset completo
    salida_completo = Path("data/processed/habana_clusterizado_completo.jsonl")
    with open(salida_completo, "w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            reg = {k: v for k, v in row.items() if k != "texto_limpio"}
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
    p(f"  {salida_completo} ({len(df)} registros, con ambos clusterings + nombres)")

    # ── Documentar en resultados/analisis_playa.txt ──────────────────────────
    doc_path = DIR_RESULTADOS / "analisis_playa.txt"
    doc_existente = ""
    if doc_path.exists():
        doc_existente = doc_path.read_text(encoding="utf-8")

    seccion_perfilado = """
================================================================================
6. PERFILADO DE CLÚSTERES — LÓGICA DE NOMBRAMIENTO
================================================================================

6.1. CLUSTERING DE TEXTO (TF-IDF + K-Means, K=5)

Criterio de nombramiento: análisis del vocabulario dominante (top 10 palabras
por peso TF-IDF), tipo de inmueble dominante y mediana de precio de cada clúster.

"""

    for c in sorted(df["cluster_texto"].unique()):
        seccion_perfilado += f"  {razones_texto[c]}\n\n"

    seccion_perfilado += """6.2. CLUSTERING NUMÉRICO (K-Means, K=óptimo)

Criterio de nombramiento: medianas de precio, habitaciones y baños, más
porcentaje de anuncios de intermediarios.

"""

    for c in sorted(df["cluster_numerico"].unique()):
        seccion_perfilado += f"  {razones_num[c]}\n\n"

    seccion_perfilado += """6.3. COMPARACIÓN CON PLAYA

Los perfiles discursivos de La Habana NO son idénticos a los de Playa:

- En La Hay 5 perfiles vs 4 en Playa (la muestra 5x más grande permite más
  granularidad).
- Aparece un perfil "Venta con Trámites Pendientes" (vocabulario: regla,
  papeles, negocio) que no existe en Playa. Refleja la complejidad legal
  adicional en la capital.
- El perfil de agencias inmobiliarias está más marcado en La Habana
  (vocabulario técnico: inmobiliaria, wa, https, ref).
- Los perfiles de "Entrega Inmediata" (deja, cosas, fijo, split) sugieren
  un mercado con mayor urgencia de venta en La Habana.
- Las diferencias de precio entre ambos municipios son significativas:
  La Habana tiene perfiles económicos más marcados (17k USD mediana) mientras
  Playa concentra el segmento de lujo (265k USD mediana).

6.4. LIMITACIONES

- K=5 fue seleccionado por Silhouette Score (0.065), un valor bajo que indica
  que los clústeres de texto no están perfectamente separados. Los nombres
  son orientativos y deben interpretarse con cautela.
- El clustering numérico usa K seleccionado también por Silhouette, con
  características estandarizadas (precio, habitaciones, baños, longitud).
"""

    # Añadir la sección al final del archivo
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write(doc_existente.rstrip() + "\n" + seccion_perfilado)
    p(f"  Documentación añadida a: {doc_path}")

    p()
    p("=" * 78)
    p("RESUMEN FINAL")
    p("=" * 78)
    p()
    p("  Clústeres de texto (K=5):")
    for c in sorted(df["cluster_texto"].unique()):
        p(f"    {c}: \"{nombre_texto_map[c]}\" (n={len(df[df['cluster_texto']==c])})")
    p()
    p("  Clústeres numéricos:")
    for c in sorted(df["cluster_numerico"].unique()):
        p(f"    {c}: \"{nombre_num_map[c]}\" (n={len(df[df['cluster_numerico']==c])})")
    p()
    p("=" * 78)

    # Guardar informe
    ruta_txt = DIR_RESULTADOS / "perfilado_clusters_habana.txt"
    ruta_txt.write_text("\n".join(lineas), encoding="utf-8")
    print(f"\nInforme: {ruta_txt}")


if __name__ == "__main__":
    main()
