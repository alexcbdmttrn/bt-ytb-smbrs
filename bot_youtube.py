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
# CONFIGURACIÓN (variables desde GitHub Secrets)
# ================================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
AGNES_API_KEY = os.getenv("AGNES_API_KEY")
YOUTUBE_USER_TOKEN = (
    json.loads(os.getenv("YOUTUBE_USER_TOKEN"))
    if os.getenv("YOUTUBE_USER_TOKEN")
    else {}
)

FACEBOOK_LINK = "https://www.facebook.com/profile.php?id=61593237382982"

# ================================================================
# 🎤 BANCO DE 12 VOCES (Dobles variaciones)
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural", "velocidad": "+14%", "tono": "-2Hz"},
    {"voz": "es-MX-DaliaNeural", "velocidad": "+12%", "tono": "+0Hz"},
    {"voz": "es-ES-AlvaroNeural", "velocidad": "+15%", "tono": "-3Hz"},
    {"voz": "es-ES-ElviraNeural", "velocidad": "+13%", "tono": "+1Hz"},
    {"voz": "es-CO-SalomeNeural", "velocidad": "+11%", "tono": "-1Hz"},
    {"voz": "es-AR-ElenaNeural", "velocidad": "+14%", "tono": "+2Hz"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+15%", "tono": "-2Hz"},
    {"voz": "es-PE-CamilaNeural", "velocidad": "+12%", "tono": "+0Hz"},
    {"voz": "es-US-PalomaNeural", "velocidad": "+13%", "tono": "-1Hz"},
    {"voz": "es-ES-XimenaNeural", "velocidad": "+14%", "tono": "+1Hz"},
    {"voz": "es-MX-CandelaNeural", "velocidad": "+10%", "tono": "-3Hz"},
    {"voz": "es-ES-AbrilNeural", "velocidad": "+15%", "tono": "-2Hz"},
]

CONFIG_VOZ_ACTUAL = random.choice(VOCES_DISPONIBLES)

# ================================================================
# 🎨 BANCO DE 12 ESTILOS VISUALES
# ================================================================
ESTILOS_VISUALES = [
    "35mm grainy vintage film photograph, vhs tape aesthetic from 1990s",
    "Dark chiaroscuro oil painting style, dramatic deep shadows, gothic atmosphere",
    "Modern cinematic thriller photography, volumetric foggy light, sharp focus",
    "Documentary realistic flash photography, dark night ambient, raw camera look",
    "Desaturated cold film look, moody cinematic lighting, 8k hyperrealistic photo",
    "Vaporwave neon noir style, intense magenta and cyan highlights, retro 80s glow",
    "Watercolor gothic ink illustration, dark wet textures, blurred eerie edges",
    "Retro 80s horror VHS screengrab, scanlines, grainy texture, analog decay",
    "Hyperrealistic night vision photography, grainy green-tinted surveillance look",
    "Analog horror found footage style, distorted lens, high contrast shadows",
    "Soviet brutalist architectural photography, cold concrete, harsh stark lighting",
    "Expressionist german silent film style, high contrast black and white, dramatic angles",
]

ESTILO_VISUAL_ACTUAL = random.choice(ESTILOS_VISUALES)

# ================================================================
# 🎨 BANCO DE 10 PALETAS DE COLOR
# ================================================================
PALETAS_COLOR = [
    "Deep crimson red, pitch black shadow, intense orange emergency light accents",
    "Cold cyan blue fog, navy blue shadows, pale white moonlight",
    "Muted sepia tones, dark brown amber glow, high contrast shadow",
    "Emerald green twilight haze, dark moss green hues, striking highlights",
    "Neon purple and electric pink, deep violet shadows, cyberpunk glitch lights",
    "Electric yellow and charcoal black, stark contrast, dusty atmospheric haze",
    "Dark teal and gold amber, vintage brass tones, warm dim candlelight",
    "Monochrome high contrast, pure white highlights, deep obsidian black shadows",
    "Blood orange and deep navy, fiery sunset remnants, dark stormy sky",
    "Toxic lime green and pitch black, eerie chemical glow, radioactive haze",
]

PALETA_COLOR_ACTUAL = random.choice(PALETAS_COLOR)

# ================================================================
# 🌟 BANCO DE 12 PROTAGONISTAS
# ================================================================
PROTAGONISTAS = [
    "un trailero de 45 años que viaja por carreteras nocturnas de México",
    "una joven estudiante de medicina de 22 años en un hospital antiguo",
    "un oficial de policía de 38 años en su turno nocturno de patrulla",
    "un agricultor de 50 años en una hacienda del siglo XIX en el campo",
    "un fotógrafo urbano de 28 años explorando edificios abandonados",
    "un taxista nocturno de 55 años que recoge pasajeros en zonas peligrosas",
    "un velador de 60 años en un panteón viejo durante la noche de muertos",
    "un arqueólogo de 40 años excavando una zona prehispánica en la selva",
    "una periodista de investigación de 35 años tras una pista en un pueblo fantasma",
    "un enfermero de 30 años en un psiquiátrico abandonado en las afueras",
    "un minero de 48 años en una mina clausurada en el norte de México",
    "una bailarina de 25 años en un teatro viejo y embrujado del centro histórico",
]

PROTAGONISTA_SELECCIONADO = random.choice(PROTAGONISTAS)

# ================================================================
# 🖼️ BANCO DE 12 DEGRADADOS PARA MINIATURA
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

# ================================================================
# LISTA DE AUDIO DE FONDO
# ================================================================
FONDOS_DISPONIBLES = [
    "Ash and Marrow.mp3",
    "Black Maw.mp3",
    "Cold Hollow.mp3",
    "Hollow Marrow.mp3",
    "Sunken Dread.mp3",
    "Sunless Vault.mp3",
    "The Deep Rot.mp3",
]

def seleccionar_fondo_disponible():
    fondos = FONDOS_DISPONIBLES.copy()
    random.shuffle(fondos)
    for root, dirs, files in os.walk("."):
        if "/." in root or "\\." in root:
            continue
        for file in files:
            for fondo in fondos:
                if file.lower() == fondo.lower():
                    full_path = os.path.join(root, file)
                    print(f"✅ Audio de fondo encontrado: {full_path}")
                    return full_path
    print("⚠️ No se encontró ningún archivo de fondo disponible.")
    return None

FONDO_AUDIO_FILE = seleccionar_fondo_disponible()
if FONDO_AUDIO_FILE:
    print(f"🎵 Audio de fondo seleccionado: {FONDO_AUDIO_FILE}")
else:
    print("⚠️ No se usará audio de fondo.")

# ================================================================
# LIMPIAR PROMPTS DE IMAGEN (inyección dinámica de estilo y paleta)
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        prompt = "Mexican street at night, dark ambiance"

    prompt = re.sub(r"\n+", " ", prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r"[^\x00-\x7F]+", "", prompt)

    palabras_prohibidas = [
        r"\bterror\b", r"\bhorror\b", r"\bsangre\b", r"\bblood\b", r"\bgore\b",
        r"\bdemacrad[oa]s?\b", r"\bzombies?\b", r"\bmuert[oa]s?\b", r"\bmatanza\b",
        r"\bscary face\b", r"\bmonster\b", r"\bdisfigured\b", r"\bwounds?\b",
    ]
    for pattern in palabras_prohibidas:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)

    prompt = re.sub(r"\s+", " ", prompt).strip()

    estilo_dinamico = (
        f", {ESTILO_VISUAL_ACTUAL}, color palette of {PALETA_COLOR_ACTUAL}, "
        "16:9 widescreen format, realistic Mexican human features, unique face, "
        "sharp details, clean anatomical proportions, no text, no letters, no logo"
    )
    return (prompt + estilo_dinamico)[:500]

# ================================================================
# AGREGAR TEXTO A LA MINIATURA CON DEGRADADO DINÁMICO
# ================================================================
def agregar_texto_miniatura(img_path, texto_portada):
    """Añade texto con degradado dinámico (rojo/naranja u otro) y fondo oscuro."""
    if not texto_portada:
        texto_portada = "CASO REAL"
    texto_portada = texto_portada.upper().strip()

    try:
        with Image.open(img_path) as img:
            img = img.convert("RGBA")
            w, h = img.size

            font_size = int(h * 0.13)
            try:
                font = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
                )
            except:
                font = ImageFont.load_default()

            dummy_draw = ImageDraw.Draw(img)
            bbox = dummy_draw.textbbox((0, 0), texto_portada, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            x = (w - text_w) / 2
            y = h - text_h - int(h * 0.08)

            # 1. Fondo oscuro de contraste
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw_overlay = ImageDraw.Draw(overlay)
            pad_x, pad_y = 35, 20
            draw_overlay.rectangle(
                [x - pad_x, y - pad_y, x + text_w + pad_x, y + text_h + pad_y * 2],
                fill=(0, 0, 0, 180),
            )
            img = Image.alpha_composite(img, overlay)

            # 2. Máscara para el degradado
            mask = Image.new("L", (w, h), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.text((x, y), texto_portada, font=font, fill=255)

            # 3. Crear degradado dinámico (seleccionado aleatoriamente)
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

            # 4. Trazo negro grueso (borde)
            draw_final = ImageDraw.Draw(img)
            stroke_w = 8
            for ox in range(-stroke_w, stroke_w + 1):
                for oy in range(-stroke_w, stroke_w + 1):
                    draw_final.text(
                        (x + ox, y + oy), texto_portada, font=font, fill=(0, 0, 0, 255)
                    )

            # 5. Aplicar degradado usando la máscara
            img.paste(gradient, (0, 0), mask)

            img.convert("RGB").save(img_path)
            print(f"✅ Texto estilo terror con degradado dinámico '{texto_portada}' en miniatura.")
    except Exception as e:
        print(f"⚠️ Error agregando texto a miniatura: {e}")

# ================================================================
# LIMPIAR RESPUESTA JSON
# ================================================================
def limpiar_respuesta_json(respuesta):
    respuesta = re.sub(r"```json\s*", "", respuesta)
    respuesta = re.sub(r"```\s*", "", respuesta)
    inicio = respuesta.find("{")
    fin = respuesta.rfind("}")
    if inicio != -1 and fin != -1:
        json_str = respuesta[inicio: fin + 1]
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
                "imagen_prompt": (
                    "Cinematic 35mm photograph of a quiet street in Mexico City at"
                    " night, warm streetlamps, fog, 16:9, 2k, hyperrealistic"
                ),
            })

    tags_fallback = (
        "relatos paranormales, leyendas urbanas, Mexico, misterio, suspenso,"
        " casos reales, historias de miedo, la llorona, nahuales, casas"
        " embrujadas, centro historico, testimonios reales, mitos mexicanos,"
        " apariciones, espectros, noche, podcast paranormal"
    )
    return {
        "titulo": "El Misterio Nocturno de la Calle Madero | Relato Real",
        "palabras_portada": "CASO REAL",
        "descripcion": (
            "Un sobrecogedor relato paranormal en primera persona.\n\nSíguenos en"
            f" nuestra página oficial de Facebook: {FACEBOOK_LINK}\n\nSuscríbete"
            " al canal para más testimonios e historias"
            " paranormales.\n\n#leyendasurbanas #Paranormal #Misterio #mexico"
            " #HistoriasDeMiedo"
        ),
        "tags": tags_fallback,
        "miniatura_prompt": (
            "Cinematic portrait of a normal white Mexican man looking out a"
            " window at night with a curious mysterious expression, dark street"
            " lights outside, 16:9 landscape, 2k"
        ),
        "segmentos": segmentos[:24],
    }

# ================================================================
# GENERAR GUION + SEO CON DEEPSEEK (CON ANTI-REPETICIÓN Y CONSISTENCIA)
# ================================================================
def generar_guion():
    prompt = f"""Eres un EXPERTO EN SEO DE YOUTUBE, GUIONISTA DE TERROR Y DIRECTOR VISUAL.
Escribe un relato de eventos PARANORMALES Y CASOS DE MIEDO reales narrado en primera persona, ambientado en México (~10000 caracteres).
Divide el relato en 24 segmentos de ~450 caracteres cada uno.

REGLAS DE CONSISTENCIA Y SINCRONIZACIÓN VISUAL (IMPORTANTE):
1. CONSISTENCIA DE PERSONAJE: Define al protagonista al inicio con una descripción física breve (ejemplo: "un hombre mexicano de 32 años, cabello corto oscuro, chaqueta café"). REPITE ESA MISMA DESCRIPCIÓN EXACTA en cada "imagen_prompt" donde el protagonista aparezca, para que su rostro NO cambie durante el video.
2. SINCRONIZACIÓN NARRATIVA: El "imagen_prompt" DEBE reflejar la acción, objeto o lugar específico que se está narrando en el "texto" de ese segmento.
3. ANTI-REPETICIÓN: Cada segmento debe aportar información NUEVA. NUNCA repitas frases, moralejas ni cierres. Si la historia se acaba antes, alarga con nuevos detalles sensoriales o reflexiones, NO con repeticiones.

REGLAS DE TÍTULO Y TEXTO DE PORTADA:
1. TÍTULO: EN ESPAÑOL. Entre 45 y 60 caracteres exactos. Frase completa.
2. PALABRAS_PORTADA: 1 o 2 PALABRAS de máximo impacto (ej: "CASO REAL", "NOCHE DE TERROR").

REGLAS DE SEO Y DESCRIPCIÓN:
1. DESCRIPCIÓN: EN ESPAÑOL. Incluir: "Síguenos en Facebook: {FACEBOOK_LINK}" y hashtags (#leyendasurbanas #Paranormal #Misterio #mexico #HistoriasDeMiedo).
2. TAGS: EN ESPAÑOL. 25-30 palabras clave separadas por comas.

Responde estrictamente en formato JSON válido:
{{
  "titulo": "Título entre 45 y 60 caracteres",
  "palabras_portada": "CASO REAL",
  "descripcion": "Sinopsis... Síguenos en Facebook: {FACEBOOK_LINK} #leyendasurbanas #Paranormal #Misterio #mexico #HistoriasDeMiedo",
  "tags": "tag1, tag2, ..., tag30",
  "miniatura_prompt": "Cinematic 16:9 photograph of [descripción del protagonista] looking with fear inside a dark old colonial house, 2k, no text",
  "segmentos": [
    {{
      "texto": "Texto en español que leerá el narrador...",
      "imagen_prompt": "Detailed photographic prompt synchronized with the text, [misma descripción del protagonista si aparece], 16:9, 2k, no text, no blood"
    }}
  ]
}}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 5000,
        "response_format": {"type": "json_object"},
    }

    for intento in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=150)
            r.raise_for_status()
            respuesta = r.json()["choices"][0]["message"]["content"].strip()
            json_str = limpiar_respuesta_json(respuesta)
            data = json.loads(json_str)

            if "segmentos" not in data or len(data["segmentos"]) == 0:
                raise ValueError("La respuesta no contiene segmentos")

            titulo = data.get("titulo", "").strip()
            if len(titulo) > 60:
                titulo = titulo[:60].rsplit(" ", 1)[0]
            data["titulo"] = titulo

            if FACEBOOK_LINK not in data.get("descripcion", ""):
                data["descripcion"] = (
                    f"{data.get('descripcion', '')}\n\nSíguenos en Facebook:"
                    f" {FACEBOOK_LINK}"
                )

            for seg in data["segmentos"]:
                if "imagen_prompt" in seg:
                    seg["imagen_prompt"] = limpiar_prompt(seg["imagen_prompt"])
                if "texto" in seg:
                    seg["texto"] = seg["texto"].replace('"', "'")
                    seg["texto"] = re.sub(
                        r"imagen_prompt.*", "", seg["texto"], flags=re.IGNORECASE
                    )

            return data
        except Exception as e:
            print(f"❌ Intento {intento+1}/3 falló: {e}")
            time.sleep(3)

    return generar_fallback(respuesta)

# ================================================================
# GENERAR IMAGEN CON AGNES AI
# ================================================================
def generar_imagen(prompt, width=2048, height=1152, intentos=3):
    prompt_limpio = limpiar_prompt(prompt)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {AGNES_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_limpio,
        "width": width,
        "height": height,
        "num_images": 1,
    }
    for i in range(intentos):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code == 200:
                return r.json()["data"][0]["url"]
            else:
                time.sleep(8)
        except Exception:
            time.sleep(8)
    return None

# ================================================================
# GENERAR AUDIO CON EDGE-TTS (voz aleatoria dinámica)
# ================================================================
def generar_audio(texto, index):
    texto_limpio = re.sub(r"imagen_prompt.*", "", texto, flags=re.IGNORECASE)
    texto_limpio = texto_limpio.strip()
    if not texto_limpio:
        return None

    filename = f"audio_{index}.mp3"
    voz = CONFIG_VOZ_ACTUAL["voz"]
    rate = CONFIG_VOZ_ACTUAL["velocidad"]
    pitch = CONFIG_VOZ_ACTUAL["tono"]

    async def _generar():
        communicate = edge_tts.Communicate(texto_limpio, voz, rate=rate, pitch=pitch)
        await communicate.save(filename)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_generar())
        loop.close()
        print(f"✅ Audio {index} generado con {voz} ({rate}, {pitch})")
        return filename
    except Exception as e:
        print(f"❌ Error generando audio {index}: {e}")
        return None

# ================================================================
# MONTAR VIDEO CON MOVIEPY (FONDO AL 8%)
# ================================================================
def montar_video(elementos, salida="video_final.mp4"):
    if not elementos:
        raise ValueError("No hay elementos para montar el video")

    clips_video = []
    clips_audio = []

    for i, elem in enumerate(elementos):
        img_url = elem["imagen_url"]
        audio_path = elem["audio_path"]

        try:
            audio_clip = AudioFileClip(audio_path)
            duracion = audio_clip.duration

            r = requests.get(img_url, timeout=30)
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
            print(f"⚠️ Error procesando segmento {i}: {e}")
            continue

    if not clips_video or not clips_audio:
        raise ValueError("No se pudieron procesar los clips")

    video = concatenate_videoclips(clips_video, method="compose")
    audio_narracion = concatenate_audioclips(clips_audio)
    duracion_total = audio_narracion.duration

    # 🎵 Mezclar audio de fondo al 8%
    fondo_path = FONDO_AUDIO_FILE
    if fondo_path and os.path.exists(fondo_path):
        try:
            fondo_clip = AudioFileClip(fondo_path)
            if fondo_clip.duration < duracion_total:
                veces = int(duracion_total / fondo_clip.duration) + 1
                fondo_clip = concatenate_audioclips([fondo_clip] * veces)
            fondo_clip = fondo_clip.subclip(0, duracion_total)
            fondo_clip = fondo_clip.volumex(0.08)
            audio_final = CompositeAudioClip([audio_narracion, fondo_clip])
            print(f"🎵 Audio de fondo mezclado al 8%: {fondo_path}")
        except Exception as e:
            print(f"⚠️ Error en audio de fondo: {e}")
            audio_final = audio_narracion
    else:
        audio_final = audio_narracion

    video = video.set_audio(audio_final)
    video.write_videofile(
        salida,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="ultrafast",
    )
    print(f"✅ Video creado correctamente: {salida}")
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
    request = youtube.videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    response = request.execute()

    video_id = response["id"]
    print(f"✅ Video subido a YouTube: https://youtu.be/{video_id}")

    if miniatura_path and os.path.exists(miniatura_path):
        try:
            media_thumb = MediaFileUpload(miniatura_path, chunksize=-1, resumable=True)
            thumb_request = youtube.thumbnails().set(
                videoId=video_id, media_body=media_thumb
            )
            thumb_request.execute()
            print("✅ Miniatura con texto estilizado subida a YouTube")
        except Exception as e:
            print(f"⚠️ No se pudo subir miniatura: {e}")

    return response

# ================================================================
# MAIN
# ================================================================
def main():
    print(f"🎬 Iniciando Bot de YouTube con Voz: {CONFIG_VOZ_ACTUAL['voz']}")
    print(f"🎨 Estilo visual: {ESTILO_VISUAL_ACTUAL[:60]}...")
    print(f"🎭 Protagonista: {PROTAGONISTA_SELECCIONADO}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if FONDO_AUDIO_FILE:
        print(f"🎵 Audio de fondo seleccionado: {FONDO_AUDIO_FILE}")
    else:
        print("⚠️ No hay audio de fondo disponible.")

    guion_data = generar_guion()
    if not guion_data:
        print("❌ No se pudo generar el guion. Abortando.")
        return

    titulo_video = guion_data.get("titulo", "El Misterio Nocturno de la Calle Madero | Relato Real")
    palabras_portada = guion_data.get("palabras_portada", "CASO REAL")
    descripcion_video = guion_data.get("descripcion", f"Relato paranormal.\n\nSíguenos en Facebook: {FACEBOOK_LINK}")
    tags_video = guion_data.get("tags", "relatos paranormales, leyendas urbanas, Mexico")
    miniatura_prompt = guion_data.get("miniatura_prompt", "Cinematic portrait of a Mexican man in an old house at night, 16:9, 2k")
    segmentos = guion_data.get("segmentos", [])

    if not segmentos:
        print("❌ No se generaron segmentos. Abortando.")
        return

    print(f"✅ Guion generado con {len(segmentos)} segmentos")
    print(f"📌 Título ({len(titulo_video)} caracteres): {titulo_video}")
    print(f"📌 Palabras de portada: {palabras_portada}")

    elementos_validos = []
    imagen_ultimo_recurso = None
    textos_vistos = set()

    print(f"\n🎨 y 🎙️ Generando {len(segmentos)} segmentos con voz {CONFIG_VOZ_ACTUAL['voz']}...")

    for i, seg in enumerate(segmentos):
        print(f"\n--- Procesando segmento {i+1}/{len(segmentos)} ---")

        texto_normalizado = seg["texto"].strip().lower()
        if texto_normalizado in textos_vistos:
            print(f"⚠️ Segmento {i+1} duplicado (texto repetido). Omitiendo.")
            continue
        textos_vistos.add(texto_normalizado)

        if i > 0:
            print("⏳ Esperando 6 segundos antes de la siguiente imagen...")
            time.sleep(6)

        url_img = generar_imagen(seg["imagen_prompt"], width=2048, height=1152)
        if url_img:
            imagen_ultimo_recurso = url_img
            print(f"✅ Imagen {i+1} generada (2K 16:9)")
        elif imagen_ultimo_recurso:
            print(f"⚠️ Reutilizando imagen previa para segmento {i+1}")
            url_img = imagen_ultimo_recurso
        else:
            print(f"❌ Sin imagen disponible para segmento {i+1}, se salta.")
            continue

        print("⏳ Esperando 4 segundos antes del audio...")
        time.sleep(4)

        audio_file = generar_audio(seg["texto"], i)
        if not audio_file:
            print(f"❌ Falló el audio {i+1}, se salta el segmento.")
            continue

        elementos_validos.append({"imagen_url": url_img, "audio_path": audio_file})
        print(f"✅ Segmento {i+1} completado")

    # Miniatura
    print("\n🖼️ Generando y ajustando miniatura horizontal 1280x720...")
    miniatura_path = "miniatura.jpg"
    miniatura_prompt_refinado = (
        f"{miniatura_prompt} 16:9 landscape aspect ratio, cinematic widescreen, 2k,"
        " no text, no words, no blood, no demaciated faces"
    )
    miniatura_url = generar_imagen(miniatura_prompt_refinado, width=1280, height=720)

    if miniatura_url:
        try:
            r = requests.get(miniatura_url, timeout=30)
            r.raise_for_status()
            with open(miniatura_path, "wb") as f:
                f.write(r.content)
            with Image.open(miniatura_path) as img:
                img_fitted = ImageOps.fit(img, (1280, 720), Image.Resampling.LANCZOS)
                img_fitted.save(miniatura_path)
            agregar_texto_miniatura(miniatura_path, palabras_portada)
            print("✅ Miniatura ajustada a 16:9 con texto estilo terror")
        except Exception as e:
            print(f"⚠️ Error al procesar miniatura: {e}")
            miniatura_path = None
    else:
        miniatura_path = None

    if not elementos_validos:
        print("❌ No hay elementos válidos para construir el video. Abortando.")
        return

    print("\n🎬 Montando video con MoviePy...")
    try:
        video_path = montar_video(elementos_validos, "video_final.mp4")
    except Exception as e:
        print(f"❌ Error montando video: {e}")
        return

    print("\n⬆️ Subiendo video a YouTube con metadatos en español...")
    try:
        subir_a_youtube(video_path, miniatura_path, titulo_video, descripcion_video, tags_video)
    except Exception as e:
        print(f"❌ Error subiendo a YouTube: {e}")
        return

    print("🎉 Proceso completado exitosamente")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
