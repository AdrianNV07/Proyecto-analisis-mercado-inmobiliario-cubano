#!/usr/bin/env python3
r"""
Informe final de las entrevistas callejeras de Playa (Pilar 4).

Entrada:  data/raw/entrevistas_playa.jsonl
Salida:   resultados/analisis_entrevistas.txt

El informe esta pensado como base del capitulo de Resultados: incluye ficha
tecnica, perfil de la muestra, motivo de venta, margen de negociacion,
problemas ocultos, uso de intermediario, razones para preferir Playa,
canales de publicacion, sintesis, limitaciones, anexo de registros y anexo
de citas textuales sobre la invisibilidad migratoria.

Uso:  .venv\Scripts\python.exe scripts\05_analisis_entrevistas.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from datetime import date
from pathlib import Path

ORIGEN = Path("data/raw/entrevistas_playa.jsonl")
SALIDA = Path("resultados/analisis_entrevistas.txt")

# Codificacion de las razones por las que no se declaro la migracion (n=10).
RAZONES_NO_ANUNCIO = {
    1: "No es de interés del comprador",
    6: "Norma informal / no tiene sentido en el anuncio",
    7: "Pérdida de poder de negociación",
    10: "Pérdida de poder de negociación",
    13: "Pérdida de poder de negociación",
    17: "Norma informal / no tiene sentido en el anuncio",
    18: "Pérdida de poder de negociación",
    22: "Privacidad",
    23: "No es de interés del comprador",
    29: "No es de interés del comprador",
}


def cargar() -> list[dict]:
    return [
        json.loads(linea)
        for linea in ORIGEN.read_text(encoding="utf-8").splitlines()
        if linea.strip()
    ]


def stats(valores: list[float]) -> dict[str, float] | None:
    if not valores:
        return None
    return {
        "n": len(valores),
        "media": statistics.mean(valores),
        "mediana": statistics.median(valores),
        "min": min(valores),
        "max": max(valores),
    }


def fmt_pct(n: int, total: int) -> str:
    return f"{100 * n / total:.1f} %" if total else "—"


def fmt_num(x: float | None, decimales: int = 0) -> str:
    if x is None:
        return "—"
    return f"{x:,.{decimales}f}"


def main() -> None:
    regs = cargar()
    total = len(regs)
    lineas: list[str] = []

    def p(s: str = "") -> None:
        lineas.append(s)

    # ── Encabezado ──────────────────────────────────────────────────────────
    p("=" * 80)
    p("ANÁLISIS DE ENTREVISTAS CALLEJERAS — MUNICIPIO DE PLAYA (PILAR 4)")
    p("=" * 80)
    p(f"Generado: {date.today().isoformat()}")
    p("Fuente: Entrevistas.docx (30 entrevistas, cuestionario de 23 preguntas)")
    p(f"Datos: {ORIGEN}")
    p()

    # ── 1. Ficha técnica ────────────────────────────────────────────────────
    p("1. FICHA TÉCNICA")
    p("-" * 80)
    p("  Universo:        vendedores de inmuebles residenciales en el municipio de Playa.")
    p("  Muestra:         30 entrevistas, selección no probabilística por conveniencia")
    p("                   (entrevistas callejeras).")
    p("  Unidad:          vivienda ofrecida en venta.")
    p("  Instrumento:     cuestionario mixto de 23 preguntas (cerradas y abiertas).")
    p("  Período:         no registrado en la transcripción.")
    p("  Alcance:         municipio de Playa, La Habana. Estudio de caso.")
    p()
    p("  ADVERTENCIA: la muestra no es probabilística. Los porcentajes describen")
    p("  a las 30 personas entrevistadas, no a la población de Playa. No deben")
    p("  presentarse como prevalencias poblacionales ni usarse para inferencia")
    p("  estadística formal.")
    p()

    # ── 2. Perfil de la muestra ─────────────────────────────────────────────
    p("2. PERFIL DE LA MUESTRA")
    p("-" * 80)

    barrios = Counter(r["barrio"] for r in regs)
    p("  Barrios declarados (n=30):")
    for barrio, n in barrios.most_common():
        p(f"    {barrio:28} {n:2}  ({fmt_pct(n, total)})")
    p()

    tipos = Counter(r["tipo_inmueble"] for r in regs)
    p("  Tipo de inmueble:")
    for tipo, n in tipos.most_common():
        p(f"    {tipo:28} {n:2}  ({fmt_pct(n, total)})")
    p()

    estados = Counter(r["estado_inmueble"] for r in regs)
    p("  Estado declarado:")
    for estado in ["Excelente", "Bueno", "Regular", "Para remodelar", "En ruinas"]:
        n = estados.get(estado, 0)
        if n:
            p(f"    {estado:28} {n:2}  ({fmt_pct(n, total)})")
    p()

    papeles = Counter(r["papeles_en_regla"] for r in regs)
    p("  Papeles en regla:")
    for valor in ["Sí", "No"]:
        n = papeles.get(valor, 0)
        p(f"    {valor:28} {n:2}  ({fmt_pct(n, total)})")
    p()

    precios = [r["precio_lista"] for r in regs if r["precio_lista"] is not None]
    sp = stats(precios)
    p(f"  Precio de lista (USD, n={sp['n']}):")
    p(f"    Mediana {fmt_num(sp['mediana'])} | Media {fmt_num(sp['media'])} | "
      f"Mínimo {fmt_num(sp['min'])} | Máximo {fmt_num(sp['max'])}")
    p()

    m2 = [r["metros_cuadrados"] for r in regs if r["metros_cuadrados"] is not None]
    sm2 = stats(m2)
    p(f"  Superficie declarada (m², n={sm2['n']} de {total}):")
    p(f"    Mediana {fmt_num(sm2['mediana'], 1)} | Media {fmt_num(sm2['media'], 1)} | "
      f"Mínimo {fmt_num(sm2['min'], 1)} | Máximo {fmt_num(sm2['max'], 1)}")
    p()

    pm2 = [
        r["precio_lista"] / r["metros_cuadrados"]
        for r in regs
        if r["precio_lista"] and r["metros_cuadrados"]
    ]
    spm2 = stats(pm2)
    p(f"  Precio por m² (USD/m², n={spm2['n']}):")
    p(f"    Mediana {fmt_num(spm2['mediana'], 1)} | Media {fmt_num(spm2['media'], 1)} | "
      f"Mínimo {fmt_num(spm2['min'], 1)} | Máximo {fmt_num(spm2['max'], 1)}")
    p()

    # ── 3. Motivo de venta ──────────────────────────────────────────────────
    p("3. MOTIVO DE VENTA")
    p("-" * 80)
    motivos = Counter(r["motivo_venta"] for r in regs)
    p("  Distribución (n=30):")
    p(f"    {'Categoría':22} {'n':>3}   {'%':>7}")
    for clave in ["Migración", "Otro", "Económico", None]:
        n = motivos.get(clave, 0)
        etiqueta = clave if clave else "Sin respuesta"
        p(f"    {etiqueta:22} {n:3}   {fmt_pct(n, total):>7}")
    p()

    migracion = [r for r in regs if r["motivo_venta"] == "Migración"]
    respondieron = [r for r in regs if r["motivo_venta"] is not None]
    p(f"  Migración sobre el total:              {len(migracion)}/{total} = "
      f"{fmt_pct(len(migracion), total)}")
    p(f"  Migración entre quienes respondieron:  {len(migracion)}/{len(respondieron)} = "
      f"{fmt_pct(len(migracion), len(respondieron))}")
    p()
    p("  CONTRASTE CON REVOLICO (Pilar 1):")
    p("    En 135 anuncios de Playa ningún texto verbaliza la migración (0.0 %).")
    p("    En las entrevistas, 10 de 30 vendedores la declaran como motivo.")
    p("    La diferencia no se explica por falta de cobertura: 28/30 entrevistados")
    p("    publicaron en Revolico (ver sección 8).")
    p()

    no_anuncio = [r for r in migracion if r["puso_migracion_en_anuncio"] == "No"]
    si_anuncio = [r for r in migracion if r["puso_migracion_en_anuncio"] == "Sí"]
    sin_dato = len(migracion) - len(si_anuncio) - len(no_anuncio)
    p(f"  ¿Lo puso en el anuncio? De los {len(migracion)} vendedores migrantes:")
    p(f"    Sí: {len(si_anuncio)}   No: {len(no_anuncio)}   Sin dato: {sin_dato}")
    p()

    razones = Counter(RAZONES_NO_ANUNCIO.values())
    p("  Razones declaradas para no ponerlo (n=10, respuesta codificada):")
    for razon, n in razones.most_common():
        p(f"    {razon:52} {n:2}  ({fmt_pct(n, len(no_anuncio))})")
    p()
    p("  Interpretación: la omisión es estratégica. El argumento más frecuente")
    p("  es que declarar la migración resta poder de negociación o proyecta")
    p("  desesperación, no que el dato sea irrelevante.")
    p()

    # ── 4. Margen de negociación ────────────────────────────────────────────
    p("4. MARGEN DE NEGOCIACIÓN")
    p("-" * 80)
    p("  Definición: (precio_lista - precio_minimo) / precio_lista × 100.")
    p("  Interpretación: a menor margen, menor disposición a rebajar y —bajo el")
    p("  supuesto del estudio— mayor urgencia de venta.")
    p()

    def margenes(grupo: list[dict]) -> list[float]:
        return [
            r["margen_negociacion_pct"]
            for r in grupo
            if r["margen_negociacion_pct"] is not None
        ]

    grupos = {
        "Migración": migracion,
        "No migración (Económico + Otro)": [
            r for r in regs if r["motivo_venta"] in {"Económico", "Otro"}
        ],
        "Sin respuesta": [r for r in regs if r["motivo_venta"] is None],
    }

    p(f"  {'Grupo':34} {'n':>3} {'Media':>9} {'Mediana':>9} {'Mín.':>7} {'Máx.':>7}")
    for nombre, grupo in grupos.items():
        s = stats(margenes(grupo))
        if s is None:
            p(f"  {nombre:34} {0:3} {'—':>9} {'—':>9} {'—':>7} {'—':>7}")
            continue
        p(f"  {nombre:34} {s['n']:3} {s['media']:8.2f}% {s['mediana']:8.2f}% "
          f"{s['min']:6.2f}% {s['max']:6.2f}%")
    p()

    todos_margenes = margenes(regs)
    ceros = sum(1 for m in todos_margenes if m == 0)
    p(f"  Casos con margen 0 ('no acepto menos'): {ceros}/{len(todos_margenes)} = "
      f"{fmt_pct(ceros, len(todos_margenes))}")
    p("  Estos casos se mantienen en el cálculo principal con margen 0: el")
    p("  vendedor declara que su mínimo es el precio pedido, no que falte el dato.")
    p()

    p("  CÁLCULO DE ROBUSTEZ (solo casos con margen > 0):")
    for nombre in ["Migración", "No migración (Económico + Otro)"]:
        vals = [m for m in margenes(grupos[nombre]) if m > 0]
        s = stats(vals)
        if s is None:
            p(f"    {nombre:34} n=0")
            continue
        p(f"    {nombre:34} n={s['n']}  media={s['media']:.2f}%  "
          f"mediana={s['mediana']:.2f}%")
    p()
    p("  Lectura: la media principal (3.13 % vs 1.42 %) está comprimida por los")
    p("  muchos casos con margen 0. Al excluirlos, la brecha persiste y se amplía")
    p("  (7.82 % vs 4.96 %), pero cada grupo queda con solo 4 casos: el resultado")
    p("  es descriptivo y no admite inferencia.")
    p()

    # ── 5. Problemas ocultos y transparencia ────────────────────────────────
    p("5. PROBLEMAS OCULTOS Y TRANSPARENCIA")
    p("-" * 80)
    oculto = [r for r in regs if r["oculto_problemas"] == "Sí"]
    p(f"  Ocultó problemas en el anuncio: {len(oculto)}/{total} = "
      f"{fmt_pct(len(oculto), total)}")
    p()
    p("  Casos con problema declarado (n=4):")
    p(f"    {'#':>2}  {'Problema':46} {'¿En el anuncio?':16} {'Transparencia':15}")
    p(f"    {'1':>2}  {'Agua irregular':46} {'No':16} {'Sí siempre':15}")
    p(f"    {'10':>2}  {'Techo de un cuarto en mal estado':46} {'Sí':16} {'Sin dato':15}")
    p(f"    {'18':>2}  {'Agua irregular':46} {'No':16} {'Sí siempre':15}")
    p(f"    {'21':>2}  {'Pequeñas filtraciones':46} {'No':16} {'Sí siempre':15}")
    p()
    p(f"  Entre quienes declararon un problema: {len(oculto)}/4 = 75.0 %")
    p("  De los 3 que ocultaron el problema, los 3 afirman que lo comunican")
    p("  verbalmente al comprador: la omisión es del anuncio, no de la relación")
    p("  de venta. El n=3 es anecdótico.")
    p()

    # ── 6. Uso de intermediario ─────────────────────────────────────────────
    p("6. USO DE INTERMEDIARIO")
    p("-" * 80)
    inter = [r for r in regs if r["usa_intermediario"] == "Sí"]
    p(f"  Usa intermediario: {len(inter)}/{total} = {fmt_pct(len(inter), total)}")
    p()
    p("  Cruce exploratorio con el motivo de venta:")
    mig_inter = sum(1 for r in migracion if r["usa_intermediario"] == "Sí")
    no_mig = grupos["No migración (Económico + Otro)"]
    no_mig_inter = sum(1 for r in no_mig if r["usa_intermediario"] == "Sí")
    p(f"    Migración:     {mig_inter}/{len(migracion)} = "
      f"{fmt_pct(mig_inter, len(migracion))}")
    p(f"    No migración:  {no_mig_inter}/{len(no_mig)} = "
      f"{fmt_pct(no_mig_inter, len(no_mig))}")
    p()
    p("  Lectura: los vendedores que emigran recurren menos a intermediarios.")
    p("  Con n=10 y n=15 el dato es exploratorio; no se controla por precio,")
    p("  tipo de inmueble ni barrio.")
    p()

    # ── 7. Razones para preferir Playa ──────────────────────────────────────
    p("7. RAZONES PARA PREFERIR PLAYA")
    p("-" * 80)
    p("  Pregunta abierta (Q22), codificada en temas. Una respuesta puede")
    p("  aportar a varios temas, por lo que los porcentajes no suman 100 %.")
    p()

    TEMAS = {
        1: ["Belleza"], 2: ["Desarrollo económico"], 3: ["Tranquilidad"],
        4: ["Desarrollo económico", "Belleza"], 5: ["Belleza", "Servicios"],
        6: ["Tranquilidad", "Céntrico"], 7: ["Tranquilidad"],
        8: ["Belleza", "Tranquilidad", "Desarrollo económico"],
        9: ["Inespecífico"], 10: ["Desarrollo económico", "Belleza"],
        11: ["Belleza", "Tranquilidad"], 12: ["Tranquilidad", "Céntrico"],
        13: ["Tranquilidad", "Céntrico"], 14: ["Belleza"],
        15: ["Céntrico", "Servicios", "Comercio"],
        16: ["Belleza", "Desarrollo económico"],
        17: ["Servicios", "Oportunidades laborales"], 18: ["Servicios", "Ocio"],
        19: ["Tranquilidad"], 20: ["Tranquilidad", "Desarrollo económico"],
        21: ["Servicios"], 22: ["Belleza", "Desarrollo económico", "Embajadas"],
        23: ["Tranquilidad"], 24: ["Comercio", "Oportunidades laborales"],
        25: ["Oportunidades laborales", "Servicios", "Tranquilidad"],
        26: ["Belleza", "Tranquilidad", "Emprendimientos"],
        27: ["Tranquilidad", "Céntrico", "Belleza", "Desarrollo económico"],
        28: ["Desarrollo económico"], 29: ["Tranquilidad", "Comercio"],
        30: ["Belleza", "Embajadas", "Emprendimientos"],
    }
    temas = Counter()
    for r in regs:
        for tema in TEMAS.get(r["id_entrevista"], []):
            temas[tema] += 1

    p(f"  {'Tema':26} {'n':>3}   {'%':>7}")
    for tema, n in temas.most_common():
        p(f"  {tema:26} {n:3}   {fmt_pct(n, total):>7}")
    p()
    p("  TOP 3:")
    for i, (tema, n) in enumerate(temas.most_common(3), 1):
        p(f"    {i}. {tema} — {n}/{total} ({fmt_pct(n, total)})")
    p()
    p("  Lectura: la preferencia por Playa se explica por atributos de calidad")
    p("  de vida (tranquilidad y belleza) más que por una narrativa migratoria.")
    p("  El desarrollo económico aparece tercero, con 9 menciones.")
    p()

    # ── 8. Canales de publicación ───────────────────────────────────────────
    p("8. CANALES DE PUBLICACIÓN")
    p("-" * 80)
    canales = {"Revolico": 0, "Facebook": 0, "Telegram": 0, "WhatsApp": 0, "Instagram": 0}
    for r in regs:
        texto = (r["canal_publicacion"] or "").lower()
        for canal in canales:
            if canal.lower() in texto:
                canales[canal] += 1
    p(f"  {'Canal':14} {'n':>3}   {'%':>7}")
    for canal, n in sorted(canales.items(), key=lambda x: -x[1]):
        p(f"  {canal:14} {n:3}   {fmt_pct(n, total):>7}")
    p()
    p("  Nota: los canales no son excluyentes; un mismo anuncio puede estar en")
    p("  varios. El 93.3 % publicó en Revolico, de modo que la ausencia de")
    p("  migración en los anuncios no se debe a que la muestra no use Revolico.")
    p()

    # ── 9. Precio por m² según motivo (exploratorio) ────────────────────────
    p("9. PRECIO POR M² SEGÚN MOTIVO (EXPLORATORIO)")
    p("-" * 80)
    p(f"  {'Grupo':34} {'n':>3} {'Mediana USD/m²':>16}")
    for nombre, grupo in grupos.items():
        vals = [
            r["precio_lista"] / r["metros_cuadrados"]
            for r in grupo
            if r["precio_lista"] and r["metros_cuadrados"]
        ]
        s = stats(vals)
        if s is None:
            p(f"  {nombre:34} {0:3} {'—':>16}")
        else:
            p(f"  {nombre:34} {s['n']:3} {s['mediana']:15,.1f}")
    p()
    p("  No se ajusta por tamaño, tipo de inmueble ni barrio. Con estos n, la")
    p("  tabla solo orienta; no permite atribuir diferencias al motivo de venta.")
    p()

    # ── 10. Síntesis ────────────────────────────────────────────────────────
    p("10. SÍNTESIS PARA EL CAPÍTULO DE RESULTADOS")
    p("-" * 80)
    p(f"  1. Migración: 33.3 % de los entrevistados (10/30) declara que emigra;")
    p("     entre quienes respondieron, 40.0 % (10/25). En Revolico, 0/135.")
    p("  2. Invisibilidad estratégica: 10/10 vendedores migrantes omitieron la")
    p("     migración en el anuncio, sobre todo para no perder poder de")
    p("     negociación.")
    p("  3. Margen: 3.13 % (migración) vs 1.42 % (no migración); mediana 0 en")
    p("     ambos. Robustez: 7.82 % vs 4.96 % al excluir los márgenes 0.")
    p("  4. Problemas ocultos: 10.0 % del total (3/30); 75.0 % de quienes")
    p("     declararon un problema (3/4). Los 3 dicen comunicarlo verbalmente.")
    p("  5. Intermediarios: 36.7 % (11/30); 10.0 % entre migrantes y 53.3 %")
    p("     entre no migrantes (exploratorio).")
    p("  6. Playa: tranquilidad (46.7 %), belleza (40.0 %) y desarrollo")
    p("     económico (30.0 %) son las razones principales.")
    p()

    # ── 11. Limitaciones ────────────────────────────────────────────────────
    p("11. LIMITACIONES")
    p("-" * 80)
    p("  - Muestra no probabilística por conveniencia (n=30). No representa a")
    p("    la población de Playa ni permite extrapolar a otros municipios.")
    p("  - Entrevistas callejeras: posible sesgo de selección y de deseabilidad")
    p("    social, sobre todo en preguntas sobre ocultamiento de problemas.")
    p("  - Período de recolección no registrado en la transcripción.")
    p("  - Subgrupos pequeños (migración n=10; económico n=4; por barrio n=1-7):")
    p("    las comparaciones son descriptivas, no inferenciales.")
    p("  - 'No acepto menos' se codifica como margen 0; es un supuesto del")
    p("    estudio, documentado y acompañado del cálculo de robustez.")
    p("  - La muestra mezcla casas y apartamentos de tamaños y barrios muy")
    p("    distintos; el precio por m² no está ajustado por esas variables.")
    p("  - Los datos son autodeclarados: no se verificaron precios, papeles ni")
    p("    problemas con documentación externa.")
    p()

    # ── 12. Anexo ───────────────────────────────────────────────────────────
    p("12. ANEXO — REGISTROS DE LA MUESTRA")
    p("-" * 80)
    p(f"  {'#':>2}  {'Barrio':24} {'Motivo':10} {'Lista':>9} {'Mínimo':>9} "
      f"{'Margen':>7} {'Ocultó':>6} {'Interm.':>7}")
    for r in regs:
        lista = fmt_num(r["precio_lista"]) if r["precio_lista"] is not None else "—"
        minimo = fmt_num(r["precio_minimo"]) if r["precio_minimo"] is not None else "—"
        margen = (f"{r['margen_negociacion_pct']:.2f}"
                  if r["margen_negociacion_pct"] is not None else "—")
        motivo = r["motivo_venta"] or "s/r"
        p(f"  {r['id_entrevista']:2}  {r['barrio']:24} {motivo:10} "
          f"{lista:>9} {minimo:>9} {margen:>7} {r['oculto_problemas']:>6} "
          f"{r['usa_intermediario']:>7}")
    p()
    p("  s/r = sin respuesta. Los valores monetarios están en USD.")
    p()

    # ── 13. Anexo: citas textuales ──────────────────────────────────────────
    p("13. ANEXO — CITAS TEXTUALES SOBRE LA INVISIBILIDAD MIGRATORIA")
    p("-" * 80)
    p("  Fragmentos literales de los 10 vendedores con motivo Migración que")
    p("  explicaron por qué no incluyeron la emigración en el anuncio.")
    p("  Campo del JSONL: razon_por_que_no_lo_puso.")
    p()
    for r in migracion:
        cita = r["razon_por_que_no_lo_puso"]
        if not cita:
            continue
        p(f"  #{r['id_entrevista']:02} — {r['barrio']} ({r['tipo_inmueble']})")
        p(f"      «{cita}»")
        p()

    texto = "\n".join(lineas) + "\n"
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(texto, encoding="utf-8")
    print(f"Informe guardado: {SALIDA}")
    print(f"Líneas: {len(lineas)}")


if __name__ == "__main__":
    main()
