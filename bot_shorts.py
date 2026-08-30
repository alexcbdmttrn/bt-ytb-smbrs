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
import urllib3

# Silenciar advertencias de SSL (inofensivas)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================================================================
# CONFIGURACIÓN
# ================================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
YOUTUBE_USER_TOKEN = (
    json.loads(os.getenv("YOUTUBE_USER_TOKEN"))
    if os.getenv("YOUTUBE_USER_TOKEN")
    else {}
)
FACEBOOK_LINK = "https://www.facebook.com/profile.php?id=61593237382982"
CANAL_LINK = "https://www.youtube.com/@sombrasdemedianocheoficial"
ESTADO_FILE = "estado_shorts.json"
TITULOS_FILE = "titulos_shorts_publicados.json"
TEMAS_FILE = "temas_usados.json"
META_DIARIA_SHORTS = 3
MAX_TEMAS_HISTORIAL = 7
ACTIVAR_DISCLOSURE_IA = True
DISCLOSURE_TEXT = "\n🤖 Contenido generado con inteligencia artificial (relato e imágenes)."

# ================================================================
# 🚀 LISTA DE OUTLIERS
# ================================================================
OUTLIERS_TERROR = [
    "Intenté sobrevivir 7 días en el hotel más embrujado de México",
    "¿Qué vi en el espejo del manicomio abandonado?",
    "De creyente a escéptico en una noche en el panteón",
    "El ritual que hice y nunca debí hacer",
    "Sobreviví a la carretera fantasma de Chihuahua sin gasolina",
    "Intenté comunicarme con los muertos y esto pasó",
    "¿Lograré salir del sanatorio abandonado antes del amanecer?",
    "Pasé una noche en la casa de las brujas de Veracruz",
    "El pueblo fantasma me llamó por mi nombre y no debí responder",
    "Intenté grabar un fantasma y casi no lo cuento",
    "De escéptico a creyente en la carretera de Zacatecas",
    "Sobreviví al bosque donde nadie entra",
    "¿Qué se esconde en la mina abandonada de Hidalgo?",
    "El día que vi a mi doble en el espejo del hospital viejo",
    "Intenté hacer un pacto con el diablo y esto pasó",
    "Pasé la noche en el panteón más viejo de Guanajuato",
    "El susurro en mi habitación no era humano",
    "Intenté escapar del pueblo fantasma y casi lo logro",
    "¿Qué encontré en el sótano de la casa embrujada?",
    "De incrédulo a perseguido en la carretera de Sinaloa",
]

# ================================================================
# HISTORIAL DE TEMAS
# ================================================================
def cargar_temas_usados():
    try:
        with open(TEMAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"temas": []}

def guardar_tema_usado(tema):
    data = cargar_temas_usados()
    data["temas"].append(tema)
    if len(data["temas"]) > MAX_TEMAS_HISTORIAL:
        data["temas"] = data["temas"][-MAX_TEMAS_HISTORIAL:]
    with open(TEMAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def obtener_temas_recientes():
    data = cargar_temas_usados()
    return data["temas"]

# ================================================================
# ÉPOCA DEL SUCESO
# ================================================================
ANIO_SUCESO = None
EPOCA_MOD = "present day contemporary era (2020s), modern vehicles, modern architecture, modern clothing, smartphones era"

def construir_modificadores_epoca(anio):
    if anio is None or anio >= 2015:
        return "present day contemporary era (2020s), modern vehicles, modern architecture, modern clothing, LED lighting, smartphones era"
    elif anio >= 2000:
        return f"early 2000s era (year {anio}): 2000s cars, CRT televisions, old flip cellphones, 2000s fashion and architecture, no smartphones"
    elif anio >= 1990:
        return f"1990s era (year {anio}): 90s cars, cassette players, CRT TVs, analog phones, 90s fashion, older architecture, no smartphones, no modern tech"
    elif anio >= 1980:
        return f"1980s era (year {anio}): 80s cars, analog rotary phones, vintage clothing, older buildings, no modern technology"
    else:
        return f"past era (year {anio}): old classic cars, analog technology, period clothing, aged architecture, no modern devices"

def actualizar_epoca(anio):
    global ANIO_SUCESO, EPOCA_MOD
    try:
        ANIO_SUCESO = int(anio)
    except Exception:
        ANIO_SUCESO = None
    EPOCA_MOD = construir_modificadores_epoca(ANIO_SUCESO)
    print(f"📅 Época del suceso: {ANIO_SUCESO if ANIO_SUCESO else 'actualidad'}")

# ================================================================
# VOCES NEURALES
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural", "velocidad": "+10%", "tono": "-2Hz"},
    {"voz": "es-ES-AlvaroNeural", "velocidad": "+10%", "tono": "-3Hz"},
    {"voz": "es-MX-ManuelNeural", "velocidad": "+10%", "tono": "-1Hz"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+10%", "tono": "-2Hz"},
]
CONFIG_VOZ_ACTUAL = random.choice(VOCES_DISPONIBLES)

# ================================================================
# PALETAS Y ESTILOS
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
# GENERADOR DE PERSONAJES
# ================================================================
def generar_perfil_personaje_shorts():
    edades = ["21-year-old", "28-year-old", "35-year-old", "42-year-old", "50-year-old", "60-year-old"]
    vestimentas = [
        "wearing a denim jacket and t-shirt", "wearing a dark green coat and wool scarf",
        "wearing a simple white shirt and leather belt", "wearing a blue mechanic uniform",
        "wearing a dark sweater and trousers", "wearing a red flannel shirt and jeans",
        "wearing a black leather jacket and boots", "wearing a hoodie and baseball cap",
        "wearing a polo shirt and dark pants", "wearing a work uniform with reflective stripes",
    ]
    cabellos = [
        "short curly dark hair", "grey cropped hair", "bald with a short beard",
        "short spiky black hair", "chestnut brown curly hair", "short salt-and-pepper hair",
    ]
    rasgos = [
        "with mestizo features and light olive skin", "with light brown skin and freckles",
        "with olive skin and a strong jaw", "with pale skin and green eyes",
        "with tan skin and a warm smile",
    ]
    profesiones = [
        "trailero conduciendo un tráiler en autopista nocturna", "policía en su turno nocturno",
        "conductor de taxi en ciudad", "repartidor en moto", "velador en condominio residencial",
        "enfermero en hospital", "guardia de seguridad en centro comercial",
    ]
    profesion = random.choice(profesiones)
    perfil_fisico = (
        f"a {random.choice(edades)} Mexican man, {random.choice(rasgos)}, "
        f"with {random.choice(cabellos)}, {random.choice(vestimentas)}"
    )
    return perfil_fisico, profesion, "un", "man"

PERFIL_PERSONAJE_SHORTS, PERSONAJE_SHORTS, ARTICULO_SHORTS, GENERO_SHORTS = generar_perfil_personaje_shorts()

ESTADO_HISTORIA_SHORTS = random.choice([
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas",
    "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit",
    "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
    "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"
])

# ================================================================
# AUDIO DE FONDO
# ================================================================
FONDOS_DISPONIBLES = [
    "Ash and Marrow.mp3", "Black Maw.mp3", "Cold Hollow.mp3",
    "Hollow Marrow.mp3", "Sunken Dread.mp3", "Sunless Vault.mp3", "The Deep Rot.mp3"
]

def seleccionar_fondo_disponible(estado):
    encontrados = {}
    for root, dirs, files in os.walk("."):
        if "/." in root or "\\." in root:
            continue
        for file in files:
            for fondo in FONDOS_DISPONIBLES:
                if file.lower() == fondo.lower():
                    encontrados[fondo] = os.path.join(root, file)
    
    if not encontrados:
        print("⚠️ No se encontraron archivos de música de fondo en el repositorio.")
        return None
    
    ultimo_fondo = estado.get("ultimo_fondo")
    candidatos = [f for f in encontrados if f != ultimo_fondo] or list(encontrados.keys())
    seleccionado = random.choice(candidatos)
    estado["ultimo_fondo"] = seleccionado
    print(f"🎵 Música de fondo seleccionada: {seleccionado} (de {len(candidatos)} candidatas disponibles)")
    return encontrados[seleccionado]

# ================================================================
# LIMPIADORES
# ================================================================
def limpiar_prompt_base(prompt, estilo_visual=None, paleta_color=None):
    estilo = estilo_visual or ESTILO_VISUAL_ACTUAL
    paleta = paleta_color or PALETA_COLOR_ACTUAL
    if not prompt:
        prompt = "Night scene, dramatic lighting"
    prompt = re.sub(r"\n+", " ", prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r"[^\x00-\x7F]+", "", prompt)
    palabras_malas = [r"\bgore\b", r"\bblood\b", r"\bzombies?\b", r"\bdisfigured\b", r"\bmonster\b"]
    for pattern in palabras_malas:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)
    prompt_base = re.sub(r"\s+", " ", prompt).strip()[:220]
    modificadores = (
        f", {estilo}, color palette of {paleta}, "
        "vertical 9:16 format, WIDE environmental establishing shot, "
        "the ENVIRONMENT, objects and location are the main focal point (cars, trees, houses, streets, buildings), "
        "if a person appears they occupy AT MOST 20% of the frame, small and at distance, "
        "EXACTLY ONE single person, NO clones, NO duplicates, NO twins, NO double faces, "
        f"{EPOCA_MOD}, period-accurate vehicles, architecture, clothing and technology, "
        "sharp focus, natural lighting, no text, no watermark"
    )
    return prompt_base + modificadores

def limpiar_caracteres_para_tts(texto):
    texto = re.sub(r'[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9\s.,;:!?¿¡\'\"]', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()

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

def limpiar_texto_para_audio(texto):
    texto = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002700-\U000027BF\U000024C2-\U0001F251]', '', texto)
    texto = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', texto)
    return re.sub(r'\s+', ' ', texto.replace('"', "'")).strip()

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
# EXPANDIR / TRUNCAR TEXTO
# ================================================================
def expandir_texto_corto(texto_corto, ubicacion, personaje):
    prompt = f"""Expande el siguiente relato a 150-170 palabras con detalles sensoriales de {ubicacion}.
IMPORTANTE: Asegúrate de que el relato tenga un OBJETIVO CLARO, una RESTRICCIÓN y que el protagonista ACTÚE.
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
# GENERAR HISTORIA CON OUTLIERS
# ================================================================
def generar_historia_completa():
    titulos_pub = cargar_titulos_publicados()["titulos"][-10:]
    titulos_referencia = "\n".join([f"- {t}" for t in titulos_pub]) if titulos_pub else "Ninguno aún."

    temas_recientes = obtener_temas_recientes()
    temas_bloqueo = ""
    if temas_recientes:
        temas_bloqueo = "\n🚫 TEMAS YA PUBLICADOS RECIENTEMENTE:\n"
        for t in temas_recientes[-5:]:
            temas_bloqueo += f"- {t.get('tipo', 'historia')} en {t.get('lugar', 'lugar desconocido')} (contexto: {t.get('contexto', '')})\n"
        temas_bloqueo += "\nAsegúrate de que tu historia NO tenga el mismo tipo de fenómeno ni el mismo lugar.\n"

    outliers_referencia = random.sample(OUTLIERS_TERROR, min(3, len(OUTLIERS_TERROR)))
    outliers_texto = "\n".join([f"  • {t}" for t in outliers_referencia])

    prompt = f"""Eres un CURADOR DE RELATOS PARANORMALES REALES de internet, especializado en SEO para YouTube Shorts.

🚀 REFERENCIAS DE OUTLIERS (temas que ya funcionaron):
{outliers_texto}

Inspírate en la estructura, pero NO copies. Crea tu propia variación.

🚨 REGLA DE ORO:
La historia DEBE estar basada en un relato REAL que alguien contó en internet.
Adáptalo en primera persona, tono coloquial, ambientado en {ESTADO_HISTORIA_SHORTS}, México.

🎯 LONGITUD: 150-170 palabras exactas.

PROTAGONISTA: {ARTICULO_SHORTS} {PERSONAJE_SHORTS}.

📐 ESTRUCTURA CON CONFLICTO ACTIVO:
1. OBJETIVO CLARO del protagonista.
2. RESTRICCIÓN o limitación.
3. ACCIÓN del protagonista.
4. RESOLUCIÓN.

🎯 TÍTULO CON ESTRATEGIA DE OUTLIER (55-75 caracteres):
Fórmulas:
- RESTRICCIÓN: "Intenté [acción] sin [recurso] en [lugar]"
- DESAFÍO: "¿[Acción imposible] en [lugar]?"
- TRANSFORMACIÓN: "De [estado inicial] a [estado final] en [lugar]"

❌ PROHIBIDOS: "La leyenda de...", "El fantasma de...", "El misterio de..."

🎯 PALABRAS DE PORTADA (máx 2 palabras)
🎯 DESCRIPCIÓN SEO
🎯 TAGS (10-15)
🎯 AÑO DEL SUCESO

🚫 TÍTULOS YA PUBLICADOS:
{titulos_referencia}

{temas_bloqueo}

Devuelve ESTRICTAMENTE este JSON:
{{
    "titulo": "Título con estructura de outlier (55-75 caracteres)",
    "titulo_alternativo": "Segundo título",
    "anio_suceso": 1998,
    "palabras_clave": ["keyword1", "keyword2", "keyword3"],
    "gancho_descripcion": "Gancho máx 90 caracteres",
    "contexto_descripcion": "1 oración con contexto",
    "fuente_relato": "Basado en un testimonio real...",
    "texto_completo": "Micro-relato REAL, 150-170 palabras",
    "palabras_portada": "TEXTO GANCHO máximo 2 palabras",
    "tags": "10-15 tags separados por coma",
    "tema": {{
        "tipo": "fantasma",
        "lugar": "carretera",
        "contexto": "persecucion"
    }}
}}"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.75,
        "max_tokens": 1100,
        "response_format": {"type": "json_object"}
    }

    for intento in range(6):
        try:
            print(f"🔄 Intento {intento+1}/6 generando historia...")
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

            anio_suceso = data.get("anio_suceso", None)
            actualizar_epoca(anio_suceso)

            titulo = data.get("titulo", "").strip()
            titulo = re.sub(r'#\w+', '', titulo).strip()
            titulo = ' '.join(titulo.split())

            palabras_outlier = ["intenté", "¿", "sobreviví", "lograré", "pasé", "escapar", "sin", "de ", " a "]
            tiene_estructura = any(p in titulo.lower() for p in palabras_outlier)
            if not tiene_estructura and len(titulo) > 10:
                keywords = data.get("palabras_clave", [])
                primera_kw = keywords[0] if keywords else "terror"
                lugar = ESTADO_HISTORIA_SHORTS
                titulo = f"Intenté sobrevivir en {lugar} sin {primera_kw}"

            if len(titulo) < 40:
                titulo = f"{titulo} - Testimonio real en {ESTADO_HISTORIA_SHORTS}"
            if len(titulo) > 95:
                titulo = titulo[:92].rsplit(' ', 1)[0] + "..."
            data["titulo"] = titulo

            if titulo_ya_publicado(titulo):
                print(f"   ⚠️ Título YA PUBLICADO. Regenerando...")
                raise ValueError("Título duplicado")

            gancho = data.get("gancho_descripcion", "").strip()
            if not gancho or len(gancho) > 110:
                gancho = f"Sin recursos, en {ESTADO_HISTORIA_SHORTS}..."[:100]
            data["gancho_descripcion"] = gancho

            contexto = data.get("contexto_descripcion", "").strip()
            if not contexto:
                contexto = f"Un testimonio real de fenómenos paranormales en {ESTADO_HISTORIA_SHORTS}, México."
            data["contexto_descripcion"] = contexto

            fuente = data.get("fuente_relato", "").strip()
            if not fuente:
                fuente = "Basado en un testimonio real compartido en internet."
            data["fuente_relato"] = fuente

            tags_raw = data.get("tags", "")
            tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()][:12]

            keywords = data.get("palabras_clave", [])
            if keywords:
                for kw in keywords:
                    if kw.lower() not in [t.lower() for t in tags_list]:
                        tags_list.append(kw)

            extras = [
                f"terror en {ESTADO_HISTORIA_SHORTS.lower()}",
                "testimonios paranormales reales", "historias reales en primera persona",
                "leyendas urbanas mexicanas reales", "casos paranormales reales mexico",
                "desafio paranormal", "restriccion terror"
            ]
            for ext in extras:
                if ext not in tags_list and len(tags_list) < 15:
                    tags_list.append(ext)

            tags_final = []
            total_chars = 0
            for t in tags_list:
                costo = len(t) + 2
                if total_chars + costo > 480:
                    break
                tags_final.append(t)
                total_chars += costo
            data["tags"] = ", ".join(tags_final)

            hashtag_base = "#Shorts"
            hashtag_lugar = f"#{ESTADO_HISTORIA_SHORTS.replace(' ', '')}"
            hashtag_keywords = []
            if keywords:
                for kw in keywords[:2]:
                    kw_clean = re.sub(r'[áéíóú]', lambda m: {'á':'a','é':'e','í':'i','ó':'o','ú':'u'}.get(m.group(), m.group()), kw)
                    kw_clean = re.sub(r'[^a-zA-Z0-9]', '', kw_clean)
                    if kw_clean and len(kw_clean) > 2:
                        hashtag_keywords.append(f"#{kw_clean.capitalize()}")
            hashtag_extra = random.choice([
                "#RelatosReales", "#Paranormal", "#MiedoReal",
                "#LeyendasUrbanas", "#CasosReales", "#TerrorMexicano"
            ])
            if "intenté" in titulo.lower() or "sin" in titulo.lower():
                hashtag_estrategia = "#RestriccionTerror"
            elif "?" in titulo or "¿" in titulo:
                hashtag_estrategia = "#DesafioParanormal"
            else:
                hashtag_estrategia = "#Outlier"
            
            hashtag_final = f"{hashtag_base} {hashtag_lugar} {' '.join(hashtag_keywords[:2])} {hashtag_extra} {hashtag_estrategia}"
            data["hashtags_descripcion"] = hashtag_final

            print(f"   🏷️ Título SEO: {data['titulo']} ({len(data['titulo'])} chars)")
            print(f"   📅 Año del suceso: {data.get('anio_suceso', 'actualidad')}")
            print(f"   🔑 Keywords: {keywords}")
            print(f"   🧩 Estrategia: {hashtag_estrategia}")
            if "tema" in data:
                print(f"   🧩 Tema: {data['tema']}")
            return data

        except Exception as e:
            print(f"❌ Intento {intento+1}/6 falló: {e}")
            if intento < 5:
                time.sleep(10 + intento * 5)

    print("❌ TODOS LOS INTENTOS FALLARON.")
    sys.exit(1)

def titulo_ya_publicado(titulo):
    data = cargar_titulos_publicados()
    titulo_norm = titulo.lower().strip()
    for t in data["titulos"]:
        if titulo_norm == t.lower().strip():
            return True
    return False

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
        json.dump({"ultimo_fondo": estado.get("ultimo_fondo"), "publicaciones_hoy": estado.get("publicaciones_hoy")}, f, indent=2)

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
            json.dump(data, f, indent=2)

def obtener_publicaciones_hoy():
    estado = cargar_estado()
    pub = estado.get("publicaciones_hoy")
    if not pub:
        return 0
    hoy = datetime.now(pytz.timezone("America/Mexico_City")).strftime("%Y-%m-%d")
    return pub.get("cantidad", 0) if pub.get("fecha") == hoy else 0

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
# GENERAR QUERY PEXELS
# ================================================================
def generar_query_pexels_shorts(segmento_texto, etapa, ubicacion_escena, index_segmento=0, total_segmentos=1):
    prompt = f"""Genera SOLO 4-6 palabras clave en inglés para buscar una foto VERTICAL en Pexels.
Contexto: {etapa} en {ubicacion_escena}.
Fragmento: "{segmento_texto[:100]}"
Ejemplos: "dark forest night fog", "empty house interior night".
Devuelve SOLO las palabras clave, sin comas, sin puntos."""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 30,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        query = r.json()["choices"][0]["message"]["content"].strip()
        query = re.sub(r'["\',\.]', '', query)
        query = " ".join(query.split())
        if len(query) < 5:
            query = "dark night landscape"
        print(f"🧠 Query Pexels: '{query}'")
        return query
    except Exception as e:
        print(f"⚠️ Error generando query: {e}")
        return "dark night landscape"

# ================================================================
# BUSCAR IMAGEN EN PEXELS (con reintentos y fallback)
# ================================================================
ULTIMA_URL_PEXELS = None

def buscar_imagen_pexels_shorts(query, intentos=3):
    global ULTIMA_URL_PEXELS
    if not PEXELS_API_KEY:
        print("⚠️ PEXELS_API_KEY no configurada. Usando placeholder.")
        return None

    variantes = ["angle", "view", "perspective", "mood", "atmosphere"]
    variacion = random.choice(variantes)
    query_variada = f"{query} {variacion}"

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": f"Bearer {PEXELS_API_KEY}"}
    params = {
        "query": query_variada,
        "orientation": "portrait",
        "per_page": 10,
        "page": random.randint(1, 8)
    }

    for intento in range(intentos):
        try:
            print(f"🔍 Intento {intento+1}/{intentos} buscando en Pexels: '{query_variada}'...")
            r = requests.get(url, headers=headers, params=params, timeout=25)
            if r.status_code == 200:
                data = r.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    fotos = data["photos"][:min(5, len(data["photos"]))]
                    foto = random.choice(fotos)
                    image_url = foto["src"]["large2x"] or foto["src"]["large"] or foto["src"]["original"]
                    if ULTIMA_URL_PEXELS and image_url == ULTIMA_URL_PEXELS:
                        print("   ⚠️ URL repetida, buscando otra página...")
                        params["page"] = (params["page"] % 8) + 1
                        continue
                    ULTIMA_URL_PEXELS = image_url
                    print(f"✅ Imagen encontrada: {image_url[:80]}...")
                    return image_url
                else:
                    print("⚠️ No se encontraron fotos.")
            else:
                print(f"⚠️ Error Pexels: {r.status_code} - {r.text[:100]}")
                if r.status_code == 401:
                    print("❌ API key inválida. Verifica tu PEXELS_API_KEY.")
                    break
        except requests.exceptions.Timeout:
            print("⏰ Timeout en Pexels. Reintentando...")
        except Exception as e:
            print(f"⚠️ Error conexión Pexels: {e}")
        if intento < intentos - 1:
            print(f"   ⏳ Esperando 5s...")
            time.sleep(5)
    
    print("❌ No se pudo obtener imagen de Pexels.")
    return None

# ================================================================
# DIVIDIR TEXTO
# ================================================================
def dividir_en_segmentos(texto, max_palabras_por_segmento=45):
    oraciones = re.split(r'(?<=[.!?¿¡])\s+', texto)
    oraciones = [o.strip() for o in oraciones if o.strip()]
    if not oraciones:
        return [texto]
    segmentos = []
    seg_actual = []
    palabras_actuales = 0
    for oracion in oraciones:
        palabras_oracion = len(oracion.split())
        if palabras_actuales + palabras_oracion > max_palabras_por_segmento and seg_actual:
            segmentos.append(" ".join(seg_actual))
            seg_actual = [oracion]
            palabras_actuales = palabras_oracion
        else:
            seg_actual.append(oracion)
            palabras_actuales += palabras_oracion
    if seg_actual:
        segmentos.append(" ".join(seg_actual))
    return segmentos

# ================================================================
# ASIGNAR ETAPAS VISUALES
# ================================================================
def asignar_etapas_visuales(segmentos, ubicacion):
    n = len(segmentos)
    etapas, ubicaciones = [], []
    for i in range(n):
        progreso = i / max(n - 1, 1)
        if progreso < 0.2:
            etapa, ubic = "inicio_casa", f"interior del hogar en {ubicacion}"
        elif progreso < 0.4:
            etapa, ubic = "desplazamiento", f"calle o vehículo en movimiento, {ubicacion}"
        elif progreso < 0.65:
            etapa, ubic = "lugar_destino", f"lugar específico del suceso en {ubicacion}"
        elif progreso < 0.85:
            etapa, ubic = "climax_evento", f"mismo lugar del suceso en {ubicacion}, momento del evento"
        else:
            etapa, ubic = "resolucion", f"salida o regreso desde el lugar, {ubicacion}"
        etapas.append(etapa)
        ubicaciones.append(ubic)
    return etapas, ubicaciones

# ================================================================
# GENERAR AUDIO
# ================================================================
def generar_audio(texto, index):
    global CONFIG_VOZ_ACTUAL
    texto_limpio = limpiar_caracteres_para_tts(limpiar_texto_para_audio(texto))
    if not texto_limpio:
        return None
    filename = f"audio_short_{index}.mp3"
    async def _generar(v, r, p):
        communicate = edge_tts.Communicate(texto_limpio, v, rate=r, pitch=p)
        await communicate.save(filename)
    for voz_config in [CONFIG_VOZ_ACTUAL] + VOCES_DISPONIBLES:
        try:
            asyncio.run(_generar(voz_config["voz"], voz_config["velocidad"], voz_config["tono"]))
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return filename
        except Exception:
            pass
    return None

def generar_audio_cta_final():
    filename = "audio_cta_final.mp3"
    async def _generar(v, r, p):
        communicate = edge_tts.Communicate("Relatos completos en el canal. Visítanos.", v, rate=r, pitch=p)
        await communicate.save(filename)
    for voz_config in VOCES_DISPONIBLES:
        try:
            asyncio.run(_generar(voz_config["voz"], voz_config["velocidad"], voz_config["tono"]))
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                return filename
        except Exception:
            pass
    return None

# ================================================================
# GENERAR RECURSOS POR SEGMENTO
# ================================================================
def generar_recursos_por_segmento(segmentos, etapas, ubicaciones, perfil, ubicacion, estilo, paleta, intentos_por_imagen=3):
    resultados = []
    total_seg = len(segmentos)
    imagen_anterior = None
    
    for idx, seg in enumerate(segmentos):
        etapa = etapas[idx] if idx < len(etapas) else "lugar_destino"
        ubic_escena = ubicaciones[idx] if idx < len(ubicaciones) else ubicacion
        print(f"  🎬 Segmento {idx+1}/{total_seg} ({len(seg.split())} palabras) - Etapa: {etapa}")
        print(f"     📍 Ubicación: {ubic_escena}")

        query = generar_query_pexels_shorts(seg, etapa, ubic_escena, idx, total_seg)
        print(f"    🔍 Query Pexels: {query}")

        img_url = buscar_imagen_pexels_shorts(query, intentos=intentos_por_imagen)
        
        if not img_url:
            # Intentar con una consulta más genérica
            query_fallback = "mexican night landscape dark"
            print(f"    🔄 Intentando con fallback: {query_fallback}")
            img_url = buscar_imagen_pexels_shorts(query_fallback, intentos=2)
            
        if not img_url and imagen_anterior:
            img_url = imagen_anterior
            print(f"    🔄 Usando imagen del segmento anterior ({idx})")
        elif not img_url:
            placeholder = generar_placeholder_local("Terror", (1080, 1920))
            img_url = placeholder if placeholder else "https://via.placeholder.com/1080x1920/1a1a1a/ff0000?text=Terror"
            print(f"    🔄 Usando placeholder genérico")

        if img_url:
            imagen_anterior = img_url

        audio_path = generar_audio(seg, f"seg_{idx}")
        if not audio_path:
            print(f"    ❌ Falló audio para segmento {idx+1}. Abortando...")
            return None

        try:
            duracion = AudioFileClip(audio_path).duration
        except:
            duracion = 10.0

        resultados.append({
            "imagen_url": img_url,
            "audio_path": audio_path,
            "duracion": duracion
        })

        if idx < len(segmentos) - 1:
            print(f"    ⏳ Esperando 5s antes del siguiente segmento...")
            time.sleep(5)

    return resultados

# ================================================================
# MONTAR VIDEO
# ================================================================
def montar_video_shorts(recursos, fondo_path, salida="short_final.mp4"):
    if not recursos:
        raise ValueError("No hay recursos para montar el video")

    clips_video, clips_audio = [], []
    for i, recurso in enumerate(recursos):
        try:
            audio_clip = AudioFileClip(recurso["audio_path"])
            clips_audio.append(audio_clip)
        except Exception as e:
            print(f"⚠️ Error cargando audio {i}: {e}")
            continue

        try:
            if recurso["imagen_url"].startswith("http"):
                r = requests.get(recurso["imagen_url"], timeout=30)
                if r.status_code == 200:
                    img_path = f"temp_short_{i}.jpg"
                    with open(img_path, "wb") as f:
                        f.write(r.content)
                else:
                    raise Exception("No se pudo descargar imagen")
            else:
                img_path = recurso["imagen_url"]

            with Image.open(img_path) as img:
                img_fitted = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
                img_fitted.save(img_path)

            duracion = recurso["duracion"]
            video_clip = ImageClip(img_path).set_duration(duracion)
            clips_video.append(video_clip)
        except Exception as e:
            print(f"⚠️ Error procesando imagen {i}: {e}")
            placeholder = generar_placeholder_local(f"Img {i+1}")
            if placeholder:
                with Image.open(placeholder) as img:
                    ImageOps.fit(img, (1080, 1920), Image.LANCZOS).save(placeholder)
                video_clip = ImageClip(placeholder).set_duration(recurso["duracion"])
                clips_video.append(video_clip)

    if not clips_video:
        raise ValueError("No se pudieron crear clips de video")

    PAUSA = 0.3
    if len(clips_audio) > 1:
        audio_con_pausas = []
        for i, audio in enumerate(clips_audio):
            audio_con_pausas.append(audio)
            if i < len(clips_audio) - 1:
                audio_con_pausas.append(AudioClip(lambda t: 0, duration=PAUSA))
        audio_narracion = concatenate_audioclips(audio_con_pausas)
    else:
        audio_narracion = clips_audio[0]

    video = concatenate_videoclips(clips_video, method="compose")

    cta_audio_path = generar_audio_cta_final()
    if cta_audio_path and os.path.exists(cta_audio_path):
        try:
            cta_clip = AudioFileClip(cta_audio_path)
            silencio = AudioClip(lambda t: 0, duration=0.5)
            audio_narracion = concatenate_audioclips([audio_narracion, silencio, cta_clip])
            duracion_cta = cta_clip.duration + 0.5
            ultimo_clip = clips_video[-1].set_duration(clips_video[-1].duration + duracion_cta)
            clips_video[-1] = ultimo_clip
            video = concatenate_videoclips(clips_video, method="compose")
            print(f"✅ CTA final agregado ({duracion_cta:.1f}s adicionales)")
        except Exception as e:
            print(f"⚠️ Error CTA final: {e}")

    duracion_total = audio_narracion.duration

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

    print(f"✅ Short vertical creado: {salida}")
    return salida

# ================================================================
# SUBIR A YOUTUBE
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
# SUBIR VIDEO A HOST TEMPORAL (para Facebook)
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
                    return r.text.strip()
        except Exception:
            pass
        time.sleep(3)
    return None

# ================================================================
# ENVIAR A MAKE
# ================================================================
def enviar_a_make(titulo, descripcion, video_url, url_youtube=""):
    webhook_url = os.getenv("MAKE_WEBHOOK_URL_REELS")
    if not webhook_url:
        return False
    payload = {"titulo": titulo, "descripcion": descripcion, "video_url": video_url, "url_youtube": url_youtube}
    try:
        r = requests.post(webhook_url, json=payload, timeout=60)
        return r.status_code == 200
    except Exception:
        return False

# ================================================================
# LIMPIEZA
# ================================================================
def limpiar_temporales_shorts():
    for f in os.listdir("."):
        if (f.startswith("temp_short_") or f.startswith("audio_short_") or f.startswith("placeholder_")) and (f.endswith(".jpg") or f.endswith(".mp3")):
            try:
                os.remove(f)
            except:
                pass
    if os.path.exists("short_final.mp4"):
        try:
            os.remove("short_final.mp4")
        except:
            pass

# ================================================================
# MAIN
# ================================================================
def main():
    print("🎬 Iniciando Bot de SHORTS (Pexels + Estrategia de Outlier)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎤 Voz inicial: {CONFIG_VOZ_ACTUAL['voz']}")

    if not YOUTUBE_USER_TOKEN:
        print("❌ No se encontró YOUTUBE_USER_TOKEN.")
        sys.exit(1)

    if not PEXELS_API_KEY:
        print("⚠️ PEXELS_API_KEY no configurada. Se usarán placeholders.")

    if obtener_publicaciones_hoy() >= META_DIARIA_SHORTS:
        print(f"✅ Meta de {META_DIARIA_SHORTS} shorts alcanzada.")
        sys.exit(0)

    estado = cargar_estado()
    fondo_path = seleccionar_fondo_disponible(estado)

    historia_raw = generar_historia_completa()
    if not historia_raw:
        print("❌ No se pudo generar la historia.")
        sys.exit(1)

    texto_completo = historia_raw.get("texto_completo", "")
    palabras = len(texto_completo.split())
    if palabras < 130:
        texto_completo = expandir_texto_corto(texto_completo, ESTADO_HISTORIA_SHORTS, PERSONAJE_SHORTS)
    elif palabras > 190:
        texto_completo = truncar_texto_largo(texto_completo)

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
    print(f"   🧩 Hashtags: {historia_raw['hashtags_descripcion']}")
    if "tema" in historia_raw:
        print(f"   🧩 Tema: {historia_raw['tema']}")
    print(f"\n   📖 Procesando historia ({len(texto_completo.split())} palabras)...")

    segmentos = dividir_en_segmentos(texto_completo)
    etapas, ubicaciones = asignar_etapas_visuales(segmentos, ubicacion)

    print(f"\n🖼️ Buscando {len(segmentos)} imágenes verticales en Pexels...")
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
        print("❌ Error generando recursos.")
        sys.exit(1)

    try:
        video_final = montar_video_shorts(recursos, fondo_path)
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

    if "tema" in historia_raw:
        guardar_tema_usado(historia_raw["tema"])
        print(f"✅ Tema guardado: {historia_raw['tema']}")

    publicaciones_antes = obtener_publicaciones_hoy()
    if publicaciones_antes < 2:
        print(f"\n📘 Reel #{publicaciones_antes + 1}: enviando a Facebook...")
        video_url_temporal = subir_video_temporal(video_final)
        if video_url_temporal:
            descripcion_facebook = f"""{historia_raw['gancho_descripcion']}
{historia_raw['contexto_descripcion']}
🔴 RELATO COMPLETO en el canal: {CANAL_LINK}
📖 {historia_raw.get('fuente_relato', 'Basado en un testimonio real.')}
📱 Síguenos: {FACEBOOK_LINK}
{historia_raw['hashtags_descripcion']}"""
            enviar_a_make(
                titulo=historia_raw["titulo"],
                descripcion=descripcion_facebook,
                video_url=video_url_temporal,
                url_youtube=f"https://youtu.be/{video_id_youtube}"
            )
        else:
            print("⚠️ No se pudo subir al host temporal.")

    incrementar_publicaciones_hoy()
    guardar_estado(estado)
    limpiar_temporales_shorts()
    print("✨ Ejecución completada.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
