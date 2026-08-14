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
# 🎨 PALETAS MODERNAS 2026
# ================================================================
PALETAS_COLOR = [
    "Cold cyan blue LED fog, navy blue modern shadows, crisp white moonlight",
    "Emerald green twilight, modern city haze, muted sage ambient lighting",
    "Deep violet LED haze, electric purple ambient light, dark magenta shadows",
    "Slate gray modern tones, freezing ice blue highlight, dim overcast ambient",
    "Dark teal and deep blue, modern oceanic midnight, cold misty atmosphere",
    "Stark black and white high contrast, silver moonlight, modern pitch shadows",
    "Desaturated cold film look, moody cinematic lighting, 8k hyperrealistic",
    "Neon purple and electric pink, deep violet shadows, cyberpunk modern lights",
    "Electric yellow and charcoal black, stark contrast, dusty atmospheric haze",
    "Deep crimson red, pitch black shadow, intense orange emergency LED lights",
    "Blood red and burnt orange, modern charcoal shadows, hellish glow",
    "Modern warm amber and dark mahogany, golden LED lighting, deep brown shadows",
    "Fiery sunset orange, deep purple shadows, modern red highlights",
    "Toxic lime green and pitch black, eerie chemical modern glow, radioactive haze",
    "Clean modern daylight, neutral gray ambient, crisp shadows",
    "Modern LED streetlight glow, cool white highlights, urban night atmosphere",
]
PALETA_COLOR_ACTUAL = random.choice(PALETAS_COLOR)

# ================================================================
# 📷 ESTILOS VISUALES MODERNOS 2026
# ================================================================
ESTILOS_VISUALES = [
    "Modern 2026 cinematic photograph, bright contemporary lighting, well-lit scene, sharp focus, current era",
    "Contemporary thriller photography 2026, soft modern ambient diffusion, bright highlights, present day",
    "Modern documentary realistic photo 2026, natural crisp skin texture, current fashion and architecture",
    "8k resolution modern cinematic frame, ultra clear facial details, bright exposure, contemporary era",
    "Modern fashion photography style 2026, dramatic but well-lit, clean skin, current trends",
    "Modern noir style 2026, high contrast but well-exposed, contemporary urban atmosphere",
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
        "wearing a modern denim jacket and grey t-shirt",
        "wearing a contemporary dark green coat and wool scarf",
        "wearing a simple white shirt and leather belt",
        "wearing a modern blue mechanic uniform",
        "wearing a dark sweater and slim trousers",
        "wearing a red flannel shirt and modern jeans",
        "wearing a black leather jacket and modern boots",
        "wearing a traditional embroidered blouse and long skirt",
        "wearing a white guayabera shirt and dark pants",
        "wearing a modern hoodie and baseball cap",
        "wearing a contemporary polo shirt and dark pants",
        "wearing a modern delivery uniform with reflective stripes",
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
        "modern fade haircut",
        "contemporary undercut hairstyle",
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
# 🧼 LIMPIADOR DE PROMPTS (MODERNIDAD 2026)
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        prompt = "A quiet modern night scene 2026, bright lighting"
    prompt = re.sub(r"\n+", " ", prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r"[^\x00-\x7F]+", "", prompt)

    palabras_antiguas = [
        r"\bgrainy\b", r"\bvhs\b", r"\bchiaroscuro\b", r"\bdirt\b", r"\bgrime\b",
        r"\blemish\b", r"\bspots\b", r"\bterro\b", r"\bhorror\b", r"\bsangre\b",
        r"\bblood\b", r"\bgore\b", r"\bdemacrad[oa]s?\b", r"\bzombies?\b",
        r"\bdisfigured\b", r"\bwounds?\b", r"\bmonster\b",
        r"\brushy\b", r"\brusted\b", r"\boxidized\b", r"\bweathered\b",
        r"\bdecayed\b", r"\brotten\b", r"\brotting\b", r"\bancient\b",
        r"\bvintage\b", r"\bretro\b", r"\bsepia\b", r"\baged\b",
        r"\bdilapidated\b", r"\bdecrepit\b", r"\brundown\b", r"\bcrumbling\b",
        r"\bcracked\b", r"\bpeeling\b", r"\bcrumpled\b", r"\beroded\b",
        r"\bdeteriorated\b", r"\bemaciated\b", r"\bgaunt\b", r"\bcorpselike\b",
        r"\bzombielike\b", r"\bskeletal\b", r"\bdecompos(?:ed|ing)\b",
        r"\bmoldy\b", r"\bmouldy\b", r"\bmusty\b", r"\bdusty\b",
        r"\bcobwebs?\b", r"\bspiders?\s?webs?\b",
        r"\b19[5-9]\d(?:s)?\b", r"\bold[- ]?(?:fashioned|timer)\b",
        r"\bclassic(?:al)?\b", r"\bantique\b", r"\bhistoric(?:al)?\b",
    ]
    for pattern in palabras_antiguas:
        prompt = re.sub(pattern, "", prompt, flags=re.IGNORECASE)

    prompt_base = re.sub(r"\s+", " ", prompt).strip()[:220]

    modificadores_calidad = (
        f", {ESTILO_VISUAL_ACTUAL}, color palette of {PALETA_COLOR_ACTUAL}, "
        "16:9 widescreen format, single solitary person in frame, exactly one person, "
        "person occupies at most 20-25% of the frame (medium or wide shot), "
        "MODERN 2026 ERA, contemporary setting, present day, current decade, "
        "modern vehicles from 2020-2026, modern architecture, modern clothing, "
        "LED lighting, modern technology visible, smartphones era, "
        "clean well-maintained environments, new or recent buildings, "
        "clean smooth skin, natural facial complexion with light skin tone, "
        "attractive features, healthy appearance, no blemishes, no cloned faces, no duplicate people, "
        "sharp focus, bright well-lit scene, no dark underexposed areas, "
        "no text, no watermark"
    )
    return prompt_base + modificadores_calidad

# ================================================================
# 🖼️ MINIATURA
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
# 🎬 GENERAR GUION CON SEO EXPERTO + CONTINUIDAD VISUAL
# ================================================================
def generar_guion(contexto_extra=""):
    titulos_pub = cargar_titulos_largos()["titulos"][-20:]
    titulos_referencia = "\n".join([f"- {t}" for t in titulos_pub]) if titulos_pub else "Ninguno aún."
    
    # 🎯 PROMPT MEJORADO CON SEO EXPERTO
    prompt_base = f"""Eres un GUIONISTA, DIRECTOR DE CINE DE MISTERIO y EXPERTO EN SEO PARA YOUTUBE 2026.

🚫 TÍTULOS YA PUBLICADOS (NO REPETIR NI PARECERSE):
{titulos_referencia}

Escribe un relato paranormal en primera persona en español, 1.600-1.850 palabras, ambientado en {UBICACION_HISTORIA}, México.
Divide la historia en 28 a 34 segmentos de 45-55 palabras cada uno.

PERSONAJE PRINCIPAL (FIJO):
"{PERFIL_PERSONAJE}"

🎯 REGLA CRÍTICA 1: TÍTULO SEO DE ALTO CTR (lo más importante)

El título DEBE seguir esta FÓRMULA GANADORA:
[VERBO EN 1RA PERSONA] + [LUGAR ESPECÍFICO] + [GANCHO EMOCIONAL]

✅ EJEMPLOS DE TÍTULOS GANADORES (usa este estilo):
- "Fui velador en Oaxaca y vi algo que no debí ver"
- "Trabajé de noche en un manicomio de Puebla. Nunca volví."
- "Escuché llorar a mi hija muerta hace 3 años en el lago"
- "El GPS me llevó a un cenote que no existe en ningún mapa"
- "Pasé la noche en un hotel de Guanajuato. No estaba solo."
- "Mi abuela me contó esto antes de morir. Hoy lo confirmé."

❌ TÍTULOS PROHIBIDOS (no los uses):
- "El misterio de..." / "La leyenda de..." / "Relato de..."
- "Una noche en..." / "La casa de..." / "El fantasma de..."
- Títulos que suenen a documental o libro
- Títulos con más de 65 caracteres

REGLAS DEL TÍTULO:
- Longitud EXACTA: 50-65 caracteres
- DEBE estar en primera persona (yo, mi, me, fui, vi, escuché)
- DEBE tener un lugar específico de {UBICACION_HISTORIA}
- DEBE generar curiosidad inmediata
- DEBE sonar a testimonio REAL, no a ficción

🎯 REGLA CRÍTICA 2: DESCRIPCIÓN CON SEO EXPERTO

La descripción DEBE tener esta ESTRUCTURA EXACTA (con saltos de línea reales):

Línea 1 (GANCHO SEO - las primeras 150 chars son críticas):
"[Frase impactante de 1 línea con keyword principal + lugar + fenómeno]"

Línea 2-3 (CONTEXTO con keywords long-tail):
"[2-3 oraciones con palabras clave naturales: 'terror en {UBICACION_HISTORIA}', 'testimonio real', 'experiencia paranormal real', etc.]"

Línea 4 (LLAMADA A LA ACCIÓN):
"🔴 SUSCRÍBETE para más relatos reales: {CANAL_LINK}"

Línea 5 (CAPÍTULOS/TIMESTAMPS - MUY IMPORTANTE PARA SEO):
"⏰ Capítulos del relato:"
"00:00 - [Título del capítulo 1]"
"02:15 - [Título del capítulo 2]"
"04:30 - [Título del capítulo 3]"
"06:45 - [Título del capítulo 4]"
"[Genera 4-6 capítulos según el flujo de la historia]"

Línea 6 (CRÉDITOS Y DISCLAIMER):
"📱 Facebook: {FACEBOOK_LINK}"
"🤖 Contenido narrado con IA. Relato basado en testimonios reales de internet."

Línea 7 (HASHTAGS - máximo 5, los más relevantes):
"#TerrorEn{UBICACION_HISTORIA.replace(' ', '')} #RelatosReales #Paranormal #Testimonios #MiedoReal"

🎯 REGLA CRÍTICA 3: TAGS SEO (15-20 tags, máximo 500 caracteres)

Los tags DEBEN incluir:
- 3-5 tags ESPECÍFICOS del relato (lugar + fenómeno)
- 5-7 tags LONG-TAIL (búsquedas comunes en YouTube)
- 3-5 tags de TENDENCIA (terror, paranormal, miedo, suspenso)
- 2-3 tags GEOGRÁFICOS (México, {UBICACION_HISTORIA})

EJEMPLOS DE TAGS CORRECTOS:
"terror en {UBICACION_HISTORIA.lower()}, testimonio real de terror, experiencia paranormal real en México, historias de miedo reales, relatos de terror mexicanos, leyendas urbanas de {UBICACION_HISTORIA.lower()}, casos paranormales reales, miedo real, historias reales de terror, terror nocturno, experiencias sobrenaturales reales, historias de fantasmas reales en México, casos sin resolver México, relatos de veladores, historias de traileros terror"

🎯 REGLA CRÍTICA 4: PALABRAS CLAVE PRINCIPALES

Define 2-3 palabras clave principales que usarás en:
- Título
- Primera línea de descripción
- Tags
- Primeros 30 segundos del relato

Ejemplos: "terror en Oaxaca", "experiencia paranormal real", "testimonio de miedo"

🎯 REGLA CRÍTICA 5: TÍTULO ALTERNATIVO (para A/B testing)

Genera un SEGUNDO título siguiendo las mismas reglas, pero con diferente ángulo emocional (uno con miedo, otro con curiosidad, otro con misterio).

🎬 CONTINUIDAD VISUAL (igual que antes):
- Etapas: inicio_casa, desplazamiento, lugar_destino, climax_evento, resolucion
- Trayectoria lógica entre segmentos
- Personaje fijo: {PERFIL_PERSONAJE}
- Ambientación moderna 2026

📐 ESTRUCTURA JSON OBLIGATORIA:
{{
  "titulo": "Título SEO en 1ra persona, 50-65 caracteres",
  "titulo_alternativo": "Segundo título con ángulo diferente",
  "palabras_clave": ["keyword 1", "keyword 2", "keyword 3"],
  "palabras_portada": "CASO REAL",
  "descripcion": "Descripción completa con estructura SEO (gancho + contexto + CTA + capítulos + créditos + hashtags)",
  "tags": "15-20 tags separados por coma (máximo 500 caracteres)",
  "miniatura_descripcion": "1-2 oraciones de la escena más impactante",
  "miniatura_prompt": "Dramatic cinematic photo in {UBICACION_HISTORIA}, {PALETA_COLOR_ACTUAL}, modern 2026 era",
  "capitulos": [
    {{"tiempo": "00:00", "titulo": "Título corto del capítulo 1"}},
    {{"tiempo": "02:15", "titulo": "Título corto del capítulo 2"}},
    {{"tiempo": "04:30", "titulo": "Título corto del capítulo 3"}},
    {{"tiempo": "06:45", "titulo": "Título corto del capítulo 4"}}
  ],
  "segmentos": [
    {{
      "texto": "Narración en español de 45-55 palabras...",
      "etapa_visual": "inicio_casa|desplazamiento|lugar_destino|climax_evento|resolucion",
      "ubicacion_escena": "Descripción breve del lugar específico",
      "imagen_prompt": "Prompt detallado en inglés para esta escena específica"
    }}
  ]
}}

🚨 REGLA DE ORO PARA IMAGEN_PROMPT:
1. Mismo tipo de escenario que el segmento anterior
2. El personaje exacto: {PERFIL_PERSONAJE}
3. Una acción que tenga sentido después de la acción anterior
4. Un ángulo de cámara diferente al segmento anterior

{contexto_extra}
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
                    import json5
                    data = json5.loads(json_str)
                    print("✅ json5 parseó exitosamente.")
                except Exception as e5:
                    print(f"❌ json5 también falló: {e5}")
                    raise

            if "segmentos" in data and len(data["segmentos"]) >= 20:
                titulo_generado = data.get("titulo", "")
                if titulo_largo_ya_publicado(titulo_generado):
                    print(f"⚠️ Título YA PUBLICADO: '{titulo_generado}'. Regenerando...")
                    raise ValueError("Título duplicado")
                
                # Validar y limpiar prompts de imagen con continuidad
                for i, seg in enumerate(data["segmentos"]):
                    if "imagen_prompt" in seg:
                        seg["imagen_prompt"] = limpiar_prompt(seg["imagen_prompt"])
                    # Asegurar campos de continuidad
                    if "etapa_visual" not in seg:
                        if i < 3:
                            seg["etapa_visual"] = "inicio_casa"
                        elif i < len(data["segmentos"]) - 3:
                            seg["etapa_visual"] = "lugar_destino"
                        else:
                            seg["etapa_visual"] = "resolucion"
                    if "ubicacion_escena" not in seg:
                        seg["ubicacion_escena"] = UBICACION_HISTORIA
                
                # 🆕 Log SEO
                print(f"✅ Guion con {len(data['segmentos'])} segmentos y continuidad visual.")
                print(f"🏷️ Título SEO: {titulo_generado}")
                print(f"🔑 Keywords: {data.get('palabras_clave', [])}")
                print(f"📝 Título alternativo: {data.get('titulo_alternativo', 'N/A')}")
                tags_count = len(data.get("tags", "").split(","))
                print(f"🏷️ Tags generados: {tags_count}")
                print(f"📑 Capítulos: {len(data.get('capitulos', []))}")
                
                return data
            else:
                num_segmentos = len(data.get('segmentos', [])) if data else 0
                print(f"⚠️ Segmentos insuficientes ({num_segmentos}). Reintentando...")
                raise ValueError("Segmentos insuficientes")

        except Exception as e:
            print(f"❌ Intento {intento+1}/3 falló: {e}")
            time.sleep(5)

    print("❌ No se pudo generar guion válido.")
    sys.exit(1)

# ================================================================
# EXPANSIÓN DE GUION
# ================================================================
def expandir_guion(titulo, ultimos_segmentos, intento_actual):
    contexto = f"""
Historia: "{titulo}"
Últimos 3 segmentos:
{json.dumps(ultimos_segmentos[-3:], ensure_ascii=False, indent=2)}

Continúa la historia con ~10 segmentos adicionales de 45-55 palabras, manteniendo:
- La misma ubicación física del último segmento
- El mismo personaje: {PERFIL_PERSONAJE}
- La trayectoria lógica de la escena
- Campos: texto, etapa_visual, ubicacion_escena, imagen_prompt
"""
    prompt = f"""Eres el mismo guionista. {contexto}

Devuelve JSON con clave "segmentos_extra" (array de objetos con texto, etapa_visual, ubicacion_escena, imagen_prompt).
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
            respuesta = r.json()["choices"][0]["message"]["content"].strip()
            json_str = limpiar_respuesta_json(respuesta)

            data = None
            try:
                data = json.loads(json_str, strict=False)
            except json.JSONDecodeError:
                import json5
                data = json5.loads(json_str)

            if "segmentos_extra" in data and len(data["segmentos_extra"]) > 0:
                for seg in data["segmentos_extra"]:
                    if "imagen_prompt" in seg:
                        seg["imagen_prompt"] = limpiar_prompt(seg["imagen_prompt"])
                print(f"✅ Expansión: {len(data['segmentos_extra'])} segmentos adicionales.")
                return data["segmentos_extra"]
            else:
                raise ValueError("Expansión vacía")
        except Exception as e:
            print(f"❌ Expansión intento {intento+1}/2 falló: {e}")
            time.sleep(5)

    return []

# ================================================================
# 🎨 GENERAR PROMPT DE IMAGEN CON MEMORIA VISUAL
# ================================================================
def generar_prompt_con_contexto(segmento_actual, segmento_anterior=None, segmento_siguiente=None):
    """
    Genera un prompt de imagen enriquecido con contexto de continuidad narrativa.
    """
    etapa = segmento_actual.get("etapa_visual", "lugar_destino")
    ubicacion = segmento_actual.get("ubicacion_escena", UBICACION_HISTORIA)
    texto_seg = segmento_actual.get("texto", "")
    prompt_base = segmento_actual.get("imagen_prompt", "")
    
    # Contexto del segmento anterior (de dónde viene)
    contexto_previo = ""
    if segmento_anterior:
        ubicacion_prev = segmento_anterior.get("ubicacion_escena", "")
        etapa_prev = segmento_anterior.get("etapa_visual", "")
        contexto_previo = f"\nPREVIOUS SCENE CONTEXT: The character was just in '{ubicacion_prev}' during the '{etapa_prev}' stage."
    
    # Contexto del siguiente (hacia dónde va)
    contexto_siguiente = ""
    if segmento_siguiente:
        ubicacion_next = segmento_siguiente.get("ubicacion_escena", "")
        contexto_siguiente = f"\nNEXT SCENE: The story continues toward '{ubicacion_next}'."
    
    # Instrucciones de continuidad según etapa
    instrucciones_etapa = {
        "inicio_casa": "Show the character in a modern home interior, establishing shot, calm before the events.",
        "desplazamiento": "Show the character in movement (walking, driving), same route as previous scene, different camera angle.",
        "lugar_destino": "Show the character arriving at or exploring the main location, maintaining architectural consistency with previous segments.",
        "climax_evento": "Show the paranormal event happening in this specific location, character reacting but NOT in close-up face.",
        "resolucion": "Show the aftermath or the character leaving/returning, calmer atmosphere."
    }
    
    instruccion = instrucciones_etapa.get(etapa, instrucciones_etapa["lugar_destino"])
    
    prompt_final = f"""{prompt_base}

SCENE CONTINUITY INSTRUCTIONS:
- Current stage: {etapa}
- Current location: {ubicacion}
- Story moment: {texto_seg[:150]}
{contexto_previo}{contexto_siguiente}
- DIRECTIVE: {instruccion}

VISUAL CONSISTENCY RULES:
- EXACTLY ONE PERSON (the main character): {PERFIL_PERSONAJE}
- The character must occupy maximum 20-25% of the frame
- Modern 2026 setting, contemporary clothing and architecture
- Maintain color palette: {PALETA_COLOR_ACTUAL}
- Style: {ESTILO_VISUAL_ACTUAL}
- Camera angle different from previous scene for visual variety

ABSOLUTE PROHIBITIONS:
- NO multiple people, NO duplicate figures, NO ghostly doubles
- NO cut-off bodies, NO partial bodies, NO limbs outside frame
- NO faces in close-up, NO portraits, NO headshots
- NO floating objects, NO illogical elements, NO surreal impossibilities
- NO vintage elements, NO rusty objects, NO abandoned ruins
- NO gore, NO blood, NO wounds, NO deformities
- NO text, NO watermarks, NO logos
"""
    return prompt_final

# ================================================================
# 🖼️ GENERAR IMAGEN CON NEGATIVE PROMPT MEJORADO
# ================================================================
def generar_imagen(prompt, texto_segmento="", width=2048, height=1152, intentos=3):
    prompt_limpio = limpiar_prompt(prompt)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    
    # Negative prompt mejorado para evitar defectos
    negative = (
        "multiple people, duplicate people, cloned faces, two people, three people, crowd, "
        "cut off body, cropped body, partial body, limbs outside frame, truncated person, "
        "deformed, mutated, bad anatomy, extra limbs, extra fingers, missing limbs, missing fingers, "
        "asymmetrical eyes, cross-eyed, malformed features, uncanny valley, "
        "close-up face, portrait, headshot, person filling frame, face occupying more than 25% of image, "
        "gore, blood, bloody, wounds, cuts, bruises, gaunt, emaciated, sickly, "
        "decayed skin, rotting, zombie-like, corpse-like, grotesque, ugly, "
        "rusty, rusted, oxidized, weathered, aged, vintage, retro, antique, old-fashioned, "
        "dilapidated, decrepit, run-down, crumbling, cracked walls, peeling paint, "
        "deteriorated, abandoned ruins, moldy, mouldy, musty, dusty, cobwebs, spiderwebs, "
        "classic car, old car, vintage car, retro car, horse carriage, "
        "1950s, 1960s, 1970s, 1980s, 1990s, ancient, medieval, historical, "
        "sepia tone, monochrome, black and white, film grain, "
        "floating objects, illogical elements, impossible physics, surreal impossibilities, "
        "ghost doubles, transparent figures, multiple versions of same person, "
        "dark, underexposed, low light, heavy shadows, too dark, "
        "over-saturated, oversharpened, low quality, blurry, text, watermark, logo, "
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
            print(f"🖼️ Intento {intento+1}/{intentos} generando imagen con continuidad...")
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code == 200:
                url_img = r.json()["data"][0]["url"]
                print(f"✅ Imagen generada (intento {intento+1})")
                return url_img
            else:
                print(f"⚠️ Error: {r.status_code} - {r.text[:100]}")
        except Exception as e:
            print(f"⚠️ Error conexión: {e}")
        
        if intento < intentos - 1:
            print(f"⏳ Esperando 10s...")
            time.sleep(10)
    
    return None

# ================================================================
# 🖼️ GENERAR MINIATURA
# ================================================================
def generar_miniatura(prompt, width=1280, height=720, intentos=5):
    prompt_limpio = limpiar_prompt(prompt)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    
    negative = (
        "multiple people, duplicate people, cloned faces, "
        "cut off body, cropped body, partial body, "
        "deformed, mutated, bad anatomy, extra limbs, "
        "close-up face, portrait, headshot, "
        "gore, blood, wounds, gaunt, emaciated, "
        "rusty, vintage, retro, antique, dilapidated, "
        "1950s, 1960s, 1970s, 1980s, 1990s, sepia, monochrome, "
        "low quality, blurry, text, watermark, logo"
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
        print(f"🖼️ Intento {intento+1}/{intentos} miniatura...")
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
        voz = voz_config["voz"]
        rate = voz_config["velocidad"]
        pitch = voz_config["tono"]
        
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
            try:
                os.remove(filename)
            except:
                pass
    
    print("❌ Todas las voces fallaron.")
    return None

# ================================================================
# 🎬 MONTAR VIDEO
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
            else:
                video_clip = ImageClip(img_path, duration=duracion)
                clips_video.append(video_clip)
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

    video.close()
    audio_final.close()
    for c in clips_video:
        c.close()
    for a in clips_audio:
        a.close()

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

# ================================================================
# SUBIR A YOUTUBE (con capítulos automáticos en descripción)
# ================================================================
def subir_a_youtube(video_path, miniatura_path, titulo, descripcion, etiquetas, capitulos=None):
    creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
    youtube = build("youtube", "v3", credentials=creds)
    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]
    
    # 🆕 Si la descripción no tiene capítulos y tenemos datos de capítulos, agregarlos
    if capitulos and "⏰ Capítulos" not in descripcion:
        capitulos_texto = "\n\n⏰ Capítulos del relato:\n"
        for cap in capitulos:
            capitulos_texto += f"{cap['tiempo']} - {cap['titulo']}\n"
        # Insertar antes de los hashtags
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

    print(f"🎬 Bot YouTube | Voz: {CONFIG_VOZ_ACTUAL['voz']}")
    print(f"🧑 Personaje: {PERFIL_PERSONAJE}")
    print(f"📍 Ubicación: {UBICACION_HISTORIA}")
    print(f"🎨 Paleta: {PALETA_COLOR_ACTUAL[:60]}...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    guion_data = generar_guion()
    titulo_video = guion_data.get("titulo", "Relato Paranormal Real")
    titulo_alternativo = guion_data.get("titulo_alternativo", "")
    palabras_clave = guion_data.get("palabras_clave", [])
    palabras_portada = guion_data.get("palabras_portada", "CASO REAL")
    descripcion_video = guion_data.get("descripcion", f"Relato paranormal.\n\n{FACEBOOK_LINK}")
    tags_video = guion_data.get("tags", "relatos, leyendas, mexico")
    capitulos_video = guion_data.get("capitulos", [])
    segmentos = guion_data.get("segmentos", [])

    # 🆕 Log SEO info
    print(f"\n📊 SEO GENERADO:")
    print(f"   🏷️ Título: {titulo_video}")
    print(f"   🔄 Alternativo: {titulo_alternativo}")
    print(f"   🔑 Keywords: {palabras_clave}")
    print(f"   📑 Capítulos: {len(capitulos_video)}")

    elementos_validos = []
    imagen_ultimo_recurso = None

    # 🎬 GENERACIÓN CON MEMORIA VISUAL
    print(f"\n🎨 Generando {len(segmentos)} imágenes con continuidad narrativa...")
    
    for i, seg in enumerate(segmentos):
        print(f"\n📍 Segmento {i+1}/{len(segmentos)} - Etapa: {seg.get('etapa_visual', '?')}")
        print(f"   📍 Ubicación: {seg.get('ubicacion_escena', 'N/A')}")
        print(f"   📝 Texto: {seg.get('texto', '')[:80]}...")
        
        # Obtener segmentos anterior y siguiente para continuidad
        seg_anterior = segmentos[i-1] if i > 0 else None
        seg_siguiente = segmentos[i+1] if i < len(segmentos) - 1 else None
        
        # Generar prompt con contexto de continuidad
        prompt_con_contexto = generar_prompt_con_contexto(seg, seg_anterior, seg_siguiente)
        
        # Generar imagen
        if i > 0:
            time.sleep(3)
        
        url_img = generar_imagen(prompt_con_contexto, texto_segmento=seg.get("texto", ""), width=2048, height=1152)
        
        if url_img:
            imagen_ultimo_recurso = url_img
        else:
            if imagen_ultimo_recurso:
                print(f"⚠️ Reutilizando imagen anterior para segmento {i}.")
                url_img = imagen_ultimo_recurso
            else:
                print(f"❌ Sin imagen para segmento {i}. Saltando...")
                continue
        
        audio_file = generar_audio(seg.get("texto", ""), i)
        if not audio_file:
            continue

        elementos_validos.append({"imagen_url": url_img, "audio_path": audio_file})

    if not elementos_validos:
        print("❌ No hay elementos válidos.")
        sys.exit(1)

    duracion_actual = sum(AudioFileClip(e["audio_path"]).duration for e in elementos_validos)
    print(f"⏱️ Duración: {duracion_actual/60:.1f} minutos")

    intentos_expansion = 0
    while duracion_actual < DURACION_MINIMA_SEGUNDOS and intentos_expansion < MAX_INTENTOS_EXPANSION:
        print(f"⚠️ Duración insuficiente. Expandiendo intento {intentos_expansion+1}...")
        nuevos_segmentos = expandir_guion(titulo_video, segmentos[-3:], intentos_expansion+1)
        if nuevos_segmentos:
            for j, seg in enumerate(nuevos_segmentos):
                seg_anterior = segmentos[-1] if segmentos else None
                prompt_ctx = generar_prompt_con_contexto(seg, seg_anterior, None)
                url_img = generar_imagen(prompt_ctx, texto_segmento=seg.get("texto", ""), width=2048, height=1152)
                if url_img:
                    imagen_ultimo_recurso = url_img
                else:
                    url_img = imagen_ultimo_recurso
                if not url_img:
                    continue
                audio_file = generar_audio(seg.get("texto", ""), len(elementos_validos) + j)
                if audio_file:
                    elementos_validos.append({"imagen_url": url_img, "audio_path": audio_file})
                    segmentos.append(seg)
            duracion_actual = sum(AudioFileClip(e["audio_path"]).duration for e in elementos_validos)
            intentos_expansion += 1
        else:
            break

    if duracion_actual < DURACION_MINIMA_SEGUNDOS:
        print(f"❌ Duración final insuficiente. Abortando.")
        sys.exit(1)

    print(f"✅ Duración final: {duracion_actual/60:.1f} minutos.")

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
        except Exception as e:
            print(f"⚠️ Error miniatura: {e}")
            miniatura_path = None
    else:
        miniatura_path = None

    print("🎬 Montando video...")
    video_path, duracion_final = montar_video(elementos_validos)
    print(f"⏱️ Duración final: {duracion_final/60:.1f} minutos")

    print("⬆️ Subiendo a YouTube...")
    subir_a_youtube(
        video_path=video_path,
        miniatura_path=miniatura_path,
        titulo=titulo_video,
        descripcion=descripcion_video,
        etiquetas=tags_video,
        capitulos=capitulos_video  # 🆕 Pasamos capítulos
    )

    guardar_titulo_largo(titulo_video)
    
    # 🆕 Guardar también el título alternativo para futuras referencias
    if titulo_alternativo and titulo_alternativo != titulo_video:
        print(f"💡 Título alternativo guardado como referencia: {titulo_alternativo}")
    
    marcar_publicacion_exitosa()
    limpiar_archivos_temporales()
    print("🎉 Proceso completado con SEO experto.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
