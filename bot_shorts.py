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
ACTIVAR_DISCLOSURE_IA = True
DISCLOSURE_TEXT = "\n🤖 Contenido generado con inteligencia artificial (relato e imágenes)."

# ================================================================
# ÉPOCA DEL SUCESO (dinámica según el relato)
# ================================================================
ANIO_SUCESO = None
EPOCA_MOD = "present day contemporary era (2020s), modern vehicles, modern architecture, modern clothing, smartphones era"

def construir_modificadores_epoca(anio):
    if anio is None or anio >= 2015:
        return (
            "present day contemporary era (2020s), modern vehicles, modern architecture, "
            "modern clothing, LED lighting, smartphones era"
        )
    elif anio >= 2000:
        return (
            f"early 2000s era (year {anio}): 2000s cars, CRT televisions, old flip cellphones, "
            "2000s fashion and architecture, no smartphones"
        )
    elif anio >= 1990:
        return (
            f"1990s era (year {anio}): 90s cars, cassette players, CRT TVs, analog phones, "
            "90s fashion, older architecture, no smartphones, no modern tech"
        )
    elif anio >= 1980:
        return (
            f"1980s era (year {anio}): 80s cars, analog rotary phones, vintage clothing, "
            "older buildings, no modern technology"
        )
    else:
        return (
            f"past era (year {anio}): old classic cars, analog technology, period clothing, "
            "aged architecture, no modern devices"
        )

def actualizar_epoca(anio):
    global ANIO_SUCESO, EPOCA_MOD
    try:
        ANIO_SUCESO = int(anio)
    except Exception:
        ANIO_SUCESO = None
    EPOCA_MOD = construir_modificadores_epoca(ANIO_SUCESO)
    print(f"📅 Época del suceso: {ANIO_SUCESO if ANIO_SUCESO else 'actualidad'}")

# ================================================================
# 🎤 SOLO 4 VOCES MASCULINAS QUE FUNCIONAN
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural", "velocidad": "+10%", "tono": "-2Hz"},
    {"voz": "es-ES-AlvaroNeural", "velocidad": "+10%", "tono": "-3Hz"},
    {"voz": "es-MX-ManuelNeural", "velocidad": "+10%", "tono": "-1Hz"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+10%", "tono": "-2Hz"},
]
CONFIG_VOZ_ACTUAL = random.choice(VOCES_DISPONIBLES)

# ================================================================
# 🎨 PALETAS
# ================================================================
PALETAS_COLOR = [
    "Cold cyan blue LED fog, navy blue shadows, crisp white moonlight",
    "Emerald green twilight, city haze, muted sage ambient lighting",
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

# ================================================================
# 📷 ESTILOS VISUALES
# ================================================================
ESTILOS_VISUALES = [
    "Cinematic photograph, dramatic lighting, sharp focus, film still",
    "Thriller photography, soft ambient diffusion, high contrast",
    "Documentary realistic photo, natural texture, authentic",
    "8k resolution cinematic frame, ultra clear details",
    "Noir style, high contrast, moody urban atmosphere",
    "Analog film photograph, grain of the period, authentic era look",
]
ESTILO_VISUAL_ACTUAL = random.choice(ESTILOS_VISUALES)

# ================================================================
# 🧑 GENERADOR DE PERSONAJES
# ================================================================
def generar_perfil_personaje_shorts():
    edades = ["21-year-old", "28-year-old", "35-year-old", "42-year-old", "50-year-old", "60-year-old"]
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
    profesiones = [
        "trailero conduciendo un tráiler en autopista nocturna",
        "policía en su turno nocturno en patrulla",
        "conductor de taxi en ciudad",
        "repartidor en moto",
        "velador en condominio residencial",
        "enfermero en hospital",
        "guardia de seguridad en centro comercial",
        "carpintero en taller",
        "paramédico en ambulancia",
    ]
    profesion = random.choice(profesiones)
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
    random.shuffle(fondos)
    for root, dirs, files in os.walk("."):
        if "/." in root or "\\." in root:
            continue
        for file in files:
            for fondo in fondos:
                if file.lower() == fondo.lower():
                    full_path = os.path.join(root, file)
                    estado["ultimo_fondo"] = fondo
                    return full_path
    for root, dirs, files in os.walk("."):
        for file in files:
            for fondo in FONDOS_DISPONIBLES:
                if file.lower() == fondo.lower():
                    full_path = os.path.join(root, file)
                    estado["ultimo_fondo"] = fondo
                    return full_path
    return None

# ================================================================
# 🧼 LIMPIADOR DE PROMPTS (conserva época, ambiente protagonista)
# ================================================================
def limpiar_prompt_base(prompt, estilo_visual=None, paleta_color=None):
    estilo = estilo_visual or ESTILO_VISUAL_ACTUAL
    paleta = paleta_color or PALETA_COLOR_ACTUAL
    if not prompt:
        prompt = "Night scene, dramatic lighting"
    prompt = re.sub(r"\n+", " ", prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r"[^\x00-\x7F]+", "", prompt)
    palabras_malas = [
        r"\bgore\b", r"\bblood\b", r"\bbloody\b", r"\bwounds?\b", r"\bzombies?\b",
        r"\bdisfigured\b", r"\bmonster\b", r"\bdemacrad[oa]s?\b",
    ]
    for pattern in palabras_malas:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)
    prompt_base = re.sub(r"\s+", " ", prompt).strip()[:220]
    modificadores = (
        f", {estilo}, color palette of {paleta}, "
        "vertical 9:16 format, WIDE environmental establishing shot, "
        "the ENVIRONMENT, objects and location are the main focal point (cars, trees, houses, streets, buildings, forests, gardens), "
        "if a person appears they occupy AT MOST 20% of the frame, small and at distance, "
        "EXACTLY ONE single person, NO clones, NO duplicates, NO twins, NO double faces, "
        f"{EPOCA_MOD}, period-accurate vehicles, architecture, clothing and technology, "
        "sharp focus, natural lighting, no text, no watermark"
    )
    return prompt_base + modificadores

# ================================================================
# 🧹 LIMPIAR CARACTERES PARA TTS
# ================================================================
def limpiar_caracteres_para_tts(texto):
    texto = re.sub(r'[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9\s.,;:!?¿¡\'\"]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

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
# 🗂️ ESTADO
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

def limpiar_texto_para_audio(texto):
    texto = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002700-\U000027BF\U000024C2-\U0001F251]', '', texto)
    texto = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', texto)
    texto = texto.replace('"', "'")
    texto = texto.replace('\n', ' ')
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def generar_placeholder_local(texto="Terror", size=(1080, 1920)):
    try:
        img = Image.new("RGB", size, (20, 20, 20))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), texto, font=font)
        x = (size[0] - (bbox[2]-bbox[0])) // 2
        y = (size[1] - (bbox[3]-bbox[1])) // 2
        draw.text((x, y), texto, fill="red", font=font)
        path = f"placeholder_{random.randint(1000, 9999)}.jpg"
        img.save(path)
        return path
    except Exception:
        return None

# ================================================================
# 🔄 EXPANDIR / TRUNCAR TEXTO
# ================================================================
def expandir_texto_corto(texto_corto, ubicacion, personaje):
    prompt = f"""Expande el siguiente relato a 150-170 palabras con detalles sensoriales de {ubicacion}.
Mantén trama y tono. Sin CTA.
RELATO: {texto_corto}
Devuelve SOLO el relato."""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.8, "max_tokens": 700}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        t = r.json()["choices"][0]["message"]["content"].strip()
        return t if len(t.split()) > 130 else texto_corto
    except Exception:
        return texto_corto

def truncar_texto_largo(texto, max_palabras=170):
    palabras = texto.split()
    if len(palabras) <= max_palabras:
        return texto
    for i in range(max_palabras, max_palabras - 30, -1):
        if i < len(palabras) and palabras[i-1].endswith(('.', '!', '?')):
            return ' '.join(palabras[:i])
    return ' '.join(palabras[:max_palabras])

# ================================================================
# 🎬 GENERAR HISTORIA CON SEO + ÉPOCA DINÁMICA
# (MEJORADO: se usan palabras_clave en tags y hashtags dinámicos)
# ================================================================
def generar_historia_completa():
    titulos_pub = cargar_titulos_publicados()["titulos"][-10:]
    titulos_referencia = "\n".join([f"- {t}" for t in titulos_pub]) if titulos_pub else "Ninguno aún."

    prompt = f"""Eres un CURADOR Y ADAPTADOR DE RELATOS PARANORMALES REALES de internet, especializado en continuidad visual cinematográfica y EXPERTO EN SEO PARA YOUTUBE SHORTS 2026.
🚨 REGLA DE ORO:
La historia DEBE estar basada en un relato que REALMENTE alguien contó en internet.
Adáptalo en primera persona, tono coloquial, ambientado en {ESTADO_HISTORIA_SHORTS}, México.

🎯 REGLA CRÍTICA: CONTINUIDAD VISUAL NARRATIVA
El relato se dividirá en 4-5 segmentos visuales con etapas:
inicio_casa, desplazamiento, lugar_destino, climax_evento, resolucion.
Trayectoria lógica y entorno coherente entre segmentos consecutivos.

PROTAGONISTA: {ARTICULO_SHORTS} {PERSONAJE_SHORTS}.
AMBIENTACIÓN: Si el relato menciona un AÑO específico, úsalo para la época (autos, ropa, tecnología). Si no, usa la actualidad.

🎯 REGLA CRÍTICA DE LONGITUD:
- EXACTAMENTE entre 150 y 170 palabras.

📐 ESTRUCTURA:
1. GANCHO (5-10 palabras)
2. CONTEXTO (20-30 palabras)
3. TENSIÓN (80-90 palabras)
4. TWIST FINAL (30-40 palabras)

🎯 REGLA CRÍTICA 1: TÍTULO SEO DE ALTO CTR
FÓRMULA: [VERBO 1RA PERSONA / IMPACTO] + [LUGAR ESPECÍFICO] + [GANCHO EMOCIONAL]
Longitud: 55-75 caracteres, primera persona, lugar específico de {ESTADO_HISTORIA_SHORTS}.
❌ PROHIBIDOS: "La leyenda de...", "El fantasma de...", "El misterio de..."
IMPORTANTE: Asegúrate de que UNA de las palabras_clave (abajo) aparezca al INICIO del título (primeras 3 palabras). Por ejemplo, si la keyword es "fantasma", el título debe empezar con "Fantasma..." o similar.

🎯 REGLA CRÍTICA 2: PALABRAS DE PORTADA
"palabras_portada": TEXTO GANCHO de MÁXIMO 2 palabras cortas.

🎯 REGLA CRÍTICA 3: DESCRIPCIÓN SEO
Línea 1 (GANCHO, máx 90 chars), Línea 2 (CONTEXTO), Línea 3 (CTA canal), Línea 4 (FUENTE), Línea 5 (FACEBOOK), Línea 6 (HASHTAGS máx 5).

🎯 REGLA CRÍTICA 4: TAGS SEO (10-15, máx 480 chars)
🎯 REGLA CRÍTICA 5: PALABRAS CLAVE (2-3) - serán usadas en el título, descripción y tags.
🎯 REGLA CRÍTICA 6: TÍTULO ALTERNATIVO (A/B testing)
🎯 REGLA CRÍTICA 7: AÑO DEL SUCESO
"anio_suceso": año específico (ej: 1998). Si no hay fecha clara, usa la actualidad (2024).

🚫 TÍTULOS YA PUBLICADOS (NO REPETIR):
{titulos_referencia}

Devuelve ESTRICTAMENTE este JSON válido:
{{
    "titulo": "Título SEO 1ra persona, 55-75 caracteres, con keyword al inicio",
    "titulo_alternativo": "Segundo título",
    "anio_suceso": 1998,
    "palabras_clave": ["keyword 1", "keyword 2", "keyword 3"],
    "gancho_descripcion": "Gancho máx 90 caracteres",
    "contexto_descripcion": "1 oración con contexto",
    "fuente_relato": "Basado en un testimonio/leyenda real de ...",
    "texto_completo": "Micro-relato REAL, 150-170 palabras, primera persona, coloquial",
    "palabras_portada": "TEXTO GANCHO máximo 2 palabras",
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
            respuesta = r.json()["choices"][0]["message"]["content"].strip()
            json_str = limpiar_respuesta_json(respuesta)
            try:
                data = json.loads(json_str, strict=False)
            except json.JSONDecodeError:
                import json5
                data = json5.loads(json_str)

            if "texto_completo" not in data or len(data["texto_completo"]) < 100:
                raise ValueError("Texto demasiado corto")

            # Actualizar época según año del suceso
            anio_suceso = data.get("anio_suceso", None)
            actualizar_epoca(anio_suceso)

            data["texto_completo"] = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', data["texto_completo"])

            # ---- TÍTULO CON PALABRA CLAVE AL INICIO ----
            titulo = data.get("titulo", "").strip()
            titulo = re.sub(r'#\w+', '', titulo).strip()
            titulo = ' '.join(titulo.split())

            keywords = data.get("palabras_clave", [])
            if keywords and isinstance(keywords, list):
                # Buscar si alguna keyword aparece al inicio del título (case insensitive)
                keyword_encontrada = None
                for kw in keywords:
                    if titulo.lower().startswith(kw.lower()):
                        keyword_encontrada = kw
                        break
                if not keyword_encontrada and keywords:
                    # Si ninguna keyword está al inicio, intentar poner la primera al principio
                    primera_kw = keywords[0]
                    # Eliminar cualquier prefijo común como "El ", "La ", "Los ", etc.
                    titulo_sin_articulo = re.sub(r'^(El|La|Los|Las|Un|Una|Unos|Unas)\s+', '', titulo, flags=re.IGNORECASE)
                    if titulo_sin_articulo != titulo:
                        titulo = f"{primera_kw.capitalize()} {titulo_sin_articulo}"
                    else:
                        titulo = f"{primera_kw.capitalize()} {titulo}"
                    # Asegurar que no exceda 75 chars
                    if len(titulo) > 75:
                        titulo = titulo[:72] + "..."

            if len(titulo) < 40:
                titulo = f"{titulo} - Testimonio real en {ESTADO_HISTORIA_SHORTS}"
            if len(titulo) > 95:
                titulo = titulo[:92].rsplit(' ', 1)[0] + "..."
            data["titulo"] = titulo

            if titulo_ya_publicado(titulo):
                print(f"   ⚠️ Título YA PUBLICADO. Regenerando...")
                raise ValueError("Título duplicado")

            # ---- GANCHO Y CONTEXTO ----
            gancho = data.get("gancho_descripcion", "").strip()
            if not gancho or len(gancho) > 110:
                gancho = f"Esto fue lo que viví en {ESTADO_HISTORIA_SHORTS} y nunca pude explicar"[:100]
            data["gancho_descripcion"] = gancho

            contexto = data.get("contexto_descripcion", "").strip()
            if not contexto:
                contexto = f"Un testimonio real de fenómenos paranormales en {ESTADO_HISTORIA_SHORTS}, México."
            data["contexto_descripcion"] = contexto

            fuente = data.get("fuente_relato", "").strip()
            if not fuente:
                fuente = "Basado en un testimonio real compartido en internet."
            data["fuente_relato"] = fuente

            # ---- TAGS INCORPORANDO KEYWORDS ----
            tags_raw = data.get("tags", "")
            tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()][:15]

            # Añadir las keywords como tags si no están ya
            if keywords:
                for kw in keywords:
                    kw_lower = kw.lower().strip()
                    if kw_lower not in [t.lower() for t in tags_list]:
                        tags_list.append(kw_lower)

            # Extras long-tail
            extras = [
                f"terror en {ESTADO_HISTORIA_SHORTS.lower()}",
                "testimonios paranormales reales",
                "historias reales contadas en primera persona",
                "leyendas urbanas mexicanas reales",
                "casos paranormales reales mexico",
                "historias de fantasmas reales",
                "shorts terror",
            ]
            i = 0
            while len(tags_list) < 10 and i < len(extras):
                if extras[i] not in tags_list:
                    tags_list.append(extras[i])
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

            # ---- HASHTAGS DINÁMICOS ----
            # Generar hashtags variados usando keywords y lugar
            hashtag_base = "#Shorts"
            hashtag_lugar = f"#{ESTADO_HISTORIA_SHORTS.replace(' ', '')}"
            hashtag_keywords = []
            if keywords:
                for kw in keywords[:2]:
                    # Limpiar y convertir a hashtag (sin espacios, sin tildes)
                    kw_clean = re.sub(r'[áéíóú]', lambda m: {'á':'a','é':'e','í':'i','ó':'o','ú':'u'}.get(m.group(), m.group()), kw)
                    kw_clean = re.sub(r'[^a-zA-Z0-9]', '', kw_clean)
                    if kw_clean and len(kw_clean) > 2:
                        hashtag_keywords.append(f"#{kw_clean.capitalize()}")
            hashtag_extra = random.choice([
                "#RelatosReales", "#Paranormal", "#MiedoReal",
                "#LeyendasUrbanas", "#CasosReales", "#TerrorMexicano",
                "#HistoriasDeTerror", "#Sobrenatural", "#ExperienciasReales"
            ])
            hashtag_final = f"{hashtag_base} {hashtag_lugar} {' '.join(hashtag_keywords[:2])} {hashtag_extra}"
            data["hashtags_descripcion"] = hashtag_final

            print(f"   🏷️ Título SEO: {data['titulo']} ({len(data['titulo'])} chars)")
            print(f"   📅 Año del suceso: {data.get('anio_suceso', 'actualidad')}")
            print(f"   🔑 Keywords: {keywords}")
            return data

        except Exception as e:
            print(f"❌ Intento {intento+1}/6 falló: {e}")
            if intento < 5:
                time.sleep(10 + intento * 5)

    print("❌ TODOS LOS INTENTOS FALLARON.")
    sys.exit(1)

# ================================================================
# 🔄 DIVIDIR TEXTO POR ORACIONES
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
# 🎭 ASIGNAR ETAPAS VISUALES
# ================================================================
def asignar_etapas_visuales(segmentos, ubicacion):
    n = len(segmentos)
    etapas = []
    ubicaciones = []
    for i in range(n):
        progreso = i / max(n - 1, 1)
        if progreso < 0.2:
            etapa = "inicio_casa"
            ubic = f"interior del hogar en {ubicacion}"
        elif progreso < 0.4:
            etapa = "desplazamiento"
            ubic = f"calle o vehículo en movimiento, {ubicacion}"
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
# 🎨 GENERAR PROMPT DE IMAGEN CON MEMORIA VISUAL + ÉPOCA + VARIEDAD DE ÁNGULO
# ================================================================
def generar_prompt_con_contexto(segmento_texto, etapa, ubicacion_escena, segmento_anterior_texto=None, perfil=None, estilo_visual=None, paleta_color=None, index_segmento=0, total_segmentos=1):
    estilo = estilo_visual or ESTILO_VISUAL_ACTUAL
    paleta = paleta_color or PALETA_COLOR_ACTUAL
    perfil = perfil or PERFIL_PERSONAJE_SHORTS

    contexto_previo = ""
    if segmento_anterior_texto:
        contexto_previo = f"\nPREVIOUS SCENE: The character was just in: '{segmento_anterior_texto[:120]}'"

    instrucciones_etapa = {
        "inicio_casa": "Show the environment of a home interior (furniture, rooms, objects). If the person is mentioned, show them SMALL at distance (max 20% of frame). If not mentioned, show ONLY the environment without people.",
        "desplazamiento": "Show the environment of movement (street, vehicle, road). Vehicles and surroundings are the MAIN subject. If person is mentioned, show them small at distance (max 20% of frame).",
        "lugar_destino": "Show the environment of the specific location. Cars, trees, houses, buildings are the MAIN subject. If person is mentioned, show them small at distance (max 20% of frame).",
        "climax_evento": "Show the environment where the event happens. The LOCATION is the main subject. If person is mentioned, show them small at distance (max 20% of frame). NO close-up faces.",
        "resolucion": "Show the environment of departure/return. Calmer atmosphere. If person is mentioned, show them small at distance (max 20% of frame).",
    }
    instruccion = instrucciones_etapa.get(etapa, instrucciones_etapa["lugar_destino"])

    # ---- VARIEDAD DE ÁNGULO ----
    angulos = ["low angle", "high angle", "eye level", "dutch angle", "overhead", "wide establishing shot"]
    # Asignar un ángulo diferente según el índice del segmento
    angulo_elegido = angulos[index_segmento % len(angulos)]
    if total_segmentos > 1 and index_segmento == total_segmentos - 1:
        angulo_elegido = "eye level"  # El último segmento más neutro

    prompt = f"""You are an expert cinematographer specializing in narrative visual continuity.
Story segment:
\"\"\"
{segmento_texto}
\"\"\"
{contexto_previo}

Generate an ENGLISH PROMPT for a vertical (9:16) photo of this scene.

CONTINUITY INSTRUCTIONS:
- Current stage: {etapa}
- Current location: {ubicacion_escena}
- DIRECTIVE: {instruccion}
- CAMERA ANGLE: {angulo_elegido} (to give visual variety between segments)
- Ensure the scene is LEGIBLE on small screens: clear composition, main subject (if any) well centered in the frame, no clutter.

STRICT COMPOSITION RULES:
- SHOT: Wide shot or extreme wide shot. ABSOLUTELY NO close-up, NO portrait, NO headshot.
- MAIN SUBJECT: The ENVIRONMENT, objects and location (cars, trees, houses, streets, buildings, forests, gardens).
- If a person is mentioned: include them occupying AT MOST 20% of the frame, small and at distance.
- If NO person is mentioned: show ONLY the environment without people.
- Style: professional hyperrealistic photography, sharp focus.
- Color palette: {paleta}
- ERA: {EPOCA_MOD}. Period-accurate vehicles, architecture, clothing and technology.
- ABSOLUTE PROHIBITIONS: NO clones, NO duplicates, NO twins, NO double faces, NO close-up faces, NO gore, NO blood.

Return ONLY the English prompt, no explanations.
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
        prompt_imagen += f", {estilo}, vertical 9:16, wide establishing shot, environment as main subject, no close-up face, no portrait, no gore, no blood, {EPOCA_MOD}, exactly one person if mentioned, no clones, no duplicates"
        return prompt_imagen
    except Exception as e:
        print(f"⚠️ Error generando prompt de imagen: {e}")
        return f"Wide establishing shot of {ubicacion_escena}, {estilo}, vertical 9:16, environment as main subject, no close-up face, {EPOCA_MOD}"

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
        "gore, blood, bloody, wounds, cuts, bruises, gaunt, emaciated, "
        "sickly, decayed skin, rotting, zombie-like, corpse-like, grotesque, ugly, "
        "dual face, split face, two faces, double face, mirror face, two heads, "
        "cloned face, duplicate person, twin, twins, doppelganger, siamese, conjoined, "
        "floating objects, illogical elements, impossible physics, "
        "ghost doubles, transparent figures, multiple versions of same person, "
        "over-saturated, oversharpened, low quality, blurry, text, watermark, logo"
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
    total_seg = len(segmentos)
    for idx, seg in enumerate(segmentos):
        etapa = etapas[idx] if idx < len(etapas) else "lugar_destino"
        ubic_escena = ubicaciones[idx] if idx < len(ubicaciones) else ubicacion
        print(f"  🎬 Segmento {idx+1}/{total_seg} ({len(seg.split())} palabras) - Etapa: {etapa}")
        print(f"     📍 Ubicación: {ubic_escena}")

        seg_anterior = segmentos[idx-1] if idx > 0 else None
        prompt_imagen = generar_prompt_con_contexto(
            segmento_texto=seg,
            etapa=etapa,
            ubicacion_escena=ubic_escena,
            segmento_anterior_texto=seg_anterior,
            perfil=perfil,
            estilo_visual=estilo,
            paleta_color=paleta,
            index_segmento=idx,
            total_segmentos=total_seg
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
        except Exception:
            duracion = 10.0

        resultados_temporales.append({
            "imagen_url": img_url,
            "audio_path": audio_path,
            "duracion": duracion
        })

        if idx < len(segmentos) - 1:
            time.sleep(12)

    # Reparar imágenes fallidas
    for i, res in enumerate(resultados_temporales):
        if res["imagen_url"] is None:
            siguiente_imagen = None
            for j in range(i + 1, len(resultados_temporales)):
                if resultados_temporales[j]["imagen_url"] is not None:
                    siguiente_imagen = resultados_temporales[j]["imagen_url"]
                    break
            if siguiente_imagen is not None:
                res["imagen_url"] = siguiente_imagen
            else:
                if i > 0 and resultados_temporales[i-1]["imagen_url"] is not None:
                    res["imagen_url"] = resultados_temporales[i-1]["imagen_url"]
                else:
                    img_url = generar_placeholder_local("Terror", (1080, 1920))
                    if not img_url:
                        img_url = "https://via.placeholder.com/1080x1920/1a1a1a/ff0000?text=Terror"
                    res["imagen_url"] = img_url
    return resultados_temporales

# ================================================================
# ✅ GENERAR AUDIO - SOLO 4 VOCES MASCULINAS QUE FUNCIONAN
# ================================================================
def generar_audio(texto, index, intentos_por_voz=2):
    global CONFIG_VOZ_ACTUAL
    texto_limpio = re.sub(r"imagen_prompt.*", "", texto, flags=re.IGNORECASE).strip()
    texto_limpio = limpiar_caracteres_para_tts(texto_limpio)
    texto_limpio = limpiar_texto_para_audio(texto_limpio)

    if len(texto_limpio) < 30:
        texto_limpio = "Esa noche en la carretera, el silencio era tan denso que podía cortarse con un cuchillo. El miedo lo envolvía todo."

    if not texto_limpio:
        return None

    filename = f"audio_short_{index}.mp3"
    voces_a_probar = [CONFIG_VOZ_ACTUAL]
    for voz_config in VOCES_DISPONIBLES:
        if voz_config["voz"] != CONFIG_VOZ_ACTUAL["voz"]:
            voces_a_probar.append(voz_config)

    for intento_voz, voz_config in enumerate(voces_a_probar):
        voz = voz_config["voz"]
        rate = voz_config["velocidad"]
        pitch = voz_config["tono"]

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
                print(f"❌ Falló con {voz}: {e}")
                if intento < intentos_por_voz - 1:
                    time.sleep(3 * (intento + 1))
                if os.path.exists(filename):
                    try:
                        os.remove(filename)
                    except:
                        pass

    print("❌ TODAS las voces fallaron.")
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

    for voz_config in voces_a_probar:
        voz = voz_config["voz"]
        rate = voz_config["velocidad"]
        pitch = voz_config["tono"]
        async def _generar():
            communicate = edge_tts.Communicate(cta_texto, voz, rate=rate, pitch=pitch)
            await communicate.save(filename)
        try:
            asyncio.run(_generar())
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return filename
        except Exception:
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                except:
                    pass
    return None

# ================================================================
# 🎬 MONTAR VIDEO - BUG audio_final CORREGIDO
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

    # CTA final
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

    # 🛠️ BUG CORREGIDO: audio_final SIEMPRE se asigna
    audio_final = audio_narracion
    if fondo_path and os.path.exists(fondo_path):
        try:
            fondo_clip = AudioFileClip(fondo_path)
            if fondo_clip.duration < duracion_total:
                veces = int(duracion_total / fondo_clip.duration) + 1
                fondo_clip = concatenate_audioclips([fondo_clip] * veces)
            fondo_clip = fondo_clip.subclip(0, duracion_total).volumex(0.08)
            audio_final = CompositeAudioClip([audio_narracion, fondo_clip])
            print("🎵 Audio de fondo mezclado al 8%")
        except Exception as e:
            print(f"⚠️ Error en audio de fondo: {e}")
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
# 🔄 SUBIR A YOUTUBE (DESCRIPCIÓN MEJORADA)
# ================================================================
def subir_a_youtube(video_path, titulo, etiquetas, gancho_descripcion, contexto_descripcion, hashtags_descripcion, fuente_relato=""):
    try:
        creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
        youtube = build("youtube", "v3", credentials=creds)
    except Exception as e:
        print(f"❌ Error autenticando con YouTube: {e}")
        sys.exit(1)

    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]

    # ---- DESCRIPCIÓN CON SALTOS DE LÍNEA DOBLES PARA LEGIBILIDAD ----
    descripcion = f"""{gancho_descripcion}

{contexto_descripcion}

🔴 RELATO COMPLETO en el canal: {CANAL_LINK}

📖 {fuente_relato}

📱 Facebook: {FACEBOOK_LINK}

{hashtags_descripcion}"""

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
# 🔄 SUBIR VIDEO A HOST TEMPORAL
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
# 🔄 ENVIAR A MAKE
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
    if os.path.exists("short_final.mp4"):
        try:
            os.remove("short_final.mp4")
        except Exception:
            pass
    print("🧹 Archivos temporales de Shorts eliminados.")

# ================================================================
# MAIN
# ================================================================
def main():
    print("🎬 Iniciando Bot de SHORTS (Micro-relatos REALES con continuidad visual)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎤 Voz inicial seleccionada: {CONFIG_VOZ_ACTUAL['voz']}")

    if not YOUTUBE_USER_TOKEN:
        print("❌ No se encontró YOUTUBE_USER_TOKEN.")
        sys.exit(1)

    publicadas_hoy = obtener_publicaciones_hoy()
    if publicadas_hoy >= META_DIARIA_SHORTS:
        print(f"✅ Ya se alcanzó la meta de {META_DIARIA_SHORTS} shorts hoy. Saliendo.")
        sys.exit(0)

    estado = cargar_estado()
    fondo_path = seleccionar_fondo_disponible(estado)

    print("🔄 Generando nueva historia REAL con SEO experto...")
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
    print(f"   📅 Año del suceso: {historia_raw.get('anio_suceso', 'actualidad')}")
    print(f"   🔑 Keywords: {historia_raw.get('palabras_clave', [])}")
    print(f"   📖 Fuente: {historia_raw.get('fuente_relato', 'N/A')}")
    print(f"   🏷️ Tags: {historia_raw['tags']}")
    print(f"\n   📖 Procesando historia ({len(texto_completo.split())} palabras)...")

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
        print("❌ Error generando recursos. Abortando.")
        sys.exit(1)

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

    # Facebook solo para los 2 primeros Shorts del día
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
    print("✨ Ejecución del Bot finalizada con éxito.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
