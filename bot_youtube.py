import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
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
)
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import edge_tts

# ================================================================
# CONFIGURACIÓN (GitHub Secrets)
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

MUSICA_ESTADO_FILE = "estado_musica.json"

# Duración mínima aceptable para el video (8 minutos)
DURACION_MINIMA_SEGUNDOS = 480
MAX_INTENTOS_EXPANSION = 2

# ================================================================
# 🎤 BANCO DE 12 VOCES
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural", "velocidad": "+12%", "tono": "-2Hz"},
    {"voz": "es-MX-DaliaNeural", "velocidad": "+12%", "tono": "+0Hz"},
    {"voz": "es-ES-AlvaroNeural", "velocidad": "+12%", "tono": "-3Hz"},
    {"voz": "es-ES-ElviraNeural", "velocidad": "+12%", "tono": "+1Hz"},
    {"voz": "es-CO-SalomeNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-AR-ElenaNeural", "velocidad": "+12%", "tono": "+2Hz"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+12%", "tono": "-2Hz"},
    {"voz": "es-PE-CamilaNeural", "velocidad": "+12%", "tono": "+0Hz"},
    {"voz": "es-US-PalomaNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-ES-XimenaNeural", "velocidad": "+12%", "tono": "+1Hz"},
    {"voz": "es-MX-CandelaNeural", "velocidad": "+12%", "tono": "-3Hz"},
    {"voz": "es-ES-AbrilNeural", "velocidad": "+12%", "tono": "-2Hz"},
]
CONFIG_VOZ_ACTUAL = random.choice(VOCES_DISPONIBLES)

# ================================================================
# 🎨 PALETAS REORDENADAS (60% FRÍAS / 40% CÁLIDAS)
# ================================================================
PALETAS_COLOR = [
    "Cold cyan blue fog, navy blue shadows, pale white moonlight",
    "Emerald green twilight, dark forest haze, muted sage green lighting",
    "Deep violet haze, electric purple ambient light, dark magenta shadows",
    "Slate gray tones, freezing ice blue highlight, dim overcast ambient",
    "Dark teal and deep blue, oceanic midnight, cold misty atmosphere",
    "Stark black and white high contrast photography, silver moonlight, deep pitch shadows",
    "Muted sepia tones, dark brown amber glow, high contrast shadow",
    "Desaturated cold film look, moody cinematic lighting, 8k hyperrealistic",
    "Neon purple and electric pink, deep violet shadows, cyberpunk glitch lights",
    "Electric yellow and charcoal black, stark contrast, dusty atmospheric haze",
    "Deep crimson red, pitch black shadow, intense orange emergency light accents",
    "Blood red and burnt orange, dark charcoal shadows, hellish glow",
    "Warm amber and dark mahogany, golden candlelight, deep brown shadows",
    "Fiery sunset orange, deep purple shadows, intense red highlights",
    "Rusty red and dark brown, sepia undertones, warm vintage look",
    "Toxic lime green and pitch black, eerie chemical glow, radioactive haze",
]
PALETA_COLOR_ACTUAL = random.choice(PALETAS_COLOR)

# ================================================================
# 📷 ESTILOS VISUALES
# ================================================================
ESTILOS_VISUALES = [
    "Clean 35mm film photograph, bright cinematic lighting, well-lit scene, sharp focus",
    "Modern cinematic thriller photography, soft ambient diffusion, bright highlights",
    "Documentary realistic photo, natural crisp skin texture, bright daylight ambient",
    "8k resolution cinematic movie frame, ultra clear facial details, bright exposure",
    "High-end fashion photography style, dramatic but well-lit lighting, clean skin",
    "Cinematic noir style, high contrast but well-exposed, bright highlights",
]
ESTILO_VISUAL_ACTUAL = random.choice(ESTILOS_VISUALES)

# ================================================================
# 🗺️ ESTADOS DE MÉXICO
# ================================================================
ESTADOS_MEXICO = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas",
    "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit",
    "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
    "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"
]

# ================================================================
# 🧑 GENERADOR DE PERSONAJES
# ================================================================
def generar_perfil_personaje():
    edades = ["21-year-old", "28-year-old", "35-year-old", "42-year-old", "50-year-old", "60-year-old"]
    generos = ["man", "woman"]
    vestimentas = [
        "wearing a denim jacket and grey shirt",
        "wearing a dark green coat and wool scarf",
        "wearing a simple white shirt and leather belt",
        "wearing an old blue mechanic uniform",
        "wearing a dark sweater and classic trousers",
        "wearing a red flannel shirt and jeans",
        "wearing a black leather jacket and boots",
        "wearing a traditional embroidered blouse and long skirt",
        "wearing a white guayabera shirt and dark pants",
        "wearing a simple cotton dress and sandals",
        "wearing a baseball cap and hoodie",
    ]
    cabellos = [
        "short curly dark hair",
        "long straight black hair tied back",
        "grey cropped hair",
        "wavy brown shoulder-length hair",
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
# 🎵 AUDIO DE FONDO
# ================================================================
FONDOS_DISPONIBLES = [
    "Ash and Marrow.mp3", "Black Maw.mp3", "Cold Hollow.mp3",
    "Hollow Marrow.mp3", "Sunken Dread.mp3", "Sunless Vault.mp3", "The Deep Rot.mp3"
]

def cargar_estado_musica():
    try:
        with open(MUSICA_ESTADO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"ultimo_fondo": None}

def guardar_estado_musica(estado):
    with open(MUSICA_ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)
    print(f"✅ Estado de música guardado: {estado}")

def seleccionar_fondo_disponible():
    estado_musica = cargar_estado_musica()
    ultimo_fondo = estado_musica.get("ultimo_fondo")
    fondos = FONDOS_DISPONIBLES.copy()
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
                    estado_musica["ultimo_fondo"] = fondo
                    guardar_estado_musica(estado_musica)
                    print(f"✅ Audio de fondo seleccionado: {full_path}")
                    return full_path
    for root, dirs, files in os.walk("."):
        for file in files:
            for fondo in FONDOS_DISPONIBLES:
                if file.lower() == fondo.lower():
                    full_path = os.path.join(root, file)
                    estado_musica["ultimo_fondo"] = fondo
                    guardar_estado_musica(estado_musica)
                    print(f"✅ Audio de fondo (única opción): {full_path}")
                    return full_path
    print("⚠️ No se encontró ningún archivo de fondo disponible.")
    return None

FONDO_AUDIO_FILE = seleccionar_fondo_disponible()

# ================================================================
# 🧼 LIMPIADOR DE PROMPTS
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        prompt = "A quiet night scene, bright lighting"
    prompt = re.sub(r"\n+", " ", prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r"[^\x00-\x7F]+", "", prompt)

    palabras_sucias = [
        r"\bgrainy\b", r"\bvhs\b", r"\bchiaroscuro\b", r"\bdirt\b", r"\bgrime\b",
        r"\bblemish\b", r"\bspots\b", r"\bterro\b", r"\bhorror\b", r"\bsangre\b",
        r"\bblood\b", r"\bgore\b", r"\bdemacrad[oa]s?\b", r"\bzombies?\b",
        r"\bdisfigured\b", r"\bwounds?\b", r"\bmonster\b"
    ]
    for pattern in palabras_sucias:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)

    prompt_base = re.sub(r"\s+", " ", prompt).strip()[:220]

    modificadores_calidad = (
        f", {ESTILO_VISUAL_ACTUAL}, color palette of {PALETA_COLOR_ACTUAL}, "
        "16:9 widescreen format, single solitary person in frame, exactly one person, "
        "person occupies at most 20-25% of the frame (medium or wide shot), "
        "clean smooth skin, natural facial complexion with light skin tone, "
        "attractive features, no blemishes, no cloned faces, no duplicate people, "
        "sharp focus, bright well-lit scene, no dark underexposed areas, "
        "no text, no watermark"
    )
    return prompt_base + modificadores_calidad

# ================================================================
# 🖼️ MINIATURA CON DEGRADADO DINÁMICO
# ================================================================
DEGRADADOS_MINIATURA = [
    {"top": (255, 30, 0), "bottom": (255, 140, 0)},
    {"top": (0, 255, 200), "bottom": (0, 100, 255)},
    {"top": (255, 215, 0), "bottom": (200, 50, 0)},
    {"top": (200, 0, 255), "bottom": (80, 0, 150)},
    {"top": (255, 255, 255), "bottom": (120, 120, 120)},
    {"top": (255, 0, 150), "bottom": (0, 200, 255)},
    {"top": (255, 200, 0), "bottom": (0, 0, 0)},
    {"top": (0, 200, 100), "bottom": (0, 50, 150)},
    {"top": (255, 100, 0), "bottom": (150, 0, 200)},
    {"top": (200, 0, 0), "bottom": (80, 0, 0)},
]
DEGRADADO_ACTUAL = random.choice(DEGRADADOS_MINIATURA)

def agregar_texto_miniatura(img_path, texto_portada):
    if not texto_portada:
        texto_portada = "CASO REAL"
    texto_portada = texto_portada.upper().strip()
    try:
        with Image.open(img_path) as img:
            img = img.convert("RGBA")
            w, h = img.size
            font_size = int(h * 0.13)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except Exception:
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except Exception:
                    font = ImageFont.load_default()
            dummy_draw = ImageDraw.Draw(img)
            bbox = dummy_draw.textbbox((0, 0), texto_portada, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = (w - text_w) / 2
            y = h - text_h - int(h * 0.08)
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            pad_x, pad_y = 35, 20
            draw_overlay.rectangle(
                [x - pad_x, y - pad_y, x + text_w + pad_x, y + text_h + pad_y * 2],
                fill=(0, 0, 0, 180)
            )
            img = Image.alpha_composite(img, overlay)
            mask = Image.new("L", (w, h), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.text((x, y), texto_portada, font=font, fill=255)
            gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw_grad = ImageDraw.Draw(gradient)
            c_top = DEGRADADO_ACTUAL["top"]
            c_bot = DEGRADADO_ACTUAL["bottom"]
            for i in range(h):
                factor = i / h
                r = int(c_top[0] + factor * (c_bot[0] - c_top[0]))
                g = int(c_top[1] + factor * (c_bot[1] - c_top[1]))
                b = int(c_top[2] + factor * (c_bot[2] - c_top[2]))
                draw_grad.line([(0, i), (w, i)], fill=(r, g, b, 255))
            draw_final = ImageDraw.Draw(img)
            stroke_w = 8
            for ox in range(-stroke_w, stroke_w + 1):
                for oy in range(-stroke_w, stroke_w + 1):
                    draw_final.text((x + ox, y + oy), texto_portada, font=font, fill=(0, 0, 0, 255))
            img.paste(gradient, (0, 0), mask)
            img.convert("RGB").save(img_path)
            print(f"✅ Texto '{texto_portada}' impreso en miniatura.")
    except Exception as e:
        print(f"⚠️ Error en miniatura: {e}")

# ================================================================
# LIMPIAR RESPUESTA JSON (CORREGIDO)
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
        # ✅ NO se escapan saltos de línea aquí: json.loads(strict=False) ya
        # tolera saltos de línea literales dentro de las cadenas, y hacerlo
        # manualmente corrompe la estructura del JSON.
        return json_str
    return respuesta

# ================================================================
# GENERAR GUION CON DEEPSEEK (con json5 y logging)
# ================================================================
def generar_guion(contexto_extra=""):
    prompt_base = f"""Eres un GUIONISTA Y DIRECTOR DE CINE DE MISTERIO.

Escribe un relato de eventos paranormales o misterio real en primera persona en español de aproximadamente 9.500 a 11.000 caracteres (1.600-1.850 palabras), ambientado en {UBICACION_HISTORIA}, México.
Divide la historia en 28 a 34 segmentos, CADA UNO de 45 a 55 palabras (esto asegura que cada segmento se narre en ~18-22 segundos a velocidad normal de TTS).

PERSONAJE PRINCIPAL (ÚNICO PARA ESTE VIDEO):
"{PERFIL_PERSONAJE}"

REGLAS DE TÍTULO:
- Debe ser DESCRIPTIVO y DIRECTO (50-80 caracteres).
- Ejemplo: "El misterio de la casona abandonada en {UBICACION_HISTORIA}"

REGLAS DE INICIO:
- La PRIMERA FRASE del relato debe ser un GANCHO IMPACTANTE.

REGLAS DE GENERACIÓN VISUAL:
1. PERSONAJE PRINCIPAL FIJO: En todos los segmentos usa la descripción exacta: "{PERFIL_PERSONAJE}".
2. CERO PERSONAJES CLONADOS: Escribe prompts pidiendo "single person".
3. PALETA DE COLOR: {PALETA_COLOR_ACTUAL}.
4. TEXTO ÚNICO EN ESPAÑOL: En el campo "texto" solo escribe la narración del relato en español.
5. IMAGEN_PROMPT: El campo 'imagen_prompt' debe ser un prompt fotográfico detallado EN INGLÉS que describa visualmente EXACTAMENTE lo que ocurre en el 'texto' de ese segmento. Incluye la ubicación, la hora, el personaje principal (si aparece), la acción y la atmósfera. Sé específico y evita descripciones genéricas.
   - La persona debe ocupar como máximo el 20-25% del encuadre (plano general o medio, nunca primer plano).
   - La persona debe ser descrita como de apariencia natural y agradable, sana, sin rasgos de sufrimiento ni deformidades.
6. ESTRUCTURA NARRATIVA: presentación, desarrollo con varios puntos de tensión, clímax, resolución — repartida en los segmentos.
7. MINIATURA: Debes generar también un campo 'miniatura_descripcion' (1-2 oraciones en español describiendo la escena o momento MÁS IMPACTANTE Y VISUAL del relato) y un 'miniatura_prompt' en inglés específico para esa escena, con composición dramática y atractiva para captar clics. A diferencia de las imágenes de los segmentos, la miniatura puede usar un encuadre más cercano (plano medio o medio-corto) para maximizar el impacto visual, pero sin llegar a primer plano extremo.

{contexto_extra}

Responde únicamente en formato JSON con esta estructura exacta:
{{
  "titulo": "Título descriptivo y directo",
  "palabras_portada": "CASO REAL",
  "descripcion": "Sinopsis completa... Síguenos en Facebook: {FACEBOOK_LINK} #leyendasurbanas #Paranormal #Misterio",
  "tags": "tag1, tag2, tag3, tag4, tag5",
  "miniatura_descripcion": "Breve descripción en español de la escena o momento más impactante y visual del relato (1-2 oraciones).",
  "miniatura_prompt": "Dramatic cinematic photo of [escena específica derivada de miniatura_descripcion] in {UBICACION_HISTORIA}, [paleta de color], striking and eye-catching composition, professional thumbnail photography, high visual impact, dramatic lighting, sharp focus, no text, no watermark, flawless hyperrealistic quality, no deformities, no blurriness, no artifacts, [personaje si aplica, ocupando un encuadre más cercano pero sin ser primer plano extremo]",
  "segmentos": [
    {{
      "texto": "Texto narrativo único en español para ser locutado por voz en off...",
      "imagen_prompt": "Detailed cinematic prompt in English for this specific scene: [describe the scene based on the 'texto' field]. Include {PERFIL_PERSONAJE} if present. Single subject, medium shot, bright well-lit, 16:9, no text, no gore"
    }}
  ]
}}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt_base}],
        "temperature": 0.7,
        "max_tokens": 7000,
        "response_format": {"type": "json_object"}
    }

    for intento in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            respuesta_json = r.json()
            respuesta = respuesta_json["choices"][0]["message"]["content"].strip()
            finish_reason = respuesta_json["choices"][0].get("finish_reason", "desconocido")

            print(f"📝 Respuesta cruda (primeros 300 chars): {respuesta[:300]}")
            print(f"🏁 Finish reason: {finish_reason}")

            json_str = limpiar_respuesta_json(respuesta)

            data = None
            try:
                data = json.loads(json_str, strict=False)
                print("✅ json.loads parseó exitosamente.")
            except json.JSONDecodeError as e:
                print(f"⚠️ json.loads falló: {e}. Intentando con json5...")
                try:
                    data = json5.loads(json_str)
                    print("✅ json5 parseó exitosamente.")
                except Exception as e5:
                    print(f"❌ json5 también falló: {e5}")
                    raise

            if "segmentos" in data and len(data["segmentos"]) >= 28:
                for seg in data["segmentos"]:
                    if "imagen_prompt" in seg:
                        seg["imagen_prompt"] = limpiar_prompt(seg["imagen_prompt"])
                print(f"✅ Guion generado exitosamente con {len(data['segmentos'])} segmentos.")
                return data
            else:
                print(f"⚠️ Número insuficiente de segmentos ({len(data.get('segmentos', []))}). Reintentando...")
                raise ValueError("Número insuficiente de segmentos")

        except Exception as e:
            print(f"❌ Intento {intento+1}/3 falló al procesar JSON de DeepSeek: {e}")
            time.sleep(5)

    print("❌ No se pudo generar un guion válido después de 3 intentos.")
    sys.exit(1)

# ================================================================
# EXPANSIÓN DE GUION (con json5 y logging)
# ================================================================
def expandir_guion(titulo, ultimos_segmentos_texto, intento_actual):
    contexto = f"""
La historia ya tiene un título: "{titulo}".
Los últimos segmentos generados son (texto únicamente):
{" --- ".join(ultimos_segmentos_texto[-3:])}

Continúa la historia de forma coherente a partir de ese punto. Genera aproximadamente 10 segmentos adicionales (cada uno de 45-55 palabras) que sigan el mismo estilo y temática. Incluye en cada segmento el campo "imagen_prompt" siguiendo las mismas reglas visuales (personaje máximo 25% del encuadre, apariencia natural, etc.).
Devuelve únicamente un array JSON llamado "segmentos_extra" con la misma estructura de objetos que en el guion original.
"""
    prompt = f"""Eres el mismo guionista. {contexto}

Responde únicamente con un JSON que contenga la clave "segmentos_extra" y un array de objetos con "texto" e "imagen_prompt".
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 3000,
        "response_format": {"type": "json_object"}
    }

    for intento in range(2):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            respuesta_json = r.json()
            respuesta = respuesta_json["choices"][0]["message"]["content"].strip()
            finish_reason = respuesta_json["choices"][0].get("finish_reason", "desconocido")

            print(f"📝 Respuesta expansión (primeros 300 chars): {respuesta[:300]}")
            print(f"🏁 Finish reason expansión: {finish_reason}")

            json_str = limpiar_respuesta_json(respuesta)

            data = None
            try:
                data = json.loads(json_str, strict=False)
                print("✅ json.loads en expansión parseó exitosamente.")
            except json.JSONDecodeError as e:
                print(f"⚠️ json.loads en expansión falló: {e}. Intentando con json5...")
                try:
                    data = json5.loads(json_str)
                    print("✅ json5 parseó la expansión exitosamente.")
                except Exception as e5:
                    print(f"❌ json5 también falló en expansión: {e5}")
                    raise

            if "segmentos_extra" in data and len(data["segmentos_extra"]) > 0:
                for seg in data["segmentos_extra"]:
                    seg["imagen_prompt"] = limpiar_prompt(seg["imagen_prompt"])
                print(f"✅ Expansión generada: {len(data['segmentos_extra'])} segmentos adicionales.")
                return data["segmentos_extra"]
            else:
                print("⚠️ La expansión no devolvió segmentos válidos.")
                raise ValueError("Expansión vacía")
        except Exception as e:
            print(f"❌ Intento de expansión {intento+1}/2 falló: {e}")
            time.sleep(5)

    print("❌ No se pudo generar expansión después de 2 intentos.")
    return []

# ================================================================
# GENERAR IMAGEN (3 intentos con 10s de espera)
# ================================================================
def generar_imagen(prompt, texto_segmento="", width=2048, height=1152, intentos=3):
    if texto_segmento:
        prompt = f"{prompt}, scene depicting: {texto_segmento[:150]}"
    prompt_limpio = limpiar_prompt(prompt)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    negative = (
        "oscuro, dark, underexposed, low light, heavy shadows, too dark, "
        "over-saturated reds, over-saturated oranges, manchas, textura fea, "
        "deforme, clonado, duplicado, gore, sangre, horror, terror, monstruo, "
        "demacrado, freckles, blemishes, skin spots, imperfections, "
        "close-up face, portrait, headshot, person filling frame, "
        "deformed face, disfigured, mutated, bad anatomy, extra limbs, "
        "extra fingers, asymmetrical eyes, malformed features, uncanny valley, "
        "gaunt, emaciated, ugly, grotesque"
    )
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_limpio,
        "negative_prompt": negative,
        "width": width,
        "height": height,
        "num_images": 1
    }
    for intento in range(intentos):
        try:
            print(f"🖼️ Intentando generar imagen (intento {intento+1}/{intentos})...")
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code == 200:
                url_img = r.json()["data"][0]["url"]
                print(f"✅ Imagen generada exitosamente en intento {intento+1}")
                return url_img
            else:
                print(f"⚠️ Respuesta no exitosa: {r.status_code} - {r.text[:100]}")
        except Exception as e:
            print(f"⚠️ Error en intento {intento+1}: {e}")
        if intento < intentos - 1:
            print(f"⏳ Esperando 10s antes de reintentar...")
            time.sleep(10)
    print("❌ No se pudo generar la imagen después de 3 intentos.")
    return None

# ================================================================
# GENERAR MINIATURA (5 intentos con backoff)
# ================================================================
def generar_miniatura(prompt, width=1280, height=720, intentos=5):
    prompt_limpio = limpiar_prompt(prompt)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    
    negative = (
        "oscuro, dark, underexposed, low light, heavy shadows, too dark, "
        "over-saturated reds, over-saturated oranges, manchas, textura fea, "
        "deforme, clonado, duplicado, gore, sangre, horror, terror, monstruo, "
        "demacrado, freckles, blemishes, skin spots, imperfections, "
        "close-up face, portrait, headshot, person filling frame, "
        "deformed face, disfigured, mutated, bad anatomy, extra limbs, "
        "extra fingers, asymmetrical eyes, malformed features, uncanny valley, "
        "gaunt, emaciated, ugly, grotesque, "
        "low quality, low resolution, boring composition, flat lighting, "
        "dull colors, amateur photography, plain background, empty background, "
        "poorly lit, washed out colors"
    )
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_limpio,
        "negative_prompt": negative,
        "width": width,
        "height": height,
        "num_images": 1
    }

    backoff = [5, 10, 15, 20, 25]
    for intento in range(intentos):
        print(f"🖼️ Intento {intento+1}/{intentos} generando miniatura...")
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code == 200:
                url_imagen = r.json()["data"][0]["url"]
                print(f"✅ Miniatura generada exitosamente (intento {intento+1}).")
                return url_imagen
            else:
                print(f"⚠️ Respuesta no exitosa: {r.status_code} - {r.text[:100]}")
        except Exception as e:
            print(f"⚠️ Error en intento {intento+1}: {e}")
        
        if intento < intentos - 1:
            espera = backoff[intento] if intento < len(backoff) else 30
            print(f"⏳ Esperando {espera}s antes de reintentar...")
            time.sleep(espera)
    
    print("❌ No se pudo generar la miniatura después de 5 intentos. El video se subirá sin miniatura personalizada (YouTube generará una automática).")
    return None

# ================================================================
# GENERAR AUDIO
# ================================================================
def generar_audio(texto, index):
    texto_limpio = re.sub(r"imagen_prompt.*", "", texto, flags=re.IGNORECASE)
    texto_limpio = re.sub(r"prompt.*", texto_limpio, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'[\{\}\[\]"]', "", texto_limpio)
    texto_limpio = re.sub(r"\s+", " ", texto_limpio).strip()

    if len(texto_limpio) < 10:
        print(f"⚠️ Texto de audio {index} demasiado corto, se omite.")
        return None

    filename = f"audio_{index}.mp3"

    async def _generar():
        communicate = edge_tts.Communicate(
            texto_limpio,
            CONFIG_VOZ_ACTUAL["voz"],
            rate=CONFIG_VOZ_ACTUAL["velocidad"],
            pitch=CONFIG_VOZ_ACTUAL["tono"]
        )
        await communicate.save(filename)

    try:
        asyncio.run(_generar())
        return filename
    except Exception as e:
        print(f"❌ Error audio {index}: {e}")
        return None

# ================================================================
# MONTAR VIDEO
# ================================================================
def montar_video(elementos, salida="video_final.mp4"):
    clips_video = []
    clips_audio = []
    duracion_total = 0.0

    for i, elem in enumerate(elementos):
        try:
            audio_clip = AudioFileClip(elem["audio_path"])
            duracion = audio_clip.duration
            duracion_total += duracion

            r = requests.get(elem["imagen_url"], timeout=30)
            r.raise_for_status()
            img_path = f"temp_img_{i}.jpg"
            with open(img_path, "wb") as f:
                f.write(r.content)
            with Image.open(img_path) as img:
                img_fitted = ImageOps.fit(img, (1920, 1080), Image.LANCZOS)
                img_fitted.save(img_path)

            if duracion > 35:
                duracion_mitad = duracion / 2
                clip1 = ImageClip(img_path, duration=duracion_mitad)
                clip2 = ImageClip(img_path, duration=duracion_mitad)
                clips_video.extend([clip1, clip2])
                audio_mitad = audio_clip.subclip(0, duracion_mitad)
                audio_mitad2 = audio_clip.subclip(duracion_mitad, duracion)
                clips_audio.extend([audio_mitad, audio_mitad2])
                print(f"🔹 Segmento {i} de {duracion:.1f}s dividido en 2 partes.")
            else:
                video_clip = ImageClip(img_path, duration=duracion)
                clips_video.append(video_clip)
                clips_audio.append(audio_clip)

        except Exception as e:
            print(f"⚠️ Error en segmento {i}: {e}")
            continue

    if not clips_video or not clips_audio:
        raise ValueError("No se pudieron procesar los clips para el montaje.")

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
            print(f"🎵 Audio de fondo mezclado al 8%: {FONDO_AUDIO_FILE}")
        except Exception as e:
            print(f"⚠️ Error en audio de fondo: {e}")
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

    print(f"✅ Video creado exitosamente: {salida}")
    return salida, duracion_total

# ================================================================
# LIMPIEZA
# ================================================================
def limpiar_archivos_temporales():
    for f in os.listdir("."):
        if (f.startswith("temp_img_") or f.startswith("audio_")) and (f.endswith(".jpg") or f.endswith(".mp3")):
            try:
                os.remove(f)
            except Exception:
                pass
    for aux in ["video_final.mp4", "miniatura.jpg"]:
        if os.path.exists(aux):
            try:
                os.remove(aux)
            except Exception:
                pass
    print("🧹 Archivos temporales eliminados correctamente.")

# ================================================================
# SUBIR A YOUTUBE
# ================================================================
def subir_a_youtube(video_path, miniatura_path, titulo, descripcion, etiquetas):
    creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
    youtube = build("youtube", "v3", credentials=creds)
    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]
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
    print(f"✅ Video subido exitosamente: https://youtu.be/{video_id}")

    if miniatura_path and os.path.exists(miniatura_path):
        try:
            media_thumb = MediaFileUpload(miniatura_path, chunksize=-1, resumable=True)
            youtube.thumbnails().set(videoId=video_id, media_body=media_thumb).execute()
            print("✅ Miniatura subida con éxito")
        except Exception as e:
            print(f"⚠️ Error al subir miniatura: {e}")

# ================================================================
# FUNCIONES DE VERIFICACIÓN DE PUBLICACIÓN DIARIA (CORREGIDAS)
# ================================================================
def verificar_publicacion_hoy():
    estado = cargar_estado_musica()
    ultima = estado.get("ultima_publicacion_exitosa")
    if not ultima:
        return False
    hoy = datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()  # ✅ CORREGIDO
    return ultima == hoy

def marcar_publicacion_exitosa():
    estado = cargar_estado_musica()
    hoy = datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()  # ✅ CORREGIDO
    estado["ultima_publicacion_exitosa"] = hoy
    guardar_estado_musica(estado)
    print(f"✅ Publicación exitosa marcada para hoy: {hoy}")

# ================================================================
# MAIN
# ================================================================
def verificar_envs():
    required = ["DEEPSEEK_API_KEY", "AGNES_API_KEY", "YOUTUBE_USER_TOKEN"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"❌ Faltan variables de entorno: {', '.join(missing)}")
        sys.exit(1)

def main():
    verificar_envs()

    if verificar_publicacion_hoy():
        print("✅ Ya se publicó un video hoy. Esta es la ejecución de respaldo, no se necesita generar otro. Saliendo.")
        sys.exit(0)

    print(f"🎬 Bot YouTube | Voz: {CONFIG_VOZ_ACTUAL['voz']} (+12%)")
    print(f"🧑 Personaje: {PERFIL_PERSONAJE}")
    print(f"📍 Historia ambientada en: {UBICACION_HISTORIA}")
    print(f"🎨 Paleta: {PALETA_COLOR_ACTUAL[:80]}...")
    print(f"🎵 Fondo musical: {FONDO_AUDIO_FILE if FONDO_AUDIO_FILE else 'Ninguno'}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    guion_data = generar_guion()
    titulo_video = guion_data.get("titulo", "Relato Paranormal Real")
    palabras_portada = guion_data.get("palabras_portada", "CASO REAL")
    descripcion_video = guion_data.get("descripcion", f"Relato paranormal.\n\nSíguenos en Facebook: {FACEBOOK_LINK}")
    tags_video = guion_data.get("tags", "relatos, leyendas, mexico")
    segmentos = guion_data.get("segmentos", [])

    textos_registrados = set()
    elementos_validos = []
    imagen_ultimo_recurso = None

    for i, seg in enumerate(segmentos):
        texto_limpio = seg["texto"].strip().lower()
        if texto_limpio in textos_registrados:
            print(f"⚠️ Segmento {i} repetido, se genera de todas formas (puede afectar duración).")
        textos_registrados.add(texto_limpio)

        if i > 0:
            time.sleep(3)

        # Intenta generar imagen con reintentos (3 intentos, 10s espera)
        url_img = generar_imagen(seg.get("imagen_prompt", ""), texto_segmento=seg["texto"], width=2048, height=1152)
        if url_img:
            imagen_ultimo_recurso = url_img
        else:
            # Si falla, reutiliza la última imagen generada con éxito
            if imagen_ultimo_recurso:
                print(f"⚠️ Reutilizando imagen anterior para segmento {i}.")
                url_img = imagen_ultimo_recurso
            else:
                print(f"❌ No se pudo generar ni reutilizar imagen para segmento {i}. Saltando...")
                continue

        audio_file = generar_audio(seg["texto"], i)
        if not audio_file:
            continue

        elementos_validos.append({"imagen_url": url_img, "audio_path": audio_file})

    if not elementos_validos:
        print("❌ No hay elementos válidos para crear el video.")
        sys.exit(1)

    # Validar duración y expandir si es necesario
    duracion_actual = sum(AudioFileClip(e["audio_path"]).duration for e in elementos_validos)
    print(f"⏱️ Duración estimada del video (solo narración): {duracion_actual/60:.1f} minutos")

    intentos_expansion = 0
    while duracion_actual < DURACION_MINIMA_SEGUNDOS and intentos_expansion < MAX_INTENTOS_EXPANSION:
        print(f"⚠️ Duración {duracion_actual:.1f}s < {DURACION_MINIMA_SEGUNDOS}s. Intentando expansión {intentos_expansion+1}...")
        ultimos_textos = [seg["texto"] for seg in segmentos[-3:]] if len(segmentos) >= 3 else [seg["texto"] for seg in segmentos]
        nuevos_segmentos = expandir_guion(titulo_video, ultimos_textos, intentos_expansion+1)
        if nuevos_segmentos:
            for j, seg in enumerate(nuevos_segmentos):
                url_img = generar_imagen(seg.get("imagen_prompt", ""), texto_segmento=seg["texto"], width=2048, height=1152)
                if url_img:
                    imagen_ultimo_recurso = url_img
                else:
                    if imagen_ultimo_recurso:
                        print(f"⚠️ Reutilizando imagen anterior para expansión {j}.")
                        url_img = imagen_ultimo_recurso
                    else:
                        print(f"❌ No se pudo generar imagen para expansión {j}. Saltando...")
                        continue
                audio_file = generar_audio(seg["texto"], len(elementos_validos) + j)
                if audio_file:
                    elementos_validos.append({"imagen_url": url_img, "audio_path": audio_file})
                    segmentos.append(seg)
            duracion_actual = sum(AudioFileClip(e["audio_path"]).duration for e in elementos_validos)
            print(f"⏱️ Duración después de expansión: {duracion_actual/60:.1f} minutos")
            intentos_expansion += 1
        else:
            print("❌ No se pudo generar expansión. Abortando.")
            sys.exit(1)

    if duracion_actual < DURACION_MINIMA_SEGUNDOS:
        print(f"❌ Duración final ({duracion_actual/60:.1f} min) insuficiente después de {MAX_INTENTOS_EXPANSION} expansiones. Abortando.")
        sys.exit(1)

    print(f"✅ Duración final aceptable: {duracion_actual/60:.1f} minutos.")

    # Generar miniatura
    print("🖼️ Generando miniatura...")
    miniatura_path = "miniatura.jpg"
    miniatura_url = generar_miniatura(guion_data.get("miniatura_prompt", "Dark mysterious scene"))

    if miniatura_url:
        try:
            r = requests.get(miniatura_url, timeout=30)
            r.raise_for_status()
            with open(miniatura_path, "wb") as f:
                f.write(r.content)
            with Image.open(miniatura_path) as img:
                ImageOps.fit(img, (1280, 720), Image.LANCZOS).save(miniatura_path)
            agregar_texto_miniatura(miniatura_path, palabras_portada)
            print("✅ Miniatura procesada y guardada.")
        except Exception as e:
            print(f"⚠️ Error al descargar o procesar la miniatura: {e}")
            miniatura_path = None
    else:
        print("⚠️ No se generó URL de miniatura. El video se subirá sin miniatura personalizada.")
        miniatura_path = None

    # Montar video
    print("🎬 Montando video...")
    video_path, duracion_final = montar_video(elementos_validos)
    print(f"⏱️ Duración final del video generado: {duracion_final/60:.1f} minutos")

    # Subir a YouTube
    print("⬆️ Subiendo a YouTube...")
    subir_a_youtube(video_path, miniatura_path, titulo_video, descripcion_video, tags_video)

    # Marcar publicación exitosa
    marcar_publicacion_exitosa()

    limpiar_archivos_temporales()
    print("🎉 Proceso completado exitosamente.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
