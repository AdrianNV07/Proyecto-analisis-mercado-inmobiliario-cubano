#!/usr/bin/env python3
r"""
Procesa las entrevistas callejeras de Playa (Pilar 4).

Fuente:  Entrevistas.docx  (30 entrevistas, respuestas numeradas 1-23)
Salidas:
  data/raw/entrevistas_playa.jsonl
  resultados/entrevistas_playa_resumen.txt

Decisiones de normalizacion (documentadas para el informe):
  - "No acepto menos" / "es lo minimo" -> precio_minimo = precio_lista.
    No es una imputacion: el vendedor declara que su minimo es el precio pedido,
    por lo que el margen de negociacion es 0.
  - motivo_venta solo admite Migracion / Economico / Otro. Las negativas a
    responder quedan en null (no se fuerzan a "Otro").
  - fecha_limite: solo cuenta una fecha limite explicita. La entrevista #22
    menciona un deseo ("antes de fin de ano") pero aclara que no es vinculante.
  - plan_b: el cuestionario transcrito no contiene una pregunta de plan B,
    por lo que el campo queda en null en todos los registros.
  - espacios_exteriores y tiempo_vendiendo conservan el texto original: las
    respuestas son descriptivas, no numericas.
  - Entrevista #30: la respuesta 4 es "108", valor imposible como numero de
    habitaciones (probablemente m2 mal ubicados). Se deja habitaciones=null
    para no introducir un valor invalido.

Uso:  .venv\Scripts\python.exe scripts\04_procesar_entrevistas_playa.py
"""

from __future__ import annotations

import json
import re
import statistics
import zipfile
from collections import Counter
from pathlib import Path

ORIGEN = Path("Entrevistas.docx")
SALIDA_JSONL = Path("data/raw/entrevistas_playa.jsonl")
SALIDA_RESUMEN = Path("resultados/entrevistas_playa_resumen.txt")

CAMPOS = [
    "id_entrevista",
    "barrio",
    "tipo_inmueble",
    "metros_cuadrados",
    "habitaciones",
    "banos",
    "estado_inmueble",
    "espacios_exteriores",
    "papeles_en_regla",
    "precio_lista",
    "moneda",
    "incluye_muebles",
    "motivo_venta",
    "puso_migracion_en_anuncio",
    "razon_por_que_no_lo_puso",
    "precio_minimo",
    "percepcion_bajan_precio",
    "usa_intermediario",
    "tiempo_vendiendo",
    "fecha_limite",
    "plan_b",
    "oculto_problemas",
    "transparencia_problemas",
    "razon_playa",
    "canal_publicacion",
    "margen_negociacion_pct",
]

# ── Codificacion semantica de respuestas abiertas ────────────────────────────
# Motivo de venta declarado (Q12).
MOTIVO = {
    1: "Migración", 2: "Otro", 3: "Otro", 4: None, 5: "Otro",
    6: "Migración", 7: "Migración", 8: "Otro", 9: "Otro", 10: "Migración",
    11: "Otro", 12: None, 13: "Migración", 14: None, 15: "Otro",
    16: None, 17: "Migración", 18: "Migración", 19: "Económico", 20: None,
    21: "Otro", 22: "Migración", 23: "Migración", 24: "Económico",
    25: "Económico", 26: "Otro", 27: "Económico", 28: "Otro",
    29: "Migración", 30: "Otro",
}

# Q13: los 10 vendedores con motivo migracion respondieron "No" a si lo
# pusieron en el anuncio; el resto no tiene respuesta.
PUSO_MIGRACION = {
    1: "No", 6: "No", 7: "No", 10: "No", 13: "No",
    17: "No", 18: "No", 22: "No", 23: "No", 29: "No",
}

ESTADO = {
    1: "Bueno", 2: "Bueno", 3: "Bueno", 4: "Bueno", 5: "Bueno",
    6: "Bueno", 7: "Bueno", 8: "Excelente", 9: "Bueno", 10: "Regular",
    11: "Excelente", 12: "Bueno", 13: "Bueno", 14: "Bueno", 15: "Bueno",
    16: "Bueno", 17: "Regular", 18: "Bueno", 19: "Bueno", 20: "Bueno",
    21: "Regular", 22: "Bueno", 23: "Bueno", 24: "Bueno", 25: "Bueno",
    26: "Bueno", 27: "Bueno", 28: "Bueno", 29: "Bueno", 30: "Bueno",
}

INCLUYE_MUEBLES = {
    1: "Sí", 2: "Sí", 3: "No", 4: "No", 5: "No",
    6: "Sí", 7: "Sí", 8: "No", 9: "No", 10: "No",
    11: "No", 12: "No", 13: "No", 14: "No", 15: "No",
    16: "Sí", 17: "Sí", 18: "Sí", 19: "No", 20: "No",
    21: "No", 22: "Sí", 23: "Sí", 24: "No", 25: "Sí",
    26: "No", 27: "No", 28: "No", 29: "No", 30: "No",
}

USA_INTERMEDIARIO = {
    3: "Sí", 4: "Sí", 5: "Sí", 8: "Sí", 11: "Sí",
    12: "Sí", 13: "Sí", 25: "Sí", 26: "Sí", 27: "Sí", 30: "Sí",
}

OCULTO_PROBLEMAS = {1: "Sí", 18: "Sí", 21: "Sí"}

TRANSPARENCIA = {1: "Sí siempre", 18: "Sí siempre", 21: "Sí siempre"}

# Q22 codificada en temas (multietiqueta: una respuesta puede tener varios).
TEMAS_PLAYA = {
    1: ["Belleza"],
    2: ["Desarrollo económico"],
    3: ["Tranquilidad"],
    4: ["Desarrollo económico", "Belleza"],
    5: ["Belleza", "Servicios"],
    6: ["Tranquilidad", "Céntrico"],
    7: ["Tranquilidad"],
    8: ["Belleza", "Tranquilidad", "Desarrollo económico"],
    9: ["Inespecífico"],
    10: ["Desarrollo económico", "Belleza"],
    11: ["Belleza", "Tranquilidad"],
    12: ["Tranquilidad", "Céntrico"],
    13: ["Tranquilidad", "Céntrico"],
    14: ["Belleza"],
    15: ["Céntrico", "Servicios", "Comercio"],
    16: ["Belleza", "Desarrollo económico"],
    17: ["Servicios", "Oportunidades laborales"],
    18: ["Servicios", "Ocio"],
    19: ["Tranquilidad"],
    20: ["Tranquilidad", "Desarrollo económico"],
    21: ["Servicios"],
    22: ["Belleza", "Desarrollo económico", "Embajadas"],
    23: ["Tranquilidad"],
    24: ["Comercio", "Oportunidades laborales"],
    25: ["Oportunidades laborales", "Servicios", "Tranquilidad"],
    26: ["Belleza", "Tranquilidad", "Emprendimientos"],
    27: ["Tranquilidad", "Céntrico", "Belleza", "Desarrollo económico"],
    28: ["Desarrollo económico"],
    29: ["Tranquilidad", "Comercio"],
    30: ["Belleza", "Embajadas", "Emprendimientos"],
}


# ── Lectura y parseo del DOCX ────────────────────────────────────────────────
def leer_parrafos(ruta: Path) -> list[str]:
    """Extrae los parrafos de word/document.xml sin dependencias externas."""
    with zipfile.ZipFile(ruta) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    parrafos = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
    textos: list[str] = []
    for p in parrafos:
        partes = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)
        t = "".join(partes)
        t = (
            t.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&apos;", "'")
        )
        if t.strip():
            textos.append(t.strip())
    return textos


def separar_entrevistas(parrafos: list[str]) -> dict[int, dict[int, str]]:
    """Agrupa las respuestas numeradas por numero de entrevista."""
    entrevistas: dict[int, dict[int, str]] = {}
    actual: int | None = None
    for texto in parrafos:
        m = re.match(r"Entrevista\s*#\s*(\d+)", texto, re.I)
        if m:
            actual = int(m.group(1))
            entrevistas[actual] = {}
            continue
        if actual is None:
            continue
        m = re.match(r"^\s*(\d{1,2})\.\s*(.*)$", texto)
        if m:
            entrevistas[actual][int(m.group(1))] = m.group(2).strip()
    return entrevistas


# ── Normalizadores ───────────────────────────────────────────────────────────
def texto_o_nulo(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    if not v or v.lower() == "null":
        return None
    return v


def parse_precio(v: str | None) -> float | None:
    if not v:
        return None
    t = v.lower().strip()
    if "mil" in t:
        m = re.search(r"(\d[\d\s.,]*)", t)
        if not m:
            return None
        base = m.group(1).replace(" ", "").replace(".", "").replace(",", "")
        return float(base) * 1000
    m = re.search(r"(\d[\d\s.,]*)", t)
    if not m:
        return None
    limpio = m.group(1).replace(" ", "").replace(".", "").replace(",", "")
    return float(limpio)


def parse_metros(v: str | None) -> float | None:
    if not v:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)", v)
    if not m:
        return None
    return float(m.group(1).replace(",", "."))


def parse_entero(v: str | None) -> int | None:
    if not v:
        return None
    m = re.search(r"(\d+)", v)
    return int(m.group(1)) if m else None


def normalizar_barrio(v: str | None) -> str | None:
    if not v:
        return None
    v = v.strip()
    # Variante sin tilde en el mismo barrio.
    if v.lower() == "nautico":
        return "Náutico"
    return v


def normalizar_tipo(v: str | None) -> str | None:
    if not v:
        return None
    v = v.strip().capitalize()
    return v if v in {"Casa", "Apartamento"} else v


def codificar_estado(v: str | None) -> str | None:
    """Fallback por texto si falta el mapeo explicito."""
    if not v:
        return None
    t = v.lower()
    if "ruina" in t:
        return "En ruinas"
    if "remodelar" in t or "para arreglar" in t:
        return "Para remodelar"
    if "recién remodelada" in t or "recien remodelada" in t:
        return "Excelente"
    if "detalles" in t or "filtracion" in t or "arreglito" in t:
        return "Regular"
    return "Bueno"


def calcular_margen(lista: float | None, minimo: float | None) -> float | None:
    if lista is None or minimo is None or lista == 0:
        return None
    return round((lista - minimo) / lista * 100, 2)


# ── Construccion del registro ────────────────────────────────────────────────
def construir_registro(id_ent: int, r: dict[int, str]) -> dict:
    precio_lista = parse_precio(r.get(9))
    precio_minimo = parse_precio(r.get(14))

    # "No acepto menos" no es un dato faltante: el minimo es el precio pedido.
    if precio_minimo is None and precio_lista is not None:
        q14 = (r.get(14) or "").lower()
        if "no acepto menos" in q14 or "es lo mínimo" in q14 or "por el momento no" in q14:
            precio_minimo = precio_lista

    habitaciones = parse_entero(r.get(4))
    if id_ent == 30:
        habitaciones = None  # valor 108 incompatible con el resto de la vivienda

    # Q16 del cuestionario transcrito = percepcion de que la desesperacion por
    # emigrar hace bajar los precios. Se codifica por contenido, no por el
    # numero de la pregunta.
    q16 = (r.get(16) or "").lower()
    if id_ent == 7:
        percepcion = "No sé"  # "No le sé decir"
    elif q16:
        percepcion = "Sí"
    else:
        percepcion = None

    return {
        "id_entrevista": id_ent,
        "barrio": normalizar_barrio(texto_o_nulo(r.get(1))),
        "tipo_inmueble": normalizar_tipo(texto_o_nulo(r.get(2))),
        "metros_cuadrados": parse_metros(r.get(3)),
        "habitaciones": habitaciones,
        "banos": parse_entero(r.get(5)),
        "estado_inmueble": ESTADO.get(id_ent) or codificar_estado(r.get(6)),
        "espacios_exteriores": texto_o_nulo(r.get(7)),
        "papeles_en_regla": "No" if id_ent == 9 else "Sí",
        "precio_lista": precio_lista,
        "moneda": (texto_o_nulo(r.get(10)) or "USD").upper(),
        "incluye_muebles": INCLUYE_MUEBLES.get(id_ent),
        "motivo_venta": MOTIVO.get(id_ent),
        "puso_migracion_en_anuncio": PUSO_MIGRACION.get(id_ent),
        "razon_por_que_no_lo_puso": (
            texto_o_nulo(r.get(13)) if id_ent in PUSO_MIGRACION else None
        ),
        "precio_minimo": precio_minimo,
        "percepcion_bajan_precio": percepcion,
        "usa_intermediario": USA_INTERMEDIARIO.get(id_ent, "No"),
        "tiempo_vendiendo": texto_o_nulo(r.get(18)),
        "fecha_limite": "No",  # ninguna entrevista declara una fecha limite vinculante
        "plan_b": None,  # el cuestionario transcrito no incluye esta pregunta
        "oculto_problemas": OCULTO_PROBLEMAS.get(id_ent, "No"),
        "transparencia_problemas": TRANSPARENCIA.get(id_ent),
        "razon_playa": texto_o_nulo(r.get(22)),
        "canal_publicacion": texto_o_nulo(r.get(23)),
        "margen_negociacion_pct": calcular_margen(precio_lista, precio_minimo),
    }


# ── Resumen ──────────────────────────────────────────────────────────────────
def resumen(registros: list[dict]) -> str:
    total = len(registros)
    lineas: list[str] = []

    def p(s: str = "") -> None:
        lineas.append(s)

    p("=" * 78)
    p("RESUMEN — ENTREVISTAS CALLEJERAS DE PLAYA (PILAR 4)")
    p("=" * 78)
    p(f"n = {total} entrevistas. Muestra no probabilistica: los resultados")
    p("describen a las personas entrevistadas, no a la poblacion de Playa.")
    p()

    # 1. Motivo migracion
    migracion = [r for r in registros if r["motivo_venta"] == "Migración"]
    respondieron = [r for r in registros if r["motivo_venta"] is not None]
    p("1) MOTIVO DE VENTA")
    p("-" * 78)
    for motivo, n in Counter(r["motivo_venta"] for r in registros).most_common():
        etiqueta = motivo if motivo is not None else "Sin respuesta"
        p(f"  {etiqueta:16} {n:2}  ({100 * n / total:5.1f} %)")
    p()
    p(f"  Migración sobre el total:        {len(migracion)}/{total} = "
      f"{100 * len(migracion) / total:.1f} %")
    p(f"  Migración entre quienes respondieron: {len(migracion)}/{len(respondieron)} = "
      f"{100 * len(migracion) / len(respondieron):.1f} %")
    p("  Contraste con Revolico: 0/135 anuncios (0.0 %) verbalizan la migración.")
    p()

    # 2. Margen de negociacion
    def margenes(grupo: list[dict]) -> list[float]:
        return [r["margen_negociacion_pct"] for r in grupo
                if r["margen_negociacion_pct"] is not None]

    mig_m = margenes(migracion)
    no_mig = [r for r in registros if r["motivo_venta"] in {"Económico", "Otro"}]
    no_mig_m = margenes(no_mig)
    sin_resp = [r for r in registros if r["motivo_venta"] is None]
    sin_resp_m = margenes(sin_resp)

    p("2) MARGEN DE NEGOCIACION  (precio_lista - precio_minimo) / precio_lista")
    p("-" * 78)
    p(f"  Migración:        n={len(mig_m):2}  promedio={statistics.mean(mig_m):5.2f} %  "
      f"mediana={statistics.median(mig_m):5.2f} %")
    p(f"  No migración:     n={len(no_mig_m):2}  promedio={statistics.mean(no_mig_m):5.2f} %  "
      f"mediana={statistics.median(no_mig_m):5.2f} %")
    p(f"  Sin respuesta:    n={len(sin_resp_m):2}  promedio={statistics.mean(sin_resp_m):5.2f} %  "
      f"mediana={statistics.median(sin_resp_m):5.2f} %")
    p()
    p("  Nota: 'no acepto menos' se registra como margen 0 porque el minimo")
    p("  declarado coincide con el precio pedido. Un caso sin precio minimo")
    p("  (entrevista #3) queda fuera del calculo.")
    p()

    # 3. Oculto problemas
    oculto = sum(1 for r in registros if r["oculto_problemas"] == "Sí")
    con_problema = sum(
        1 for r in registros
        if r["oculto_problemas"] == "Sí" or r["transparencia_problemas"] is not None
        or r["id_entrevista"] == 10
    )
    p("3) PROBLEMAS OCULTOS")
    p("-" * 78)
    p(f"  Ocultó problemas en el anuncio: {oculto}/{total} = {100 * oculto / total:.1f} %")
    p(f"  Entre quienes declararon algún problema: {oculto}/{con_problema} = "
      f"{100 * oculto / con_problema:.1f} %")
    p()

    # 4. Intermediario
    inter = sum(1 for r in registros if r["usa_intermediario"] == "Sí")
    p("4) USO DE INTERMEDIARIO")
    p("-" * 78)
    p(f"  Usa intermediario: {inter}/{total} = {100 * inter / total:.1f} %")
    p()

    # 5. Razones para preferir Playa
    conteo_temas: Counter[str] = Counter()
    for r in registros:
        for tema in TEMAS_PLAYA.get(r["id_entrevista"], []):
            conteo_temas[tema] += 1
    p("5) RAZONES PARA PREFERIR PLAYA  (respuesta abierta, multietiqueta)")
    p("-" * 78)
    for tema, n in conteo_temas.most_common():
        p(f"  {tema:26} {n:2}/{total}  ({100 * n / total:5.1f} %)")
    p()
    p("  Top 3:")
    for i, (tema, n) in enumerate(conteo_temas.most_common(3), 1):
        p(f"    {i}. {tema} — {n}/{total} ({100 * n / total:.1f} %)")
    p()
    p("  Multietiqueta: una misma respuesta puede aportar a varios temas, por")
    p("  lo que los porcentajes no suman 100 %.")
    p()

    # 6. Coherencia con el anuncio
    p("6) MIGRACIÓN EN EL ANUNCIO")
    p("-" * 78)
    p(f"  Vendedores con motivo migración: {len(migracion)}")
    p(f"  De ellos, dijeron haberlo puesto en el anuncio: "
      f"{sum(1 for r in migracion if r['puso_migracion_en_anuncio'] == 'Sí')}")
    p(f"  De ellos, dijeron NO haberlo puesto: "
      f"{sum(1 for r in migracion if r['puso_migracion_en_anuncio'] == 'No')}")
    p()

    return "\n".join(lineas)


def main() -> None:
    if not ORIGEN.exists():
        raise FileNotFoundError(f"No se encontro {ORIGEN}")

    parrafos = leer_parrafos(ORIGEN)
    entrevistas = separar_entrevistas(parrafos)
    print(f"Entrevistas detectadas: {len(entrevistas)}")
    print(f"IDs: {sorted(entrevistas)}")

    registros = [construir_registro(i, entrevistas[i]) for i in sorted(entrevistas)]

    # Verificacion de esquema
    for r in registros:
        if set(r) != set(CAMPOS):
            faltan = set(CAMPOS) - set(r)
            sobran = set(r) - set(CAMPOS)
            raise ValueError(f"Esquema invalido en #{r['id_entrevista']}: "
                             f"faltan={faltan}, sobran={sobran}")

    SALIDA_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with SALIDA_JSONL.open("w", encoding="utf-8", newline="\n") as f:
        for r in registros:
            f.write(json.dumps({k: r[k] for k in CAMPOS}, ensure_ascii=False) + "\n")
    print(f"JSONL guardado: {SALIDA_JSONL} ({len(registros)} lineas)")

    texto_resumen = resumen(registros)
    SALIDA_RESUMEN.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_RESUMEN.write_text(texto_resumen + "\n", encoding="utf-8")
    print(f"Resumen guardado: {SALIDA_RESUMEN}")
    print()
    print(texto_resumen)


if __name__ == "__main__":
    main()
