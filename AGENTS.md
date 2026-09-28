# AGENTS.md — Mercado Inmobiliario en Cuba y Crisis Migratoria

## 🎯 Objetivo del proyecto

Analizar la relación entre la **crisis migratoria** y el mercado inmobiliario cubano,
midiendo su impacto en tres dimensiones:

| Dimensión | Métricas clave |
|---|---|
| **Precios** | Precio por m², distribución por tipo de inmueble, tendencia por municipio |
| **Urgencia de venta** | `%` de anuncios con señales de urgencia, tiempo de publicación vs. precio |
| **Distribución geográfica** | Densidad de anuncios, gradiente emigración → municipio (solo La Habana) |

El proyecto se sostiene sobre **tres pilares de datos** que deben integrarse y cruzarse
al final para validar o refutar hipótesis sobre el comportamiento del mercado.

> **Alcance geográfico: exclusivamente La Habana.** Todos los análisis son
> **intra-urbanos**. El análisis de la capital se hace comparando sus municipios entre
> sí; nunca se comparan provincias ni se extrapolan resultados al resto del país.
> Los anuncios de fuera de La Habana se registran y se descartan, no se analizan.

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
│   ├── raw/                   # Datos sin procesar (JSONL, CSV) — solo lectura
│   │   ├── revolico_ventas.jsonl
│   │   ├──Sitios_especializados.csv
│   │   └── entrevistas_raw.txt
│   ├── interim/               # Datos limpios / normalizados
│   └── processed/             # Datasets analíticos finales
├── logs/                      # Logs de ejecución (scraping, errores)
├── notebooks/                 # Análisis exploratorio
├── scripts/
│   ├── 01_scrap_revolico.py
│   ├── 02_plantilla_csv.py
│   ├── 03_procesar_entrevistas.py
│   ├── 04_unificar_datasets.py
│   └── 05_analisis_final.py
└── src/
    ├── config.py
    ├── cleaning.py
    ├── schema.py
    └── utils.py
```

**Regla:** `data/raw/` es inmutable. Toda transformación escribe en `interim/` o `processed/`.

---

## 🐍 Stack tecnológico

- **Python 3.10+** (obligatorio; usar sintaxis `X | None`, `match`, `list[str]`)
- **requests** — cliente HTTP
- **BeautifulSoup4 (bs4)** — parsing de HTML
- **pandas** — manipulación tabular
- **jupyter** — notebooks de análisis
- Entorno virtual `.venv` obligatorio. Nunca instalar paquetes globalmente.

---

## 📌 Pilar 1 — Scraping de Revolico (venta de viviendas)

### Script
`scripts/01_scrap_revolico.py`

### Requisitos técnicos
- Usar **`requests.Session`** para reutilizar conexiones.
- **Cabeceras** legítimas en cada petición:
  ```python
  HEADERS = {
      "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
      "Accept-Language": "es-CU,es;q=0.9",
  }
  ```

### Esquema de salida
**Archivo:** `data/raw/revolico_ventas.jsonl` (un objeto JSON por línea, UTF-8)

| Campo | Tipo | Notas |
|---|---|---|
| `precio` | float \| null | Valor numérico, sin símbolo de moneda |
| `moneda` | str | `CUP`, `USD`, `EUR` — normalizado |
| `tamaño` | float \| null | En **m²**, siempre |
| `habitaciones` | int \| null | Número entero |
| `tipo_inmueble` | str | Vocabulario cerrado (ver abajo) |
| `dirección` | str | Texto original + municipio extraído |
| `fecha_publicación` | str | ISO `YYYY-MM-DD` |
| `url` | str | URL absoluta del anuncio |
| `casa_amueblada` | bool | `True` / `False` |
| `menciona_urgencia_viaje` | bool | `True` / `False` |

### Campo derivado obligatorio: `menciona_urgencia_viaje`
Detección por **palabras clave** en la descripción del anuncio (case-insensitive):

```python
URGENCIA_KEYWORDS = ["viaje", "me voy", "emigrar", "emigrando", "migrar", "salir del país",
                     "partiendo", "me mudo", "oportunidad única", "última oportunidad"]
```

Reglas:
- Buscar sobre el texto completo (título + descripción), **normalizado**: minúsculas, sin
  acentos, sin puntuación.
- Usar **coincidencia por palabra completa o frase** (`\bviaje\b`), no subcadena,
  para evitar falsos positivos (p. ej. `viaj` no debe disparar la regla).
- `viaje` no debe activarse por URLs, correos ni nombres propios: excluir del texto
  normalizado todo lo que parezca URL (`http`, `www`, `.com`) y emails.
- El valor es siempre `bool` real de Python al serializar (`true`/`false` en JSONL),
  nunca `"sí"`/`"no"`.

### Vocabulario cerrado para `tipo_inmueble`
```
casa | apartamento | townhouse | duplex | solar
```
Normalizar sin acentos, minúsculas, snake_case. Cualquier valor fuera del vocabulario
→ `"otro"`.

### Paginación
- Recorrer todas las páginas disponibles hasta agotar el listado.
- Registrar en el log el número de página y la cantidad de anuncios extraídos.
- Si una página devuelve 0 resultados, **terminar** el bucle y loguear `INFO` (fin
  natural del listado), no es un error.

---

## 📝 Pilar 2 — Sitios especializados / grupos (registro manual en CSV)

### Script
`scripts/02_plantilla_csv.py`

Genera una **plantilla CSV vacía con encabezados** para que el usuario registre
manualmente anuncios provenientes de portales inmobiliarios formales (Vivopedia, Infocasa,
Cubanet, etc.) o de grupos de redes sociales (Facebook, WhatsApp, Telegram).

**Archivo:** `data/raw/sitios_especializados.csv`

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

## 🎤 Pilar 3 — Entrevistas callejeras (texto → CSV)

### Script
`scripts/03_procesar_entrevistas.py`

Procesa el archivo de respuestas textuales de entrevistas y lo convierte a un CSV
estructurado y listo para análisis.

**Entrada:** `data/raw/entrevistas_raw.txt`
**Salida:** `data/interim/entrevistas.csv`

### Columnas (en este orden exacto)
```
nombre_persona, carné_identidad, precio, tamaño, habitaciones, estado_casa,
tipo_inmueble, fuente, fecha_publicación, moneda, dirección, baños,
espacios_exteriores, casa_amueblada, urgencia_viaje
```

| Columna | Tipo | Notas |
|---|---|---|
| `nombre_persona` | str | — |
| `carné_identidad` | str | **Cifrado / anonimizado** (ver abajo) |
| `precio` | float | — |
| `tamaño` | float | m² |
| `habitaciones` | int | — |
| `estado_casa` | str | Vocabulario cerrado |
| `tipo_inmueble` | str | Vocabulario cerrado |
| `fuente` | str | `entrevista_urbana` (o submuestra: `La Habana Vieja`, `Playa`…) |
| `fecha_publicación` | str | ISO `YYYY-MM-DD` (fecha de la entrevista) |
| `moneda` | str | `CUP` / `USD` / `EUR` |
| `dirección` | str | — |
| `baños` | int \| null | — |
| `espacios_exteriores` | int \| null | — |
| `casa_amueblada` | bool | — |
| `urgencia_viaje` | bool | Derivado del texto, mismas keywords que Pilar 1 |

### 🔒 Privacidad — regla no negociable
- **`carné_identidad` nunca se almacena en texto claro.** Hashing con SHA-256 + salt
  fijo del proyecto, tomando solo los primeros 12 caracteres del digest.
- No incluir en el CSV ningún otro dato personal (teléfono, dirección exacta del
  entrevistado, correo).
- La dirección del inmueble sí se conserva, pero normalizada a **municipio** cuando
  sea posible.

### Parsing del texto
- Segmentar el archivo por entrevista usando un delimitador explícito
  (p. ej. líneas `---` o `### Entrevista N`).
- Extraer los campos con regex tolerantes a variantes de escritura
  ("3 habitaciones", "3 hab", "3 rooms", "tres dormitorios", "3 dormitorios").
- Si un campo no aparece en el texto → `None`/celda vacía. **Nunca inventar valores ni
  usar medias o imputaciones** en esta etapa.
- Detectar la moneda por contexto textual ("dólares", "USD", "euros", "CUP", "pesos")
  y no solo por el símbolo.

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
  `logs/01_scrap_revolico_YYYY-MM-DD_HHMMSS.log`.
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

## 📊 Análisis final — integración y cruces

**Script:** `scripts/05_analisis_final.py`
**Salida:** `data/processed/`

### Preguntas centrales a responder

1. **¿Coinciden geográficamente la urgencia y los motivos de venta?**
   ¿Los municipios con más anuncios de "urgencia por viaje" en Revolico coinciden con
   los motivos de venta declarados en las entrevistas callejeras?
   → Cruzar `municipio` × `urgencia_viaje` entre datasets, comparar distribuciones
   (Chi-cuadrado o prueba de Kolmogorov-Smirnov según el tipo de variable).

2. **¿El precio se ve afectado por la urgencia?**
   Comparar `precio / tamaño` (USD/m²) entre anuncios con `urgencia_viaje = True` vs
   `False`. Usar **precio por m² normalizado a USD** para no confundir monedas
   (aplicar tipo de cambio oficial o de mercado acordado en `config.yaml`).

3. **Gradiente interno de La Habana**
   La crisis migratoria se manifiesta de forma desigual dentro de la capital. ¿La
   proporción de anuncios urgentes y el precio por m² varían de forma consistente entre
   los municipios habaneros (comparar por ejemplo Habana del Este / Guanabacoa /
   Regla frente a Playa / Habana del Oeste / La Habana Vieja)?
   → Sustituye a la comparación provincial: el análisis es **intra-urbano**, nunca
   entre provincias.

4. **¿Difieren los canales?**
   ¿El perfil del anuncio de portal formal (Pilar 2) difiere del anuncio informal
   (Pilar 1) en precio por m², urgencia y tipo de inmueble?

5. **Motivos de venta declarados en entrevistas**
   Categorizar el texto de entrevistas en motivos: `emigración`, `necesidad
   económica`, `herencia`, `cambio de vivienda`, `venta especulativa`. Analizar su
   frecuencia por municipio y cruzarla con `urgencia_viaje`.

### Reglas de análisis
- Documentar **cada** figura y tabla generada en `notebooks/`.
- Toda estadística debe ir acompañada de su **tamaño de muestra (n)**.
- No presentar correlaciones como causalidad. Reportar siempre el tamaño del efecto.
- Manejar las monedas de forma explícita: **nunca mezclar CUP y USD sin convertir** y
  documentar la tasa usada.
- Asumir que las entrevistas tienen **sesgo de muestreo** (muestra no probabilística).
  Reportarlo explícitamente en las conclusiones.

---

## ✅ Convenciones generales

- Código en español para los **nombres de negocio**, inglés para las librerías.
- Docstrings y comentarios en español.
- Tipado con `type hints` en todas las funciones públicas.
- Funciones pequeñas, con una responsabilidad cada una.
- Todo script debe ser ejecutable de forma independiente:
  `python scripts/01_scrap_revolico.py`.
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
- Usar `print()` en lugar de `logging` en los scripts.
