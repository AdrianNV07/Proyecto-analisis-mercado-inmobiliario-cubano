# AGENTS.md — Crisis Migratoria y Mercado Inmobiliario en Playa, La Habana

## 🎯 Objetivo del proyecto

**Estudio de caso** con **enfoque mixto** sobre el impacto de la **crisis
migratoria** en el mercado inmobiliario del **municipio de Playa (La Habana)**.

Combina dos tipos de evidencia:

| Tipo de evidencia | Rol |
|---|---|
| **Cuantitativa online** (Pilares 1-3) | Contexto macro y comparación de tendencias |
| **Cualitativa/cuantitativa presencial** (Pilar 4) | Fuente principal |

### Los cuatro pilares de recolección

| # | Pilar | Cobertura | Rol en el análisis |
|---|---|---|---|
| 1 | **Scraper de Revolico** | Toda La Habana | Contexto macro y tendencias |
| 2 | **Sitios especializados (inmobiliarias)** | Toda La Habana | Precios formales vs. informales |
| 3 | **Redes sociales (Facebook/Telegram)** | Playa y zonas de oferta | Contexto social, validar Revolico |
| 4 | **Entrevistas callejeras** | Solo Playa | **Fuente principal** |

Los pilares 1-3 son datos de terceros: describen **qué se publica**, no **por qué
se vende**. El pilar 4 es el eje interpretativo: las entrevistas capturan los
motivos que los anuncios no verbalizan.

Tres dimensiones de análisis:

| Dimensión | Métricas clave |
|---|---|
| **Precios** | Precio por m², distribución por tipo, dispersión por barrio |
| **Urgencia de venta** | `%` con señales de urgencia, precio de lista vs. mínimo aceptable |
| **Percepción de la emigración** | Motivos de venta codificados, efecto percibido en el barrio |

> **Alcance geográfico: La Habana, con foco en Playa.**
> Los datos de los pilares 1-2 cubren los 15 municipios de la capital y se usan
> como **contexto comparativo**. El pilar 3 se concentra donde haya actividad
> de grupos de compraventa. El análisis de precios, los cruces con entrevistas y
> las conclusiones se restringen a **Playa**. Nunca se extrapolan resultados de
> Playa al resto de la ciudad: es un estudio de caso, no representativo.

> **Limitación asumida.** El muestreo de entrevistas es no probabilístico (ver
> Pilar 4). Los resultados describen a las personas entrevistadas, no a la
> población de Playa. Reportar siempre el `n` y el método de selección.

---

## 🧱 Estructura del repositorio

```
.
├── AGENTS.md
├── README.md
├── requirements.txt
├── config/
│   └── config.yaml            # URLs, delays, rutas, parámetros de scraping
├── data/
│   ├── raw/                   # Datos sin procesar — solo lectura
│   │   ├── revolico_ventas.jsonl      # Pilar 1: toda La Habana
│   │   ├── inmobiliarias_ventas.jsonl # Pilar 2: portales formales
│   │   ├── grupos_manual.csv          # Pilar 3: Facebook/Telegram
│   │   ├── entrevistas_playa_raw.txt  # Pilar 4: transcripciones
│   │   └── entrevistas_playa.csv      # Pilar 4: codificadas
│   ├── interim/               # Datos limpios / normalizados
│   └── processed/             # Datasets analíticos finales
├── resultados/
│   └── analisis_playa.txt     # Hallazgos finales del estudio de caso
├── logs/                      # Logs de ejecución (scraping, errores)
├── notebooks/                 # Análisis exploratorio
├── scripts/
│   ├── scraper_revolico.py          # Pilar 1 (nombre real actual)
│   ├── 02_plantilla_csv.py
│   ├── 03_procesar_entrevistas.py
│   ├── 04_unificar_datasets.py
│   ├── 05_analisis_final.py
│   └── resumen_revolico.py
└── src/
    ├── config.py
    ├── cleaning.py
    ├── schema.py
    └── utils.py
```

**Regla:** `data/raw/` es inmutable. Toda transformación escribe en `interim/`,
`processed/` o `resultados/`.

### Archivos de salida del proyecto

| # | Archivo | Pilar | Contenido | Cobertura |
|---|---|---|---|---|
| 1 | `data/raw/revolico_ventas.jsonl` | 1 | Anuncios scrapeados | Toda La Habana |
| 2 | `data/raw/inmobiliarias_ventas.jsonl` | 2 | Portales formales | Toda La Habana |
| 3 | `data/raw/grupos_manual.csv` | 3 | Grupos de compraventa | Playa y zonas de oferta |
| 4 | `data/raw/entrevistas_playa.csv` | 4 | Entrevistas codificadas | Solo Playa |
| — | `resultados/analisis_playa.txt` | — | Hallazgos y conclusiones | Playa (contexto de ciudad) |

---

## 🐍 Stack tecnológico

- **Python 3.10+** (obligatorio; usar sintaxis `X | None`, `match`, `list[str]`)
- **requests** — cliente HTTP
- **BeautifulSoup4 (bs4)** — parsing de HTML
- **pandas** — manipulación tabular
- **jupyter** — notebooks de análisis
- Entorno virtual `.venv` obligatorio. Nunca instalar paquetes globalmente.

---

## 📌 Pilar 1 — Scraping de Revolico (contexto macro, toda La Habana)

### Script
`scripts/scraper_revolico.py`

> **Rol en el estudio:** los anuncios de toda La Habana son **contexto macro**.
> El análisis de precios y los cruces con entrevistas se focalizan en el
> subconjunto con `municipio == "Playa"`, que es el caso de estudio. El resto de
> municipios se conserva para contrastar el contexto de Playa contra la ciudad.

### Fuente de datos: `__NEXT_DATA__` (no selectores CSS)
Revolico es una **SPA de Next.js**. Los datos de cada anuncio **no están en el DOM**:
los `id` tipo `BasicInfo__Title-*` solo existen dentro del `<style>` de
styled-components, por lo que los selectores CSS deducidos de los fixtures no
funcionan contra el HTML servido.

El flujo real de extracción es:

```
HTML servido
  └─ <script id="__NEXT_DATA__">
       └─ props.pageProps.__APOLLO_STATE__   # estado de Apollo
            └─ "AdType:<id>"                 # entidad del anuncio
                 title, price, currency, description,
                 municipality, province, subcategory (refs)
```

Reglas:
- Parsear `__NEXT_DATA__` con `json.loads`; nunca BeautifulSoup para los datos.
- Las referencias `{"__ref": "Tipo:id"}` se resuelven contra el estado Apollo.
- `price` y `currency` vienen **ya tipados**: no requieren regex.
- El campo `subcategoria` identifica el origen: `Casas` u `Otros - Inmobiliaria`.

### Subcategorías de venta recorridas
Verificadas contra el sitio (septiembre de 2026). Los slugs
`inmobiliaria-apartamentos` e `inmobiliaria-solares` **no existen** (HTTP 500):

| Subcategoría | Anuncios |
|---|---|
| `inmobiliaria-casas` | Principal |
| `inmobiliaria-otros-inmobiliaria` | Mezcla locales, solares, terrenos |

`Otros - Inmobiliaria` mezcla tipos de inmueble. El campo `tipo_inmueble` permite
filtrar por vivienda en el análisis de Playa.

### Esquema de salida
**Archivo:** `data/raw/revolico_ventas.jsonl` (un objeto JSON por línea, UTF-8)

| Campo | Tipo | Notas |
|---|---|---|
| `titulo` | str | Del `AdType` |
| `precio` | float \| null | Ya tipado por la API |
| `moneda` | str | `USD` / `CUP` / `MLC` / `EUR` |
| `descripcion` | str | Texto completo |
| `municipio` | str \| null | Normalizado a los 15 de La Habana |
| `municipio_bruto` | str \| null | Texto original de la API |
| `provincia` | str | — |
| `subcategoria` | str | `Casas` / `Otros - Inmobiliaria` |
| `habitaciones` | int \| null | Regex; rangos `N/M` toman el mínimo |
| `banos` | int \| null | 4 estrategias, ver abajo |
| `banos_inferido` | bool | `True` si se dedujo por singular |
| `tipo_inmueble` | str | Vocabulario cerrado |
| `menciona_urgencia_viaje` | bool | Ver reglas de keywords |
| `menciona_problemas_estructurales` | bool | — |
| `cantidad_palabras` | int | — |
| `url` | str | Clave de deduplicación |

### Campo `menciona_urgencia_viaje`: hallazgo empírico
En la muestra scrapeada (308 anuncios, 69 de Playa) el resultado es **0/308**.
Ningún anuncio de venta verbaliza la emigración de forma explícita.

Keywords vigentes tras depurar:

```python
URGENCIA_VIAJE_KEYWORDS = [
    "viaje", "viaje al extranjero", "me voy", "me voy del pais",
    "emigrar", "emigrando", "visa", "pasaje",
    "reunificacion familiar", "reunion familiar",
    "salida del pais", "me marcho", "partiendo",
    "mudanza al extranjero", "me mudo al extranjero",
]
```

**Eliminadas y por qué:**
- `"urge"` → matcheaba con `URGENTE`, presente en casi todos los títulos.
- `"salida"` → matcheaba con `"salida de emergencia"`, `"la salida del garaje"`.
- `"oportunidad unica"` → lenguaje publicitario de anuncios de lujo.

> **Consecuencia metodológica:** esta variable **no puede** usarse para medir la
> urgencia migratoria en Playa. Constituye evidencia negativa: los vendedores no
> verbalizan la emigración. La aproximación válida es cruzar los motivos de venta
> declarados en las entrevistas (Pilar 3) contra los anuncios, no esperar que el
> anuncio declare la emigración.

### Campo `banos`: cuatro estrategias
1. Rango `N/M` (`"2/3 baños"`) → toma la **parte baja** (interpretación
   conservadora). Se evalúa antes de las demás porque `"3 baños"` dentro de
   `"2/3 baños"` encajaría en el patrón de cantidad.
2. Cantidad explícita: `"2 baños"`, `"un baño"`, `"3 wc"`, `"toilette"`.
3. Singular sin cantidad (`"cocina, baño/lavadero"`) → `1`, marcado con
   `banos_inferido = True`. **Es una inferencia, no una extracción.**
4. Plural sin cantidad (`"2 plantas con baños"`) → `None`.

En la muestra, una proporción relevante de los valores de `baños` son inferidos.
Para inferencia estadística usar solo `banos_inferido == False`.

### Paginación y control de duplicados
- Paginación real del sitio: `&cu=0&page=N` a partir de la página 2.
- El JSONL se abre en modo `append`. Antes de procesar cada anuncio se comprueba
  si su `url` ya está en el archivo; si lo está, se omite **sin petición HTTP**.
- Al final se ejecuta una limpieza que conserva la primera aparición de cada
  `url` (escritura en `.tmp` y sustitución atómica).
- Si una página devuelve 0 resultados, se registra `WARNING` y se continúa con
  la siguiente: el script es reanudable e idempotente.

---

## 📝 Pilar 2 — Sitios especializados / inmobiliarias (precios formales)

### Script
`scripts/02_plantilla_csv.py`

Genera una **plantilla vacía con encabezados** para registrar anuncios de portales
inmobiliarios formales y gestores: Vivopedia, Infocasa, Cubanet y agencias
con sitio web.

> **Rol en el estudio:** permite contrastar el **precio formal** (agencia, con
> comisión, contrato) contra el **precio informal** del Pilar 1. Si hay diferencia
> sistemática en Playa, indica un costo de intermediación que presiona al
> vendedor directo.

**Archivo:** `data/raw/inmobiliarias_ventas.jsonl`

> Los grupos de redes sociales se registran aparte, en el **Pilar 3**
> (`data/raw/grupos_manual.csv`), porque tienen dinámica y tratamiento distintos.

### Columnas (en este orden exacto)
```
precio, tamaño, habitaciones, estado_casa, tipo_inmueble, fuente,
fecha_publicación, moneda, dirección, baños, espacios_exteriores, casa_amueblada
```

| Columna | Tipo | Notas |
|---|---|---|
| `precio` | float | Sin símbolo de moneda |
| `tamaño` | float | m² |
| `habitaciones` | int | — |
| `estado_casa` | str | Vocabulario cerrado (ver abajo) |
| `tipo_inmueble` | str | Mismo vocabulario que Pilar 1 |
| `fuente` | str | `Vivopedia`, `Facebook`, `WhatsApp`, etc. |
| `fecha_publicación` | str | ISO `YYYY-MM-DD` |
| `moneda` | str | `CUP` / `USD` / `EUR` |
| `dirección` | str | — |
| `baños` | int \| null | — |
| `espacios_exteriores` | int \| null | Cantidad (jardín, patio, terraza…) |
| `casa_amueblada` | bool | `True` / `False` |

### Vocabulario cerrado para `estado_casa`
```
nuevo | como_nuevo | remodelado | bueno | necesita_reparacion | para_remodelar
```

### Comportamiento del script
- Escribir el CSV **con encabezados y sin filas de datos**.
- Crear el archivo solo si no existe. **Nunca sobrescribir** un CSV con datos
  registrados manualmente; preguntar al usuario antes de cualquier operación
  destructiva sobre este archivo.
- Usar `csv.DictWriter` con `newline=""` y `encoding="utf-8-sig"` (para que Excel
  abra bien los acentos en Windows).
- No inventar ni rellenar valores de ejemplo: la plantilla es solo de estructura.

---

## 📱 Pilar 3 — Redes sociales (grupos de Facebook/Telegram)

### Script
`scripts/03_grupos_sociales.py`

> **Rol en el estudio:** los grupos de compraventa son la vía por la que muchos
> vendedores publican **evitando el costo o la exposición de un portal
> formal**. Aporta el contexto social que Revolico no captura, y permite
> **validar** que las tendencias observadas en el Pilar 1 no son un artefacto de
> esa plataforma.

**Archivo:** `data/raw/grupos_manual.csv`

### Método de recolección: manual
A diferencia del Pilar 1, aquí **no se automatiza**. Motivos:

- Los grupos de Facebook y Telegram **requieren autenticación** y en muchos
  casos tienen acuerdo con la plataforma que prohíbe el acceso automatizado.
- Scrapear grupos cerrados viola los términos de servicio.
- El volumen es mucho menor: la recolección manual es viable y más fiable.

**Regla:** registrar manualmente cada anuncio relevante, anotando el
**nombre del grupo** como campo obligatorio. Es trazabilidad y permite saber si
un precio corresponde a un grupo informal o a una inmobiliaria.

### Columnas
```
fecha_publicacion, precio, moneda, tamano, habitaciones, banos, tipo_inmueble,
municipio, barrio, direccion, casa_amueblada, publicado_en_revolico,
grupo, enlace_publicacion, urgencia_declarada, motivo_declarado
```

| Columna | Tipo | Notas |
|---|---|---|
| `fecha_publicacion` | str | ISO `YYYY-MM-DD` |
| `precio` | float \| null | Sin símbolo de moneda |
| `moneda` | str | `USD` / `CUP` |
| `tamaño` | float \| null | m² |
| `habitaciones` | int \| null | — |
| `baños` | int \| null | Marcar si fue inferido |
| `tipo_inmueble` | str | Vocabulario cerrado |
| `municipio` | str \| null | Normalizado a los 15 |
| `barrio` | str \| null | Para análisis en Playa |
| `direccion` | str | — |
| `casa_amueblada` | bool | — |
| `publicado_en_revolico` | bool | ¿El mismo inmueble también está en Revolico? |
| `grupo` | str | **Obligatorio.** Nombre del grupo o chat |
| `enlace_publicacion` | str \| null | Enlace al post, si es accesible |
| `urgencia_declarada` | bool | El texto dice urgencia |
| `motivo_declarado` | str \| null | Si el vendedor lo menciona |

### Reglas de privacidad y consentimiento
- **No publicar capturas de pantalla** que identifiquen al vendedor.
- No incluir teléfono ni nombre de usuario del vendedor en el dataset.
- Los grupos son espacios privados: **no reenviar** contenido a terceros.
- Si un post contiene datos personales, se registra solo el inmueble, no la
  persona.

### Observación clave para Playa
El campo `publicado_en_revolico` permite responder una pregunta que el Pilar 1
no puede: ¿los anuncios de Playa que aparecen en grupos informales son
**anuncios distintos** de los de Revolico, o los mismos inmuebles publicados en
dos canales? Esto cambia la lectura de la oferta total.

---

## 🎤 Pilar 4 — Entrevistas callejeras en Playa (FUENTE PRINCIPAL)

### Script
`scripts/04_procesar_entrevistas.py`

**Entrada:** `data/raw/entrevistas_playa_raw.txt`
**Salida:** `data/raw/entrevistas_playa.csv`

> **Rol en el estudio:** es la **fuente principal**. A diferencia del Pilar 1,
> donde los anuncios no verbalizan la migración, las entrevistas sí capturan el
> motivo real de la venta. El scraping de Revolico sirve para contrastar precios
> y calibrar lo que declaran los entrevistados.

### Alcance geográfico: exclusivamente Playa
Las entrevistas se realizan **solo en el municipio de Playa**. Los barrios
objetivo incluyen Miramar, Pueblo Nuevo, La Ceiba, La punta, Alamar, Siboney y
sectores URJC.

- Registrar el `barrio` declarado por cada entrevistado.
- Si la entrevista se realiza fuera de Playa, **no incluirla** en el dataset.
- No se extrapola a otros municipios: es un estudio de caso.

### Diseño de la encuesta: instrumento mixto

**Preguntas cerradas (cuantificables):**

| Campo | Tipo | Notas |
|---|---|---|
| `motivo_venta` | str | Vocabulario cerrado, ver abajo |
| `precio_lista` | float | Precio pedido públicamente |
| `precio_minimo` | float | Mínimo aceptable por el vendedor |
| `publico_revolico` | bool | ¿Publicó en Revolico? |
| `publico_redes` | bool | ¿Publicó en redes/grupos? |

El par `precio_lista` / `precio_minimo` es la **medición directa de la urgencia
de venta**: la brecha entre ambos cuantifica cuánta margen hay para negociar, que
es un proxy de urgencia que sí es observable (a diferencia de
`menciona_urgencia_viaje` en los anuncios, que da 0).

**Preguntas abiertas (cualitativas → cuantificadas):**

| Campo | Tipo | Notas |
|---|---|---|
| `percepcion_migracion` | str | Texto libre: ¿qué pasa con la migración en el barrio? |
| `percepcion_precios` | str | Texto libre: ¿cómo afecta a los precios? |
| `motivo_venta_codificado` | str | Categoría asignada al texto abierto |

**Codificación de las respuestas abiertas.** El texto libre se transforma en
variables cuantitativas mediante un **libro de códigos cerrado**:

```python
MOTIVOS_CODIFICADOS = {
    "migracion":              # emigración, viaje, visa, familia en el exterior
    "economico":              # necesidad de dinero, deuda, gastos
    "diferencia_cambiaria":   # el precio en CUP/USD cambió
    "herencia":               # herencia, reparto familiar
    "cambio_vivienda":        # se muda, quiere otro lugar
    "venta_especulativa":     # inversión, esperar que suba
    "problema_inmueble":      # humedad, problemas estructurales, papeles
    "otro":                   # no encaja en ninguna categoría
}
```

Reglas de codificación:
- Cada respuesta abierta recibe **una** categoría primaria. Si es ambigua,
  registrar `otro` y anotar el caso cualitativamente.
- Guardar **siempre** el texto original junto al código: el dato cualitativo
  no se descarta al cuantificar.
- El libro de códigos debe permanecer **estable** durante todo el análisis. Si
  hay que añadir una categoría, se documenta el cambio y se recodifica todo el
  dataset para mantener comparabilidad.
- Documentar el **`n` por categoría**. Con muestras pequeñas, una categoría con
  1 o 2 casos no admite interpretación; se reporta como anecdotal.

### Esquema de salida
**Archivo:** `data/raw/entrevistas_playa.csv`

| Columna | Tipo | Notas |
|---|---|---|
| `nombre_persona` | str | — |
| `carné_identidad` | str | **Anonimizado** (hash SHA-256, ver abajo) |
| `barrio` | str | Miramar, Pueblo Nuevo, La Ceiba… |
| `fecha_entrevista` | str | ISO `YYYY-MM-DD` |
| `motivo_venta` | str | Vocabulario cerrado |
| `motivo_venta_codificado` | str | Categoría del texto abierto |
| `precio_lista` | float \| null | — |
| `precio_minimo` | float \| null | — |
| `moneda` | str | `USD` / `CUP` |
| `tamaño` | float \| null | m² |
| `habitaciones` | int \| null | — |
| `banos` | int \| null | Marcar si es inferido |
| `tipo_inmueble` | str | Vocabulario cerrado |
| `publico_revolico` | bool | — |
| `publico_redes` | bool | — |
| `percepcion_migracion` | str | Texto abierto (se conserva) |
| `percepcion_precios` | str | Texto abierto (se conserva) |
| `direccion` | str | — |
| `espacios_exteriores` | int \| null | — |
| `casa_amueblada` | bool | — |

### 🔒 Privacidad — regla no negociable
- **`carné_identidad` nunca se almacena en texto claro.** Hashing con SHA-256 + salt
  fijo del proyecto, tomando solo los primeros 12 caracteres del digest.
- No incluir teléfono, correo ni dirección exacta del entrevistado. Solo el
  municipio y el barrio, que son datos de agregado.
- Los textos abiertos pueden contener información que identifique indirectamente
  a la persona (nombres de familiares, detalles de la vivienda). **Releer y
  anonimizar antes de escribir el CSV.**

### Parsing del texto
- Segmentar por entrevista con un delimitador explícito (`---` o `### Entrevista N`).
- Regex tolerantes a variantes de escritura ("3 habitaciones", "3 hab", "tres
  dormitorios", "1/2").
- Si un campo no aparece → vacío. **Nunca inventar ni imputar valores.**
- Detectar la moneda por contexto textual ("dólares", "USD", "euros", "pesos"),
  no solo por el símbolo.

---

## 🛡️ Reglas de scraping (obligatorias)

Estas reglas aplican a **todo** script que acceda a un sitio web.

### 1. Respetar `robots.txt`
- Antes de scrapear un dominio, **descargar y parsear su `robots.txt`** con
  `urllib.robotparser.RobotFileParser`.
- Verificar la ruta específica (`can_fetch(user_agent, url)`) para **cada** URL antes
  de cada petición.
- Si `robots.txt` no responde (404) o falla el parseo → **abortar el scraping** de ese
  dominio y loguear `WARNING`. Ante la duda, no scrapear.
- Respetar también `Crawl-delay` si está definido (usar el mayor entre el valor de
  `robots.txt` y el delay propio).
- Si el `User-Agent` de `robots.txt` devuelve una regla específica para nuestro
  crawler, se aplica esa.

### 2. Delays aleatorios
- **Delay aleatorio uniforme entre 3 y 5 segundos** entre peticiones.

```python
import random
time.sleep(random.uniform(3, 5))
```

- El delay se aplica **siempre**, también entre páginas y también después de errores.
- Nunca hacer peticiones concurrentes al mismo dominio (sin `ThreadPool`, sin `asyncio`
  con ráfagas). El scraping es **estrictamente secuencial**.
- El primer request de cada sesión no requiere delay, pero sí todos los siguientes.

### 3. Manejo de errores sin detener el script
- El script **nunca debe abortar** por un error de red o de parsing de un anuncio
  individual. Se continúa con el siguiente elemento.
- Códigos a tratar:

| Situación | Acción |
|---|---|
| HTTP 429 (Too Many Requests) | Log `WARNING`, backoff exponencial (esperar 60 s y reintentar 1 vez) |
| HTTP 5xx | Log `ERROR`, reintentar hasta 2 veces con backoff, luego continuar |
| HTTP 4xx (otro) | Log `ERROR`, omitir la URL, continuar |
| `requests.Timeout` / `ConnectionError` | Log `ERROR`, reintentar 2 veces, luego continuar |
| `AttributeError`/`IndexError` en BeautifulSoup | Log `WARNING` con el HTML relevante truncado, anunciar saltado |
| Respuesta vacía (0 anuncios) | Log `INFO`, fin del listado |

- Usar un **límite de reintentos** global; nunca reintentar indefinidamente.

### 4. Logging
- Todos los scripts usan `logging` (nunca `print` para diagnostics).
- Archivo de log por script en `logs/`, con marca de tiempo en el nombre:
  `logs/scraper_revolico_YYYY-MM-DD_HHMMSS.log`.
- Formato: `%(asctime)s | %(levelname)-7s | %(message)s`.
- Niveles usados: `DEBUG` (detalle), `INFO` (progreso), `WARNING` (incidencia
  esperada), `ERROR` (fallo recuperable), `CRITICAL` (script abortado).
- El log debe permitir **reconstruir qué se extrajo y qué se perdió**.

### 5. Idempotencia y reanudación
- El JSONL se abre en modo **append**. En cada ejecución, registrar el `url` ya
  procesado y **omitir duplicados** (no volver a guardar el mismo anuncio).
- Permitir reanudar una ejecución interrumpida sin duplicar registros.

---

## 🧹 Limpieza y estandarización de datos

Prioridad alta. Aplicar **al unificar y antes de cualquier análisis**.

1. **Moneda** → `CUP` / `USD` / `EUR` en mayúsculas. Default: `CUP`.
2. **Tamaños** → `float` en m². Patrones: `"80 m2"`, `"80 m²"`, `"80mts2"`, `"80 metros"`.
   Si el valor viene en `"vares"` o `"paces"`, **no convertir** sin un factor de
   conversión verificado: dejar `None` y loguear.
3. **Precios** → `float` sin separador de miles ni símbolo. Manejar `"45 000"`,
   `"45.000"`, `"$1.200"` (ambüedad: validar por contexto de moneda).
4. **Fechas** → ISO `YYYY-MM-DD`. Aceptar `"hace 3 días"`, `"ayer"`, `"hace 2 semanas"`
   como relativas al momento de la extracción.
5. **Booleanos** → `True` / `False` reales. Aceptar `"sí"`, `"si"`, `"y"`, `"1"`, `1`,
   `"x"` como `True`. **Nunca** dejar strings en columnas booleanas.
6. **Municipios** → extraer y normalizar a un vocabulario cerrado. Este campo es
   **central para el análisis geográfico**; debe existir en los tres datasets.

   ```
   La Habana Vieja | Centro Habana | Habana del Este | Habana del Oeste
   Cerro | Marianao | Plaza de la Revolución | Playa
   Guanabacoa | Regla | San Miguel del Padrón | Jesús del Monte | VEDADO
   otro
   ```

   - Cualquier municipio no reconocido tras la normalización → `"otro"`. Registrar en
     el log los valores no reconocidos para poder ampliar el vocabulario en iteraciones
     futuras.
   - Si el anuncio es claramente de **otra provincia** (por ejemplo `Santiago de Cuba`,
     `Matanzas`), se marca `"otro"` y se loguea como `FUERA_DE_ALCANCE` para medir
     cuánto se descarta. No se amplíe el vocabulario más allá de La Habana.
7. **Nulos** → usar `None` (pandas `NaN`). No rellenar con ceros ni medias.
8. **Duplicados** → eliminar por `url` (Pilar 1) o por combinación
   `direccion + tamaño + precio` (Pilares 2 y 3). Registrar cuántos se eliminaron.

### Esquema común de integración
Los tres datasets se alinean en un **esquema unificado** para poder cruzarlos:

```python
ESQUEMA_UNIFICADO = [
    "precio", "moneda", "tamaño", "habitaciones", "baños", "estado_casa",
    "tipo_inmueble", "direccion", "municipio", "fecha_publicación", "url",
    "fuente", "casa_amueblada", "urgencia_viaje", "espacios_exteriores",
]
```

- `menciona_urgencia_viaje` (Pilar 1) y `urgencia_viaje` (Pilar 3) se **unifican** en
  `urgencia_viaje`.
- Pilar 2 se une al esquema unificado aunque no tenga `urgencia_viaje` (se llena con
  `None` / `False` según corresponda, documentando la decisión).
- La columna `fuente` es obligatoria en el esquema unificado: permite distinguir el
  origen de cada registro al hacer los cruces.

---

## 📊 Análisis final — Estudio de caso Playa

**Script:** `scripts/05_analisis_final.py`
**Salida:** `resultados/analisis_playa.txt`

> **Estructura del análisis en dos niveles:**
> 1. **Contexto macro** — anuncios de toda La Habana (Pilares 1-2), para situar a
>    Playa dentro de la distribución de la ciudad.
> 2. **Estudio de caso** — anuncios y grupos de Playa (Pilares 1 y 3) más las
>    entrevistas (Pilar 4), donde se concentran las conclusiones.
>
> Toda cifra debe indicar de qué nivel y de qué pilar proviene.

### Preguntas de investigación

**Nivel macro (toda La Habana):**

1. **¿Dónde se concentra la oferta?** Densidad de anuncios por municipio, tipo
   de inmueble y moneda. Playa como punto de comparación dentro de la ciudad.

2. **¿Qué perfil de precios tiene Playa frente a la ciudad?** Mediana de
   precio por m² en USD, comparando Playa con el resto de municipios.
   Reportar `n` de cada grupo.

**Nivel caso (Playa):**

3. **¿Cuál es el motivo real de venta?** Distribución de
   `motivo_venta_codificado` en las entrevistas de Playa. Esta es la pregunta
   central del estudio, y la que los anuncios no pueden responder.

4. **¿La urgencia de venta es medible?** Brecha entre `precio_lista` y
   `precio_minimo` declarada por cada vendedor. A menor brecha, mayor urgencia
   de venta. Contrastar con los precios publicados en Revolico para Playa.

5. **¿Coincide lo que dicen los vendedores con lo que publican los anuncios?**
   Cruzar `motivo_venta_codificado` (entrevistas) con el precio por m² y la
   urgencia de los anuncios de Playa. Si los vendedores con motivo `migracion`
   fijan precios por debajo de la mediana, es evidencia de presión por venta.

6. **¿Cómo percibe la población la migración?** Análisis temático de
   `percepcion_migracion` y `percepcion_precios`, con la frecuencia de cada
   `motivo_venta_codificado` como variable cuantitativa de apoyo.

7. **¿Hay diferencias entre barrios?** Si el `n` de entrevistas por barrio lo
   permite, comparar `precio_lista` y motivo declarado entre Miramar, Pueblo
   Nuevo, La Ceiba y otros. Con muestras pequeñas, reportar como exploratorio.

8. **¿El precio formal supera al informal?** (Pilares 1 vs 2) Comparar precio por
   m² entre anuncios de Revolico y de inmobiliarias formales para Playa. Una
   brecha positiva y consistente evidencia el costo de intermediación.

9. **¿Los grupos de redes sociales amplían la oferta o la duplican?** (Pilar 3)
   Usar el campo `publicado_en_revolico` para distinguir anuncios nuevos de
   inmuebles ya publicados en Revolico. Si la maioria está duplicada, la oferta
   real de Playa es menor que la suma de los tres pilares.

### Reglas de análisis
- **Documentar cada figura y tabla** generada en `notebooks/`.
- Toda estadística debe ir acompañada de su **tamaño de muestra (n)**.
- No presentar correlaciones como causalidad. Reportar siempre el tamaño del
  efecto.
- **Nunca mezclar CUP y USD sin convertir**, y documentar la tasa usada.
- Para los datos de anuncios, usar solo `banos_inferido == False` cuando el
  análisis dependa de bathrooms.
- `menciona_urgencia_viaje` **no debe usarse** como medida de urgencia: da 0 en
  toda la muestra por diseño del texto de los anuncios.
- **Reportar explícitamente el sesgo de muestreo** de las entrevistas: es una
  muestra no probabilística. Los hallazgos describen a los entrevistados, no
  a la población de Playa.
- Con `n` pequeño, preferir **descripción** sobre inferencia. Una categoría con
  1 o 2 casos se reporta como anecdotal, no como tendencia.
- Concluir siempre dentro del alcance: **resultados sobre Playa**, sin
  extrapolar a La Habana ni a Cuba.

---

## ✅ Convenciones generales

- Código en español para los **nombres de negocio**, inglés para las librerías.
- Docstrings y comentarios en español.
- Tipado con `type hints` en todas las funciones públicas.
- Funciones pequeñas, con una responsabilidad cada una.
- Todo script debe ser ejecutable de forma independiente:
  `python scripts/scraper_revolico.py`.
- Usar `pathlib.Path`, nunca concatenación manual de rutas.
- Variables de entorno para secretos (`.env`, nunca commitear).
- Antes de sobrescribir cualquier archivo existente, **preguntar al usuario**.
- Cada script debe ser **re-ejecutable** sin romper el estado previo.

---

## 🚫 Prohibiciones

- Ignorar `robots.txt` o hacer scraping concurrente/ráfaga.
- Reducir el delay por debajo de 3 segundos.
- Inventar, imputar o rellenar datos faltantes.
- Almacenar `carné_identidad` u otros datos personales en texto claro.
- Sobrescribir `data/raw/` o los CSVs con registro manual.
- Entregar un análisis sin indicar `n` de cada grupo comparado.
- Extrapolar resultados de Playa a otros municipios o al país.
- Usar `menciona_urgencia_viaje` como medida de urgencia (da 0 por construcción).
- Usar `print()` en lugar de `logging` en los scripts.
