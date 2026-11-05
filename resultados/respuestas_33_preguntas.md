# Respuestas — 33 Preguntas de Investigación

**Estudio de caso:** Crisis migratoria y mercado inmobiliario en Playa, La Habana.

**Base metodológica:** Las respuestas se redactan a partir de los hallazgos ya
generados en el proyecto (Pilar 1–3: `data/processed/` y `data/raw/`;
Pilar 4: `data/raw/entrevistas_playa.jsonl`; análisis: `resultados/`; NLP:
clustering de texto sobre `data/processed/playa_limpio_v2.csv`).

> **Nota:** cada respuesta debe acompañarse del tamaño de muestra (`n`) de la
> fuente que la sustenta, y dentro del alcance del estudio de caso (Playa).

---

## Tabla de respuestas

| # | Pregunta | Respuesta | Fuente | Estado |
|---|---|---|---|---|
| 1 | ¿Cuál es el precio promedio y mediano de las viviendas en Playa? | Mediana de 46,500 USD (n=106 anuncios de Playa en Revolico; media de 146,333 USD por outliers, rango 1,100–2,200,000 USD). Por fuente: redes 27,500 USD (n=30); agencias 70,000 USD (n=30); entrevistas 37,500 USD (n=30). Al excluir La Sierra, la mediana de las entrevistas baja a 35,000 USD, lo que sugiere que la diferencia no es del canal sino de la zona (sesgo geográfico). | Triangulación (Revolico / Redes / Agencias / Entrevistas) | Respondida |
| 2 | ¿Cómo se distribuyen los precios según el tipo de inmueble? | En Playa (Revolico, n=106): apartamento mediana 25,000 USD; casa 70,000; habitacion 100,000; local 58,500; solar 115,000; otro 1,167. El apartamento es el tipo mas ofertado (44 anuncios, 41.5%). | Revolico (NLP) | Parcial |
| 3 | ¿Existe una diferencia significativa de precios entre los barrios de Playa? | No interpretable con inferencia (n<3 en la mayoria de barrios). Solo 4 barrios alcanzan n>=3 en ambos canales. Hallazgo geografico: entrevistas sobrerrepresentadas por La Sierra (mediana 45,000 USD; sin La Sierra 35,000 USD) y redes por La Ceiba (mediana 13,500 USD). Diferencia por barrio no estadisticamente interpretable. | Triangulacion (Entrevistas / Redes) | Limitación |
| 4 | ¿Cuál es el precio por metro cuadrado promedio en Playa? | n=36 anuncios con metros cuadrados: media 661 USD/m2, mediana 552 USD/m2. Entrevistas: medianos 312.5 (migrantes) vs 479.0 (no migrantes) USD/m2. | Triangulacion | Parcial |
| 5 | ¿Qué tipo de inmueble es el más ofertado en Playa? | Apartamento (44 anuncios, 41.5% de Playa en Revolico). Redes: casa 18 / apartamento 12; agencias: Apartamento 12, Casa Independiente 10, Casa 6, Biplanta 2. | Revolico / Redes / Agencias (NLP) | Respondida |
| 6 | ¿Cuántas habitaciones y baños tienen en promedio las viviendas ofertadas? | Playa: promedio habitaciones 3.35; banos 2.39 (n=106 con dato). Para analisis de banos usar banos_inferido == False. | Revolico | Parcial |
| 7 | ¿Existe una relación entre la cantidad de palabras en la descripcion y el precio del inmueble? | Correlacion de Pearson r=0.170 (n=105), debil. Clusters: casas 87 palabras / 70,000; agencias 127 / 150,000; Miramar-papeles 79 / 25,000; edificios capitalistas 51 / 20,000. | NLP | Parcial |
| 8 | ¿Qué porcentaje de anuncios en Playa menciona explicitamente urgencia por viaje o migracion? | 0% (0/135 anuncios de Playa en dataset unificado; Revolico 0/106, redes 0/30). Entrevistas: 10/30 = 33.3% declaran migracion. | NLP / Triangulacion | Respondida |
| 9 | ¿Los anuncios con menciones de urgencia tienen precios mas bajos que los que no las mencionan? | No aplica: no hay anuncios con menciones de urgencia (0%). | Redes / Revolico | No respondida |
| 10 | ¿Cual es el margen de negociacion promedio entre el precio publicado y el precio minimo aceptable? | Migrantes: media 3.13%, mediana 0 (n=10). No migrantes: media 1.42%, mediana 0 (n=14). Robustez (solo margen > 0): migrantes n=4 media 7.82% mediana 6.12%; no migrantes n=4 media 4.96% mediana 3.91%. Casos margen 0: 17/29 = 58.6%. | Entrevistas | Parcial |
| 11 | ¿Los vendedores con urgencia migratoria estan dispuestos a bajar mas el precio que los no urgentes? | Descriptivamente si: migrantes media 3.13% vs no migrantes 1.42%; robustez 7.82% vs 4.96%. Interpretacion: menor margen implica mayor urgencia. | Entrevistas | Parcial |
| 12 | ¿Existe una relacion entre el tiempo que lleva el anuncio publicado y la probabilidad de mencionar urgencia? | No analizada con los datos disponibles. | Entrevistas / NLP | Limitación |
| 13 | ¿La urgencia migratoria afecta de forma diferente a los distintos segmentos de mercado? | No determinada con rigor (n insuficiente). Clusters: agencias 0%, casas 1.9%, Miramar/papeles 5.9%. | NLP | Limitación |
| 14 | ¿Existe una diferencia significativa en el margen de negociacion entre los vendedores con motivacion migratoria y los que no la tienen? | Diferencia descriptiva: migrantes media 3.13% vs no migrantes 1.42%; robustez 7.82% vs 4.96%. Sin prueba de significancia formal (n pequenos). | Entrevistas | Parcial |
| 15 | ¿Los anuncios con urgencia usan un lenguaje mas emocional o directo? | No hay anuncios con urgencia (0%). Razones declaradas para no publicar: perdida de poder de negociacion 40%, no interes del comprador 30%, norma informal 20%, privacidad 10%. | Entrevistas / NLP | Respondida |
| 16 | ¿Que porcentaje de anuncios menciona problemas estructurales? | Aproximadamente 2% de anuncios de Playa (2/105 en limpieza). Entrevistas: 3/30 = 10% declararon problema; 75% de quienes declararon ocultaron (3/4). | NLP / Entrevistas | Parcial |
| 17 | ¿Los vendedores con urgencia migratoria ocultan mas problemas estructurales que los no urgentes? | No se puede inferir (n=4 en declarar problema). | Entrevistas | Limitación |
| 18 | ¿Existe una diferencia entre lo que se publica en Revolico y lo que se revela en las entrevistas presenciales? | Si. Revolico: 0/135 publican migracion; entrevistas: 10/30 = 33.3% la declaran; 0/10 la pusieron en anuncio. Omision estrategica. | Triangulacion | Respondida |
| 19 | ¿Las inmobiliarias publican mas detalles sobre el estado del inmueble que los particulares? | Cluster agencias: n=16, 0% menciones problemas; cluster casas: 3.8%. Intermediarios median 97,500 vs particulares 37,000 (+163.5%; ratio 2.64x). | NLP / Triangulacion | Parcial |
| 20 | ¿Como varia la longitud de las descripciones segun la fuente? | Longitud media Playa Revolico: 80 palabras (min 5, max 155). Cluster agencias: 127 palabras; cluster edificios capitalistas: 51. | NLP | Respondida |
| 21 | ¿El uso de lenguaje tecnico o formal esta asociado a precios mas altos? | Cluster agencias: mediana 150,000 USD (la mas alta de los 4 clusters); vocabulario tecnico (ref, qr, cisterna, tanque motor). Asociacion descriptiva (n=16). | NLP | Parcial |
| 22 | ¿Se pueden identificar perfiles discursivos diferenciados en los anuncios de Playa? | Si, con K=4 (silhouette 0.131, bajo). Perfiles: casas familiares n=52 mediana 70,000; agencias n=16 mediana 150,000; Miramar/papeles n=17 mediana 25,000; edificios capitalistas n=20 mediana 20,000. PCA: 19.8% varianza. | NLP | Parcial |
| 23 | ¿Que palabras clave estan mas asociadas a la urgencia migratoria? | Ninguna: 0% de anuncios la mencionan. Keywords depuradas; no se identifican terminos por ausencia. | NLP | No respondida |
| 24 | ¿Que palabras clave estan mas asociadas a problemas estructurales? | Aproximadamente 2% de anuncios de Playa; cluster casas 3.8%. | NLP | Parcial |
| 25 | ¿Existen diferencias en el lenguaje utilizado segun el barrio? | Redes: precision de barrio 76.7% vs Revolico 23.8% (3.2x). Comparacion por barrio entre canales no viable (n<3). | Redes / NLP | Limitación |
| 26 | ¿Se puede predecir el segmento de mercado basandose unicamente en el texto? | No: K=4, silhouette bajo, PCA 19.8%, agrupa por estilo/tema no por motivacion. | NLP | No respondida |
| 27 | ¿Existen diferencias significativas de precio entre Revolico, inmobiliarias y redes sociales? | Si descriptivas. Playa: intermediarios Revolico median 97,500 vs particulares 37,000 (+163.5%; ratio 2.64x); redes intermediarios 40,000 vs particulares 22,000 (+81.8%; ratio 1.82x). Medianas por fuente: Revolico 46,500; redes 27,500; agencias 70,000; entrevistas 37,500. Sesgo geografico: entrevistas La Sierra 45,000; sin La Sierra 35,000; redes La Ceiba 13,500. | Triangulacion | Parcial |
| 28 | ¿Los anuncios de redes sociales son mas informales o mas urgentes que los de Revolico? | Redes: urgencia migratoria 0 (n=30); medianas de precio mas bajas (27,500 vs 46,500). No mas urgentes. | Redes / NLP | Parcial |
| 29 | ¿Las inmobiliarias tienden a publicar precios mas altos que los particulares en Revolico? | Si: medianas 97,500 vs 37,000 en Playa (+163.5%; ratio 2.64x); en La Habana +119% (52,500 vs 24,000). | Triangulacion / Revolico | Parcial |
| 30 | ¿Que fuente de datos ofrece una vision mas realista del mercado? | Entrevistas (Pilar 4): 33.3% declaran migracion vs 0% online; omision estrategica. Mercado online ciego para motivacion migratoria. | Entrevistas | Respondida |
| 31 | ¿Cual es la percepcion de los residentes de Playa sobre el impacto de la migracion en los precios? | Entrevistas: percepcion de precios; medianos 312.5 (migrantes) vs 479.0 (no migrantes) USD/m2. Razones preferencia Playa: tranquilidad (46.7%), belleza (40%), desarrollo economico (30%). | Entrevistas | Parcial |
| 32 | ¿Que motivos de venta son mas frecuentes en la calle? | Migracion 33.3% (10/30); Otro 36.7%; Economico 13.3%; Sin respuesta 16.7%. Razones Playa: tranquilidad (46.7%), belleza (40%), desarrollo economico (30%). | Entrevistas | Respondida |
| 33 | ¿Como perciben los vendedores la demanda actual y como adaptan su estrategia de precios? | Estrategia: no acepto menos (margen 0) en 17/29 = 58.6%. Vendedores migrantes omitian migracion para no perder poder de negociacion. | Entrevistas | Parcial |

---

## Metodología aplicada a las respuestas

- **Nivel macro:** contexto de toda La Habana (Pilares 1-2) para situar a Playa.
- **Nivel caso:** Playa (Pilares 1 y 3) + entrevistas (Pilar 4).
- **Muestras pequeñas:** con n < 30 se reportan estadísticas descriptivas, sin
  inferencia formal ni clustering sobre subgrupos.
- **Sesgo geográfico documentado:** entrevistas sobrerrepresentadas por La Sierra
  (mediana 45,000 USD; sin La Sierra 35,000 USD) y redes sociales por La Ceiba
  (mediana 13,500 USD). La diferencia de precios no se atribuye al canal, sino
  a la zona.
- **Fuente unificada vs. separada:** las respuestas se elaboran sobre los
  archivos sin unificar (entrevistas, agencias y dataset unificado se leen por
  separado), y se triangulan entre fuentes para los cruces.
