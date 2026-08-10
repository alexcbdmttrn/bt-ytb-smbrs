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
CANAL_LINK = "https://www.youtube.com/@sombrasdemedianocheoficial"  # <-- FIJADO

ESTADO_FILE = "estado_shorts.json"

# ================================================================
# 🎤 BANCO DE 12 VOCES (igual que el bot largo)
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
# 🎨 BANCO DE 16 PALETAS DE COLOR (igual que bot largo)
# ================================================================
PALETAS_COLOR = [
    "Deep crimson red, pitch black shadow, intense orange emergency light accents",
    "Blood red and burnt orange, dark charcoal shadows, hellish glow",
    "Warm amber and dark mahogany, golden candlelight, deep brown shadows",
    "Fiery sunset orange, deep purple shadows, intense red highlights",
    "Rusty red and dark brown, sepia undertones, warm vintage look",
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
    "Toxic lime green and pitch black, eerie chemical glow, radioactive haze",
]
PALETA_COLOR_ACTUAL = random.choice(PALETAS_COLOR)

# ================================================================
# 📷 ESTILOS VISUALES (limpios, sin manchas)
# ================================================================
ESTILOS_VISUALES = [
    "Clean 35mm film photograph, sharp focus, cinematic lighting",
    "Modern cinematic thriller photography, soft ambient diffusion, clean details",
    "Documentary realistic photo, natural crisp skin texture, soft shadows",
    "8k resolution cinematic movie frame, ultra clear facial details",
    "High-end fashion photography style, dramatic lighting, clean skin",
    "Cinematic noir style, high contrast, sharp shadows, clean aesthetic",
]
ESTILO_VISUAL_ACTUAL = random.choice(ESTILOS_VISUALES)

# ================================================================
# 🧑 GENERADOR DE PERSONAJES (diversidad real, igual que bot largo)
# ================================================================
def generar_perfil_personaje_shorts():
    """Genera un perfil mexicano diverso para Shorts."""
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
    rasgos = [
        "with indigenous facial features",
        "with mestizo features",
        "with light brown skin and freckles",
        "with dark brown skin and kind eyes",
        "with olive skin and a strong jaw",
        "with pale skin and green eyes",
    ]
    profesiones = [
        "trailero de 45 años en carretera nocturna",
        "estudiante de medicina de 22 años en un hospital antiguo",
        "policía de 38 años en su turno nocturno",
        "agricultor de 50 años en una hacienda del siglo XIX",
        "fotógrafo urbano de 28 años en edificios abandonados",
        "taxista nocturno de 55 años en zonas peligrosas",
        "velador de 60 años en un panteón viejo",
        "arqueólogo de 40 años excavando en la selva",
        "periodista de investigación de 35 años en un pueblo fantasma",
        "enfermero de 30 años en un psiquiátrico abandonado",
        "minero de 48 años en una mina clausurada",
        "bailarina de 25 años en un teatro embrujado",
    ]
    personaje = random.choice(profesiones)
    perfil_fisico = (
        f"a {random.choice(edades)} Mexican {random.choice(generos)}, "
        f"{random.choice(rasgos)}, "
        f"with {random.choice(cabellos)}, {random.choice(vestimentas)}"
    )
    return perfil_fisico, personaje

PERFIL_PERSONAJE_SHORTS, PERSONAJE_SHORTS = generar_perfil_personaje_shorts()
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
# 🧼 LIMPIADOR DE PROMPTS (igual que bot largo)
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        prompt = "Mexican street at night, dark ambiance"

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

    modificadores_calidad = (
        f", {ESTILO_VISUAL_ACTUAL}, color palette of {PALETA_COLOR_ACTUAL}, "
        "vertical 9:16 portrait format for mobile, single solitary person, exactly one person, "
        "clean smooth skin, natural facial complexion, no face blemishes, no skin spots, "
        "no cloned faces, sharp focus, no text, no watermark"
    )
    return (prompt + modificadores_calidad)[:500]

# ================================================================
# LIMPIAR RESPUESTA JSON (mismo método que bot largo)
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
# GENERAR HISTORIA COMPLETA CON DEEPSEEK (CON JSON VALIDADO)
# ================================================================
def generar_historia_completa():
    prompt = f"""Eres un EXPERTO EN STORYTELLING PARA YOUTUBE SHORTS.
Crea una historia de TERROR/PARANORMAL en PRIMERA PERSONA, protagonizada por un {PERSONAJE_SHORTS}.
La historia debe tener entre 700 y 800 palabras, y estar dividida en DOS PARTES claras con un CLIFFHANGER en el punto medio.
Ambientada en el estado de {ESTADO_HISTORIA_SHORTS}, México.

DESCRIPCIÓN FÍSICA DEL PROTAGONISTA (ÚNICA PARA ESTE SHORT):
"{PERFIL_PERSONAJE_SHORTS}"

REGLAS:
- Inicio: presenta al personaje y la situación en {ESTADO_HISTORIA_SHORTS}.
- Desarrollo: construye tensión, describe sonidos, olores, sensaciones.
- Mitad: un giro o revelación (CLIFFHANGER) para la Parte 1.
- Final: resolución o nuevo giro en la Parte 2.
- ANTI-REPETICIÓN: NO repitas frases.
- IMPORTANTE: ESCAPA todas las comillas dobles dentro del texto (ej: "dijo" -> \"dijo\").
- PALETA DE COLOR: {PALETA_COLOR_ACTUAL}

Devuelve ESTRICTAMENTE este JSON válido:
{{
  "titulo": "Título atractivo para el Short (máx 50 caracteres)",
  "texto_completo": "Historia completa de 700-800 palabras... (sin comillas internas sin escapar)",
  "palabras_portada": "PALABRA CLAVE (ej: TERROR, APARICIÓN)",
  "tags": "tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9, tag10, tag11, tag12, tag13, tag14, tag15 (mínimo 15 tags, total > 200 caracteres)"
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

    for intento in range(5):
        try:
            print(f"🔄 Intento {intento+1}/5 generando historia...")
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            r.raise_for_status()
            respuesta = r.json()["choices"][0]["message"]["content"].strip()
            
            # Limpiar respuesta
            respuesta = re.sub(r"```json\s*", "", respuesta)
            respuesta = re.sub(r"```\s*", "", respuesta)
            
            # Intentar parsear JSON con manejo de errores
            try:
                data = json.loads(respuesta)
            except json.JSONDecodeError as e:
                print(f"⚠️ Error JSON: {e}. Limpiando manualmente...")
                # Reemplazar comillas internas en el texto_completo
                # Buscar y reemplazar comillas dobles dentro del texto
                match = re.search(r'"texto_completo"\s*:\s*"([^"]*)"', respuesta, re.DOTALL)
                if match:
                    texto = match.group(1)
                    texto = texto.replace('"', "'")
                    respuesta = re.sub(
                        r'"texto_completo"\s*:\s*"[^"]*"',
                        f'"texto_completo": "{texto}"',
                        respuesta
                    )
                    data = json.loads(respuesta)
                else:
                    raise e
            
            if "texto_completo" not in data or len(data["texto_completo"]) < 100:
                raise ValueError("Texto demasiado corto")
            
            # Limpiar texto (eliminar caracteres de control)
            data["texto_completo"] = re.sub(r'[\x00-\x1f\x7f]', '', data["texto_completo"])
            data["texto_completo"] = re.sub(r'\n{3,}', '\n\n', data["texto_completo"])
            
            # Asegurar tags largos
            if "tags" in data and len(data["tags"]) < 200:
                data["tags"] = data["tags"] + ", terror, shorts, mexico, paranormal, miedo, relatos, leyendas, misterio, suspenso"
            
            return data
            
        except Exception as e:
            print(f"❌ Intento {intento+1}/5 falló: {e}")
            if intento < 4:
                print(f"⏳ Esperando {10 + intento * 5} segundos...")
                time.sleep(10 + intento * 5)
    
    # Fallback manual
    print("⚠️ Creando fallback manual...")
    return {
        "titulo": "Relato de Terror Nocturno",
        "texto_completo": f"""Era una noche oscura cuando {PERSONAJE_SHORTS} sintió que algo no andaba bien en {ESTADO_HISTORIA_SHORTS}. El silencio era pesado, como si el aire mismo contuviera la respiración. De repente, un ruido extraño rompió la calma. No era el viento, no era un animal. Era algo más. Algo que parecía venir de las sombras. El corazón le latía con fuerza mientras intentaba descubrir qué era. Entonces, una figura emergió de la oscuridad. No tenía rostro, pero parecía mirarlo directamente. Sin tiempo para reaccionar, sintió un frío helado recorrer su espalda. Era el miedo hecho carne. Y esa noche, el miedo lo encontró a él. El pueblo de {ESTADO_HISTORIA_SHORTS} guarda muchos secretos, y esa noche él descubriría uno de los más oscuros.""",
        "palabras_portada": "TERROR",
        "tags": "terror, shorts, mexico, paranormal, miedo, relatos, leyendas, misterio, suspenso, historia, noche, oscuridad, sombras, aparicion, escalofrio, casas, embrujadas, pueblo, fantasma, real"
    }

# ================================================================
# DIVIDIR TEXTO EN DOS PARTES
# ================================================================
def dividir_texto(texto):
    palabras = texto.split()
    if len(palabras) < 20:
        mitad = len(texto) // 2
        return texto[:mitad].strip(), texto[mitad:].strip()
    
    mitad = len(palabras) // 2
    for i in range(mitad, min(mitad + 50, len(palabras))):
        if palabras[i].endswith('.') or palabras[i].endswith('?') or palabras[i].endswith('!'):
            break
    parte1 = ' '.join(palabras[:i+1])
    parte2 = ' '.join(palabras[i+1:])
    if len(parte2) < 50 and i < len(palabras) - 10:
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
    texto_limpio = re.sub(r"imagen_prompt.*", "", texto, flags=re.IGNORECASE).strip()
    if not texto_limpio:
        return None

    filename = f"audio_short_{index}.mp3"
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

    descripcion = f"""📌 {texto_corto[:150]}...

🔴 SUSCRÍBETE para más historias: {CANAL_LINK}
📱 Facebook: {FACEBOOK_LINK}

#Shorts #Terror #LeyendasMexicanas {' '.join(['#'+t for t in etiquetas])} #RelatosDeTerror #Paranormal"""

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
    print(f"🎭 Personaje: {PERSONAJE_SHORTS}")
    print(f"📍 Ubicación: {ESTADO_HISTORIA_SHORTS}")
    print(f"🎨 Paleta: {PALETA_COLOR_ACTUAL[:60]}...")

    estado = cargar_estado()
    parte_actual = estado.get("parte", 1)
    print(f"📌 Estado actual: Parte {parte_actual}")

    if parte_actual == 1:
        print("🆕 Generando nueva historia completa...")
        historia = generar_historia_completa()
        if not historia:
            print("❌ No se pudo generar la historia")
            return
        
        estado["historia"] = {
            "titulo": historia.get("titulo", "Relato de Terror"),
            "texto_completo": historia.get("texto_completo", ""),
            "palabras_portada": historia.get("palabras_portada", "TERROR"),
            "tags": historia.get("tags", "terror, shorts, mexico, paranormal, miedo, relatos, leyendas, misterio")
        }
        estado["parte"] = 2
        guardar_estado(estado)

        parte1, parte2 = dividir_texto(historia["texto_completo"])
        estado["historia"]["parte2"] = parte2
        guardar_estado(estado)

        texto_publicar = parte1
        cta = "\n\n📌 Parte 2 mañana a la misma hora. ¡No te la pierdas! 👻"
        texto_publicar += cta
        parte_num = 1
        print(f"📝 Publicando Parte 1 ({len(texto_publicar)} caracteres)")
    else:
        historia = estado.get("historia")
        if not historia or not historia.get("parte2"):
            print("❌ No hay historia para Parte 2. Reiniciando.")
            estado["parte"] = 1
            guardar_estado(estado)
            return

        texto_publicar = historia.get("parte2", "")
        cta = "\n\n👻 ¿Te gustó? SUSCRÍBETE para más historias de terror."
        texto_publicar += cta
        titulo = historia.get("titulo", "Relato de Terror")
        palabras_portada = historia.get("palabras_portada", "TERROR")
        tags = historia.get("tags", "terror, shorts, mexico, paranormal, miedo")
        parte_num = 2
        print(f"📝 Publicando Parte 2 ({len(texto_publicar)} caracteres)")

        estado["parte"] = 1
        estado["historia"] = None
        guardar_estado(estado)

    # Generar imagen vertical
    print("🎨 Generando imagen vertical...")
    prompt_img = f"{PERFIL_PERSONAJE_SHORTS} en {ESTADO_HISTORIA_SHORTS}, escena de terror, vertical 9:16"
    imagen_url = generar_imagen_vertical(prompt_img)
    if not imagen_url:
        print("⚠️ Falló imagen, usando placeholder")
        imagen_url = "https://via.placeholder.com/1080x1920/1a1a1a/ff0000?text=Terror"

    # Esperar 6 segundos antes del audio (igual que bot largo)
    print("⏳ Esperando 6 segundos antes del audio...")
    time.sleep(6)

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
    tags = historia.get("tags", "terror, shorts, mexico, paranormal, miedo") if parte_actual == 2 else historia.get("tags", "terror, shorts, mexico, paranormal, miedo")
    
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
