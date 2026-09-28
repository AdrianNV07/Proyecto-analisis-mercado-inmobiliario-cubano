#!/usr/bin/env python3
"""
Scraper de Revolico - Pilar 1
Extrae anuncios de venta de viviendas en La Habana.

Salida: data/raw/revolico_ventas.jsonl (una linea JSON por anuncio)
"""

import json
import logging
import random
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

BASE_URL = "https://www.revolico.com"
LISTADO_URL = (
    f"{BASE_URL}/search"
    f"?category=inmobiliaria"
    f"&subcategory=inmobiliaria-casas"
    f"&province=la-habana"
)
MAX_PAGINAS = 3  # Límite para la primera prueba de validación

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-CU,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Selectores CSS deducidos de los fixtures reales
SELECTORES = {
    "titulo": '[id^="BasicInfo__Title-"]',
    "precio": '[id^="BasicInfo__Price-"]',
    "ad_data": '[id^="BasicInfo__AdData-"]',
    "descripcion": '[id^="Description__Wrapper-"]',
    "detalles": '[id^="Detail__Details-"]',
    # El listado es una SPA: las tarjetas no estan en el HTML inicial, por lo que
    # el contenedor GridList__CardsList no sirve. Se recolectan los enlaces
    # <a href="/item/..."> del HTML servido, que si aparecen.
    "tarjetas_listado": 'a[href*="/item/"]',
    "paginacion": '[id^="Paginator__Page-"]',
}

# Urgencia de viaje
URGENCIA_VIAJE_KEYWORDS = [
    "viaje",
    "me voy",
    "emigrar",
    "visa",
    "pasaje",
    "salida del pais",
    "me marcho",
    "urge",
    "salida",
    "mudanza al extranjero",
]

# Problemas estructurales
PROBLEMAS_ESTRUCTURALES_KEYWORDS = [
    "humedad",
    "filtracion",
    "se inunda",
    "problema con el agua",
    "falta de agua",
    "para arreglar",
    "para remodelar",
    "sin terminar",
    "ilegal",
    "no tiene escritura",
    "necesita reparacion",
]

# Vocabulario cerrado para tipo de inmueble
TIPOS_INMUEBLE = {
    "casa": ["casa", "villa", "chalet", "townhouse"],
    "apartamento": ["apartamento", "apto", "flat", "estudio"],
    "habitacion": ["habitacion", "cuarto", "dormitorio", "room"],
    "solar": ["solar", "terreno", "lote"],
    "local": ["local", "comercio", "negocio", "oficina"],
}

# Equivalencia de números escritos a su valor numérico
NUMEROS_ESCRITOS = {
    "un": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
}

# Los 15 municipios de La Habana
MUNICIPIOS_LA_HABANA = [
    "la lisa",
    "diez de octubre",
    "marianao",
    "boyeros",
    "plaza de la revolucion",
    "arroyo naranjo",
    "playa",
    "centro habana",
    "habana vieja",
    "cotorro",
    "habana del este",
    "san miguel del padron",
    "guanabacoa",
    "cerro",
    "regla",
]


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

def configurar_logging() -> logging.Logger:
    """Configura el sistema de logging. Devuelve el logger de errores."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "scraper_revolico.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    error_logger = logging.getLogger("errores")
    error_logger.handlers.clear()
    error_handler = logging.FileHandler(log_dir / "errores.log", encoding="utf-8")
    error_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    error_logger.addHandler(error_handler)
    error_logger.setLevel(logging.ERROR)
    error_logger.propagate = False

    return error_logger


# ═══════════════════════════════════════════════════════════════════════════════
# SESIÓN CON REINTENTOS
# ═══════════════════════════════════════════════════════════════════════════════

def crear_sesion_con_reintentos() -> requests.Session:
    """
    Crea una sesión de requests con reintentos automáticos.

    total=3 intentos, backoff_factor=2 (esperas de 0, 4 y 8 s).
    Reintenta ante 429, 500, 502, 503 y 504.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=4)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# ═══════════════════════════════════════════════════════════════════════════════
# ROBOTS.TXT
# ═══════════════════════════════════════════════════════════════════════════════

def verificar_robots_txt(session: requests.Session) -> bool:
    """
    Verifica robots.txt con RobotFileParser y comprueba si "*" puede
    acceder a LISTADO_URL.

    Retorna False (y el script se detiene) si:
      - robots.txt prohíbe explícitamente el acceso a LISTADO_URL, o
      - no se pudo leer o parsear robots.txt (fallo de red o contenido ilegible).

    Retorna True solo si las reglas permiten el acceso de forma inequívoca.
    """
    robots_url = f"{BASE_URL}/robots.txt"

    try:
        logging.info("Verificando robots.txt...")
        response = session.get(robots_url, timeout=30)
    except requests.RequestException as e:
        logging.critical(f"No se pudo descargar robots.txt: {e}")
        logging.critical(f"URL intentada: {robots_url}")
        logging.critical(
            "No se puede confirmar si el sitio permite el scraping. "
            "Deteniendo el script por seguridad."
        )
        return False

    # Un 403 al pedir robots.txt significa que el sitio no quiere que lo leamos.
    if response.status_code in (401, 403):
        logging.critical(f"robots.txt devolvio {response.status_code} Forbidden")
        logging.critical(f"URL intentada: {robots_url}")
        logging.critical(
            "El sitio bloquea el acceso a robots.txt. No se puede determinar "
            "si el scraping esta permitido. Deteniendo el script."
        )
        return False

    # Un 4xx (salvo 401/403) o 5xx: no se puede confiar en el contenido.
    if response.status_code >= 400:
        logging.critical(f"robots.txt devolvio status {response.status_code}")
        logging.critical(f"URL intentada: {robots_url}")
        logging.critical(
            "No se pudo leer robots.txt de forma fiable. "
            "Deteniendo el script por seguridad."
        )
        return False

    try:
        # Se usa rp.parse() con la respuesta ya descargada y session en vez de
        # rp.read(): este ultimo usa urllib.request, que envia
        # "User-Agent: Python-urllib/x.y" y recibe 403 en muchos sitios.
        # Ademas, un 404 se interpreta como "sin reglas" (permitido).
        rp = RobotFileParser()
        rp.parse(response.text.splitlines())

        # RobotFileParser espera un nombre simple, no la cadena completa del navegador
        user_agent = "*"

        # can_fetch() normaliza la URL por si misma, pero se pasa solo la ruta
        # para que las query strings no interfieran con la comparacion.
        ruta = urlparse(LISTADO_URL).path
        logging.info(f"Verificando acceso a la ruta: {ruta}")
        puede_acceder = rp.can_fetch(user_agent, ruta)

        if puede_acceder:
            logging.info("OK: acceso permitido por robots.txt")
            return True

        logging.error("ACCESO DENEGADO por robots.txt")
        logging.error(f"User-Agent evaluado: {user_agent}")
        logging.error(f"Ruta bloqueada: {ruta}")
        logging.error("El sitio no permite el scraping. Deteniendo el script.")
        return False

    except Exception as e:
        # Ante la duda, no scrapear (regla de AGENTS.md).
        # Un robots.txt inexistente (404) NO llega aqui: RobotFileParser lo
        # interpreta como "sin restricciones" y can_fetch devuelve True.
        # Este bloque solo salta ante fallo de red o contenido ilegible.
        logging.critical(f"No se pudo verificar robots.txt: {e}")
        logging.critical(f"URL intentada: {robots_url}")
        logging.critical(
            "No se puede confirmar si el sitio permite el scraping. "
            "Deteniendo el script por seguridad."
        )
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════════════════════════

def normalizar_texto(texto: str) -> str:
    """
    Normaliza el texto: quita tildes, pasa a minúsculas y colapsa espacios.
    """
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower().strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def extraer_precio(texto: str) -> tuple[Optional[float], Optional[str]]:
    """
    Extrae (precio, moneda) del texto de precio. Ej: "50,000 USD" -> (50000.0, "USD").
    """
    if not texto:
        return None, None

    texto = normalizar_texto(texto)

    moneda = None
    if "usd" in texto or "dolar" in texto or "$" in texto:
        moneda = "USD"
    elif "mlc" in texto:
        moneda = "MLC"
    elif "eur" in texto or "euro" in texto:
        moneda = "EUR"
    elif "cup" in texto or "peso" in texto:
        moneda = "CUP"

    numeros = re.findall(r"[\d,]+(?:\.\d+)?", texto)
    if numeros:
        try:
            return float(numeros[0].replace(",", "")), moneda
        except ValueError:
            pass

    return None, moneda


def extraer_habitaciones(texto: str) -> Optional[int]:
    """
    Extrae el número de habitaciones. Patrones: "3 hab", "2 cuartos", "3/4".
    """
    if not texto:
        return None

    texto = normalizar_texto(texto)

    patrones = [
        r"(\d+)\s*(?:hab|habitacion|habitaciones|cuarto|cuartos|dormitorio|dormitorios)",
        r"(\d+)\s*/\s*(\d+)",
        r"(\d+)\s*hab",
    ]

    for patron in patrones:
        match = re.search(patron, texto)
        if match:
            try:
                return int(match.group(1))
            except (ValueError, IndexError):
                continue

    return None


def extraer_banos(texto: str, auditoria: Optional[dict] = None) -> Optional[int]:
    """
    Extrae el número de baños.

    Tres estrategias, en orden de prioridad:
      1. Cantidad explícita: "2 baños", "un baño", "3 wc", "toilette".
         Incluye el formato "N/M baños", donde se toma la parte alta.
      2. Singular sin cantidad: si el texto menciona "baño"/"wc"/"toilette"
         en singular y no da cantidad, se asume 1. El singular en español
         implica una unidad. ESTA ES UNA INFERENCIA, no una extracción: se
         marca con `auditoria["banos_inferido"] = True`.
      3. Plural sin cantidad ("2 plantas con baños"): devuelve None,
         porque la cantidad es realmente desconocida.

    Si se pasa un dict `auditoria`, se le añade la clave "banos_inferido"
    (True/False) para distinguir valores extraídos de valores inferidos.
    """
    if not texto:
        if auditoria is not None:
            auditoria["banos_inferido"] = False
        return None

    texto = normalizar_texto(texto)

    # --- Estrategia 1: cantidad explícita ---
    # Acepta dígitos y números escritos ("un", "una", "dos", "tres", "cuatro").
    # Se evita la alternancia "ba" suelta para no confundir "20 barrels" o
    # "3 bases" con baños. "una?" cubre tanto "un" como "una".
    patron = r"\b(\d+|una?|dos|tres|cuatro)\s*(?:bano|banos|wc|toilette)s?\b"

    match = re.search(patron, texto)
    if match:
        if auditoria is not None:
            auditoria["banos_inferido"] = False
        cantidad = match.group(1)
        if cantidad.isdigit():
            return int(cantidad)
        return NUMEROS_ESCRITOS.get(cantidad)

    # Formato "N/M baños": se toma la parte alta (el máximo declarado).
    match = re.search(r"\b\d+\s*/\s*(\d+)\s*(?:bano|banos|wc|toilette)s?\b", texto)
    if match:
        if auditoria is not None:
            auditoria["banos_inferido"] = False
        return int(match.group(1))

    # --- Estrategia 2: singular sin cantidad ---
    # "cocina, bano/lavadero" o "3 cuartos, bano, cocina" mencionan un baño
    # único pero sin repetir la cantidad. El singular implica 1.
    if re.search(r"\b(?:bano|wc|toilette)\b", texto):
        if auditoria is not None:
            auditoria["banos_inferido"] = True
        return 1

    # --- Estrategia 3: plural sin cantidad: desconocido ---
    if auditoria is not None:
        auditoria["banos_inferido"] = False
    return None


def inferir_tipo_inmueble(texto: str) -> str:
    """
    Infiere el tipo de inmueble. Vocabulario cerrado.
    """
    if not texto:
        return "otro"

    texto = normalizar_texto(texto)

    for tipo, keywords in TIPOS_INMUEBLE.items():
        for keyword in keywords:
            if keyword in texto:
                return tipo

    return "otro"


def extraer_municipio(texto: str) -> Optional[str]:
    """
    Extrae el municipio de La Habana. Vocabulario cerrado de 15 municipios.
    """
    if not texto:
        return None

    texto = normalizar_texto(texto)

    for municipio in MUNICIPIOS_LA_HABANA:
        if municipio in texto:
            return municipio.title()

    return None


def contar_palabras(texto: str) -> int:
    """Cuenta el número de palabras del texto."""
    if not texto:
        return 0
    return len(texto.split())


def contiene_keywords(texto: str, keywords: list[str]) -> bool:
    """
    Indica si el texto contiene alguna de las palabras clave.
    """
    if not texto:
        return False

    texto_norm = normalizar_texto(texto)
    return any(normalizar_texto(k) in texto_norm for k in keywords)


# ═══════════════════════════════════════════════════════════════════════════════
# SCRAPING
# ═══════════════════════════════════════════════════════════════════════════════

def obtener_urls_anuncios(session: requests.Session, url_listado: str) -> list[str]:
    """
    Obtiene las URLs de los anuncios de una página de listado.
    """
    urls: list[str] = []

    try:
        logging.info(f"Obteniendo listado: {url_listado}")
        response = session.get(url_listado, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        enlaces = soup.select(SELECTORES["tarjetas_listado"])

        for enlace in enlaces:
            href = enlace.get("href", "")
            if not href or "/item/" not in href:
                continue

            if href.startswith("http"):
                url_completa = href
            elif href.startswith("/"):
                url_completa = f"{BASE_URL}{href}"
            else:
                url_completa = f"{BASE_URL}/{href}"

            # Eliminar parámetros de tracking y el sufijo /publish
            url_completa = url_completa.split("?")[0]
            if url_completa.endswith("/publish"):
                continue

            if url_completa not in urls:
                urls.append(url_completa)

        logging.info(f"Encontradas {len(urls)} URLs de anuncios")

    except requests.RequestException as e:
        logging.error(f"Error obteniendo listado {url_listado}: {e}")

    return urls


def extraer_next_data(html: str) -> dict:
    """
    Extrae el objeto JSON de __NEXT_DATA__ del HTML servido.

    Revolico es una SPA de Next.js: los datos del anuncio NO estan en el DOM
    (los id "BasicInfo__Title-*" solo existen dentro del <style> de
    styled-components), por lo que se leen del estado de Apollo.
    """
    patron = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
    match = re.search(patron, html, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        logging.error(f"__NEXT_DATA__ no es JSON valido: {e}")
        return {}


def desreferenciar(apollo_state: dict, valor) -> dict:
    """
    Resuelve una referencia Apollo {"__ref": "Tipo:id"} contra el estado.
    """
    if isinstance(valor, dict) and "__ref" in valor:
        return apollo_state.get(valor["__ref"], {})
    return valor or {}


def extraer_datos_anuncio(session: requests.Session, url: str) -> Optional[dict]:
    """
    Extrae los datos de un anuncio individual desde __NEXT_DATA__.
    Retorna un diccionario, o None si hay error.
    """
    try:
        logging.info(f"Extrayendo anuncio: {url}")
        response = session.get(url, timeout=30)
        response.raise_for_status()

        next_data = extraer_next_data(response.text)
        apollo_state = next_data.get("props", {}).get("pageProps", {}).get(
            "__APOLLO_STATE__", {}
        )

        if not apollo_state:
            logging.warning(f"Anuncio sin __APOLLO_STATE__: {url}")
            return None

        # El anuncio real es la entidad AdType; su id es el ultimo de la URL.
        ad_id = url.rstrip("/").split("-")[-1]
        ad = apollo_state.get(f"AdType:{ad_id}")

        if not ad:
            # Fallback: primera entidad AdType presente en el estado.
            candidatas = [
                v for k, v in apollo_state.items() if k.startswith("AdType:")
            ]
            if not candidatas:
                logging.warning(f"No se encontro entidad AdType: {url}")
                return None
            ad = candidatas[0]

        titulo = (ad.get("title") or "").strip()
        descripcion = (ad.get("description") or "").strip()
        precio = ad.get("price")
        moneda = (ad.get("currency") or "").strip() or None

        # Municipio, provincia y subcategoria llegan como referencias Apollo.
        municipio_bruto = (
            desreferenciar(apollo_state, ad.get("municipality")).get("name") or ""
        ).strip()
        provincia_bruto = (
            desreferenciar(apollo_state, ad.get("province")).get("name") or ""
        ).strip()
        subcat_bruto = (
            desreferenciar(apollo_state, ad.get("subcategory")).get("title") or ""
        ).strip()

        # El municipio se normaliza contra los 15 municipios de La Habana.
        municipio = extraer_municipio(f"{municipio_bruto} {provincia_bruto}")

        texto_completo = f"{titulo} {subcat_bruto} {descripcion}"

        # El precio puede venir como numero o como texto ("A consultar").
        if isinstance(precio, str):
            precio_num, moneda_texto = extraer_precio(precio)
            if moneda_texto and not moneda:
                moneda = moneda_texto
            precio = precio_num

        # Auditoria: distingue el banos extraido del banos inferido por singular.
        auditoria: dict = {}
        banos = extraer_banos(texto_completo, auditoria)

        return {
            "titulo": titulo,
            "precio": float(precio) if isinstance(precio, (int, float)) else None,
            "moneda": moneda,
            "descripcion": descripcion,
            "municipio": municipio,
            "municipio_bruto": municipio_bruto or None,
            "provincia": provincia_bruto or None,
            "subcategoria": subcat_bruto or None,
            "habitaciones": extraer_habitaciones(texto_completo),
            "banos": banos,
            "banos_inferido": auditoria.get("banos_inferido", False),
            "tipo_inmueble": inferir_tipo_inmueble(texto_completo),
            "menciona_urgencia_viaje": contiene_keywords(
                texto_completo, URGENCIA_VIAJE_KEYWORDS
            ),
            "menciona_problemas_estructurales": contiene_keywords(
                texto_completo, PROBLEMAS_ESTRUCTURALES_KEYWORDS
            ),
            "cantidad_palabras": contar_palabras(descripcion),
            "url": url,
        }

    except requests.RequestException as e:
        logging.error(f"Error HTTP extrayendo {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado extrayendo {url}: {e}")
        return None


def cargar_urls_existentes(archivo: Path) -> set[str]:
    """
    Lee el JSONL y devuelve el conjunto de URLs ya scrapadas.

    Permite reanudar una ejecución interrumpida sin volver a descargar ni
    volver a guardar los anuncios que ya estaban.
    """
    urls: set[str] = set()

    if not archivo.exists():
        return urls

    with open(archivo, "r", encoding="utf-8") as f:
        for num_linea, linea in enumerate(f, start=1):
            linea = linea.strip()
            if not linea:
                continue
            try:
                registro = json.loads(linea)
            except json.JSONDecodeError as e:
                logging.warning(
                    f"Línea {num_linea} corrupta en {archivo}: {e}. Se ignora."
                )
                continue

            url = registro.get("url")
            if url:
                urls.add(url)

    logging.info(f"URLs ya presentes en {archivo}: {len(urls)}")
    return urls


def guardar_anuncio(anuncio: dict, archivo: Path) -> None:
    """
    Añade un anuncio como línea JSON al archivo JSONL.
    """
    with open(archivo, "a", encoding="utf-8") as f:
        json.dump(anuncio, f, ensure_ascii=False)
        f.write("\n")


def eliminar_duplicados(archivo: Path) -> int:
    """
    Reescribe el JSONL conservando solo la primera aparición de cada URL.

    Se escribe primero en un archivo temporal y luego se sustituye el
    original, para no dejar el JSONL corrupto si algo falla a mitad.

    Retorna el número de duplicados eliminados.
    """
    if not archivo.exists():
        return 0

    vistas: set[str] = set()
    lineas_finales: list[str] = []
    eliminados = 0
    corruptas = 0

    with open(archivo, "r", encoding="utf-8") as f:
        for linea in f:
            if not linea.strip():
                continue

            try:
                registro = json.loads(linea)
            except json.JSONDecodeError:
                corruptas += 1
                continue

            url = registro.get("url")
            clave = url or json.dumps(registro, sort_keys=True, ensure_ascii=False)

            if clave in vistas:
                eliminados += 1
                continue

            vistas.add(clave)
            lineas_finales.append(json.dumps(registro, ensure_ascii=False))

    if eliminados == 0 and corruptas == 0:
        logging.info("Limpieza final: no había duplicados que eliminar.")
        return 0

    archivo_temporal = archivo.with_suffix(archivo.suffix + ".tmp")
    with open(archivo_temporal, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas_finales))
        if lineas_finales:
            f.write("\n")

    archivo_temporal.replace(archivo)

    logging.info(
        f"Limpieza final: {eliminados} duplicado(s) eliminado(s), "
        f"{len(lineas_finales)} registro(s) conservados."
    )
    if corruptas:
        logging.warning(f"Limpieza final: {corruptas} línea(s) corrupta(s) descartada(s).")

    return eliminados


# ═══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Función principal del scraper."""
    error_logger = configurar_logging()

    logging.info("=" * 60)
    logging.info("Iniciando scraper de Revolico")
    logging.info(f"URL base: {LISTADO_URL}")
    logging.info(f"Máximo de páginas: {MAX_PAGINAS}")
    logging.info("=" * 60)

    data_dir = Path("data/raw")
    data_dir.mkdir(parents=True, exist_ok=True)
    archivo_salida = data_dir / "revolico_ventas.jsonl"

    total_extraidos = 0
    total_fallidos = 0
    total_duplicados = 0

    # URLs ya presentes: se cargan una vez y se van actualizando en memoria,
    # de modo que la comprobación es O(1) y no relee el archivo por anuncio.
    urls_ya_procesadas = cargar_urls_existentes(archivo_salida)

    session = crear_sesion_con_reintentos()

    if not verificar_robots_txt(session):
        logging.critical("Script detenido: robots.txt no permite el scraping.")
        logging.critical(
            "Revisa logs/scraper_revolico.log para ver el detalle del bloqueo."
        )
        sys.exit(1)

    for pagina in range(1, MAX_PAGINAS + 1):
        logging.info(f"--- Procesando página {pagina}/{MAX_PAGINAS} ---")

        if pagina == 1:
            # La primera pagina no lleva parametros de paginacion.
            url_pagina = LISTADO_URL
        else:
            # El sitio usa "cu" (currency) + "page"; el orden de los parametros
            # que genera el propio sitio es: ...&cu=0&page=N
            url_pagina = f"{LISTADO_URL}&cu=0&page={pagina}"

        urls_anuncios = obtener_urls_anuncios(session, url_pagina)

        # Una página vacía no detiene el script: se avisa y se sigue.
        if not urls_anuncios:
            logging.warning(
                f"Página {pagina}: no se encontraron URLs. "
                "Continuando con la siguiente página."
            )
            continue

        for url in urls_anuncios:
            # Control de duplicados: si la URL ya está en el JSONL (o se
            # acaba de guardar en esta misma ejecución), se salta sin
            # pedirla al servidor ni escribir nada.
            if url in urls_ya_procesadas:
                total_duplicados += 1
                logging.info(f"DUPLICADO omitido: {url}")
                continue

            delay = random.uniform(3, 5)
            logging.info(f"Esperando {delay:.1f} segundos...")
            time.sleep(delay)

            anuncio = extraer_datos_anuncio(session, url)

            if anuncio:
                guardar_anuncio(anuncio, archivo_salida)
                urls_ya_procesadas.add(url)
                total_extraidos += 1
                titulo = (anuncio["titulo"] or "")[:50]
                logging.info(f"OK: anuncio guardado -> {titulo}")
            else:
                total_fallidos += 1
                error_logger.error(f"Fallo en URL: {url}")
                logging.error(f"Fallo extrayendo: {url}")

    # Limpieza final: elimina cualquier duplicado que se haya colado.
    duplicados_eliminados = eliminar_duplicados(archivo_salida)

    logging.info("=" * 60)
    logging.info("RESUMEN FINAL")
    logging.info("=" * 60)
    logging.info(f"Anuncios extraídos correctamente: {total_extraidos}")
    logging.info(f"Anuncios fallidos: {total_fallidos}")
    logging.info(f"Duplicados omitidos: {total_duplicados}")
    logging.info(f"Duplicados eliminados en limpieza final: {duplicados_eliminados}")
    logging.info(f"Total procesados: {total_extraidos + total_fallidos + total_duplicados}")
    logging.info(f"Archivo de salida: {archivo_salida}")
    logging.info("=" * 60)

    print()
    print("=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    print(f"Anuncios extraídos correctamente: {total_extraidos}")
    print(f"Anuncios fallidos: {total_fallidos}")
    print(f"Duplicados omitidos: {total_duplicados}")
    print(f"Duplicados eliminados en limpieza final: {duplicados_eliminados}")
    print(f"Total procesados: {total_extraidos + total_fallidos + total_duplicados}")
    print(f"Archivo de salida: {archivo_salida}")
    print("=" * 60)


if __name__ == "__main__":
    main()
