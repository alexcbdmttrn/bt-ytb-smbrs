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
from PIL import Image, ImageOps
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

MUSICA_ESTADO_FILE = "estado_musica.json"
TITULOS_LARGOS_FILE = "titulos_largos_publicados.json"

DURACION_MINIMA_SEGUNDOS = 480
MAX_INTENTOS_EXPANSION = 2

# ================================================================
# 🗓️ ÉPOCA DEL SUCESO (Dinámica según el relato)
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
        # Si la IA no da año, inventamos uno al azar entre 1975 y 2005 para tono de leyenda
        ANIO_SUCESO = random.choice([1975, 1982, 1988, 1993, 1998, 2004])
    EPOCA_MOD = construir_modificadores_epoca(ANIO_SUCESO)
    print(f"🗓️ Época del suceso configurada: {ANIO_SUCESO}")

# ================================================================
# 🎤 VOCES NEURALES VÁLIDAS
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural", "velocidad": "+12%", "tono": "-2Hz"},
    {"voz": "es-MX-DaliaNeural", "velocidad": "+12%", "tono": "+0Hz"},
    {"voz": "es-ES-AlvaroNeural", "velocidad": "+12%", "tono": "-3Hz"},
    {"voz": "es-ES-ElviraNeural", "velocidad": "+12%", "tono": "+1Hz"},
    {"voz": "es-CO-GonzaloNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-CO-SalomeNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-AR-ElenaNeural", "velocidad": "+12%", "tono": "+2Hz"},
    {"voz": "es-AR-DiegoNeural", "velocidad": "+12%", "tono": "-2Hz"},
    {"voz": "es-US-AlonsoNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-US-PalomaNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-PE-CamilaNeural", "velocidad": "+12%", "tono": "+0Hz"},
    {"voz": "es-PE-AlexNeural", "velocidad": "+12%", "tono": "-1Hz"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+12%", "tono": "-2Hz"},
    {"voz": "es-CL-CatalinaNeural", "velocidad": "+12%", "tono": "+1Hz"},
]
CONFIG_VOZ_ACTUAL = random.choice(VOCES_DISPONIBLES)

# ================================================================
# 🎨 PALETAS DE COLOR (Adaptadas a cualquier época)
# ================================================================
PALETAS_COLOR = [
    "Cold cyan blue fog, navy blue shadows, crisp white moonlight",
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
    "Documentary realistic photo, natural skin texture, authentic",
    "8k resolution cinematic frame, ultra clear details",
    "Noir style, high contrast, moody urban atmosphere",
    "Analog film photograph, grain of the period, authentic era look",
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
# 🧑 GENERADOR DE PERSONAJES (Sin forzar "moderno")
# ================================================================
def generar_perfil_personaje():
    edades = ["21-year-old", "28-year-old", "35-year-old", "42-year-old", "50-year-old", "60-year-old"]
    generos = ["man", "woman"]
    vestimentas = [
        "wearing a denim jacket and grey t-shirt",
        "wearing a dark green coat and wool scarf",
        "wearing a simple white shirt and leather belt",
        "wearing a blue mechanic uniform",
        "wearing a dark sweater and trousers",
        "wearing a red flannel shirt and jeans",
        "wearing a black leather jacket and boots",
        "wearing a traditional embroidered blouse and long skirt",
        "wearing a white guayabera shirt and dark pants",
        "wearing a hoodie and baseball cap",
        "wearing a polo shirt and dark pants",
        "wearing a work uniform",
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
# 🆕 GESTIÓN DE TÍTULOS PUBLICADOS
# ================================================================
def cargar_titulos_largos():
    try:
        with open(TITULOS_LARGOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"titulos": []}

def guardar_titulo_largo(titulo):
    data = cargar_titulos_largos()
    if titulo not in data["titulos"]:
        data["titulos"].append(titulo)
        with open(TITULOS_LARGOS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Título largo guardado en registro: '{titulo}'")

def titulo_largo_ya_publicado(titulo):
    data = cargar_titulos_largos()
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
# 🧼 LIMPIADOR DE PROMPTS (Enfoque en Entorno + Anti-Clones + Época)
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        prompt = "Night scene, dramatic lighting"
    prompt = re.sub(r"\n+", " ", prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r"[^\x00-\x7F]+", "", prompt)

    # Solo limpiamos defectos visuales y gore. NO tocamos palabras de época.
    palabras_malas = [
        r"\bgore\b", r"\bblood\b", r"\bbloody\b", r"\bwounds?\b", r"\bzombies?\b",
        r"\bdisfigured\b", r"\bmonster\b", r"\bdemacrad[oa]s?\b",
    ]
    for pattern in palabras_malas:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)

    prompt_base = re.sub(r"\s+", " ", prompt).strip()[:220]

    modificadores_calidad = (
        f", {ESTILO_VISUAL_ACTUAL}, color palette of {PALETA_COLOR_ACTUAL}, "
        "VERTICAL 9:16 portrait format, WIDE environmental establishing shot, "
        "the ENVIRONMENT, objects and location are the main focal point (cars, trees, houses, streets, buildings, forests), "
        "if a person appears they occupy AT MOST 20% of the frame, small and at distance, "
        "EXACTLY ONE single person, NO clones, NO duplicates, NO twins, NO double faces, NO mirror faces, "
        f"{EPOCA_MOD}, period-accurate vehicles, architecture, clothing and technology, "
        "sharp focus, natural lighting, no text, no watermark"
    )
    return prompt_base + modificadores_calidad

# ================================================================
# LIMPIAR RESPUESTA JSON
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
        return json_str
    return respuesta

# ================================================================
# 🎬 GENERAR HISTORIA (TEXTO CONTINUO + AÑO DE SUCESO)
# ================================================================
def generar_historia_completa():
    titulos_pub = cargar_titulos_largos()["titulos"][-20:]
    titulos_referencia = "\n".join([f"- {t}" for t in titulos_pub]) if titulos_pub else "Ninguno aún."

    prompt_base = f"""Eres un GUIONISTA, DIRECTOR DE CINE DE MISTERIO y EXPERTO EN SEO + MINIATURAS PARA YOUTUBE.

🚫 TÍTULOS YA PUBLICADOS (NO REPETIR NI PARECERSE):
{titulos_referencia}

Escribe un RELATO PARANORMAL COMPLETO en primera persona, en español, de 1.400-1.600 palabras, ambientado en {UBICACION_HISTORIA}, México.
Escríbelo como TEXTO CONTINUO en párrafos (NO lo dividas en segmentos ni listas).

PERSONAJE PRINCIPAL (FIJO):
"{PERFIL_PERSONAJE}"

🎯 REGLA CRÍTICA 1: TÍTULO SEO DE ALTO CTR
FÓRMULA: [VERBO EN 1RA PERSONA] + [LUGAR ESPECÍFICO] + [GANCHO EMOCIONAL]
Longitud: 50-65 caracteres, primera persona, lugar específico de {UBICACION_HISTORIA}.

🎯 REGLA CRÍTICA 2: MINIATURA DE ALTO CTR (HORIZONTAL 16:9)
"palabras_portada": TEXTO GANCHO de 2-3 palabras emocionales ESPECÍFICO del relato.
"miniatura_prompt": PROMPT EN INGLÉS para miniatura HORIZONTAL 16:9 de terror de alto CTR:
- Extreme close-up de un rostro mexicano aterrorizado con ojos muy abiertos
- Detrás, una silueta fantasmal oscura con ojos brillantes
- Ambientado en {UBICACION_HISTORIA}, alto contraste rojo/negro
- Deja un área oscura limpia en el LADO DERECHO para texto

🎯 REGLA CRÍTICA 3: DESCRIPCIÓN CON SEO EXPERTO
Línea 1 (GANCHO, 150 chars): frase impactante con keyword + lugar
Línea 2-3 (CONTEXTO): keywords long-tail naturales
Línea 4 (CTA): "🔴 SUSCRÍBETE: {CANAL_LINK}"
Línea 5 (CAPÍTULOS): 4-6 timestamps "00:00 - Título"
Línea 6 (CRÉDITOS): "📱 Facebook: {FACEBOOK_LINK}"
Línea 7 (HASHTAGS): máx 5

🎯 REGLA CRÍTICA 4: TAGS SEO (15-20, máx 500 chars)
🎯 REGLA CRÍTICA 5: PALABRAS CLAVE (2-3)
🎯 REGLA CRÍTICA 6: TÍTULO ALTERNATIVO (A/B testing)

🎬 ESTRUCTURA DEL RELATO (texto_completo):
1. GANCHO inicial impactante
2. CONTEXTO: quién, dónde, cuándo
3. DESARROLLO con detalles sensoriales
4. CLÍMAX paranormal
5. DESENLACE
- Tono natural y coloquial, primera persona.

Devuelve ESTRICTAMENTE este JSON válido:
{{
  "titulo": "Título SEO 1ra persona, 50-65 caracteres",
  "titulo_alternativo": "Segundo título con ángulo diferente",
  "anio_suceso": 1995,
  "palabras_clave": ["keyword 1", "keyword 2", "keyword 3"],
  "palabras_portada": "TEXTO GANCHO 2-3 palabras específico del relato",
  "descripcion": "Descripción SEO completa (gancho + contexto + CTA + capítulos + créditos + hashtags)",
  "tags": "15-20 tags separados por coma (máx 500 caracteres)",
  "miniatura_prompt": "YouTube horror thumbnail 16:9: terrified face close-up + ghostly silhouette with glowing eyes in {UBICACION_HISTORIA}, high contrast red/black, dark clean area on the right side for text",
  "capitulos": [
    {{"tiempo": "00:00", "titulo": "Capítulo 1"}},
    {{"tiempo": "02:15", "titulo": "Capítulo 2"}},
    {{"tiempo": "04:30", "titulo": "Capítulo 3"}},
    {{"tiempo": "06:45", "titulo": "Capítulo 4"}}
  ],
  "texto_completo": "Relato continuo de 1.400-1.600 palabras en párrafos, primera persona, coloquial"
}}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt_base}],
        "temperature": 0.7,
        "max_tokens": 4000,
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
                    import json5
                    data = json5.loads(json_str)
                    print("✅ json5 parseó exitosamente.")
                except Exception as e5:
                    print(f"❌ json5 también falló: {e5}")
                    raise

            texto = data.get("texto_completo", "")
            palabras = len(texto.split())
            print(f"📊 Palabras del relato: {palabras}")

            if "texto_completo" in data and palabras >= 900:
                titulo_generado = data.get("titulo", "")
                if titulo_largo_ya_publicado(titulo_generado):
                    print(f"⚠️ Título YA PUBLICADO: '{titulo_generado}'. Regenerando...")
                    raise ValueError("Título duplicado")

                print(f"✅ Historia generada: {palabras} palabras.")
                print(f"🏷️ Título SEO: {titulo_generado}")
                print(f"🖼️ Texto miniatura: {data.get('palabras_portada', 'N/A')}")
                print(f"🔑 Keywords: {data.get('palabras_clave', [])}")
                return data
            else:
                print(f"⚠️ Texto insuficiente ({palabras} palabras). Reintentando...")
                raise ValueError("Texto insuficiente")

        except Exception as e:
            print(f"❌ Intento {intento+1}/3 falló: {e}")
            time.sleep(5)

    print("❌ No se pudo generar historia válida.")
    sys.exit(1)

# ================================================================
# 🆕 DIVIDIR TEXTO EN SEGMENTOS (por código)
# ================================================================
def dividir_en_segmentos(texto, max_palabras_por_segmento=55):
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
# 🎬 ASIGNAR ETAPAS VISUALES A SEGMENTOS
# ================================================================
def asignar_etapas_visuales(segmentos, ubicacion):
    n = len(segmentos)
    etapas = []
    ubicaciones = []
    for i in range(n):
        progreso = i / max(n - 1, 1)
        if progreso < 0.2:
            etapa = "inicio_casa"; ubic = f"interior del hogar en {ubicacion}"
        elif progreso < 0.4:
            etapa = "desplazamiento"; ubic = f"calle o vehículo en movimiento, {ubicacion}"
        elif progreso < 0.65:
            etapa = "lugar_destino"; ubic = f"lugar específico del suceso en {ubicacion}"
        elif progreso < 0.85:
            etapa = "climax_evento"; ubic = f"mismo lugar del suceso en {ubicacion}, momento del evento"
        else:
            etapa = "resolucion"; ubic = f"salida o regreso desde el lugar, {ubicacion}"
        etapas.append(etapa)
        ubicaciones.append(ubic)
    return etapas, ubicaciones

# ================================================================
# 🎨 GENERAR PROMPT DE IMAGEN POR SEGMENTO (Entorno + Época)
# ================================================================
def generar_prompt_imagen_segmento(segmento_texto, etapa, ubicacion_escena, segmento_anterior_texto=None):
    contexto_previo = ""
    if segmento_anterior_texto:
        contexto_previo = f"\nPREVIOUS SCENE: The character was just in: '{segmento_anterior_texto[:120]}'"

    instrucciones_etapa = {
        "inicio_casa": "Show the character in a home interior, establishing shot, calm before the events.",
        "desplazamiento": "Show the character in movement (walking, driving), same route as previous scene, different camera angle.",
        "lugar_destino": "Show the character arriving at or exploring the main location, maintaining architectural consistency.",
        "climax_evento": "Show the paranormal event happening in this specific location, character reacting but NOT in close-up face.",
        "resolucion": "Show the aftermath or the character leaving/returning, calmer atmosphere."
    }
    instruccion = instrucciones_etapa.get(etapa, instrucciones_etapa["lugar_destino"])

    prompt = f"""Eres un director de fotografía experto en continuidad narrativa.

Fragmento del relato:
\"\"\"
{segmento_texto}
\"\"\"
{contexto_previo}

Genera un PROMPT DE IMAGEN EN INGLÉS para una foto VERTICAL (9:16) de esta escena.

SCENE CONTINUITY INSTRUCTIONS:
- Current stage: {etapa}
- Current location: {ubicacion_escena}
- DIRECTIVE: {instruccion}
- ERA: {EPOCA_MOD} (Ensure all cars, technology, clothing, and architecture strictly match this specific time period).

Reglas:
- FORMATO: VERTICAL 9:16 (portrait), composición alta.
- ENFOQUE: El ENTORNO (bosques, casas, carros, calles) es el protagonista. 
- Personaje: Si el texto lo menciona, incluye a {PERFIL_PERSONAJE}, pero ocupando MÁXIMO 20% del encuadre, pequeño y a la distancia. Si el texto NO menciona a la persona, NO la incluyas, solo muestra el entorno y los objetos.
- Estilo: hyperrealistic photography, 4k, ultra-detailed.
- Paleta: {PALETA_COLOR_ACTUAL}
- PROHIBIDO: clones, duplicate people, two faces, split faces, gore, blood, text, watermarks.

Devuelve SOLO el prompt en inglés, sin explicaciones.
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "max_tokens": 200,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"⚠️ Error generando prompt de imagen: {e}")
        return f"Vertical 9:16 wide shot of {ubicacion_escena}, depicting: {segmento_texto[:100]}, no close-up face, single person"

# ================================================================
# 🆕 EXPANDIR TEXTO (continuación)
# ================================================================
def expandir_texto(titulo, texto_actual):
    prompt = f"""Historia: "{titulo}"
Final actual del relato:
\"\"\"
{texto_actual[-400:]}
\"\"\"
Continúa la historia con 300-400 palabras más en primera persona, mismo tono, manteniendo coherencia.
Devuelve SOLO el texto de continuación, sin título ni explicaciones.
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 900,
    }
    for intento in range(2):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            r.raise_for_status()
            extra = r.json()["choices"][0]["message"]["content"].strip()
            if len(extra.split()) > 100:
                print(f"✅ Expansión: {len(extra.split())} palabras adicionales.")
                return extra
        except Exception as e:
            print(f"❌ Expansión intento {intento+1}/2 falló: {e}")
            time.sleep(5)
    return ""

# ================================================================
# 🖼️ GENERAR IMAGEN VERTICAL (segmentos 1080x1920)
# ================================================================
def generar_imagen(prompt, width=1080, height=1920, intentos=3):
    prompt_limpio = limpiar_prompt(prompt)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    
    # Negative prompt: Bloquea clones, deformaciones y texto. NO bloquea épocas pasadas.
    negative = (
        "multiple people, duplicate people, cloned faces, two people, three people, crowd, "
        "dual face, split face, two faces, double face, mirror face, two heads, "
        "cut off body, cropped body, partial body, limbs outside frame, truncated person, "
        "deformed, mutated, bad anatomy, extra limbs, extra fingers, missing limbs, missing fingers, "
        "asymmetrical eyes, cross-eyed, malformed features, uncanny valley, "
        "close-up face, portrait, headshot, person filling frame, face occupying more than 25% of image, "
        "gore, blood, bloody, wounds, cuts, bruises, gaunt, emaciated, sickly, "
        "decayed skin, rotting, zombie-like, corpse-like, grotesque, ugly, "
        "text, letters, words, watermarks, logos, signatures, "
        "floating objects, illogical elements, impossible physics, surreal impossibilities, "
        "ghost doubles, transparent figures, multiple versions of same person, "
        "dark, underexposed, low light, heavy shadows, too dark, "
        "over-saturated, oversharpened, low quality, blurry, "
        "broken, shattered, destroyed, post-apocalyptic, dystopian ruins"
    )
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_limpio[:800],
        "negative_prompt": negative,
        "width": width,
        "height": height,
        "num_images": 1
    }
    for intento in range(intentos):
        try:
            print(f"🖼️ Intento {intento+1}/{intentos} generando imagen VERTICAL...")
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code == 200:
                return r.json()["data"][0]["url"]
            else:
                print(f"⚠️ Error: {r.status_code} - {r.text[:100]}")
        except Exception as e:
            print(f"⚠️ Error conexión: {e}")
        if intento < intentos - 1:
            time.sleep(10)
    return None

# ================================================================
# 🖼️ MINIATURA HORIZONTAL CON TEXTO INTEGRADO (1280x720)
# ================================================================
def generar_miniatura_con_texto(prompt_base, texto_portada, width=1280, height=720, intentos=5):
    texto_portada = (texto_portada or "LO VI").upper().strip()
    palabras = texto_portada.split()
    if len(palabras) > 3:
        texto_portada = " ".join(palabras[:3])
    prompt_base = re.sub(r'"', "'", prompt_base or "")
    prompt_base = re.sub(r"\n+", " ", prompt_base)

    prompt_final = f"""{prompt_base}, {ESTILO_VISUAL_ACTUAL}, color palette of {PALETA_COLOR_ACTUAL}, 16:9 widescreen HORIZONTAL YouTube thumbnail, cinematic horror style, high contrast dramatic lighting, sharp focus, {EPOCA_MOD}.

TEXT OVERLAY (CRITICAL REQUIREMENT):
- Render the EXACT Spanish text: "{texto_portada}"
- Style: bold, highly readable horror-themed typography, bright yellow or stark white fill, thick black outline, subtle drop shadow.
- Size: Medium-large but strictly proportional. The text height must NOT exceed 25% of the image height.
- Position: right side of the frame, vertically centered, over a dark clean area.
- The text MUST fit entirely inside the frame with safe margins, never cut off, never overflowing, never touching the edges.
- Spelling MUST be EXACT, character by character: "{texto_portada}". NO typos, NO extra letters.
- Maximum 2 lines if needed.

NO other text, NO watermarks, NO logos."""

    negative = (
        "misspelled text, wrong spelling, typo, distorted letters, garbled text, broken characters, "
        "cut off text, text outside frame, text touching edges, overflowing text, oversized text, giant letters, "
        "multiple people, duplicate people, cloned faces, dual face, split face, "
        "deformed, mutated, bad anatomy, extra limbs, "
        "asymmetrical eyes, cross-eyed, malformed features, uncanny valley, "
        "gore, blood, wounds, gaunt, emaciated, zombie-like, corpse-like, "
        "low quality, blurry, watermark, logo, text other than the requested"
    )
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "agnes-image-2.1-flash",
        "prompt": prompt_final[:1000],
        "negative_prompt": negative,
        "width": width,
        "height": height,
        "num_images": 1
    }
    backoff = [5, 10, 15, 20, 25]
    for intento in range(intentos):
        print(f"🖼️ Intento {intento+1}/{intentos} miniatura HORIZONTAL con texto '{texto_portada}'...")
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code == 200:
                return r.json()["data"][0]["url"]
        except Exception as e:
            print(f"⚠️ Error: {e}")
        if intento < intentos - 1:
            time.sleep(backoff[intento] if intento < len(backoff) else 30)
    return None

# ================================================================
# ✅ GENERAR AUDIO CON FALLBACK ENTRE VOCES
# ================================================================
def generar_audio(texto, index, intentos_por_voz=2):
    global CONFIG_VOZ_ACTUAL
    texto_limpio = re.sub(r"imagen_prompt.*", "", texto, flags=re.IGNORECASE)
    texto_limpio = re.sub(r"prompt.*", "", texto_limpio, flags=re.IGNORECASE)
    texto_limpio = re.sub(r'[\{\}\[\]"]', "", texto_limpio)
    texto_limpio = re.sub(r"\s+", " ", texto_limpio).strip()
    if len(texto_limpio) < 10:
        return None
    filename = f"audio_{index}.mp3"
    voces_a_probar = [CONFIG_VOZ_ACTUAL]
    for voz_config in VOCES_DISPONIBLES:
        if voz_config["voz"] != CONFIG_VOZ_ACTUAL["voz"]:
            voces_a_probar.append(voz_config)
    for intento_voz, voz_config in enumerate(voces_a_probar):
        voz = voz_config["voz"]; rate = voz_config["velocidad"]; pitch = voz_config["tono"]
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
                print(f"❌ Falló {voz}: {e}")
                if intento < intentos_por_voz - 1:
                    time.sleep(3 * (intento + 1))
        if os.path.exists(filename):
            try: os.remove(filename)
            except: pass
    print("❌ Todas las voces fallaron.")
    return None

# ================================================================
# 🎬 MONTAR VIDEO VERTICAL (1080x1920)
# ================================================================
def montar_video(elementos, salida="video_final.mp4"):
    clips_video = []; clips_audio = []
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
                ImageOps.fit(img, (1080, 1920), Image.LANCZOS).save(img_path)
            if duracion > 35:
                duracion_mitad = duracion / 2
                clips_video.extend([ImageClip(img_path, duration=duracion_mitad), ImageClip(img_path, duration=duracion_mitad)])
                clips_audio.extend([audio_clip.subclip(0, duracion_mitad), audio_clip.subclip(duracion_mitad, duracion)])
            else:
                clips_video.append(ImageClip(img_path, duration=duracion))
                clips_audio.append(audio_clip)
        except Exception as e:
            print(f"⚠️ Error en segmento {i}: {e}")
            continue
    if not clips_video or not clips_audio:
        raise ValueError("No se pudieron procesar los clips.")
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
        except Exception as e:
            print(f"⚠️ Error en audio fondo: {e}")
            audio_final = audio_narracion
    else:
        audio_final = audio_narracion
    video = video.set_audio(audio_final)
    video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")
    video.close(); audio_final.close()
    for c in clips_video: c.close()
    for a in clips_audio: a.close()
    return salida, duracion_total

# ================================================================
# LIMPIEZA
# ================================================================
def limpiar_archivos_temporales():
    for f in os.listdir("."):
        if (f.startswith("temp_img_") or f.startswith("audio_")) and (f.endswith(".jpg") or f.endswith(".mp3")):
            try: os.remove(f)
            except: pass
    for aux in ["video_final.mp4", "miniatura.jpg"]:
        if os.path.exists(aux):
            try: os.remove(aux)
            except: pass

# ================================================================
# SUBIR A YOUTUBE (con capítulos automáticos)
# ================================================================
def subir_a_youtube(video_path, miniatura_path, titulo, descripcion, etiquetas, capitulos=None):
    creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
    youtube = build("youtube", "v3", credentials=creds)
    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]
    if capitulos and "⏰ Capítulos" not in descripcion:
        capitulos_texto = "\n\n⏰ Capítulos del relato:\n"
        for cap in capitulos:
            capitulos_texto += f"{cap['tiempo']} - {cap['titulo']}\n"
        if "#" in descripcion:
            partes = descripcion.rsplit("#", 1)
            descripcion = partes[0] + capitulos_texto + "#" + partes[1]
        else:
            descripcion += capitulos_texto
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
            print("✅ Miniatura subida correctamente")
        except Exception as e:
            print(f"⚠️ Error miniatura: {e}")

# ================================================================
# PUBLICACIÓN DIARIA
# ================================================================
def verificar_publicacion_hoy():
    estado = cargar_estado_musica()
    ultima = estado.get("ultima_publicacion_exitosa")
    if not ultima:
        return False
    hoy = datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()
    return ultima == hoy

def marcar_publicacion_exitosa():
    estado = cargar_estado_musica()
    hoy = datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()
    estado["ultima_publicacion_exitosa"] = hoy
    guardar_estado_musica(estado)

# ================================================================
# 🎬 PROCESAR SEGMENTOS (imágenes verticales + audio)
# ================================================================
def procesar_segmentos(segmentos, etapas, ubicaciones, offset=0):
    elementos = []
    imagen_ultimo_recurso = None
    for i, seg_texto in enumerate(segmentos):
        idx = offset + i
        etapa = etapas[i] if i < len(etapas) else "lugar_destino"
        ubic = ubicaciones[i] if i < len(ubicaciones) else UBICACION_HISTORIA
        print(f"\n📍 Segmento {idx+1} - Etapa: {etapa} | {ubic}")
        seg_anterior = segmentos[i-1] if i > 0 else None
        prompt_img = generar_prompt_imagen_segmento(seg_texto, etapa, ubic, seg_anterior)
        if i > 0:
            time.sleep(3)
        url_img = generar_imagen(prompt_img)
        if url_img:
            imagen_ultimo_recurso = url_img
        else:
            if imagen_ultimo_recurso:
                url_img = imagen_ultimo_recurso
            else:
                continue
        audio_file = generar_audio(seg_texto, idx)
        if not audio_file:
            continue
        elementos.append({"imagen_url": url_img, "audio_path": audio_file})
    return elementos

# ================================================================
# MAIN
# ================================================================
def verificar_envs():
    required = ["DEEPSEEK_API_KEY", "AGNES_API_KEY", "YOUTUBE_USER_TOKEN"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print(f"❌ Faltan variables: {', '.join(missing)}")
        sys.exit(1)

def main():
    verificar_envs()
    if verificar_publicacion_hoy():
        print("✅ Ya se publicó hoy. Saliendo.")
        sys.exit(0)

    print(f"🎬 Bot YouTube VERTICAL | Voz: {CONFIG_VOZ_ACTUAL['voz']}")
    print(f"🧑 Personaje: {PERFIL_PERSONAJE}")
    print(f"📍 Ubicación: {UBICACION_HISTORIA}")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    historia = generar_historia_completa()
    
    # 🆕 Extraer año y actualizar época visual antes de generar imágenes
    anio = historia.get("anio_suceso", None)
    actualizar_epoca(anio)

    titulo_video = historia.get("titulo", "Relato Paranormal Real")
    palabras_portada = historia.get("palabras_portada", "LO VI")
    descripcion_video = historia.get("descripcion", f"Relato paranormal.\n\n{FACEBOOK_LINK}")
    tags_video = historia.get("tags", "relatos, leyendas, mexico")
    capitulos_video = historia.get("capitulos", [])
    texto_completo = historia.get("texto_completo", "")

    print(f"\n📊 SEO GENERADO:")
    print(f"   🏷️ Título: {titulo_video}")
    print(f"   🖼️ Texto miniatura: {palabras_portada}")

    segmentos = dividir_en_segmentos(texto_completo, 55)
    etapas, ubicaciones = asignar_etapas_visuales(segmentos, UBICACION_HISTORIA)
    print(f"\n🎨 {len(segmentos)} segmentos divididos por código (imágenes VERTICALES).")

    elementos_validos = procesar_segmentos(segmentos, etapas, ubicaciones, offset=0)

    if not elementos_validos:
        print("❌ No hay elementos válidos.")
        sys.exit(1)

    duracion_actual = sum(AudioFileClip(e["audio_path"]).duration for e in elementos_validos)
    print(f"⏱️ Duración: {duracion_actual/60:.1f} minutos")

    intentos_expansion = 0
    while duracion_actual < DURACION_MINIMA_SEGUNDOS and intentos_expansion < MAX_INTENTOS_EXPANSION:
        print(f"⚠️ Duración insuficiente. Expandiendo intento {intentos_expansion+1}...")
        texto_extra = expandir_texto(titulo_video, texto_completo)
        if texto_extra:
            texto_completo += " " + texto_extra
            nuevos = dividir_en_segmentos(texto_extra, 55)
            etapas_n, ubic_n = asignar_etapas_visuales(nuevos, UBICACION_HISTORIA)
            elems_n = procesar_segmentos(nuevos, etapas_n, ubic_n, offset=len(elementos_validos))
            elementos_validos.extend(elems_n)
            duracion_actual = sum(AudioFileClip(e["audio_path"]).duration for e in elementos_validos)
            intentos_expansion += 1
        else:
            break

    if duracion_actual < DURACION_MINIMA_SEGUNDOS:
        print(f"❌ Duración final insuficiente. Abortando.")
        sys.exit(1)
    print(f"✅ Duración final: {duracion_actual/60:.1f} minutos.")

    print("🖼️ Generando miniatura HORIZONTAL con texto integrado (Agnes)...")
    miniatura_path = "miniatura.jpg"
    miniatura_url = generar_miniatura_con_texto(historia.get("miniatura_prompt", "Terrified face with ghostly silhouette"), palabras_portada)
    if miniatura_url:
        try:
            r = requests.get(miniatura_url, timeout=30)
            r.raise_for_status()
            with open(miniatura_path, "wb") as f:
                f.write(r.content)
            with Image.open(miniatura_path) as img:
                ImageOps.fit(img, (1280, 720), Image.LANCZOS).save(miniatura_path)
            print(f"✅ Miniatura HORIZONTAL con texto '{palabras_portada}' lista.")
        except Exception as e:
            print(f"⚠️ Error miniatura: {e}")
            miniatura_path = None
    else:
        miniatura_path = None

    print("🎬 Montando video VERTICAL...")
    video_path, duracion_final = montar_video(elementos_validos)
    print(f"⏱️ Duración final: {duracion_final/60:.1f} minutos")

    print("⬆️ Subiendo a YouTube...")
    subir_a_youtube(video_path, miniatura_path, titulo_video, descripcion_video, tags_video, capitulos_video)

    guardar_titulo_largo(titulo_video)
    marcar_publicacion_exitosa()
    limpiar_archivos_temporales()
    print("🎉 Proceso completado (video vertical + miniatura horizontal).")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
