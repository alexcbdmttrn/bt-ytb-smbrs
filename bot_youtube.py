import asyncio
from datetime import datetime
import json
import os
import random
import re
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

# ================================================================
# 🎤 BANCO DE 12 VOCES (velocidad estandarizada a +12%)
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
    # ❄️ FRÍAS (10 paletas - más probables)
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
    # 🔥 CÁLIDAS (6 paletas - menos probables)
    "Deep crimson red, pitch black shadow, intense orange emergency light accents",
    "Blood red and burnt orange, dark charcoal shadows, hellish glow",
    "Warm amber and dark mahogany, golden candlelight, deep brown shadows",
    "Fiery sunset orange, deep purple shadows, intense red highlights",
    "Rusty red and dark brown, sepia undertones, warm vintage look",
    "Toxic lime green and pitch black, eerie chemical glow, radioactive haze",
]
PALETA_COLOR_ACTUAL = random.choice(PALETAS_COLOR)

# ================================================================
# 📷 ESTILOS VISUALES CON ILUMINACIÓN CLARA
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
# 🧑 GENERADOR DE PERSONAJES (PIEL CLARA / BLANCA)
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
        "wearing a traditional embroidered blouse (huipil) and long skirt",
        "wearing a white guayabera shirt and dark pants",
        "wearing a charro suit with silver buttons",
        "wearing a simple cotton dress and sandals",
        "wearing a baseball cap and hoodie",
    ]
    cabellos = [
        "short curly dark hair",
        "long straight black hair tied back",
        "grey cropped hair",
        "wavy brown shoulder-length hair",
        "bald with a short beard",
        "long grey braided hair",
        "short spiky black hair",
        "chestnut brown curly hair",
        "long wavy dark hair with grey streaks",
        "short salt-and-pepper hair",
    ]
    # 🔥 SOLO RASGOS DE PIEL CLARA (sin indígenas ni morenos)
    rasgos = [
        "with mestizo features and light olive skin",
        "with light brown skin and freckles",
        "with olive skin and a strong jaw",
        "with pale skin and green eyes",
        "with fair skin and blue eyes",
        "with tan skin and a warm smile",
        "with light beige skin and a serious expression",
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
# 🎵 AUDIO DE FONDO (CON PERSISTENCIA PARA EVITAR REPETICIÓN)
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
    """Selecciona un fondo evitando repetir el último usado (persistido en archivo)."""
    estado_musica = cargar_estado_musica()
    ultimo_fondo = estado_musica.get("ultimo_fondo")
    
    fondos = FONDOS_DISPONIBLES.copy()
    
    # Evitar el último fondo usado
    if ultimo_fondo and ultimo_fondo in fondos:
        fondos.remove(ultimo_fondo)
        print(f"🎵 Evitando repetir fondo: {ultimo_fondo}")
    
    # Shuffle para aleatoriedad
    random.shuffle(fondos)
    
    # Buscar en el repositorio
    for root, dirs, files in os.walk("."):
        if "/." in root or "\\." in root:
            continue
        for file in files:
            for fondo in fondos:
                if file.lower() == fondo.lower():
                    full_path = os.path.join(root, file)
                    # Actualizar estado con el nuevo fondo
                    estado_musica["ultimo_fondo"] = fondo
                    guardar_estado_musica(estado_musica)
                    print(f"✅ Audio de fondo seleccionado: {full_path}")
                    return full_path
    
    # Si no hay más opciones, usar el primero disponible
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
# 🧼 LIMPIADOR DE PROMPTS CON ILUMINACIÓN CLARA
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

    prompt = re.sub(r"\s+", " ", prompt).strip()

    # 🔥 FORZAR ILUMINACIÓN CLARA Y PIEL CLARA
    modificadores_calidad = (
        f", {ESTILO_VISUAL_ACTUAL}, color palette of {PALETA_COLOR_ACTUAL}, "
        "16:9 widescreen format, single solitary person in frame, exactly one person, "
        "clean smooth skin, natural facial complexion with light skin tone, no face blemishes, "
        "no cloned faces, no duplicate people, sharp focus, bright well-lit scene, no dark underexposed areas, "
        "no text, no watermark"
    )
    return (prompt + modificadores_calidad)[:500]

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
    {"top": (150, 200, 255), "bottom": (50, 50, 100)},
    {"top": (255, 255, 100), "bottom": (200, 100, 0)},
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
            except:
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
# FALLBACK
# ================================================================
def generar_fallback(respuesta):
    print("⚠️ Usando fallback limpiado.")
    texto_narrativo = re.sub(
        r"imagen_prompt.*?(?=(texto|$))",
        "",
        respuesta,
        flags=re.DOTALL | re.IGNORECASE,
    )
    texto_narrativo = re.sub(r"prompt.*?:", "", texto_narrativo, flags=re.IGNORECASE)
    texto_narrativo = re.sub(r'[\{\}\[\]"]', "", texto_narrativo)
    texto_narrativo = re.sub(r"\s+", " ", texto_narrativo).strip()

    segmentos = []
    chars_por_segmento = 450
    for i in range(0, len(texto_narrativo), chars_por_segmento):
        segmento = texto_narrativo[i: i + chars_por_segmento]
        if len(segmento.strip()) > 40:
            segmentos.append({
                "texto": segmento,
                "imagen_prompt": "Cinematic 35mm photograph of a quiet street in Mexico City at night, 16:9, 2k, hyperrealistic"
            })

    tags_fallback = "relatos paranormales, leyendas urbanas, Mexico, misterio, suspenso"
    return {
        "titulo": "El Misterio Nocturno de la Calle Madero | Relato Real",
        "palabras_portada": "CASO REAL",
        "descripcion": f"Un relato paranormal.\n\nSíguenos en Facebook: {FACEBOOK_LINK}\n\n#leyendasurbanas #Paranormal #Misterio",
        "tags": tags_fallback,
        "miniatura_prompt": "Cinematic portrait of a Mexican person at night, 16:9, 2k",
        "segmentos": segmentos[:24],
    }

# ================================================================
# GENERAR GUION CON DEEPSEEK (CON TÍTULO DIRECTO Y GANCHO)
# ================================================================
def generar_guion():
    prompt = f"""Eres un GUIONISTA Y DIRECTOR DE CINE DE MISTERIO.

Escribe un relato de eventos paranormales o misterio real en primera persona (~9000 caracteres), ambientado en el estado de {UBICACION_HISTORIA}, México.
Divide la historia en 20 a 24 segmentos cortos.

PERSONAJE PRINCIPAL (ÚNICO PARA ESTE VIDEO):
"{PERFIL_PERSONAJE}"

REGLAS DE TÍTULO (IMPORTANTE PARA CTR):
- Debe ser DESCRIPTIVO y DIRECTO. Sin metáforas confusas.
- Debe decir EXACTAMENTE de qué trata el video.
- Ejemplo BUENO: "El misterio del manicomio abandonado en Hidalgo"
- Ejemplo MALO: "El guardián del pabellón" (demasiado vago)
- Entre 50 y 80 caracteres exactos.

REGLAS DE INICIO (IMPORTANTE PARA RETENCIÓN):
- La PRIMERA FRASE del relato debe ser un GANCHO IMPACTANTE.
- Ejemplo: "Esa noche en el manicomio abandonado, supe que no estaba solo."
- Debe resumir el misterio y enganchar al espectador en los primeros 5 segundos.

REGLAS DE GENERACIÓN VISUAL Y PERSONAJES:
1. PERSONAJE PRINCIPAL FIJO: En todos los segmentos donde aparezca el protagonista, USA EXACTAMENTE ESTA DESCRIPCIÓN EN INGLÉS: "{PERFIL_PERSONAJE}".
2. CERO PERSONAJES CLONADOS: Escribe los prompts pidiendo SIEMPRE "single person" o "one solitary character".
3. PALETA DE COLOR DE ESTE VIDEO: {PALETA_COLOR_ACTUAL}. NO uses luces naranjas ni rojas a menos que sea una llama directa.
4. TEXTO ÚNICO: Prohibido repetir frases, moralejas o reflexiones de cierre. Cada segmento debe aportar trama nueva.
5. AMBIENTACIÓN LOCAL: La historia debe incluir referencias a lugares, costumbres o tradiciones del estado de {UBICACION_HISTORIA}.

Responde con este JSON estructurado:
{{
  "titulo": "Título descriptivo y directo (50-80 caracteres)",
  "palabras_portada": "PALABRA IMPACTO",
  "descripcion": "Sinopsis completa... Síguenos en Facebook: {FACEBOOK_LINK} #leyendasurbanas #Paranormal #Misterio #mexico",
  "tags": "tag1, tag2, tag3, ..., tag25",
  "miniatura_prompt": "Horizontal 16:9 cinematic image prompt of {PERFIL_PERSONAJE} in a mysterious location in {UBICACION_HISTORIA}, intense facial expression, high contrast, bright well-lit scene, {PALETA_COLOR_ACTUAL}",
  "segmentos": [
    {{
      "texto": "Texto narrativo único en español... (primera frase como gancho)",
      "imagen_prompt": "Detailed cinematic prompt in English with {PERFIL_PERSONAJE} if present, single subject, clean smooth face, bright well-lit, 16:9, no text"
    }}
  ]
}}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 5000,
        "response_format": {"type": "json_object"}
    }

    for intento in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=150)
            r.raise_for_status()
            respuesta = r.json()["choices"][0]["message"]["content"].strip()
            json_str = limpiar_respuesta_json(respuesta)
            data = json.loads(json_str)

            if "segmentos" not in data or len(data["segmentos"]) == 0:
                raise ValueError("Sin segmentos válidos")

            for seg in data["segmentos"]:
                if "imagen_prompt" in seg:
                    seg["imagen_prompt"] = limpiar_prompt(seg["imagen_prompt"])

            return data
        except Exception as e:
            print(f"❌ Intento {intento+1}/3 falló: {e}")
            time.sleep(3)
    return generar_fallback(respuesta)

# ================================================================
# GENERAR IMAGEN CON NEGATIVE PROMPT
# ================================================================
def generar_imagen(prompt, width=2048, height=1152, intentos=3):
    prompt_limpio = limpiar_prompt(prompt)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_limpio,
        "negative_prompt": "oscuro, dark, underexposed, low light, heavy shadows, too dark, over-saturated reds, over-saturated oranges, piel oscura, moreno, indígena, manchas, textura fea, deforme, clonado, duplicado, gore, sangre, horror, terror, monstruo, demacrado",
        "width": width,
        "height": height,
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
# GENERAR AUDIO
# ================================================================
def generar_audio(texto, index):
    texto_limpio = re.sub(r"imagen_prompt.*", "", texto, flags=re.IGNORECASE).strip()
    if not texto_limpio:
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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_generar())
        loop.close()
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
                img_fitted = ImageOps.fit(img, (1920, 1080), Image.Resampling.LANCZOS)
                img_fitted.save(img_path)

            video_clip = ImageClip(img_path).set_duration(duracion)
            clips_video.append(video_clip)
            clips_audio.append(audio_clip)
        except Exception as e:
            print(f"⚠️ Error en segmento {i}: {e}")
            continue

    video = concatenate_videoclips(clips_video, method="compose")
    audio_narracion = concatenate_audioclips(clips_audio)
    duracion_total = audio_narracion.duration

    # Usar el fondo seleccionado (evita repetición)
    if FONDO_AUDIO_FILE and os.path.exists(FONDO_AUDIO_FILE):
        try:
            fondo_clip = AudioFileClip(FONDO_AUDIO_FILE)
            if fondo_clip.duration < duracion_total:
                veces = int(duracion_total / fondo_clip.duration) + 1
                fondo_clip = concatenate_audioclips([fondo_clip] * veces)
            fondo_clip = fondo_clip.subclip(0, duracion_total).volumex(0.08)
            audio_final = CompositeAudioClip([audio_narracion, fondo_clip])
            print(f"🎵 Audio de fondo mezclado al 8%: {FONDO_AUDIO_FILE}")
        except Exception as e:
            print(f"⚠️ Error en audio de fondo: {e}")
            audio_final = audio_narracion
    else:
        audio_final = audio_narracion

    video = video.set_audio(audio_final)
    video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")
    return salida

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
    print(f"✅ Video subido: https://youtu.be/{video_id}")

    if miniatura_path and os.path.exists(miniatura_path):
        try:
            media_thumb = MediaFileUpload(miniatura_path, chunksize=-1, resumable=True)
            youtube.thumbnails().set(videoId=video_id, media_body=media_thumb).execute()
            print("✅ Miniatura subida")
        except Exception as e:
            print(f"⚠️ Error miniatura: {e}")

# ================================================================
# MAIN
# ================================================================
def main():
    print(f"🎬 Bot YouTube | Voz: {CONFIG_VOZ_ACTUAL['voz']} (+12%)")
    print(f"🧑 Personaje: {PERFIL_PERSONAJE}")
    print(f"📍 Historia ambientada en: {UBICACION_HISTORIA}")
    print(f"🎨 Paleta: {PALETA_COLOR_ACTUAL[:80]}...")
    print(f"🎵 Fondo musical: {FONDO_AUDIO_FILE if FONDO_AUDIO_FILE else 'Ninguno'}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    guion_data = generar_guion()
    if not guion_data:
        print("❌ No se pudo generar el guion.")
        return

    titulo_video = guion_data.get("titulo", "Relato Paranormal")
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
            print(f"⚠️ Segmento {i} ignorado por repetición.")
            continue
        textos_registrados.add(texto_limpio)

        if i > 0:
            time.sleep(4)

        url_img = generar_imagen(seg["imagen_prompt"], width=2048, height=1152)
        if url_img:
            imagen_ultimo_recurso = url_img
        elif imagen_ultimo_recurso:
            url_img = imagen_ultimo_recurso
        else:
            continue

        audio_file = generar_audio(seg["texto"], i)
        if not audio_file:
            continue

        elementos_validos.append({"imagen_url": url_img, "audio_path": audio_file})

    if not elementos_validos:
        print("❌ No hay elementos válidos.")
        return

    print("🖼️ Generando miniatura...")
    miniatura_path = "miniatura.jpg"
    miniatura_url = generar_imagen(guion_data.get("miniatura_prompt", "Dark mysterious scene"), width=1280, height=720)
    
    if miniatura_url:
        try:
            r = requests.get(miniatura_url, timeout=30)
            r.raise_for_status()
            with open(miniatura_path, "wb") as f:
                f.write(r.content)
            with Image.open(miniatura_path) as img:
                ImageOps.fit(img, (1280, 720), Image.Resampling.LANCZOS).save(miniatura_path)
            agregar_texto_miniatura(miniatura_path, palabras_portada)
        except Exception as e:
            print(f"⚠️ Error en miniatura: {e}")
            miniatura_path = None

    print("🎬 Montando video...")
    video_path = montar_video(elementos_validos)

    print("⬆️ Subiendo a YouTube...")
    subir_a_youtube(video_path, miniatura_path, titulo_video, descripcion_video, tags_video)

    print("🎉 Proceso completado exitosamente")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
