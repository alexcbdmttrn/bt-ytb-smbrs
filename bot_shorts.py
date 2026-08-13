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
import gtts
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
# 🎤 SOLO 4 VOCES MASCULINAS - SE SELECCIONA UNA AL INICIO
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural", "velocidad": "+10%", "tono": "-2Hz"},
    {"voz": "es-ES-AlvaroNeural", "velocidad": "+10%", "tono": "-3Hz"},
    {"voz": "es-MX-ManuelNeural", "velocidad": "+10%", "tono": "-1Hz"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+10%", "tono": "-2Hz"},
]
# ✅ Se selecciona UNA voz al inicio y se usa para TODO el video
CONFIG_VOZ_ACTUAL = random.choice(VOCES_DISPONIBLES)

# ================================================================
# 🎨 PALETAS REORDENADAS
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
# 🧑 GENERADOR DE PERSONAJES
# ================================================================
def generar_perfil_personaje_shorts():
    edades = ["21-year-old", "28-year-old", "35-year-old", "42-year-old", "50-year-old", "60-year-old"]
    vestimentas = [
        "wearing a denim jacket and grey shirt",
        "wearing a dark green coat and wool scarf",
        "wearing a simple white shirt and leather belt",
        "wearing an old blue mechanic uniform",
        "wearing a dark sweater and classic trousers",
        "wearing a red flannel shirt and jeans",
        "wearing a black leather jacket and boots",
        "wearing a charro suit with silver buttons",
        "wearing a baseball cap and hoodie",
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
        "guardia de seguridad de 45 años en una fábrica abandonada",
        "pescador de 55 años en un pueblo costero",
        "carpintero de 60 años en un taller antiguo",
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
# 🧼 LIMPIADOR DE PROMPTS
# ================================================================
def limpiar_prompt_base(prompt, estilo_visual=None, paleta_color=None):
    estilo = estilo_visual or ESTILO_VISUAL_ACTUAL
    paleta = paleta_color or PALETA_COLOR_ACTUAL
    if not prompt:
        prompt = "Mexican street at night, bright lighting"
    prompt = re.sub(r"\n+", " ", prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r"[^\x00-\x7F]+", "", prompt)
    palabras_sucias = [
        r"\bgrainy\b", r"\bvhs\b", r"\bchiaroscuro\b", r"\bdirt\b", r"\bgrime\b",
        r"\blemish\b", r"\bspots\b", r"\bterro\b", r"\bhorror\b", r"\bsangre\b",
        r"\bblood\b", r"\bgore\b", r"\bdemacrad[oa]s?\b", r"\bzombies?\b",
        r"\bdisfigured\b", r"\bwounds?\b", r"\bmonster\b"
    ]
    for pattern in palabras_sucias:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)
    prompt_base = re.sub(r"\s+", " ", prompt).strip()[:200]
    modificadores_calidad = (
        f", {estilo}, color palette of {paleta}, "
        "vertical 9:16 format, wide environmental establishing shot, medium-wide shot, "
        "subject small in frame or partially visible, scene and location as focal point, "
        "single person, exactly one person, "
        "clean smooth skin, natural facial complexion, no freckles, no blemishes, no spots, "
        "sharp focus, bright well-lit scene, no dark underexposed areas, no text, no watermark"
    )
    return prompt_base + modificadores_calidad

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
# 🆕 GESTIÓN DE TÍTULOS PUBLICADOS (sin repetir jamás)
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
# EXPANDIR TEXTO CORTO
# ================================================================
def expandir_texto_corto(texto_corto, ubicacion, personaje):
    print("🔄 Expandiendo texto corto...")
    prompt = f"""Eres un escritor experto en micro-relatos de terror. Expande el siguiente relato para que tenga entre 150 y 170 palabras.
Añade más descripciones sensoriales (sonidos, olores, texturas), más pensamientos internos del protagonista 
y más detalles del entorno en {ubicacion}.
Mantén la trama exactamente igual, solo añade contenido donde sea natural.
NO agregues ningún llamado a suscribirse ni CTA — solo la narración pura.

RELATO ORIGINAL (debe expandirse):
{texto_corto}

Devuelve SOLO el relato expandido (150-170 palabras), sin títulos ni comentarios adicionales.
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
# GENERAR HISTORIA COMPLETA — MICRO-RELATO VIRAL (150-170 palabras)
# ================================================================
def generar_historia_completa():
    hashtags_disponibles = [
        "#paranormal", "#terror", "#misterio", "#suspenso", "#leyendasurbanas",
        "#miedo", "#sobrenatural", "#oscuridad", "#fantasma", "#espanto",
        "#escalofrio", "#noche", "#pueblo", "#casasembrujadas", "#relatos",
        "#brujas", "#aparicion", "#almas", "#pena", "#real"
    ]
    hashtags_elegidos = random.sample(hashtags_disponibles, 3)
    hashtags_descripcion_base = "#Shorts " + " ".join(hashtags_elegidos)

    titulos_pub = cargar_titulos_publicados()["titulos"][-10:]
    titulos_referencia = "\n".join([f"- {t}" for t in titulos_pub]) if titulos_pub else "Ninguno aún."

    prompt = f"""Eres un MAESTRO DEL MICRO-RELATO DE TERROR, especializado en historias virales para YouTube Shorts.
Crea una historia de TERROR/PARANORMAL en PRIMERA PERSONA, protagonizada por {ARTICULO_SHORTS} {PERSONAJE_SHORTS}.

🚫 TÍTULOS YA PUBLICADOS (NO REPETIR NI PARECERSE A ESTOS):
{titulos_referencia}

🎯 REGLA CRÍTICA DE LONGITUD:
- EXACTAMENTE entre 150 y 170 palabras (NO más de 170, NO menos de 150).
- Esto debe durar entre 50 y 65 segundos al ser narrado a velocidad +10%.
- Cada palabra cuenta: NO hay espacio para relleno.

📐 ESTRUCTURA DE MICRO-RELATO VIRAL:
1. GANCHO (5-10 palabras): Frase inicial impactante que atrape en el primer segundo.
2. CONTEXTO (20-30 palabras): Establece el lugar y situación rápidamente.
3. TENSIÓN (80-90 palabras): Construye el miedo con detalles sensoriales precisos.
4. TWIST FINAL (30-40 palabras): Remate inesperado que deje al espectador impactado.

⚠️ REGLAS DEL TWIST FINAL:
- Debe ser INESPERADO pero LÓGICO con la historia.
- Debe generar ganas de COMENTAR y COMPARTIR.
- NO uses finales abiertos tipo "y nunca supe qué pasó".
- SÍ usa revelaciones concretas que dejen escalofríos.

REGLAS DEL TÍTULO (SEO 2026):
- Longitud: entre 55 y 75 caracteres.
- Palabra clave al inicio (front-loaded).
- Debe sugerir el twist sin spoilearlo.
- NO debe parecerse a ningún título ya publicado listado arriba.

REGLAS DE DESCRIPCIÓN:
- "gancho_descripcion": 1 línea de MÁXIMO 90 caracteres que genere curiosidad.
- "contexto_descripcion": 1 oración con palabras clave naturales.

REGLAS DE ETIQUETAS (10-15 tags long-tail, máx 480 caracteres):
- Mezcla etiquetas específicas del lugar + tipo de fenómeno + micro-relato.

REGLAS GENERALES:
- PRIMERA FRASE = GANCHO IMPACTANTE de máximo 5 palabras.
- Ortografía perfecta (acentos, ñ, signos).
- NO repitas frases.
- PALETA: {PALETA_COLOR_ACTUAL}
- IMPORTANTE: el campo "texto_completo" debe ser una historia AUTOCONCLUSIVA con final cerrado y twist impactante.
- NO incluyas CTA de suscripción en el relato.

Devuelve ESTRICTAMENTE este JSON válido:
{{
  "titulo": "Título 55-75 caracteres, SIN hashtags, original",
  "gancho_descripcion": "Gancho de máx 90 caracteres",
  "contexto_descripcion": "1 oración con contexto",
  "texto_completo": "Micro-relato AUTOCONCLUSIVO de 150-170 palabras con twist final impactante",
  "palabras_portada": "2-3 PALABRAS CLAVE",
  "tags": "tag long-tail 1, tag long-tail 2, ... (10-15 tags)"
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
            print(f"🔄 Intento {intento+1}/6 generando historia...")
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
                    print("   ❌ json5 no está instalado. Instálalo con: pip install json5")
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
                titulo = f"{titulo} - Testimonio real de terror en {ESTADO_HISTORIA_SHORTS}"
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

            tags_raw = data.get("tags", "")
            tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]
            tags_list = tags_list[:15]

            extras_long_tail = [
                f"relatos de terror en {ESTADO_HISTORIA_SHORTS.lower()}",
                "leyendas urbanas mexicanas",
                "historias paranormales reales",
                "testimonios de terror mexico",
                "fenomenos paranormales reales",
                "relatos cortos de miedo",
                "historias de fantasmas mexico",
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

            data["hashtags_descripcion"] = hashtags_descripcion_base

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
# 🆕 DIVIDIR TEXTO POR ORACIONES (sin cortes antinaturales)
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
# GENERAR PROMPT DE IMAGEN POR SEGMENTO
# ================================================================
def generar_prompt_imagen_segmento(segmento_texto, perfil, ubicacion, estilo_visual, paleta_color):
    prompt = f"""Eres un director de fotografía experto en composición cinematográfica.
Interpreta el siguiente fragmento de un relato de terror y genera un PROMPT DE IMAGEN EN INGLÉS para una foto vertical (9:16) que represente la escena exacta.

Fragmento del relato:
\"\"\"
{segmento_texto}
\"\"\"

Reglas estrictas de composición:
- PLANO: Wide shot o extreme wide shot. PROHIBIDO close-up, portrait, headshot.
- Enfoque principal: el ENTORNO, ARQUITECTURA u OBJETOS mencionados.
- Si el fragmento menciona al personaje, inclúyelo ocupando como MÁXIMO el 20% del área, a distancia.
- Si solo describe ambiente, NO incluyas personas.
- Estilo: professional hyperrealistic photography, 4k, ultra-detailed, natural lighting.
- Paleta de color: {paleta_color}
- Personaje (si aparece): apariencia normal y agradable, piel sana.
- Restricciones explícitas: "no close-up face, no portrait, no face filling frame, person occupies max 20% of frame, environment as main focus, no gore, no blood"

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
        prompt_imagen += f", {estilo_visual}, vertical 9:16, wide establishing shot, person occupies max 20% of frame, environment as main subject, no close-up face, no portrait, no blood, no gore"
        return prompt_imagen
    except Exception as e:
        print(f"⚠️ Error generando prompt de imagen: {e}")
        return f"Wide establishing shot of {ubicacion}, depicting: {segmento_texto[:100]}, {estilo_visual}, vertical 9:16, no close-up face, environment as main subject"

# ================================================================
# GENERAR IMAGEN VERTICAL
# ================================================================
def generar_imagen_vertical(prompt, intentos=3):
    prompt_limpio = limpiar_prompt_base(prompt, ESTILO_VISUAL_ACTUAL, PALETA_COLOR_ACTUAL)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_limpio,
        "negative_prompt": (
            "close-up face, portrait, headshot, person filling frame, face occupying more than 20% of image, "
            "centered subject, camera pointed directly at face, deformed face, disfigured, mutated, bad anatomy, "
            "extra limbs, missing limbs, extra fingers, fused fingers, asymmetrical eyes, cross-eyed, malformed features, "
            "uncanny valley, plastic skin, waxy skin, gore, blood, bloody, wounds, cuts, bruises, gaunt, emaciated, "
            "sickly, decayed skin, rotting, zombie-like, corpse-like, grotesque, ugly, unattractive, monstrous features, "
            "cloned faces, duplicate people, multiple subjects, over-saturated, oversharpened, low quality, blurry, "
            "grainy, vhs, chiaroscuro, dirt, grime, blemishes, spots, text, watermark, logo"
        ),
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
# GENERAR RECURSOS POR SEGMENTO
# ================================================================
def generar_recursos_por_segmento(segmentos, perfil, ubicacion, estilo, paleta, intentos_por_imagen=3):
    resultados_temporales = []

    for idx, seg in enumerate(segmentos):
        print(f"  🎬 Procesando segmento {idx+1}/{len(segmentos)} ({len(seg.split())} palabras)...")

        prompt_imagen = generar_prompt_imagen_segmento(seg, perfil, ubicacion, estilo, paleta)
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
# ✅ GENERAR AUDIO - UNA SOLA VOZ PARA TODO EL VIDEO (CORREGIDO)
# ================================================================
def generar_audio(texto, index, intentos=4):
    texto_limpio = re.sub(r"imagen_prompt.*", "", texto, flags=re.IGNORECASE).strip()
    texto_limpio = limpiar_caracteres_para_tts(texto_limpio)
    texto_limpio = limpiar_texto_para_audio(texto_limpio)

    if len(texto_limpio) < 30:
        print(f"⚠️ Texto corto ({len(texto_limpio)} caracteres). Rellenando...")
        texto_limpio = "Esa noche en la carretera, el silencio era tan denso que podía cortarse con un cuchillo. El miedo lo envolvía todo. No podía escapar."

    if not texto_limpio:
        return None

    filename = f"audio_short_{index}.mp3"

    # ✅ USAR SIEMPRE LA MISMA VOZ (CONFIG_VOZ_ACTUAL seleccionada al inicio)
    voz = CONFIG_VOZ_ACTUAL["voz"]
    rate = CONFIG_VOZ_ACTUAL["velocidad"]
    pitch = CONFIG_VOZ_ACTUAL["tono"]

    print(f"🔊 Generando audio para segmento {index} con voz: {voz}")

    for intento in range(intentos):
        print(f"🎤 Intento {intento+1}/{intentos} con voz: {voz}")

        async def _generar():
            communicate = edge_tts.Communicate(texto_limpio, voz, rate=rate, pitch=pitch)
            await communicate.save(filename)

        try:
            asyncio.run(_generar())
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                print(f"✅ Audio segmento {index} generado con {voz}")
                return filename
        except Exception as e:
            print(f"❌ Falló con {voz}: {e}")
            if intento < intentos - 1:
                espera = 5 * (intento + 1)
                print(f"⏳ Esperando {espera}s antes de reintentar...")
                time.sleep(espera)

    print("⚠️ Todos los intentos con edge-tts fallaron. Usando gTTS como fallback...")
    try:
        from gtts import gTTS
        tts = gTTS(texto_limpio, lang="es")
        tts.save(filename)
        print(f"✅ Audio generado con gTTS (fallback) para segmento {index}")
        return filename
    except Exception as e:
        print(f"❌ Fallback gTTS también falló: {e}")
        return None

# ================================================================
# GENERAR AUDIO CTA FINAL (misma voz que el relato)
# ================================================================
def generar_audio_cta_final():
    cta_texto = "Relatos completos en el canal. Visítanos."
    filename = "audio_cta_final.mp3"
    
    voz = CONFIG_VOZ_ACTUAL["voz"]
    rate = CONFIG_VOZ_ACTUAL["velocidad"]
    pitch = CONFIG_VOZ_ACTUAL["tono"]
    
    async def _generar():
        communicate = edge_tts.Communicate(cta_texto, voz, rate=rate, pitch=pitch)
        await communicate.save(filename)
    
    try:
        asyncio.run(_generar())
        print(f"✅ Audio CTA final generado con voz: {voz}")
        return filename
    except Exception as e:
        print(f"⚠️ Error generando audio CTA: {e}")
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
# PUBLICAR COMENTARIO FIJADO
# ================================================================
def publicar_comentario_fijado(video_id):
    try:
        creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
        youtube = build("youtube", "v3", credentials=creds)
        
        mensaje_comentario = f"""👻 ¿Te gustó este micro-relato?

🔴 SUSCRÍBETE para más historias de terror reales: {CANAL_LINK}
📱 Síguenos en Facebook: {FACEBOOK_LINK}

¿Qué harías tú en esta situación? Déjamelo en los comentarios 👇"""
        
        request = youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": mensaje_comentario
                        }
                    }
                }
            }
        )
        response = request.execute()
        comentario_id = response["id"]
        
        print(f"✅ Comentario publicado en el Short {video_id}")
        return comentario_id
    except Exception as e:
        print(f"⚠️ No se pudo publicar comentario: {e}")
        return None

# ================================================================
# SUBIR A YOUTUBE
# ================================================================
def subir_a_youtube(video_path, titulo, etiquetas, gancho_descripcion, contexto_descripcion, hashtags_descripcion):
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

🔴 Relatos completos en el canal. Visítanos: {CANAL_LINK}

👇 SUSCRÍBETE PARA MÁS RELATOS REALES 👇
{CANAL_LINK}

📱 Facebook: {FACEBOOK_LINK}

{hashtags_descripcion}"""

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
        
        time.sleep(3)
        publicar_comentario_fijado(video_id)
        
        return video_id
    except Exception as e:
        print(f"❌ Error subiendo a YouTube: {e}")
        sys.exit(1)

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
    print("🎬 Iniciando Bot de SHORTS (Micro-relatos virales +10% velocidad)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎤 Voz seleccionada para TODO el video: {CONFIG_VOZ_ACTUAL['voz']}")

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

    print("🆕 Generando nueva historia completa (micro-relato viral)...")
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

    print(f"📖 Procesando historia ({len(texto_completo.split())} palabras)...")
    print(f"🏷️ Título SEO ({len(historia_raw['titulo'])} chars): {historia_raw['titulo']}")
    print(f"🏷️ Tags: {historia_raw['tags']}")

    segmentos = dividir_en_segmentos(texto_completo, max_palabras_por_segmento=45)
    print(f"🖼️ Generando imágenes y audios para {len(segmentos)} segmentos...")

    recursos = generar_recursos_por_segmento(
        segmentos=segmentos,
        perfil=perfil,
        ubicacion=ubicacion,
        estilo=estilo,
        paleta=paleta,
        intentos_por_imagen=3
    )

    if not recursos:
        print("❌ Error generando recursos para los segmentos. Abortando.")
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

    print(f"🚀 Subiendo Short a YouTube...")
    subir_a_youtube(
        video_path=video_final,
        titulo=historia_raw["titulo"],
        etiquetas=historia_raw["tags"],
        gancho_descripcion=historia_raw["gancho_descripcion"],
        contexto_descripcion=historia_raw["contexto_descripcion"],
        hashtags_descripcion=historia_raw["hashtags_descripcion"]
    )

    guardar_titulo_publicado(historia_raw["titulo"])

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
