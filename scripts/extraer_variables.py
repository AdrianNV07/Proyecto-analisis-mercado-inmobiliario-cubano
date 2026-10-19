#!/usr/bin/env python3
r"""
Extracción de metros_cuadrados y barrio para el estudio de Playa.

Lee data/processed/playa_limpio.csv y produce
data/processed/playa_limpio_v2.csv con dos columnas nuevas:
  - metros_cuadrados: extraído con regex del título y la descripción
  - barrio: topónimo de Playa detectado en el texto

Si un dato no aparece en el texto, se deja como None / "Desconocido".
NO se imputa ningún valor: la imputación por mediana se hace después,
en el paso de clustering, sobre lo que realmente se pudo observar.

Uso:  .venv\Scripts\python.exe scripts\extraer_variables.py
"""

import re
import unicodedata
from pathlib import Path

import pandas as pd

ORIGEN = Path("data/processed/playa_limpio.csv")
DESTINO = Path("data/processed/playa_limpio_v2.csv")

# ─────────────────────────────────────────────────────────────────────────────
# BARRIOS Y ZONAS DEL MUNICIPIO PLAYA
# ─────────────────────────────────────────────────────────────────────────────
# Se listan los topónimos reales del municipio. El orden NO importa: la
# prioridad la decide la posición en el texto, no la del diccionario.
BARRIOS_PLAYA = [
    "Miramar",
    "Siboney",
    "Vedado",
    "Kohly",
    "Alamar",
    "La Punta",
    "Atabey",
    "Jaimanitas",
    "Reparto Náutico",
    "Náutico",
    "Buenavista",
    "Floresta",
    "Fustería",
    "Guanabacoa",
    "Reventazón",
    "Santeurce",
    "La Puntilla",
    "Santa Fe",
    "Alberro",
    "Sans Souci",
    "Barrio Chino",
    "Caleta",
    "Playa Ancha",
    "Ciudad Escolar",
    "Habana del Este",
]


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar topónimos de forma robusta."""
    if not texto or not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.lower()


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACCIÓN DE SUPERFICIE
# ─────────────────────────────────────────────────────────────────────────────

# Patrones de superficie. Se prueban en orden: el más explícito primero.
# Nota: NO seCapturan "m2" cuando en realidad es un año ("2m2" en "2 m2") ni
# precios. Se exige que el número esté seguido de la unidad.
PATRONES_SUPERFICIE = [
    # "948m2", "765.38m2", "150 m2", "1,150.00 m²"
    r"(?P<valor>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros\s*2|metros\s*cuadrados|mts2)",
    # "superficie: 765.38", "área útil: 294.90"
    r"(?:superficie|area|área|extensi[oó]n|metros)\s*(?:util|total|construida|edificada|de\s*la\s*casa|habitable)?\s*[:=]?\s*(?P<valor>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)",
    # "de 300 metros", "unos 400 mts"
    r"(?P<valor>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)\s*(?:metros|mts)\b",
]

# Rangos plausibles para una vivienda en Playa. Fuera de este rango el valor
# se considera un falso positivo (un año, un teléfono, un código postal).
SUPERFICIE_MINIMA = 15.0
SUPERFICIE_MAXIMA = 5000.0


def _a_float(texto_num: str) -> float | None:
    """
    Convierte '765.38' o '1,150.00' a float.

    Se usa el último separador como decimal: en '1,150.00' el punto es
    decimal y la coma es millar; en '765,38' ocurre lo contrario.
    """
    if not texto_num:
        return None
    limpio = texto_num.strip()
    if "," in limpio and "." in limpio:
        # Ambos presentes: el último es el separador decimal
        if limpio.rfind(",") > limpio.rfind("."):
            limpio = limpio.replace(".", "").replace(",", ".")
        else:
            limpio = limpio.replace(",", "")
    elif "," in limpio:
        # Solo coma: si hay 3 dígitos detrás, es millar; si no, decimal
        if len(limpio.split(",")[-1]) == 3:
            limpio = limpio.replace(",", "")
        else:
            limpio = limpio.replace(",", ".")
    try:
        return float(limpio)
    except ValueError:
        return None


def extraer_metros_cuadrados(titulo: str, descripcion: str) -> float | None:
    """
    Extrae la superficie en m² del título y la descripción.

    Se prueba primero el TÍTULO (más conciso y fiable) y después la
    descripción. Devuelve None si no encuentra un valor plausible.
    """
    for texto in (titulo, descripcion):
        if not texto or not isinstance(texto, str):
            continue
        for patron in PATRONES_SUPERFICIE:
            for m in re.finditer(patron, texto, flags=re.IGNORECASE):
                valor = _a_float(m.group("valor"))
                if valor is None:
                    continue
                if SUPERFICIE_MINIMA <= valor <= SUPERFICIE_MAXIMA:
                    return valor
    return None


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACCIÓN DE BARRIO
# ─────────────────────────────────────────────────────────────────────────────

# Topónimos normalizados (sin acentos) -> forma original
BARRIOS_NORMALIZADOS = {normalizar(b): b for b in BARRIOS_PLAYA}

# "Reparto Náutico" se detecta por cualquiera de sus partes.
BARRIOS_ALIAS = [
    (normalizar("Reparto Náutico"), "Reparto Náutico"),
    (normalizar("Reparto Nautico"), "Reparto Náutico"),
]


def extraer_barrio(titulo: str, descripcion: str) -> str:
    """
    Devuelve el topónimo de Playa que aparece PRIMERO en el texto.

    La prioridad es posicional: si un anuncio dice "Siboney, cerca de
    Miramar", devuelve "Siboney", que es donde está la vivienda.
    Si no encuentra ninguno, devuelve "Desconocido".
    """
    # Se busca primero en el título: es más preciso
    for texto in (titulo, descripcion):
        if not texto or not isinstance(texto, str):
            continue
        norm = normalizar(texto)
        mejor_pos, mejor_barrio = None, None
        for clave, original in BARRIOS_NORMALIZADOS.items():
            # Busca por palabra completa para evitar "alamar" dentro de otra
            patron = r"\b" + re.escape(clave) + r"\b"
            m = re.search(patron, norm)
            if m and (mejor_pos is None or m.start() < mejor_pos):
                mejor_pos, mejor_barrio = m.start(), original
        for clave, original in BARRIOS_ALIAS:
            m = re.search(re.escape(clave), norm)
            if m and (mejor_pos is None or m.start() < mejor_pos):
                mejor_pos, mejor_barrio = m.start(), original
        if mejor_barrio:
            return mejor_barrio
    return "Desconocido"


# ─────────────────────────────────────────────────────────────────────────────
# PROCESO
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    df = pd.read_csv(ORIGEN, encoding="utf-8-sig")
    print("=" * 74)
    print("EXTRACCIÓN DE metros_cuadrados Y barrio")
    print("=" * 74)
    print(f"Origen  : {ORIGEN}  ({len(df)} filas)")
    print(f"Destino : {DESTINO}")
    print()

    df["metros_cuadrados"] = [
        extraer_metros_cuadrados(t, d) for t, d in zip(df["titulo"], df["descripcion"])
    ]
    df["barrio"] = [
        extraer_barrio(t, d) for t, d in zip(df["titulo"], df["descripcion"])
    ]

    n_m2 = df["metros_cuadrados"].notna().sum()
    n_barrio = (df["barrio"] != "Desconocido").sum()
    print(f"metros_cuadrados extraídos : {n_m2}/{len(df)}  ({100*n_m2/len(df):.1f}%)")
    print(f"barrio identificado         : {n_barrio}/{len(df)}  ({100*n_barrio/len(df):.1f}%)")
    print()

    if n_m2:
        s = df["metros_cuadrados"]
        print(f"  m²  min={s.min():.0f}  mediana={s.median():.0f}  max={s.max():.0f}")
    print()
    print("Distribución de barrio:")
    print(df["barrio"].value_counts().to_string())
    print()

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DESTINO, index=False, encoding="utf-8-sig")
    print(f"Guardado: {DESTINO}  ({len(df)} filas, {len(df.columns)} columnas)")


if __name__ == "__main__":
    main()
