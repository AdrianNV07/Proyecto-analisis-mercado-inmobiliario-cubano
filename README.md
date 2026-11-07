# 🏠 El precio de la maleta: La migración invisible en el mercado inmobiliario de Playa

Este repositorio contiene el código, los datos procesados y los resultados del proyecto final de Ciencia de Datos sobre el impacto de la crisis migratoria en el mercado inmobiliario del municipio de Playa, La Habana (2026).

## 📌 Hallazgo Principal
El estudio revela una profunda asimetría de información: mientras el 0% de los anuncios online menciona la migración, el 33.3% de los vendedores en la calle confiesa que vende para emigrar. Los vendedores ocultan su urgencia y los problemas de las viviendas (75% de ocultamiento) para no perder poder de negociación. Como resultado, los migrantes aceptan rebajas de precio de casi el doble (7.82%) que los no migrantes (4.96%).

## 📊 Fuentes de Datos (Los 4 Pilares)
1. Web Scraping (Revolico): 515 anuncios extraídos de toda La Habana.
2. Agencias Online: 30 anuncios de catálogos formales (Casaoasis).
3. Redes Sociales: 30 anuncios de grupos de Facebook/WhatsApp.
4. Entrevistas Callejeras: 30 vendedores reales entrevistados en Playa.

## 🛠️ Stack Tecnológico
- Lenguaje: Python 3.13
- Extracción: Requests, BeautifulSoup4
- Análisis: Pandas, Numpy, Scikit-learn (K-Means, PCA, TF-IDF)
- Visualización: Matplotlib, Seaborn
- Desarrollo: Git, OpenCode (Asistente de IA)

## 📂 Estructura del Repositorio
- scripts/: Todo el código de scraping, limpieza y análisis (Python).
- data/processed/: Datasets finales procesados en formato JSONL.
- resultados/: Informes de texto generados (análisis, comparativas y reporte técnico).
- graficos/: Visualizaciones generadas (mapas, clústeres, boxplots).
- docs/: Documentación del proyecto, journals y matriz de preguntas.
- index.html: Prototipo web (MVP) de "PlayaTransparente", una propuesta para mitigar la asimetría de información.

## 👨‍💻 Autor
[Tu Nombre Completo] - Estudiante de Ciencia de Datos.
*Profesor:* Yudivian Almeida.
*Asignatura:* [Nombre de la asignatura].

> *Nota metodológica: El estudio se apoya en el análisis histórico de Almeida (2013) y en los datos demográficos oficiales de la ONEI.*
