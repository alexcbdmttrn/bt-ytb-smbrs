import asyncio
from datetime import datetime
import json
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
    TextClip,
    CompositeVideoClip,
    AudioClip,
)
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import edge_tts
import pytz

# ================================================================
# CONFIGURACIÓN
# ================================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
AGNES_API_KEY = os.getenv("AGNES_API_KEY")
YOUTUBE_USER_TOKEN = (
    json.loads(os.getenv("YOUTUBE_USER_TOKEN"))
    if os.getenv("YOUTUBE_USER_TOKEN")
    else {}
)

FACEBOOK_LINK = "https://www.facebook.com/profile.php?id=61593237382982"
CANAL_LINK = "https://www.youtube.com/@sombrasdemedianocheoficial"

ESTADO_FILE = "estado_shorts.json"
TITULOS_FILE = "titulos_shorts_publicados.json"
META_DIARIA_SHORTS = 3

# ================================================================
# 🤖 DISCLOSURE DE IA (transparencia)
# ================================================================
ACTIVAR_DISCLOSURE_IA = True
DISCLOSURE_TEXT = "\n\n🤖 Contenido generado con inteligencia artificial (relato e imágenes)."

# ================================================================
# 🎤 VOCES NEURALES VÁLIDAS
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural", "velocidad": "+10%", "tono": "-2Hz"},
    {"voz": "es-MX-DaliaNeural", "velocidad": "+10%", "tono": "+0Hz"},
    {"voz": "es-ES-AlvaroNeural", "velocidad": "+10%", "tono": "-3Hz"},
    {"voz": "es-ES-ElviraNeural", "velocidad": "+10%", "tono": "+1Hz"},
    {"voz": "es-CO-GonzaloNeural", "velocidad": "+10%", "tono": "-1Hz"},
    {"voz": "es-CO-SalomeNeural", "velocidad": "+10%", "tono": "-1Hz"},
    {"voz": "es-AR-ElenaNeural", "velocidad": "+10%", "tono": "+2Hz"},
    {"voz": "es-AR-DiegoNeural", "velocidad": "+10%", "tono": "-2Hz"},
    {"voz": "es-US-AlonsoNeural", "velocidad": "+10%", "tono": "-1Hz"},
    {"voz": "es-US-PalomaNeural", "velocidad": "+10%", "tono": "-1Hz"},
    {"voz": "es-PE-CamilaNeural", "velocidad": "+10%", "tono": "+0Hz"},
    {"voz": "es-PE-AlexNeural", "velocidad": "+10%", "tono": "-1Hz"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+10%", "tono": "-2Hz"},
    {"voz": "es-CL-CatalinaNeural", "velocidad": "+10%", "tono": "+1Hz"},
]
CONFIG_VOZ_ACTUAL = random.choice(VOCES_DISPONIBLES)

# ================================================================
# 🎨 PALETAS MODERNAS 2026
# ================================================================
PALETAS_COLOR = [
    "Cold cyan blue LED fog, navy blue modern shadows, crisp white moonlight",
    "Emerald green twilight, modern city haze, muted sage ambient lighting",
    "Deep violet LED haze, electric purple ambient light, dark magenta shadows",
    "Slate gray modern tones, freezing ice blue highlight, dim overcast ambient",
    "Dark teal and deep blue, modern oceanic midnight, cold misty atmosphere",
    "Stark black and white high contrast, silver moonlight, modern pitch shadows",
    "Desaturated cold film look, moody cinematic lighting, 8k hyperrealistic",
    "Neon purple and electric pink, deep violet shadows, cyberpunk modern lights",
    "Electric yellow and charcoal black, stark contrast, dusty atmospheric haze",
    "Deep crimson red, pitch black shadow, intense orange emergency LED lights",
    "Blood red and burnt orange, modern charcoal shadows, hellish glow",
    "Modern warm amber and dark mahogany, golden LED lighting, deep brown shadows",
    "Fiery sunset orange, deep purple shadows, modern red highlights",
    "Toxic lime green and pitch black, eerie chemical modern glow, radioactive haze",
    "Clean modern daylight, neutral gray ambient, crisp shadows",
    "Modern LED streetlight glow, cool white highlights, urban night atmosphere",
]
PALETA_COLOR_ACTUAL = random.choice(PALETAS_COLOR)

# ================================================================
# 📷 ESTILOS VISUALES MODERNOS 2026
# ================================================================
ESTILOS_VISUALES = [
    "Modern 2026 cinematic photograph, bright contemporary lighting, well-lit scene, sharp focus, current era",
    "Contemporary thriller photography 2026, soft modern ambient diffusion, bright highlights, present day",
    "Modern documentary realistic photo 2026, natural crisp skin texture, current fashion and architecture",
    "8k resolution modern cinematic frame, ultra clear facial details, bright exposure, contemporary era",
    "Modern fashion photography style 2026, dramatic but well-lit, clean skin, current trends",
    "Modern noir style 2026, high contrast but well-exposed, contemporary urban atmosphere",
]
ESTILO_VISUAL_ACTUAL = random.choice(ESTILOS_VISUALES)

# ================================================================
# 🧑 GENERADOR DE PERSONAJES
# ================================================================
def generar_perfil_personaje_shorts():
    edades = ["21-year-old", "28-year-old", "35-year-old", "42-year-old", "50-year-old", "60-year-old"]
    vestimentas = [
        "wearing a modern denim jacket and grey t-shirt",
        "wearing a contemporary dark green coat and wool scarf",
        "wearing a simple white shirt and leather belt",
        "wearing a modern blue mechanic uniform",
        "wearing a dark sweater and slim trousers",
        "wearing a red flannel shirt and modern jeans",
        "wearing a black leather jacket and modern boots",
        "wearing a modern hoodie and baseball cap",
        "wearing a contemporary polo shirt and dark pants",
        "wearing a modern delivery uniform with reflective stripes",
    ]
    cabellos = [
        "short curly dark hair",
        "grey cropped hair",
        "bald with a short beard",
        "short spiky black hair",
        "chestnut brown curly hair",
        "short salt-and-pepper hair",
        "modern fade haircut",
        "contemporary undercut hairstyle",
    ]
    rasgos = [
        "with mestizo features and light olive skin",
        "with light brown skin and freckles",
        "with olive skin and a strong jaw",
        "with pale skin and green eyes",
        "with tan skin and a warm smile",
        "with light beige skin and a serious expression",
    ]
    profesiones_masculinas = [
        "trailero de 35 años conduciendo tráiler moderno 2025 en autopista nocturna",
        "policía de 38 años en su turno nocturno en patrulla moderna",
        "conductor de Uber de 32 años en ciudad contemporánea",
        "repartidor de apps tipo Rappi de 28 años en moto moderna",
        "programador de 30 años trabajando remoto en departamento moderno",
        "fotógrafo de 28 años en edificios contemporáneos",
        "velador de 55 años en condominio residencial moderno",
        "enfermero de 30 años en hospital privado contemporáneo",
        "taxista de 45 años en aeropuerto moderno",
        "guardia de seguridad de 40 años en centro comercial actual",
        "influencer de 25 años grabando contenido en zonas urbanas",
        "carpintero de 45 años en taller moderno con herramientas actuales",
        "mesero de 26 años en restaurante contemporáneo nocturno",
        "paramédico de 33 años en ambulancia moderna",
        "vendedor ambulante de 40 años en calle urbana actual",
    ]
    profesion = random.choice(profesiones_masculinas)
    articulo = "un"
    perfil_fisico = (
        f"a {random.choice(edades)} Mexican man, "
        f"{random.choice(rasgos)}, "
        f"with {random.choice(cabellos)}, {random.choice(vestimentas)}"
    )
    return perfil_fisico, profesion, articulo, "man"

PERFIL_PERSONAJE_SHORTS, PERSONAJE_SHORTS, ARTICULO_SHORTS, GENERO_SHORTS = generar_perfil_personaje_shorts()
ESTADO_HISTORIA_SHORTS = random.choice([
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas",
    "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit",
    "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
    "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"
])

# ================================================================
# 🎵 AUDIO DE FONDO
# ================================================================
FONDOS_DISPONIBLES = [
    "Ash and Marrow.mp3", "Black Maw.mp3", "Cold Hollow.mp3",
    "Hollow Marrow.mp3", "Sunken Dread.mp3", "Sunless Vault.mp3", "The Deep Rot.mp3"
]

def seleccionar_fondo_disponible(estado):
    fondos = FONDOS_DISPONIBLES.copy()
    ultimo_fondo = estado.get("ultimo_fondo")
    if ultimo_fondo and ultimo_fondo in fondos:
        fondos.remove(ultimo_fondo)
        print(f"🎵 Evitando repetir fondo: {ultimo_fondo}")
    random.shuffle(fondos)
    for root, dirs, files in os.walk("."):
        if "/." in root or "\\." in root:
            continue
        for file in files:
            for fondo in fondos:
                if file.lower() == fondo.lower():
                    full_path = os.path.join(root, file)
                    estado["ultimo_fondo"] = fondo
                    print(f"✅ Audio de fondo seleccionado: {full_path}")
                    return full_path
    for root, dirs, files in os.walk("."):
        for file in files:
            for fondo in FONDOS_DISPONIBLES:
                if file.lower() == fondo.lower():
                    full_path = os.path.join(root, file)
                    estado["ultimo_fondo"] = fondo
                    print(f"✅ Audio de fondo (única opción): {full_path}")
                    return full_path
    print("⚠️ No se encontró ningún archivo de fondo disponible.")
    return None

# ================================================================
# 🧼 LIMPIADOR DE PROMPTS (MODERNIDAD 2026)
# ================================================================
def limpiar_prompt_base(prompt, estilo_visual=None, paleta_color=None):
    estilo = estilo_visual or ESTILO_VISUAL_ACTUAL
    paleta = paleta_color or PALETA_COLOR_ACTUAL
    if not prompt:
        prompt = "Modern street at night 2026, bright lighting"
    prompt = re.sub(r"\n+", " ", prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r"[^\x00-\x7F]+", "", prompt)
    
    palabras_antiguas = [
        r"\bgrainy\b", r"\bvhs\b", r"\bchiaroscuro\b", r"\bdirt\b", r"\bgrime\b",
        r"\blemish\b", r"\bspots\b", r"\bterro\b", r"\bhorror\b", r"\bsangre\b",
        r"\bblood\b", r"\bgore\b", r"\bdemacrad[oa]s?\b", r"\bzombies?\b",
        r"\bdisfigured\b", r"\bwounds?\b", r"\bmonster\b",
        r"\brushy\b", r"\brusted\b", r"\boxidized\b", r"\bweathered\b",
        r"\bdecayed\b", r"\brotten\b", r"\brotting\b", r"\bancient\b",
        r"\bvintage\b", r"\bretro\b", r"\bsepia\b", r"\baged\b",
        r"\bdilapidated\b", r"\bdecrepit\b", r"\brundown\b", r"\bcrumbling\b",
        r"\bcracked\b", r"\bpeeling\b", r"\bcrumpled\b", r"\beroded\b",
        r"\bdeteriorated\b", r"\bemaciated\b", r"\bgaunt\b", r"\bcorpselike\b",
        r"\bzombielike\b", r"\bskeletal\b", r"\bdecompos(?:ed|ing)\b",
        r"\bmoldy\b", r"\bmouldy\b", r"\bmusty\b", r"\bdusty\b",
        r"\bcobwebs?\b", r"\bspiders?\s?webs?\b",
        r"\b19[5-9]\d(?:s)?\b", r"\bold[- ]?(?:fashioned|timer)\b",
        r"\bclassic(?:al)?\b", r"\bantique\b", r"\bhistoric(?:al)?\b",
    ]
    for pattern in palabras_antiguas:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)
    
    prompt_base = re.sub(r"\s+", " ", prompt).strip()[:200]
    
    modificadores_modernidad = (
        f", {estilo}, color palette of {paleta}, "
        "vertical 9:16 format, wide environmental establishing shot, medium-wide shot, "
        "subject small in frame or partially visible, scene and location as focal point, "
        "single person, exactly one person, "
        "MODERN 2026 ERA, contemporary setting, present day, current decade, "
        "modern vehicles from 2020-2026, modern architecture, modern clothing, "
        "LED lighting, modern technology visible, smartphones era, "
        "clean well-maintained environments, new or recent buildings, "
        "clean smooth skin, natural facial complexion, healthy appearance, "
        "modern fashion, contemporary hairstyles, current trends, "
        "sharp focus, bright well-lit scene, no dark underexposed areas, "
        "no text, no watermark"
    )
    return prompt_base + modificadores_modernidad

# ================================================================
# 🧹 LIMPIAR CARACTERES ESPECIALES PARA TTS
# ================================================================
def limpiar_caracteres_para_tts(texto):
    texto = re.sub(r'[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9\s.,;:!?¿¡\'\"]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

# ================================================================
# LIMPIAR RESPUESTA JSON
# ================================================================
def limpiar_respuesta_json(respuesta):
    respuesta = re.sub(r"```json\s*", "", respuesta)
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
# 🗂️ ESTADO DE SHORTS
# ================================================================
def cargar_estado():
    try:
        with open(ESTADO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "publicaciones_hoy" not in data:
                data["publicaciones_hoy"] = None
            return data
    except Exception:
        return {"ultimo_fondo": None, "publicaciones_hoy": None}

def guardar_estado(estado):
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "ultimo_fondo": estado.get("ultimo_fondo"),
            "publicaciones_hoy": estado.get("publicaciones_hoy")
        }, f, indent=2, ensure_ascii=False)
    print("✅ Estado de Shorts guardado")

# ================================================================
# 🆕 GESTIÓN DE TÍTULOS PUBLICADOS
# ================================================================
def cargar_titulos_publicados():
    try:
        with open(TITULOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"titulos": []}

def guardar_titulo_publicado(titulo):
    data = cargar_titulos_publicados()
    if titulo not in data["titulos"]:
        data["titulos"].append(titulo)
        with open(TITULOS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Título guardado en registro: '{titulo}'")

def titulo_ya_publicado(titulo):
    data = cargar_titulos_publicados()
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
# 📊 FUNCIONES DE CONTEO DIARIO
# ================================================================
def obtener_publicaciones_hoy():
    estado = cargar_estado()
    pub = estado.get("publicaciones_hoy")
    if not pub:
        return 0
    hoy = datetime.now(pytz.timezone("America/Mexico_City")).strftime("%Y-%m-%d")
    if pub.get("fecha") == hoy:
        return pub.get("cantidad", 0)
    return 0

def incrementar_publicaciones_hoy():
    estado = cargar_estado()
    hoy = datetime.now(pytz.timezone("America/Mexico_City")).strftime("%Y-%m-%d")
    pub = estado.get("publicaciones_hoy")
    if pub and pub.get("fecha") == hoy:
        pub["cantidad"] = pub.get("cantidad", 0) + 1
    else:
        estado["publicaciones_hoy"] = {"fecha": hoy, "cantidad": 1}
    guardar_estado(estado)

# ================================================================
# 🧹 LIMPIAR TEXTO PARA AUDIO
# ================================================================
def limpiar_texto_para_audio(texto):
    texto = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002700-\U000027BF\U000024C2-\U0001F251]', '', texto)
    texto = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', texto)
    texto = texto.replace('"', "'")
    texto = texto.replace('\n', ' ')
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

# ================================================================
# GENERAR PLACEHOLDER LOCAL
# ================================================================
def generar_placeholder_local(texto="Terror", size=(1080, 1920)):
    try:
        img = Image.new("RGB", size, (20, 20, 20))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), texto, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (size[0] - text_w) // 2
        y = (size[1] - text_h) // 2
        draw.text((x, y), texto, fill="red", font=font)
        path = f"placeholder_{random.randint(1000, 9999)}.jpg"
        img.save(path)
        return path
    except Exception as e:
        print(f"⚠️ Error generando placeholder local: {e}")
        return None

# ================================================================
# 🖼️ PORTADA VERTICAL CON TEXTO INTEGRADO (Agnes dibuja el texto)
# ================================================================
def generar_portada_shorts(texto_portada, intentos=4):
    """Genera portada vertical 9:16 con el texto gancho dibujado por Agnes DENTRO del marco."""
    texto_portada = (texto_portada or "LO VI").upper().strip()
    palabras = texto_portada.split()
    if len(palabras) > 3:
        texto_portada = " ".join(palabras[:3])
    
    ubicacion = ESTADO_HISTORIA_SHORTS
    paleta = PALETA_COLOR_ACTUAL
    
    prompt_final = f"""YouTube Shorts horror cover, vertical 9:16: extreme close-up of a terrified Mexican face with wide scared eyes and open mouth screaming silently, behind a dark ghostly silhouette with glowing red eyes, set in {ubicacion} at night, high contrast dramatic lighting, saturated deep red and black color grading, cinematic horror style, sharp focus, color palette of {paleta}, modern 2026 era.

TEXT OVERLAY (CRITICAL REQUIREMENT):
- Render the EXACT Spanish text: "{texto_portada}"
- Style: huge bold capital letters, bright yellow fill, thick black outline, subtle drop shadow
- Position: BOTTOM CENTER of the vertical frame, over a dark clean area, keeping the terrified face visible at the top
- The text MUST fit entirely INSIDE the vertical frame with safe margins on all sides: never cut off, never overflowing, never touching the edges, never rotated
- Spelling MUST be EXACT, character by character: "{texto_portada}". NO typos, NO extra letters, NO missing letters, NO distorted characters
- Maximum 2 lines, centered horizontally

NO other text, NO watermarks, NO logos."""
    
    negative = (
        "misspelled text, wrong spelling, typo, distorted letters, garbled text, broken characters, "
        "cut off text, text outside frame, text touching edges, overflowing text, oversized text, "
        "text rotated, text sideways, text at top covering face, "
        "multiple people, duplicate people, cloned faces, deformed, mutated, bad anatomy, "
        "asymmetrical eyes, uncanny valley, gore, blood, wounds, zombie-like, corpse-like, "
        "rusty, vintage, retro, antique, dilapidated, sepia, monochrome, "
        "low quality, blurry, watermark, logo"
    )
    
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_final[:1000],
        "negative_prompt": negative,
        "width": 1080,
        "height": 1920,
        "num_images": 1
    }
    for intento in range(intentos):
        try:
            print(f"🖼️ Intento {intento+1}/{intentos} portada vertical con texto '{texto_portada}'...")
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code == 200:
                return r.json()["data"][0]["url"]
        except Exception as e:
            print(f"⚠️ Error portada: {e}")
        time.sleep(6)
    return None

# ================================================================
# 🆕 EXPANDIR TEXTO CORTO
# ================================================================
def expandir_texto_corto(texto_corto, ubicacion, personaje):
    print("🔄 Expandiendo texto corto...")
    prompt = f"""Eres un editor de testimonios paranormales reales. Expande el siguiente
relato para que tenga entre 150 y 170 palabras.
Añade más detalles sensoriales y específicos (sonidos, olores, lugares reales de {ubicacion},
horas, objetos) como los que incluiría una persona contando su experiencia real.
Mantén la trama y el tono coloquial exactamente iguales.
NO agregues ningún llamado a suscribirse ni CTA.

RELATO ORIGINAL:
{texto_corto}

Devuelve SOLO el relato expandido (150-170 palabras).
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 700,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        texto_expandido = r.json()["choices"][0]["message"]["content"].strip()
        if len(texto_expandido.split()) > 130:
            return texto_expandido
        else:
            return texto_corto + " El miedo crecía con cada paso. El silencio era ensordecedor."
    except Exception as e:
        print(f"❌ Error expandiendo: {e}")
        return texto_corto

# ================================================================
# TRUNCAR TEXTO LARGO
# ================================================================
def truncar_texto_largo(texto, max_palabras=170):
    palabras = texto.split()
    if len(palabras) <= max_palabras:
        return texto
    for i in range(max_palabras, max_palabras - 30, -1):
        if i < len(palabras) and palabras[i-1].endswith(('.', '!', '?')):
            return ' '.join(palabras[:i])
    return ' '.join(palabras[:max_palabras])

# ================================================================
# 🎬 GENERAR HISTORIA CON SEO EXPERTO + ETAPAS VISUALES
# ================================================================
def generar_historia_completa():
    titulos_pub = cargar_titulos_publicados()["titulos"][-10:]
    titulos_referencia = "\n".join([f"- {t}" for t in titulos_pub]) if titulos_pub else "Ninguno aún."

    prompt = f"""Eres un CURADOR Y ADAPTADOR DE RELATOS PARANORMALES REALES de internet, especializado en continuidad visual cinematográfica y EXPERTO EN SEO PARA YOUTUBE SHORTS 2026.

🚨 REGLA DE ORO:
La historia DEBE estar basada en un relato que REALMENTE alguien contó en internet.
Adáptalo en primera persona, tono coloquial, ambientado en {ESTADO_HISTORIA_SHORTS}, México.

🎯 REGLA CRÍTICA: CONTINUIDAD VISUAL NARRATIVA
El relato se dividirá en 4-5 segmentos visuales. Cada segmento DEBE tener:
- "etapa_visual": una de estas 5 etapas:
  * "inicio_casa" (el personaje en su espacio seguro)
  * "desplazamiento" (en movimiento: caminando, en auto, en moto)
  * "lugar_destino" (llega al lugar de los hechos)
  * "climax_evento" (ocurre el evento paranormal)
  * "resolucion" (conclusión o regreso)
- "ubicacion_escena": el lugar específico donde ocurre ese fragmento
- Las escenas deben tener TRAYECTORIA LÓGICA
- El entorno se mantiene coherente durante segmentos consecutivos

PROTAGONISTA: {ARTICULO_SHORTS} {PERSONAJE_SHORTS}.
AMBIENTACIÓN ACTUAL 2026: tecnología moderna, vehículos actuales, ropa moderna.

🎯 REGLA CRÍTICA DE LONGITUD:
- EXACTAMENTE entre 150 y 170 palabras.
- Duración narrada: 50-65 segundos a velocidad +10%.

📐 ESTRUCTURA:
1. GANCHO (5-10 palabras)
2. CONTEXTO (20-30 palabras)
3. TENSIÓN (80-90 palabras)
4. TWIST FINAL (30-40 palabras)

🎯 REGLA CRÍTICA 1: TÍTULO SEO DE ALTO CTR (lo más importante)
FÓRMULA: [VERBO EN 1RA PERSONA / PALABRA DE IMPACTO] + [LUGAR ESPECÍFICO] + [GANCHO EMOCIONAL]
✅ EJEMPLOS:
- "Vi algo en la carretera de Zacatecas que no era humano"
- "Escuché mi nombre en un pueblo abandonado de Puebla"
- "El Uber me dejó en un lugar que no existe en el mapa"
- "Trabajé de velador 1 noche en Monterrey. No volví jamás."
❌ PROHIBIDOS: "La leyenda de...", "El fantasma de...", "Una noche en...", "El misterio de..."
Longitud: 55-75 caracteres, primera persona, lugar específico de {ESTADO_HISTORIA_SHORTS}.

🎯 REGLA CRÍTICA 2: PALABRAS DE PORTADA (texto gancho del primer frame)
"palabras_portada": TEXTO GANCHO de 2-3 palabras emocionales ESPECÍFICO del relato.
✅ EJEMPLOS: "LO VI EN EL ESPEJO", "NO ESTABA SOLO", "ME SIGUIÓ", "NO ERA HUMANO", "3:33 AM", "NO ENTRES", "JAMÁS VOLVÍ"
❌ NUNCA uses: "CASO REAL", "TERROR", "MISTERIO" (genéricos)

🎯 REGLA CRÍTICA 3: DESCRIPCIÓN CON SEO EXPERTO
Línea 1 (GANCHO, máx 90 chars): keyword principal + {ESTADO_HISTORIA_SHORTS}
Línea 2 (CONTEXTO): keywords long-tail
Línea 3 (CTA): "🔴 RELATO COMPLETO en el canal: {CANAL_LINK}"
Línea 4 (FUENTE): "📖 Basado en un testimonio real compartido en internet."
Línea 5 (FACEBOOK): "📱 Síguenos: {FACEBOOK_LINK}"
Línea 6 (HASHTAGS): máx 5

🎯 REGLA CRÍTICA 4: TAGS SEO (10-15, máx 480 chars)
- 2-3 específicos del lugar y fenómeno
- 4-5 long-tail
- 3-4 tendencia
- 2-3 geográficos

🎯 REGLA CRÍTICA 5: PALABRAS CLAVE (2-3)
🎯 REGLA CRÍTICA 6: TÍTULO ALTERNATIVO (A/B testing)

🚫 TÍTULOS YA PUBLICADOS (NO REPETIR NI PARECERSE):
{titulos_referencia}

REGLAS GENERALES:
- PRIMERA FRASE = GANCHO IMPACTANTE de máximo 5 palabras.
- Ortografía perfecta. NO repitas frases.
- PALETA: {PALETA_COLOR_ACTUAL}
- "texto_completo" NO debe incluir CTA de suscripción.

Devuelve ESTRICTAMENTE este JSON válido:
{{
  "titulo": "Título SEO 1ra persona, 55-75 caracteres",
  "titulo_alternativo": "Segundo título con ángulo diferente",
  "palabras_clave": ["keyword 1", "keyword 2", "keyword 3"],
  "gancho_descripcion": "Gancho de máx 90 caracteres (primera línea de descripción)",
  "contexto_descripcion": "1 oración con contexto y keywords",
  "fuente_relato": "Basado en un testimonio/leyenda real de ...",
  "texto_completo": "Micro-relato REAL, 150-170 palabras, primera persona, coloquial",
  "palabras_portada": "TEXTO GANCHO 2-3 palabras específicas del relato",
  "tags": "10-15 tags separados por coma (máximo 480 caracteres)"
}}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 1100,
        "response_format": {"type": "json_object"}
    }

    for intento in range(6):
        try:
            print(f"🔄 Intento {intento+1}/6 generando historia real...")
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            r.raise_for_status()

            finish_reason = r.json()["choices"][0].get("finish_reason", "unknown")
            print(f"   📊 finish_reason: {finish_reason}")

            respuesta = r.json()["choices"][0]["message"]["content"].strip()
            print(f"   📝 Respuesta cruda (primeros 300 chars): {respuesta[:300]}...")

            json_str = limpiar_respuesta_json(respuesta)

            try:
                data = json.loads(json_str, strict=False)
                print("   ✅ JSON parseado correctamente con json.loads")
            except json.JSONDecodeError as e:
                print(f"   ⚠️ json.loads falló: {e}")
                try:
                    import json5
                    data = json5.loads(json_str)
                    print("   ✅ JSON parseado correctamente con json5 (fallback)")
                except ImportError:
                    print("   ❌ json5 no está instalado.")
                    raise
                except Exception as e2:
                    print(f"   ❌ json5 también falló: {e2}")
                    raise

            if "texto_completo" not in data or len(data["texto_completo"]) < 100:
                raise ValueError("Texto demasiado corto o campo faltante")

            data["texto_completo"] = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', data["texto_completo"])
            data["texto_completo"] = re.sub(r'\n{3,}', '\n\n', data["texto_completo"])

            titulo = data.get("titulo", "").strip()
            titulo = re.sub(r'#\w+', '', titulo).strip()
            titulo = ' '.join(titulo.split())
            
            if len(titulo) < 40:
                titulo = f"{titulo} - Testimonio real en {ESTADO_HISTORIA_SHORTS}"
            if len(titulo) > 95:
                recorte = titulo[:92].rsplit(' ', 1)[0]
                titulo = recorte + "..."
            data["titulo"] = titulo

            if titulo_ya_publicado(titulo):
                print(f"   ⚠️ Título YA PUBLICADO: '{titulo}'. Regenerando...")
                raise ValueError("Título duplicado")

            gancho = data.get("gancho_descripcion", "").strip()
            if not gancho or len(gancho) > 110:
                gancho = f"Esto fue lo que viví en {ESTADO_HISTORIA_SHORTS} y nunca pude explicar"[:100]
            data["gancho_descripcion"] = gancho

            contexto = data.get("contexto_descripcion", "").strip()
            if not contexto:
                contexto = f"Un testimonio real de fenómenos paranormales ocurrido en {ESTADO_HISTORIA_SHORTS}, México."
            data["contexto_descripcion"] = contexto

            fuente = data.get("fuente_relato", "").strip()
            if not fuente:
                fuente = "Basado en un testimonio real compartido en internet."
            data["fuente_relato"] = fuente

            tags_raw = data.get("tags", "")
            tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
            tags_list = tags_list[:15]

            extras_long_tail = [
                f"terror en {ESTADO_HISTORIA_SHORTS.lower()}",
                f"relatos reales de terror en {ESTADO_HISTORIA_SHORTS.lower()}",
                "testimonios paranormales reales",
                "historias reales contadas en primera persona",
                "leyendas urbanas mexicanas reales",
                "relatos de internet reales",
                "casos paranormales reales mexico",
                "historias de fantasmas reales",
                "shorts terror",
            ]
            i = 0
            while len(tags_list) < 10 and i < len(extras_long_tail):
                if extras_long_tail[i] not in tags_list:
                    tags_list.append(extras_long_tail[i])
                i += 1

            tags_final = []
            total_chars = 0
            for t in tags_list:
                costo = len(t) + 2
                if total_chars + costo > 480:
                    break
                tags_final.append(t)
                total_chars += costo
            data["tags"] = ", ".join(tags_final)

            hashtags_descripcion = "#Shorts #TerrorEn" + ESTADO_HISTORIA_SHORTS.replace(" ", "") + " #RelatosReales #Paranormal #MiedoReal"
            data["hashtags_descripcion"] = hashtags_descripcion

            print(f"   🏷️ Título SEO: {data['titulo']} ({len(data['titulo'])} chars)")
            print(f"   🖼️ Portada: {data.get('palabras_portada', 'N/A')}")
            print(f"   🔑 Keywords: {data.get('palabras_clave', [])}")
            print(f"   📖 Fuente: {data['fuente_relato']}")
            print(f"   🏷️ Tags generados: {len(tags_final)}")
            
            return data

        except Exception as e:
            print(f"❌ Intento {intento+1}/6 falló: {e}")
            if intento < 5:
                espera = 10 + intento * 5
                print(f"⏳ Esperando {espera}s antes de reintentar...")
                time.sleep(espera)

    print("❌ TODOS LOS INTENTOS DE GENERACIÓN FALLARON.")
    sys.exit(1)

# ================================================================
# 🆕 DIVIDIR TEXTO POR ORACIONES
# ================================================================
def dividir_en_segmentos(texto, max_palabras_por_segmento=45):
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
# 🎬 ASIGNAR ETAPAS VISUALES A SEGMENTOS
# ================================================================
def asignar_etapas_visuales(segmentos, ubicacion):
    n = len(segmentos)
    etapas = []
    ubicaciones = []
    
    for i in range(n):
        progreso = i / max(n - 1, 1)
        
        if progreso < 0.2:
            etapa = "inicio_casa"
            ubic = f"interior del hogar moderno en {ubicacion}"
        elif progreso < 0.4:
            etapa = "desplazamiento"
            ubic = f"calle o vehículo moderno en movimiento, {ubicacion}"
        elif progreso < 0.65:
            etapa = "lugar_destino"
            ubic = f"lugar específico del suceso en {ubicacion}"
        elif progreso < 0.85:
            etapa = "climax_evento"
            ubic = f"mismo lugar del suceso en {ubicacion}, momento del evento"
        else:
            etapa = "resolucion"
            ubic = f"salida o regreso desde el lugar, {ubicacion}"
        
        etapas.append(etapa)
        ubicaciones.append(ubic)
    
    return etapas, ubicaciones

# ================================================================
# 🎨 GENERAR PROMPT DE IMAGEN CON MEMORIA VISUAL
# ================================================================
def generar_prompt_con_contexto(segmento_texto, etapa, ubicacion_escena, segmento_anterior_texto=None, perfil=None, estilo_visual=None, paleta_color=None):
    estilo = estilo_visual or ESTILO_VISUAL_ACTUAL
    paleta = paleta_color or PALETA_COLOR_ACTUAL
    perfil = perfil or PERFIL_PERSONAJE_SHORTS
    
    contexto_previo = ""
    if segmento_anterior_texto:
        contexto_previo = f"\nPREVIOUS SCENE: The character was just in the previous moment: '{segmento_anterior_texto[:120]}'"
    
    instrucciones_etapa = {
        "inicio_casa": "Show the character in a modern home interior, establishing shot, calm atmosphere before the events begin.",
        "desplazamiento": "Show the character in movement (walking or driving), same route continuing from the previous scene, different camera angle.",
        "lugar_destino": "Show the character arriving at or exploring the specific location, maintaining architectural consistency.",
        "climax_evento": "Show the paranormal event happening in this exact location, character reacting but NOT in close-up face.",
        "resolucion": "Show the aftermath or the character leaving, calmer atmosphere, conclusion."
    }
    instruccion = instrucciones_etapa.get(etapa, instrucciones_etapa["lugar_destino"])
    
    prompt = f"""Eres un director de fotografía experto en composición cinematográfica y continuidad narrativa.

Fragmento del relato actual:
\"\"\"
{segmento_texto}
\"\"\"
{contexto_previo}

Genera un PROMPT DE IMAGEN EN INGLÉS para una foto vertical (9:16) que represente esta escena.

SCENE CONTINUITY INSTRUCTIONS:
- Current narrative stage: {etapa}
- Current location: {ubicacion_escena}
- DIRECTIVE: {instruccion}

Reglas estrictas de composición:
- PLANO: Wide shot o extreme wide shot. PROHIBIDO close-up, portrait, headshot.
- Enfoque principal: el ENTORNO y la acción del momento.
- Personaje: {perfil}, ocupando como MÁXIMO el 20% del área, a distancia.
- Si solo describe ambiente, NO incluyas personas.
- Estilo: professional hyperrealistic photography, 4k, ultra-detailed, natural lighting.
- Paleta de color: {paleta}
- ERA MODERNA 2026: edificios modernos, vehículos 2020-2026, iluminación LED, ropa actual.
- PROHIBIDO: abandoned, decaying, rusty, rusted, crumbling, cracked, peeling, weathered, dilapidated, vintage, antique, sepia, emaciated, gaunt, corpse-like, zombie-like, rotting, moldy, cobwebs.
- Si la escena requiere un lugar "abandonado", descríbelo como un edificio moderno RECIENTEMENTE cerrado (concreto limpio, ventanas modernas, luces LED de emergencia).

VISUAL CONSISTENCY RULES:
- EXACTLY ONE PERSON (the main character)
- NO cut-off bodies, NO partial bodies, NO limbs outside frame
- NO multiple people, NO duplicate figures
- NO floating objects, NO illogical elements

Devuelve SOLO el prompt en inglés, sin explicaciones.
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "max_tokens": 300,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        prompt_imagen = r.json()["choices"][0]["message"]["content"].strip()
        prompt_imagen += f", {estilo}, vertical 9:16, wide establishing shot, person occupies max 20% of frame, environment as main subject, no close-up face, no portrait, no blood, no gore, modern 2026 era, contemporary setting, no rusty, no vintage, no decayed, single person only, no cut off body"
        return prompt_imagen
    except Exception as e:
        print(f"⚠️ Error generando prompt de imagen: {e}")
        return f"Wide establishing shot of modern {ubicacion_escena} in 2026, depicting: {segmento_texto[:100]}, {estilo}, vertical 9:16, no close-up face, environment as main subject, contemporary era, single person, no cut off body"

# ================================================================
# 🖼️ GENERAR IMAGEN VERTICAL (negative prompt anti-defectos)
# ================================================================
def generar_imagen_vertical(prompt, intentos=3):
    prompt_limpio = limpiar_prompt_base(prompt, ESTILO_VISUAL_ACTUAL, PALETA_COLOR_ACTUAL)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    
    negative = (
        "multiple people, duplicate people, cloned faces, two people, three people, crowd, "
        "cut off body, cropped body, partial body, limbs outside frame, truncated person, "
        "deformed, mutated, bad anatomy, extra limbs, extra fingers, missing limbs, missing fingers, "
        "asymmetrical eyes, cross-eyed, malformed features, uncanny valley, "
        "close-up face, portrait, headshot, person filling frame, face occupying more than 20% of image, "
        "centered subject, camera pointed directly at face, "
        "gore, blood, bloody, wounds, cuts, bruises, gaunt, emaciated, "
        "sickly, decayed skin, rotting, zombie-like, corpse-like, grotesque, ugly, unattractive, "
        "rusty, rusted, oxidized, weathered, aged, vintage, retro, antique, old-fashioned, "
        "dilapidated, decrepit, run-down, crumbling, cracked walls, peeling paint, eroded, "
        "deteriorated, abandoned ruins, moldy, mouldy, musty, dusty, cobwebs, spiderwebs, "
        "classic car, old car, vintage car, retro car, horse carriage, "
        "1950s, 1960s, 1970s, 1980s, 1990s, ancient, medieval, historical, "
        "sepia tone, monochrome, black and white, film grain, "
        "floating objects, illogical elements, impossible physics, "
        "ghost doubles, transparent figures, multiple versions of same person, "
        "over-saturated, oversharpened, low quality, blurry, text, watermark, logo, "
        "broken, shattered, destroyed, post-apocalyptic, dystopian ruins"
    )
    
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_limpio,
        "negative_prompt": negative,
        "width": 1080,
        "height": 1920,
        "num_images": 1
    }
    for _ in range(intentos):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code == 200:
                return r.json()["data"][0]["url"]
            time.sleep(6)
        except Exception:
            time.sleep(6)
    return None

# ================================================================
# 🎬 GENERAR RECURSOS POR SEGMENTO
# ================================================================
def generar_recursos_por_segmento(segmentos, etapas, ubicaciones, perfil, ubicacion, estilo, paleta, intentos_por_imagen=3):
    resultados_temporales = []

    for idx, seg in enumerate(segmentos):
        etapa = etapas[idx] if idx < len(etapas) else "lugar_destino"
        ubic_escena = ubicaciones[idx] if idx < len(ubicaciones) else ubicacion
        
        print(f"  🎬 Segmento {idx+1}/{len(segmentos)} ({len(seg.split())} palabras) - Etapa: {etapa}")
        print(f"     📍 Ubicación: {ubic_escena}")

        seg_anterior = segmentos[idx-1] if idx > 0 else None
        
        prompt_imagen = generar_prompt_con_contexto(
            segmento_texto=seg,
            etapa=etapa,
            ubicacion_escena=ubic_escena,
            segmento_anterior_texto=seg_anterior,
            perfil=perfil,
            estilo_visual=estilo,
            paleta_color=paleta
        )
        print(f"    📝 Prompt generado: {prompt_imagen[:100]}...")

        img_url = None
        for intento in range(intentos_por_imagen):
            try:
                img_url = generar_imagen_vertical(prompt_imagen, intentos=1)
                if img_url:
                    print(f"    ✅ Imagen generada (intento {intento+1})")
                    break
            except Exception:
                pass
            if intento < intentos_por_imagen - 1:
                print(f"    ⏳ Reintentando imagen...")
                time.sleep(6)

        if not img_url:
            print(f"    ⚠️ Imagen falló, se usará la siguiente imagen disponible")

        audio_path = generar_audio(seg, f"seg_{idx}")
        if not audio_path:
            print(f"    ❌ Falló audio para segmento {idx+1}. Abortando...")
            return None

        try:
            audio_clip = AudioFileClip(audio_path)
            duracion = audio_clip.duration
            audio_clip.close()
        except Exception as e:
            print(f"    ⚠️ Error midiendo duración: {e}. Usando estimación de 10s.")
            duracion = 10.0

        resultados_temporales.append({
            "imagen_url": img_url,
            "audio_path": audio_path,
            "duracion": duracion
        })

        if idx < len(segmentos) - 1:
            print(f"    ⏳ Esperando 12 segundos antes del siguiente segmento...")
            time.sleep(12)

    print("\n  🔄 Reparando imágenes fallidas...")
    for i, res in enumerate(resultados_temporales):
        if res["imagen_url"] is None:
            siguiente_imagen = None
            for j in range(i + 1, len(resultados_temporales)):
                if resultados_temporales[j]["imagen_url"] is not None:
                    siguiente_imagen = resultados_temporales[j]["imagen_url"]
                    print(f"    🔄 Segmento {i+1} usando imagen del segmento {j+1}")
                    break

            if siguiente_imagen is not None:
                res["imagen_url"] = siguiente_imagen
            else:
                if i > 0 and resultados_temporales[i-1]["imagen_url"] is not None:
                    res["imagen_url"] = resultados_temporales[i-1]["imagen_url"]
                    print(f"    🔄 Segmento {i+1} usando imagen del segmento anterior")
                else:
                    img_url = generar_placeholder_local("Terror", (1080, 1920))
                    if not img_url:
                        img_url = "https://via.placeholder.com/1080x1920/1a1a1a/ff0000?text=Terror"
                    res["imagen_url"] = img_url
                    print(f"    ⚠️ Segmento {i+1}: usando placeholder")

    return resultados_temporales

# ================================================================
# ✅ GENERAR AUDIO - CON FALLBACK ENTRE VOCES NEURALES
# ================================================================
def generar_audio(texto, index, intentos_por_voz=2):
    global CONFIG_VOZ_ACTUAL
    
    texto_limpio = re.sub(r"imagen_prompt.*", "", texto, flags=re.IGNORECASE).strip()
    texto_limpio = limpiar_caracteres_para_tts(texto_limpio)
    texto_limpio = limpiar_texto_para_audio(texto_limpio)

    if len(texto_limpio) < 30:
        print(f"⚠️ Texto corto ({len(texto_limpio)} caracteres). Rellenando...")
        texto_limpio = "Esa noche en la carretera, el silencio era tan denso que podía cortarse con un cuchillo. El miedo lo envolvía todo. No podía escapar."

    if not texto_limpio:
        return None

    filename = f"audio_short_{index}.mp3"

    voces_a_probar = [CONFIG_VOZ_ACTUAL]
    for voz_config in VOCES_DISPONIBLES:
        if voz_config["voz"] != CONFIG_VOZ_ACTUAL["voz"]:
            voces_a_probar.append(voz_config)
    
    print(f"🔊 Generando audio para segmento {index}. Probando hasta {len(voces_a_probar)} voces neurales...")

    for intento_voz, voz_config in enumerate(voces_a_probar):
        voz = voz_config["voz"]
        rate = voz_config["velocidad"]
        pitch = voz_config["tono"]
        
        print(f"🎤 Intento {intento_voz+1}/{len(voces_a_probar)} con voz: {voz}")
        
        for intento in range(intentos_por_voz):
            async def _generar():
                communicate = edge_tts.Communicate(texto_limpio, voz, rate=rate, pitch=pitch)
                await communicate.save(filename)

            try:
                asyncio.run(_generar())
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    print(f"✅ Audio segmento {index} generado con {voz}")
                    
                    if voz != CONFIG_VOZ_ACTUAL["voz"]:
                        print(f"🔄 Voz principal cambiada de {CONFIG_VOZ_ACTUAL['voz']} a {voz}")
                        CONFIG_VOZ_ACTUAL = voz_config
                    
                    return filename
            except Exception as e:
                print(f"❌ Falló con {voz}: {e}")
                if intento < intentos_por_voz - 1:
                    espera = 3 * (intento + 1)
                    print(f"⏳ Esperando {espera}s antes de reintentar con la misma voz...")
                    time.sleep(espera)
        
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass
    
    print("❌ TODAS las voces neurales de Edge TTS fallaron. Abortando generación de audio.")
    return None

# ================================================================
# ✅ GENERAR AUDIO CTA FINAL
# ================================================================
def generar_audio_cta_final():
    global CONFIG_VOZ_ACTUAL
    
    cta_texto = "Relatos completos en el canal. Visítanos."
    filename = "audio_cta_final.mp3"
    
    voces_a_probar = [CONFIG_VOZ_ACTUAL]
    for voz_config in VOCES_DISPONIBLES:
        if voz_config["voz"] != CONFIG_VOZ_ACTUAL["voz"]:
            voces_a_probar.append(voz_config)
    
    print(f"🔊 Generando audio CTA final. Probando hasta {len(voces_a_probar)} voces neurales...")
    
    for intento_voz, voz_config in enumerate(voces_a_probar):
        voz = voz_config["voz"]
        rate = voz_config["velocidad"]
        pitch = voz_config["tono"]
        
        print(f"🎤 CTA - Intento {intento_voz+1}/{len(voces_a_probar)} con voz: {voz}")
        
        async def _generar():
            communicate = edge_tts.Communicate(cta_texto, voz, rate=rate, pitch=pitch)
            await communicate.save(filename)
        
        try:
            asyncio.run(_generar())
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"✅ Audio CTA final generado con voz: {voz}")
                
                if voz != CONFIG_VOZ_ACTUAL["voz"]:
                    print(f"🔄 Voz principal cambiada de {CONFIG_VOZ_ACTUAL['voz']} a {voz}")
                    CONFIG_VOZ_ACTUAL = voz_config
                
                return filename
        except Exception as e:
            print(f"❌ CTA falló con {voz}: {e}")
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except:
                    pass
    
    print("❌ No se pudo generar audio CTA con ninguna voz neural.")
    return None

# ================================================================
# MONTAR VIDEO CON TRANSICIONES SUAVES
# ================================================================
def montar_video_shorts(recursos_por_segmento, fondo_path, salida="short_final.mp4"):
    if not recursos_por_segmento:
        raise ValueError("No hay recursos para montar el video")

    clips_video = []
    clips_audio = []

    for i, recurso in enumerate(recursos_por_segmento):
        img_url = recurso["imagen_url"]
        audio_path = recurso["audio_path"]
        duracion = recurso["duracion"]

        try:
            audio_clip = AudioFileClip(audio_path)
            clips_audio.append(audio_clip)
        except Exception as e:
            print(f"⚠️ Error cargando audio segmento {i}: {e}")
            raise ValueError(f"Fallo al cargar audio del segmento {i}")

        try:
            if img_url.startswith("http"):
                r = requests.get(img_url, timeout=30)
                r.raise_for_status()
                img_path = f"temp_short_{i}.jpg"
                with open(img_path, "wb") as f:
                    f.write(r.content)
            else:
                img_path = img_url

            with Image.open(img_path) as img:
                img_fitted = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
                img_fitted.save(img_path)

            video_clip = ImageClip(img_path).set_duration(duracion)
            clips_video.append(video_clip)
        except Exception as e:
            print(f"⚠️ Error procesando imagen {i}: {e}")
            placeholder = generar_placeholder_local(f"Img {i+1}")
            if placeholder:
                with Image.open(placeholder) as img:
                    img_fitted = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
                    img_fitted.save(placeholder)
                video_clip = ImageClip(placeholder).set_duration(duracion)
                clips_video.append(video_clip)
            else:
                continue

    if not clips_video:
        raise ValueError("No se pudieron crear clips de video")

    PAUSA_ENTRE_SEGMENTOS = 0.3
    
    if len(clips_audio) > 1:
        audio_con_pausas = []
        for i, audio in enumerate(clips_audio):
            audio_con_pausas.append(audio)
            if i < len(clips_audio) - 1:
                silencio = AudioClip(lambda t: 0, duration=PAUSA_ENTRE_SEGMENTOS)
                audio_con_pausas.append(silencio)
        audio_narracion = concatenate_audioclips(audio_con_pausas)
    else:
        audio_narracion = clips_audio[0]

    video = concatenate_videoclips(clips_video, method="compose")
    
    cta_audio_path = generar_audio_cta_final()
    if cta_audio_path and os.path.exists(cta_audio_path):
        try:
            cta_clip = AudioFileClip(cta_audio_path)
            silencio_antes_cta = AudioClip(lambda t: 0, duration=0.5)
            audio_narracion = concatenate_audioclips([audio_narracion, silencio_antes_cta, cta_clip])
            
            duracion_cta = cta_clip.duration + 0.5
            ultimo_clip = clips_video[-1]
            ultimo_clip = ultimo_clip.set_duration(ultimo_clip.duration + duracion_cta)
            clips_video[-1] = ultimo_clip
            
            video = concatenate_videoclips(clips_video, method="compose")
            print(f"✅ CTA final agregado ({duracion_cta:.1f}s adicionales)")
        except Exception as e:
            print(f"⚠️ Error agregando CTA final: {e}")
    
    duracion_total = audio_narracion.duration

    if fondo_path and os.path.exists(fondo_path):
        try:
            fondo_clip = AudioFileClip(fondo_path)
            if fondo_clip.duration < duracion_total:
                veces = int(duracion_total / fondo_clip.duration) + 1
                fondo_clip = concatenate_audioclips([fondo_clip] * veces)
            fondo_clip = fondo_clip.subclip(0, duracion_total).volumex(0.08)
            audio_final = CompositeAudioClip([audio_narracion, fondo_clip])
        except Exception as e:
            print(f"⚠️ Error en audio de fondo: {e}")
            audio_final = audio_narracion
    else:
        audio_final = audio_narracion

    video = video.set_audio(audio_final)
    video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")

    video.close()
    audio_final.close()
    audio_narracion.close()
    for c in clips_video:
        c.close()
    for a in clips_audio:
        a.close()
    if 'fondo_clip' in locals():
        fondo_clip.close()
    if cta_audio_path and os.path.exists(cta_audio_path):
        try:
            os.remove(cta_audio_path)
        except:
            pass

    print(f"✅ Short vertical creado: {salida}")
    return salida

# ================================================================
# 🆕 SUBIR A YOUTUBE
# ================================================================
def subir_a_youtube(video_path, titulo, etiquetas, gancho_descripcion, contexto_descripcion, hashtags_descripcion, fuente_relato=""):
    try:
        creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
        youtube = build("youtube", "v3", credentials=creds)
    except Exception as e:
        print(f"❌ Error autenticando con YouTube: {e}")
        if "invalid_grant" in str(e) or "expired" in str(e):
            print("🔴 El token de YouTube ha expirado. Debes renovar YOUTUBE_USER_TOKEN.")
        sys.exit(1)

    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]

    descripcion = f"""{gancho_descripcion}

{contexto_descripcion}

🔴 RELATO COMPLETO en el canal: {CANAL_LINK}

📖 {fuente_relato}

📱 Facebook: {FACEBOOK_LINK}

{hashtags_descripcion}"""

    # 🆕 Agregar disclosure de IA si está activado
    if ACTIVAR_DISCLOSURE_IA:
        descripcion += DISCLOSURE_TEXT

    body = {
        "snippet": {
            "title": titulo,
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
    try:
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        video_id = response["id"]
        print(f"✅ Short subido: https://youtu.be/{video_id}")
        return video_id
    except Exception as e:
        print(f"❌ Error subiendo a YouTube: {e}")
        sys.exit(1)

# ================================================================
# 🆕 SUBIR VIDEO A HOST TEMPORAL
# ================================================================
def subir_video_temporal(video_path, intentos=2):
    for _ in range(intentos):
        try:
            with open(video_path, "rb") as f:
                r = requests.post(
                    "https://litterbox.catbox.moe/resources/internals/api.php",
                    data={"reqtype": "fileupload", "time": "72h"},
                    files={"fileToUpload": f},
                    timeout=180,
                )
            if r.status_code == 200 and r.text.strip().startswith("http"):
                url = r.text.strip()
                print(f"✅ Video subido a litterbox: {url}")
                return url
        except Exception as e:
            print(f"⚠️ litterbox falló: {e}")
        time.sleep(3)

    for _ in range(intentos):
        try:
            with open(video_path, "rb") as f:
                r = requests.post(
                    "https://tmpfiles.org/api/v1/upload",
                    files={"file": f},
                    timeout=180,
                )
            if r.status_code == 200:
                url = r.json()["data"]["url"]
                url = url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                print(f"✅ Video subido a tmpfiles: {url}")
                return url
        except Exception as e:
            print(f"⚠️ tmpfiles falló: {e}")
        time.sleep(3)

    try:
        with open(video_path, "rb") as f:
            r = requests.post("https://0x0.st", files={"file": f}, timeout=180)
        if r.status_code == 200 and r.text.strip().startswith("http"):
            url = r.text.strip()
            print(f"✅ Video subido a 0x0.st: {url}")
            return url
    except Exception as e:
        print(f"⚠️ 0x0.st falló: {e}")

    print("❌ No se pudo subir el video a ningún host temporal.")
    return None

# ================================================================
# 🆕 ENVIAR A MAKE
# ================================================================
def enviar_a_make(titulo, descripcion, video_url, url_youtube=""):
    webhook_url = os.getenv("MAKE_WEBHOOK_URL_REELS")
    if not webhook_url:
        print("⚠️ MAKE_WEBHOOK_URL_REELS no configurado. Saltando Facebook.")
        return False

    payload = {
        "titulo": titulo,
        "descripcion": descripcion,
        "video_url": video_url,
        "url_youtube": url_youtube,
    }
    try:
        print("📡 Enviando datos al webhook de Make...")
        r = requests.post(webhook_url, json=payload, timeout=60)
        print(f"📡 Make respondió con código: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Error enviando a Make: {e}")
        return False

# ================================================================
# LIMPIEZA DE TEMPORALES
# ================================================================
def limpiar_temporales_shorts():
    for f in os.listdir("."):
        if (f.startswith("temp_short_") or f.startswith("audio_short_") or f.startswith("placeholder_")) and (f.endswith(".jpg") or f.endswith(".mp3")):
            try:
                os.remove(f)
            except Exception:
                pass
    for aux in ["short_final.mp4", "portada_short.jpg"]:
        if os.path.exists(aux):
            try:
                os.remove(aux)
            except Exception:
                pass
    print("🧹 Archivos temporales de Shorts eliminados.")

# ================================================================
# MAIN
# ================================================================
def main():
    print("🎬 Iniciando Bot de SHORTS (Micro-relatos REALES con Portada de Alto CTR)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎤 Voz inicial seleccionada: {CONFIG_VOZ_ACTUAL['voz']}")

    if not YOUTUBE_USER_TOKEN:
        print("❌ No se encontró YOUTUBE_USER_TOKEN en las variables de entorno.")
        sys.exit(1)

    publicadas_hoy = obtener_publicaciones_hoy()
    if publicadas_hoy >= META_DIARIA_SHORTS:
        print(f"✅ Ya se alcanzó la meta de {META_DIARIA_SHORTS} shorts hoy. Saliendo.")
        sys.exit(0)

    estado = cargar_estado()
    print(f"📌 Estado cargado: {estado}")

    fondo_path = seleccionar_fondo_disponible(estado)

    print("🆕 Generando nueva historia REAL con SEO experto...")
    historia_raw = generar_historia_completa()
    if not historia_raw:
        print("❌ No se pudo generar la historia. Abortando.")
        sys.exit(1)

    texto_completo = historia_raw.get("texto_completo", "")
    palabras = len(texto_completo.split())

    if palabras < 130:
        print(f"⚠️ Texto corto ({palabras} palabras). Expandiendo...")
        texto_completo = expandir_texto_corto(
            texto_completo,
            ESTADO_HISTORIA_SHORTS,
            PERSONAJE_SHORTS
        )
    elif palabras > 190:
        print(f"✂️ Texto largo ({palabras} palabras). Truncando...")
        texto_completo = truncar_texto_largo(texto_completo, max_palabras=170)

    perfil = PERFIL_PERSONAJE_SHORTS
    ubicacion = ESTADO_HISTORIA_SHORTS
    paleta = PALETA_COLOR_ACTUAL
    estilo = ESTILO_VISUAL_ACTUAL

    print(f"\n📊 RESUMEN SEO:")
    print(f"   🏷️ Título: {historia_raw['titulo']} ({len(historia_raw['titulo'])} chars)")
    print(f"   🔄 Alternativo: {historia_raw.get('titulo_alternativo', 'N/A')}")
    print(f"   🔑 Keywords: {historia_raw.get('palabras_clave', [])}")
    print(f"   🖼️ Portada: {historia_raw.get('palabras_portada', 'LO VI')}")
    print(f"   📖 Fuente: {historia_raw.get('fuente_relato', 'N/A')}")
    print(f"   🏷️ Tags: {historia_raw['tags']}")
    print(f"   📖 Procesando historia ({len(texto_completo.split())} palabras)...")

    segmentos = dividir_en_segmentos(texto_completo, max_palabras_por_segmento=45)
    etapas, ubicaciones = asignar_etapas_visuales(segmentos, ubicacion)
    
    print(f"\n🖼️ Generando {len(segmentos)} imágenes con continuidad narrativa...")
    for i, (etapa, ubic) in enumerate(zip(etapas, ubicaciones)):
        print(f"   📍 Segmento {i+1}: [{etapa}] {ubic}")

    recursos = generar_recursos_por_segmento(
        segmentos=segmentos,
        etapas=etapas,
        ubicaciones=ubicaciones,
        perfil=perfil,
        ubicacion=ubicacion,
        estilo=estilo,
        paleta=paleta,
        intentos_por_imagen=3
    )

    if not recursos:
        print("❌ Error generando recursos para los segmentos. Abortando.")
        sys.exit(1)

    # 🆕 PORTADA: Agnes dibuja el texto DENTRO del marco vertical
    print("\n🖼️ Generando portada vertical con texto integrado (Agnes)...")
    portada_url = generar_portada_shorts(historia_raw.get("palabras_portada", "LO VI"))
    if portada_url and recursos:
        try:
            r = requests.get(portada_url, timeout=30)
            r.raise_for_status()
            portada_path = "portada_short.jpg"
            with open(portada_path, "wb") as f:
                f.write(r.content)
            with Image.open(portada_path) as img:
                ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS).save(portada_path)
            recursos[0]["imagen_url"] = portada_path
            print("✅ Portada con texto integrada aplicada como PRIMER frame del Short.")
        except Exception as e:
            print(f"⚠️ Error aplicando portada: {e}")
    else:
        print("⚠️ No se generó portada; se usa la imagen del segmento 1.")

    try:
        video_final = montar_video_shorts(
            recursos_por_segmento=recursos,
            fondo_path=fondo_path,
            salida="short_final.mp4"
        )
    except Exception as e:
        print(f"❌ Error montando video: {e}")
        sys.exit(1)

    print(f"\n🚀 Subiendo Short a YouTube...")
    video_id_youtube = subir_a_youtube(
        video_path=video_final,
        titulo=historia_raw["titulo"],
        etiquetas=historia_raw["tags"],
        gancho_descripcion=historia_raw["gancho_descripcion"],
        contexto_descripcion=historia_raw["contexto_descripcion"],
        hashtags_descripcion=historia_raw["hashtags_descripcion"],
        fuente_relato=historia_raw.get("fuente_relato", "Basado en un testimonio real compartido en internet."),
    )

    guardar_titulo_publicado(historia_raw["titulo"])
    
    titulo_alternativo = historia_raw.get("titulo_alternativo", "")
    if titulo_alternativo and titulo_alternativo != historia_raw["titulo"]:
        print(f"💡 Título alternativo para A/B testing: {titulo_alternativo}")

    publicaciones_antes = obtener_publicaciones_hoy()
    if publicaciones_antes < 2:
        print(f"\n📘 Reel #{publicaciones_antes + 1} del día: enviando a Facebook vía Make...")
        video_url_temporal = subir_video_temporal(video_final)
        if video_url_temporal:
            descripcion_facebook = f"""{historia_raw['gancho_descripcion']}

{historia_raw['contexto_descripcion']}

🔴 RELATO COMPLETO en el canal: {CANAL_LINK}

📖 {historia_raw.get('fuente_relato', 'Basado en un testimonio real compartido en internet.')}

📱 Síguenos: {FACEBOOK_LINK}

{historia_raw['hashtags_descripcion']}"""
            enviar_a_make(
                titulo=historia_raw["titulo"],
                descripcion=descripcion_facebook,
                video_url=video_url_temporal,
                url_youtube=f"https://youtu.be/{video_id_youtube}"
            )
        else:
            print("⚠️ No se pudo subir al host temporal. Facebook omitido.")
    else:
        print(f"\n⏭️ Reel #{publicaciones_antes + 1} del día: NO se envía a Facebook (límite: 2 diarios).")

    incrementar_publicaciones_hoy()

    guardar_estado(estado)
    limpiar_temporales_shorts()
    print("✨ Ejecución del Bot finalizada con portada de alto CTR.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
