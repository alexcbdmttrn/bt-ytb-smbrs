import asyncio
from datetime import date, datetime
from zoneinfo import ZoneInfo
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
from PIL import Image, ImageDraw, ImageFont, ImageOps
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
# 🧠 CONFIGURACIÓN DE PUBLICACIÓN HUMANA (VIDEOS LARGOS)
# ================================================================
MAX_VIDEOS_DIA = 1
PROBABILIDAD_DESCANSO = 0.20      # 20% días sin publicar
PROBABILIDAD_CAPRICHO = 0.15      # 15% capricho de no publicar
INTERVALO_MIN_HORAS = 24
INTERVALO_MAX_HORAS = 72
RETRASO_MAX_MINUTOS = 45

# Umbral de demanda (vistas promedio en YouTube)
UMBRAL_DEMANDA_VIEWS = 10000

# ================================================================
# 🧠 DECISIONES DE PUBLICACIÓN
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
        print(f"📅 Nuevo día. Contador reiniciado.")

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
# VALIDAR PEXELS API KEY (SIN "Bearer")
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
        print(f"⚠️ Error probando API Key: {e}")
        return False

PEXELS_VALIDA = validar_pexels_api_key()

# ================================================================
# VERIFICAR DEMANDA EN YOUTUBE (FILTRO 2)
# ================================================================
def verificar_demanda_youtube(tema, umbral_views=UMBRAL_DEMANDA_VIEWS):
    """
    Busca el tema en YouTube y devuelve True si hay suficiente demanda.
    """
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
        # Si falla, asumimos que hay demanda para no bloquear
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
# VOCES NEURALES (con fallback automático)
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
# AUDIO DE FONDO (sin repetir los últimos 3)
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
# GESTIÓN DE TEMAS (para evitar repeticiones)
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
# VALIDACIÓN DE TÍTULO GANCHO (MEJORADA - FILTRO 1)
# ================================================================
def validar_titulo_gancho(titulo):
    """
    Valida que el título sea un gancho claro que se entienda en 10 segundos.
    """
    if not titulo or len(titulo) < 25:
        return False

    # Títulos genéricos prohibidos
    genericas = ["misterio", "leyenda", "relato", "caso", "historia de terror", "el fantasma de"]
    if any(titulo.lower().startswith(g) for g in genericas):
        return False

    # Palabras que indican gancho fuerte (pregunta, restricción, primera persona impactante)
    ganchos_fuertes = [
        "vi", "escuché", "sobreviví", "regresé", "volví", "fui", "estuve", "viví",
        "descubrí", "encontré", "pasó", "ocurrió", "sucedió", "oí", "sentí",
        "3:33", "3:00", "medianoche", "nunca", "jamás", "solo", "primero",
        "último", "desapareció", "regresó", "volvió", "entró", "salió", "huyó",
        "escapé", "corrí", "grité", "lloré", "rogué", "supliqué", "¿", "?",
        "cómo", "por qué", "qué", "dónde", "cuándo"
    ]
    tiene_gancho = any(g in titulo.lower() for g in ganchos_fuertes)
    longitud_ok = 30 <= len(titulo) <= 75
    tiene_separador = any(c in titulo for c in [":", "-", "|", ","])

    if tiene_gancho and longitud_ok:
        return True
    if longitud_ok and tiene_separador and len(titulo) > 35:
        return True
    if any(titulo.startswith(p) for p in ["Trabajé", "Fui", "El pozo", "Encontré", "Vi lo que"]):
        return True

    return False

# ================================================================
# EVALUAR CLARIDAD DEL TÍTULO CON DEEPSEEK (FILTRO 1 EXTRA)
# ================================================================
def evaluar_claridad_titulo(titulo, historia_resumen):
    """
    Pide a DeepSeek que evalúe si el título se entiende en 10 segundos y es un gancho claro.
    Devuelve True si pasa.
    """
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
- ¿Evita ser genérico (ej: "El misterio de...")?
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
        # Si falla, asumimos que es claro para no bloquear
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
# GENERAR HISTORIA (CON PROMPT MEJORADO - FILTRO 1)
# ================================================================
def generar_historia_completa():
    temas_recientes = cargar_temas_shorts()["temas"][-20:]
    temas_texto = "\n".join([f"- {t}" for t in temas_recientes]) if temas_recientes else "Ninguno aún."

    titulos_pub = cargar_titulos_largos()["titulos"][-20:]
    titulos_referencia = "\n".join([f"- {t}" for t in titulos_pub]) if titulos_pub else "Ninguno aún."

    prompt_base = f"""
Eres un GUIONISTA EXPERTO en TERROR, SUSPENSO y NARRATIVA DE ALTO IMPACTO para YouTube.

🚫 TÍTULOS YA PUBLICADOS (NO REPETIR NI PARECERSE):
{titulos_referencia}

🚫 TEMAS YA PUBLICADOS (EVITAR ESTAS TEMÁTICAS):
{temas_texto}

🎯 REGLA DE ORO: Tu historia debe tener una PREMISA FUERTE que genere CURIOSIDAD INMEDIATA.

🎯 REGLA DE TÍTULO SEO (CRÍTICA - FILTRO 1):
El título debe ser un GANCHO que se entienda en 10 segundos. Debe ser una pregunta, una restricción o una promesa clara.
EJEMPLOS DE TÍTULOS GANADORES (30-75 caracteres):
- "¿Qué vi en el manicomio de Puebla a las 3 AM?"
- "Sobreviví 7 días en el hotel más embrujado de México"
- "El pozo de mi pueblo no tenía fondo. Hasta que lo vi."
- "Fui velador en Oaxaca y vi algo que no debí ver"
❌ NUNCA: "El misterio de...", "La leyenda de...", "Relato de..."

🎯 REGLA DE PALABRAS CLAVE PARA MINIATURA:
"palabras_portada": TEXTO GANCHO de 2-3 palabras emocionales y ESPECÍFICAS del relato.

🎯 REGLA DE ÉPOCA Y AMBIENTACIÓN:
"anio_suceso": año específico del suceso (1970-2020).

🎯 REGLA DE PERSONAJE:
Personaje principal fijo: "{PERFIL_PERSONAJE}"

🎯 ESTRUCTURA DEL RELATO (texto_completo - 1400-1600 palabras):
1. GANCHO (1-2 párrafos): Presenta el conflicto central.
2. CONTEXTO: Quién, dónde, cuándo.
3. DESARROLLO: Aumento de tensión. Detalles sensoriales.
4. CLÍMAX: El momento más aterrador.
5. DESENLACE: Resolución o reflexión.
- Tono: Natural, coloquial, en primera persona.
- IMPORTANTE: Describe ENTORNOS (carros, casas, bosques, calles).

🎯 REGLA DE CAPÍTULOS:
Genera 4-6 capítulos con timestamps REALISTAS basados en una duración total de 8-12 minutos.

Responde ESTRICTAMENTE en este JSON:
{{
  "titulo": "Título GANCHO de 30-75 caracteres",
  "titulo_alternativo": "Título alternativo",
  "anio_suceso": 1998,
  "palabras_clave": ["keyword1", "keyword2", "keyword3"],
  "palabras_portada": "TEXTO GANCHO 2-3 palabras",
  "descripcion": "Descripción SEO completa",
  "tags": "15-20 tags separados por coma",
  "hashtags": "#Terror #Mexico #RelatosReales (mínimo 5 hashtags relevantes)",
  "miniatura_prompt": "YouTube horror thumbnail 16:9: [escena impactante del relato]",
  "capitulos": [
    {{"tiempo": "00:00", "titulo": "El Comienzo"}},
    {{"tiempo": "02:15", "titulo": "El Encuentro"}},
    {{"tiempo": "05:30", "titulo": "El Clímax"}},
    {{"tiempo": "09:00", "titulo": "La Revelación"}}
  ],
  "texto_completo": "Relato completo de 1400-1600 palabras"
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

                # Validación de gancho (filtro 1 básico)
                if not validar_titulo_gancho(titulo_generado):
                    print(f"⚠️ Título no pasa validación básica: '{titulo_generado}'. Reintentando...")
                    raise ValueError("Título no cumple estándar de gancho")

                # Evaluación de claridad con DeepSeek (filtro 1 extra)
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
                print(f"🏷️ Título GANCHO: {titulo_generado}")
                return data
            else:
                print(f"⚠️ Texto insuficiente ({palabras} palabras). Reintentando en 10s...")
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
# ASIGNAR ETAPAS VISUALES A SEGMENTOS
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
# GENERAR QUERY PARA PEXELS (MEJORADA - INCLUYE ÉPOCA)
# ================================================================
def generar_query_pexels(segmento_texto, etapa, ubicacion_escena):
    prompt = f"""Eres un EXPERTO EN BÚSQUEDA DE FOTOGRAFÍA DE STOCK. Genera SOLO 4-6 palabras clave en inglés para buscar una foto HORIZONTAL (16:9) en Pexels que represente perfectamente esta escena.

ESCENA: "{segmento_texto[:150]}"
ETAPA: {etapa}
UBICACIÓN: {ubicacion_escena}
ÉPOCA: {EPOCA_MOD}

REGLAS:
- Palabras clave separadas por espacio, sin comas.
- Enfócate en: tipo de lugar, ambiente (noche, niebla, lluvia), objetos clave (coche, puerta, etc.), y la época.
- Ejemplos: "abandoned church night fog vintage car", "old house interior darkness 1990s", "lonely road rain night 1980s".

Devuelve SOLO las palabras clave en inglés, sin puntos, sin comillas.
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "max_tokens": 50,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        query = r.json()["choices"][0]["message"]["content"].strip()
        query = re.sub(r'["\']', '', query)
        query = re.sub(r',', ' ', query)
        query = re.sub(r'\s+', ' ', query)
        if len(query.split()) < 3:
            query = "dark night landscape scary"
        print(f"🧠 Query Pexels: '{query}'")
        return query
    except Exception as e:
        print(f"⚠️ Error generando query: {e}. Usando fallback.")
        return "dark night landscape scary"

def generar_query_miniatura_pexels(miniatura_prompt):
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
        return query if len(query) > 5 else "horror night dark landscape vintage"
    except Exception as e:
        return "horror night dark landscape vintage"

# ================================================================
# BUSCAR IMAGEN EN PEXELS (HORIZONTAL)
# ================================================================
ULTIMA_URL_PEXELS = None

def buscar_imagen_pexels(query, orientation="landscape", intentos=3):
    global ULTIMA_URL_PEXELS
    if not PEXELS_VALIDA:
        print("⚠️ Pexels no disponible.")
        return None

    variantes = ["angle", "view", "perspective", "mood", "atmosphere"]
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
                    print("⚠️ No se encontraron fotos para esta consulta.")
            else:
                print(f"⚠️ Error Pexels: {r.status_code} - {r.text[:100]}")
        except requests.exceptions.Timeout:
            print("⏰ Timeout en Pexels. Reintentando...")
        except Exception as e:
            print(f"⚠️ Error conexión Pexels: {e}")
        if intento < intentos - 1:
            print(f"   ⏳ Esperando 5s antes de reintentar...")
            time.sleep(5)

    print("❌ No se pudo obtener imagen de Pexels.")
    return None

def buscar_miniatura_pexels(query, intentos=3):
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": "landscape",
        "per_page": 5,
        "page": random.randint(1, 3)
    }
    for intento in range(intentos):
        try:
            print(f"🔍 Intento {intento+1}/{intentos} buscando miniatura en Pexels: '{query}'...")
            r = requests.get(url, headers=headers, params=params, timeout=25)
            if r.status_code == 200:
                data = r.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    return random.choice(data["photos"])["src"]["large2x"] or random.choice(data["photos"])["src"]["large"]
            else:
                print(f"⚠️ Error Pexels: {r.status_code} - {r.text[:100]}")
        except Exception as e:
            print(f"⚠️ Error conexión Pexels: {e}")
        if intento < intentos - 1:
            print("⏳ Esperando 5s...")
            time.sleep(5)
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
# DIBUJAR TEXTO EN MINIATURA CON PIL (MEJORADA - FILTRO 3)
# ================================================================
def dibujar_texto_miniatura(img_path, texto, output_path):
    """
    Crea una miniatura atractiva con texto grande, sombra y un círculo o rectángulo de fondo.
    """
    colores_texto = [
        (255, 50, 50), (180, 0, 255), (255, 255, 0), (255, 140, 0),
        (255, 255, 255), (0, 0, 0), (0, 200, 255), (255, 0, 200), (50, 255, 50),
    ]
    color_fill = random.choice(colores_texto)
    brillo = sum(color_fill) / 3
    color_outline = (255, 255, 255) if brillo < 128 else (0, 0, 0)

    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arial.ttf"
    ]
    font = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 120)
            break
        except:
            continue
    if font is None:
        font = ImageFont.load_default()

    with Image.open(img_path) as img:
        img = img.convert("RGBA")
        w, h = img.size

        # Texto a dibujar (mayúsculas)
        texto_limpio = texto.upper().strip()
        palabras = texto_limpio.split()
        if len(palabras) > 3:
            mitad = len(palabras) // 2
            linea1 = " ".join(palabras[:mitad])
            linea2 = " ".join(palabras[mitad:])
            lineas = [linea1, linea2]
        else:
            lineas = [texto_limpio]

        # Ajustar tamaño de fuente
        font_size = 120
        for intento in range(5):
            try:
                font = ImageFont.truetype(font_paths[0], font_size)
            except:
                font = ImageFont.load_default()
            max_w = 0
            total_h = 0
            for lin in lineas:
                bbox = ImageDraw.Draw(Image.new('RGBA', (1,1))).textbbox((0,0), lin, font=font)
                w_lin = bbox[2] - bbox[0]
                h_lin = bbox[3] - bbox[1]
                if w_lin > max_w:
                    max_w = w_lin
                total_h += h_lin + 10
            if max_w > w * 0.8:
                font_size = int(font_size * 0.9)
            elif max_w < w * 0.25:
                font_size = int(font_size * 1.1)
            else:
                break

        try:
            font = ImageFont.truetype(font_paths[0], font_size)
        except:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(img)
        y_offset = (h - total_h) // 2
        x_base = int(w * 0.55)

        # Dibujar fondo semitransparente para legibilidad
        rect_width = int(w * 0.4)
        rect_height = total_h + 60
        rect_x = w - rect_width - 20
        rect_y = (h - rect_height) // 2
        draw.rectangle([rect_x, rect_y, w-10, rect_y+rect_height], fill=(0, 0, 0, 150))

        for lin in lineas:
            bbox = draw.textbbox((0,0), lin, font=font)
            w_lin = bbox[2] - bbox[0]
            h_lin = bbox[3] - bbox[1]
            x = x_base + (w - x_base - w_lin) // 2
            y = y_offset

            # Sombra
            for dx in range(-6, 7):
                for dy in range(-6, 7):
                    if dx == 0 and dy == 0:
                        continue
                    if abs(dx) > 4 or abs(dy) > 4:
                        draw.text((x+dx, y+dy), lin, font=font, fill=(0, 0, 0, 180))
                    else:
                        draw.text((x+dx, y+dy), lin, font=font, fill=color_outline)
            draw.text((x, y), lin, font=font, fill=color_fill)
            y_offset += h_lin + 15

        img.convert("RGB").save(output_path, "JPEG", quality=95)
    print(f"✅ Miniatura mejorada con texto '{texto}' guardada en {output_path}")

# ================================================================
# GENERAR AUDIO CON FALLBACK
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
# MONTAR VIDEO HORIZONTAL (1920x1080)
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
                ImageOps.fit(img, (1920, 1080), Image.LANCZOS).save(img_path)
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
# PROCESAR SEGMENTOS (IMÁGENES HORIZONTALES)
# ================================================================
def procesar_segmentos(segmentos, etapas, ubicaciones, offset=0):
    elementos = []
    imagen_ultimo_recurso = None
    for i, seg_texto in enumerate(segmentos):
        idx = offset + i
        etapa = etapas[i] if i < len(etapas) else "lugar_destino"
        ubic = ubicaciones[i] if i < len(ubicaciones) else UBICACION_HISTORIA
        print(f"\n📍 Segmento {idx+1} - Etapa: {etapa} | {ubic}")

        query = generar_query_pexels(seg_texto, etapa, ubic)

        if i > 0:
            time.sleep(3)

        url_img = buscar_imagen_pexels(query, orientation="landscape")
        if url_img:
            imagen_ultimo_recurso = url_img
        else:
            if imagen_ultimo_recurso:
                print(f"⚠️ Reutilizando imagen anterior para segmento {idx+1}.")
                url_img = imagen_ultimo_recurso
            else:
                query_fallback = "mexican night landscape dark"
                url_img = buscar_imagen_pexels(query_fallback, orientation="landscape")
                if url_img:
                    print(f"⚠️ Usando imagen genérica para segmento {idx+1}.")
                    imagen_ultimo_recurso = url_img
                else:
                    continue

        audio_file = generar_audio(seg_texto, idx)
        if not audio_file:
            continue

        elementos.append({"imagen_url": url_img, "audio_path": audio_file})
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

    # Forzar publicación si es workflow_dispatch
    if os.getenv("FORCE_PUBLISH") == "true":
        print("🚀 FORCE_PUBLISH activado: se publicará aunque ya haya video hoy.")
    else:
        estado_musica = cargar_estado_musica()
        if verificar_publicacion_hoy():
            print("✅ Ya se publicó hoy. Saliendo.")
            sys.exit(0)

    # ============================================================
    # 🧠 DECISIÓN DE PUBLICAR (MODO HUMANO)
    # ============================================================
    estado_publicacion = cargar_estado_musica()

    if not deberia_publicar_ahora(estado_publicacion):
        print("⏸️ Decisión: No publicar en esta ejecución.")
        guardar_estado_musica(estado_publicacion)
        sys.exit(0)

    # ============================================================
    # GENERAR VIDEO
    # ============================================================
    print("="*70)
    print("👻 SOMBRAS DE MEDIANOCHE - BOT VIDEOS LARGOS (HORIZONTAL 16:9)")
    print("   ✦ Títulos gancho (validación automática + evaluación de claridad)")
    print("   ✦ Imágenes HORIZONTALES 16:9 para YouTube")
    print("   ✦ Miniaturas con texto mejorado (filtro 3)")
    print("   ✦ Verificación de demanda real en YouTube (filtro 2)")
    print("   ✦ Capítulos con timestamps realistas")
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
    palabras_portada = historia.get("palabras_portada", "LO VI")
    descripcion_base = historia.get("descripcion", f"Relato paranormal.\n{FACEBOOK_LINK}")
    tags_video = historia.get("tags", "relatos, leyendas, mexico")
    hashtags_video = historia.get("hashtags", "#Terror #Mexico #RelatosReales")
    capitulos_video = historia.get("capitulos", [])
    texto_completo = historia.get("texto_completo", "")
    keywords = historia.get("palabras_clave", [])

    # ============================================================
    # 🧠 VERIFICAR DEMANDA REAL (FILTRO 2)
    # ============================================================
    if keywords:
        tema_busqueda = keywords[0]
    else:
        tema_busqueda = titulo_video.split()[0]
    if not verificar_demanda_youtube(tema_busqueda):
        print("⛔ Demanda insuficiente. Cancelando publicación.")
        sys.exit(0)

    # ============================================================
    # CONSTRUIR DESCRIPCIÓN COMPLETA
    # ============================================================
    descripcion_completa = f"""{descripcion_base}

🔴 RELATO COMPLETO en el canal: {CANAL_LINK}
📱 Facebook: {FACEBOOK_LINK}

{hashtags_video}"""

    print(f"\n📊 SEO GENERADO:")
    print(f"   🏷️ Título GANCHO: {titulo_video}")
    print(f"   🖼️ Texto miniatura: {palabras_portada}")
    print(f"   🗓️ Año del suceso: {ANIO_SUCESO if ANIO_SUCESO else 'actualidad'}")
    print(f"   📚 Capítulos: {len(capitulos_video)}")
    print(f"   🔑 Keywords: {keywords}")

    segmentos = dividir_en_segmentos(texto_completo, 55)
    etapas, ubicaciones = asignar_etapas_visuales(segmentos, UBICACION_HISTORIA)
    print(f"\n🎨 {len(segmentos)} segmentos divididos por código (imágenes HORIZONTALES 16:9).")

    elementos_validos = procesar_segmentos(segmentos, etapas, ubicaciones, offset=0)
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
            elems_n = procesar_segmentos(nuevos, etapas_n, ubic_n, offset=len(elementos_validos))
            elementos_validos.extend(elems_n)
            duracion_actual = sum(AudioFileClip(e["audio_path"]).duration for e in elementos_validos)
            intentos_expansion += 1
        else:
            break

    if duracion_actual < DURACION_MINIMA_SEGUNDOS:
        print(f"❌ Duración final insuficiente. Abortando.")
        sys.exit(1)

    print(f"✅ Duración final: {duracion_actual/60:.1f} minutos.")

    # ============================================================
    # 🖼️ GENERAR MINIATURA HORIZONTAL (FILTRO 3)
    # ============================================================
    print("🖼️ Buscando miniatura HORIZONTAL en Pexels y aplicando texto con PIL...")
    miniatura_path = None

    query_miniatura = generar_query_miniatura_pexels(historia.get("miniatura_prompt", "scary horror night dark landscape"))
    miniatura_base_url = buscar_miniatura_pexels(query_miniatura)

    if miniatura_base_url:
        try:
            r = requests.get(miniatura_base_url, timeout=30)
            r.raise_for_status()
            temp_base = "miniatura_base.jpg"
            with open(temp_base, "wb") as f:
                f.write(r.content)
            with Image.open(temp_base) as img:
                img_resized = ImageOps.fit(img, (1280, 720), Image.LANCZOS)
                img_resized.save(temp_base)

            dibujar_texto_miniatura(temp_base, palabras_portada, "miniatura.jpg")
            miniatura_path = "miniatura.jpg"
            print(f"✅ Miniatura HORIZONTAL con texto '{palabras_portada}' generada.")

            if os.path.exists(temp_base):
                os.remove(temp_base)

        except Exception as e:
            print(f"⚠️ Error generando miniatura con PIL: {e}")
            import traceback
            traceback.print_exc()
            try:
                if os.path.exists("miniatura_base.jpg"):
                    with Image.open("miniatura_base.jpg") as img:
                        img.save("miniatura.jpg", "JPEG", quality=85)
                    miniatura_path = "miniatura.jpg"
                    print(f"⚠️ Fallback: miniatura guardada SIN texto")
            except Exception as e2:
                print(f"❌ Fallback también falló: {e2}")
                miniatura_path = None
    else:
        print("❌ No se pudo encontrar la imagen base de la miniatura en Pexels.")
        miniatura_path = None

    # ============================================================
    # MONTAJE Y SUBIDA
    # ============================================================
    print("🎬 Montando video HORIZONTAL (1920x1080)...")
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

    # Marcar publicación exitosa
    estado_publicacion["publicaciones_hoy"] = estado_publicacion.get("publicaciones_hoy", 0) + 1
    estado_publicacion["ultima_publicacion"] = datetime.now(ZoneInfo("America/Mexico_City")).isoformat()
    marcar_publicacion_exitosa()
    guardar_estado_musica(estado_publicacion)

    limpiar_archivos_temporales()
    print("🎉 Proceso completado (video HORIZONTAL 16:9 + miniatura mejorada + filtros de Yayas).")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
