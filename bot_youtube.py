# -*- coding: utf-8 -*-
"""
SOMBRAS DE MEDIANOCHE - Bot de relatos de terror v3 (CORREGIDO)
Flujo: elegir tema -> plan SEO -> relato por capítulos -> voz -> escenas (Pexels) 
-> miniatura -> subtítulos SRT -> subida programada con reintentos robustos.
"""
import asyncio
import bisect
import json
import os
import random
import re
import sys
import time
import traceback
import ssl
import socket
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import edge_tts
import numpy as np
import requests
import urllib3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    VideoClip,
    VideoFileClip,
    concatenate_audioclips,
)
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
try:
    import json5
except ImportError:
    json5 = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================================================================
# CONFIGURACIÓN
# ================================================================
TZ = ZoneInfo("America/Mexico_City")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
YOUTUBE_USER_TOKEN = json.loads(os.getenv("YOUTUBE_USER_TOKEN") or "{}")
PLAYLIST_ID = os.getenv("YOUTUBE_PLAYLIST_ID", "")
FACEBOOK_LINK = "https://www.facebook.com/profile.php?id=61593237382982"
CANAL_LINK = "https://www.youtube.com/@sombrasdemedianocheoficial"

# Archivos de estado
MUSICA_ESTADO_FILE = "estado_musica.json"
TITULOS_LARGOS_FILE = "titulos_largos_publicados.json"
TEMAS_SHORTS_FILE = "temas_shorts.json"

# ✅ CORRECCIONES DE DURACIÓN Y ESTRUCTURA
DURACION_MINIMA_SEGUNDOS = 480   # 8 minutos mínimo
DURACION_MAXIMA_SEGUNDOS = 660   # 11 minutos máximo (TOPE DE SEGURIDAD)
MAX_INTENTOS_EXPANSION = 1       # Reducido de 2 a 1
NUM_CAPITULOS = 4                # Reducido de 6 a 4 capítulos

SEG_MAX_PALABRAS = 55
SEG_ESCENA = 9.0
W, H, FPS = 1920, 1080, 24
VOL_FONDO = 0.10
USAR_VIDEOS = os.getenv("USAR_VIDEOS", "true").lower() == "true"
GENERAR_SHORT = os.getenv("GENERAR_SHORT", "true").lower() == "true"
PROGRAMAR_PICO = os.getenv("PROGRAMAR_PICO", "true").lower() == "true"
HORA_PICO = int(os.getenv("HORA_PICO", "19"))
INTERVALO_MIN_HORAS = float(os.getenv("INTERVALO_MIN_HORAS", "20"))
ACTIVAR_DISCLOSURE_IA = True
DISCLOSURE_TEXT = (
    "\n\n⚠️ Relato de ficción narrado con inteligencia artificial, inspirado en "
    "leyendas urbanas, creepypastas y folclor. Personajes y sucesos son ficticios."
)
VOZ_CANAL = {"voz": "es-MX-JorgeNeural", "tono": "-4Hz"}
VOCES_RESPALDO = ["es-MX-JorgeNeural", "es-ES-AlvaroNeural", "es-CO-GonzaloNeural", "es-US-AlonsoNeural"]
RATE_ETAPA = {"apertura": "+6%", "tension": "+6%", "destino": "+4%", "climax": "-2%", "resolucion": "+2%"}
PAUSA_ETAPA = {"apertura": 0.5, "tension": 0.45, "destino": 0.5, "climax": 0.75, "resolucion": 0.6}
PROB_VIDEO = {"apertura": 0.5, "tension": 0.5, "destino": 0.6, "climax": 0.5, "resolucion": 0.4}
FUENTE_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"
SUFIJO_TITULO = " | Relato de Terror"
FONDOS_DISPONIBLES = [
    "Ash and Marrow.mp3", "Black Maw.mp3", "Cold Hollow.mp3",
    "Hollow Marrow.mp3", "Sunken Dread.mp3", "Sunless Vault.mp3", "The Deep Rot.mp3",
]
ESTADOS_MEXICO = [
    "Aguascalientes", "Baja California", "Campeche", "Chiapas", "Chihuahua", "Coahuila",
    "Colima", "Durango", "Estado de México", "Guanajuato", "Guerrero", "Hidalgo", "Jalisco",
    "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", "Puebla", "Querétaro",
    "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora", "Tabasco", "Tamaulipas",
    "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas",
]

# ================================================================
# TEMAS
# ================================================================
TEMAS = [
    {"tema": "backrooms", "seed": "backrooms historia", "angulo": "Un espacio liminal aparece al cruzar una puerta común; reglas extrañas, imposible salir.",
     "keywords": ["backrooms", "espacios liminales", "dimensión paralela", "atrapado"],
     "contextos": ["hotel abandonado", "centro comercial vacío", "túneles", "edificio de oficinas"],
     "visuales": ["empty office corridor", "yellow wallpaper room", "fluorescent light hallway", "empty parking garage", "abandoned mall interior"],
     "hashtags": ["#Backrooms", "#EspaciosLiminales"]},
    {"tema": "skinwalker", "seed": "skinwalker relatos", "angulo": "Algo imita voces y te sigue por un camino solitario durante varias noches.",
     "keywords": ["skinwalker", "criatura", "persecución", "bosque"],
     "contextos": ["carretera solitaria", "bosque profundo", "sierra aislada", "desierto de noche"],
     "visuales": ["dark forest fog", "desert road night", "mountain night", "lonely highway night", "eyes in the dark"],
     "hashtags": ["#Skinwalker", "#CriaturasDeLaNoche"]},
    {"tema": "ritual", "seed": "ritual prohibido historia de terror", "angulo": "Un ritual hecho por curiosidad abre algo que no se puede cerrar.",
     "keywords": ["ritual", "invocación", "maldición", "ocultismo"],
     "contextos": ["cementerio antiguo", "casa abandonada", "cueva", "iglesia en ruinas"],
     "visuales": ["candles dark room", "old cemetery night", "abandoned church", "cave darkness", "old book candle"],
     "hashtags": ["#Rituales", "#Ocultismo"]},
    {"tema": "ia_maldita", "seed": "inteligencia artificial terror historia", "angulo": "Una IA empieza a predecir cosas íntimas y cada predicción se cumple.",
     "keywords": ["inteligencia artificial", "predicción", "algoritmo", "tecnología"],
     "contextos": ["oficina de noche", "cuarto de servidores", "universidad", "casa con domótica"],
     "visuales": ["computer screen dark", "server room", "laptop night dark", "glitch screen", "dark office night"],
     "hashtags": ["#IA", "#TerrorTecnologico"]},
    {"tema": "llamada_misteriosa", "seed": "llamada misteriosa terror", "angulo": "Un número desconocido llama a la misma hora y sabe cosas que nadie debería saber.",
     "keywords": ["llamada misteriosa", "teléfono", "número desconocido", "voz"],
     "contextos": ["casa sola", "oficina nocturna", "sótano", "cabina telefónica"],
     "visuales": ["old telephone dark", "phone booth night", "ringing phone dark", "dark basement", "empty office night"],
     "hashtags": ["#LlamadaMisteriosa"]},
    {"tema": "deep_web", "seed": "deep web terror historia", "angulo": "Un archivo encontrado en foros oscuros parece describir la vida del narrador.",
     "keywords": ["deep web", "archivos", "foro oscuro", "internet"],
     "contextos": ["cuarto oscuro", "cibercafé viejo", "sótano", "departamento en la madrugada"],
     "visuales": ["dark room computer", "monitor glow dark", "bunker corridor", "cables dark", "hooded figure dark"],
     "hashtags": ["#DeepWeb", "#TerrorDigital"]},
    {"tema": "creepypasta", "seed": "creepypasta relato", "angulo": "Una leyenda de internet resulta tener un punto de origen físico y cercano.",
     "keywords": ["creepypasta", "leyenda urbana", "internet", "origen"],
     "contextos": ["parque abandonado", "calle solitaria", "bosque nocturno", "casa del barrio"],
     "visuales": ["dark forest night", "abandoned playground", "empty street night", "old house night", "foggy park night"],
     "hashtags": ["#Creepypasta", "#LeyendasUrbanas"]},
    {"tema": "objeto_maldito", "seed": "objeto maldito historia", "angulo": "Un objeto comprado barato trae reglas silenciosas y consecuencias cada noche.",
     "keywords": ["objeto maldito", "antigüedad", "espejo", "muñeca"],
     "contextos": ["tienda de antigüedades", "mercado de pulgas", "casa heredada", "subasta"],
     "visuales": ["antique shop", "old doll", "old mirror dark", "antique room dark", "pawn shop night"],
     "hashtags": ["#ObjetoMaldito"]},
    {"tema": "velador", "seed": "trabajé de velador terror", "angulo": "Turno nocturno de vigilante; las cámaras muestran algo que no está en el pasillo real.",
     "keywords": ["velador", "turno de noche", "cámaras de seguridad", "trabajo nocturno"],
     "contextos": ["fábrica abandonada", "bodega", "escuela vacía", "estacionamiento"],
     "visuales": ["security guard night", "empty factory night", "warehouse dark", "cctv camera", "parking lot night"],
     "hashtags": ["#Velador", "#TurnoDeNoche"]},
    {"tema": "hospital", "seed": "hospital terror historia", "angulo": "Guardia nocturna en un hospital donde un paciente ya no debería existir.",
     "keywords": ["hospital", "guardia nocturna", "paciente", "enfermera"],
     "contextos": ["hospital viejo", "clínica cerrada", "ala clausurada", "morgue"],
     "visuales": ["hospital corridor dark", "abandoned hospital", "empty hospital bed", "wheelchair dark", "operating room old"],
     "hashtags": ["#HospitalEmbrujado"]},
    {"tema": "carretera", "seed": "carretera de noche terror historia", "angulo": "Un viaje nocturno por carretera con un pasajero o una señal que no debieron existir.",
     "keywords": ["carretera", "viaje nocturno", "taxi", "autoestopista"],
     "contextos": ["carretera federal", "gasolinera", "túnel", "curva de la muerte"],
     "visuales": ["highway night fog", "taxi night city", "road tunnel dark", "truck night highway", "gas station night"],
     "hashtags": ["#CarreteraMaldita"]},
    {"tema": "leyenda_mexicana", "seed": "leyenda mexicana terror", "angulo": "Una leyenda del pueblo cobra vida en versión contemporánea.",
     "keywords": ["leyendas mexicanas", "nahual", "la llorona", "pueblo"],
     "contextos": ["pueblo antiguo", "río de noche", "panteón del pueblo", "rancho abandonado"],
     "visuales": ["old village night", "colonial church night", "dirt road night", "river fog night", "candles altar"],
     "hashtags": ["#LeyendasMexicanas", "#TerrorMexicano"]},
]

ESCENAS_FALLBACK = {
    "apertura": ["dark hallway night", "old house interior dark", "flickering light bulb", "lonely street night"],
    "tension": ["foggy road night", "empty highway night", "car headlights fog", "dark forest path"],
    "destino": ["abandoned building", "creepy old house", "dark forest fog", "abandoned corridor"],
    "climax": ["shadow figure dark", "scary dark room", "flashlight darkness", "silhouette door light"],
    "resolucion": ["sunrise fog road", "dawn empty street", "morning mist forest", "walking away silhouette dawn"],
}

# ================================================================
# UTILIDADES
# ================================================================
def cargar_json(ruta, default):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def guardar_json(ruta, data):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, ruta)

def cargar_estado():
    estado = cargar_json(MUSICA_ESTADO_FILE, {})
    if "ultimo_fondo" in estado and "ultimos_fondos" not in estado:
        estado["ultimos_fondos"] = [estado.pop("ultimo_fondo")]
    estado.setdefault("ultimos_fondos", [])
    estado.setdefault("videos", [])
    estado.setdefault("temas_recientes", [])
    return estado

def parsear_json(texto):
    if not texto:
        raise ValueError("respuesta vacía")
    t = re.sub(r"```(?:json)?", " ", texto, flags=re.I)
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1:
        raise ValueError("sin JSON")
    t = t[i:j + 1]
    t = re.sub(r",\s*([}\]])", r"\1", t)
    if json5:
        try:
            return json5.loads(t)
        except Exception:
            pass
    return json.loads(t, strict=False)

def llm(prompt, temperature=0.8, max_tokens=1500, json_mode=False, system=None, intentos=3):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    payload = {"model": DEEPSEEK_MODEL, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    for i in range(intentos):
        try:
            r = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=150)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"⚠️ LLM intento {i+1}/{intentos}: {e}")
            time.sleep(5 * (i + 1))
    return None

def descargar(url, ruta, max_bytes=20 * 1024 * 1024):
    try:
        with requests.get(url, stream=True, timeout=40) as r:
            r.raise_for_status()
            total = 0
            with open(ruta, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("archivo demasiado grande")
                    f.write(chunk)
            return os.path.getsize(ruta) > 1000
    except Exception as e:
        print(f"⚠️ Descarga fallida: {e}")
        if os.path.exists(ruta):
            os.remove(ruta)
        return False

def fmt_ts(seg):
    seg = int(seg)
    h, m, s = seg // 3600, seg % 3600 // 60, seg % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

# ================================================================
# HISTORIAL
# ================================================================
def titulo_largo_ya_publicado(titulo):
    data = cargar_json(TITULOS_LARGOS_FILE, {"titulos": []})
    n = titulo.lower().strip()
    p1 = set(re.findall(r"\w+", n))
    for t in data["titulos"]:
        tn = t.lower().strip()
        if n == tn:
            return True
        p2 = set(re.findall(r"\w+", tn))
        if len(p1) > 3 and len(p2) > 3 and len(p1 & p2) / min(len(p1), len(p2)) > 0.7:
            return True
    return False

def guardar_titulo_largo(titulo):
    data = cargar_json(TITULOS_LARGOS_FILE, {"titulos": []})
    if titulo not in data["titulos"]:
        data["titulos"].append(titulo)
    guardar_json(TITULOS_LARGOS_FILE, data)

def tema_ya_usado(tema, umbral=0.5):
    data = cargar_json(TEMAS_SHORTS_FILE, {"temas": []})
    nuevas = set(re.findall(r"\w+", tema.lower()))
    for antiguo in data["temas"][-20:]:
        viejas = set(re.findall(r"\w+", antiguo.lower()))
        union = nuevas | viejas
        if union and len(nuevas & viejas) / len(union) > umbral:
            print(f"⚠️ Tema similar a: '{antiguo}'")
            return True
    return False

def guardar_tema(tema):
    data = cargar_json(TEMAS_SHORTS_FILE, {"temas": []})
    if tema not in data["temas"]:
        data["temas"].append(tema)
    guardar_json(TEMAS_SHORTS_FILE, data)

# ================================================================
# YOUTUBE: cliente, demanda, rendimiento propio
# ================================================================
def crear_cliente_youtube():
    try:
        creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
        return build("youtube", "v3", credentials=creds)
    except Exception as e:
        print(f"⚠️ No se pudo crear cliente YouTube: {e}")
        return None

def sugerencias_youtube(seed):
    try:
        r = requests.get("https://suggestqueries.google.com/complete/search", timeout=10,
                         params={"client": "firefox", "ds": "yt", "hl": "es", "gl": "mx", "q": seed})
        return [s for s in r.json()[1] if isinstance(s, str)][:8]
    except Exception:
        return []

def puntuar_demanda(youtube, consulta):
    if youtube is None:
        return None
    try:
        desde = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
        r = youtube.search().list(part="id", q=consulta, type="video", order="viewCount", publishedAfter=desde,
                                  relevanceLanguage="es", regionCode="MX", maxResults=8).execute()
        ids = [i["id"]["videoId"] for i in r.get("items", [])]
        if not ids:
            return 0
        s = youtube.videos().list(part="statistics", id=", ".join(ids)).execute()
        vistas = [int(i["statistics"].get("viewCount", 0)) for i in s.get("items", [])]
        return sum(vistas) / len(vistas) if vistas else 0
    except Exception as e:
        print(f"⚠️ Demanda no disponible ({consulta}): {e}")
        return None

def actualizar_rendimiento(youtube, estado):
    ids = [v["id"] for v in estado["videos"][-30:] if v.get("id")]
    if not ids or youtube is None:
        return
    try:
        r = youtube.videos().list(part="statistics", id=", ".join(ids)).execute()
        vistas = {i["id"]: int(i["statistics"].get("viewCount", 0)) for i in r.get("items", [])}
        for v in estado["videos"]:
            if v.get("id") in vistas:
                v["vistas"] = vistas[v["id"]]
    except Exception as e:
        print(f"⚠️ No se pudo leer rendimiento: {e}")

def elegir_tema(estado, youtube):
    recientes = estado["temas_recientes"][-4:]
    pool = [t for t in TEMAS if t["tema"] not in recientes] or TEMAS[:]
    candidatos = random.sample(pool, min(4, len(pool)))
    acum = {}
    for v in estado["videos"]:
        if "vistas" in v:
            acum.setdefault(v["tema"], []).append(v["vistas"])
    rend = {k: sum(x) / len(x) for k, x in acum.items()}
    max_r = max(rend.values()) if rend else 1
    demandas = {t["tema"]: puntuar_demanda(youtube, t["seed"]) for t in candidatos}
    max_d = max([d for d in demandas.values() if d] or [1])
    
    def score(t):
        d = demandas[t["tema"]]
        sd = d / max_d if d else 0.4
        sr = rend[t["tema"]] / max_r if t["tema"] in rend and max_r else 0.6
        return 0.5 * sd + 0.5 * sr + random.uniform(0, 0.15)
        
    elegido = max(candidatos, key=score)
    print(f"🎯 Tema elegido: {elegido['tema']} (demanda={demandas[elegido['tema']]}, propio={rend.get(elegido['tema'])})")
    return elegido

# ================================================================
# TÍTULOS: puntuación CTR + honestidad
# ================================================================
GANCHOS = ["nunca", "nadie", "jamás", "no ", "noche", "3:33", "3:00", "4:44", "madrugada", "medianoche",
           "escuché", "vi ", "descubrí", "encontré", "sobreviví", "trabajé", "qué", "por qué", "cómo", "?", "si "]
PROHIBIDAS = ["testimonio real", "caso real", "100% real", "verídico", "evidencia", "pruebas", "autoridades",
              "filtrado", "es real", "historia real", "hechos reales"]
GENERICAS = ["misterio", "leyenda", "relato", "caso", "historia de terror", "el fantasma de"]

def limpiar_titulo(t):
    t = re.sub(r"\s+", " ", t.strip().strip("“”'").rstrip("."))
    t = re.sub(r"\s*[-|–]\s*relato de terror\s*$", "", t, flags=re.I)
    palabras = t.split()
    caps = [w for w in palabras if len(re.sub(r"\W", " ", w)) >= 3 and w.isupper()]
    if len(caps) > 3:
        keep = set(caps[:2])
        palabras = [w if (not w.isupper() or w in keep or len(w) < 3) else w.capitalize() for w in palabras]
    return " ".join(palabras)

def puntuar_titulo(t):
    s, n, tl = 0, len(t), t.lower()
    if 45 <= n <= 68:
        s += 4
    elif 30 <= n < 45 or 68 < n <= 80:
        s += 2
    elif n > 95 or n < 25:
        s -= 6
    if re.search(r"\d", t):
        s += 2
    s += min(3, sum(1 for g in GANCHOS if g in tl))
    caps = re.findall(r"\b[A-ZÁÉÍÓÚÑ]{4,}\b", t)
    s += 2 if 1 <= len(caps) <= 2 else (-3 if len(caps) > 3 else 0)
    if any(p in tl for p in PROHIBIDAS):
        s -= 8
    if any(tl.startswith(g) for g in GENERICAS):
        s -= 6
    if "!" in t:
        s -= 1
    return s

def elegir_titulo(candidatos):
    puntuados = []
    for c in candidatos:
        if not isinstance(c, str):
            continue
        base = limpiar_titulo(c)
        if len(base) < 25 or titulo_largo_ya_publicado(base):
            continue
        puntuados.append((puntuar_titulo(base), base))
    if not puntuados:
        return None
    puntuados.sort(reverse=True)
    for sc, t in puntuados[:3]:
        print(f"   📝 [{sc:>2}] {t}")
    titulo = puntuados[0][1]
    if "relato" not in titulo.lower() and len(titulo) + len(SUFIJO_TITULO) <= 80:
        titulo += SUFIJO_TITULO
    return titulo[:100]

def elegir_texto_portada(opciones, titulo):
    pt = set(re.findall(r"\w+", titulo.lower()))
    mejor = None
    for o in opciones or []:
        if not isinstance(o, str):
            continue
        o = re.sub(r"[^\w¿?¡! ]", "", o).strip().upper()
        w = o.split()
        if not 1 <= len(w) <= 4:
            continue
        solape = len({x.lower() for x in w} & pt) / len(w)
        sc = (3 if len(w) in (2, 3) else 1) - 2 * solape + (1 if "?" in o else 0)
        if mejor is None or sc > mejor[0]:
            mejor = (sc, o)
    return mejor[1] if mejor else "NO ENTRES"

# ================================================================
# HISTORIA: plan SEO + relato por capítulos
# ================================================================
ESQUEMA_PLAN = """{
 "titulos": ["6 títulos candidatos, cada uno de 45-68 caracteres, SIN el sufijo 'Relato de Terror'"],
 "anio_suceso": 2014,
 "protagonista": "nombre de pila del narrador",
 "gancho": "1-2 frases (máx 35 palabras) que abren el relato en medio de lo más inquietante, en primera persona",
 "resumen": "sinopsis de 2-3 oraciones sin spoilers del final",
 "palabras_clave": ["5 keywords SEO en español"],
 "palabras_portada": ["3 opciones de 2-3 palabras EN MAYÚSCULAS, distintas al título, que provoquen curiosidad"],
 "miniatura_escena": "4-6 palabras en inglés para buscar la foto de portada en un banco de stock (ej: dark hallway door)",
 "descripcion_gancho": "2 líneas: la primera con el keyword principal y una promesa concreta; la segunda invita a suscribirse",
 "titulo_short": "gancho de máx 55 caracteres para un YouTube Short",
 "pregunta_comentario": "pregunta corta que invite a comentar (¿tú qué habrías hecho?)",
 "tags": ["15 tags SEO"],
 "capitulos": [{"titulo": "2-4 palabras con intriga", "resumen": "qué ocurre y qué cliffhanger deja"}]
}"""

def generar_plan(tema, contexto, estado_mx, sugerencias, titulos_previos):
    prev = "\n".join(f"- {t}" for t in titulos_previos) or "Ninguno"
    sug = "\n".join(f"- {s}" for s in sugerencias) or "Ninguna"
    prompt = f"""Eres showrunner de un canal de relatos de terror en español (México/Latam) con millones de vistas.
Diseña el PLAN de un relato de ficción narrado en primera persona (~10-12 minutos, {NUM_CAPITULOS} capítulos).
TEMA: {tema['tema']} | ÁNGULO: {tema['angulo']}
LUGAR: {contexto}, en {estado_mx}, México
BÚSQUEDAS REALES EN YOUTUBE (úsalas de forma natural si encajan en título/descripción/tags):
{sug}
TÍTULOS YA PUBLICADOS (no repetir estructura ni idea):
{prev}
REGLAS DE TÍTULO (clave para CTR):
45-68 caracteres, primera persona o advertencia directa, con un detalle concreto (hora, número, lugar).
Curiosidad sin revelar el final. Solo 1-2 palabras en MAYÚSCULAS.
Ejemplos de estructura: "Trabajé 7 noches de velador y la cámara 4 mostraba algo", "Si oyes tu nombre en la carretera, NO respondas".
PROHIBIDO decir que es real, verídico, testimonio, evidencia o que 'las autoridades ocultan' algo: es ficción.
Nunca empieces con 'El misterio', 'La leyenda', 'Relato' ni 'Caso'.
El gancho debe ser lo más perturbador del relato, no una presentación.
Cada capítulo termina en un cliffhanger, excepto el último.
Responde SOLO con este JSON:
{ESQUEMA_PLAN}"""
    txt = llm(prompt, temperature=0.9, max_tokens=2200, json_mode=True)
    plan = parsear_json(txt)
    # ✅ CORRECCIÓN: Validar dinámicamente según NUM_CAPITULOS
    if not (isinstance(plan.get("titulos"), list) and len(plan["titulos"]) >= 3
            and isinstance(plan.get("capitulos"), list) and len(plan["capitulos"]) >= NUM_CAPITULOS
            and plan.get("gancho") and plan.get("palabras_portada")):
        raise ValueError("plan incompleto")
    return plan

def limpiar_texto_narracion(t):
    t = re.sub(r"[\U00010000-\U0010ffff]", " ", t)
    t = re.sub(r"(?im)^\s*(cap[ií]tulo|parte)\s*\d+.\s*$", " ", t)
    t = re.sub(r"\[[^\]]*\]", " ", t)
    t = re.sub(r"[*_#>`~]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def generar_capitulos(plan, tema, contexto, estado_mx):
    caps = plan["capitulos"][:NUM_CAPITULOS]
    indice = "\n".join(f"{i+1}. {c.get('titulo','')}: {c.get('resumen','')}" for i, c in enumerate(caps))
    textos = []
    for i, cap in enumerate(caps):
        previo = textos[-1][-700:] if textos else ""
        extra = ""
        if i == 0:
            extra = f"Empieza EXACTAMENTE con esta frase de gancho: \"{plan['gancho']}\" y luego retrocede para dar contexto sin bajar la tensión."
        elif i == len(caps) - 1:
            extra = "Cierra con un final abierto e inquietante que deje una duda, sin explicar todo."
        else:
            extra = "Termina con un cliffhanger (algo se revela, alguien aparece, un sonido cambia todo)."
        prompt = f"""Escribe el CAPÍTULO {i+1} de {len(caps)} de un relato de terror en primera persona.
Narrador: {plan.get('protagonista','Marco')}. Año: {plan.get('anio_suceso','2015')}. Lugar: {contexto}, {estado_mx}, México.
Ángulo: {tema['angulo']}
Sinopsis: {plan.get('resumen','')}
ÍNDICE COMPLETO:
{indice}
ESTE CAPÍTULO: {cap.get('titulo','')} -> {cap.get('resumen','')}
{extra}
{('FINAL DEL CAPÍTULO ANTERIOR (continúa sin repetir): ' + previo) if previo else ''}
ESTILO (se leerá en voz alta):
200-250 palabras. Español mexicano natural y coloquial, sin exagerar modismos.
Mezcla frases cortas y secas con otras largas. Detalles sensoriales (sonidos, olores, frío), horas exactas.
Muestra, no expliques. Diálogos breves si ayudan. Sin listas, sin emojis, sin títulos, sin acotaciones, sin marcas de tiempo.
No menciones que es ficción ni que eres una IA.
Devuelve SOLO el texto del capítulo."""
        texto = None
        for intento in range(3):
            t = llm(prompt, temperature=0.85, max_tokens=1200)
            t = limpiar_texto_narracion(t) if t else ""
            if len(t.split()) >= 180:
                texto = t
                break
            print(f"⚠️ Capítulo {i+1} corto ({len(t.split())} pal.), reintento {intento+1}")
        if not texto:
            raise RuntimeError(f"No se pudo generar el capítulo {i+1}")
        textos.append(texto)
        print(f"   ✅ Capítulo {i+1}/{len(caps)}: {len(texto.split())} palabras")
    return textos

# ✅ CORRECCIÓN DE SINTAXIS AQUÍ:
def expandir_texto(titulo, texto_actual):
    prompt = f"""Relato de terror en primera persona: "{titulo}".
Final actual:
"{texto_actual[-500:]}"
Añade 300-400 palabras que profundicen el desenlace (un giro perturbador más), mismo tono, sin resolver todo.
Devuelve SOLO el texto."""
    for _ in range(2):
        t = llm(prompt, temperature=0.8, max_tokens=900)
        t = limpiar_texto_narracion(t) if t else ""
        if len(t.split()) > 150:
            return t
    return ""

OUTROS = [
    "Y hasta aquí llega mi historia. Si te mantuvo despierto, suscríbete y activa la campanita. Cuéntame en los comentarios: ¿tú qué habrías hecho?",
    "Esa fue la historia de hoy. Si llegaste hasta el final, déjame un like y suscríbete para no perderte la próxima. ¿Tú habrías entrado? Te leo en los comentarios.",
]

# ================================================================
# SEGMENTOS, ETAPAS Y ESCENAS
# ================================================================
def dividir_en_segmentos(texto, max_palabras=SEG_MAX_PALABRAS):
    oraciones = [o.strip() for o in re.split(r"(?<=[.!?…])\s+", texto) if o.strip()]
    if not oraciones:
        return [texto]
    segs, actual, cuenta = [], [], 0
    for o in oraciones:
        n = len(o.split())
        if cuenta + n > max_palabras and actual:
            segs.append(" ".join(actual))
            actual, cuenta = [o], n
        else:
            actual.append(o)
            cuenta += n
    if actual:
        segs.append(" ".join(actual))
    if len(segs) > 1 and len(segs[-1].split()) < 12:
        segs[-2] += " " + segs.pop()
    return segs

def crear_segmentos(capitulos_txt):
    segs = []
    for ci, txt in enumerate(capitulos_txt):
        for k, p in enumerate(dividir_en_segmentos(txt)):
            segs.append({"cap": ci, "texto": p, "cap_ini": k == 0})
    n = len(segs)
    for i, s in enumerate(segs):
        p = i / max(n - 1, 1)
        s["etapa"] = ("apertura" if p < 0.15 else "tension" if p < 0.40 else "destino" if p < 0.62
                      else "climax" if p < 0.85 else "resolucion")
    return segs

# ================================================================
# VOZ
# ================================================================
def duracion_audio(ruta):
    a = AudioFileClip(ruta)
    d = a.duration
    a.close()
    return d

def generar_audio(texto, nombre, etapa):
    limpio = re.sub(r'[{}[\]"]', " ", texto)
    limpio = re.sub(r"\s+", " ", limpio).strip()
    if len(limpio) < 10:
        return None
    ruta = f"temp_audio_{nombre}.mp3"
    rate, pitch = RATE_ETAPA.get(etapa, "+4%"), VOZ_CANAL["tono"]
    voces = [VOZ_CANAL["voz"]] + [v for v in VOCES_RESPALDO if v != VOZ_CANAL["voz"]]
    for voz in voces:
        for intento in range(2):
            async def _go():
                await edge_tts.Communicate(limpio, voz, rate=rate, pitch=pitch).save(ruta)
            try:
                asyncio.run(_go())
                if os.path.exists(ruta) and os.path.getsize(ruta) > 500:
                    return ruta
            except Exception as e:
                print(f"❌ TTS {voz}: {e}")
                time.sleep(2 * (intento + 1))
    return None

def sintetizar(segs):
    ok = []
    for i, s in enumerate(segs):
        ruta = generar_audio(s["texto"], s.get("id", i), s["etapa"])
        if not ruta:
            print(f"⚠️ Segmento {i} sin audio, se omite")
            continue
        s["audio"] = ruta
        s["dur_audio"] = duracion_audio(ruta)
        ok.append(s)
        time.sleep(0.3)
    if len(ok) < len(segs) * 0.9:
        raise RuntimeError("Demasiados segmentos sin audio")
    return ok

def construir_timeline(segs):
    t = 0.0
    for s in segs:
        s["inicio"] = t
        s["dur"] = s["dur_audio"] + PAUSA_ETAPA.get(s["etapa"], 0.5)
        t += s["dur"]
    return t

# ================================================================
# PEXELS
# ================================================================
POOL, USADOS = [], set()

def pexels_get(url, params, intentos=3):
    for i in range(intentos):
        try:
            r = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, params=params, timeout=25)
            if r.status_code == 200:
                time.sleep(0.6)
                return r.json()
            if r.status_code == 429:
                time.sleep(25 * (i + 1))
                continue
            print(f"⚠️ Pexels {r.status_code}")
        except Exception as e:
            print(f"⚠️ Pexels: {e}")
            time.sleep(3)
    return None

def buscar_fotos(query, cantidad):
    for pagina in (random.randint(1, 2), 1):
        data = pexels_get("https://api.pexels.com/v1/search",
                          {"query": query, "orientation": "landscape", "size": "large", "per_page": 15, "page": pagina})
        fotos = [f["src"]["large2x"] for f in (data or {}).get("photos", [])]
        random.shuffle(fotos)
        fotos = [u for u in fotos if u not in USADOS]
        if fotos:
            return fotos[:cantidad]
    return []

def buscar_video(query):
    data = pexels_get("https://api.pexels.com/videos/search",
                      {"query": query, "orientation": "landscape", "size": "medium", "per_page": 10})
    vids = (data or {}).get("videos", [])
    random.shuffle(vids)
    for v in vids:
        if v["id"] in USADOS or v.get("duration", 0) < 5:
            continue
        archivos = [f for f in v.get("video_files", [])
                    if f.get("file_type") == "video/mp4" and f.get("width") and 1280 <= f["width"] <= 1920]
        if archivos:
            f = min(archivos, key=lambda x: abs(x["width"] - 1920))
            return v["id"], f["link"]
    return None

def video_valido(ruta):
    try:
        c = VideoFileClip(ruta, audio=False)
        ok = (c.duration or 0) > 2
        c.close()
        return ok
    except Exception:
        return False

def fallback_consultas(tema, etapa):
    return ESCENAS_FALLBACK.get(etapa, ESCENAS_FALLBACK["tension"]) + tema["visuales"]

def planificar_consultas(segs, tema, anio):
    out = [None] * len(segs)
    for ini in range(0, len(segs), 15):
        lote = segs[ini:ini + 15]
        listado = "\n".join(f"{j+1}. {s['texto'][:230]}" for j, s in enumerate(lote))
        prompt = f"""Eres director de fotografía de un canal de terror. Para CADA fragmento numerado devuelve UNA consulta
corta (2-4 palabras, EN INGLÉS) para buscar en Pexels una foto o video de stock que ilustre la escena con atmósfera de
terror nocturno. Usa cosas que existan en bancos de stock (lugares, objetos, clima, siluetas). Sin nombres propios.
Ejemplos: "abandoned hospital corridor", "foggy road night", "old wooden door", "flashlight dark forest".
Tema: {tema['tema']}.
Fragmentos:
{listado}
Responde SOLO JSON: {{"consultas": ["..."]}} con exactamente {len(lote)} elementos."""
        lista = []
        try:
            lista = parsear_json(llm(prompt, 0.4, 700, json_mode=True)).get("consultas", [])
        except Exception as e:
            print(f"⚠️ Consultas de escena: {e}")
        for j, s in enumerate(lote):
            q = lista[j] if j < len(lista) and isinstance(lista[j], str) else ""
            q = " ".join(re.sub(r"[^a-zA-Z ]", " ", q).split()[:5])
            if len(q) < 6:
                q = random.choice(fallback_consultas(tema, s["etapa"]))
            if anio and anio < 2005 and "vintage" not in q:
                q += " vintage"
            out[ini + j] = q
    return out

def obtener_medios(idx, etapa, query, n, tema):
    medios = []
    if USAR_VIDEOS and random.random() < PROB_VIDEO.get(etapa, 0.5):
        r = buscar_video(query)
        if r:
            vid, url = r
            ruta = f"temp_vid_{idx}.mp4"
            if descargar(url, ruta, 70 * 1024 * 1024) and video_valido(ruta):
                USADOS.add(vid)
                medios.append({"tipo": "video", "path": ruta})
    faltan = n - len(medios)
    if faltan > 0:
        urls = buscar_fotos(query, faltan)
        if len(urls) < faltan:
            for q in random.sample(fallback_consultas(tema, etapa), 2):
                urls += [u for u in buscar_fotos(q, faltan - len(urls)) if u not in urls]
        if len(urls) >= faltan:
            pass
        for k, u in enumerate(urls[:faltan]):
            ruta = f"temp_img_{idx}_{k}.jpg"
            if descargar(u, ruta, 15 * 1024 * 1024):
                USADOS.add(u)
                medios.append({"tipo": "img", "path": ruta})
    while len(medios) < n and POOL:
        medios.append(dict(random.choice(POOL)))
    for m in medios:
        if m not in POOL:
            POOL.append(m)
    if not medios:
        raise RuntimeError("Sin imágenes disponibles: revisa PEXELS_API_KEY")
    return medios

# ================================================================
# RENDER DE VIDEO
# ================================================================
_VIG = {}

def vignette(size, base=1.0, fuerza=0.55):
    k = (size, base)
    if k not in _VIG:
        w, h = size
        y, x = np.ogrid[-1:1:h * 1j, -1:1:w * 1j]
        d = np.clip(np.sqrt(x ** 2 + y ** 2) / 1.414, 0, 1)
        _VIG[k] = ((1 - fuerza * d ** 2.2) * base).astype(np.float32)[..., None]
    return _VIG[k]

def grade(img, etapa):
    img = ImageEnhance.Color(img).enhance(0.82)
    img = ImageEnhance.Contrast(img).enhance({"climax": 1.3, "apertura": 1.1}.get(etapa, 1.15))
    img = ImageEnhance.Brightness(img).enhance({"apertura": 0.8, "climax": 0.95}.get(etapa, 0.88))
    return Image.blend(img, Image.new("RGB", img.size, (8, 24, 40)), 0.10)

class RenderEscenas:
    def __init__(self, escenas, size, total):
        self.esc, self.size, self.total = escenas, size, total
        self.starts = [e["inicio"] for e in escenas]
        self._ikey = self._img = self._vpath = self._vid = None
        self.vig_img = vignette(size, 1.0)
        self.vig_vid = vignette(size, 0.85)

    def cerrar(self):
        if self._vid is not None:
            try:
                self._vid.close()
            except Exception:
                pass

    def _base(self, e):
        key = (e["path"], e["etapa"])
        if self._ikey != key:
            sz = (int(self.size[0] * 1.2), int(self.size[1] * 1.2))
            im = ImageOps.fit(Image.open(e["path"]).convert("RGB"), sz, Image.LANCZOS)
            arr = np.asarray(grade(im, e["etapa"]), dtype=np.float32) * vignette(sz, 1.0)
            self._img, self._ikey = Image.fromarray(arr.astype(np.uint8)), key
        return self._img

    def _frame_img(self, e, lt):
        base = self._base(e)
        bw, bh = base.size
        p = min(max(lt / e["dur"], 0), 1) if e["dur"] > 0 else 0
        if not e["zin"]:
            p = 1 - p
        cw = bw / (1 + 0.2 * p)
        ch = cw * bh / bw
        mx, my = bw - cw, bh - ch
        x0 = min(max(mx / 2 + e["ax"] * mx / 2 * 0.8, 0), mx)
        y0 = min(max(my / 2 + e["ay"] * my / 2 * 0.8, 0), my)
        return np.asarray(base.resize(self.size, Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)))

    def _frame_video(self, e, lt):
        if self._vpath != e["path"]:
            self.cerrar()
            self._vid, self._vpath = VideoFileClip(e["path"], audio=False), e["path"]
        v = self._vid
        d = v.duration or 1
        off = e["off"] * max(0, d - e["dur"])
        tt = max(0, min((off + lt) % d, d - 0.05))
        im = ImageOps.fit(Image.fromarray(v.get_frame(tt)), self.size, Image.BILINEAR)
        return (np.asarray(im, dtype=np.float32) * self.vig_vid).astype(np.uint8)

    def frame(self, t):
        i = max(0, bisect.bisect_right(self.starts, t) - 1)
        e = self.esc[i]
        lt = t - e["inicio"]
        fr = self._frame_video(e, lt) if e["tipo"] == "video" else self._frame_img(e, lt)
        f = 1.0
        if e.get("fade") and lt < 0.6:
            f = lt / 0.6
        if t > self.total - 1.5:
            f = min(f, max(0.0, (self.total - t) / 1.5))
        if f < 1.0:
            fr = (fr.astype(np.float32) * f).astype(np.uint8)
        return fr

def construir_escenas(segs):
    esc = []
    for s in segs:
        m = s["medios"]
        d = s["dur"] / len(m)
        for k, med in enumerate(m):
            esc.append({"tipo": med["tipo"], "path": med["path"], "inicio": s["inicio"] + k * d, "dur": d,
                        "etapa": s["etapa"], "fade": bool(k == 0 and s.get("cap_ini")), "off": random.random(),
                        "zin": random.random() < 0.6, "ax": random.uniform(-1, 1), "ay": random.uniform(-1, 1)})
    return esc

def mezclar_audio(segs, total, fondo, extras=()):
    clips = [AudioFileClip(s["audio"]).set_start(s["inicio"]) for s in segs]
    clips += list(extras)
    narr = CompositeAudioClip(clips)
    capas = [narr]
    if fondo and os.path.exists(fondo):
        try:
            bg = AudioFileClip(fondo)
            if bg.duration < total:
                bg = concatenate_audioclips([bg] * (int(total / bg.duration) + 1))
            capas.append(bg.subclip(0, total).volumex(VOL_FONDO).audio_fadein(2).audio_fadeout(3))
        except Exception as e:
            print(f"⚠️ Fondo: {e}")
    return CompositeAudioClip(capas).set_duration(total), clips

def renderizar(escenas, total, audio, size, salida):
    render = RenderEscenas(escenas, size, total)
    video = VideoClip(render.frame, duration=total).set_audio(audio)
    video.write_videofile(salida, fps=FPS, codec="libx264", audio_codec="aac", audio_bitrate="192k", threads=4,
                          preset="veryfast", temp_audiofile="temp_audio_final.m4a",
                          ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart"])
    render.cerrar()
    video.close()
    return salida

# ================================================================
# MINIATURA
# ================================================================
def obtener_fuente(size):
    os.makedirs("fonts", exist_ok=True)
    ruta = "fonts/Anton-Regular.ttf"
    if not os.path.exists(ruta):
        try:
            r = requests.get(FUENTE_URL, timeout=20)
            if r.status_code == 200 and len(r.content) > 20000:
                with open(ruta, "wb") as f:
                    f.write(r.content)
        except Exception:
            pass
    for p in [ruta, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def puntuar_miniatura(ruta):
    try:
        a = np.asarray(Image.open(ruta).convert("L").resize((320, 180)), dtype=np.float32)
        w = a.shape[1]
        return a.std() + 0.5 * a[:, w // 2:].std() - 0.3 * a[:, :w // 2].std() - 0.4 * abs(a.mean() - 90)
    except Exception:
        return -999

def elegir_base_miniatura(query):
    urls = []
    for q in (query, query + " dark", "dark horror night"):
        data = pexels_get("https://api.pexels.com/v1/search",
                          {"query": q, "orientation": "landscape", "size": "large", "per_page": 8, "page": 1})
        urls += [f["src"]["large2x"] for f in (data or {}).get("photos", [])[:6] if f["src"]["large2x"] not in urls]
        if len(urls) >= 6:
            break
    mejor = (-999, None)
    for i, u in enumerate(urls[:6]):
        ruta = f"temp_thumb_{i}.jpg"
        if descargar(u, ruta, 15 * 1024 * 1024):
            sc = puntuar_miniatura(ruta)
            if sc > mejor[0]:
                mejor = (sc, ruta)
    return mejor[1]

def dividir_lineas(palabras):
    if len(palabras) <= 2:
        return palabras[:]
    mejor = None
    for i in range(1, len(palabras)):
        a, b = " ".join(palabras[:i]), " ".join(palabras[i:])
        m = max(len(a), len(b))
        if mejor is None or m < mejor[0]:
            mejor = (m, [a, b])
    return mejor[1]

def crear_miniatura(img_path, texto, salida):
    TW, TH = 1280, 720
    try:
        img = Image.open(img_path).convert("RGB") if img_path else Image.new("RGB", (TW, TH), (14, 14, 24))
        img = ImageOps.fit(img, (TW, TH), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(1.25)
        img = ImageEnhance.Color(img).enhance(1.2)
        img = ImageEnhance.Sharpness(img).enhance(1.6)
        grad = Image.new("L", (TW, TH), 0)
        gd = ImageDraw.Draw(grad)
        for x in range(TW):
            gd.line([(x, 0), (x, TH)], fill=int(215 * max(0, 1 - x / (TW * 0.7)) ** 1.3))
        img = Image.composite(Image.new("RGB", (TW, TH), (0, 0, 0)), img, grad)
        arr = np.asarray(img, dtype=np.float32) * vignette((TW, TH), 1.0, 0.45)
        img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
        lineas = dividir_lineas(texto.upper().split()[:4])
        max_w, max_h = int(TW * 0.58), int(TH * 0.78)
        for size in range(280, 60, -6):
            font = obtener_fuente(size)
            cajas = [font.getbbox(l) for l in lineas]
            alto = sum(b[3] - b[1] for b in cajas) + 18 * (len(lineas) - 1)
            if max(b[2] - b[0] for b in cajas) <= max_w and alto <= max_h:
                break
        acento = random.choice([(255, 214, 0), (255, 45, 45)])
        y = (TH - alto) // 2 + 10
        pos = []
        for l, b in zip(lineas, cajas):
            pos.append((l, 60, y - b[1]))
            y += (b[3] - b[1]) + 18
        glow = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        for l, x, yy in pos:
            gdraw.text((x, yy), l, font=font, fill=acento + (255,), stroke_width=10, stroke_fill=acento + (255,))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(24)))
        draw = ImageDraw.Draw(img)
        borde = max(7, size // 20)
        for i, (l, x, yy) in enumerate(pos):
            color = acento if (i == len(pos) - 1) else (255, 255, 255)
            draw.text((x, yy), l, font=font, fill=color + (255,), stroke_width=borde, stroke_fill=(0, 0, 0, 255))
        rgb = img.convert("RGB")
        for q in (92, 87, 82, 76, 70):
            rgb.save(salida, "JPEG", quality=q, optimize=True)
            if os.path.getsize(salida) < 1_900_000:
                break
        print(f"✅ Miniatura: '{' / '.join(lineas)}' ({size}px)")
        return True
    except Exception as e:
        print(f"❌ Error miniatura: {e}")
        traceback.print_exc()
        return False

# ================================================================
# SEO: descripción, tags, subtítulos
# ================================================================
def construir_tags(plan, tema, sugerencias):
    base = ["relato de terror", "relatos de terror", "historias de terror", "terror", "paranormal", "miedo",
            "creepypasta", "leyendas urbanas", "terror mexicano", "relatos paranormales", "sombras de medianoche"]
    extra = plan.get("tags", [])
    if isinstance(extra, str):
        extra = [x.strip() for x in extra.split(",")]
    finales, total = [], 0
    for t in tema["keywords"] + list(extra) + sugerencias + base:
        t = re.sub(r"[<>]", " ", str(t)).strip().lower()
        costo = len(t) + 1 + (2 if " " in t else 0)
        if 2 <= len(t) <= 40 and t not in finales and total + costo <= 480:
            finales.append(t)
            total += costo
    return finales

def construir_hashtags(tema):
    hs = ["#RelatosDeTerror", "#Terror", "#Paranormal"] + tema.get("hashtags", [])[:2] + ["#Mexico"]
    return " ".join(hs[:6])

def construir_descripcion(plan, tema, caps_ts, sugerencias, hashtags):
    gancho = plan.get("descripcion_gancho", " ").strip() or plan["gancho"]
    if "relato de terror" not in gancho.lower()[:220]:
        gancho = "Relato de terror: " + gancho
    capitulos = "\n".join(f"{ts} {t}" for ts, t in caps_ts)
    rel = ", ".join(sugerencias[:5])
    partes = [
        gancho,
        f"🔔 Suscríbete para un relato nuevo cada semana: {CANAL_LINK}?sub_confirmation=1",
        f"⏰ CAPÍTULOS\n{capitulos}",
        f"📖 SOBRE ESTE RELATO\n{plan.get('resumen','')}",
        (f"🔎 Temas relacionados: {rel}" if rel else " "),
        f"📱 Facebook: {FACEBOOK_LINK}",
        hashtags,
    ]
    desc = "\n\n".join(p for p in partes if p)
    if ACTIVAR_DISCLOSURE_IA:
        desc = desc.replace(f"\n\n{hashtags}", DISCLOSURE_TEXT + f"\n\n{hashtags}")
    return desc[:4900]

def generar_srt(segs, ruta):
    def ts(x):
        h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"
    lineas, n = [], 1
    for s in segs:
        pal = s["texto"].split()
        if not pal:
            continue
        t = s["inicio"]
        for i in range(0, len(pal), 9):
            tr = pal[i:i + 9]
            d = s["dur_audio"] * len(tr) / len(pal)
            lineas.append(f"{n}\n{ts(t)} --> {ts(t + d)}\n{' '.join(tr)}\n")
            n, t = n + 1, t + d
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    return ruta

# ================================================================
# PUBLICACIÓN
# ================================================================
def deberia_publicar(estado):
    ult = estado.get("ultima_publicacion")
    if not ult:
        return True
    try:
        dt = datetime.fromisoformat(ult)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        horas = (datetime.now(TZ) - dt).total_seconds() / 3600
        if horas < INTERVALO_MIN_HORAS:
            print(f"⏸️ Han pasado {horas:.1f}h (mínimo {INTERVALO_MIN_HORAS}h).")
            return False
    except ValueError:
        pass
    return True

def proximo_slot():
    ahora = datetime.now(TZ)
    slot = ahora.replace(hour=HORA_PICO, minute=0, second=0, microsecond=0)
    if slot - ahora < timedelta(minutes=30):
        slot += timedelta(days=1)
    return slot

def utc_iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

# ✅ CORRECCIÓN: Subida robusta con reintentos ante errores de red/SSL
def subir_video(youtube, ruta, titulo, descripcion, tags, publish_at=None):
    status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}
    if publish_at:
        status.update({"privacyStatus": "private", "publishAt": publish_at})
    
    body = {"snippet": {"title": titulo[:100], "description": descripcion[:5000], "tags": tags,
                        "categoryId": "24", "defaultLanguage": "es", "defaultAudioLanguage": "es"},
            "status": status}
    
    # Chunksize reducido a 4MB para mayor estabilidad en redes inestables
    media = MediaFileUpload(ruta, chunksize=4 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    
    resp, reintentos = None, 0
    while resp is None:
        try:
            st, resp = req.next_chunk()
            if st:
                print(f"   ⬆️ {int(st.progress() * 100)}% ")
        except (HttpError, ssl.SSLError, ConnectionError, socket.timeout, OSError) as e:
            es_reintento = False
            if isinstance(e, HttpError) and e.resp.status in (429, 500, 502, 503, 504):
                es_reintento = True
            elif isinstance(e, (ssl.SSLError, ConnectionError, socket.timeout, OSError)):
                es_reintento = True
            
            if es_reintento and reintentos < 8:
                reintentos += 1
                espera = 2 ** reintentos
                print(f"⚠️ Error de red/SSL en la subida (intento {reintentos}/8). Reintentando en {espera}s...")
                time.sleep(espera)
                continue
            
            print(f"❌ Error fatal en la subida: {e}")
            raise
            
    print(f"✅ Video subido: https://youtu.be/{resp['id']}" + (f" (programado {publish_at})" if publish_at else ""))
    return resp["id"]

def extras_post_subida(youtube, vid, miniatura, srt, comentario):
    if miniatura and os.path.exists(miniatura):
        try:
            youtube.thumbnails().set(videoId=vid, media_body=MediaFileUpload(miniatura, mimetype="image/jpeg")).execute()
            print("✅ Miniatura subida")
        except Exception as e:
            print(f"⚠️ Miniatura: {e}")
    if srt and os.path.exists(srt):
        try:
            youtube.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": "es",
                                      "name": "Español", "isDraft": False}},
                                      media_body=MediaFileUpload(srt, mimetype="application/octet-stream")).execute()
            print("✅ Subtítulos subidos")
        except Exception as e:
            print(f"⚠️ Subtítulos (requiere scope youtube.force-ssl): {e}")
    if PLAYLIST_ID:
        try:
            youtube.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": PLAYLIST_ID,
                                         "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
            print("✅ Añadido a playlist")
        except Exception as e:
            print(f"⚠️ Playlist: {e}")
    if comentario:
        try:
            youtube.commentThreads().insert(part="snippet", body={"snippet": {"videoId": vid, "topLevelComment": {
                                "snippet": {"textOriginal": comentario}}}}).execute()
            print("✅ Comentario publicado (fíjalo a mano en Studio)")
        except Exception as e:
            print(f"⚠️ Comentario: {e}\n   Texto sugerido para fijar: {comentario}")

# ================================================================
# SHORT EMBUDO
# ================================================================
def crear_short(segs, plan, fondo, salida="short_final.mp4"):
    sel, t = [], 0.0
    for s in segs:
        if sel and t + s["dur"] > 50:
            break
        sel.append(s)
        t += s["dur"]
        if t >= 32:
            break
    cta = generar_audio("La historia completa ya está en el canal. Suscríbete para no perderte la siguiente.", "cta", "resolucion")
    escenas = construir_escenas(sel)
    extras, total = [], t
    if cta:
        d = duracion_audio(cta)
        extras.append(AudioFileClip(cta).set_start(t))
        ult = escenas[-1]
        escenas.append({**ult, "inicio": t, "dur": d + 0.6, "fade": False})
        total = t + d + 0.6
    audio, _ = mezclar_audio(sel, total, fondo, extras)
    renderizar(escenas, total, audio, (1080, 1920), salida)
    return salida

# ================================================================
# MÚSICA DE FONDO
# ================================================================
def buscar_archivo(nombre):
    for root, _, files in os.walk("."):
        if "/." in root or "\\." in root:
            continue
        if nombre in files:
            return os.path.join(root, nombre)
    return None

def seleccionar_fondo(estado):
    ultimos = estado["ultimos_fondos"]
    disp = [f for f in FONDOS_DISPONIBLES if f not in ultimos[-3:]] or FONDOS_DISPONIBLES[:]
    random.shuffle(disp)
    for f in disp + FONDOS_DISPONIBLES:
        ruta = buscar_archivo(f)
        if ruta:
            estado["ultimos_fondos"] = (ultimos + [f])[-10:]
            print(f"🎵 Fondo: {ruta}")
            return ruta
    print("⚠️ Sin música de fondo")
    return None

# ================================================================
# LIMPIEZA Y VALIDACIONES
# ================================================================
def limpiar_temporales():
    for f in os.listdir("."):
        if f.startswith("temp_") or f in ("video_final.mp4", "short_final.mp4", "miniatura.jpg", "subtitulos.srt"):
            try:
                os.remove(f)
            except OSError:
                pass

def verificar_envs():
    faltan = [v for v in ("DEEPSEEK_API_KEY", "PEXELS_API_KEY", "YOUTUBE_USER_TOKEN") if not os.getenv(v)]
    if faltan:
        print(f"❌ Faltan variables: {', '.join(faltan)}")
        sys.exit(1)
    r = requests.get("https://api.pexels.com/v1/search?query=test&per_page=1",
                     headers={"Authorization": PEXELS_API_KEY}, timeout=10)
    if r.status_code != 200:
        print(f"❌ PEXELS_API_KEY inválida ({r.status_code})")
        sys.exit(1)

# ================================================================
# MAIN
# ================================================================
def main():
    verificar_envs()
    limpiar_temporales()
    estado = cargar_estado()
    if os.getenv("FORCE_PUBLISH") == "true":
        print("⚡ FORCE_PUBLISH activo")
    elif not deberia_publicar(estado):
        sys.exit(0)
    
    print("=" * 70)
    print("👻 SOMBRAS DE MEDIANOCHE - BOT v3 (CORREGIDO)")
    print(f"📅 {datetime.now(TZ):%Y-%m-%d %H:%M} | 🎤 {VOZ_CANAL['voz']} | 🎬 videos Pexels: {USAR_VIDEOS}")
    print("=" * 70)
    
    youtube = crear_cliente_youtube()
    actualizar_rendimiento(youtube, estado)
    tema = elegir_tema(estado, youtube)
    contexto, estado_mx = random.choice(tema["contextos"]), random.choice(ESTADOS_MEXICO)
    sugerencias = list(dict.fromkeys(sugerencias_youtube(tema["seed"]) +
                                     sugerencias_youtube("relato de terror " + tema["keywords"][0])))[:10]
    print(f"🔎 Sugerencias YouTube: {sugerencias[:5]}")
    fondo = seleccionar_fondo(estado)
    
    # ---- Plan + título
    titulos_previos = cargar_json(TITULOS_LARGOS_FILE, {"titulos": []})["titulos"][-20:]
    plan = titulo = None
    for intento in range(4):
        try:
            plan = generar_plan(tema, contexto, estado_mx, sugerencias, titulos_previos)
            if plan.get("palabras_clave") and tema_ya_usado(" ".join(map(str, plan["palabras_clave"]))):
                raise ValueError("tema repetido")
            titulo = elegir_titulo(plan["titulos"])
            if not titulo:
                raise ValueError("sin título válido")
            break
        except Exception as e:
            print(f"⚠️ Plan intento {intento+1}/4: {e}")
            plan = None
            time.sleep(5)
    if not plan:
        print("❌ No se pudo generar un plan válido.")
        sys.exit(1)
        
    try:
        anio = int(plan.get("anio_suceso"))
    except (TypeError, ValueError):
        anio = None
    print(f"🔥 Título: {titulo}")
    
    # ---- Relato
    capitulos_txt = generar_capitulos(plan, tema, contexto, estado_mx)
    n_caps = len(capitulos_txt)
    segs = crear_segmentos(capitulos_txt)
    print(f"🧩 {len(segs)} segmentos, {sum(len(c.split()) for c in capitulos_txt)} palabras")
    
    # ---- Voz + expansión si hace falta
    segs = sintetizar(segs)
    total = construir_timeline(segs)
    
    # ✅ CORRECCIÓN: Bucle de expansión con tope máximo
    intentos = 0
    while total < DURACION_MINIMA_SEGUNDOS and intentos < MAX_INTENTOS_EXPANSION:
        print(f"⚠️ {total/60:.1f} min < mínimo. Expandiendo ({intentos+1})...")
        extra = expandir_texto(titulo, " ".join(s["texto"] for s in segs))
        intentos += 1
        if not extra:
            break
        nuevos = [{"cap": n_caps - 1, "texto": p, "cap_ini": False, "etapa": "resolucion", "id": f"x{intentos}_{k}"}
                  for k, p in enumerate(dividir_en_segmentos(extra))]
        segs += sintetizar(nuevos)
        total = construir_timeline(segs)
        
        if total > DURACION_MAXIMA_SEGUNDOS:
            print(f"⚠️ Duración {total/60:.1f} min excede el máximo. Deteniendo expansión.")
            break

    # ✅ CORRECCIÓN: Truncado limpio si se pasa del máximo
    if total > DURACION_MAXIMA_SEGUNDOS:
        print(f"⚠️ Ajustando duración final a {DURACION_MAXIMA_SEGUNDOS/60:.1f} min...")
        segs_truncados = []
        tiempo_acumulado = 0
        for s in segs:
            if tiempo_acumulado + s["dur"] <= DURACION_MAXIMA_SEGUNDOS:
                segs_truncados.append(s)
                tiempo_acumulado += s["dur"]
            else:
                break
        segs = segs_truncados
        total = construir_timeline(segs)
        print(f"✅ Duración ajustada a {total/60:.1f} min")

    outro = [{"cap": n_caps - 1, "texto": random.choice(OUTROS), "cap_ini": False, "etapa": "resolucion", "id": "outro", "outro": True}]
    segs += sintetizar(outro)
    total = construir_timeline(segs)
    print(f"⏱️ Duración: {total/60:.1f} min")
    
    # ---- Escenas (Pexels)
    consultas = planificar_consultas(segs, tema, anio)
    for i, s in enumerate(segs):
        n = max(1, round(s["dur"] / SEG_ESCENA))
        print(f"🖼️ {i+1}/{len(segs)} [{s['etapa']}] '{consultas[i]}' x{n}")
        s["medios"] = obtener_medios(i, s["etapa"], consultas[i], n, tema)
        
    # ---- Capítulos con timestamps REALES
    caps_ts = []
    for c in range(n_caps):
        primero = next((s for s in segs if s["cap"] == c), None)
        nombre = str(plan["capitulos"][c].get("titulo", f"Parte {c+1}"))[:50] if c < len(plan["capitulos"]) else f"Parte {c+1}"
        if primero:
            caps_ts.append((fmt_ts(primero["inicio"]), nombre))
    caps_ts[0] = ("00:00", caps_ts[0][1])
    
    hashtags = construir_hashtags(tema)
    descripcion = construir_descripcion(plan, tema, caps_ts, sugerencias, hashtags)
    tags = construir_tags(plan, tema, sugerencias)
    srt = generar_srt(segs, "subtitulos.srt")
    
    # ---- Miniatura
    portada = elegir_texto_portada(plan.get("palabras_portada"), titulo)
    base = elegir_base_miniatura(re.sub(r"[^a-zA-Z ]", " ", str(plan.get("miniatura_escena", "dark hallway door"))) or "dark hallway door")
    miniatura = "miniatura.jpg" if crear_miniatura(base, portada, "miniatura.jpg") else None
    
    # ---- Render y subida
    escenas = construir_escenas(segs)
    audio, _ = mezclar_audio(segs, total, fondo)
    print("🎬 Renderizando video largo...")
    renderizar(escenas, total, audio, (W, H), "video_final.mp4")
    
    slot = proximo_slot() if PROGRAMAR_PICO else None
    print(f"🕖 Programación: {slot:%Y-%m-%d %H:%M} CDMX" if slot else "🕖 Publicación inmediata")
    
    vid = subir_video(youtube, "video_final.mp4", titulo, descripcion, tags, utc_iso(slot) if slot else None)
    comentario = str(plan.get("pregunta_comentario") or "¿Tú qué habrías hecho? Te leo 👇")
    extras_post_subida(youtube, vid, miniatura, srt, comentario)
    
    if GENERAR_SHORT:
        try:
            print("📱 Creando Short embudo...")
            crear_short(segs, plan, fondo)
            t_short = str(plan.get("titulo_short") or titulo)[:88] + " #Shorts"
            d_short = (f"Historia completa 👉 https://youtu.be/{vid}\n\nSuscríbete: {CANAL_LINK}?sub_confirmation=1\n\n"
                       f"#Shorts {hashtags}" + (DISCLOSURE_TEXT if ACTIVAR_DISCLOSURE_IA else ""))
            slot_s = utc_iso(slot + timedelta(minutes=30)) if slot else None
            subir_video(youtube, "short_final.mp4", t_short, d_short, tags[:15] + ["shorts"], slot_s)
        except Exception as e:
            print(f"⚠️ Short falló (el video largo ya está subido): {e}")
            traceback.print_exc()
            
    # ---- Estado
    ahora = datetime.now(TZ).isoformat()
    guardar_titulo_largo(titulo)
    guardar_tema(" ".join(map(str, plan.get("palabras_clave", []))) or tema["tema"])
    estado["videos"].append({"id": vid, "titulo": titulo, "tema": tema["tema"], "fecha": ahora})
    estado["videos"] = estado["videos"][-60:]
    estado["temas_recientes"] = (estado["temas_recientes"] + [tema["tema"]])[-6:]
    estado["ultima_publicacion"] = ahora
    estado["ultima_publicacion_exitosa"] = datetime.now(TZ).date().isoformat()
    guardar_json(MUSICA_ESTADO_FILE, estado)
    
    limpiar_temporales()
    print("🎉 Proceso completado.")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        traceback.print_exc()
        sys.exit(1)
