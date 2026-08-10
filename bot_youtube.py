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
CANAL_LINK = "https://www.youtube.com/@TUCANAL"  # <-- REEMPLAZA CON TU LINK

# ================================================================
# 🎤 BANCO DE VOCES (Rotación Automática)
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
# 🎨 PALETAS DE COLOR DIVERSAS (Elimina la monotonía de rojo/naranja)
# ================================================================
PALETAS_COLOR_DIVERSAS = [
    {"nombre": "Azul Cian y Niebla Marina", "prompt": "cold cyan fog, deep navy blue shadows, pale moonlight, icy atmosphere"},
    {"nombre": "Verde Esmeralda y Musgo", "prompt": "emerald green twilight, dark forest haze, muted sage green lighting, dark teal"},
    {"nombre": "Violeta Neón y Púrpura", "prompt": "deep violet haze, electric purple ambient light, dark magenta shadows, eerie neon glow"},
    {"nombre": "Blanco y Negro Monocromático", "prompt": "stark black and white high contrast photography, silver moonlight, deep pitch shadows"},
    {"nombre": "Sepia y Ámbar Oscuro", "prompt": "muted amber lighting, dark mahogany shadows, vintage warm bronze haze"},
    {"nombre": "Gris Pizarra y Azul Helado", "prompt": "slate gray tones, freezing ice blue highlight, dim overcast ambient, desaturated"}
]
PALETA_SELECCIONADA = random.choice(PALETAS_COLOR_DIVERSAS)

# ================================================================
# 📷 ESTILOS VISUALES LIMPIOS (Sin marcas ni manchas en la piel)
# ================================================================
ESTILOS_VISUALES = [
    "Clean 35mm film photograph, sharp focus, cinematic lighting",
    "Modern photographic thriller style, soft ambient diffusion, clean details",
    "Documentary realistic photo, natural crisp skin texture, soft shadows",
    "8k resolution cinematic movie frame, ultra clear facial details"
]
ESTILO_VISUAL_ACTUAL = random.choice(ESTILOS_VISUALES)

# ================================================================
# 🖼️ BANCO DE COLORES PARA DEGRADADO DE MINIATURAS
# ================================================================
DEGRADADOS_MINIATURA = [
    {"top": (0, 255, 200), "bottom": (0, 80, 220), "nombre": "Cian a Azul"},
    {"top": (0, 255, 120), "bottom": (0, 100, 80), "nombre": "Verde Neón"},
    {"top": (220, 0, 255), "bottom": (80, 0, 150), "nombre": "Violeta Púrpura"},
    {"top": (255, 215, 0), "bottom": (200, 50, 0), "nombre": "Dorado a Carmesí"},
    {"top": (255, 255, 255), "bottom": (120, 120, 120), "nombre": "Plata Blanco"}
]
DEGRADADO_ACTUAL = random.choice(DEGRADADOS_MINIATURA)

# ================================================================
# 🎵 ARCHIVOS DE AUDIO DE FONDO
# ================================================================
FONDOS_DISPONIBLES = [
    "Ash and Marrow.mp3", "Black Maw.mp3", "Cold Hollow.mp3",
    "Hollow Marrow.mp3", "Sunken Dread.mp3", "Sunless Vault.mp3", "The Deep Rot.mp3"
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
                    return os.path.join(root, file)
    return None

FONDO_AUDIO_FILE = seleccionar_fondo_disponible()

# ================================================================
# 🧼 LIMPIADOR DE PROMPTS CON FILTROS ANTI-CLON Y ANTI-MANCHAS
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        prompt = "A quiet night scene, moody lighting"

    prompt = re.sub(r"\n+", " ", prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r"[^\x00-\x7F]+", "", prompt)

    # 1. Eliminar palabras que manchan la piel o ensucian la imagen
    palabras_sucias = [
        r"\bgrainy\b", r"\bvhs\b", r"\bchiaroscuro\b", r"\bdirt\b", r"\bgrime\b",
        r"\bblemish\b", r"\bspots\b", r"\bterro\b", r"\bhorror\b", r"\bsangre\b",
        r"\bblood\b", r"\bgore\b", r"\bdemacrad[oa]s?\b", r"\bzombies?\b",
        r"\bdisfigured\b", r"\bwounds?\b", r"\bmonster\b"
    ]
    for pattern in palabras_sucias:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)

    prompt = re.sub(r"\s+", " ", prompt).strip()

    # 2. Reglas estricta de 1 solo sujeto y piel limpia
    modificadores_calidad = (
        f", {ESTILO_VISUAL_ACTUAL}, color palette of {PALETA_SELECCIONADA['prompt']}, "
        "16:9 widescreen format, single solitary person in frame, exactly one person, "
        "clean smooth skin, natural facial complexion, no face blemishes, no skin spots, "
        "no cloned faces, no duplicate people, sharp focus, clean anatomical features, "
        "no text, no watermark"
    )
    return (prompt + modificadores_calidad)[:500]

# ================================================================
# 🖼️ MINIATURA CON DEGRADADO DINÁMICO
# ================================================================
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
            print(f"✅ Texto '{texto_portada}' impreso en miniatura ({DEGRADADO_ACTUAL['nombre']}).")
    except Exception as e:
        print(f"⚠️ Error en miniatura: {e}")

# ================================================================
# LIMPIAR RESPUESTA JSON DE DEEPSEEK
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
# GENERAR GUION (GENERADOR DINÁMICO DE PERSONAJES)
# ================================================================
def generar_guion():
    # 1. Generador de perfiles únicos para evitar repetir el mismo protagonista
    EDADES = ["21-year-old", "35-year-old", "48-year-old", "60-year-old"]
    GENEROS = ["man", "woman"]
    VESTIMENTAS = [
        "wearing a denim jacket and grey shirt",
        "wearing a dark green coat and wool scarf",
        "wearing a simple white shirt and leather belt",
        "wearing an old blue mechanic uniform",
        "wearing a dark sweater and classic trousers"
    ]
    CABELLOS = ["short curly dark hair", "long straight black hair tied back", "grey cropped hair", "wavy brown shoulder-length hair"]

    perfil_personaje = (
        f"a {random.choice(EDADES)} Mexican {random.choice(GENEROS)} with "
        f"{random.choice(CABELLOS)}, {random.choice(VESTIMENTAS)}"
    )

    prompt = f"""Eres un GUIONISTA Y DIRECTOR DE CINE DE MISTERIO.
Escribe un relato de eventos paranormales o misterio real en primera persona (~9000 caracteres).
Divide la historia en 20 a 24 segmentos cortos.

REGLAS DE GENERACIÓN VISUAL Y PERSONAJES:
1. PERSONAJE PRINCIPAL FIJO: En todos los segmentos donde aparezca el protagonista, USA EXACTAMENTE ESTA DESCRIPCIÓN EN INGLÉS: "{perfil_personaje}".
2. CERO PERSONAJES CLONADOS: Escribe los prompts pidiendo SIEMPRE "single person" o "one solitary character". Nunca uses plurales si solo hay una persona en escena.
3. PALETA DE COLOR DE ESTE VIDEO: El estilo de color debe inclinarse hacia: {PALETA_SELECCIONADA['prompt']}. NO uses luces naranjas ni rojas a menos que sea una llama directa.
4. TEXTO ÚNICO: Prohibido repetir frases, moralejas o reflexiones de cierre en múltiples segmentos. Cada segmento debe aportar trama nueva.

Responde con este JSON estructurado:
{{
  "titulo": "Título de misterio impactante (50-80 caracteres)",
  "palabras_portada": "PALABRA IMPACTO",
  "descripcion": "Sinopsis completa... Síguenos en Facebook: {FACEBOOK_LINK} #leyendasurbanas #Paranormal #Misterio #mexico",
  "tags": "tag1, tag2, tag3, ..., tag25",
  "miniatura_prompt": "Horizontal 16:9 cinematic image prompt of {perfil_personaje} in a mysterious location, {PALETA_SELECCIONADA['prompt']}",
  "segmentos": [
    {{
      "texto": "Texto narrativo único...",
      "imagen_prompt": "Detailed cinematic prompt in English with {perfil_personaje} if present, single subject, clean smooth face, 16:9 widescreen, no text"
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
    return None

# ================================================================
# GENERAR IMAGEN CON AGNES AI
# ================================================================
def generar_imagen(prompt, width=2048, height=1152, intentos=3):
    prompt_limpio = limpiar_prompt(prompt)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_limpio,
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
# GENERAR AUDIO CON EDGE-TTS
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
# MONTAR VIDEO CON MOVIEPY (FONDO AL 8%)
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

    # Audio de fondo al 8%
    if FONDO_AUDIO_FILE and os.path.exists(FONDO_AUDIO_FILE):
        try:
            fondo_clip = AudioFileClip(FONDO_AUDIO_FILE)
            if fondo_clip.duration < duracion_total:
                veces = int(duracion_total / fondo_clip.duration) + 1
                fondo_clip = concatenate_audioclips([fondo_clip] * veces)
            fondo_clip = fondo_clip.subclip(0, duracion_total).volumex(0.08)
            audio_final = CompositeAudioClip([audio_narracion, fondo_clip])
        except Exception:
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
    print(f"✅ Video subido a YouTube: https://youtu.be/{video_id}")

    if miniatura_path and os.path.exists(miniatura_path):
        try:
            media_thumb = MediaFileUpload(miniatura_path, chunksize=-1, resumable=True)
            youtube.thumbnails().set(videoId=video_id, media_body=media_thumb).execute()
            print("✅ Miniatura subida a YouTube")
        except Exception as e:
            print(f"⚠️ No se pudo subir miniatura: {e}")

# ================================================================
# MAIN
# ================================================================
def main():
    print(f"🎬 Bot de Vídeos Largos | Voz: {CONFIG_VOZ_ACTUAL['voz']} | Paleta: {PALETA_SELECCIONADA['nombre']}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    guion_data = generar_guion()
    if not guion_data:
        print("❌ No se pudo generar el guion.")
        return

    titulo_video = guion_data.get("titulo", "Relato Paranormal Nocturno")
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
        print("❌ No hay elementos válidos para montar el video.")
        return

    # Miniatura
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
