# Journal — 2026-11-05

> **Periodo del trabajo: 2026-11-04 – 2026-11-05** (continuación de la jornada del
> 2026-11-05 iniciada con el cierre del Pilar 4 y la generación de gráficos finales).

## Objetivo del día
Cerrar el Pilar 4 con las entrevistas de Playa, añadir el dataset de agencias
online (Pilar 2) y generar los gráficos finales de la sesión. En la franja final
del día, redactar las respuestas a las 33 preguntas de investigación para el
informe final.

## Actividades realizadas
- **2026-11-04:** Procesamiento de entrevistas a partir de `Entrevistas.docx`.
  - `scripts/04_procesar_entrevistas_playa.py` → `data/raw/entrevistas_playa.jsonl`.
  - `scripts/05_analisis_entrevistas.py` → `resultados/analisis_entrevistas.txt`.
- **2026-11-05:** Agencias online + gráficos finales.
  - `data/processed/agencias_online.jsonl` (30 anuncios, Casaoasis, Playa, USD).
  - Gráficos: `graficos/1_brecha_migracion.png`, `graficos/2_margen_negociacion.png`,
    `graficos/3_dona_problemas.png`, `graficos/4_boxplot_fuentes.png`.
- **2026-11-05 (sesión final):** Creación del archivo con las respuestas a las
  33 preguntas de investigación: `resultados/respuestas_33_preguntas.md`.

## Subida de audios y actividad del día 2026-11-04

- **Actividad del día 2026-11-04:** procesamiento de entrevistas a partir de
  `Entrevistas.docx` (scripts `04_procesar_entrevistas_playa.py` y
  `05_analisis_entrevistas.py`; JSONL y resúmenes generados).
- **Días con actividad de subida de audios (`.m4a`)** (archivos con modificación
  registrada):

  - **2026-10-27:** `Entrevista #6.m4a`, `Entrevista#1.m4a`.
  - **2026-10-29:** `Entrevista #10`, `#11`, `#14`, `#15`, `#8`, `#12`, `#13`, `#2`,
    `#3`, `#4`, `#5`, `#7` (más `Entrevista #10` en `proyecto-mercado-inmobiliario-cubano`).
  - **2026-11-01:** `Entrevista #17`, `#19`, `#16`, `#9`.
  - **2026-11-02:** `Entrevista #18`, `#20`, `#26`, `#21`, `#22`, `#23`, `#24`, `#25`.

  > Nota: los audios se registraron tanto en `entrevistas/` como en
  > `proyecto-mercado-inmobiliario-cubano/entrevistas/` (mismo contenido).

## Problemas encontrados y soluciones
- Boxplot: matplotlib 3.11 exige `tick_labels` / `whiskerprops`; no usar `labels` ni
  `whiskprops`. Se corrigieron y se regeneró `graficos/4_boxplot_fuentes.png`.
- Dona: `ax.pie` devolvió más de 2 valores → se evitó el unpack.
- Gráficos: `savefig` fallaba por archivo bloqueado → se eliminó antes de regenerar.
- Handoff: archivo `Handoff No.1.txt` estaba vacío → se actualizó.
- Respuestas 33 preguntas: se generó la tabla con las 33 preguntas, sus respuestas,
  fuente y estado; se incluyó el hallazgo del sesgo geográfico (La Sierra en entrevistas,
  La Ceiba en redes) en P1–P3 y P27–P30.

## Archivos creados / modificados
- `scripts/04_procesar_entrevistas_playa.py` — nuevo.
- `scripts/05_analisis_entrevistas.py` — nuevo.
- `scripts/grafico_brecha_migracion.py` — nuevo.
- `scripts/grafico_margen_negociacion.py` — nuevo.
- `scripts/grafico_dona_problemas.py` — nuevo.
- `scripts/grafico_boxplot_fuentes.py` — nuevo.
- `data/raw/entrevistas_playa.jsonl` — nuevo.
- `data/processed/agencias_online.jsonl` — nuevo.
- `resultados/analisis_entrevistas.txt` — nuevo.
- `resultados/entrevistas_playa_resumen.txt` — nuevo.
- `graficos/1_brecha_migracion.png`, `graficos/2_margen_negociacion.png`,
  `graficos/3_dona_problemas.png`, `graficos/4_boxplot_fuentes.png` — nuevos.
- `resultados/respuestas_33_preguntas.md` — **nuevo en esta sesión final** (tabla con
  las 33 respuestas, fuentes y estado; incluye sesgo geográfico).
- `entrevistas/*.m4a` y `proyecto-mercado-inmobiliario-cubano/entrevistas/*.m4a` —
  audios subidos en los días 2026-10-27, 2026-10-29, 2026-11-01 y 2026-11-02.

## Próximos pasos
- Revisar las respuestas de las 33 preguntas antes de incorporarlas al informe final.
- Push de los commits pendientes (`main...origin/main [ahead 4]`).
- Cerrar el capítulo de resultados y preparar la redacción final del informe.

## Notas
- El 2026-11-04 se procesaron las entrevistas; el 2026-11-05 se añadió el dataset de
  agencias y se generaron los gráficos finales; el mismo día, a las 16:52, se creó
  `resultados/respuestas_33_preguntas.md` con las respuestas a las 33 preguntas.
- El adjunto `ENTREVISTAS TRANSCRITAS.txt` llegó vacío (0 bytes); la fuente real es
  `Entrevistas.docx`.
- `plan_b`: null en los 30 registros. "No acepto menos" se codifica como margen 0.
- Entrevista #30: `habitaciones = null` (respuesta 108 imposible). Entrevista #3:
  `precio_minimo = null` (falta la pregunta 14).
