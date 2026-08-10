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
CANAL_LINK = "https://www.youtube.com/@TUCANAL"  # <-- REEMPLAZA CON TU LINK

ESTADO_FILE = "estado_shorts.json"

# ================================================================
# BANCO DE VOCES (12)
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
# ESTILOS VISUALES (12)
# ================================================================
ESTILOS_VISUALES = [
    "35mm grainy vintage film photograph",
    "Dark chiaroscuro oil painting style, dramatic deep shadows",
    "Modern cinematic thriller photography, volumetric foggy light",
    "Documentary realistic flash photography, raw camera look",
    "Desaturated cold film look, moody cinematic lighting",
    "Vaporwave neon noir style, intense magenta and cyan highlights",
    "Watercolor gothic ink illustration, dark wet textures",
    "Retro 80s horror VHS screengrab, grainy texture",
    "Hyperrealistic night vision photography, grainy green-tinted",
    "Analog horror found footage style, distorted lens",
    "Soviet brutalist architectural photography, harsh stark lighting",
    "Expressionist german silent film style, high contrast black and white",
]
ESTILO_VISUAL_ACTUAL = random.choice(ESTILOS_VISUALES)

# ================================================================
# PROTAGONISTAS (12)
# ================================================================
PROTAGONISTAS = [
    "un trailero de 45 años en carretera nocturna",
    "una estudiante de medicina de 22 años en un hospital antiguo",
    "un policía de 38 años en su turno nocturno",
    "un agricultor de 50 años en una hacienda del siglo XIX",
    "un fotógrafo urbano de 28 años en edificios abandonados",
    "un taxista nocturno de 55 años en zonas peligrosas",
    "un velador de 60 años en un panteón viejo",
    "un arqueólogo de 40 años excavando en la selva",
    "una periodista de investigación de 35 años en un pueblo fantasma",
    "un enfermero de 30 años en un psiquiátrico abandonado",
    "un minero de 48 años en una mina clausurada",
    "una bailarina de 25 años en un teatro embrujado",
]
PROTAGONISTA_SELECCIONADO = random.choice(PROTAGONISTAS)

# ================================================================
# AUDIO DE FONDO
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
# LIMPIAR PROMPT (VERTICAL 9:16)
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        prompt = "Mexican street at night, dark ambiance"
    prompt = re.sub(r"\n+", " ", prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r"[^\x00-\x7F]+", "", prompt)

    palabras_prohibidas = [
        r"\bterror\b", r"\bhorror\b", r"\bsangre\b", r"\bblood\b", r"\bgore\b",
        r"\bdemacrad[oa]s?\b", r"\bzombies?\b", r"\bmuert[oa]s?\b", r"\bscary face\b",
        r"\bmonster\b", r"\bdisfigured\b"
    ]
    for pattern in palabras_prohibidas:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)
    prompt = re.sub(r"\s+", " ", prompt).strip()

    estilo_dinamico = (
        f", {ESTILO_VISUAL_ACTUAL}, vertical 9:16 portrait format for mobile, "
        "realistic Mexican human features, unique face, sharp details, "
        "clean anatomical proportions, no text, no letters, no logo"
    )
    return (prompt + estilo_dinamico)[:500]

# ================================================================
# ESTADO DE SHORTS
# ================================================================
def cargar_estado():
    try:
        with open(ESTADO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"historia": None, "parte": 1}

def guardar_estado(estado):
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)
    print(f"✅ Estado de Shorts guardado")

# ================================================================
# GENERAR HISTORIA COMPLETA CON DEEPSEEK (~700-800 palabras)
# ================================================================
def generar_historia_completa():
    prompt = f"""Eres un EXPERTO EN STORYTELLING PARA YOUTUBE SHORTS.
Crea una historia de TERROR/PARANORMAL en PRIMERA PERSONA, protagonizada por {PROTAGONISTA_SELECCIONADO}.
La historia debe tener entre 700 y 800 palabras, y estar dividida en DOS PARTES claras con un CLIFFHANGER en el punto medio.

REGLAS:
- Inicio: presenta al personaje y la situación.
- Desarrollo: construye tensión, describe sonidos, olores, sensaciones.
- Mitad: un giro o revelación que deje al espectador con ganas de más (CLIFFHANGER). Este será el final de la Parte 1.
- Final: resolución o nuevo giro en la Parte 2.
- ANTI-REPETICIÓN: NO repitas frases.

Devuelve ESTRICTAMENTE este JSON:
{{
  "titulo": "Título atractivo para el Short (máx 50 caracteres)",
  "texto_completo": "Historia completa de 700-800 palabras...",
  "palabras_portada": "PALABRA CLAVE (ej: TERROR, APARICIÓN)",
  "tags": "tag1, tag2, tag3, tag4, tag5"
}}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 1200,
        "response_format": {"type": "json_object"}
    }

    for intento in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            r.raise_for_status()
            respuesta = r.json()["choices"][0]["message"]["content"].strip()
            respuesta = re.sub(r"```json\s*", "", respuesta)
            respuesta = re.sub(r"```\s*", "", respuesta)
            data = json.loads(respuesta)
            if "texto_completo" not in data:
                raise ValueError("Falta texto_completo")
            return data
        except Exception as e:
            print(f"❌ Intento {intento+1}/3 falló: {e}")
            time.sleep(3)
    return None

# ================================================================
# DIVIDIR TEXTO EN DOS PARTES (mitad aproximada)
# ================================================================
def dividir_texto(texto):
    """Divide el texto en dos partes aproximadamente iguales, buscando un punto o salto de línea."""
    palabras = texto.split()
    mitad = len(palabras) // 2
    # Buscar un punto o salto de línea cerca de la mitad
    for i in range(mitad, min(mitad + 30, len(palabras))):
        if palabras[i].endswith('.') or palabras[i].endswith('?') or palabras[i].endswith('!'):
            break
    parte1 = ' '.join(palabras[:i+1])
    parte2 = ' '.join(palabras[i+1:])
    return parte1.strip(), parte2.strip()

# ================================================================
# GENERAR IMAGEN VERTICAL
# ================================================================
def generar_imagen_vertical(prompt, intentos=3):
    prompt_limpio = limpiar_prompt(prompt)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_limpio,
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
# GENERAR AUDIO
# ================================================================
def generar_audio(texto, index):
    voz = CONFIG_VOZ_ACTUAL["voz"]
    rate = CONFIG_VOZ_ACTUAL["velocidad"]
    pitch = CONFIG_VOZ_ACTUAL["tono"]
    filename = f"audio_short_{index}.mp3"

    async def _generar():
        communicate = edge_tts.Communicate(texto, voz, rate=rate, pitch=pitch)
        await communicate.save(filename)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_generar())
        loop.close()
        print(f"✅ Audio Short generado con {voz}")
        return filename
    except Exception as e:
        print(f"❌ Error audio: {e}")
        return None

# ================================================================
# MONTAR VIDEO VERTICAL
# ================================================================
def montar_video_shorts(elementos, salida="short_final.mp4"):
    clips_video = []
    clips_audio = []

    for i, elem in enumerate(elementos):
        try:
            audio_clip = AudioFileClip(elem["audio_path"])
            duracion = audio_clip.duration

            r = requests.get(elem["imagen_url"], timeout=30)
            r.raise_for_status()
            img_path = f"temp_short_{i}.jpg"
            with open(img_path, "wb") as f:
                f.write(r.content)

            with Image.open(img_path) as img:
                img_fitted = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
                img_fitted.save(img_path)

            video_clip = ImageClip(img_path).set_duration(duracion)
            clips_video.append(video_clip)
            clips_audio.append(audio_clip)
        except Exception as e:
            print(f"⚠️ Error segmento {i}: {e}")
            continue

    if not clips_video or not clips_audio:
        raise ValueError("No hay clips")

    video = concatenate_videoclips(clips_video, method="compose")
    audio_narracion = concatenate_audioclips(clips_audio)

    if FONDO_AUDIO_FILE and os.path.exists(FONDO_AUDIO_FILE):
        try:
            fondo_clip = AudioFileClip(FONDO_AUDIO_FILE)
            duracion_total = audio_narracion.duration
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
    print(f"✅ Short vertical creado: {salida}")
    return salida

# ================================================================
# SUBIR A YOUTUBE
# ================================================================
def subir_a_youtube(video_path, miniatura_path, titulo, texto_corto, etiquetas, parte):
    creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
    youtube = build("youtube", "v3", credentials=creds)

    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]

    # Descripción con CTA
    descripcion = f"""📌 {texto_corto[:150]}...

🔴 SUSCRÍBETE para más historias: {CANAL_LINK}
📱 Facebook: {FACEBOOK_LINK}

#Shorts #Terror #LeyendasMexicanas {' '.join(['#'+t for t in etiquetas])} #RelatosDeTerror"""

    body = {
        "snippet": {
            "title": f"{titulo} - Parte {parte}" if parte else titulo,
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
    print(f"✅ Short subido: https://youtu.be/{video_id}")

# ================================================================
# MAIN
# ================================================================
def main():
    print("🎬 Iniciando Bot de SHORTS (Parte 1 y Parte 2 automático)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎤 Voz: {CONFIG_VOZ_ACTUAL['voz']}")
    print(f"🎭 Protagonista: {PROTAGONISTA_SELECCIONADO}")

    estado = cargar_estado()
    parte_actual = estado.get("parte", 1)
    print(f"📌 Estado actual: Parte {parte_actual}")

    # Si es Parte 1, generar nueva historia
    if parte_actual == 1:
        print("🆕 Generando nueva historia completa...")
        historia = generar_historia_completa()
        if not historia:
            print("❌ No se pudo generar la historia")
            return
        # Guardar en estado
        estado["historia"] = {
            "titulo": historia.get("titulo", "Relato de Terror"),
            "texto_completo": historia.get("texto_completo", ""),
            "palabras_portada": historia.get("palabras_portada", "TERROR"),
            "tags": historia.get("tags", "terror, shorts, mexico")
        }
        estado["parte"] = 2
        guardar_estado(estado)

        # Dividir texto
        parte1, parte2 = dividir_texto(historia["texto_completo"])
        # Guardar la parte 2 en el estado para la siguiente ejecución
        estado["historia"]["parte2"] = parte2
        guardar_estado(estado)

        texto_publicar = parte1
        cta = "\n\n📌 Parte 2 mañana a la misma hora. ¡No te la pierdas! 👻"
        texto_publicar += cta
        parte_num = 1
        print(f"📝 Publicando Parte 1 ({len(texto_publicar)} caracteres)")
    else:
        # Parte 2: usar historia guardada
        historia = estado.get("historia")
        if not historia or not historia.get("parte2"):
            print("❌ No hay historia guardada para la Parte 2. Reiniciando estado.")
            estado["parte"] = 1
            guardar_estado(estado)
            return

        texto_publicar = historia.get("parte2", "")
        cta = "\n\n👻 ¿Te gustó? SUSCRÍBETE para más historias de terror."
        texto_publicar += cta
        titulo = historia.get("titulo", "Relato de Terror")
        palabras_portada = historia.get("palabras_portada", "TERROR")
        tags = historia.get("tags", "terror, shorts, mexico")
        parte_num = 2
        print(f"📝 Publicando Parte 2 ({len(texto_publicar)} caracteres)")

        # Resetear estado después de publicar Parte 2
        estado["parte"] = 1
        estado["historia"] = None
        guardar_estado(estado)

    # Generar imagen vertical
    print("🎨 Generando imagen vertical...")
    prompt_img = f"{texto_publicar[:200]} escena de terror, vertical 9:16"
    imagen_url = generar_imagen_vertical(prompt_img)
    if not imagen_url:
        print("⚠️ Falló imagen, usando placeholder")
        imagen_url = "https://via.placeholder.com/1080x1920/1a1a1a/ff0000?text=Terror"

    # Generar audio
    print("🎙️ Generando audio...")
    audio_path = generar_audio(texto_publicar, 0)
    if not audio_path:
        print("❌ Falló audio")
        return

    # Montar video
    elementos = [{"imagen_url": imagen_url, "audio_path": audio_path}]
    print("🎬 Montando Short vertical...")
    video_path = montar_video_shorts(elementos, "short_final.mp4")

    # Subir a YouTube
    titulo = historia.get("titulo", "Relato de Terror") if parte_actual == 2 else historia.get("titulo", "Relato de Terror")
    tags = historia.get("tags", "terror, shorts, mexico") if parte_actual == 2 else historia.get("tags", "terror, shorts, mexico")
    print("⬆️ Subiendo Short...")
    subir_a_youtube(video_path, None, titulo, texto_publicar, tags, parte_num)

    print("🎉 Short publicado exitosamente!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
