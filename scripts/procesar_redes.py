#!/usr/bin/env python3
r"""
Procesa los anuncios recolectados en grupos de redes sociales (Pilar 3).

Entrada : data/raw/Anuncios_extraídos.docx
          Es un .docx (Word), NO un .txt: cada anuncio es un bloque de
          párrafos etiquetados, separados por una línea de guiones.
Salida  : data/processed/redes_sociales_limpias.csv

Aplica la MISMA lógica de normalización que el scraper de Revolico,
importándola desde scripts/scraper_revolico.py y scripts/extraer_variables.py
para no duplicar reglas:

  - contiene_keywords  (detección con límites de palabra)
  - extraer_banos / extraer_habitaciones
  - inferir_tipo_inmueble
  - extraer_barrio / extraer_metros_cuadrados

Añade un campo propio del canal: `respaldo_energetico`, porque en los
grupos de compraventa lamention de energía es común y en Revolico no se
medía.

Uso:  .venv\Scripts\python.exe scripts\procesar_redes.py
"""

import csv
import re
import statistics
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from extraer_variables import extraer_barrio, extraer_metros_cuadrados  # noqa: E402
from scraper_revolico import (  # noqa: E402
    PROBLEMAS_ESTRUCTURALES_KEYWORDS,
    URGENCIA_VIAJE_KEYWORDS,
    contiene_keywords,
    extraer_banos,
    extraer_habitaciones,
    inferir_tipo_inmueble,
    normalizar_texto,
)

ORIGEN = Path("data/raw/Anuncios_extraídos.docx")
DESTINO = Path("data/processed/redes_sociales_limpias.csv")

# ---------------------------------------------------------------------------
# Palabras clave propias del canal de redes sociales
# ---------------------------------------------------------------------------

# Respaldo energético: independencias del suministro eléctrico.
# Construido empíricamente sobre los 30 anuncios: "planta" aparece 26
# veces, "solar" y "ecoflow" una vez cada uno.
RESPALDO_ENERGETICO_KEYWORDS = [
    "planta",
    "solar",
    "ecoflow",
    "inversor",
    "bateria",
    "baterias",
    "generador",
    "panel solar",
    "paneles solares",
    "no tiene luz",
    "sin luz",
    "sin energia",
    "sin electricidad",
]

# Infraestructura complementaria (no es respaldo, pero indica inversión).
INFRAESTRUCTURA_KEYWORDS = [
    "cisterna",
    "tanque",
    "motobomba",
    "bomba",
    "pozo",
    "gas de la calle",
    "glicol",
]

CAMPOS_SALIDA = [
    "numero", "titulo", "precio", "moneda", "municipio", "barrio",
    "barrio_referencia",
    "tipo_inmueble", "habitaciones", "banos", "banos_inferido",
    "metros_cuadrados", "descripcion", "fuente", "grupo",
    "menciona_urgencia_viaje", "menciona_problemas_estructurales",
    "respaldo_energetico", "menciona_infraestructura", "url",
]


# ---------------------------------------------------------------------------
# NORMALIZACION DE BARRIOS
# ---------------------------------------------------------------------------

# LosToponimos llegan con grafías distintas entre announceCollectors:
# "Buenavista", "Buena Vista" y "Buenavista (a una cuadra de Avenida 19)" son
# el mismo barrio, igual que "Kholy" y "Kohly". Sin normalizar, el resumen
# los cuenta como categorías distintas y subestima el peso de esas zonas.
#
# La clave es la forma normalizada (sin acentos, sin parentesis, en
# minusculas) y el valor es el topónimo canónico.
BARRIOS_CANONICOS = {
    "buena vista": "Buenavista",
    "buenavista": "Buenavista",
    "kholy": "Kohly",
    "koly": "Kohly",
    "kohly": "Kohly",
    "reparto kholy": "Kohly",
    "reparto koly": "Kohly",
    "reparto kohly": "Kohly",
    "buenavista playa": "Buenavista",
    "la ceiba": "La Ceiba",
    "reparto nautico": "Reparto Náutico",
    "juan manuel marquez": "Juan Manuel Márquez",
}


def normalizar_barrio(valor: str | None) -> tuple[str, str | None]:
    """
    Normaliza un topónimo de barrio.

    Retorna (barrio_canónico, referencia_extra).

    - Si el valor trae información entre paréntesis (por ejemplo
      "Buenavista (a una cuadra de Avenida 19)"), se extrae como referencia
      y se conserva aparte, porque no forma parte del nombre del barrio.
    - Si no está en el diccionario, se devuelve tal cual normalizado.
    """
    if valor is None:
        return "Desconocido", None

    texto = valor.strip()
    if not texto or texto.lower() == "null":
        return "Desconocido", None

    # Extraer y separar lo que va entre paréntesis
    referencia = None
    m = re.search(r"\(([^)]*)\)", texto)
    if m:
        referencia = m.group(1).strip() or None
        texto = re.sub(r"\([^)]*\)", " ", texto)

    clave = re.sub(r"[^a-zA-Záéíóúñ ]", " ", texto)
    clave = " ".join(normalizar_texto(clave).split())

    canonico = BARRIOS_CANONICOS.get(clave)
    if canonico:
        return canonico, referencia

    # Topónimo no catalogado: se devuelve con acentos y capitalización básica
    limpio = " ".join(texto.split())
    return limpio.title() if limpio.islower() else limpio, referencia


# ---------------------------------------------------------------------------
# LECTURA DEL .DOCX
# ---------------------------------------------------------------------------

def leer_parrafos_docx(ruta: Path) -> list[str]:
    """
    Extrae el texto párrafo a párrafo de un .docx sin usar python-docx.

    Un .docx es un ZIP: el texto vive en word/document.xml, con cada
    párrafo en <w:p> y cada fragmento en <w:t>.
    """
    if not ruta.exists():
        sys.exit(f"No existe {ruta}")

    with zipfile.ZipFile(ruta) as z:
        xml = z.read("word/document.xml").decode("utf-8")

    parrafos = []
    for pm in re.finditer(r"<w:p[ >].*?</w:p>", xml, re.S):
        fragmentos = re.findall(r"<w:t[^>]*>(.*?)</w:t>", pm.group(0), re.S)
        texto = "".join(fragmentos)
        for entidad, caracter in [
            ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
            ("&quot;", '"'), ("&apos;", "'"),
        ]:
            texto = texto.replace(entidad, caracter)
        parrafos.append(texto.strip())
    return parrafos


def partir_anuncios(parrafos: list[str]) -> list[list[str]]:
    """
    Divide los párrafos en bloques, uno por anuncio.

    El separador es una línea de guiones ("------"). En algunos puntos
    del documento el separador quedó pegado al inicio del párrafo
    siguiente ("------NÚMERO: 28"), así que también se parte por ahí.
    """
    bloques: list[list[str]] = []
    actual: list[str] = []

    for p in parrafos:
        # Partir si el párrafo empieza con guiones
        if re.match(r"^-{3,}", p):
            # Lo que haya detrás del separador pertenece al anuncio siguiente
            resto = re.sub(r"^-{3,}\s*", "", p)
            if actual:
                bloques.append(actual)
                actual = []
            if resto:
                actual.append(resto)
            continue
        actual.append(p)

    if actual:
        bloques.append(actual)

    # Descartar encabezados sueltos que no contienen "NÚMERO:"
    return [b for b in bloques if any(x.upper().startswith("NÚMERO") for x in b)]


# ---------------------------------------------------------------------------
# EXTRACCIÓN DE CAMPOS
# ---------------------------------------------------------------------------

def _limpiar_valor(v: str) -> str | None:
    """
    Normaliza un valor de campo. Devuelve None si está vacío o es el
    literal "null" que aparece en el documento.
    """
    if v is None:
        return None
    v = v.strip().strip("*").strip()
    if not v or v.lower() == "null" or v == "-":
        return None
    return v


def _a_numero(v: str | None) -> float | None:
    """
    Convierte a número tolerando formatos-PE: '15 000', '7500', '183.24',
    '127 (total) / 114 (útil)'.
    """
    if v is None:
        return None
    limpio = v.replace(" ", "").replace("\u00a0", "")
    # Si hay varios números (ej. "127 (total) / 114 (útil)"), se toma el primero
    m = re.search(r"\d+(?:[.,]\d+)?", limpio)
    if not m:
        return None
    numero = m.group(0)
    # '183.24' decimal; '15.000' sería separador de miles pero aquí el
    # documento usa punto como decimal, así que se respeta tal cual.
    try:
        return float(numero.replace(",", "."))
    except ValueError:
        return None


def _campo(bloque: list[str], etiqueta: str) -> str | None:
    """
    Busca un campo por etiqueta en la primera línea que lo contenga.
    Devuelve el resto de la línea.
    """
    # Se exige el separador ":" tras la etiqueta completa, para que una
    # etiqueta como "BARRIO (si lo dice)" no se lea como "BARRIO" con valor
    # "(si lo dice)".
    patron = re.compile(
        rf"^{re.escape(etiqueta)}\s*:(.*)$", re.IGNORECASE
    )
    for linea in bloque:
        m = patron.match(linea.strip())
        if m:
            return _limpiar_valor(m.group(1))
    return None


def _descripcion(bloque: list[str]) -> str:
    """
    La descripción ocupa todos los párrafos desde la línea 'DESCRIPCIÓN:'
    hasta la línea de URL (o hasta el final del bloque).
    """
    recogiendo = False
    partes: list[str] = []
    for linea in bloque:
        s = linea.strip()
        if re.match(r"^DESCRIPCI[ÓO]N\s*:", s, re.IGNORECASE):
            resto = re.sub(r"^DESCRIPCI[ÓO]N\s*:\s*", "", s, flags=re.IGNORECASE)
            if resto:
                partes.append(resto)
            recogiendo = True
            continue
        if recogiendo:
            # Cortar en la línea de URL
            if re.match(r"^\*?URL\*?\s*:", s, re.IGNORECASE):
                break
            if s:
                partes.append(s)
    return " ".join(partes).strip()


def procesar_bloque(bloque: list[str]) -> dict:
    """Convierte un bloque de párrafos en un registro."""
    titulo = _campo(bloque, "TÍTULO DEL ANUNCIO") or _campo(bloque, "TITULO DEL ANUNCIO")
    numero = _campo(bloque, "NÚMERO")
    grupo = _campo(bloque, "NOMBRE DEL GRUPO")
    fuente = _campo(bloque, "Fuente")
    precio_txt = _campo(bloque, "PRECIO")
    moneda = (_campo(bloque, "MONEDA") or "USD").upper()
    municipio = _campo(bloque, "MUNICIPIO")
    # La etiqueta en el documento es "BARRIO (si lo dice):".
    # Importante: el patrón NO puede ser solo "BARRIO", porque entonces
    # capturaría el texto "(si lo dice)" como si fuera el valor.
    barrio = _campo(bloque, "BARRIO (si lo dice)") or _campo(bloque, "BARRIO")
    tipo_bruto = _campo(bloque, "TIPO DE INMUEBLE")
    hab_txt = _campo(bloque, "HABITACIONES")
    banos_txt = _campo(bloque, "BAÑOS")
    m2_txt = _campo(bloque, "METROS CUADRADOS")
    url = _campo(bloque, "URL")
    descripcion = _descripcion(bloque)

    texto = normalizar_texto(" ".join(filter(None, [titulo, descripcion])))

    # Tipo de inmueble: el documento ya lo declara; si falta, se infiere.
    if tipo_bruto:
        tipo = normalizar_texto(tipo_bruto).split("(")[0].strip()
        tipo = re.sub(r"[^a-z ]", "", tipo).strip() or "otro"
    else:
        tipo = inferir_tipo_inmueble(texto)

    # Habitaciones y baños: si el campo falta o es nulo, se infiere del texto.
    hab = _a_numero(hab_txt)
    if hab is None:
        hab = extraer_habitaciones(texto)
    banos = _a_numero(banos_txt)
    auditoria: dict = {}
    if banos is None:
        banos = extraer_banos(texto, auditoria)
    else:
        auditoria["banos_inferido"] = False

    # metros: si el campo falta, se busca en el texto
    m2 = _a_numero(m2_txt)
    if m2 is None:
        m2 = extraer_metros_cuadrados(titulo or "", descripcion)

    # Si el barrio no viene, se busca en el texto (misma lista que Playa)
    barrio_bruto = barrio or extraer_barrio(titulo or "", descripcion)
    barrio_final, barrio_ref = normalizar_barrio(barrio_bruto)

    return {
        "numero": int(_a_numero(numero)) if _a_numero(numero) else None,
        "titulo": titulo,
        "precio": _a_numero(precio_txt),
        "moneda": moneda,
        "municipio": municipio,
        "barrio": barrio_final,
        "barrio_referencia": barrio_ref,
        "tipo_inmueble": tipo,
        "habitaciones": int(hab) if hab is not None else None,
        "banos": int(banos) if banos is not None else None,
        "banos_inferido": auditoria.get("banos_inferido", False),
        "metros_cuadrados": m2,
        "descripcion": descripcion,
        "fuente": fuente,
        "grupo": grupo,
        "menciona_urgencia_viaje": contiene_keywords(texto, URGENCIA_VIAJE_KEYWORDS),
        "menciona_problemas_estructurales": contiene_keywords(
            texto, PROBLEMAS_ESTRUCTURALES_KEYWORDS
        ),
        "respaldo_energetico": contiene_keywords(texto, RESPALDO_ENERGETICO_KEYWORDS),
        "menciona_infraestructura": contiene_keywords(texto, INFRAESTRUCTURA_KEYWORDS),
        "url": url,
    }


# ---------------------------------------------------------------------------
# PROCESO
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 78)
    print("PROCESAMIENTO DE ANUNCIOS DE REDES SOCIALES (Pilar 3)")
    print("=" * 78)
    print(f"Origen : {ORIGEN}")
    print(f"Destino: {DESTINO}")
    print()

    parrafos = leer_parrafos_docx(ORIGEN)
    bloques = partir_anuncios(parrafos)
    print(f"Párrafos leídos : {len(parrafos)}")
    print(f"Anuncios detectados: {len(bloques)}")
    print()

    registros = []
    errores = 0
    for bloque in bloques:
        try:
            registros.append(procesar_bloque(bloque))
        except Exception as e:  # noqa: BLE001
            errores += 1
            print(f"  ERROR procesando un bloque: {type(e).__name__}: {e}")

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CAMPOS_SALIDA, extrasaction="ignore")
        writer.writeheader()
        for r in registros:
            writer.writerow(r)

    # ── RESUMEN ─────────────────────────────────────────────────────────────
    n = len(registros)
    print("=" * 78)
    print("RESUMEN")
    print("=" * 78)
    print(f"Anuncios procesados   : {n}")
    print(f"Errores de parseo     : {errores}")
    print(f"Archivo generado      : {DESTINO}")
    print()

    # Precio
    precios = [r["precio"] for r in registros if r["precio"] is not None]
    print("PRECIO (USD)")
    print("-" * 78)
    if precios:
        precios_ord = sorted(precios)
        print(f"  con precio : {len(precios)}/{n}")
        print(f"  promedio   : {statistics.mean(precios):,.0f} USD")
        print(f"  mediana    : {statistics.median(precios):,.0f} USD")
        print(f"  mínimo     : {precios_ord[0]:,.0f} USD")
        print(f"  máximo     : {precios_ord[-1]:,.0f} USD")
    else:
        print("  sin precios válidos")
    print()

    # Barrio
    print("DISTRIBUCIÓN POR BARRIO")
    print("-" * 78)
    barrios = Counter(r["barrio"] or "(sin barrio)" for r in registros)
    for b, c in barrios.most_common():
        pct = f"{100*c/n:5.1f}%" if n else "  n/a"
        print(f"  {b:28} {c:>4}  {pct}  {'#' * round(28*c/n) if n else ''}")
    print()

    # Tipo de inmueble
    print("TIPO DE INMUEBLE")
    print("-" * 78)
    for t, c in Counter(r["tipo_inmueble"] for r in registros).most_common():
        print(f"  {t:28} {c:>4}  {f'{100*c/n:5.1f}%' if n else 'n/a'}")
    print()

    # Detección por keywords
    print("DETECCIÓN POR PALABRAS CLAVE")
    print("-" * 78)
    print(f"  {'urgencia migratoria':32} "
          f"{sum(1 for r in registros if r['menciona_urgencia_viaje']):>4}")
    print(f"  {'problemas estructurales':32} "
          f"{sum(1 for r in registros if r['menciona_problemas_estructurales']):>4}")
    print(f"  {'respaldo energético':32} "
          f"{sum(1 for r in registros if r['respaldo_energetico']):>4}")
    print(f"  {'infraestructura (cisterna, etc.)':32} "
          f"{sum(1 for r in registros if r['menciona_infraestructura']):>4}")
    print()

    # Fuente
    print("FUENTE")
    print("-" * 78)
    for f, c in Counter(r["fuente"] or "(sin fuente)" for r in registros).most_common():
        print(f"  {f:40} {c:>4}")
    print()

    # Cobertura de campos
    print("COBERTURA DE CAMPOS")
    print("-" * 78)
    for campo in ["precio", "barrio", "habitaciones", "banos",
                  "metros_cuadrados", "descripcion"]:
        ok = sum(1 for r in registros if r[campo] is not None
                 and r[campo] != "" and r[campo] != "(sin barrio)")
        pct = f"{100*ok/n:5.1f}%" if n else "  n/a"
        print(f"  {campo:32} {ok:>4}/{n}  {pct}")
    print("=" * 78)


if __name__ == "__main__":
    main()