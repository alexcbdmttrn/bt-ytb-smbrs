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
CANAL_LINK = "https://www.youtube.com/@sombrasdemedianocheoficial"

ESTADO_FILE = "estado_shorts.json"

# ================================================================
# 🎤 BANCO DE 12 VOCES (1.05x)
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural", "velocidad": "+5%", "tono": "-2Hz"},
    {"voz": "es-MX-DaliaNeural", "velocidad": "+5%", "tono": "+0Hz"},
    {"voz": "es-ES-AlvaroNeural", "velocidad": "+5%", "tono": "-3Hz"},
    {"voz": "es-ES-ElviraNeural", "velocidad": "+5%", "tono": "+1Hz"},
    {"voz": "es-CO-SalomeNeural", "velocidad": "+5%", "tono": "-1Hz"},
    {"voz": "es-AR-ElenaNeural", "velocidad": "+5%", "tono": "+2Hz"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+5%", "tono": "-2Hz"},
    {"voz": "es-PE-CamilaNeural", "velocidad": "+5%", "tono": "+0Hz"},
    {"voz": "es-US-PalomaNeural", "velocidad": "+5%", "tono": "-1Hz"},
    {"voz": "es-ES-XimenaNeural", "velocidad": "+5%", "tono": "+1Hz"},
    {"voz": "es-MX-CandelaNeural", "velocidad": "+5%", "tono": "-3Hz"},
    {"voz": "es-ES-AbrilNeural", "velocidad": "+5%", "tono": "-2Hz"},
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
# 🧑 GENERADOR DE PERSONAJES
# ================================================================
def generar_perfil_personaje_shorts():
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
        "with mestizo features and light olive skin",
        "with light brown skin and freckles",
        "with olive skin and a strong jaw",
        "with pale skin and green eyes",
        "with fair skin and blue eyes",
        "with tan skin and a warm smile",
        "with light beige skin and a serious expression",
    ]
    profesiones_masculinas = [
        "trailero de 45 años en carretera nocturna",
        "policía de 38 años en su turno nocturno",
        "agricultor de 50 años en una hacienda del siglo XIX",
        "fotógrafo urbano de 28 años en edificios abandonados",
        "taxista nocturno de 55 años en zonas peligrosas",
        "velador de 60 años en un panteón viejo",
        "arqueólogo de 40 años excavando en la selva",
        "enfermero de 30 años en un psiquiátrico abandonado",
        "minero de 48 años en una mina clausurada",
    ]
    profesiones_femeninas = [
        "estudiante de medicina de 22 años en un hospital antiguo",
        "periodista de investigación de 35 años en un pueblo fantasma",
        "bailarina de 25 años en un teatro embrujado",
    ]
    profesiones_neutras = [
        "agricultor de 50 años en una hacienda del siglo XIX",
        "fotógrafo urbano de 28 años en edificios abandonados",
        "taxista nocturno de 55 años en zonas peligrosas",
        "arqueólogo de 40 años excavando en la selva",
        "enfermero de 30 años en un psiquiátrico abandonado",
        "minero de 48 años en una mina clausurada",
    ]
    genero = random.choice(generos)
    if genero == "man":
        profesion = random.choice(profesiones_masculinas + profesiones_neutras)
        articulo = "un"
    else:
        profesion = random.choice(profesiones_femeninas + profesiones_neutras)
        articulo = "una"
    perfil_fisico = (
        f"a {random.choice(edades)} Mexican {genero}, "
        f"{random.choice(rasgos)}, "
        f"with {random.choice(cabellos)}, {random.choice(vestimentas)}"
    )
    return perfil_fisico, profesion, articulo, genero

PERFIL_PERSONAJE_SHORTS, PERSONAJE_SHORTS, ARTICULO_SHORTS, GENERO_SHORTS = generar_perfil_personaje_shorts()
ESTADO_HISTORIA_SHORTS = random.choice([
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas",
    "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit",
    "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
    "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"
])

# ================================================================
# 🎵 AUDIO DE FONDO CON PERSISTENCIA
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
# 🧼 LIMPIADOR DE PROMPTS
# ================================================================
def limpiar_prompt(prompt, estilo_visual=None, paleta_color=None):
    estilo = estilo_visual or ESTILO_VISUAL_ACTUAL
    paleta = paleta_color or PALETA_COLOR_ACTUAL
    if not prompt:
        prompt = "Mexican street at night, bright lighting"
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
    prompt_base = re.sub(r"\s+", " ", prompt).strip()[:200]
    modificadores_calidad = (
        f", {estilo}, color palette of {paleta}, "
        "vertical 9:16 portrait format for mobile, single solitary person, exactly one person, "
        "clean smooth skin, natural facial complexion with light skin tone, no freckles, no blemishes, no spots, "
        "sharp focus, bright well-lit scene, no dark underexposed areas, no text, no watermark"
    )
    return prompt_base + modificadores_calidad

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
        json_str = re.sub(r'(?<!\\)\r?\n', r'\\n', json_str)
        return json_str
    return respuesta

# ================================================================
# 🗂️ ESTADO DE SHORTS (3 partes)
# ================================================================
def cargar_estado():
    try:
        with open(ESTADO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"parte": 1, "ultimo_fondo": None, "historia": None}

def guardar_estado(estado):
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)
    print("✅ Estado de Shorts guardado")

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
# EXPANDIR TEXTO CORTO (300-360 palabras)
# ================================================================
def expandir_texto_corto(texto_corto, ubicacion, personaje):
    print("🔄 Expandiendo texto corto...")
    prompt = f"""Eres un escritor experto en terror. Expande el siguiente relato para que tenga entre 300 y 360 palabras.
    Añade más descripciones sensoriales (sonidos, olores, texturas), más pensamientos internos del protagonista 
    y más detalles del entorno en {ubicacion}.
    Mantén la trama exactamente igual, solo añade contenido donde sea natural.

    RELATO ORIGINAL (debe expandirse):
    {texto_corto}

    Devuelve SOLO el relato expandido (300-360 palabras), sin títulos ni comentarios adicionales.
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
        if len(texto_expandido.split()) > 200:
            return texto_expandido
        else:
            return texto_corto + " El miedo crecía con cada paso. El silencio era ensordecedor."
    except Exception as e:
        print(f"❌ Error expandiendo: {e}")
        return texto_corto

# ================================================================
# TRUNCAR TEXTO LARGO (300-360 palabras)
# ================================================================
def truncar_texto_largo(texto, max_palabras=340):
    palabras = texto.split()
    if len(palabras) <= max_palabras:
        return texto
    for i in range(max_palabras, max_palabras - 30, -1):
        if i < len(palabras) and palabras[i-1].endswith(('.', '!', '?')):
            return ' '.join(palabras[:i])
    return ' '.join(palabras[:max_palabras])

# ================================================================
# GENERAR HISTORIA COMPLETA (300-360 palabras)
# ================================================================
def generar_historia_completa():
    prompt = f"""Eres un EXPERTO EN STORYTELLING PARA YOUTUBE SHORTS.
Crea una historia de TERROR/PARANORMAL en PRIMERA PERSONA, protagonizada por {ARTICULO_SHORTS} {PERSONAJE_SHORTS}.
La historia debe tener EXACTAMENTE entre 300 y 360 palabras (NO más de 360, NO menos de 300), y estar dividida en TRES PARTES claras con un CLIFFHANGER en cada punto de división.
Ambientada en el estado de {ESTADO_HISTORIA_SHORTS}, México.

DESCRIPCIÓN FÍSICA DEL PROTAGONISTA (ÚNICA PARA ESTE SHORT):
"{PERFIL_PERSONAJE_SHORTS}"

REGLAS DE TÍTULO (IMPORTANTE PARA CTR):
- Debe ser DESCRIPTIVO y DIRECTO. Sin metáforas confusas.
- Debe decir EXACTAMENTE de qué trata el video.
- Entre 40 y 60 caracteres exactos.

REGLAS DE INICIO (IMPORTANTE PARA RETENCIÓN):
- La PRIMERA FRASE del relato debe ser un GANCHO IMPACTANTE de máximo 5 palabras.
- Ejemplo: "Esa noche no estaba solo."
- Ejemplo: "El manicomio guardaba un secreto."

REGLAS DE CONTENIDO:
- Escribe con ORTOGRAFÍA Y ACENTUACIÓN CORRECTA en español (usa ñ, acentos, etc.).
- Desarrollo: construye tensión, describe sonidos, olores, sensaciones.
- Parte 1: presentación y primera tensión.
- Parte 2: desarrollo y segundo cliffhanger.
- Parte 3: resolución final.
- ANTI-REPETICIÓN: NO repitas frases.
- PALETA DE COLOR: {PALETA_COLOR_ACTUAL}
- CTA OBLIGATORIO al final de la Parte 3: "¿Te gustó este relato? SUSCRÍBETE para más historias de terror."

ETIQUETAS: Genera 20 etiquetas separadas por comas. El total de caracteres de las etiquetas debe superar los 200 caracteres.

Devuelve ESTRICTAMENTE este JSON válido:
{{
  "titulo": "Título descriptivo y directo de 40-60 caracteres",
  "texto_completo": "Historia completa de 300-360 palabras... (con la primera frase como gancho)",
  "palabras_portada": "PALABRA CLAVE (ej: TERROR, APARICIÓN)",
  "tags": "tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9, tag10, tag11, tag12, tag13, tag14, tag15, tag16, tag17, tag18, tag19, tag20"
}}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 700,
        "response_format": {"type": "json_object"}
    }
    respuesta = ""
    for intento in range(5):
        try:
            print(f"🔄 Intento {intento+1}/5 generando historia...")
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            r.raise_for_status()
            respuesta = r.json()["choices"][0]["message"]["content"].strip()
            json_str = limpiar_respuesta_json(respuesta)
            data = json.loads(json_str, strict=False)
            if "texto_completo" not in data or len(data["texto_completo"]) < 100:
                raise ValueError("Texto demasiado corto")
            data["texto_completo"] = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', data["texto_completo"])
            data["texto_completo"] = re.sub(r'\n{3,}', '\n\n', data["texto_completo"])
            titulo = data.get("titulo", "").strip()
            if len(titulo) < 40:
                data["titulo"] = f"{titulo} | Relato de Terror"[:60]
            elif len(titulo) > 60:
                data["titulo"] = titulo[:57] + "..."
            tags = data.get("tags", "")
            tags_list = [t.strip() for t in tags.split(",") if t.strip()]
            if len(tags_list) < 20:
                extras = ["terror", "shorts", "mexico", "paranormal", "miedo", "relatos", "leyendas", "misterio", "suspenso", "noche", "oscuridad", "sombras", "aparicion", "escalofrio", "casas", "embrujadas", "pueblo", "real", "historias", "leyenda"]
                while len(tags_list) < 20:
                    tags_list.append(random.choice(extras))
            data["tags"] = ", ".join(tags_list[:20])
            return data
        except Exception as e:
            print(f"❌ Intento {intento+1}/5 falló: {e}")
            if intento < 4:
                time.sleep(10 + intento * 5)
    print("⚠️ Creando fallback manual...")
    texto_fallback = f"Esa noche en {ESTADO_HISTORIA_SHORTS}, {ARTICULO_SHORTS} {PERSONAJE_SHORTS} sintió que algo no andaba bien. El silencio era pesado. De repente, un ruido extraño rompió la calma. No era el viento, no era un animal. Era algo más. Algo que parecía venir de las sombras. El corazón le latía con fuerza. Entonces, una figura emergió de la oscuridad. No tenía rostro, pero parecía mirarlo directamente. Sin tiempo para reaccionar, sintió un frío helado recorrer su espalda. Era el miedo hecho carne."
    return {
        "titulo": f"El misterio de {ESTADO_HISTORIA_SHORTS}",
        "texto_completo": texto_fallback,
        "palabras_portada": "TERROR",
        "tags": "terror, shorts, mexico, paranormal, miedo, relatos, leyendas, misterio, suspenso, noche, oscuridad, sombras, aparicion, escalofrio, casas, embrujadas, pueblo, real, historias, leyenda"
    }

# ================================================================
# DIVIDIR TEXTO EN 3 PARTES (~100-120 palabras cada una)
# ================================================================
def dividir_texto(texto, n_partes=3):
    palabras = texto.split()
    total = len(palabras)
    if total < n_partes * 10:
        return [texto]
    tam = total // n_partes
    partes = []
    for i in range(n_partes):
        inicio = i * tam
        fin = (i + 1) * tam if i < n_partes - 1 else total
        parte = " ".join(palabras[inicio:fin])
        partes.append(parte.strip())
    return partes

# ================================================================
# DIVIDIR TEXTO EN SEGMENTOS DE ~50 PALABRAS (~10 SEGUNDOS)
# ================================================================
def dividir_en_segmentos(texto, palabras_por_segmento=55):
    palabras = texto.split()
    total = len(palabras)
    if total <= palabras_por_segmento:
        return [texto]
    segmentos = []
    for i in range(0, total, palabras_por_segmento):
        segmento = " ".join(palabras[i:i+palabras_por_segmento])
        segmentos.append(segmento.strip())
    return segmentos

# ================================================================
# GENERAR IMÁGENES PARA CADA SEGMENTO (con texto específico)
# ================================================================
def generar_imagenes_para_segmentos(segmentos, perfil, ubicacion, estilo, paleta, intentos_por_imagen=3):
    imagenes = []
    for idx, seg in enumerate(segmentos):
        print(f"  🖼️ Generando imagen para segmento {idx+1}/{len(segmentos)}...")
        prompt_imagen = f"scene in {ubicacion}, showing the described moment"
        img_url = generar_imagen_vertical(
            prompt_imagen,
            perfil_personaje=perfil,
            estado_mexico=ubicacion,
            estilo_visual=estilo,
            paleta_color=paleta,
            texto_segmento=seg,
            intentos=intentos_por_imagen
        )
        if not img_url:
            print(f"⚠️ Falló imagen para segmento {idx+1}, usando placeholder")
            img_url = "https://via.placeholder.com/1080x1920/1a1a1a/ff0000?text=Terror"
        imagenes.append(img_url)
        time.sleep(2)  # Pequeña pausa entre imágenes
    return imagenes

# ================================================================
# GENERAR IMAGEN VERTICAL INDIVIDUAL
# ================================================================
def generar_imagen_vertical(prompt, perfil_personaje=None, estado_mexico=None, estilo_visual=None, paleta_color=None, texto_segmento="", intentos=3):
    perfil = perfil_personaje or PERFIL_PERSONAJE_SHORTS
    ubicacion = estado_mexico or ESTADO_HISTORIA_SHORTS
    if texto_segmento:
        prompt = f"{prompt}, scene depicting: {texto_segmento[:150]}"
    prompt_completo = f"{perfil} en {ubicacion}, {prompt}, bright cinematic lighting, intense facial expression of fear or surprise, high contrast colors, vibrant highlights, sharp focus, dramatic shadows"
    prompt_limpio = limpiar_prompt(prompt_completo, estilo_visual, paleta_color)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_limpio,
        "negative_prompt": "oscuro, dark, underexposed, low light, heavy shadows, too dark, over-saturated reds, over-saturated oranges, piel oscura, moreno, indígena, manchas, textura fea, deforme, clonado, duplicado, gore, sangre, horror, terror, monstruo, demacrado, freckles, blemishes, skin spots, imperfections",
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
# GENERAR AUDIO PARA UNA PARTE
# ================================================================
def generar_audio(texto, index):
    texto_limpio = re.sub(r"imagen_prompt.*", "", texto, flags=re.IGNORECASE).strip()
    texto_limpio = limpiar_texto_para_audio(texto_limpio)
    if len(texto_limpio) < 50:
        print(f"⚠️ Texto corto ({len(texto_limpio)} caracteres). Rellenando...")
        texto_limpio += " El miedo crecía con cada paso. El silencio era ensordecedor."
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
        asyncio.run(_generar())
        print(f"✅ Audio Short generado ({index}) con {voz}")
        return filename
    except Exception as e:
        print(f"❌ Error audio: {e}")
        return None

# ================================================================
# MONTAR VIDEO CON MÚLTIPLES IMÁGENES Y UN SOLO AUDIO
# ================================================================
def montar_video_shorts(imagenes_urls, audio_path, fondo_path, salida="short_final.mp4"):
    if not imagenes_urls or not audio_path:
        raise ValueError("No hay imágenes o audio para montar")
    
    # Cargar audio
    audio_clip = AudioFileClip(audio_path)
    duracion_total = audio_clip.duration
    
    # Crear clips de video para cada imagen
    clips_video = []
    # Duración por imagen: proporcional al número de caracteres aproximado? 
    # Como no tenemos el texto original aquí, repartimos el tiempo equitativamente
    duracion_por_imagen = duracion_total / len(imagenes_urls)
    
    for i, img_url in enumerate(imagenes_urls):
        try:
            r = requests.get(img_url, timeout=30)
            r.raise_for_status()
            img_path = f"temp_short_{i}.jpg"
            with open(img_path, "wb") as f:
                f.write(r.content)
            with Image.open(img_path) as img:
                img_fitted = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
                img_fitted.save(img_path)
            video_clip = ImageClip(img_path).set_duration(duracion_por_imagen)
            clips_video.append(video_clip)
        except Exception as e:
            print(f"⚠️ Error procesando imagen {i}: {e}")
            # Usar una imagen de placeholder si falla
            continue
    
    if not clips_video:
        raise ValueError("No se pudieron crear clips de video")
    
    video = concatenate_videoclips(clips_video, method="compose")
    
    # Mezclar audio de fondo
    if fondo_path and os.path.exists(fondo_path):
        try:
            fondo_clip = AudioFileClip(fondo_path)
            if fondo_clip.duration < duracion_total:
                veces = int(duracion_total / fondo_clip.duration) + 1
                fondo_clip = concatenate_audioclips([fondo_clip] * veces)
            fondo_clip = fondo_clip.subclip(0, duracion_total).volumex(0.08)
            audio_final = CompositeAudioClip([audio_clip, fondo_clip])
        except Exception as e:
            print(f"⚠️ Error en audio de fondo: {e}")
            audio_final = audio_clip
    else:
        audio_final = audio_clip
    
    video = video.set_audio(audio_final)
    video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")
    
    # Limpiar recursos
    video.close()
    audio_final.close()
    audio_clip.close()
    for c in clips_video:
        c.close()
    
    print(f"✅ Short vertical creado: {salida}")
    return salida

# ================================================================
# SUBIR A YOUTUBE
# ================================================================
def subir_a_youtube(video_path, titulo, texto_corto, etiquetas, parte):
    creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
    youtube = build("youtube", "v3", credentials=creds)
    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]
    
    if parte == 1:
        cta_texto = "📌 Parte 2 disponible en unas horas. Sígueme para no perdértela."
    elif parte == 2:
        cta_texto = "📌 Parte 3 disponible en unas horas. Sígueme para no perdértela."
    else:
        cta_texto = "👻 ¿Te gustó la historia? SUSCRÍBETE para más relatos de terror."
    
    descripcion = f"""📌 {texto_corto[:150]}...

{cta_texto}

🔴 SUSCRÍBETE: {CANAL_LINK}
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
# LIMPIEZA DE TEMPORALES DE SHORTS
# ================================================================
def limpiar_temporales_shorts():
    for f in os.listdir("."):
        if (f.startswith("temp_short_") or f.startswith("audio_short_")) and (f.endswith(".jpg") or f.endswith(".mp3")):
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
# MAIN (3 PARTES, MÚLTIPLES IMÁGENES POR PARTE)
# ================================================================
def main():
    print("🎬 Iniciando Bot de SHORTS (3 partes, imágenes cada ~10s)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    estado = cargar_estado()
    parte_actual = estado.get("parte", 1)
    print(f"📌 Estado actual: Parte {parte_actual}")

    fondo_path = seleccionar_fondo_disponible(estado)

    # Si es Parte 1: generar nueva historia
    if parte_actual == 1:
        print("🆕 Generando nueva historia completa (3 partes)...")
        historia = generar_historia_completa()
        if not historia:
            print("❌ No se pudo generar la historia")
            return
            
        texto_completo = historia.get("texto_completo", "")
        palabras = len(texto_completo.split())
        if palabras < 250:
            print(f"⚠️ Texto corto ({palabras} palabras). Expandiendo...")
            texto_completo = expandir_texto_corto(texto_completo, ESTADO_HISTORIA_SHORTS, PERSONAJE_SHORTS)
        elif palabras > 400:
            print(f"⚠️ Texto largo ({palabras} palabras). Truncando...")
            texto_completo = truncar_texto_largo(texto_completo, 340)
        else:
            print(f"✅ Texto con longitud ideal ({palabras} palabras)")

        # Dividir en 3 partes
        partes = dividir_texto(texto_completo, 3)
        if len(partes) < 3:
            print("⚠️ No se pudieron generar 3 partes. Añadiendo relleno...")
            while len(partes) < 3:
                partes.append("El misterio continuaba. La noche guardaba más secretos.")
        
        # Guardar en estado
        historia_guardada = {
            "titulo": historia.get("titulo", f"Misterio en {ESTADO_HISTORIA_SHORTS}"),
            "partes": partes,
            "palabras_portada": historia.get("palabras_portada", "TERROR"),
            "tags": historia.get("tags", ""),
            "perfil_personaje": PERFIL_PERSONAJE_SHORTS,
            "estado_mexico": ESTADO_HISTORIA_SHORTS,
            "paleta_color": PALETA_COLOR_ACTUAL,
            "estilo_visual": ESTILO_VISUAL_ACTUAL
        }
        estado["historia"] = historia_guardada
        estado["parte"] = 2
        guardar_estado(estado)
        texto_publicar = partes[0]
        parte_num = 1
    else:
        # Parte 2 o 3: recuperar del estado
        historia_guardada = estado.get("historia")
        if not historia_guardada or not historia_guardada.get("partes"):
            print("⚠️ No hay historia guardada. Reiniciando a Parte 1...")
            estado["parte"] = 1
            guardar_estado(estado)
            return main()
        
        partes = historia_guardada.get("partes", [])
        if parte_actual == 2 and len(partes) >= 2:
            texto_publicar = partes[1]
            parte_num = 2
        elif parte_actual == 3 and len(partes) >= 3:
            texto_publicar = partes[2]
            parte_num = 3
        else:
            print("⚠️ No hay más partes disponibles. Reiniciando...")
            estado["parte"] = 1
            guardar_estado(estado)
            return main()

    # Recuperar metadatos
    historia_guardada = estado.get("historia", {})
    titulo = historia_guardada.get("titulo", "Relato de Terror")
    tags = historia_guardada.get("tags", "terror, shorts, mexico")
    perfil = historia_guardada.get("perfil_personaje", PERFIL_PERSONAJE_SHORTS)
    ubicacion = historia_guardada.get("estado_mexico", ESTADO_HISTORIA_SHORTS)
    paleta = historia_guardada.get("paleta_color", PALETA_COLOR_ACTUAL)
    estilo = historia_guardada.get("estilo_visual", ESTILO_VISUAL_ACTUAL)

    print(f"🎤 Voz: {CONFIG_VOZ_ACTUAL['voz']} (1.05x)")
    print(f"📍 Ubicación: {ubicacion}")
    print(f"🎨 Paleta: {paleta[:50]}...")
    print(f"📝 Publicando Parte {parte_num} ({len(texto_publicar)} caracteres, {len(texto_publicar.split())} palabras)")

    # Dividir el texto de esta parte en segmentos de ~55 palabras (~10 segundos)
    segmentos = dividir_en_segmentos(texto_publicar, palabras_por_segmento=55)
    print(f"📌 Texto dividido en {len(segmentos)} segmentos (aproximadamente {len(segmentos)*10} segundos)")

    # Generar imágenes para cada segmento
    print("🎨 Generando imágenes para cada segmento...")
    imagenes_urls = generar_imagenes_para_segmentos(
        segmentos,
        perfil=perfil,
        ubicacion=ubicacion,
        estilo=estilo,
        paleta=paleta,
        intentos_por_imagen=3
    )
    
    if not imagenes_urls:
        print("❌ No se generaron imágenes. Abortando.")
        return

    print("⏳ Esperando 4 segundos antes del audio...")
    time.sleep(4)

    print("🎙️ Generando audio...")
    audio_path = generar_audio(texto_publicar, parte_num)
    if not audio_path:
        print("❌ Falló audio")
        return

    print("🎬 Montando Short vertical con múltiples imágenes...")
    video_path = montar_video_shorts(imagenes_urls, audio_path, fondo_path, "short_final.mp4")

    print("⬆️ Subiendo Short...")
    subir_a_youtube(video_path, titulo, texto_publicar, tags, parte_num)

    # Actualizar estado para la siguiente parte
    if parte_actual == 1:
        estado["parte"] = 2
        print("⏩ Parte 1 publicada. Siguiente: Parte 2")
    elif parte_actual == 2:
        estado["parte"] = 3
        print("⏩ Parte 2 publicada. Siguiente: Parte 3")
    else:
        estado["parte"] = 1
        estado["historia"] = None
        print("🎉 Parte 3 publicada. Ciclo completado. Reiniciando a Parte 1")
    
    guardar_estado(estado)
    limpiar_temporales_shorts()
    print("🎉 Proceso de Shorts completado")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
