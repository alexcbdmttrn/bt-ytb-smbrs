# -*- coding: utf-8 -*-
import asyncio, bisect, json, os, random, re, sys, time, traceback, unicodedata, ssl, socket
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import edge_tts, numpy as np, requests, urllib3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from moviepy.editor import AudioFileClip, CompositeAudioClip, VideoClip, VideoFileClip, concatenate_audioclips
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
try: import json5
except ImportError: json5 = None
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= CONFIGURACIÓN =================
TZ = ZoneInfo("America/Mexico_City")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
YOUTUBE_USER_TOKEN = json.loads(os.getenv("YOUTUBE_USER_TOKEN") or "{}")
PLAYLIST_ID = os.getenv("YOUTUBE_PLAYLIST_ID", "")
FACEBOOK_LINK = "https://www.facebook.com/profile.php?id=61593237382982"
CANAL_LINK = "https://www.youtube.com/@sombrasdemedianocheoficial"
EMAIL_CONTACTO = os.getenv("EMAIL_CONTACTO", "sombras.contacto@gmail.com")
MUSICA_ESTADO_FILE = "estado_musica.json"
TITULOS_LARGOS_FILE = "titulos_largos_publicados.json"
TEMAS_SHORTS_FILE = "temas_shorts.json"
DURACION_MINIMA_SEGUNDOS = 480
DURACION_MAXIMA_SEGUNDOS = 720
MAX_INTENTOS_EXPANSION = 3
NUM_CAPITULOS = 4 
SEG_MAX_PALABRAS = 55
SEG_ESCENA = 18.0
W, H, FPS = 1920, 1080, 24
VOL_FONDO = 0.10
USAR_VIDEOS = os.getenv("USAR_VIDEOS", "true").lower() == "true"
GENERAR_SHORT = os.getenv("GENERAR_SHORT", "false").lower() == "true"
PROGRAMAR_PICO = os.getenv("PROGRAMAR_PICO", "true").lower() == "true"
HORA_PICO = int(os.getenv("HORA_PICO", "19"))
INTERVALO_MIN_HORAS = float(os.getenv("INTERVALO_MIN_HORAS", "48"))
ACTIVAR_DISCLOSURE_IA = True
OUTLIERS_FILE = "outliers_cache_sombras.json"
UNIFORME_FILE = "uniforme_cache_sombras.json"
PERFIL_LOCK_MIN_VISTAS = int(os.getenv("PERFIL_LOCK_MIN_VISTAS", "500"))
PERFIL_LOCK_VIDEOS = int(os.getenv("PERFIL_LOCK_VIDEOS", "5"))
OUTLIER_MAX_SUBS = int(os.getenv("OUTLIER_MAX_SUBS", "50000"))
OUTLIER_MIN_RATIO = float(os.getenv("OUTLIER_MIN_RATIO", "3.5"))
OUTLIER_CACHE_HORAS = int(os.getenv("OUTLIER_CACHE_HORAS", "24"))

FONT_URLS = [
    "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf",
    "https://raw.githubusercontent.com/google/fonts/main/ofl/oswald/Oswald-Bold.ttf",
    "https://raw.githubusercontent.com/google/fonts/main/ofl/bebasneue/BebasNeue-Regular.ttf",
    "https://raw.githubusercontent.com/google/fonts/main/ofl/righteous/Righteous-Regular.ttf"
]

IDENTIDAD_VISUAL = {"estilos_rotacion": ["miedo_rojo", "advertencia_amarillo", "misterio_blanco", "shock_cyan", "secreto_naranja"]}
DISCLOSURE_TEXT = f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📢 CONTENIDO CON ASISTENCIA DE IA\n\nEste relato fue creado con asistencia de Inteligencia Artificial:\n\n• Guion: generado con IA, revisado y editado por el equipo\n• Narración: voz sintética neural\n• Imágenes: material de archivo y recursos libres de regalías\n• Edición: automatizada con supervisión humana\n\n🎯 PROPÓSITO: Entretener y preservar el folclor de terror mexicano.\n⚠️ Este contenido es ficción narrativa con fines de entretenimiento.\nNo pretende ser un testimonio real ni sustituir asesoría profesional.\n\n📧 Contacto: {EMAIL_CONTACTO}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
VOCES_ROTACION = [
    {"voz": "es-MX-JorgeNeural", "estilo": "narrativo_masculino"}, {"voz": "es-MX-DaliaNeural", "estilo": "narrativo_femenino"},
    {"voz": "es-ES-AlvaroNeural", "estilo": "dramatico_es"}, {"voz": "es-MX-ManuelNeural", "estilo": "conversacional"},
    {"voz": "es-CO-GonzaloNeural", "estilo": "suspenso_colombiano"}, {"voz": "es-US-AlonsoNeural", "estilo": "rapido_neutro"},
    {"voz": "es-AR-TomasNeural", "estilo": "argentino_intenso"}, {"voz": "es-MX-DaliaNeural", "estilo": "susurro_femenino"},
    {"voz": "es-ES-ElviraNeural", "estilo": "femenino_es"}, {"voz": "es-CL-LorenzoNeural", "estilo": "chileno_narrador"}
]
VOZ_CANAL = {"voz": "es-MX-JorgeNeural", "tono": "-4Hz", "rate": "+6%"}
VOCES_RESPALDO = ["es-MX-JorgeNeural", "es-ES-AlvaroNeural", "es-CO-GonzaloNeural", "es-US-AlonsoNeural"]
RATE_ETAPA = {"apertura": "+6%", "tension": "+6%", "destino": "+4%", "climax": "-2%", "resolucion": "+2%"}
PAUSA_ETAPA = {"apertura": 0.5, "tension": 0.45, "destino": 0.5, "climax": 0.75, "resolucion": 0.6}
PROB_VIDEO = {"apertura": 0.5, "tension": 0.5, "destino": 0.6, "climax": 0.5, "resolucion": 0.4}
FUENTE_URL = FONT_URLS[0]
FONDOS_DISPONIBLES = ["Ash and Marrow.mp3", "Black Maw.mp3", "Cold Hollow.mp3", "Hollow Marrow.mp3", "Sunken Dread.mp3", "Sunless Vault.mp3", "The Deep Rot.mp3"]
ESTADOS_MEXICO = ["Aguascalientes", "Baja California", "Campeche", "Chiapas", "Chihuahua", "Coahuila", "Colima", "Durango", "Estado de México", "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas"]

# ================= TEMAS (42) =================
TEMAS = [
{"tema": "skinwalker", "seed": "skinwalker relatos", "angulo": "Algo imita voces humanas y te sigue por el bosque; cada noche se acerca más.", "keywords": ["skinwalker", "criatura", "bosque"], "contextos": ["carretera solitaria", "bosque profundo", "sierra aislada", "desierto"], "visuales": ["dark forest fog", "desert road night", "mountain night", "eyes in the dark"], "hashtags": ["#Skinwalker"]},
{"tema": "duendes", "seed": "duendes historia real", "angulo": "Objetos que desaparecen, risas en la madrugada, y un niño que habla con alguien que no está.", "keywords": ["duendes", "casa", "travesuras"], "contextos": ["casa del pueblo", "rancho", "bosque cercano", "milpa"], "visuales": ["old mexican house night", "dark forest small figure", "rustic mexican ranch"], "hashtags": ["#Duendes"]},
{"tema": "aluxes", "seed": "aluxes mayas terror", "angulo": "Los guardianes mayas de la milpa cobran venganza cuando alguien invade su territorio.", "keywords": ["aluxes", "mayas", "milpa"], "contextos": ["milpa yucateca", "ruinas mayas", "cenote", "selva"], "visuales": ["mayan ruins night", "jungle fog night", "cenote dark water"], "hashtags": ["#Aluxes"]},
{"tema": "chupacabras", "seed": "chupacabras avistamiento", "angulo": "Los animales aparecen sin sangre y el rancho entero escucha algo en el monte.", "keywords": ["chupacabras", "ganado", "rancho"], "contextos": ["rancho ganadero", "monte", "sierra", "desierto"], "visuales": ["mexican ranch night", "dead livestock field", "mountain silhouette creature"], "hashtags": ["#Chupacabras"]},
{"tema": "nahual", "seed": "nahual historia terror", "angulo": "Un vecino del pueblo puede convertirse en animal; tú lo viste cambiar.", "keywords": ["nahual", "brujo", "animal"], "contextos": ["pueblo viejo", "cerro", "camino de tierra", "casa del brujo"], "visuales": ["mexican village night", "dirt road night fog", "coyote eyes dark"], "hashtags": ["#Nahual"]},
{"tema": "llorona", "seed": "la llorona historia", "angulo": "El llanto de una mujer en el río anuncia la muerte de alguien del pueblo.", "keywords": ["llorona", "río", "llanto"], "contextos": ["río del pueblo", "panteón", "puente viejo", "camino a la iglesia"], "visuales": ["mexican river night fog", "old bridge night", "woman silhouette river"], "hashtags": ["#LaLlorona"]},
{"tema": "charro_negro", "seed": "charro negro leyenda", "angulo": "Un jinete vestido de negro ofrece dinero en el camino; pagar el precio es perder el alma.", "keywords": ["charro negro", "jinete", "diablo"], "contextos": ["camino de terracería", "carretera solitaria", "encrucijada"], "visuales": ["dark horseman silhouette", "dusty road night", "crossroads night mexico"], "hashtags": ["#CharroNegro"]},
{"tema": "vampiro", "seed": "vampiro historia terror", "angulo": "Un vecino nunca sale de día, no come en las reuniones, y las noches del pueblo hay gente que amanece pálida.", "keywords": ["vampiro", "colmillos", "sangre"], "contextos": ["casa del pueblo", "hacienda vieja", "casona abandonada"], "visuales": ["castle night fog", "dark coffin candle", "bat silhouette moon"], "hashtags": ["#Vampiros"]},
{"tema": "hombre_lobo", "seed": "hombre lobo historia real", "angulo": "En cada luna llena el cerro aúlla, el ganado aparece destrozado, y un vecino desaparece por tres días.", "keywords": ["hombre lobo", "luna llena", "cerro"], "contextos": ["rancho", "cerro", "bosque profundo", "sierra"], "visuales": ["full moon forest night", "wolf silhouette dark", "torn livestock field"], "hashtags": ["#HombreLobo"]},
{"tema": "fantasmas", "seed": "fantasmas casa historia", "angulo": "En la casa hay alguien más: mueve cosas, apaga luces, y a veces se deja ver.", "keywords": ["fantasmas", "aparecidos", "casa"], "contextos": ["casa antigua", "departamento", "casa heredada", "edificio viejo"], "visuales": ["dark hallway ghost shadow", "old house interior night", "door half open dark"], "hashtags": ["#Fantasmas"]},
{"tema": "demonios", "seed": "demonios invocación historia", "angulo": "Algo responde cuando no debieron llamar; no es un espíritu, es algo mucho peor.", "keywords": ["demonios", "invocación", "posesión"], "contextos": ["casa abandonada", "sótano", "iglesia abandonada", "cementerio"], "visuales": ["dark basement horror", "abandoned church night", "candles dark room"], "hashtags": ["#Demonios"]},
{"tema": "brujas", "seed": "brujas historia terror", "angulo": "Una mujer del pueblo sabe demasiado; la gente la evita, y los que no, desaparecen.", "keywords": ["brujas", "hechicería", "pueblo"], "contextos": ["casa al final del pueblo", "cerro", "mercado", "cueva"], "visuales": ["old mexican woman dark", "candles ritual night", "abandoned shack night"], "hashtags": ["#Brujas"]},
{"tema": "brujos", "seed": "brujo trabajo magia negra", "angulo": "Le pidieron un trabajo de magia negra; ahora el cliente no puede escapar de lo que pidió.", "keywords": ["brujos", "magia negra", "trabajo"], "contextos": ["casa del brujo", "mercado esotérico", "cementerio de noche"], "visuales": ["dark altar candles", "old esoteric shop night", "ritual circle dark"], "hashtags": ["#MagiaNegra"]},
{"tema": "poltergeist", "seed": "poltergeist casa real", "angulo": "Los objetos se mueven solos, las puertas se azotan, y la actividad aumenta cada noche.", "keywords": ["poltergeist", "objetos", "casa"], "contextos": ["casa familiar", "departamento", "casa de la infancia", "ático"], "visuales": ["objects flying room dark", "thrown furniture room night", "slammed door dark"], "hashtags": ["#Poltergeist"]},
{"tema": "muneca_poseida", "seed": "muñeca poseída historia", "angulo": "La muñeca cambia de posición sola y empieza a aparecer en los sueños de la familia.", "keywords": ["muñeca", "poseída", "maldita"], "contextos": ["casa antigua", "cuarto de niña", "ático", "tienda de antigüedades"], "visuales": ["creepy doll dark room", "old doll chair night", "doll face closeup dark"], "hashtags": ["#MuñecaMaldita"]},
{"tema": "payaso_maldito", "seed": "payaso maldito historia", "angulo": "Un payaso aparece en el mismo lugar cada noche; nadie lo contrató.", "keywords": ["payaso", "maldito", "aparición"], "contextos": ["circo abandonado", "parque", "calle solitaria", "feria"], "visuales": ["creepy clown dark", "abandoned circus night", "clown silhouette fog"], "hashtags": ["#PayasoMaldito"]},
{"tema": "casa_embrujada", "seed": "casa embrujada historia real", "angulo": "La casa nueva tiene historia; los vecinos hablan de la familia anterior y nadie quiere entrar.", "keywords": ["casa embrujada", "aparición", "familia"], "contextos": ["casa antigua", "casa de campo", "casa heredada"], "visuales": ["abandoned mexican house night", "haunted house fog", "dark house interior hallway"], "hashtags": ["#CasaEmbrujada"]},
{"tema": "hospital", "seed": "hospital terror historia", "angulo": "En la guardia nocturna, un paciente que ya no debería existir sigue apareciendo en el mismo pasillo.", "keywords": ["hospital", "paciente", "morgue"], "contextos": ["hospital viejo", "clínica cerrada", "ala clausurada", "morgue"], "visuales": ["hospital corridor dark", "abandoned hospital", "morgue dark"], "hashtags": ["#HospitalEmbrujado"]},
{"tema": "velador", "seed": "trabajé de velador terror", "angulo": "Turno nocturno de vigilante; las cámaras muestran algo que no está en el pasillo real.", "keywords": ["velador", "turno de noche", "cámaras"], "contextos": ["fábrica abandonada", "bodega", "escuela vacía", "estacionamiento"], "visuales": ["security guard night", "empty factory night", "cctv camera"], "hashtags": ["#Velador"]},
{"tema": "carretera", "seed": "carretera de noche terror", "angulo": "Un viaje nocturno con un pasajero que no recuerda haber subido, o una parada que nadie debió hacer.", "keywords": ["carretera", "viaje nocturno", "taxi"], "contextos": ["carretera federal", "gasolinera", "túnel", "desvío"], "visuales": ["highway night fog", "taxi night city", "road tunnel dark"], "hashtags": ["#CarreteraMaldita"]},
{"tema": "hotel_embrujado", "seed": "hotel embrujado historia", "angulo": "En el hotel hay habitaciones que no deberían estar en el mapa, y un huésped que nunca se fue.", "keywords": ["hotel", "habitación", "huésped"], "contextos": ["hotel viejo", "motel de carretera", "hostal", "hotel de pueblo"], "visuales": ["hotel corridor dark", "old hotel room night", "motel neon night"], "hashtags": ["#HotelEmbrujado"]},
{"tema": "cementerio", "seed": "cementerio noche terror", "angulo": "Algo se mueve entre las tumbas; los que se quedan hasta tarde escuchan rezos que nadie reza.", "keywords": ["cementerio", "panteón", "tumba"], "contextos": ["panteón del pueblo", "cementerio antiguo", "cripta", "mausoleo"], "visuales": ["cemetery night fog", "old mexican pantheon", "crypt candles dark"], "hashtags": ["#Cementerio"]},
{"tema": "bosque_maldito", "seed": "bosque maldito terror", "angulo": "Los que entran al bosque no salen iguales; algunos no salen, y otros vuelven cambiados.", "keywords": ["bosque", "maldito", "perdido"], "contextos": ["bosque profundo", "sierra", "montaña", "cabaña"], "visuales": ["dark forest fog night", "cabin in woods night", "tall trees silhouette"], "hashtags": ["#BosqueMaldito"]},
{"tema": "mina_abandonada", "seed": "mina abandonada terror", "angulo": "En la mina cerrada hubo un accidente; los que bajaron después escucharon golpes desde dentro.", "keywords": ["mina", "abandonada", "túnel"], "contextos": ["mina abandonada", "túnel", "cerro", "pueblo minero"], "visuales": ["abandoned mine entrance", "mine tunnel dark", "mine shaft night"], "hashtags": ["#MinaAbandonada"]},
{"tema": "hacienda", "seed": "hacienda embrujada historia", "angulo": "La hacienda vieja guarda lo que pasó con los dueños anteriores; los nuevos no duermen igual.", "keywords": ["hacienda", "embrujada", "historia"], "contextos": ["hacienda vieja", "ex-hacienda", "rancho heredado", "casona"], "visuales": ["old hacienda night", "colonial house dark", "courtyard night dark"], "hashtags": ["#HaciendaEmbrujada"]},
{"tema": "zona_secreta", "seed": "zona secreta mexico", "angulo": "Hay una zona en el mapa donde el GPS falla, los locales no entran, y quien lo hace regresa distinto.", "keywords": ["zona secreta", "desapariciones", "prohibida"], "contextos": ["zona militar abandonada", "cerro con antenas", "pueblo fantasma"], "visuales": ["restricted area sign night", "abandoned military base", "fence warning night"], "hashtags": ["#ZonaSecreta"]},
{"tema": "ritual", "seed": "ritual prohibido historia", "angulo": "Un ritual hecho por curiosidad abre algo que no se puede cerrar.", "keywords": ["ritual", "invocación", "ocultismo"], "contextos": ["cementerio antiguo", "casa abandonada", "cueva", "sótano"], "visuales": ["candles dark room", "old cemetery night", "cave darkness"], "hashtags": ["#Rituales"]},
{"tema": "ouija", "seed": "ouija historia terror", "angulo": "Algo respondió en la tabla; desde esa noche, no dejó de responder.", "keywords": ["ouija", "tabla", "espíritus"], "contextos": ["casa de amigo", "cuarto oscuro", "sótano", "habitación de hotel"], "visuales": ["ouija board candles", "dark room hands", "seance circle dark"], "hashtags": ["#Ouija"]},
{"tema": "posesion", "seed": "posesión demoníaca historia", "angulo": "Alguien de la familia cambió; habla en otra lengua, no duerme, y sabe cosas que no debería.", "keywords": ["posesión", "demonio", "familia"], "contextos": ["casa familiar", "habitación", "iglesia", "convento"], "visuales": ["dark bedroom horror", "candlelit church interior", "shadow figure bed"], "hashtags": ["#Posesión"]},
{"tema": "exorcismo", "seed": "exorcismo real historia", "angulo": "El sacerdote accedió a hacer el exorcismo; lo que salió del cuerpo no era humano.", "keywords": ["exorcismo", "sacerdote", "demonio"], "contextos": ["iglesia vieja", "casa del pueblo", "convento abandonado", "capilla"], "visuales": ["candlelit church dark", "priest silhouette", "rosary candle dark"], "hashtags": ["#Exorcismo"]},
{"tema": "pacto_demonio", "seed": "pacto con el diablo historia", "angulo": "Alguien hizo un pacto por dinero o poder; ahora el precio se está cobrando.", "keywords": ["pacto", "demonio", "trato"], "contextos": ["encrucijada", "casa abandonada", "camino solitario", "cementerio"], "visuales": ["crossroads night dark", "candles pentagram dark", "old contract candle"], "hashtags": ["#Pacto"]},
{"tema": "maldicion", "seed": "maldición familiar historia", "angulo": "La familia carga una maldición de generaciones; cada cierto tiempo, cobra una vida.", "keywords": ["maldición", "familia", "tragedia"], "contextos": ["casa familiar", "pueblo", "cementerio", "hacienda"], "visuales": ["old family photo dark", "abandoned house interior", "old diary pages"], "hashtags": ["#Maldición"]},
{"tema": "objeto_maldito", "seed": "objeto maldito historia", "angulo": "Un objeto comprado barato trae reglas silenciosas y consecuencias cada noche.", "keywords": ["objeto maldito", "antigüedad", "tianguis"], "contextos": ["tienda de antigüedades", "mercado de pulgas", "casa heredada"], "visuales": ["antique shop", "old doll", "old mirror dark"], "hashtags": ["#ObjetoMaldito"]},
{"tema": "espejo_maldito", "seed": "espejo maldito historia", "angulo": "En el espejo hay alguien más; refleja cosas que no están en la habitación.", "keywords": ["espejo", "reflejo", "aparición"], "contextos": ["casa antigua", "baño", "recámara", "hotel"], "visuales": ["old mirror dark room", "cracked mirror dark", "bathroom mirror fog dark"], "hashtags": ["#EspejoMaldito"]},
{"tema": "santero", "seed": "santero trabajo espiritual", "angulo": "Le pidieron un trabajo espiritual; lo que llegó no era lo que esperaban.", "keywords": ["santero", "trabajo", "espiritual"], "contextos": ["casa del santero", "mercado esotérico", "cementerio", "altar"], "visuales": ["dark altar candles bones", "esoteric shop night", "skull candle dark"], "hashtags": ["#Santería"]},
{"tema": "curandero", "seed": "curandero limpia terror", "angulo": "La limpia espiritual debía quitarle el mal; el mal se quedó, y algo más entró.", "keywords": ["curandero", "limpia", "energía"], "contextos": ["casa del curandero", "mercado", "pueblo", "temazcal"], "visuales": ["herbs hanging dark", "smoke ritual dark", "candles eggs limpia"], "hashtags": ["#Curanderos"]},
{"tema": "aliens", "seed": "avistamiento ovni historia", "angulo": "Lo que bajó del cielo no era un avión; la luz se movió como algo vivo.", "keywords": ["ovni", "extraterrestre", "luces"], "contextos": ["campo abierto", "carretera solitaria", "sierra", "rancho"], "visuales": ["ufo lights sky night", "strange light rural night", "silhouette hill ufo"], "hashtags": ["#Ovnis"]},
{"tema": "abduccion", "seed": "abducción extraterrestre historia", "angulo": "Recuerdas fragmentos: luces, frialdad, voces; y una marca que no estaba antes.", "keywords": ["abducción", "extraterrestre", "marca"], "contextos": ["casa de campo", "carretera", "rancho", "montaña"], "visuales": ["bright light sky night", "car headlights ufo", "strange marks skin"], "hashtags": ["#Abducción"]},
{"tema": "encuentro_cercano", "seed": "encuentro cercano extraterrestre", "angulo": "El encuentro fue cercano; el ser que salió del objeto habló sin mover la boca.", "keywords": ["encuentro", "extraterrestre", "ser"], "contextos": ["camino rural", "campo", "sierra", "mina abandonada"], "visuales": ["ufo landed field night", "strange silhouette fog", "alien figure dark"], "hashtags": ["#EncuentroCercano"]},
{"tema": "implante_alien", "seed": "implante extraterrestre historia", "angulo": "Tienes una marca que no recuerdas, un implante que los médicos no saben explicar, y algo que se mueve dentro.", "keywords": ["implante", "extraterrestre", "marca"], "contextos": ["casa de campo", "rancho", "hospital rural", "habitación"], "visuales": ["strange scar skin dark", "medical xray strange", "glowing skin mark"], "hashtags": ["#ImplanteAlien"]},
{"tema": "leyenda_mexicana", "seed": "leyenda mexicana terror", "angulo": "Una leyenda del pueblo cobra vida en versión contemporánea.", "keywords": ["leyendas mexicanas", "pueblo"], "contextos": ["pueblo antiguo", "río de noche", "panteón del pueblo"], "visuales": ["old village night", "colonial church night", "dirt road night"], "hashtags": ["#LeyendasMexicanas"]},
{"tema": "creepypasta", "seed": "creepypasta relato", "angulo": "Una leyenda de internet resulta tener un origen físico y cercano.", "keywords": ["creepypasta", "leyenda urbana", "barrio"], "contextos": ["parque abandonado", "calle solitaria", "bosque nocturno"], "visuales": ["dark forest night", "abandoned playground", "empty street night"], "hashtags": ["#Creepypasta"]}
]

ESCENAS_FALLBACK = {
    "apertura": ["dark hallway night", "old house interior dark", "flickering light bulb", "lonely street night"],
    "tension": ["foggy road night", "empty highway night", "car headlights fog", "dark forest path"],
    "destino": ["abandoned building", "creepy old house", "dark forest fog", "abandoned corridor"],
    "climax": ["shadow figure dark", "scary dark room", "flashlight darkness", "silhouette door light"],
    "resolucion": ["sunrise fog road", "dawn empty street", "morning mist forest", "walking away silhouette dawn"],
}

# ================= UTILIDADES =================
def _chunks(lst, n):
    for i in range(0, len(lst), n): yield lst[i:i + n]

def cargar_json(ruta, default):
    try:
        with open(ruta, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def guardar_json(ruta, data):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, ruta)

def cargar_estado():
    estado = cargar_json(MUSICA_ESTADO_FILE, {})
    if "ultimo_fondo" in estado and "ultimos_fondos" not in estado: estado["ultimos_fondos"] = [estado.pop("ultimo_fondo")]
    estado.setdefault("ultimos_fondos", []); estado.setdefault("videos", []); estado.setdefault("temas_recientes", [])
    return estado

def parsear_json(texto):
    if not texto: raise ValueError("respuesta vacía")
    t = re.sub(r"```(?:json)?", " ", texto, flags=re.I)
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1: raise ValueError("sin JSON")
    t = re.sub(r",\s*([}\]])", r"\1", t[i:j + 1])
    if json5:
        try: return json5.loads(t)
        except Exception: pass
    return json.loads(t, strict=False)

def llm(prompt, temperature=0.8, max_tokens=1500, json_mode=False, system=None, intentos=3):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    payload = {"model": DEEPSEEK_MODEL, "messages": msgs, "temperature": temperature, "max_tokens": max_tokens}
    if json_mode: payload["response_format"] = {"type": "json_object"}
    for i in range(intentos):
        try:
            r = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=150)
            r.raise_for_status(); return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"⚠️ LLM intento {i+1}/{intentos}: {e}"); time.sleep(5 * (i + 1))
    return None

def descargar(url, ruta, max_bytes=20 * 1024 * 1024):
    try:
        with requests.get(url, stream=True, timeout=40) as r:
            r.raise_for_status(); total = 0
            with open(ruta, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    total += len(chunk)
                    if total > max_bytes: raise ValueError("grande")
                    f.write(chunk)
            return os.path.getsize(ruta) > 1000
    except Exception as e:
        print(f"⚠️ Descarga: {e}")
        if os.path.exists(ruta): os.remove(ruta)
        return False

def fmt_ts(seg):
    seg = int(seg); h, m, s = seg // 3600, seg % 3600 // 60, seg % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

# ================= HISTORIAL Y YOUTUBE =================
def titulo_largo_ya_publicado(titulo):
    data = cargar_json(TITULOS_LARGOS_FILE, {"titulos": []})
    n = titulo.lower().strip(); p1 = set(re.findall(r"\w+", n))
    for t in data["titulos"]:
        tn = t.lower().strip(); p2 = set(re.findall(r"\w+", tn))
        if n == tn or (len(p1) > 3 and len(p2) > 3 and len(p1 & p2) / min(len(p1), len(p2)) > 0.7): return True
    return False

def titulo_empieza_igual(titulo):
    data = cargar_json(TITULOS_LARGOS_FILE, {"titulos": []})
    primeras3 = titulo.lower().split()[:3]
    for t in data["titulos"][-15:]:
        if t.lower().split()[:3] == primeras3: return True
    return False

def guardar_titulo_largo(titulo):
    data = cargar_json(TITULOS_LARGOS_FILE, {"titulos": []})
    if titulo not in data["titulos"]: data["titulos"].append(titulo)
    data["titulos"] = data["titulos"][-100:]; guardar_json(TITULOS_LARGOS_FILE, data)

def tema_ya_usado(tema, umbral=0.5):
    data = cargar_json(TEMAS_SHORTS_FILE, {"temas": []})
    nuevas = set(re.findall(r"\w+", str(tema).lower()))
    for antiguo in data["temas"][-20:]:
        if isinstance(antiguo, dict): antiguo = antiguo.get("tema", "")
        if not isinstance(antiguo, str) or len(antiguo) > 80: continue
        viejas = set(re.findall(r"\w+", antiguo.lower())); union = nuevas | viejas
        if union and len(nuevas & viejas) / len(union) > umbral: return True
    return False

def guardar_tema(tema):
    data = cargar_json(TEMAS_SHORTS_FILE, {"temas": []})
    data["temas"] = [t for t in data["temas"] if isinstance(t, str) and len(t) < 80]
    if isinstance(tema, str) and len(tema) < 80 and tema not in data["temas"]: data["temas"].append(tema)
    data["temas"] = data["temas"][-20:]; guardar_json(TEMAS_SHORTS_FILE, data)

def crear_cliente_youtube():
    try: return build("youtube", "v3", credentials=Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN))
    except Exception as e: print(f"⚠️ YouTube cliente: {e}"); return None

def sugerencias_youtube(seed):
    try:
        r = requests.get("https://suggestqueries.google.com/complete/search", timeout=10, params={"client": "firefox", "ds": "yt", "hl": "es", "gl": "mx", "q": seed})
        return [s for s in r.json()[1] if isinstance(s, str)][:8]
    except Exception: return []

def actualizar_rendimiento(youtube, estado):
    ids = [v["id"] for v in estado["videos"][-30:] if v.get("id")]
    if not ids or youtube is None: return
    try:
        r = youtube.videos().list(part="statistics", id=",".join(ids)).execute()
        vistas = {i["id"]: int(i["statistics"].get("viewCount", 0)) for i in r.get("items", [])}
        for v in estado["videos"]:
            if v.get("id") in vistas: v["vistas"] = vistas[v["id"]]
    except Exception: pass

def detectar_outliers(youtube, keyword, max_subs=OUTLIER_MAX_SUBS, min_ratio=OUTLIER_MIN_RATIO, days=180, cache_h=OUTLIER_CACHE_HORAS):
    if youtube is None: return []
    cache = cargar_json(OUTLIERS_FILE, {})
    key = f"{keyword}|{max_subs}|{min_ratio}"
    if key in cache and (time.time() - cache[key].get("ts", 0)) < cache_h * 3600: return cache[key]["items"]
    try:
        desde = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        s = youtube.search().list(part="id,snippet", q=keyword, type="video", order="viewCount", publishedAfter=desde, relevanceLanguage="es", regionCode="MX", maxResults=25).execute()
        vids = [i["id"]["videoId"] for i in s.get("items", [])]
        if not vids: return []
        
        v_resp = youtube.videos().list(part="statistics,snippet", id=",".join(vids)).execute()
        ch_ids, rows = set(), []
        for v in v_resp.get("items", []):
            ch = v["snippet"]["channelId"]; ch_ids.add(ch)
            vistas = int(v["statistics"].get("viewCount", 0))
            likes = int(v["statistics"].get("likeCount", 0))
            
            # V9.2 ENGAGED VIEWS FILTER: Si tiene mas de 1000 vistas y menos del 1% de likes, es vista inflada (TV)
            if vistas > 1000 and (likes / vistas) < 0.01:
                continue
                
            rows.append({"video_id": v["id"], "title": v["snippet"]["title"], "channel_id": ch, "channel_title": v["snippet"]["channelTitle"], "views": vistas})
            
        subs_map = {}
        for chunk in _chunks(list(ch_ids), 50):
            c = youtube.channels().list(part="statistics", id=",".join(chunk)).execute()
            for item in c.get("items", []): subs_map[item["id"]] = int(item["statistics"].get("subscriberCount", 0))
        out = []
        for r in rows:
            subs = subs_map.get(r["channel_id"], 0)
            if subs == 0 or subs > max_subs: continue
            ratio = r["views"] / max(subs, 1)
            if ratio >= min_ratio: out.append({**r, "subs": subs, "ratio": round(ratio, 1)})
        out.sort(key=lambda x: x["ratio"], reverse=True); out = out[:8]
        cache[key] = {"ts": time.time(), "items": out}; guardar_json(OUTLIERS_FILE, cache)
        return out
    except Exception: return []

def cruzar_temas(tema_original, outlier):
    prompt = f"Estratega de YouTube. Cruza estos temas para un video de terror.\nTEMA: {tema_original['tema']} | ÁNGULO: {tema_original['angulo']}\nOUTLIER: {outlier['title']} ({outlier['views']} vistas)\nReglas: UN video, buscable, conserva nicho, sugiere ELEMENTO IMPOSIBLE.\nSOLO JSON: {{\"tema\":\"slug\",\"angulo\":\"...\",\"keywords\":[\"k1\",\"k2\",\"k3\",\"k4\",\"k5\"], \"elemento_imposible_sugerido\":\"...\"}}"
    try:
        txt = llm(prompt, temperature=0.9, max_tokens=600, json_mode=True); d = parsear_json(txt)
        if d.get("tema") and d.get("angulo") and d.get("keywords"): return d
    except Exception: pass
    return None

def elegir_tema(estado, youtube):
    recientes = estado["temas_recientes"][-6:]; pool = [t for t in TEMAS if t["tema"] not in recientes] or TEMAS[:]
    candidatos = random.sample(pool, min(5, len(pool))); outliers_map = {}; scores = {}
    for t in candidatos:
        o = detectar_outliers(youtube, t["seed"]); outliers_map[t["tema"]] = o; scores[t["tema"]] = sum(x["ratio"] for x in o)
    acum = {}
    for v in estado["videos"]:
        if "vistas" in v: acum.setdefault(v["tema"], []).append(v["vistas"])
    rend = {k: sum(x) / len(x) for k, x in acum.items()}; max_r = max(rend.values()) if rend else 1; max_o = max(scores.values()) if any(scores.values()) else 1
    def final_score(t):
        o = scores[t["tema"]] / max_o if max_o else 0; r = rend.get(t["tema"], 0) / max_r if max_r else 0
        return 0.6 * o + 0.3 * r + random.uniform(0, 0.15)
    elegido = max(candidatos, key=final_score)
    outs = outliers_map.get(elegido["tema"], [])
    if outs:
        refinado = cruzar_temas(elegido, outs[0])
        if refinado:
            return {"tema": refinado["tema"], "seed": refinado["tema"].replace("_", " "), "angulo": refinado["angulo"], "keywords": refinado["keywords"][:5], "contextos": elegido["contextos"], "hashtags": elegido["hashtags"], "visuales": elegido["visuales"], "elemento_imposible_hint": refinado.get("elemento_imposible_sugerido", "")}
    return elegido

# ================= TÍTULOS Y PLAN =================
GANCHOS = ["nunca", "nadie", "jamás", "solo", "prohibido", "secreto", "escuché", "vi ", "descubrí", "encontré", "sobreviví", "trabajé", "entré", "confieso", "recuerdo", "desapareció", "apareció", "cambió", "por qué", "cómo", "noche", "oscuridad"]
PROHIBIDAS = ["testimonio real", "caso real", "100% real", "verídico", "evidencia", "pruebas", "autoridades", "filtrado"]
GENERICAS = ["misterio", "leyenda", "relato", "caso", "historia de terror"]
SIGLAS_INTOCABLES = {"ADN", "ARN", "NASA", "ONU", "IA", "EEUU", "COVID", "VIH", "SIDA", "OVNI", "PIB", "UE", "OMS", "POV", "TDAH", "OCD", "IQ", "CI", "FGR", "CIA", "FBI", "DEA", "DNI", "GPS", "CCTV", "USB", "LED", "RIP"}

def limpiar_titulo(t):
    t = t.strip().strip('"').strip("'"); t = re.sub(r"\s+", " ", t); t = re.sub(r"\s*[-|–]\s*relato de terror\s*$", "", t, flags=re.I).rstrip(".")
    palabras = t.split(); caps = [w for w in palabras if len(re.sub(r"\W", " ", w)) >= 3 and w.isupper() and w not in SIGLAS_INTOCABLES]
    if len(caps) > 3:
        keep = set(caps[:2]) | SIGLAS_INTOCABLES; palabras = [w if (not w.isupper() or w in keep or len(w) < 3) else w.capitalize() for w in palabras]
    return " ".join(palabras)

def puntuar_titulo(t):
    s, n, tl = 0, len(t), t.lower()
    if 45 <= n <= 68: s += 6
    elif 40 <= n < 45 or 68 < n <= 75: s += 4
    elif 30 <= n < 40 or 75 < n <= 80: s += 2
    elif n > 95 or n < 25: s -= 8
    else: s -= 2
    s += min(8, sum(1 for g in GANCHOS if g in tl) * 2)
    if re.search(r"\d", t): s += 3
    if any(p in tl for p in PROHIBIDAS): s -= 8
    if any(tl.startswith(g) for g in GENERICAS): s -= 6
    return s

def elegir_titulo(candidatos):
    puntuados = []
    for c in candidatos:
        if not isinstance(c, str): continue
        base = limpiar_titulo(c)
        if len(base) < 25 or titulo_largo_ya_publicado(base) or titulo_empieza_igual(base): continue
        puntuados.append((puntuar_titulo(base), base))
    if not puntuados: return None
    puntuados.sort(reverse=True); return puntuados[0][1][:100]

def elegir_texto_portada(opciones, titulo):
    pt = set(re.findall(r"\w+", titulo.lower())); mejor = None
    fallbacks = ["NO SUBAS", "PROHIBIDO", "EL SECRETO", "NO ENTRES", "OCULTAN", "NO MIRES", "PELIGRO", "CUIDADO", "ALERTA"]
    for o in opciones or []:
        if not isinstance(o, str): continue
        o = re.sub(r"[^\w¿?¡! ]", "", o).strip().upper(); w = o.split()
        if not 1 <= len(w) <= 4: continue
        solape = len({x.lower() for x in w} & pt) / len(w)
        sc = (3 if len(w) in (2, 3) else 1) - 2 * solape + (1 if "?" in o else 0)
        if any(x in o for x in ["SECRETO", "PROHIBIDO", "NADIE", "OCULTAN"]): sc += 5
        if mejor is None or sc > mejor[0]: mejor = (sc, o)
    return mejor[1] if mejor else random.choice(fallbacks)

ESQUEMA_PLAN = "{\n \"titulos\": [\"8 títulos de 45-68 caracteres. CADA TÍTULO DEBE TENER UNA ESTRUCTURA SINTÁCTICA COMPLETAMENTE DISTINTA.\"],\n \"anio_suceso\": 2014, \"protagonista\": \"nombre\", \"elemento_imposible\": \"detalle\", \"gancho\": \"1-2 frases\",\n \"resumen\": \"sinopsis\", \"palabras_clave\": [\"5 keywords SEO\"], \"palabras_portada\": [\"3 opciones MAYÚSCULAS\"],\n \"miniatura_escena\": \"4-6 palabras inglés\", \"descripcion_gancho\": \"2 líneas\", \"titulo_short\": \"máx 55 caracteres\",\n \"pregunta_comentario\": \"pregunta\", \"tags\": [\"15 tags\"], \"capitulos\": [{\"titulo\": \"2-4 palabras\", \"resumen\": \"qué pasa\"}]\n}"

def generar_plan(tema, contexto, estado_mx, sugerencias, titulos_previos, formato_narracion=None, perfil_narrador=None):
    prev = "\n".join(f"- {t}" for t in titulos_previos) or "Ninguno"; sug  = "\n".join(f"- {s}" for s in sugerencias) or "Ninguna"
    hint = tema.get("elemento_imposible_hint", "")
    if formato_narracion is None: formato_narracion = FORMATOS_NARRACION[0]
    if perfil_narrador is None: perfil_narrador = "persona común"
    prompt = f"Eres showrunner de TERROR. Guion de ~8-12 min, {NUM_CAPITULOS} capítulos.\nTEMA: {tema['tema']} | ÁNGULO: {tema['angulo']} | LUGAR: {contexto}, {estado_mx}.\n{hint}\nFORMATO: {formato_narracion['nombre'].upper()} {formato_narracion['instruccion']}\nPERFIL: {perfil_narrador}\nBÚSQUEDAS: {sug}\nTÍTULOS YA PUBLICADOS: {prev}\nREGLA ESTRICTA: Genera 8 títulos. NO REPITAS ESTRUCTURAS.\nSOLO JSON: {ESQUEMA_PLAN}"
    txt = llm(prompt, temperature=0.95, max_tokens=2400, json_mode=True); plan = parsear_json(txt)
    if not (isinstance(plan.get("titulos"), list) and len(plan["titulos"]) >= 3 and isinstance(plan.get("capitulos"), list) and len(plan["capitulos"]) >= NUM_CAPITULOS and plan.get("gancho") and plan.get("palabras_portada") and plan.get("elemento_imposible")): raise ValueError("plan incompleto")
    return plan

def limpiar_texto_narracion(t):
    t = re.sub(r"[\U00010000-\U0010ffff]", " ", t); t = re.sub(r"(?im)^\s*(cap[ií]tulo|parte)\s*\d+.\s*$", " ", t); t = re.sub(r"\[[^\]]*\]", " ", t); t = re.sub(r"[*_#>`~]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def generar_capitulos(plan, tema, contexto, estado_mx):
    caps = plan["capitulos"][:NUM_CAPITULOS]; indice = "\n".join(f"{i+1}. {c.get('titulo','')}: {c.get('resumen','')}" for i, c in enumerate(caps)); textos = []
    formato_instruccion = plan.get("_formato_instruccion", "Primera persona."); perfil_narrador = plan.get("_perfil_narrador", "común")
    nombre_formato = plan.get("_nombre_formato", "primera_persona"); elemento_imposible = plan.get("elemento_imposible", "detalle")
    for i, cap in enumerate(caps):
        previo = textos[-1][-700:] if textos else ""
        extra = f"Empieza con: \"{plan['gancho']}\" e INTEGRA '{elemento_imposible}'." if i == 0 else (f"Cierra con final abierto. Menciona '{elemento_imposible}'." if i == len(caps) - 1 else f"Cliffhanger. Menciona '{elemento_imposible}'.")
        formato_cap = f"ENTRADA DE DIARIO 'Día {i*3+1}'." if nombre_formato == "diario" else f"Mantén formato {nombre_formato}."
        prompt = f"CAPÍTULO {i+1}/{len(caps)} de documental de terror.\nFORMATO: {nombre_formato.upper()} {formato_instruccion} {formato_cap}\nNARRADOR: {plan.get('protagonista', 'Marco')} — {perfil_narrador}\nLUGAR: {contexto}, {estado_mx} | ÁNGULO: {tema['angulo']}\nELEMENTO: \"{elemento_imposible}\"\nÍNDICE: {indice}\nESTE CAP: {cap.get('titulo', '')} → {cap.get('resumen', '')}\n{extra}\nFINAL ANTERIOR: {previo}\nREGLAS: EXACTAMENTE 300-400 palabras por capítulo. Español mexicano. MÁXIMO TERROR CONCRETO. SHOWING. SOLO texto."
        texto = None
        for intento in range(3):
            t = llm(prompt, temperature=0.85, max_tokens=1000); t = limpiar_texto_narracion(t) if t else ""
            if len(t.split()) >= 280: texto = t; break
            elif len(t.split()) >= 200 and intento == 2: texto = t; break
        if not texto: raise RuntimeError(f"Error cap {i+1}")
        textos.append(texto); print(f"   ✅ Cap {i+1}/{len(caps)}: {len(texto.split())} pal.")
    return textos

def expandir_texto(titulo, texto_actual, ronda=1):
    cantidad = 400 if ronda == 1 else 300
    prompt = f'Relato: "{titulo}". Final actual:\n"""\n{texto_actual[-800:]}\n"""\nAñade EXACTAMENTE {cantidad} palabras que profundicen el desenlace con un giro perturbador adicional. Mismo tono, mismo narrador, mismo lugar. NO resuelvas todo. NO repitas lo ya dicho. SOLO el texto nuevo.'
    for _ in range(2):
        t = llm(prompt, temperature=0.8, max_tokens=1200); t = limpiar_texto_narracion(t) if t else ""
        if len(t.split()) > 250: return t
    return ""

OUTROS = ["Y hasta aquí llega mi historia. Si te mantuvo despierto, suscríbete y activa la campanita. Cuéntame: ¿tú qué habrías hecho?", "Esa fue la historia de hoy. Si llegaste hasta el final, déjame un like y suscríbete. ¿Tú habrías entrado? Te leo."]
FORMATOS_NARRACION = [{"nombre": "primera_persona", "instruccion": "Primera persona directa."}, {"nombre": "confesion", "instruccion": "Confesión urgente."}, {"nombre": "carta_mensaje", "instruccion": "Carta/mensaje."}, {"nombre": "diario", "instruccion": "Diario con fechas."}, {"nombre": "testigo", "instruccion": "Testigo cuenta lo de otro."}]
PERFILES_NARRADOR = ["velador", "conductor nocturno", "médico de guardia", "ama de casa", "turista", "jornalero", "estudiante", "taxista", "mecánico", "maestro rural", "obrero", "fotógrafo", "cuidador", "comerciante", "bombero"]

def generar_avatar_audiencia(plan, tema): return None
def bloquear_perfil(estado, formato, perfil, vid): return True

# ================= SEGMENTOS Y AUDIO =================
def dividir_en_segmentos(texto, max_palabras=SEG_MAX_PALABRAS):
    oraciones = [o.strip() for o in re.split(r"(?<=[.!?…])\s+", texto) if o.strip()]
    if not oraciones: return [texto]
    segs, actual, cuenta = [], [], 0
    for o in oraciones:
        n = len(o.split())
        if cuenta + n > max_palabras and actual: segs.append(" ".join(actual)); actual, cuenta = [o], n
        else: actual.append(o); cuenta += n
    if actual: segs.append(" ".join(actual))
    if len(segs) > 1 and len(segs[-1].split()) < 12: segs[-2] += " " + segs.pop()
    return segs

def crear_segmentos(capitulos_txt):
    segs = []
    for ci, txt in enumerate(capitulos_txt):
        for k, p in enumerate(dividir_en_segmentos(txt)): segs.append({"cap": ci, "texto": p, "cap_ini": k == 0})
    n = len(segs)
    for i, s in enumerate(segs):
        p = i / max(n - 1, 1)
        s["etapa"] = ("apertura" if p < 0.15 else "tension" if p < 0.40 else "destino" if p < 0.62 else "climax" if p < 0.85 else "resolucion")
    return segs

def duracion_audio(ruta):
    a = AudioFileClip(ruta); d = a.duration; a.close(); return d

def generar_audio(texto, nombre, etapa):
    limpio = re.sub(r'[{}[\]"]', " ", texto); limpio = re.sub(r"\s+", " ", limpio).strip()
    if len(limpio) < 10: return None
    ruta = f"temp_audio_{nombre}.mp3"; rate = RATE_ETAPA.get(etapa, "+4%"); pitch = VOZ_CANAL.get("tono", "-4Hz")
    voces = [VOZ_CANAL["voz"]] + [v for v in VOCES_RESPALDO if v != VOZ_CANAL["voz"]]
    for voz in voces:
        for intento in range(2):
            async def _go():
                communicate = edge_tts.Communicate(limpio, voz, rate=rate, pitch=pitch); await communicate.save(ruta)
            try:
                asyncio.run(_go())
                if os.path.exists(ruta) and os.path.getsize(ruta) > 500: return ruta
            except Exception: time.sleep(2)
    try:
        from gtts import gTTS
        gTTS(text=limpio, lang="es", slow=False).save(ruta)
        if os.path.exists(ruta) and os.path.getsize(ruta) > 500: return ruta
    except Exception: pass
    return None

def sintetizar(segs):
    ok = []
    for i, s in enumerate(segs):
        ruta = generar_audio(s["texto"], s.get("id", i), s["etapa"])
        if not ruta: print(f"⚠️ Seg {i} sin audio"); continue
        s["audio"] = ruta; s["dur_audio"] = duracion_audio(ruta); ok.append(s); time.sleep(0.3)
    if len(ok) < len(segs) * 0.9: raise RuntimeError("Faltan audios")
    return ok

def construir_timeline(segs):
    t = 0.0
    for s in segs: s["inicio"] = t; s["dur"] = s["dur_audio"] + PAUSA_ETAPA.get(s["etapa"], 0.5); t += s["dur"]
    return t

# ================= PEXELS Y RENDER =================
POOL, USADOS = [], set()

def pexels_get(url, params, intentos=3):
    for i in range(intentos):
        try:
            r = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, params=params, timeout=25)
            if r.status_code == 200: time.sleep(0.6); return r.json()
            if r.status_code == 429: time.sleep(25 * (i + 1))
        except Exception: time.sleep(3)
    return None

def buscar_fotos(query, cantidad):
    for pagina in (random.randint(1, 2), 1):
        data = pexels_get("https://api.pexels.com/v1/search", {"query": query, "orientation": "landscape", "size": "large", "per_page": 15, "page": pagina})
        fotos = [f["src"]["large2x"] for f in (data or {}).get("photos", [])]; random.shuffle(fotos); fotos = [u for u in fotos if u not in USADOS]
        if fotos: return fotos[:cantidad]
    return []

def buscar_video(query):
    data = pexels_get("https://api.pexels.com/videos/search", {"query": query, "orientation": "landscape", "size": "medium", "per_page": 10})
    vids = (data or {}).get("videos", []); random.shuffle(vids)
    for v in vids:
        if v["id"] in USADOS or v.get("duration", 0) < 5: continue
        archivos = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width") and 1280 <= f["width"] <= 1920]
        if archivos: return v["id"], min(archivos, key=lambda x: abs(x["width"] - 1920))["link"]
    return None

def video_valido(ruta):
    try: c = VideoFileClip(ruta, audio=False); ok = (c.duration or 0) > 2; c.close(); return ok
    except Exception: return False

def fallback_consultas(tema, etapa):
    return ESCENAS_FALLBACK.get(etapa, ESCENAS_FALLBACK["tension"]) + tema["visuales"]

def planificar_consultas(segs, tema, anio):
    out = [None] * len(segs)
    for ini in range(0, len(segs), 15):
        lote = segs[ini:ini + 15]; listado = "\n".join(f"{j+1}. {s['texto'][:230]}" for j, s in enumerate(lote))
        prompt = f"Director de fotografía de terror. Devuelve 1 consulta corta EN INGLÉS (2-5 palabras) por fragmento. Tema: {tema['tema']}. Fragmentos:\n{listado}\nSOLO JSON: {{\"consultas\": [\"...\"]}} con {len(lote)} elementos."
        lista = []
        try: lista = parsear_json(llm(prompt, 0.4, 700, json_mode=True)).get("consultas", [])
        except Exception: pass
        for j, s in enumerate(lote):
            q = lista[j] if j < len(lista) and isinstance(lista[j], str) else ""; q = " ".join(re.sub(r"[^a-zA-Z ]", " ", q).split()[:5])
            if len(q) < 6: q = random.choice(fallback_consultas(tema, s["etapa"]))
            if anio and anio < 2005 and "vintage" not in q: q += " vintage"
            out[ini + j] = q
    return out

def obtener_medios(idx, etapa, query, n, tema):
    medios = []
    if USAR_VIDEOS and random.random() < PROB_VIDEO.get(etapa, 0.5):
        r = buscar_video(query)
        if r:
            vid, url = r; ruta = f"temp_vid_{idx}.mp4"
            if descargar(url, ruta, 70 * 1024 * 1024) and video_valido(ruta): USADOS.add(vid); medios.append({"tipo": "video", "path": ruta})
    faltan = n - len(medios)
    if faltan > 0:
        urls = buscar_fotos(query, faltan)
        if len(urls) < faltan:
            for q in random.sample(fallback_consultas(tema, etapa), 2): urls += [u for u in buscar_fotos(q, faltan - len(urls)) if u not in urls]
        for k, u in enumerate(urls[:faltan]):
            ruta = f"temp_img_{idx}_{k}.jpg"
            if descargar(u, ruta, 15 * 1024 * 1024): USADOS.add(u); medios.append({"tipo": "img", "path": ruta})
    while len(medios) < n and POOL: medios.append(dict(random.choice(POOL)))
    for m in medios:
        if m not in POOL: POOL.append(m)
    if not medios: raise RuntimeError("Sin media")
    return medios

_VIG = {}
def vignette(size, base=1.0, fuerza=0.55):
    k = (size, base)
    if k not in _VIG:
        w, h = size; y, x = np.ogrid[-1:1:h * 1j, -1:1:w * 1j]; d = np.clip(np.sqrt(x ** 2 + y ** 2) / 1.414, 0, 1)
        _VIG[k] = ((1 - fuerza * d ** 2.2) * base).astype(np.float32)[..., None]
    return _VIG[k]

def grade(img, etapa):
    img = ImageEnhance.Color(img).enhance(0.82); img = ImageEnhance.Contrast(img).enhance({"climax": 1.3, "apertura": 1.1}.get(etapa, 1.15)); img = ImageEnhance.Brightness(img).enhance({"apertura": 0.8, "climax": 0.95}.get(etapa, 0.88))
    return Image.blend(img, Image.new("RGB", img.size, (8, 24, 40)), 0.10)

class RenderEscenas:
    def __init__(self, escenas, size, total):
        self.esc, self.size, self.total = escenas, size, total; self.starts = [e["inicio"] for e in escenas]
        self._ikey = self._img = self._vpath = self._vid = None; self.vig_vid = vignette(size, 0.85)
    def cerrar(self):
        if self._vid is not None:
            try: self._vid.close()
            except Exception: pass
    def _base(self, e):
        key = (e["path"], e["etapa"])
        if self._ikey != key:
            sz = (int(self.size[0] * 1.2), int(self.size[1] * 1.2)); im = ImageOps.fit(Image.open(e["path"]).convert("RGB"), sz, Image.LANCZOS)
            arr = np.asarray(grade(im, e["etapa"]), dtype=np.float32) * vignette(sz, 1.0); self._img, self._ikey = Image.fromarray(arr.astype(np.uint8)), key
        return self._img
    def _frame_img(self, e, lt):
        base = self._base(e); bw, bh = base.size; p = min(max(lt / e["dur"], 0), 1) if e["dur"] > 0 else 0
        if not e["zin"]: p = 1 - p
        cw = bw / (1 + 0.2 * p); ch = cw * bh / bw; mx, my = bw - cw, bh - ch
        x0 = min(max(mx / 2 + e["ax"] * mx / 2 * 0.8, 0), mx); y0 = min(max(my / 2 + e["ay"] * my / 2 * 0.8, 0), my)
        return np.asarray(base.resize(self.size, Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch)))
    def _frame_video(self, e, lt):
        if self._vpath != e["path"]: self.cerrar(); self._vid, self._vpath = VideoFileClip(e["path"], audio=False), e["path"]
        v = self._vid; d = v.duration or 1; off = e["off"] * max(0, d - e["dur"]); tt = max(0, min((off + lt) % d, d - 0.05))
        im = ImageOps.fit(Image.fromarray(v.get_frame(tt)), self.size, Image.BILINEAR)
        return (np.asarray(im, dtype=np.float32) * self.vig_vid).astype(np.uint8)
    def frame(self, t):
        i = max(0, bisect.bisect_right(self.starts, t) - 1); e = self.esc[i]; lt = t - e["inicio"]
        fr = self._frame_video(e, lt) if e["tipo"] == "video" else self._frame_img(e, lt); f = 1.0
        if e.get("fade") and lt < 0.6: f = lt / 0.6
        if t > self.total - 1.5: f = min(f, max(0.0, (self.total - t) / 1.5))
        if f < 1.0: fr = (fr.astype(np.float32) * f).astype(np.uint8)
        return fr

def construir_escenas(segs):
    esc = []
    for s in segs:
        m = s["medios"]; d = s["dur"] / len(m)
        for k, med in enumerate(m):
            esc.append({"tipo": med["tipo"], "path": med["path"], "inicio": s["inicio"] + k * d, "dur": d, "etapa": s["etapa"], "fade": bool(k == 0 and s.get("cap_ini")), "off": random.random(), "zin": random.random() < 0.6, "ax": random.uniform(-1, 1), "ay": random.uniform(-1, 1)})
    return esc

def mezclar_audio(segs, total, fondo, extras=()):
    clips = [AudioFileClip(s["audio"]).set_start(s["inicio"]) for s in segs] + list(extras); narr = CompositeAudioClip(clips); capas = [narr]
    if fondo and os.path.exists(fondo):
        try:
            bg = AudioFileClip(fondo); bg = concatenate_audioclips([bg] * (int(total / bg.duration) + 1)) if bg.duration < total else bg
            capas.append(bg.subclip(0, total).volumex(VOL_FONDO).audio_fadein(2).audio_fadeout(3))
        except Exception: pass
    return CompositeAudioClip(capas).set_duration(total), clips

def generar_overlay_disclosure(size=(W, H)):
    img = Image.new("RGBA", size, (0, 0, 0, 0)); draw = ImageDraw.Draw(img); texto = "CONTENIDO CON ASISTENCIA DE IA"
    try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except Exception: font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), texto, font=font); ancho = bbox[2] - bbox[0]
    x = (size[0] - ancho) // 2; y = size[1] - 100
    draw.rectangle([x - 20, y - 10, x + ancho + 20, y + 45], fill=(0, 0, 0, 180)); draw.text((x, y), texto, font=font, fill=(255, 220, 0, 255))
    ruta = "temp_overlay_ia.png"; img.save(ruta); return ruta

def renderizar(escenas, total, audio, size, salida):
    overlay_ia = generar_overlay_disclosure()
    if overlay_ia and os.path.exists(overlay_ia) and escenas and escenas[0]["tipo"] == "img":
        try:
            base = Image.open(escenas[0]["path"]).convert("RGBA"); ovl = Image.open(overlay_ia)
            base.alpha_composite(ovl, (0, 0)); ruta_ovl = escenas[0]["path"].replace(".jpg", "_ia.jpg")
            base.convert("RGB").save(ruta_ovl, "JPEG", quality=92); escenas[0]["path"] = ruta_ovl
        except Exception: pass
    render = RenderEscenas(escenas, size, total); video = VideoClip(render.frame, duration=total).set_audio(audio)
    video.write_videofile(salida, fps=FPS, codec="libx264", audio_codec="aac", audio_bitrate="192k", threads=4, preset="veryfast", temp_audiofile="temp_audio_final.m4a", ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart"], logger=None)
    render.cerrar(); video.close(); return salida

# ================= MINIATURAS =================
def obtener_fuente(size, font_idx=0):
    os.makedirs("fonts", exist_ok=True); 
    url = FONT_URLS[font_idx % len(FONT_URLS)]
    ruta = f"fonts/font_{font_idx}.ttf"
    if not os.path.exists(ruta):
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200 and len(r.content) > 20000:
                with open(ruta, "wb") as f: f.write(r.content)
        except Exception: pass
    for p in [ruta, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        try: return ImageFont.truetype(p, size)
        except Exception: continue
    return ImageFont.load_default()

def buscar_rostro_terror_pexels(query_base=""):
    if not PEXELS_API_KEY: return None
    queries = ["terrified man face dark", "scared woman portrait dark", "horrified man face closeup", "shocked face dark horror", "screaming man dark face"]
    if query_base: queries = [query_base + " scared face dark"] + queries
    random.shuffle(queries)
    for q in queries[:4]:
        try:
            data = pexels_get("https://api.pexels.com/v1/search", {"query": q, "orientation": "portrait", "size": "large", "per_page": 8, "page": 1}); fotos = (data or {}).get("photos", [])
            if not fotos: continue
            candidatas = [f for f in fotos if f["src"]["large2x"] not in USADOS and f.get("width", 0) > 1000]
            if not candidatas: continue
            foto = random.choice(candidatas[:4]); url = foto["src"]["large2x"]; ruta = f"temp_thumb_rostro_{random.randint(1000,9999)}.jpg"
            if descargar(url, ruta, 15 * 1024 * 1024): USADOS.add(url); return ruta
        except Exception: pass
    return None

def buscar_escena_terror_pexels(query_base=""):
    if not PEXELS_API_KEY: return None
    queries = ["abandoned house dark night", "creepy hallway dark", "dark forest fog", "cemetery night fog", "shadow figure dark"]
    if query_base: queries = [query_base + " dark night", "creepy house dark"] + queries
    random.shuffle(queries)
    for q in queries[:5]:
        try:
            data = pexels_get("https://api.pexels.com/v1/search", {"query": q, "orientation": "landscape", "size": "large", "per_page": 8, "page": 1}); fotos = (data or {}).get("photos", [])
            if not fotos: continue
            candidatas = [f for f in fotos if f["src"]["large2x"] not in USADOS]
            if not candidatas: continue
            foto = random.choice(candidatas[:4]); url = foto["src"]["large2x"]; ruta = f"temp_thumb_escena_{random.randint(1000,9999)}.jpg"
            if descargar(url, ruta, 15 * 1024 * 1024): USADOS.add(url); return ruta
        except Exception: pass
    return None

def buscar_cuerpo_terror_pexels(query_base=""):
    if not PEXELS_API_KEY: return None
    queries = ["hands covering face dark", "silhouette person scared night", "hand reaching dark door", "person hiding dark", "human hands trembling fear"]
    if query_base: queries = [query_base + " person dark"] + queries
    random.shuffle(queries)
    for q in queries[:5]:
        try:
            data = pexels_get("https://api.pexels.com/v1/search", {"query": q, "orientation": "portrait", "size": "large", "per_page": 8, "page": 1}); fotos = (data or {}).get("photos", [])
            if not fotos: continue
            candidatas = [f for f in fotos if f["src"]["large2x"] not in USADOS]
            if not candidatas: continue
            foto = random.choice(candidatas[:4]); url = foto["src"]["large2x"]; ruta = f"temp_thumb_cuerpo_{random.randint(1000,9999)}.jpg"
            if descargar(url, ruta, 15 * 1024 * 1024): USADOS.add(url); return ruta
        except Exception: pass
    return None

def elegir_estilo_miniatura():
    return random.choice([
        {"nombre": "miedo_rojo", "color_texto": (255, 255, 255), "color_acento": (255, 20, 20), "stroke": (0, 0, 0), "elemento": "flecha_roja"},
        {"nombre": "advertencia_amarillo", "color_texto": (255, 220, 0), "color_acento": (255, 255, 255), "stroke": (0, 0, 0), "elemento": "triangulo_peligro"},
        {"nombre": "shock_cyan", "color_texto": (0, 255, 255), "color_acento": (255, 255, 255), "stroke": (0, 0, 0), "elemento": "ninguno"},
        {"nombre": "misterio_blanco", "color_texto": (255, 255, 255), "color_acento": (255, 30, 30), "stroke": (0, 0, 0), "elemento": "x_roja"}
    ])

ESTILOS_IDENTIDAD = [
    {"nombre": "miedo_rojo", "color_texto": (255, 255, 255), "color_acento": (255, 20, 20), "stroke": (0, 0, 0), "elemento": "flecha_roja"},
    {"nombre": "advertencia_amarillo", "color_texto": (255, 220, 0), "color_acento": (255, 255, 255), "stroke": (0, 0, 0), "elemento": "triangulo_peligro"},
    {"nombre": "misterio_blanco", "color_texto": (255, 255, 255), "color_acento": (255, 30, 30), "stroke": (0, 0, 0), "elemento": "x_roja"},
]

def dividir_lineas(palabras):
    if len(palabras) <= 2: return palabras[:]
    mejor = None
    for i in range(1, len(palabras)):
        a, b = " ".join(palabras[:i]), " ".join(palabras[i:]); m = max(len(a), len(b))
        if mejor is None or m < mejor[0]: mejor = (m, [a, b])
    return mejor[1]

def crear_miniatura_v68(img_rostro_path, texto, salida, estilo=None, forzar_estilo=None):
    TW, TH = 1280, 720
    if forzar_estilo:
        match = next((s for s in ESTILOS_IDENTIDAD if s["nombre"] == forzar_estilo), None)
        if match: estilo = match
    estilo = estilo or elegir_estilo_miniatura()
    layout = random.choice([1, 2, 3, 4])
    font_idx = random.randint(0, len(FONT_URLS)-1)
    try:
        if img_rostro_path and os.path.exists(img_rostro_path):
            img = Image.open(img_rostro_path).convert("RGB")
            img = ImageOps.fit(img, (TW, TH), Image.LANCZOS)
        else:
            img = Image.new("RGB", (TW, TH), (8, 10, 20))
            for y in range(TH):
                c = (int(5 + 20 * y / TH), int(10 + 25 * y / TH), int(20 + 35 * y / TH))
                ImageDraw.Draw(img).line([(0, y), (TW, y)], fill=c)
        
        # SUBIR BRILLO y BAJAR CONTRASTE PARA QUE SE VEA LA IMAGEN
        img = ImageEnhance.Contrast(img).enhance(1.35); img = ImageEnhance.Color(img).enhance(1.25); img = ImageEnhance.Sharpness(img).enhance(2.3); img = ImageEnhance.Brightness(img).enhance(1.15)
        grad = Image.new("L", (TW, TH), 0); gd = ImageDraw.Draw(grad)
        
        if layout == 1: # Texto a la derecha
            for x in range(TW): gd.line([(x, 0), (x, TH)], fill=int(200 * max(0, min(1, (x / TW - 0.40) / 0.60))))
        elif layout == 2: # Texto a la izquierda
            for x in range(TW): gd.line([(x, 0), (x, TH)], fill=int(200 * max(0, min(1, ((TW-x) / TW - 0.40) / 0.60))))
        elif layout == 3: # Texto abajo
            for y in range(TH): gd.line([(0, y), (TW, y)], fill=int(200 * max(0, min(1, (y / TH - 0.35) / 0.65))))
        else: # Texto arriba
            for y in range(TH): gd.line([(0, y), (TW, y)], fill=int(200 * max(0, min(1, ((TH-y) / TH - 0.35) / 0.65))))
            
        img = Image.composite(Image.new("RGB", (TW, TH), (0, 0, 0)), img, grad)
        arr = np.asarray(img, dtype=np.float32) * vignette((TW, TH), 1.0, 0.25); img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
        texto_upper = texto.upper(); palabras = texto_upper.split()[:4]; lineas = dividir_lineas(palabras)
        
        if layout == 1: x_inicio, max_w_texto = int(TW * 0.55), TW - int(TW * 0.55) - 40
        elif layout == 2: x_inicio, max_w_texto = 40, int(TW * 0.45) - 40
        else: x_inicio, max_w_texto = 60, TW - 120
        
        max_h_texto = int(TH * 0.75)
        size_final = 60
        for size in range(140, 55, -6):
            font = obtener_fuente(size, font_idx); cajas = [font.getbbox(l) for l in lineas]; ancho_max = max(b[2] - b[0] for b in cajas); alto_total = sum(b[3] - b[1] for b in cajas) + 18 * (len(lineas) - 1)
            if ancho_max <= max_w_texto and alto_total <= max_h_texto: size_final = size; break
        
        font = obtener_fuente(size_final, font_idx); cajas = [font.getbbox(l) for l in lineas]; alto_total = sum(b[3] - b[1] for b in cajas) + 18 * (len(lineas) - 1)
        
        if layout == 1 or layout == 2: y = (TH - alto_total) // 2
        elif layout == 3: y = TH - alto_total - 60
        else: y = 60
        
        pos_lineas = []
        for l, b in zip(lineas, cajas):
            ancho_l = b[2] - b[0]; x = x_inicio + (max_w_texto - ancho_l) // 2; pos_lineas.append((l, x, y - b[1])); y += (b[3] - b[1]) + 18
            
        # FONDO NEGRO DETRÁS DEL TEXTO PARA QUE RESALTE
        overlay_bg = Image.new("RGBA", (TW, TH), (0,0,0,0)); bg_draw = ImageDraw.Draw(overlay_bg)
        for l, x, yy in pos_lineas:
            bbox = font.getbbox(l)
            bg_draw.rectangle([x - 15, yy - 10, x + (bbox[2]-bbox[0]) + 15, yy + (bbox[3]-bbox[1]) + 10], fill=(0,0,0,160))
        img = Image.alpha_composite(img, overlay_bg)

        glow = Image.new("RGBA", (TW, TH), (0, 0, 0, 0)); gdraw = ImageDraw.Draw(glow)
        for l, x, yy in pos_lineas: gdraw.text((x, yy), l, font=font, fill=estilo["color_acento"] + (255,), stroke_width=14, stroke_fill=estilo["color_acento"] + (255,))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(24)))
        
        draw = ImageDraw.Draw(img); borde = max(8, size_final // 14)
        for i, (l, x, yy) in enumerate(pos_lineas): draw.text((x, yy), l, font=font, fill=(estilo["color_acento"] if (i == len(pos_lineas) - 1) else estilo["color_texto"]) + (255,), stroke_width=borde, stroke_fill=estilo["stroke"] + (255,))
        
        elem = estilo.get("elemento", "ninguno")
        if elem == "flecha_roja":
            ax, ay = (int(TW * 0.52), int(TH * 0.85)) if layout == 1 else (int(TW * 0.40), int(TH * 0.85)); draw.polygon([(ax, ay), (ax + 80, ay - 40), (ax + 80, ay - 20), (ax + 140, ay - 20), (ax + 140, ay + 20), (ax + 80, ay + 20), (ax + 80, ay + 40)], fill=(255, 20, 20, 255))
        elif elem == "triangulo_peligro":
            cx, cy = int(TW * 0.30), int(TH * 0.55); size_t = 90; draw.polygon([(cx, cy - size_t), (cx - size_t, cy + size_t // 2), (cx + size_t, cy + size_t // 2)], fill=(255, 220, 0, 255), outline=(0, 0, 0, 255)); draw.text((cx - 15, cy - 20), "!", font=obtener_fuente(int(size_t * 1.2), font_idx), fill=(0, 0, 0, 255))
        elif elem == "x_roja":
            cx, cy = int(TW * 0.28), int(TH * 0.5); r = 100; draw.line([(cx - r, cy - r), (cx + r, cy + r)], fill=(255, 20, 20, 255), width=22); draw.line([(cx + r, cy - r), (cx - r, cy + r)], fill=(255, 20, 20, 255), width=22)
            
        rgb = img.convert("RGB")
        for q in (92, 87, 82, 76, 70):
            rgb.save(salida, "JPEG", quality=q, optimize=True)
            if os.path.getsize(salida) < 1_900_000: break
        print(f"✅ Miniatura [Layout {layout}] [Font {font_idx}]")
        return True
    except Exception as e: print(f"❌ Error miniatura: {e}"); return False

# ================= SEO Y TAGS =================
def _ascii_tag_yt(t):
    nfd = unicodedata.normalize('NFD', str(t)); sin_acentos = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    limpio = re.sub(r'[^a-z0-9 ]', '', sin_acentos.lower()); return re.sub(r'\s+', ' ', limpio).strip()

def _sanitizar_tags(tags, max_tags=35, max_chars_tag=45, max_words=6):
    # Se relajan los límites para permitir Long-Tail Keywords
    limpios, vistos = [], set()
    for t in tags or []:
        if not isinstance(t, str): continue
        t = _ascii_tag_yt(t)
        if not t or t in vistos: continue
        if len(t) > max_chars_tag: t = " ".join(t.split()[:max_words])
        if len(t.split()) > max_words or len(t) < 3: continue
        if re.search(r"\d{3,}", t): continue
        vistos.add(t); limpios.append(t)
        if len(limpios) >= max_tags: break
    random.shuffle(limpios); return limpios

def construir_tags(plan, tema, sugerencias, estado_mx=""):
    nombre_tema = _ascii_tag_yt(tema["tema"].replace("_", " "))
    estado_ascii = _ascii_tag_yt(estado_mx) if estado_mx else ""
    
    exactos = list(plan.get("tags", []))[:15]
    broad = ["terror", "miedo", "horror", "paranormal", "misterio", "relatos de terror", "historias de terror", "documental de terror"]
    
    long_tail = []
    if estado_ascii:
        long_tail += [f"terror en {estado_ascii}", f"leyendas de {estado_ascii}", f"misterio en {estado_ascii}"]
    
    long_tail += [
        f"historias de terror {nombre_tema}", f"relatos de terror {nombre_tema}", 
        f"que hay en {nombre_tema}", f"el secreto de {nombre_tema}", 
        f"por que nadie sube a {nombre_tema}", f"lo que ocultan en {nombre_tema}",
        f"peligro en {nombre_tema}", f"{nombre_tema} real", f"caso de {nombre_tema}"
    ]
    
    especificos = list(tema["keywords"])
    busquedas = list(sugerencias)[:10]
    
    todos = exactos + broad + long_tail + especificos + busquedas
    return _sanitizar_tags(todos, max_tags=35, max_chars_tag=45, max_words=6)

def construir_hashtags(tema):
    hs = ["#RelatosDeTerror", "#Terror", "#Paranormal"] + tema.get("hashtags", [])[:2] + ["#Mexico"]
    return " ".join(hs[:6])

def construir_descripcion(plan, tema, caps_ts, sugerencias, hashtags):
    gancho = plan.get("descripcion_gancho", " ").strip() or plan["gancho"]
    if "relato de terror" not in gancho.lower()[:220]: gancho = "Relato de terror: " + gancho
    capitulos = "\n".join(f"{ts} {t}" for ts, t in caps_ts); rel = ", ".join(sugerencias[:5])
    partes = [gancho, f"🔔 Suscríbete para un relato nuevo cada semana: {CANAL_LINK}?sub_confirmation=1", f"⏰ CAPÍTULOS\n{capitulos}", f"📖 SOBRE ESTE RELATO\n{plan.get('resumen', '')}", (f"🔎 Temas relacionados: {rel}" if rel else ""), f"📱 Facebook: {FACEBOOK_LINK}"]
    if ACTIVAR_DISCLOSURE_IA: partes.append(DISCLOSURE_TEXT.strip())
    partes.append(hashtags); return "\n\n".join(p for p in partes if p and p.strip())[:4900]

def generar_srt(segs, ruta):
    def ts(x):
        h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"
    lineas, n = [], 1
    for s in segs:
        pal = s["texto"].split()
        if not pal: continue
        t = s["inicio"]
        for i in range(0, len(pal), 9):
            tr = pal[i:i + 9]; d = s["dur_audio"] * len(tr) / len(pal); lineas.append(f"{n}\n{ts(t)} --> {ts(t + d)}\n{' '.join(tr)}\n"); n, t = n + 1, t + d
    with open(ruta, "w", encoding="utf-8") as f: f.write("\n".join(lineas))
    return ruta

def seleccionar_voz_semana(estado):
    v = random.choice(VOCES_ROTACION)
    return {"voz": v["voz"], "tono": f"{random.randint(-5, 2)}Hz", "rate": f"+{random.randint(5, 15)}%"}

def seleccionar_estilo_semana(estado):
    return random.choice(IDENTIDAD_VISUAL["estilos_rotacion"])

def generar_comentario_fijado(plan, tema):
    pregunta = plan.get("pregunta_comentario") or random.choice([f"¿Ustedes qué harían si les pasara algo así en {random.choice(tema['contextos'])}?", "¿Creen que estas leyendas tienen algo de real?", "¿Cuál es la historia más extraña que les ha pasado?"])
    return f"📖 Este relato fue adaptado con asistencia de IA para narrar una leyenda compartida por la comunidad.\n\n{pregunta} Los leo 👇\n\n— El equipo de Sombras 🌙"

# ================= PUBLICACIÓN =================
def deberia_publicar(estado):
    ult = estado.get("ultima_publicacion")
    if not ult: return True
    try:
        dt = datetime.fromisoformat(ult)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=TZ)
        horas = (datetime.now(TZ) - dt).total_seconds() / 3600; min_horas = INTERVALO_MIN_HORAS * random.uniform(0.85, 1.15)
        if horas < min_horas: print(f"⏸️ Han pasado {horas:.1f}h (mínimo {min_horas:.1f}h)."); return False
    except ValueError: pass
    return True

def proximo_slot():
    ahora = datetime.now(TZ); slot = ahora.replace(hour=HORA_PICO, minute=0, second=0, microsecond=0)
    if slot - ahora < timedelta(minutes=10): slot += timedelta(days=1)
    return slot

def utc_iso(dt): return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

def subir_video(youtube, ruta, titulo, descripcion, tags, publish_at=None):
    status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}
    if publish_at: status.update({"privacyStatus": "private", "publishAt": publish_at})
    
    tags = _sanitizar_tags(tags, max_tags=35, max_chars_tag=45, max_words=6)
    
    body = {"snippet": {"title": titulo[:100], "description": descripcion[:5000], "tags": tags, "categoryId": "24", "defaultLanguage": "es", "defaultAudioLanguage": "es"}, "status": status}
    media = MediaFileUpload(ruta, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    resp, reintentos = None, 0
    while resp is None:
        try:
            st, resp = req.next_chunk()
            if st: print(f"   ⬆️ {int(st.progress() * 100)}%")
        except (HttpError, ssl.SSLEOFError, ConnectionError, socket.timeout, OSError) as e:
            if isinstance(e, HttpError) and e.resp.status == 400 and "invalidTags" in str(e):
                print(f"⚠️ invalidTags. Reintentando con tags seguros...")
                body["snippet"]["tags"] = _sanitizar_tags(tags, max_tags=15, max_chars_tag=20, max_words=3)
                req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
                continue
            es_reintento = (isinstance(e, HttpError) and e.resp.status in (429, 500, 502, 503, 504)) or isinstance(e, (ssl.SSLEOFError, ConnectionError, socket.timeout, OSError))
            if es_reintento and reintentos < 8: reintentos += 1; time.sleep(2 ** reintentos); continue
            raise
    print(f"✅ Video subido: https://youtu.be/{resp['id']}" + (f" (programado {publish_at})" if publish_at else "")); return resp["id"]

def extras_post_subida(youtube, vid, miniatura, srt, comentario):
    if miniatura and os.path.exists(miniatura):
        try: youtube.thumbnails().set(videoId=vid, media_body=MediaFileUpload(miniatura, mimetype="image/jpeg")).execute(); print("✅ Miniatura subida")
        except Exception: pass
    if srt and os.path.exists(srt):
        try: youtube.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": "es", "name": "Español", "isDraft": False}}, media_body=MediaFileUpload(srt, mimetype="application/octet-stream")).execute(); print("✅ Subtítulos subidos")
        except Exception: pass
    if PLAYLIST_ID:
        try: youtube.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": PLAYLIST_ID, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute(); print("✅ Añadido a playlist")
        except Exception: pass
    if comentario:
        try: youtube.commentThreads().insert(part="snippet", body={"snippet": {"videoId": vid, "topLevelComment": {"snippet": {"textOriginal": comentario}}}}).execute(); print("✅ Comentario publicado")
        except Exception: pass

def crear_short(segs_orig, plan, fondo, salida="short_final.mp4"):
    segs = [{**s} for s in segs_orig]; sel, t = [], 0.0
    for s in segs:
        if sel and t + s["dur"] > 50: break
        sel.append(s); t += s["dur"]
        if t >= 32: break
    t0 = 0.0
    for s in sel: s["inicio"] = t0; t0 += s["dur"]
    t = t0; cta = generar_audio("La historia completa ya está en el canal. Suscríbete.", "cta", "resolucion")
    escenas = construir_escenas(sel); extras, total = [], t
    if cta:
        d = duracion_audio(cta); extras.append(AudioFileClip(cta).set_start(t)); ult = escenas[-1]; escenas.append({**ult, "inicio": t, "dur": d + 0.6, "fade": False}); total = t + d + 0.6
    audio, _ = mezclar_audio(sel, total, fondo, extras); renderizar(escenas, total, audio, (1080, 1920), salida); return salida

# ================= MAIN =================
def buscar_archivo(nombre):
    for root, _, files in os.walk("."):
        if "/." in root or "\\." in root: continue
        if nombre in files: return os.path.join(root, nombre)
    return None

def seleccionar_fondo(estado):
    ultimos = estado["ultimos_fondos"]; disp = [f for f in FONDOS_DISPONIBLES if f not in ultimos[-3:]] or FONDOS_DISPONIBLES[:]
    random.shuffle(disp)
    for f in disp + FONDOS_DISPONIBLES:
        ruta = buscar_archivo(f)
        if ruta: estado["ultimos_fondos"] = (ultimos + [f])[-10:]; print(f"🎵 Fondo: {ruta}"); return ruta
    print("⚠️ Sin música de fondo"); return None

def limpiar_temporales():
    for f in os.listdir("."):
        if f.startswith("temp_") or f in ("video_final.mp4", "short_final.mp4", "miniatura.jpg", "subtitulos.srt"):
            try: os.remove(f)
            except OSError: pass

def verificar_envs():
    faltan = [v for v in ("DEEPSEEK_API_KEY", "PEXELS_API_KEY", "YOUTUBE_USER_TOKEN") if not os.getenv(v)]
    if faltan: print(f"❌ Faltan variables: {', '.join(faltan)}"); sys.exit(1)
    yt = crear_cliente_youtube()
    if yt is None: sys.exit(1)
    return yt

def main():
    global NUM_CAPITULOS, VOZ_CANAL
    youtube = verificar_envs(); limpiar_temporales(); estado = cargar_estado()
    if os.getenv("FORCE_PUBLISH") == "true": print("⚡ FORCE_PUBLISH activo")
    elif not deberia_publicar(estado): sys.exit(0)

    NUM_CAPITULOS = random.choice([3, 4, 4, 5, 5, 6])
    VOZ_CANAL = seleccionar_voz_semana(estado); estilo_semana = seleccionar_estilo_semana(estado)
    
    print("=" * 70)
    print("👻 SOMBRAS DE MEDIANOCHE - BOT v9.2 MEGA SEO & VISUAL FIX")
    print(f"📅 {datetime.now(TZ):%Y-%m-%d %H:%M} | 🎤 {VOZ_CANAL['voz']} ({VOZ_CANAL['rate']}, {VOZ_CANAL['tono']}) | 🎬 videos: {USAR_VIDEOS}")
    print(f"📚 Temas: {len(TEMAS)} | SEG_ESCENA={SEG_ESCENA}s | INTERVALO={INTERVALO_MIN_HORAS}h")
    print(f"🎯 v9.2: Miniaturas iluminadas + 35 tags long-tail + Filtro Engaged Views")
    print("=" * 70)

    actualizar_rendimiento(youtube, estado)
    tema = elegir_tema(estado, youtube); contexto = random.choice(tema["contextos"]); estado_mx = random.choice(ESTADOS_MEXICO)
    formato = random.choice(FORMATOS_NARRACION); perfil = random.choice(PERFILES_NARRADOR)
    print(f"🎭 Formato: {formato['nombre']} | Narrador: {perfil} | Capítulos: {NUM_CAPITULOS}")

    sugerencias = list(dict.fromkeys(sugerencias_youtube(tema["seed"]) + sugerencias_youtube("relato de terror " + tema["keywords"][0])))[:10]
    fondo = seleccionar_fondo(estado); titulos_previos = cargar_json(TITULOS_LARGOS_FILE, {"titulos": []})["titulos"][-20:]

    plan = titulo = None
    for intento in range(6):
        try:
            plan = generar_plan(tema, contexto, estado_mx, sugerencias, titulos_previos, formato_narracion=formato, perfil_narrador=perfil)
            if plan.get("palabras_clave") and tema_ya_usado(" ".join(map(str, plan["palabras_clave"]))): raise ValueError("tema repetido")
            titulo = elegir_titulo(plan["titulos"])
            if not titulo: raise ValueError("sin título válido")
            plan["_formato_instruccion"] = formato["instruccion"]; plan["_perfil_narrador"] = perfil; plan["_nombre_formato"] = formato["nombre"]
            break
        except Exception as e:
            print(f"⚠️ Plan intento {intento+1}/6: {e}"); plan = None; time.sleep(5)
    if not plan: print("❌ No se pudo generar un plan válido."); sys.exit(1)

    try: anio = int(plan.get("anio_suceso"))
    except: anio = None
    print(f"📌 Título: {titulo}"); print(f"🎯 Elemento imposible: {plan.get('elemento_imposible', 'N/A')}"); print(f"📍 Estado: {estado_mx}")

    capitulos_txt = generar_capitulos(plan, tema, contexto, estado_mx); n_caps = len(capitulos_txt); segs = crear_segmentos(capitulos_txt)
    total_palabras = sum(len(c.split()) for c in capitulos_txt)
    print(f"🧩 {len(segs)} segmentos, {total_palabras} palabras (meta: 1200-1600)")

    segs = sintetizar(segs); total = construir_timeline(segs); intentos = 0
    
    while total < DURACION_MINIMA_SEGUNDOS and intentos < MAX_INTENTOS_EXPANSION:
        deficit_min = (DURACION_MINIMA_SEGUNDOS - total) / 60
        print(f"⚠️ {total/60:.1f} min < mínimo (8 min). Déficit: {deficit_min:.1f} min. Expansión {intentos+1}/{MAX_INTENTOS_EXPANSION}...")
        extra = expandir_texto(titulo, " ".join(s["texto"] for s in segs), ronda=intentos+1); intentos += 1
        if not extra:
            print(f"   ⚠️ Expansión {intentos} devolvió vacío. Reintentando...")
            continue
        nuevos = [{"cap": n_caps - 1, "texto": p, "cap_ini": False, "etapa": "resolucion", "id": f"x{intentos}_{k}", "expansion": True} for k, p in enumerate(dividir_en_segmentos(extra))]
        segs += sintetizar(nuevos); total = construir_timeline(segs)
        print(f"   ✅ Tras expansión {intentos}: {total/60:.1f} min")

    if total < DURACION_MINIMA_SEGUNDOS:
        print(f"🚨 Generando capítulo de emergencia para alcanzar mínimo...")
        prompt_emerg = f"""Escribe un CAPÍTULO FINAL de emergencia para un documental de terror.
Título: "{titulo}". Narrador: {plan.get('protagonista', 'Marco')}. Lugar: {contexto}, {estado_mx}.
Ángulo: {tema['angulo']}. Elemento imposible: {plan.get('elemento_imposible', 'detalle')}.
Contexto previo: {(" ".join(s["texto"] for s in segs))[-600:]}
Escribe 400-500 palabras que añadan una revelación final perturbadora. Español mexicano. Solo texto."""
        t_emerg = llm(prompt_emerg, temperature=0.9, max_tokens=1200)
        t_emerg = limpiar_texto_narracion(t_emerg) if t_emerg else ""
        if len(t_emerg.split()) >= 300:
            nuevos = [{"cap": n_caps, "texto": p, "cap_ini": k == 0, "etapa": "resolucion", "id": f"emerg_{k}", "expansion": True} for k, p in enumerate(dividir_en_segmentos(t_emerg))]
            segs += sintetizar(nuevos); total = construir_timeline(segs)
            print(f"   ✅ Cap emergencia añadido. Total: {total/60:.1f} min")

    if total > DURACION_MAXIMA_SEGUNDOS:
        print(f"⚠️ {total/60:.1f} min > máximo ({DURACION_MAXIMA_SEGUNDOS/60:.0f} min). Recortando expansiones primero...")
        while total > DURACION_MAXIMA_SEGUNDOS:
            idx = next((i for i in range(len(segs) - 1, -1, -1) if segs[i].get("expansion")), None)
            if idx is None: break
            segs.pop(idx); total = construir_timeline(segs)
        while total > DURACION_MAXIMA_SEGUNDOS and len(segs) > 15:
            segs.pop(); total = construir_timeline(segs)
    
    if total < DURACION_MINIMA_SEGUNDOS: 
        print(f"❌ Duración insuficiente tras todas las expansiones ({total/60:.1f} min). Abortando.")
        sys.exit(1)
        
    outro = [{"cap": n_caps - 1, "texto": random.choice(OUTROS), "cap_ini": False, "etapa": "resolucion", "id": "outro", "outro": True}]
    segs += sintetizar(outro); total = construir_timeline(segs); print(f"⏱️ Duración final: {total/60:.1f} min")

    consultas = planificar_consultas(segs, tema, anio)
    for i, s in enumerate(segs): n = max(1, round(s["dur"] / SEG_ESCENA)); s["medios"] = obtener_medios(i, s["etapa"], consultas[i], n, tema)

    caps_ts = []
    for c in range(n_caps):
        primero = next((s for s in segs if s["cap"] == c), None)
        nombre = str(plan["capitulos"][c].get("titulo", f"Parte {c+1}"))[:50] if c < len(plan["capitulos"]) else f"Parte {c+1}"
        if primero: caps_ts.append((fmt_ts(primero["inicio"]), nombre))
    if caps_ts: caps_ts[0] = ("00:00", caps_ts[0][1])

    hashtags = construir_hashtags(tema); descripcion = construir_descripcion(plan, tema, caps_ts, sugerencias, hashtags); tags = construir_tags(plan, tema, sugerencias, estado_mx); srt = generar_srt(segs, "subtitulos.srt")
    print(f"🏷️  Tags ({len(tags)}): {', '.join(tags[:6])}...")

    print("🖼️  Buscando rostro de terror para miniatura...")
    portada = elegir_texto_portada(plan.get("palabras_portada"), titulo)
    img_miniatura = None; miniatura_ok = False
    
    if random.random() < 0.5:
        img_miniatura = buscar_rostro_terror_pexels(tema["tema"] + " scared face")
        if not img_miniatura: img_miniatura = buscar_escena_terror_pexels(tema["contextos"][0])
    else:
        img_miniatura = buscar_escena_terror_pexels(tema["contextos"][0])
        if not img_miniatura: img_miniatura = buscar_rostro_terror_pexels(tema["tema"] + " scared face")

    if img_miniatura: miniatura_ok = crear_miniatura_v68(img_miniatura, portada, "miniatura.jpg", forzar_estilo=estilo_semana)
    if not miniatura_ok and not img_miniatura: 
        img_miniatura = buscar_cuerpo_terror_pexels(tema["tema"])
        if img_miniatura: miniatura_ok = crear_miniatura_v68(img_miniatura, portada, "miniatura.jpg", forzar_estilo=estilo_semana)
    if not miniatura_ok: miniatura_ok = crear_miniatura_v68(None, portada, "miniatura.jpg", forzar_estilo=estilo_semana)
    miniatura = "miniatura.jpg" if miniatura_ok else None

    escenas = construir_escenas(segs); audio, _ = mezclar_audio(segs, total, fondo)
    print("🎬 Renderizando video largo..."); renderizar(escenas, total, audio, (W, H), "video_final.mp4")

    slot = proximo_slot() if PROGRAMAR_PICO else None
    if slot: print(f"🕖 Programado: {slot:%Y-%m-%d %H:%M} CDMX")

    vid = subir_video(youtube, "video_final.mp4", titulo, descripcion, tags, utc_iso(slot) if slot else None)
    comentario = generar_comentario_fijado(plan, tema); extras_post_subida(youtube, vid, miniatura, srt, comentario)

    if GENERAR_SHORT:
        print("📱 Creando Short embudo...")
        try:
            short_path = crear_short(segs, plan, fondo, "short_final.mp4")
            if short_path and os.path.exists(short_path):
                short_titulo = str(plan.get("titulo_short") or titulo)[:88] + " #Shorts"
                short_desc = f"{plan.get('titulo_short', titulo)[:100]}\n\n📺 Video completo 👉 https://youtu.be/{vid}\n\n🔔 Suscríbete: {CANAL_LINK}?sub_confirmation=1\n\n#Shorts {hashtags}" + (DISCLOSURE_TEXT if ACTIVAR_DISCLOSURE_IA else "")
                tags_short = _sanitizar_tags(tags[:12] + ["shorts"]); slot_short = slot + timedelta(hours=2) if slot else None
                vid_short = subir_video(youtube, short_path, short_titulo, short_desc, tags_short, utc_iso(slot_short) if slot_short else None)
                if vid_short:
                    print(f"✅ Short subido: https://youtu.be/{vid_short}")
                    estado["videos"].append({"id": vid_short, "titulo": short_titulo, "tema": tema["tema"], "tipo": "short", "fecha": datetime.now(TZ).isoformat()})
        except Exception as e: print(f"❌ Error creando short: {e}")

    ahora = datetime.now(TZ).isoformat(); guardar_titulo_largo(titulo); guardar_tema(tema["tema"])
    estado["videos"].append({"id": vid, "titulo": titulo, "tema": tema["tema"], "formato": formato["nombre"], "perfil": perfil, "elemento_imposible": plan.get("elemento_imposible"), "estado_mx": estado_mx, "duracion_min": round(total / 60, 1), "voz": VOZ_CANAL["voz"], "estilo_miniatura": estilo_semana, "fecha": ahora})
    estado["videos"] = estado["videos"][-60:]; estado["temas_recientes"] = (estado["temas_recientes"] + [tema["tema"]])[-6:]; estado["ultima_publicacion"] = ahora

    if not estado.get("avatar_audiencia"):
        avatar_nuevo = generar_avatar_audiencia(plan, tema)
        if avatar_nuevo: estado["avatar_audiencia"] = avatar_nuevo; print(f"👤 Avatar guardado")
            
    if vid and not estado.get("perfil_lock"): bloquear_perfil(estado, formato, perfil, vid)

    guardar_json(MUSICA_ESTADO_FILE, estado); limpiar_temporales(); print("🎉 Proceso completo: 1 video largo programado.")

if __name__ == "__main__":
    try: main()
    except SystemExit: raise
    except Exception as e: print(f"❌ Error fatal: {e}"); traceback.print_exc(); sys.exit(1)
