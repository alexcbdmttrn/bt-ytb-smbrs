import asyncio
from datetime import date, datetime
from zoneinfo import ZoneInfo
from PIL import ImageEnhance
import json
import json5
import os
import random
import re
import sys
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    ImageClip,
    concatenate_audioclips,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
import requests
import edge_tts
import urllib3

# Silenciar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================================================================
# CONFIGURACIÓN
# ================================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
YOUTUBE_USER_TOKEN = (
    json.loads(os.getenv("YOUTUBE_USER_TOKEN"))
    if os.getenv("YOUTUBE_USER_TOKEN")
    else {}
)

FACEBOOK_LINK = "https://www.facebook.com/profile.php?id=61593237382982"
CANAL_LINK = "https://www.youtube.com/@sombrasdemedianocheoficial"

MUSICA_ESTADO_FILE = "estado_musica.json"
TITULOS_LARGOS_FILE = "titulos_largos_publicados.json"
TEMAS_SHORTS_FILE = "temas_shorts.json"

DURACION_MINIMA_SEGUNDOS = 480  # 8 minutos
MAX_INTENTOS_EXPANSION = 2

ACTIVAR_DISCLOSURE_IA = True
DISCLOSURE_TEXT = "\n\n🤖 Contenido narrado con inteligencia artificial. Relato basado en testimonios reales de internet."

# ================================================================
# 🎯 TEMAS VIRALES 2024 (ADAPTADOS PARA VIDEOS LARGOS)
# ================================================================
TEMAS_VIRALES_LARGOS = [
    {
        "tema": "backrooms_exploracion",
        "titulo_base": "Exploré los Backrooms de {lugar} durante {horas} horas",
        "keywords": ["backrooms", "liminal spaces", "dimensiones paralelas", "atrapado", "infinito"],
        "contextos": ["hotel abandonado", "centro comercial vacío", "túneles subterráneos", "edificio abandonado"],
        "duracion_objetivo": 600,  # 10 minutos
        "busquedas": 450000
    },
    {
        "tema": "skinwalker_persiguiendo",
        "titulo_base": "Un Skinwalker me persiguió {dias} días en {lugar}",
        "keywords": ["skinwalker", "wendigo", "criatura", "persecución", "bosque maldito"],
        "contextos": ["carretera solitaria", "bosque profundo", "montaña aislada", "desierto nocturno"],
        "duracion_objetivo": 540,  # 9 minutos
        "busquedas": 380000
    },
    {
        "tema": "ritual_completo",
        "titulo_base": "Hice el ritual completo en {lugar} y esto pasó",
        "keywords": ["ritual", "invocación", "ceremonia", "maldición", "ocultismo"],
        "contextos": ["cementerio antiguo", "casa abandonada", "bosque sagrado", "cueva"],
        "duracion_objetivo": 660,  # 11 minutos
        "busquedas": 520000
    },
    {
        "tema": "ia_prediccion_muerte",
        "titulo_base": "Una IA predijo mi muerte en {lugar} - {dias} días después",
        "keywords": ["IA", "inteligencia artificial", "predicción", "muerte", "algoritmo maldito"],
        "contextos": ["laboratorio", "cuarto de servidores", "oficina tech", "universidad"],
        "duracion_objetivo": 600,
        "busquedas": 890000
    },
    {
        "tema": "numero_maldito_llamadas",
        "titulo_base": "Llamé al número maldito {numero} veces en {lugar}",
        "keywords": ["teléfono maldito", "llamadas", "número prohibido", "voz del más allá"],
        "contextos": ["cabina telefónica", "casa embrujada", "oficina nocturna", "sótano"],
        "duracion_objetivo": 540,
        "busquedas": 670000
    },
    {
        "tema": "deep_web_archivos",
        "titulo_base": "Descargué archivos prohibidos de la Deep Web en {lugar}",
        "keywords": ["deep web", "red oscura", "archivos prohibidos", "contenido clasificado"],
        "contextos": ["cuarto oscuro", "bunker", "oficina abandonada", "sótano tech"],
        "duracion_objetivo": 600,
        "busquedas": 540000
    },
    {
        "tema": "creepypasta_real",
        "titulo_base": "La creepypasta de {lugar} es REAL - Testimonio",
        "keywords": ["creepypasta", "Slenderman", "Jeff the Killer", "leyenda urbana", "internet"],
        "contextos": ["bosque nocturno", "parque abandonado", "calle solitaria", "casa embrujada"],
        "duracion_objetivo": 660,
        "busquedas": 230000
    },
    {
        "tema": "objeto_maldito_casa",
        "titulo_base": "Compré un objeto maldito en {lugar} - {dias} noches de terror",
        "keywords": ["muñeca maldita", "espejo embrujado", "pintura maldita", "reliquia"],
        "contextos": ["tienda de antigüedades", "mercado de pulgas", "subasta", "casa heredada"],
        "duracion_objetivo": 600,
        "busquedas": 340000
    },
]

# ================================================================
# 🔥 FÓRMULAS DE TÍTULOS VIRALES PARA VIDEOS LARGOS
# ================================================================
FORMULAS_TITULOS_LARGOS = {
    "experiencia_extrema": [
        "Sobreviví {numero} noches en {lugar} - Testimonio REAL",
        "Estuve {horas} horas atrapado en {lugar} - Esto vi",
        "{dias} días explorando {lugar} - Lo que descubrí",
    ],
    "numero_especifico": [
        "{numero} veces que vi al mismo fantasma en {lugar}",
        "{hora} exacto: Lo que pasó en {lugar}",
        "Día {numero} en {lugar}: Algo me seguía",
    ],
    "advertencia_real": [
        "⚠️ NO vayas a {lugar} si ves ESTO - Testigo lo confirma",
        " ALERTA: Algo acecha en {lugar} - Múltiples avistamientos",
        "PELIGRO REAL en {lugar} - Lo que las autoridades ocultan",
    ],
    "secreto_revelado": [
        "El SECRETO que {lugar} esconde (FILTRADO)",
        "Lo que NADIE te cuenta sobre {lugar} - Investigación",
        "Descubrí algo PROHIBIDO en {lugar} - Evidencia",
    ],
    "pregunta_misterio": [
        "¿Qué hay realmente en {lugar}? - Investigación completa",
        "¿Por qué NADIE entra a {lugar} después de {hora}?",
        "¿Sobrevivirías {horas} horas en {lugar}? - Experimento",
    ],
}

# ================================================================
# 🧠 CONFIGURACIÓN DE PUBLICACIÓN HUMANA (VIDEOS LARGOS)
# ================================================================
MAX_VIDEOS_DIA = 1
PROBABILIDAD_DESCANSO = 0.20
PROBABILIDAD_CAPRICHO = 0.15
INTERVALO_MIN_HORAS = 24
INTERVALO_MAX_HORAS = 72
RETRASO_MAX_MINUTOS = 45

UMBRAL_DEMANDA_VIEWS = 10000

# ================================================================
# 🎬 DECISIONES DE PUBLICACIÓN
# ================================================================
def deberia_publicar_ahora(estado):
    """Decide si publicar hoy con comportamiento humano."""
    hoy = datetime.now(ZoneInfo("America/Mexico_City")).date()
    fecha_hoy = hoy.isoformat()

    if estado.get("fecha") != fecha_hoy:
        estado["fecha"] = fecha_hoy
        estado["publicaciones_hoy"] = 0
        if random.random() < PROBABILIDAD_DESCANSO:
            estado["dia_descanso"] = fecha_hoy
            print("🛌 Día de descanso activado. No se publicará nada hoy.")
        else:
            estado["dia_descanso"] = None
        print(f" Nuevo día. Contador reiniciado.")

    if estado.get("dia_descanso") == fecha_hoy:
        return False

    publicadas_hoy = estado.get("publicaciones_hoy", 0)
    if publicadas_hoy >= MAX_VIDEOS_DIA:
        print(f"✅ Límite de {MAX_VIDEOS_DIA} video diario alcanzado.")
        return False

    ultima_hora = estado.get("ultima_publicacion")
    if ultima_hora:
        ultima_hora = datetime.fromisoformat(ultima_hora)
        hora_actual = datetime.now(ZoneInfo("America/Mexico_City"))
        diff_horas = (hora_actual - ultima_hora).total_seconds() / 3600
        intervalo_requerido = random.uniform(INTERVALO_MIN_HORAS, INTERVALO_MAX_HORAS)
        if diff_horas < intervalo_requerido:
            print(f"⏳ Esperando {intervalo_requerido:.1f}h desde la última publicación.")
            print(f"   Han pasado {diff_horas:.1f}h. Aún no es momento.")
            return False
        else:
            print(f"✅ Han pasado {diff_horas:.1f}h. Intervalo superado.")

    if random.random() < PROBABILIDAD_CAPRICHO:
        print("🎲 Capricho aleatorio: no publicar esta vez.")
        return False

    print("✅ Decisión: Publicar video largo.")

    retraso_segundos = random.randint(0, RETRASO_MAX_MINUTOS * 60)
    if retraso_segundos > 0:
        print(f"⏳ Esperando {retraso_segundos//60} min {retraso_segundos%60} seg antes de comenzar...")
        time.sleep(retraso_segundos)

    return True

# ================================================================
# VALIDAR PEXELS API KEY
# ================================================================
def validar_pexels_api_key():
    if not PEXELS_API_KEY:
        print("⚠️ PEXELS_API_KEY no configurada.")
        return False
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        r = requests.get("https://api.pexels.com/v1/search?query=test&per_page=1", headers=headers, timeout=10)
        if r.status_code == 200:
            print("✅ API Key de Pexels válida.")
            return True
        else:
            print(f"⚠️ API Key de Pexels inválida (código {r.status_code}).")
            return False
    except Exception as e:
        print(f"️ Error probando API Key: {e}")
        return False

PEXELS_VALIDA = validar_pexels_api_key()

# ================================================================
#  GENERAR TÍTULO ULTRA-VIRAL PARA VIDEOS LARGOS
# ================================================================
def generar_titulo_viral_largo(keywords, lugar, tema_viral):
    """
    Genera títulos virales adaptados para videos largos (8-12 min)
    """
    categorias = list(FORMULAS_TITULOS_LARGOS.keys())
    categoria = random.choice(categorias)
    
    formulas = FORMULAS_TITULOS_LARGOS[categoria]
    formula = random.choice(formulas)
    
    horas = ["3:33 AM", "2:00 AM", "4:44 AM", "medianoche", "3:00 AM", "12 horas", "24 horas"]
    numeros = ["3", "7", "13", "47", "9", "5", "10"]
    dias = ["3", "7", "5", "10", "13"]
    
    titulo = formula.replace("{hora}", random.choice(horas))
    titulo = titulo.replace("{lugar}", lugar)
    titulo = titulo.replace("{numero}", random.choice(numeros))
    titulo = titulo.replace("{dias}", random.choice(dias))
    
    titulo = titulo[0].upper() + titulo[1:]
    
    if len(titulo) > 95:
        titulo = titulo[:92] + "..."
    
    return titulo

# ================================================================
# VERIFICAR DEMANDA EN YOUTUBE
# ================================================================
def verificar_demanda_youtube(tema, umbral_views=UMBRAL_DEMANDA_VIEWS):
    try:
        creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
        youtube = build("youtube", "v3", credentials=creds)
        request = youtube.search().list(
            part="snippet",
            q=tema,
            maxResults=10,
            type="video"
        )
        response = request.execute()
        items = response.get("items", [])
        if not items:
            print(f"⚠️ No se encontraron videos para el tema '{tema}'.")
            return False

        video_ids = [item["id"]["videoId"] for item in items if item["id"]["kind"] == "youtube#video"]
        if not video_ids:
            return False

        stats_request = youtube.videos().list(
            part="statistics",
            id=",".join(video_ids[:5])
        )
        stats_response = stats_request.execute()
        stats_items = stats_response.get("items", [])
        if not stats_items:
            return False

        total_views = 0
        for stat in stats_items:
            views = int(stat["statistics"].get("viewCount", 0))
            total_views += views

        avg_views = total_views / len(stats_items)
        print(f"📊 Demanda para '{tema}': {len(stats_items)} videos, promedio de vistas: {avg_views:,.0f}")
        if avg_views >= umbral_views:
            print("✅ Demanda suficiente.")
            return True
        else:
            print(f"⛔ Demanda baja (promedio < {umbral_views:,}). Cancelando publicación.")
            return False
    except Exception as e:
        print(f"⚠️ Error verificando demanda: {e}")
        return True

# ================================================================
# ÉPOCA DEL SUCESO
# ================================================================
ANIO_SUCESO = None
EPOCA_MOD = "present day contemporary era (2020s), modern vehicles, modern architecture, modern clothing, smartphones era"

def construir_modificadores_epoca(anio):
    if anio is None or anio >= 2015:
        return "present day contemporary era (2020s), modern vehicles, modern architecture, modern clothing, LED lighting, smartphones era"
    elif anio >= 2000:
        return f"early 2000s era (year {anio}): 2000s cars, CRT televisions, old flip cellphones, 2000s fashion and architecture, no smartphones"
    elif anio >= 1990:
        return f"1990s era (year {anio}): 90s cars, cassette players, CRT TVs, analog phones, 90s fashion, older architecture, no smartphones, no modern tech"
    elif anio >= 1980:
        return f"1980s era (year {anio}): 80s cars, analog rotary phones, vintage clothing, older buildings, no modern technology"
    else:
        return f"past era (year {anio}): old classic cars, analog technology, period clothing, aged architecture, no modern devices"

def actualizar_epoca(anio):
    global ANIO_SUCESO, EPOCA_MOD
    try:
        ANIO_SUCESO = int(anio)
    except Exception:
        ANIO_SUCESO = None
    EPOCA_MOD = construir_modificadores_epoca(ANIO_SUCESO)
    print(f"🗓️ Época del suceso: {ANIO_SUCESO if ANIO_SUCESO else 'actualidad'}")

# ================================================================
# VOCES NEURALES
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural", "velocidad": "+12%", "tono": "-2Hz"},
    {"voz": "es-MX-DaliaNeural", "velocidad": "+12%", "tono": "+0Hz"},
    {"voz": "es-ES-AlvaroNeural", "velocidad": "+12%", "tono": "-3Hz"},
    {"voz": "es-ES-ElviraNeural", "velocidad": "+12%", "tono": "+1Hz"},
    {"voz": "es-CO-GonzaloNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-CO-SalomeNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-AR-ElenaNeural", "velocidad": "+12%", "tono": "+2Hz"},
    {"voz": "es-AR-DiegoNeural", "velocidad": "+12%", "tono": "-2Hz"},
    {"voz": "es-US-AlonsoNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-US-PalomaNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-PE-CamilaNeural", "velocidad": "+12%", "tono": "+0Hz"},
    {"voz": "es-PE-AlexNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+12%", "tono": "-2Hz"},
    {"voz": "es-CL-CatalinaNeural", "velocidad": "+12%", "tono": "+1Hz"},
]
CONFIG_VOZ_ACTUAL = random.choice(VOCES_DISPONIBLES)

# ================================================================
# PALETAS Y ESTILOS
# ================================================================
PALETAS_COLOR = [
    "Cold cyan blue LED fog, navy blue modern shadows, crisp white moonlight",
    "Emerald green twilight, modern city haze, muted sage ambient lighting",
    "Deep violet haze, electric purple ambient light, dark magenta shadows",
    "Slate gray tones, freezing ice blue highlight, dim overcast ambient",
    "Dark teal and deep blue, oceanic midnight, cold misty atmosphere",
    "Stark black and white high contrast, silver moonlight, pitch shadows",
    "Desaturated cold film look, moody cinematic lighting, hyperrealistic",
    "Warm amber and dark mahogany, golden lighting, deep brown shadows",
    "Fiery sunset orange, deep purple shadows, red highlights",
    "Deep crimson red, pitch black shadow, intense orange emergency lights",
    "Muted sepia-toned film look, faded analog colors, nostalgic atmosphere",
    "Warm tungsten indoor glow, soft yellow lamplight, aged shadows",
]
PALETA_COLOR_ACTUAL = random.choice(PALETAS_COLOR)

ESTILOS_VISUALES = [
    "Cinematic photograph, dramatic lighting, sharp focus, film still",
    "Thriller photography, soft ambient diffusion, high contrast",
    "Documentary realistic photo, natural skin texture, authentic",
    "8k resolution cinematic frame, ultra clear details",
    "Noir style, high contrast, moody urban atmosphere",
    "Analog film photograph, grain of the period, authentic era look",
]
ESTILO_VISUAL_ACTUAL = random.choice(ESTILOS_VISUALES)

# ================================================================
# ESTADOS DE MÉXICO
# ================================================================
ESTADOS_MEXICO = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas",
    "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit",
    "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
    "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"
]

# ================================================================
# GENERADOR DE PERSONAJES
# ================================================================
def generar_perfil_personaje():
    edades = ["21-year-old", "28-year-old", "35-year-old", "42-year-old", "50-year-old", "60-year-old"]
    generos = ["man", "woman"]
    vestimentas = [
        "wearing a denim jacket and t-shirt",
        "wearing a dark green coat and wool scarf",
        "wearing a simple white shirt and leather belt",
        "wearing a blue mechanic uniform",
        "wearing a dark sweater and trousers",
        "wearing a red flannel shirt and jeans",
        "wearing a black leather jacket and boots",
        "wearing a hoodie and baseball cap",
        "wearing a polo shirt and dark pants",
        "wearing a work uniform with reflective stripes",
    ]
    cabellos = [
        "short curly dark hair",
        "grey cropped hair",
        "bald with a short beard",
        "short spiky black hair",
        "chestnut brown curly hair",
        "short salt-and-pepper hair",
    ]
    rasgos = [
        "with mestizo features and light olive skin",
        "with light brown skin and freckles",
        "with olive skin and a strong jaw",
        "with pale skin and green eyes",
        "with tan skin and a warm smile",
    ]
    perfil = (
        f"a {random.choice(edades)} Mexican {random.choice(generos)}, "
        f"{random.choice(rasgos)}, "
        f"with {random.choice(cabellos)}, {random.choice(vestimentas)}"
    )
    return perfil

PERFIL_PERSONAJE = generar_perfil_personaje()
UBICACION_HISTORIA = random.choice(ESTADOS_MEXICO)

# ================================================================
# AUDIO DE FONDO
# ================================================================
FONDOS_DISPONIBLES = [
    "Ash and Marrow.mp3", "Black Maw.mp3", "Cold Hollow.mp3",
    "Hollow Marrow.mp3", "Sunken Dread.mp3", "Sunless Vault.mp3", "The Deep Rot.mp3"
]

def cargar_estado_musica():
    try:
        with open(MUSICA_ESTADO_FILE, "r", encoding="utf-8") as f:
            estado = json.load(f)
        if "ultimo_fondo" in estado and "ultimos_fondos" not in estado:
            estado["ultimos_fondos"] = [estado["ultimo_fondo"]]
            del estado["ultimo_fondo"]
            guardar_estado_musica(estado)
        return estado
    except:
        return {"ultimos_fondos": []}

def guardar_estado_musica(estado):
    with open(MUSICA_ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)

def seleccionar_fondo_disponible():
    estado = cargar_estado_musica()
    ultimos = estado.get("ultimos_fondos", [])
    excluir = set(ultimos[-3:]) if ultimos else set()
    disponibles = [f for f in FONDOS_DISPONIBLES if f not in excluir]
    if not disponibles:
        disponibles = FONDOS_DISPONIBLES.copy()
    for _ in range(5):
        elegido = random.choice(disponibles)
        for root, dirs, files in os.walk("."):
            if "/." in root or "\\." in root:
                continue
            if elegido in files:
                full_path = os.path.join(root, elegido)
                ultimos.append(elegido)
                if len(ultimos) > 10:
                    ultimos = ultimos[-10:]
                estado["ultimos_fondos"] = ultimos
                guardar_estado_musica(estado)
                print(f"✅ Audio de fondo seleccionado: {full_path}")
                return full_path
        disponibles.remove(elegido)
        if not disponibles:
            break
    for fondo in FONDOS_DISPONIBLES:
        for root, dirs, files in os.walk("."):
            if "/." in root or "\\." in root:
                continue
            if fondo in files:
                full_path = os.path.join(root, fondo)
                print(f"⚠️ Fallback: {full_path}")
                return full_path
    print("⚠️ No se encontró ningún archivo de fondo.")
    return None

FONDO_AUDIO_FILE = seleccionar_fondo_disponible()

# ================================================================
# GESTIÓN DE TÍTULOS PUBLICADOS
# ================================================================
def cargar_titulos_largos():
    try:
        with open(TITULOS_LARGOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"titulos": []}

def guardar_titulo_largo(titulo):
    data = cargar_titulos_largos()
    if titulo not in data["titulos"]:
        data["titulos"].append(titulo)
    with open(TITULOS_LARGOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def titulo_largo_ya_publicado(titulo):
    data = cargar_titulos_largos()
    titulo_norm = titulo.lower().strip()
    for t in data["titulos"]:
        t_norm = t.lower().strip()
        if titulo_norm == t_norm:
            return True
        palabras1 = set(re.findall(r'\w+', titulo_norm))
        palabras2 = set(re.findall(r'\w+', t_norm))
        if len(palabras1) > 3 and len(palabras2) > 3:
            interseccion = palabras1.intersection(palabras2)
            similitud = len(interseccion) / min(len(palabras1), len(palabras2))
            if similitud > 0.7:
                return True
    return False

# ================================================================
# GESTIÓN DE TEMAS
# ================================================================
def cargar_temas_shorts():
    try:
        with open(TEMAS_SHORTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"temas": []}

def guardar_tema_shorts(tema):
    data = cargar_temas_shorts()
    if tema not in data["temas"]:
        data["temas"].append(tema)
    with open(TEMAS_SHORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def tema_ya_usado(tema, umbral=0.5):
    data = cargar_temas_shorts()
    if not data["temas"]:
        return False
    palabras_nuevas = set(re.findall(r'\w+', tema.lower()))
    if not palabras_nuevas:
        return False
    for tema_antiguo in data["temas"][-20:]:
        palabras_antiguas = set(re.findall(r'\w+', tema_antiguo.lower()))
        if not palabras_antiguas:
            continue
        interseccion = palabras_nuevas.intersection(palabras_antiguas)
        union = palabras_nuevas.union(palabras_antiguas)
        similitud = len(interseccion) / len(union) if union else 0
        if similitud > umbral:
            print(f"⚠️ Tema similar: '{tema_antiguo}' (similitud {similitud:.2f})")
            return True
    return False

# ================================================================
# VALIDACIÓN DE TÍTULO GANCHO
# ================================================================
def validar_titulo_gancho(titulo):
    if not titulo or len(titulo) < 30:
        return False

    genericas = ["misterio", "leyenda", "relato", "caso", "historia de terror", "el fantasma de"]
    if any(titulo.lower().startswith(g) for g in genericas):
        return False

    ganchos_fuertes = [
        "vi", "escuché", "sobreviví", "regresé", "volví", "fui", "estuve", "viví",
        "descubrí", "encontré", "pasó", "ocurrió", "sucedió", "oí", "sentí",
        "3:33", "3:00", "medianoche", "nunca", "jamás", "solo", "primero",
        "último", "desapareció", "regresó", "volvió", "entró", "salió", "huyó",
        "escapé", "corrí", "grité", "lloré", "rogué", "supliqué", "¿", "?",
        "cómo", "por qué", "qué", "dónde", "cuándo", "horas", "días", "noches"
    ]
    tiene_gancho = any(g in titulo.lower() for g in ganchos_fuertes)
    longitud_ok = 35 <= len(titulo) <= 95
    tiene_separador = any(c in titulo for c in [":", "-", "|", ","])

    if tiene_gancho and longitud_ok:
        return True
    if longitud_ok and tiene_separador and len(titulo) > 40:
        return True
    if any(titulo.startswith(p) for p in ["Trabajé", "Fui", "El pozo", "Encontré", "Vi lo que", "Exploré", "Sobreviví"]):
        return True

    return False

# ================================================================
# EVALUAR CLARIDAD DEL TÍTULO
# ================================================================
def evaluar_claridad_titulo(titulo, historia_resumen):
    prompt = f"""
Eres un EXPERTO EN TÍTULOS DE YOUTUBE. Evalúa el siguiente título para un video de terror/paranormal.

Título: "{titulo}"
Resumen de la historia: "{historia_resumen[:200]}..."

Responde únicamente con un JSON:
{{
    "claro": true/false,
    "razon": "Breve explicación",
    "sugerencia": "Si no es claro, una sugerencia de mejora"
}}

Criterios:
- ¿Se entiende de qué trata el video en menos de 10 segundos?
- ¿Genera curiosidad o promete algo concreto?
- ¿Evita ser genérico?
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 150,
        "response_format": {"type": "json_object"}
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        respuesta = r.json()["choices"][0]["message"]["content"].strip()
        data = json.loads(limpiar_respuesta_json(respuesta))
        claro = data.get("claro", False)
        if not claro:
            print(f"⚠️ Título no claro: {data.get('razon', 'sin razón')}")
            print(f"   Sugerencia: {data.get('sugerencia', '')}")
        return claro
    except Exception as e:
        print(f"⚠️ Error evaluando claridad del título: {e}")
        return True

# ================================================================
# LIMPIAR RESPUESTA JSON
# ================================================================
def limpiar_respuesta_json(respuesta):
    if not respuesta:
        return ""
    respuesta = re.sub(r"```json\s*", "", respuesta, flags=re.IGNORECASE)
    respuesta = re.sub(r"```\s*", "", respuesta)
    inicio = respuesta.find("{")
    fin = respuesta.rfind("}")
    if inicio != -1 and fin != -1:
        json_str = respuesta[inicio : fin + 1]
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*\]", "]", json_str)
        return json_str
    return respuesta

# ================================================================
# 🎯 GENERAR HISTORIA CON TEMAS VIRALES
# ================================================================
def generar_historia_completa():
    # Seleccionar tema viral
    tema_viral = random.choice(TEMAS_VIRALES_LARGOS)
    contexto = random.choice(tema_viral["contextos"])
    keywords = tema_viral["keywords"]
    
    temas_recientes = cargar_temas_shorts()["temas"][-20:]
    temas_texto = "\n".join([f"- {t}" for t in temas_recientes]) if temas_recientes else "Ninguno aún."

    titulos_pub = cargar_titulos_largos()["titulos"][-20:]
    titulos_referencia = "\n".join([f"- {t}" for t in titulos_pub]) if titulos_pub else "Ninguno aún."

    prompt_base = f"""
Eres un GUIONISTA EXPERTO en TERROR, SUSPENSO y NARRATIVA DE ALTO IMPACTO para YouTube.

🔥 TEMA VIRAL SELECCIONADO: {tema_viral['tema'].upper()}
📍 CONTEXTO: {contexto}
🔑 KEYWORDS: {', '.join(keywords)}
⏱️ DURACIÓN OBJETIVO: {tema_viral['duracion_objetivo']//60} minutos

🚫 TÍTULOS YA PUBLICADOS (NO REPETIR):
{titulos_referencia}

🚫 TEMAS YA PUBLICADOS (EVITAR):
{temas_texto}

 REGLA DE ORO: Tu historia debe tener una PREMISA FUERTE que genere CURIOSIDAD INMEDIATA.

🎯 REGLA DE TÍTULO SEO (CRÍTICA):
El título debe ser un GANCHO que se entienda en 10 segundos.
EJEMPLOS DE TÍTULOS GANADORES (40-95 caracteres):
- "Exploré los Backrooms de {contexto} durante 12 horas"
- "Sobreviví 7 noches en {contexto} - Testimonio REAL"
- "Una IA predijo mi muerte en {contexto} - 3 días después"
❌ NUNCA: "El misterio de...", "La leyenda de...", "Relato de..."

🎯 REGLA DE PALABRAS CLAVE PARA MINIATURA:
"palabras_portada": TEXTO GANCHO de 2-4 palabras emocionales y ESPECÍFICAS.

🎯 REGLA DE ÉPOCA Y AMBIENTACIÓN:
"anio_suceso": año específico del suceso (1970-2020).

🎯 REGLA DE PERSONAJE:
Personaje principal fijo: "{PERFIL_PERSONAJE}"

🎯 ESTRUCTURA DEL RELATO (texto_completo - 1600-2000 palabras):
1. HOOK INMEDIATO (primeros 30 segundos impactantes)
2. CONTEXTO DETALLADO: Quién, dónde, cuándo, por qué
3. DESARROLLO PROGRESIVO: Aumento constante de tensión
4. CLÍMAX MÚLTIPLE: Varios momentos aterradores
5. DESENLACE ABIERTO: Reflexión o pregunta final
- Tono: Natural, coloquial, en primera persona
- IMPORTANTE: Describe ENTORNOS, SONIDOS, SENSACIONES
- Incluye timestamps naturales cada 2-3 minutos

🎯 REGLA DE CAPÍTULOS:
Genera 5-7 capítulos con timestamps REALISTAS basados en {tema_viral['duracion_objetivo']//60}-{(tema_viral['duracion_objetivo']+120)//60} minutos.

Responde ESTRICTAMENTE en este JSON:
{{
  "titulo": "Título ultra-viral 2024 (40-95 caracteres)",
  "titulo_alternativo": "Título alternativo",
  "anio_suceso": 2019,
  "palabras_clave": ["{keywords[0]}", "{keywords[1]}", "{keywords[2]}"],
  "palabras_portada": "TEXTO GANCHO 2-4 palabras",
  "descripcion": "Descripción SEO completa con gancho inicial",
  "tags": "15-20 tags separados por coma",
  "hashtags": "#Terror #Mexico #RelatosReales #Viral2024 (mínimo 5 hashtags)",
  "miniatura_prompt": "YouTube horror thumbnail 16:9: [escena MÁS impactante del relato]",
  "capitulos": [
    {{"tiempo": "00:00", "titulo": "El Comienzo"}},
    {{"tiempo": "02:30", "titulo": "Los Primeros Signos"}},
    {{"tiempo": "05:45", "titulo": "El Encuentro"}},
    {{"tiempo": "09:15", "titulo": "El Clímax"}},
    {{"tiempo": "12:00", "titulo": "La Revelación"}}
  ],
  "texto_completo": "Relato completo de 1600-2000 palabras con timestamps naturales"
}}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt_base}],
        "temperature": 0.75,
        "max_tokens": 5000,
        "response_format": {"type": "json_object"}
    }

    for intento in range(6):
        try:
            print(f"🔄 Intento {intento+1}/6 generando historia viral...")
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            respuesta_json = r.json()
            respuesta = respuesta_json["choices"][0]["message"]["content"].strip()
            json_str = limpiar_respuesta_json(respuesta)
            data = None
            try:
                data = json5.loads(json_str)
            except Exception as e5:
                try:
                    data = json.loads(json_str, strict=False)
                except json.JSONDecodeError as e:
                    print(f"❌ JSON inválido: {e}")
                    raise

            texto = data.get("texto_completo", "")
            palabras = len(texto.split())
            print(f"📊 Palabras del relato: {palabras}")

            if "texto_completo" in data and palabras >= 500:
                titulo_generado = data.get("titulo", "")

                if not validar_titulo_gancho(titulo_generado):
                    print(f"⚠️ Título no pasa validación básica: '{titulo_generado}'. Reintentando...")
                    raise ValueError("Título no cumple estándar de gancho")

                if not evaluar_claridad_titulo(titulo_generado, texto[:300]):
                    print(f"⚠️ Título no pasa evaluación de claridad. Reintentando...")
                    raise ValueError("Título no claro")

                if titulo_largo_ya_publicado(titulo_generado):
                    print(f"⚠️ Título YA PUBLICADO: '{titulo_generado}'. Regenerando...")
                    raise ValueError("Título duplicado")

                keywords = data.get("palabras_clave", [])
                if keywords:
                    tema = " ".join(keywords)
                    if tema_ya_usado(tema):
                        print(f"⚠️ Tema YA PUBLICADO: '{tema}'. Regenerando...")
                        raise ValueError("Tema duplicado")

                anio_suceso = data.get("anio_suceso", None)
                actualizar_epoca(anio_suceso)
                print(f"✅ Historia generada: {palabras} palabras.")
                print(f"🔥 Título VIRAL: {titulo_generado}")
                print(f"🎯 Tema viral: {tema_viral['tema']}")
                return data
            else:
                print(f"️ Texto insuficiente ({palabras} palabras). Reintentando en 10s...")
                raise ValueError("Texto insuficiente")
        except Exception as e:
            print(f"❌ Intento {intento+1}/6 falló: {e}")
            if intento < 5:
                time.sleep(10)
    print("❌ No se pudo generar historia válida después de 6 intentos.")
    sys.exit(1)

# ================================================================
# DIVIDIR TEXTO EN SEGMENTOS
# ================================================================
def dividir_en_segmentos(texto, max_palabras_por_segmento=55):
    oraciones = re.split(r'(?<=[.!?¿¡])\s+', texto)
    oraciones = [o.strip() for o in oraciones if o.strip()]
    if not oraciones:
        return [texto]
    segmentos = []
    segmento_actual = []
    palabras_actuales = 0
    for oracion in oraciones:
        palabras_oracion = len(oracion.split())
        if palabras_actuales + palabras_oracion > max_palabras_por_segmento and segmento_actual:
            segmentos.append(" ".join(segmento_actual))
            segmento_actual = [oracion]
            palabras_actuales = palabras_oracion
        else:
            segmento_actual.append(oracion)
            palabras_actuales += palabras_oracion
    if segmento_actual:
        segmentos.append(" ".join(segmento_actual))
    return segmentos

# ================================================================
# ASIGNAR ETAPAS VISUALES
# ================================================================
def asignar_etapas_visuales(segmentos, ubicacion):
    n = len(segmentos)
    etapas = []
    ubicaciones = []
    for i in range(n):
        progreso = i / max(n - 1, 1)
        if progreso < 0.2:
            etapa = "inicio_casa"; ubic = f"interior del hogar en {ubicacion}"
        elif progreso < 0.4:
            etapa = "desplazamiento"; ubic = f"calle o vehículo en movimiento, {ubicacion}"
        elif progreso < 0.65:
            etapa = "lugar_destino"; ubic = f"lugar específico del suceso en {ubicacion}"
        elif progreso < 0.85:
            etapa = "climax_evento"; ubic = f"mismo lugar del suceso en {ubicacion}, momento del evento"
        else:
            etapa = "resolucion"; ubic = f"salida o regreso desde el lugar, {ubicacion}"
        etapas.append(etapa)
        ubicaciones.append(ubic)
    return etapas, ubicaciones

# ================================================================
# 🎬 GENERAR QUERY CINEMATOGRÁFICO PARA PEXELS
# ================================================================
def generar_query_cinematografico(segmento_texto, etapa, ubicacion_escena, tema_viral):
    """
    Genera prompts cinematográficos profesionales para videos largos
    """
    prompts_cinematograficos = {
        "inicio_casa": f"""
            POV shot from inside dark mexican {ubicacion_escena}, 
            single flickering light bulb, long hallway leading to darkness, 
            cinematic horror photography, shallow depth of field, 
            shot on 35mm, film grain, cold blue tones, unsettling atmosphere
        """,
        "desplazamiento": f"""
            Night driving shot, dark mexican road through {ubicacion_escena}, 
            fog, headlights illuminating mist, cinematic thriller photography, 
            motion blur, shallow focus, eerie atmosphere, 35mm film look
        """,
        "lugar_destino": f"""
            Wide establishing shot of {ubicacion_escena} at night, 
            mexican location, fog, dramatic lighting, cinematic horror photography, 
            ultra wide angle, deep shadows, mysterious atmosphere
        """,
        "climax_evento": f"""
            Extreme close-up of terrified eyes reflecting something horrifying 
            in {ubicacion_escena}, dramatic chiaroscuro lighting, 
            horror movie still, hyperrealistic, shallow focus, tension, fear
        """,
        "resolucion": f"""
            Person walking away from {ubicacion_escena} at dawn, 
            silhouette against morning light, cinematic horror photography, 
            wide shot, atmospheric fog, emotional aftermath
        """
    }
    
    prompt_base = prompts_cinematograficos.get(etapa, prompts_cinematograficos["inicio_casa"])
    
    if tema_viral == "backrooms":
        prompt_base += ", liminal space, endless corridors, yellow wallpaper, fluorescent lights"
    elif tema_viral == "skinwalker":
        prompt_base += ", creature silhouette, forest, antlers, glowing eyes"
    elif tema_viral == "ritual":
        prompt_base += ", candles, ritual circle, ancient symbols, mystical atmosphere"
    elif tema_viral == "ia":
        prompt_base += ", computer screen, code, digital horror, glitch effects"
    
    prompt_base = re.sub(r'\s+', ' ', prompt_base).strip()
    
    return prompt_base[:200]

# ================================================================
# 🎬 GENERAR QUERY PARA MINIATURA EN PEXELS
# ================================================================
def generar_query_miniatura_pexels(miniatura_prompt):
    """
    Genera query optimizada para buscar miniatura en Pexels
    """
    prompt = f"""Genera SOLO 4-6 palabras clave en inglés para buscar una foto HORIZONTAL (16:9) en Pexels para una miniatura de YouTube de terror.
    Idea: "{miniatura_prompt[:150]}"
    Época: {EPOCA_MOD}
    Devuelve SOLO las palabras clave.
    """
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 40,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        query = r.json()["choices"][0]["message"]["content"].strip()
        query = re.sub(r'["\']', '', query)
        query = re.sub(r',', ' ', query)
        query = re.sub(r'\s+', ' ', query)
        return query if len(query) > 5 else "horror night dark landscape cinematic"
    except Exception as e:
        print(f"⚠️ Error generando query de miniatura: {e}")
        return "horror night dark landscape cinematic"

# ================================================================
# BUSCAR IMAGEN EN PEXELS
# ================================================================
ULTIMA_URL_PEXELS = None

def buscar_imagen_pexels(query, orientation="landscape", intentos=3):
    global ULTIMA_URL_PEXELS
    if not PEXELS_VALIDA:
        print("️ Pexels no disponible.")
        return None

    variantes = ["cinematic", "dramatic", "atmospheric", "moody", "film"]
    variacion = random.choice(variantes)
    query_variada = f"{query} {variacion}"

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query_variada,
        "orientation": orientation,
        "per_page": 10,
        "page": random.randint(1, 8)
    }

    for intento in range(intentos):
        try:
            print(f"🔍 Intento {intento+1}/{intentos} buscando en Pexels: '{query_variada}' ({orientation})...")
            r = requests.get(url, headers=headers, params=params, timeout=25)
            if r.status_code == 200:
                data = r.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    fotos = data["photos"][:min(5, len(data["photos"]))]
                    foto = random.choice(fotos)
                    image_url = foto["src"]["large2x"] or foto["src"]["large"] or foto["src"]["original"]
                    if ULTIMA_URL_PEXELS and image_url == ULTIMA_URL_PEXELS:
                        print("   ⚠️ URL repetida, buscando otra página...")
                        params["page"] = (params["page"] % 8) + 1
                        continue
                    ULTIMA_URL_PEXELS = image_url
                    print(f"✅ Imagen encontrada: {image_url[:80]}...")
                    return image_url
                else:
                    print("️ No se encontraron fotos para esta consulta.")
            else:
                print(f"️ Error Pexels: {r.status_code} - {r.text[:100]}")
        except requests.exceptions.Timeout:
            print("⏰ Timeout en Pexels. Reintentando...")
        except Exception as e:
            print(f"️ Error conexión Pexels: {e}")
        if intento < intentos - 1:
            print(f"   ⏳ Esperando 5s antes de reintentar...")
            time.sleep(5)

    print("❌ No se pudo obtener imagen de Pexels.")
    return None

# ================================================================
# 🖼️ BUSCAR MINIATURA EN PEXELS
# ================================================================
def buscar_miniatura_pexels(query, intentos=5):
    variantes_texto = [
        "empty space", "copy space", "negative space", 
        "dark background", "blurry background", "minimal"
    ]
    
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    
    for intento in range(intentos):
        try:
            variante = random.choice(variantes_texto)
            query_completa = f"{query} {variante}"
            
            params = {
                "query": query_completa,
                "orientation": "landscape",
                "per_page": 10,
                "page": random.randint(1, 5),
                "size": "large"
            }
            
            print(f"🔍 Intento {intento+1}/{intentos}: '{query_completa}'...")
            r = requests.get(url, headers=headers, params=params, timeout=25)
            
            if r.status_code == 200:
                data = r.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    for foto in data["photos"][:5]:
                        img_url = foto["src"]["large2x"] or foto["src"]["large"]
                        
                        try:
                            r_img = requests.get(img_url, timeout=10)
                            if r_img.status_code == 200:
                                print(f"✅ Miniatura encontrada: {img_url[:80]}...")
                                return img_url
                        except:
                            continue
                    
            else:
                print(f"⚠️ Error Pexels: {r.status_code}")
                
        except Exception as e:
            print(f"⚠️ Error: {e}")
        
        if intento < intentos - 1:
            time.sleep(3)
    
    print("⚠️ Usando búsqueda de fallback...")
    params = {
        "query": query,
        "orientation": "landscape",
        "per_page": 5,
        "page": 1
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=25)
        if r.status_code == 200:
            data = r.json()
            if data.get("photos"):
                return data["photos"][0]["src"]["large2x"]
    except:
        pass
    
    return None

# ================================================================
# EXPANDIR TEXTO
# ================================================================
def expandir_texto(titulo, texto_actual):
    prompt = f"""Historia: "{titulo}"

Final actual del relato:
\"\"\"
{texto_actual[-400:]}
\"\"\"

Continúa la historia con 300-400 palabras más en primera persona, mismo tono.
Devuelve SOLO el texto de continuación.
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 900,
    }
    for intento in range(2):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            r.raise_for_status()
            extra = r.json()["choices"][0]["message"]["content"].strip()
            if len(extra.split()) > 100:
                print(f"✅ Expansión: {len(extra.split())} palabras adicionales.")
                return extra
        except Exception as e:
            print(f"❌ Expansión intento {intento+1}/2 falló: {e}")
        if intento < 1:
            print("⏳ Esperando 10 segundos...")
            time.sleep(10)
    return ""

# ================================================================
# 🎨 CREAR MINIATURA PROFESIONAL TIPO YOUTUBE
# ================================================================
def crear_miniatura_profesional(img_path, texto, output_path):
    colores_impacto = [
        {"texto": (255, 255, 0), "fondo": (0, 0, 0)},
        {"texto": (255, 50, 50), "fondo": (0, 0, 0)},
        {"texto": (255, 140, 0), "fondo": (0, 0, 0)},
        {"texto": (0, 255, 255), "fondo": (0, 0, 0)},
        {"texto": (255, 255, 255), "fondo": (0, 0, 0)},
        {"texto": (255, 0, 255), "fondo": (0, 0, 0)},
    ]
    
    color_elegido = random.choice(colores_impacto)
    color_texto = color_elegido["texto"]
    
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    
    try:
        with Image.open(img_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img = ImageOps.fit(img, (1280, 720), Image.LANCZOS)
            
            # Aplicar mejoras de imagen
            img = ImageEnhance.Contrast(img).enhance(1.3)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
            
            draw = ImageDraw.Draw(img)
            width, height = img.size
            
            texto_final = texto.upper().strip()
            
            palabras = texto_final.split()
            if len(palabras) > 4:
                mitad = len(palabras) // 2
                linea1 = " ".join(palabras[:mitad])
                linea2 = " ".join(palabras[mitad:])
                lineas = [linea1, linea2]
            else:
                lineas = [texto_final]
            
            font_size = 90
            font = None
            
            for size in range(120, 40, -5):
                try:
                    font = ImageFont.truetype(font_paths[0], size)
                    max_width = 0
                    total_height = 0
                    for linea in lineas:
                        bbox = draw.textbbox((0, 0), linea, font=font)
                        w = bbox[2] - bbox[0]
                        h = bbox[3] - bbox[1]
                        max_width = max(max_width, w)
                        total_height += h + 15
                    
                    if max_width < width * 0.9 and total_height < height * 0.5:
                        font_size = size
                        break
                except:
                    continue
            
            if font is None:
                try:
                    font = ImageFont.truetype(font_paths[0], font_size)
                except:
                    font = ImageFont.load_default()
            
            total_height = 0
            heights = []
            for linea in lineas:
                bbox = draw.textbbox((0, 0), linea, font=font)
                h = bbox[3] - bbox[1]
                heights.append(h)
                total_height += h + 15
            
            y_start = (height - total_height) // 2 + 50
            
            padding = 30
            max_line_width = 0
            for linea in lineas:
                bbox = draw.textbbox((0, 0), linea, font=font)
                w = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, w)
            
            rect_x = (width - max_line_width) // 2 - padding
            rect_y = y_start - padding
            rect_w = max_line_width + (padding * 2)
            rect_h = total_height + (padding * 2)
            
            draw.rectangle(
                [rect_x, rect_y, rect_x + rect_w, rect_y + rect_h],
                fill=(0, 0, 0, 200)
            )
            
            y_current = y_start
            for linea in lineas:
                bbox = draw.textbbox((0, 0), linea, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                
                x = (width - w) // 2
                
                for offset in range(-5, 6):
                    for offset_y in range(-5, 6):
                        if offset != 0 or offset_y != 0:
                            draw.text(
                                (x + offset, y_current + offset_y),
                                linea,
                                font=font,
                                fill=(0, 0, 0, 200)
                            )
                
                for dx in [-4, -3, -2, -1, 1, 2, 3, 4]:
                    for dy in [-4, -3, -2, -1, 1, 2, 3, 4]:
                        draw.text(
                            (x + dx, y_current + dy),
                            linea,
                            font=font,
                            fill=(0, 0, 0)
                        )
                
                draw.text(
                    (x, y_current),
                    linea,
                    font=font,
                    fill=color_texto
                )
                
                y_current += h + 15
            
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            
            for i in range(200):
                alpha = int(150 * (i / 200))
                draw_overlay.rectangle(
                    [i, i, width-i, height-i],
                    fill=(0, 0, 0, alpha//4)
                )
            
            img = Image.alpha_composite(img.convert('RGBA'), overlay)
            
            img.convert('RGB').save(output_path, "JPEG", quality=95, optimize=True)
            
            print(f"✅ Miniatura profesional creada: {output_path}")
            print(f"   📝 Texto: '{texto}'")
            print(f"   🎨 Color: {color_texto}")
            return True
            
    except Exception as e:
        print(f"❌ Error creando miniatura: {e}")
        import traceback
        traceback.print_exc()
        return False

# ================================================================
# GENERAR AUDIO
# ================================================================
def generar_audio(texto, index, intentos_por_voz=2):
    global CONFIG_VOZ_ACTUAL
    texto_limpio = re.sub(r"imagen_prompt.*", "", texto, flags=re.IGNORECASE)
    texto_limpio = re.sub(r"prompt.*", "", texto_limpio, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'[\{\}\[\]"]', "", texto_limpio)
    texto_limpio = re.sub(r"\s+", " ", texto_limpio).strip()
    if len(texto_limpio) < 10:
        return None
    filename = f"audio_{index}.mp3"
    voces_a_probar = [CONFIG_VOZ_ACTUAL]
    for voz_config in VOCES_DISPONIBLES:
        if voz_config["voz"] != CONFIG_VOZ_ACTUAL["voz"]:
            voces_a_probar.append(voz_config)
    for intento_voz, voz_config in enumerate(voces_a_probar):
        voz = voz_config["voz"]; rate = voz_config["velocidad"]; pitch = voz_config["tono"]
        for intento in range(intentos_por_voz):
            async def _generar():
                communicate = edge_tts.Communicate(texto_limpio, voz, rate=rate, pitch=pitch)
                await communicate.save(filename)
            try:
                asyncio.run(_generar())
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    if voz != CONFIG_VOZ_ACTUAL["voz"]:
                        print(f"🔄 Voz cambiada: {CONFIG_VOZ_ACTUAL['voz']} → {voz}")
                    CONFIG_VOZ_ACTUAL = voz_config
                    return filename
            except Exception as e:
                print(f"❌ Falló {voz}: {e}")
            if intento < intentos_por_voz - 1:
                time.sleep(3 * (intento + 1))
    if os.path.exists(filename):
        try:
            os.remove(filename)
        except:
            pass
    print("❌ Todas las voces neurales fallaron.")
    return None

# ================================================================
# 🎬 MONTAR VIDEO CON EFECTOS CINEMATOGRÁFICOS
# ================================================================
def montar_video(elementos, salida="video_final.mp4"):
    clips_video = []
    clips_audio = []
    for i, elem in enumerate(elementos):
        try:
            audio_clip = AudioFileClip(elem["audio_path"])
            duracion = audio_clip.duration
            r = requests.get(elem["imagen_url"], timeout=30)
            r.raise_for_status()
            img_path = f"temp_img_{i}.jpg"
            with open(img_path, "wb") as f:
                f.write(r.content)
            with Image.open(img_path) as img:
                img = ImageOps.fit(img, (1920, 1080), Image.LANCZOS)
                
                # Aplicar efectos según etapa
                if "climax" in elem.get("etapa", ""):
                    img = ImageEnhance.Contrast(img).enhance(1.4)
                    img = img.filter(ImageFilter.SHARPEN)
                elif "inicio" in elem.get("etapa", ""):
                    img = ImageEnhance.Brightness(img).enhance(0.8)
                    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
                
                img.save(img_path)
                
            if duracion > 35:
                duracion_mitad = duracion / 2
                clips_video.extend([ImageClip(img_path, duration=duracion_mitad), ImageClip(img_path, duration=duracion_mitad)])
                clips_audio.extend([audio_clip.subclip(0, duracion_mitad), audio_clip.subclip(duracion_mitad, duracion)])
            else:
                clips_video.append(ImageClip(img_path, duration=duracion))
                clips_audio.append(audio_clip)
        except Exception as e:
            print(f"⚠️ Error en segmento {i}: {e}")
            continue
    if not clips_video or not clips_audio:
        raise ValueError("No se pudieron procesar los clips.")
    video = concatenate_videoclips(clips_video, method="compose")
    audio_narracion = concatenate_audioclips(clips_audio)
    duracion_total = audio_narracion.duration
    if FONDO_AUDIO_FILE and os.path.exists(FONDO_AUDIO_FILE):
        try:
            fondo_clip = AudioFileClip(FONDO_AUDIO_FILE)
            if fondo_clip.duration < duracion_total:
                veces = int(duracion_total / fondo_clip.duration) + 1
                fondo_clip = concatenate_audioclips([fondo_clip] * veces)
            fondo_clip = fondo_clip.subclip(0, duracion_total).volumex(0.08)
            fondo_clip = fondo_clip.audio_fadein(2).audio_fadeout(2)
            audio_final = CompositeAudioClip([audio_narracion, fondo_clip])
        except Exception as e:
            print(f"⚠️ Error en audio fondo: {e}")
            audio_final = audio_narracion
    else:
        audio_final = audio_narracion
    video = video.set_audio(audio_final)
    video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")
    video.close()
    audio_final.close()
    for c in clips_video:
        c.close()
    for a in clips_audio:
        a.close()
    return salida, duracion_total

# ================================================================
# LIMPIEZA
# ================================================================
def limpiar_archivos_temporales():
    for f in os.listdir("."):
        if (f.startswith("temp_img_") or f.startswith("audio_")) and (f.endswith(".jpg") or f.endswith(".mp3")):
            try:
                os.remove(f)
            except:
                pass
    for aux in ["video_final.mp4", "miniatura.jpg", "miniatura_base.jpg"]:
        if os.path.exists(aux):
            try:
                os.remove(aux)
            except:
                pass

# ================================================================
# SUBIR A YOUTUBE
# ================================================================
def subir_a_youtube(video_path, miniatura_path, titulo, descripcion, etiquetas, capitulos=None, duracion_real_minutos=0):
    creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
    youtube = build("youtube", "v3", credentials=creds)
    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]

    if capitulos and "⏰ Capítulos" not in descripcion:
        capitulos_texto = "\n⏰ Capítulos del relato:\n"
        for cap in capitulos:
            capitulos_texto += f"{cap['tiempo']} - {cap['titulo']}\n"
        if "#" in descripcion:
            partes = descripcion.rsplit("#", 1)
            descripcion = partes[0] + capitulos_texto + "#" + partes[1]
        else:
            descripcion += capitulos_texto

    if ACTIVAR_DISCLOSURE_IA:
        descripcion += DISCLOSURE_TEXT

    body = {
        "snippet": {
            "title": titulo[:100],
            "description": descripcion[:5000],
            "tags": etiquetas[:30],
            "categoryId": "24",
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,
        },
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    video_id = response["id"]
    print(f"✅ Video subido: https://youtu.be/{video_id}")
    if miniatura_path and os.path.exists(miniatura_path):
        try:
            media_thumb = MediaFileUpload(miniatura_path, chunksize=-1, resumable=True)
            youtube.thumbnails().set(videoId=video_id, media_body=media_thumb).execute()
            print("✅ Miniatura subida correctamente")
        except Exception as e:
            print(f"⚠️ Error miniatura: {e}")

# ================================================================
# PUBLICACIÓN DIARIA
# ================================================================
def verificar_publicacion_hoy():
    estado = cargar_estado_musica()
    ultima = estado.get("ultima_publicacion_exitosa")
    if not ultima:
        return False
    hoy = datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()
    return ultima == hoy

def marcar_publicacion_exitosa():
    estado = cargar_estado_musica()
    hoy = datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()
    estado["ultima_publicacion_exitosa"] = hoy
    guardar_estado_musica(estado)

# ================================================================
# PROCESAR SEGMENTOS CON EFECTOS
# ================================================================
def procesar_segmentos(segmentos, etapas, ubicaciones, tema_viral, offset=0):
    elementos = []
    imagen_ultimo_recurso = None
    for i, seg_texto in enumerate(segmentos):
        idx = offset + i
        etapa = etapas[i] if i < len(etapas) else "lugar_destino"
        ubic = ubicaciones[i] if i < len(ubicaciones) else UBICACION_HISTORIA
        print(f"\n📍 Segmento {idx+1} - Etapa: {etapa} | {ubic}")

        query = generar_query_cinematografico(seg_texto, etapa, ubic, tema_viral)

        if i > 0:
            time.sleep(3)

        url_img = buscar_imagen_pexels(query, orientation="landscape")
        if url_img:
            imagen_ultimo_recurso = url_img
        else:
            if imagen_ultimo_recurso:
                print(f"️ Reutilizando imagen anterior para segmento {idx+1}.")
                url_img = imagen_ultimo_recurso
            else:
                query_fallback = "mexican night landscape dark cinematic"
                url_img = buscar_imagen_pexels(query_fallback, orientation="landscape")
                if url_img:
                    print(f"⚠️ Usando imagen genérica para segmento {idx+1}.")
                    imagen_ultimo_recurso = url_img
                else:
                    continue

        audio_file = generar_audio(seg_texto, idx)
        if not audio_file:
            continue

        elementos.append({"imagen_url": url_img, "audio_path": audio_file, "etapa": etapa})
    return elementos

# ================================================================
# MAIN
# ================================================================
def verificar_envs():
    required = ["DEEPSEEK_API_KEY", "PEXELS_API_KEY", "YOUTUBE_USER_TOKEN"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"❌ Faltan variables: {', '.join(missing)}")
        sys.exit(1)

def main():
    verificar_envs()

    if os.getenv("FORCE_PUBLISH") == "true":
        print(" FORCE_PUBLISH activado: se publicará aunque ya haya video hoy.")
    else:
        estado_musica = cargar_estado_musica()
        if verificar_publicacion_hoy():
            print("✅ Ya se publicó hoy. Saliendo.")
            sys.exit(0)

    estado_publicacion = cargar_estado_musica()

    if not deberia_publicar_ahora(estado_publicacion):
        print("⏸️ Decisión: No publicar en esta ejecución.")
        guardar_estado_musica(estado_publicacion)
        sys.exit(0)

    print("="*70)
    print("👻 SOMBRAS DE MEDIANOCHE - BOT VIDEOS LARGOS VIRAL 2024")
    print("   ✦ Temas virales trending (Backrooms, Skinwalker, IA, etc.)")
    print("   ✦ Títulos ultra-virales con fórmulas probadas")
    print("   ✦ Miniaturas profesionales tipo MrBeast")
    print("   ✦ Imágenes cinematográficas con efectos")
    print("   ✦ Verificación de demanda real")
    print("="*70)
    print(f"🎤 Voz: {CONFIG_VOZ_ACTUAL['voz']} (+12%)")
    print(f"🧑 Personaje: {PERFIL_PERSONAJE}")
    print(f"📍 Ubicación: {UBICACION_HISTORIA}")
    print(f"🎨 Paleta: {PALETA_COLOR_ACTUAL[:80]}...")
    print(f"🎵 Fondo: {FONDO_AUDIO_FILE if FONDO_AUDIO_FILE else 'Ninguno'}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-"*70)

    historia = generar_historia_completa()
    titulo_video = historia.get("titulo", "Relato Paranormal Real")
    palabras_portada = historia.get("palabras_portada", "TERROR")
    descripcion_base = historia.get("descripcion", f"Relato paranormal.\n{FACEBOOK_LINK}")
    tags_video = historia.get("tags", "relatos, leyendas, mexico")
    hashtags_video = historia.get("hashtags", "#Terror #Mexico #RelatosReales #Viral2024")
    capitulos_video = historia.get("capitulos", [])
    texto_completo = historia.get("texto_completo", "")
    keywords = historia.get("palabras_clave", [])
    
    tema_viral = historia.get("tema", {}).get("tipo", "paranormal")

    if keywords:
        tema_busqueda = keywords[0]
    else:
        tema_busqueda = titulo_video.split()[0]
    if not verificar_demanda_youtube(tema_busqueda):
        print("⛔ Demanda insuficiente. Cancelando publicación.")
        sys.exit(0)

    descripcion_completa = f"""{descripcion_base}

🔴 RELATO COMPLETO en el canal: {CANAL_LINK}
 Facebook: {FACEBOOK_LINK}

{hashtags_video}"""

    print(f"\n SEO VIRAL GENERADO:")
    print(f"   🔥 Título VIRAL: {titulo_video}")
    print(f"   ️ Texto miniatura: {palabras_portada}")
    print(f"   🗓️ Año del suceso: {ANIO_SUCESO if ANIO_SUCESO else 'actualidad'}")
    print(f"   📚 Capítulos: {len(capitulos_video)}")
    print(f"   🔑 Keywords: {keywords}")
    print(f"   🎯 Tema viral: {tema_viral}")

    segmentos = dividir_en_segmentos(texto_completo, 55)
    etapas, ubicaciones = asignar_etapas_visuales(segmentos, UBICACION_HISTORIA)
    print(f"\n {len(segmentos)} segmentos con efectos cinematográficos.")

    elementos_validos = procesar_segmentos(segmentos, etapas, ubicaciones, tema_viral, offset=0)
    if not elementos_validos:
        print("❌ No hay elementos válidos.")
        sys.exit(1)

    duracion_actual = sum(AudioFileClip(e["audio_path"]).duration for e in elementos_validos)
    print(f"⏱️ Duración: {duracion_actual/60:.1f} minutos")

    intentos_expansion = 0
    while duracion_actual < DURACION_MINIMA_SEGUNDOS and intentos_expansion < MAX_INTENTOS_EXPANSION:
        print(f"⚠️ Duración insuficiente. Expandiendo intento {intentos_expansion+1}...")
        texto_extra = expandir_texto(titulo_video, texto_completo)
        if texto_extra:
            texto_completo += " " + texto_extra
            nuevos = dividir_en_segmentos(texto_extra, 55)
            etapas_n, ubic_n = asignar_etapas_visuales(nuevos, UBICACION_HISTORIA)
            elems_n = procesar_segmentos(nuevos, etapas_n, ubic_n, tema_viral, offset=len(elementos_validos))
            elementos_validos.extend(elems_n)
            duracion_actual = sum(AudioFileClip(e["audio_path"]).duration for e in elementos_validos)
            intentos_expansion += 1
        else:
            break

    if duracion_actual < DURACION_MINIMA_SEGUNDOS:
        print(f"❌ Duración final insuficiente. Abortando.")
        sys.exit(1)

    print(f"✅ Duración final: {duracion_actual/60:.1f} minutos.")

    print("🖼️ Creando miniatura profesional viral...")
    miniatura_path = None
    
    query_miniatura = generar_query_miniatura_pexels(historia.get("miniatura_prompt", "scary horror night"))
    miniatura_base_url = buscar_miniatura_pexels(query_miniatura)

    if miniatura_base_url:
        try:
            r = requests.get(miniatura_base_url, timeout=30)
            r.raise_for_status()
            
            temp_base = "miniatura_base.jpg"
            with open(temp_base, "wb") as f:
                f.write(r.content)
            
            if crear_miniatura_profesional(temp_base, palabras_portada, "miniatura.jpg"):
                miniatura_path = "miniatura.jpg"
                print(f"✅ Miniatura viral generada con texto: '{palabras_portada}'")
            else:
                import shutil
                shutil.copy(temp_base, "miniatura.jpg")
                miniatura_path = "miniatura.jpg"
                print(f"⚠️ Miniatura guardada sin texto")
            
            if os.path.exists(temp_base):
                os.remove(temp_base)
                
        except Exception as e:
            print(f"⚠️ Error con miniatura: {e}")
            miniatura_path = None
    else:
        print("❌ No se pudo obtener imagen para miniatura.")
        miniatura_path = None

    print("🎬 Montando video HORIZONTAL (1920x1080) con efectos...")
    video_path, duracion_final = montar_video(elementos_validos)
    duracion_minutos = duracion_final / 60
    print(f"⏱️ Duración final: {duracion_minutos:.1f} minutos")

    print("⬆️ Subiendo a YouTube...")
    subir_a_youtube(
        video_path,
        miniatura_path,
        titulo_video,
        descripcion_completa,
        tags_video,
        capitulos_video,
        duracion_real_minutos=duracion_minutos
    )

    guardar_titulo_largo(titulo_video)
    if keywords:
        tema = " ".join(keywords)
        if not tema_ya_usado(tema):
            guardar_tema_shorts(tema)
    else:
        tema = f"{UBICACION_HISTORIA} {titulo_video.split()[0]}"
        guardar_tema_shorts(tema)

    estado_publicacion["publicaciones_hoy"] = estado_publicacion.get("publicaciones_hoy", 0) + 1
    estado_publicacion["ultima_publicacion"] = datetime.now(ZoneInfo("America/Mexico_City")).isoformat()
    marcar_publicacion_exitosa()
    guardar_estado_musica(estado_publicacion)

    limpiar_archivos_temporales()
    print("🎉 Proceso completado. ¡Video viral listo!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
