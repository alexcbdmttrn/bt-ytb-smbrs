# -*- coding: utf-8 -*-
"""
SOMBRAS DE MEDIANOCHE - Bot v6.1 (SEO mejorado)
v6.1 - 3 fixes SEO sobre v6.0:
  1. construir_tags: quita filtro "historia real" (tag válido), añade estado_mx param
     con tags de estado long-tail (terror jalisco, leyendas veracruz, etc.)
  2. construir_descripcion: hashtags SIEMPRE al final absoluto (YT muestra los
     primeros 3 encima del título — no enterrarlos en medio del disclosure)
  3. main(): pasa estado_mx a construir_tags
v6.0 - Overhaul de temas y variedad (38 temas paranormales)
v5.3 - Fix validación de token (tolerante a youtube.upload sin readonly)
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

# =================================================================
# CONFIGURACIÓN
# =================================================================
TZ = ZoneInfo("America/Mexico_City")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
YOUTUBE_USER_TOKEN = json.loads(os.getenv("YOUTUBE_USER_TOKEN") or "{}")
PLAYLIST_ID = os.getenv("YOUTUBE_PLAYLIST_ID", "")
FACEBOOK_LINK = "https://www.facebook.com/profile.php?id=61593237382982"
CANAL_LINK = "https://www.youtube.com/@sombrasdemedianocheoficial"

MUSICA_ESTADO_FILE = "estado_musica.json"
TITULOS_LARGOS_FILE = "titulos_largos_publicados.json"
TEMAS_SHORTS_FILE = "temas_shorts.json"

DURACION_MINIMA_SEGUNDOS = 480
DURACION_MAXIMA_SEGUNDOS = 900
MAX_INTENTOS_EXPANSION = 1
NUM_CAPITULOS = 4

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
    "\n\n⚠️ Relato compartido por un oyente de nuestra comunidad, narrado con voz "
    "sintética y mejorado con IA para una mayor inmersión."
)

VOZ_CANAL = {"voz": "es-MX-JorgeNeural", "tono": "-4Hz"}
VOCES_RESPALDO = ["es-MX-JorgeNeural", "es-ES-AlvaroNeural", "es-CO-GonzaloNeural", "es-US-AlonsoNeural"]
RATE_ETAPA = {"apertura": "+6%", "tension": "+6%", "destino": "+4%", "climax": "-2%", "resolucion": "+2%"}
PAUSA_ETAPA = {"apertura": 0.5, "tension": 0.45, "destino": 0.5, "climax": 0.75, "resolucion": 0.6}
PROB_VIDEO = {"apertura": 0.5, "tension": 0.5, "destino": 0.6, "climax": 0.5, "resolucion": 0.4}
FUENTE_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"
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

# =================================================================
# TEMAS — 38 CATEGORÍAS PARANORMALES
# =================================================================
TEMAS = [
    # ========== CRIATURAS Y SERES LEGENDARIOS (7) ==========
    {"tema": "skinwalker", "seed": "skinwalker relatos", "angulo": "Algo imita voces humanas y te sigue por el bosque; cada noche se acerca más.",
     "keywords": ["skinwalker", "criatura", "persecución", "bosque"],
     "contextos": ["carretera solitaria", "bosque profundo", "sierra aislada", "desierto de noche"],
     "visuales": ["dark forest fog", "desert road night", "mountain night", "lonely highway night", "eyes in the dark"],
     "hashtags": ["#Skinwalker", "#CriaturasDeLaNoche"]},

    {"tema": "duendes", "seed": "duendes historia real", "angulo": "Objetos que desaparecen, risas en la madrugada, y un niño que habla con alguien que no está.",
     "keywords": ["duendes", "duende", "casa", "travesuras"],
     "contextos": ["casa del pueblo", "rancho", "bosque cercano", "milpa", "casa antigua"],
     "visuales": ["old mexican house night", "dark forest small figure", "rustic mexican ranch night", "cornfield night fog", "small footprints dust"],
     "hashtags": ["#Duendes", "#DuendesReales"]},

    {"tema": "aluxes", "seed": "aluxes mayas terror", "angulo": "Los guardianes mayas de la milpa cobran venganza cuando alguien invade su territorio.",
     "keywords": ["aluxes", "alux", "mayas", "milpa"],
     "contextos": ["milpa yucateca", "ruinas mayas", "cenote", "selva", "pueblo maya"],
     "visuales": ["mayan ruins night", "jungle fog night", "mexican cornfield night", "cenote dark water", "small stone altar jungle"],
     "hashtags": ["#Aluxes", "#LeyendasMayas"]},

    {"tema": "chupacabras", "seed": "chupacabras avistamiento", "angulo": "Los animales aparecen sin sangre y el rancho entero escucha algo en el monte.",
     "keywords": ["chupacabras", "ganado", "avistamiento", "rancho"],
     "contextos": ["rancho ganadero", "monte", "sierra", "desierto", "pueblo rural"],
     "visuales": ["mexican ranch night", "dead livestock field night", "desert ranch night", "mountain silhouette creature", "cattle field fog"],
     "hashtags": ["#Chupacabras", "#CriaturasReales"]},

    {"tema": "nahual", "seed": "nahual historia terror", "angulo": "Un vecino del pueblo puede convertirse en animal; tú lo viste cambiar.",
     "keywords": ["nahual", "brujo", "animal", "pueblo"],
     "contextos": ["pueblo viejo", "barrio del pueblo", "cerro", "camino de tierra", "casa del brujo"],
     "visuales": ["mexican village night", "dirt road night fog", "mountain silhouette night", "coyote eyes dark", "old mexican house night"],
     "hashtags": ["#Nahual", "#LeyendasMexicanas"]},

    {"tema": "llorona", "seed": "la llorona historia", "angulo": "El llanto de una mujer en el río anuncia la muerte de alguien del pueblo.",
     "keywords": ["la llorona", "río", "leyenda", "llanto"],
     "contextos": ["río del pueblo", "panteón", "puente viejo", "camino a la iglesia", "casa junto al río"],
     "visuales": ["mexican river night fog", "old bridge night", "colonial church night", "woman silhouette river", "candles altar night"],
     "hashtags": ["#LaLlorona", "#LeyendasMexicanas"]},

    {"tema": "charro_negro", "seed": "charro negro leyenda", "angulo": "Un jinete vestido de negro ofrece dinero en el camino; pagar el precio es perder el alma.",
     "keywords": ["charro negro", "jinete", "diablo", "camino"],
     "contextos": ["camino de terracería", "carretera solitaria", "pueblo", "encrucijada", "puente viejo"],
     "visuales": ["dark horseman silhouette", "dusty road night", "black horse night fog", "crossroads night mexico", "old bridge night fog"],
     "hashtags": ["#CharroNegro", "#LeyendasMexicanas"]},

    # ========== SERES Y ENTIDADES PARANORMALES (7) ==========
    {"tema": "fantasmas", "seed": "fantasmas casa historia", "angulo": "En la casa hay alguien más: mueve cosas, apaga luces, y a veces se deja ver.",
     "keywords": ["fantasmas", "aparecidos", "casa", "espíritus"],
     "contextos": ["casa antigua", "departamento", "casa heredada", "habitación de hotel", "edificio viejo"],
     "visuales": ["dark hallway ghost shadow", "old house interior night", "empty room night", "door half open dark", "fog room interior"],
     "hashtags": ["#Fantasmas", "#Aparecidos"]},

    {"tema": "demonios", "seed": "demonios invocación historia", "angulo": "Algo responde cuando no debieron llamar; no es un espíritu, es algo mucho peor.",
     "keywords": ["demonios", "invocación", "posesión", "infierno"],
     "contextos": ["casa abandonada", "sótano", "iglesia abandonada", "cementerio", "habitación cerrada"],
     "visuales": ["dark basement horror", "abandoned church night", "candles dark room", "shadow figure dark", "old wooden door dark"],
     "hashtags": ["#Demonios", "#TerrorOculto"]},

    {"tema": "brujas", "seed": "brujas historia terror", "angulo": "Una mujer del pueblo sabe demasiado; la gente la evita, y los que no, desaparecen.",
     "keywords": ["brujas", "hechicería", "pueblo", "maldición"],
     "contextos": ["casa al final del pueblo", "cerro", "mercado", "camino al panteón", "cueva"],
     "visuales": ["old mexican woman dark", "candles ritual night", "abandoned shack night", "herbs hanging dark", "moonlight house silhouette"],
     "hashtags": ["#Brujas", "#Hechicería"]},

    {"tema": "brujos", "seed": "brujo trabajo magia negra", "angulo": "Le pidieron un trabajo de magia negra; ahora el cliente no puede escapar de lo que pidió.",
     "keywords": ["brujos", "magia negra", "trabajo", "maldición"],
     "contextos": ["casa del brujo", "mercado esotérico", "cementerio de noche", "camino solitario", "altar"],
     "visuales": ["dark altar candles", "old esoteric shop night", "cemetery candle night", "ritual circle dark", "skull candle dark"],
     "hashtags": ["#Brujos", "#MagiaNegra"]},

    {"tema": "poltergeist", "seed": "poltergeist casa real", "angulo": "Los objetos se mueven solos, las puertas se azotan, y la actividad aumenta cada noche.",
     "keywords": ["poltergeist", "objetos", "casa", "actividad"],
     "contextos": ["casa familiar", "departamento", "casa de la infancia", "habitación", "ático"],
     "visuales": ["objects flying room dark", "thrown furniture room night", "slammed door dark", "broken mirror room night", "scattered objects floor dark"],
     "hashtags": ["#Poltergeist", "#CasaEmbrujada"]},

    {"tema": "muneca_poseida", "seed": "muñeca poseída historia", "angulo": "La muñeca cambia de posición sola y empieza a aparecer en los sueños de la familia.",
     "keywords": ["muñeca", "poseída", "juguete", "maldita"],
     "contextos": ["casa antigua", "cuarto de niña", "ático", "tienda de antigüedades", "casa heredada"],
     "visuales": ["creepy doll dark room", "old doll chair night", "doll face closeup dark", "antique doll cabinet", "child room dark"],
     "hashtags": ["#MuñecaMaldita", "#ObjetoMaldito"]},

    {"tema": "payaso_maldito", "seed": "payaso maldito historia", "angulo": "Un payaso aparece en el mismo lugar cada noche; nadie lo contrató.",
     "keywords": ["payaso", "maldito", "aparición", "circo"],
     "contextos": ["circo abandonado", "parque", "calle solitaria", "cumpleaños", "feria"],
     "visuales": ["creepy clown dark", "abandoned circus night", "empty carnival night", "clown silhouette fog", "broken carousel night"],
     "hashtags": ["#PayasoMaldito", "#TerrorPsicológico"]},

    # ========== LUGARES EMBRUJADOS (9) ==========
    {"tema": "casa_embrujada", "seed": "casa embrujada historia real", "angulo": "La casa nueva tiene historia; los vecinos hablan de la familia anterior y nadie quiere entrar.",
     "keywords": ["casa embrujada", "aparición", "familia", "historia"],
     "contextos": ["casa antigua", "casa de campo", "casa heredada", "casa en venta", "casa del barrio"],
     "visuales": ["abandoned mexican house night", "haunted house fog", "dark house interior hallway", "broken window house night", "creepy attic dark"],
     "hashtags": ["#CasaEmbrujada", "#Fantasmas"]},

    {"tema": "hospital", "seed": "hospital terror historia", "angulo": "En la guardia nocturna, un paciente que ya no debería existir sigue apareciendo en el mismo pasillo.",
     "keywords": ["hospital", "guardia nocturna", "paciente", "morgue"],
     "contextos": ["hospital viejo", "clínica cerrada", "ala clausurada", "morgue", "quirófano abandonado"],
     "visuales": ["hospital corridor dark", "abandoned hospital", "empty hospital bed", "morgue dark", "operating room old"],
     "hashtags": ["#HospitalEmbrujado", "#TerrorNocturno"]},

    {"tema": "velador", "seed": "trabajé de velador terror", "angulo": "Turno nocturno de vigilante; las cámaras muestran algo que no está en el pasillo real.",
     "keywords": ["velador", "turno de noche", "cámaras de seguridad", "trabajo nocturno"],
     "contextos": ["fábrica abandonada", "bodega", "escuela vacía", "estacionamiento", "condominio"],
     "visuales": ["security guard night", "empty factory night", "warehouse dark", "cctv camera", "parking lot night"],
     "hashtags": ["#Velador", "#TurnoDeNoche"]},

    {"tema": "carretera", "seed": "carretera de noche terror", "angulo": "Un viaje nocturno con un pasajero que no recuerda haber subido, o una parada que nadie debió hacer.",
     "keywords": ["carretera", "viaje nocturno", "taxi", "autoestopista"],
     "contextos": ["carretera federal", "gasolinera", "túnel", "curva de la muerte", "desvío"],
     "visuales": ["highway night fog", "taxi night city", "road tunnel dark", "truck night highway", "gas station night"],
     "hashtags": ["#CarreteraMaldita", "#TerrorNocturno"]},

    {"tema": "hotel_embrujado", "seed": "hotel embrujado historia", "angulo": "En el hotel hay habitaciones que no deberían estar en el mapa, y un huésped que nunca se fue.",
     "keywords": ["hotel", "habitación", "huésped", "embrujado"],
     "contextos": ["hotel viejo", "motel de carretera", "hostal", "hotel de pueblo", "casa de huéspedes"],
     "visuales": ["hotel corridor dark", "old hotel room night", "abandoned hotel lobby", "motel neon night", "vintage room dark"],
     "hashtags": ["#HotelEmbrujado", "#Fantasmas"]},

    {"tema": "cementerio", "seed": "cementerio noche terror", "angulo": "Algo se mueve entre las tumbas; los que se quedan hasta tarde escuchan rezos que nadie reza.",
     "keywords": ["cementerio", "panteón", "tumba", "noche"],
     "contextos": ["panteón del pueblo", "cementerio antiguo", "cripta", "mausoleo", "fosa común"],
     "visuales": ["cemetery night fog", "old mexican pantheon", "crypt candles dark", "graveyard silhouette night", "grave candles night"],
     "hashtags": ["#Cementerio", "#TerrorNocturno"]},

    {"tema": "bosque_maldito", "seed": "bosque maldito terror", "angulo": "Los que entran al bosque no salen iguales; algunos no salen, y otros vuelven cambiados.",
     "keywords": ["bosque", "maldito", "perdido", "criatura"],
     "contextos": ["bosque profundo", "sierra", "montaña", "camino de tierra", "cabaña"],
     "visuales": ["dark forest fog night", "cabin in woods night", "trail in forest dark", "tall trees silhouette night", "campfire forest dark"],
     "hashtags": ["#BosqueMaldito", "#Criaturas"]},

    {"tema": "mina_abandonada", "seed": "mina abandonada terror", "angulo": "En la mina cerrada hubo un accidente; los que bajaron después escucharon golpes desde dentro.",
     "keywords": ["mina", "abandonada", "túnel", "accidente"],
     "contextos": ["mina abandonada", "túnel", "cerro", "pueblo minero", "entrada tapiada"],
     "visuales": ["abandoned mine entrance", "mine tunnel dark", "mine shaft night", "old mining town night", "minecart abandoned dark"],
     "hashtags": ["#MinaAbandonada", "#Fantasmas"]},

    {"tema": "hacienda", "seed": "hacienda embrujada historia", "angulo": "La hacienda vieja guarda lo que pasó con los dueños anteriores; los nuevos no duermen igual.",
     "keywords": ["hacienda", "embrujada", "historia", "antigua"],
     "contextos": ["hacienda vieja", "ex-hacienda", "rancho heredado", "casa de campo", "casona"],
     "visuales": ["old hacienda night", "colonial house dark", "mexican hacienda night fog", "courtyard night dark", "old wooden doors night"],
     "hashtags": ["#HaciendaEmbrujada", "#Fantasmas"]},

    # ========== OCULTISMO (10) ==========
    {"tema": "ritual", "seed": "ritual prohibido historia", "angulo": "Un ritual hecho por curiosidad abre algo que no se puede cerrar.",
     "keywords": ["ritual", "invocación", "maldición", "ocultismo"],
     "contextos": ["cementerio antiguo", "casa abandonada", "cueva", "iglesia en ruinas", "sótano"],
     "visuales": ["candles dark room", "old cemetery night", "abandoned church", "cave darkness", "old book candle"],
     "hashtags": ["#Rituales", "#Ocultismo"]},

    {"tema": "ouija", "seed": "ouija historia terror", "angulo": "Algo respondió en la tabla; desde esa noche, no dejó de responder.",
     "keywords": ["ouija", "tabla", "espíritus", "sesión"],
     "contextos": ["casa de amigo", "cuarto oscuro", "sótano", "casa abandonada", "habitación de hotel"],
     "visuales": ["ouija board candles", "dark room hands", "old wooden table candle", "seance circle dark", "mysterious planchette dark"],
     "hashtags": ["#Ouija", "#TerrorOculto"]},

    {"tema": "posesion", "seed": "posesión demoníaca historia", "angulo": "Alguien de la familia cambió; habla en otra lengua, no duerme, y sabe cosas que no debería.",
     "keywords": ["posesión", "demonio", "familia", "cambio"],
     "contextos": ["casa familiar", "habitación", "iglesia", "casa del pueblo", "convento"],
     "visuales": ["dark bedroom horror", "candlelit church interior", "old wooden crucifix dark", "shadow figure bed", "priest silhouette dark"],
     "hashtags": ["#Posesión", "#Exorcismo"]},

    {"tema": "exorcismo", "seed": "exorcismo real historia", "angulo": "El sacerdote accedió a hacer el exorcismo; lo que salió del cuerpo no era humano.",
     "keywords": ["exorcismo", "sacerdote", "demonio", "ritual"],
     "contextos": ["iglesia vieja", "casa del pueblo", "convento abandonado", "habitación cerrada", "capilla"],
     "visuales": ["candlelit church dark", "priest silhouette", "rosary candle dark", "old church interior night", "confessional dark"],
     "hashtags": ["#Exorcismo", "#TerrorReligioso"]},

    {"tema": "pacto_demonio", "seed": "pacto con el diablo historia", "angulo": "Alguien hizo un pacto por dinero o poder; ahora el precio se está cobrando.",
     "keywords": ["pacto", "demonio", "diablo", "trato"],
     "contextos": ["encrucijada", "casa abandonada", "camino solitario", "cueva", "cementerio"],
     "visuales": ["crossroads night dark", "candles pentagram dark", "old contract candle", "shadow figure door", "dark ritual circle"],
     "hashtags": ["#Pacto", "#TerrorOculto"]},

    {"tema": "maldicion", "seed": "maldición familiar historia", "angulo": "La familia carga una maldición de generaciones; cada cierto tiempo, cobra una vida.",
     "keywords": ["maldición", "familia", "herencia", "tragedia"],
     "contextos": ["casa familiar", "pueblo", "cementerio", "casa antigua", "hacienda"],
     "visuales": ["old family photo dark", "abandoned house interior", "family portrait creepy", "candles altar dark", "old diary pages"],
     "hashtags": ["#Maldición", "#TerrorFamiliar"]},

    {"tema": "objeto_maldito", "seed": "objeto maldito historia", "angulo": "Un objeto comprado barato trae reglas silenciosas y consecuencias cada noche.",
     "keywords": ["objeto maldito", "antigüedad", "espejo", "muñeca", "tianguis"],
     "contextos": ["tienda de antigüedades", "mercado de pulgas", "casa heredada", "subasta", "tianguis"],
     "visuales": ["antique shop", "old doll", "old mirror dark", "antique room dark", "pawn shop night"],
     "hashtags": ["#ObjetoMaldito", "#Coleccionista"]},

    {"tema": "espejo_maldito", "seed": "espejo maldito historia", "angulo": "En el espejo hay alguien más; refleja cosas que no están en la habitación.",
     "keywords": ["espejo", "reflejo", "maldito", "aparición"],
     "contextos": ["casa antigua", "baño", "recámara", "hotel", "casa heredada"],
     "visuales": ["old mirror dark room", "reflection strange silhouette", "cracked mirror dark", "antique mirror night", "bathroom mirror fog dark"],
     "hashtags": ["#EspejoMaldito", "#Fantasmas"]},

    {"tema": "santero", "seed": "santero trabajo espiritual", "angulo": "Le pidieron un trabajo espiritual; lo que llegó no era lo que esperaban.",
     "keywords": ["santero", "palo mayombe", "trabajo", "espiritual"],
     "contextos": ["casa del santero", "mercado esotérico", "cementerio", "altar", "sótano"],
     "visuales": ["dark altar candles bones", "esoteric shop night", "skull candle dark", "ritual objects dark", "incense smoke dark"],
     "hashtags": ["#Santería", "#TrabajoEspiritual"]},

    {"tema": "curandero", "seed": "curandero limpia terror", "angulo": "La limpia espiritual debía quitarle el mal; el mal se quedó, y algo más entró.",
     "keywords": ["curandero", "limpia", "energía", "mal"],
     "contextos": ["casa del curandero", "mercado", "pueblo", "cerro", "temazcal"],
     "visuales": ["herbs hanging dark", "smoke ritual dark", "old mexican healer house", "candles eggs limpia", "temazcal night"],
     "hashtags": ["#Curanderos", "#Limpia"]},

    # ========== EXTRATERRESTRES (3) ==========
    {"tema": "aliens", "seed": "avistamiento ovni historia", "angulo": "Lo que bajó del cielo no era un avión; la luz se movió como algo vivo.",
     "keywords": ["ovni", "extraterrestre", "avistamiento", "luces"],
     "contextos": ["campo abierto", "carretera solitaria", "sierra", "rancho", "desierto"],
     "visuales": ["ufo lights sky night", "strange light rural night", "silhouette hill ufo", "farm field night lights", "desert night sky object"],
     "hashtags": ["#Ovnis", "#Extraterrestres"]},

    {"tema": "abduccion", "seed": "abducción extraterrestre historia", "angulo": "Recuerdas fragmentos: luces, frialdad, voces; y una marca que no estaba antes.",
     "keywords": ["abducción", "extraterrestre", "recuerdo", "marca"],
     "contextos": ["casa de campo", "carretera", "rancho", "montaña", "bosque"],
     "visuales": ["bright light sky night", "car headlights ufo", "rural house light beam", "strange marks skin", "silhouette hills night ufo"],
     "hashtags": ["#Abducción", "#Extraterrestres"]},

    {"tema": "encuentro_cercano", "seed": "encuentro cercano extraterrestre", "angulo": "El encuentro fue cercano; el ser que salió del objeto habló sin mover la boca.",
     "keywords": ["encuentro", "extraterrestre", "ser", "objeto"],
     "contextos": ["camino rural", "campo", "sierra", "mina abandonada", "rancho"],
     "visuales": ["ufo landed field night", "strange silhouette fog", "field crop circle night", "glowing object rural night", "alien figure dark"],
     "hashtags": ["#EncuentroCercano", "#Extraterrestres"]},

    # ========== LEYENDAS Y CREEPYPASTA (2) ==========
    {"tema": "leyenda_mexicana", "seed": "leyenda mexicana terror", "angulo": "Una leyenda del pueblo cobra vida en versión contemporánea.",
     "keywords": ["leyendas mexicanas", "nahual", "la llorona", "pueblo"],
     "contextos": ["pueblo antiguo", "río de noche", "panteón del pueblo", "rancho abandonado", "camino de terracería"],
     "visuales": ["old village night", "colonial church night", "dirt road night", "river fog night", "candles altar"],
     "hashtags": ["#LeyendasMexicanas", "#TerrorMexicano"]},

    {"tema": "creepypasta", "seed": "creepypasta relato", "angulo": "Una leyenda de internet resulta tener un origen físico y cercano.",
     "keywords": ["creepypasta", "leyenda urbana", "barrio", "origen"],
     "contextos": ["parque abandonado", "calle solitaria", "bosque nocturno", "casa del barrio", "escuela abandonada"],
     "visuales": ["dark forest night", "abandoned playground", "empty street night", "old house night", "foggy park night"],
     "hashtags": ["#Creepypasta", "#LeyendasUrbanas"]},
]

ESCENAS_FALLBACK = {
    "apertura": ["dark hallway night", "old house interior dark", "flickering light bulb", "lonely street night"],
    "tension": ["foggy road night", "empty highway night", "car headlights fog", "dark forest path"],
    "destino": ["abandoned building", "creepy old house", "dark forest fog", "abandoned corridor"],
    "climax": ["shadow figure dark", "scary dark room", "flashlight darkness", "silhouette door light"],
    "resolucion": ["sunrise fog road", "dawn empty street", "morning mist forest", "walking away silhouette dawn"],
}

# =================================================================
# UTILIDADES
# =================================================================
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

# =================================================================
# HISTORIAL
# =================================================================
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
    nuevas = set(re.findall(r"\w+", str(tema).lower()))
    for antiguo in data["temas"][-20:]:
        if isinstance(antiguo, dict):
            antiguo = antiguo.get("tema", "")
        if not isinstance(antiguo, str) or len(antiguo) > 80:
            continue
        viejas = set(re.findall(r"\w+", antiguo.lower()))
        union = nuevas | viejas
        if union and len(nuevas & viejas) / len(union) > umbral:
            print(f"⚠️ Tema similar a: '{antiguo}'")
            return True
    return False

def guardar_tema(tema):
    data = cargar_json(TEMAS_SHORTS_FILE, {"temas": []})
    data["temas"] = [t for t in data["temas"] if isinstance(t, str) and len(t) < 80]
    if isinstance(tema, str) and len(tema) < 80 and tema not in data["temas"]:
        data["temas"].append(tema)
    data["temas"] = data["temas"][-20:]
    guardar_json(TEMAS_SHORTS_FILE, data)

# =================================================================
# YOUTUBE
# =================================================================
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
        q = f"relato de terror {consulta}"
        r = youtube.search().list(part="id", q=q, type="video", order="viewCount", publishedAfter=desde,
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
    recientes = estado["temas_recientes"][-6:]
    pool = [t for t in TEMAS if t["tema"] not in recientes] or TEMAS[:]
    candidatos = random.sample(pool, min(5, len(pool)))
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
        return 0.5 * sd + 0.5 * sr + random.uniform(0, 0.2)

    elegido = max(candidatos, key=score)
    print(f"🎯 Tema elegido: {elegido['tema']} (demanda={demandas[elegido['tema']]}, propio={rend.get(elegido['tema'])})")
    return elegido

# =================================================================
# TÍTULOS
# =================================================================
GANCHOS = [
    "nunca", "nadie", "jamás", "solo", "prohibido", "prohibieron",
    "advirtieron", "dijeron", "no debí", "no debes",
    "maldito", "maldición", "peligro", "cuidado", "secreto",
    "escuché", "vi ", "descubrí", "encontré", "sobreviví", "trabajé",
    "entré", "confieso", "juré", "prometí", "recuerdo",
    "desapareció", "apareció", "cambió", "volvió", "se fue",
    "qué", "por qué", "cómo", "?", "si ", "cuando",
    "noche", "madrugada", "oscuridad",
]
PROHIBIDAS = ["testimonio real", "caso real", "100% real", "verídico", "evidencia", "pruebas", "autoridades",
              "filtrado", "es real", "historia real", "hechos reales"]
GENERICAS = ["misterio", "leyenda", "relato", "caso", "historia de terror", "el fantasma de"]

def limpiar_titulo(t):
    t = t.strip().strip('"').strip("'")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*[-|–]\s*relato de terror\s*$", "", t, flags=re.I)
    t = t.rstrip(".")
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
    if re.search(r"\b([012]?[0-9]):[0-5][0-9]\s*(am|pm|a\.m\.|p\.m\.)?\b", tl, re.I):
        s -= 3
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
    return puntuados[0][1][:100]

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

# =================================================================
# HISTORIA
# =================================================================
ESQUEMA_PLAN = """{
 "titulos": ["6 títulos candidatos de 45-68 caracteres, cada uno con ESTRUCTURA DISTINTA. NUNCA termines con '| Relato de Terror'"],
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
    sug  = "\n".join(f"- {s}" for s in sugerencias) or "Ninguna"
    prompt = f"""Eres showrunner de un canal de relatos de terror en español (México/Latam) con millones de vistas.
Diseña el PLAN de un relato de terror narrado en primera persona, presentado como un relato
compartido por un oyente de la comunidad y mejorado con IA para mayor inmersión
(~8-12 minutos, {NUM_CAPITULOS} capítulos).
TEMA: {tema['tema']} | ÁNGULO: {tema['angulo']}
LUGAR: {contexto}, en {estado_mx}, México
BÚSQUEDAS REALES EN YOUTUBE:
{sug}
TÍTULOS YA PUBLICADOS (no repetir estructura ni idea):
{prev}

REGLAS DE TÍTULO (CLAVE PARA CTR):
1. NUNCA termines el título con "| Relato de Terror".
2. Cada uno de los 6 títulos DEBE usar una estructura DISTINTA.
3. ⚠️ NO fijes una hora concreta como 3:33 AM, 3:00 AM, 4:44 AM. Ese patrón está sobre-explotado.
4. Usa mayúsculas solo para 1-2 palabras de impacto.
5. NO empieces los 6 títulos igual.
6. Evita errores ortográficos.

REGLAS DE CONTENIDO:
1. Prioriza escenarios cotidianos y relacionables.
2. El disclosure va en la descripción, NO en la narración.
3. El gancho debe ser lo más perturbador del relato.
4. Cada capítulo termina en cliffhanger, excepto el último.
5. El relato completo: estrictamente 1100-1400 palabras.

Responde SOLO con este JSON:
{ESQUEMA_PLAN}"""
    txt  = llm(prompt, temperature=0.9, max_tokens=2200, json_mode=True)
    plan = parsear_json(txt)
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
    return re.sub(r"\s+", " ", t).strip()

def generar_capitulos(plan, tema, contexto, estado_mx):
    caps   = plan["capitulos"][:NUM_CAPITULOS]
    indice = "\n".join(f"{i+1}. {c.get('titulo','')}: {c.get('resumen','')}" for i, c in enumerate(caps))
    textos = []
    for i, cap in enumerate(caps):
        previo = textos[-1][-700:] if textos else ""
        if i == 0:
            extra = f"Empieza EXACTAMENTE con esta frase de gancho: \"{plan['gancho']}\" y luego retrocede para dar contexto sin bajar la tensión."
        elif i == len(caps) - 1:
            extra = "Cierra con un final abierto e inquietante que deje una duda, sin explicar todo."
        else:
            extra = "Termina con un cliffhanger."
        prompt = f"""Escribe el CAPÍTULO {i+1} de {len(caps)} de un relato de terror en primera persona.
Narrador: {plan.get('protagonista','Marco')}. Año: {plan.get('anio_suceso','2015')}. Lugar: {contexto}, {estado_mx}, México.
Ángulo: {tema['angulo']}
Sinopsis: {plan.get('resumen','')}
ÍNDICE: {indice}
ESTE CAPÍTULO: {cap.get('titulo','')} -> {cap.get('resumen','')}
{extra}
{('FINAL DEL CAPÍTULO ANTERIOR: ' + previo) if previo else ''}
REGLAS: 250-350 palabras. Español mexicano coloquial. Sin listas, emojis, títulos ni acotaciones.
⚠️ Si mencionas hora, VARÍALA: no uses "3:33 AM".
Devuelve SOLO el texto."""
        texto = None
        for intento in range(3):
            t = llm(prompt, temperature=0.85, max_tokens=800)
            t = limpiar_texto_narracion(t) if t else ""
            if len(t.split()) >= 200:
                texto = t
                break
            print(f"⚠️ Capítulo {i+1} corto ({len(t.split())} pal.), reintento {intento+1}")
        if not texto:
            raise RuntimeError(f"No se pudo generar el capítulo {i+1}")
        textos.append(texto)
        print(f"   ✅ Capítulo {i+1}/{len(caps)}: {len(texto.split())} palabras")
    return textos

def expandir_texto(titulo, texto_actual):
    prompt = f"""Relato: "{titulo}". Final actual:\n\"\"\"\n{texto_actual[-500:]}\n\"\"\"\nAñade 200-300 palabras que profundicen el desenlace, mismo tono, sin resolver todo.\nDevuelve SOLO el texto."""
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

# =================================================================
# SEGMENTOS
# =================================================================
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

# =================================================================
# VOZ
# =================================================================
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
    ruta   = f"temp_audio_{nombre}.mp3"
    rate   = RATE_ETAPA.get(etapa, "+4%")
    pitch  = VOZ_CANAL["tono"]
    voces  = [VOZ_CANAL["voz"]] + [v for v in VOCES_RESPALDO if v != VOZ_CANAL["voz"]]
    for voz in voces:
        for intento in range(2):
            async def _go():
                communicate = edge_tts.Communicate(limpio, voz, rate=rate, pitch=pitch)
                await communicate.save(ruta)
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
        s["audio"]     = ruta
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
        s["dur"]    = s["dur_audio"] + PAUSA_ETAPA.get(s["etapa"], 0.5)
        t += s["dur"]
    return t

# =================================================================
# PEXELS
# =================================================================
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
        data  = pexels_get("https://api.pexels.com/v1/search",
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
        c  = VideoFileClip(ruta, audio=False)
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
        lote    = segs[ini:ini + 15]
        listado = "\n".join(f"{j+1}. {s['texto'][:230]}" for j, s in enumerate(lote))
        prompt  = f"""Eres director de fotografía de un canal de terror. Para CADA fragmento numerado devuelve UNA consulta
corta (2-4 palabras, EN INGLÉS) para buscar en Pexels una foto o video con atmósfera de terror nocturno.
Tema: {tema['tema']}.
Fragmentos:\n{listado}
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

# =================================================================
# RENDER
# =================================================================
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
            sz  = (int(self.size[0] * 1.2), int(self.size[1] * 1.2))
            im  = ImageOps.fit(Image.open(e["path"]).convert("RGB"), sz, Image.LANCZOS)
            arr = np.asarray(grade(im, e["etapa"]), dtype=np.float32) * vignette(sz, 1.0)
            self._img, self._ikey = Image.fromarray(arr.astype(np.uint8)), key
        return self._img

    def _frame_img(self, e, lt):
        base    = self._base(e)
        bw, bh  = base.size
        p       = min(max(lt / e["dur"], 0), 1) if e["dur"] > 0 else 0
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
        v  = self._vid
        d  = v.duration or 1
        off = e["off"] * max(0, d - e["dur"])
        tt  = max(0, min((off + lt) % d, d - 0.05))
        im  = ImageOps.fit(Image.fromarray(v.get_frame(tt)), self.size, Image.BILINEAR)
        return (np.asarray(im, dtype=np.float32) * self.vig_vid).astype(np.uint8)

    def frame(self, t):
        i  = max(0, bisect.bisect_right(self.starts, t) - 1)
        e  = self.esc[i]
        lt = t - e["inicio"]
        fr = self._frame_video(e, lt) if e["tipo"] == "video" else self._frame_img(e, lt)
        f  = 1.0
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
    narr   = CompositeAudioClip(clips)
    capas  = [narr]
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
    video  = VideoClip(render.frame, duration=total).set_audio(audio)
    video.write_videofile(salida, fps=FPS, codec="libx264", audio_codec="aac", audio_bitrate="192k", threads=4,
                          preset="veryfast", temp_audiofile="temp_audio_final.m4a",
                          ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
                          logger=None)
    render.cerrar()
    video.close()
    return salida

# =================================================================
# MINIATURA
# =================================================================
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
        data  = pexels_get("https://api.pexels.com/v1/search",
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
        gd   = ImageDraw.Draw(grad)
        for x in range(TW):
            gd.line([(x, 0), (x, TH)], fill=int(215 * max(0, 1 - x / (TW * 0.7)) ** 1.3))
        img = Image.composite(Image.new("RGB", (TW, TH), (0, 0, 0)), img, grad)
        arr = np.asarray(img, dtype=np.float32) * vignette((TW, TH), 1.0, 0.45)
        img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")

        lineas      = dividir_lineas(texto.upper().split()[:4])
        max_w, max_h = int(TW * 0.58), int(TH * 0.78)

        for size in range(150, 60, -6):
            font  = obtener_fuente(size)
            cajas = [font.getbbox(l) for l in lineas]
            alto  = sum(b[3] - b[1] for b in cajas) + 18 * (len(lineas) - 1)
            if max(b[2] - b[0] for b in cajas) <= max_w and alto <= max_h:
                break

        acento = random.choice([(255, 214, 0), (255, 45, 45)])
        y      = (TH - alto) // 2 + 10
        pos    = []
        for l, b in zip(lineas, cajas):
            pos.append((l, 60, y - b[1]))
            y += (b[3] - b[1]) + 18

        glow  = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        for l, x, yy in pos:
            gdraw.text((x, yy), l, font=font, fill=acento + (255,), stroke_width=10, stroke_fill=acento + (255,))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(24)))

        draw  = ImageDraw.Draw(img)
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

# =================================================================
# SEO  ← FIX 1 y FIX 2 aquí
# =================================================================
def construir_tags(plan, tema, sugerencias, estado_mx=""):
    """
    FIX 1 v6.1:
    - Eliminado "historia real" del filtro (es un tag válido y de alto volumen).
    - Añadido parámetro estado_mx para incluir tags long-tail de estado.
    - Tags de estado van al principio para que aterricen antes del límite de 480 chars.
    """
    estado_lower = estado_mx.lower() if estado_mx else ""

    # Tags de estado — long-tail geolocalizado, alta intención de búsqueda
    tags_estado = []
    if estado_lower:
        tags_estado = [
            f"terror {estado_lower}",
            f"leyendas {estado_lower}",
            f"misterio {estado_lower}",
        ]

    base = [
        "terror", "miedo", "paranormal", "horror",
        "relato de terror", "relatos de terror", "historias de terror",
        "historia real", "terror mexicano", "relatos paranormales",
        "sombras de medianoche", "narrativa de terror", "audio relatos",
        "relatos narrados", "creepypasta", "leyendas urbanas",
    ]

    extra = plan.get("tags", [])
    if isinstance(extra, str):
        extra = [x.strip() for x in extra.split(",")]

    finales, total = [], 0
    for t in tema["keywords"] + list(extra) + sugerencias + tags_estado + base:
        t     = re.sub(r"[<>]", " ", str(t)).strip().lower()
        # FIX: solo filtramos los realmente problemáticos; "historia real" ya no se filtra
        if any(x in t for x in ("100% real", "veridico", "verídico", "testimonio real",
                                 "caso real", "hechos reales")):
            continue
        costo = len(t) + 1 + (2 if " " in t else 0)
        if 2 <= len(t) <= 40 and t not in finales and total + costo <= 480:
            finales.append(t)
            total += costo
    return finales

def construir_hashtags(tema):
    hs = ["#RelatosDeTerror", "#Terror", "#Paranormal"] + tema.get("hashtags", [])[:2] + ["#Mexico"]
    return " ".join(hs[:6])

def construir_descripcion(plan, tema, caps_ts, sugerencias, hashtags):
    """
    FIX 2 v6.1:
    Hashtags SIEMPRE al final absoluto de la descripción.
    YouTube muestra los primeros 3 hashtags encima del título — enterrarlos
    en medio del disclosure los desperdiciaba.
    """
    gancho = plan.get("descripcion_gancho", " ").strip() or plan["gancho"]
    if "relato de terror" not in gancho.lower()[:220]:
        gancho = "Relato de terror: " + gancho

    capitulos = "\n".join(f"{ts} {t}" for ts, t in caps_ts)
    rel        = ", ".join(sugerencias[:5])

    partes = [
        gancho,
        f"🔔 Suscríbete para un relato nuevo cada semana: {CANAL_LINK}?sub_confirmation=1",
        f"⏰ CAPÍTULOS\n{capitulos}",
        f"📖 SOBRE ESTE RELATO\n{plan.get('resumen', '')}",
        (f"🔎 Temas relacionados: {rel}" if rel else ""),
        f"📱 Facebook: {FACEBOOK_LINK}",
    ]

    if ACTIVAR_DISCLOSURE_IA:
        partes.append(DISCLOSURE_TEXT.strip())

    # Hashtags van SIEMPRE al final
    partes.append(hashtags)

    desc = "\n\n".join(p for p in partes if p and p.strip())
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
            d  = s["dur_audio"] * len(tr) / len(pal)
            lineas.append(f"{n}\n{ts(t)} --> {ts(t + d)}\n{' '.join(tr)}\n")
            n, t = n + 1, t + d
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    return ruta

# =================================================================
# PUBLICACIÓN
# =================================================================
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
    slot  = ahora.replace(hour=HORA_PICO, minute=0, second=0, microsecond=0)
    if slot - ahora < timedelta(minutes=10):
        slot += timedelta(days=1)
    return slot

def utc_iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

def subir_video(youtube, ruta, titulo, descripcion, tags, publish_at=None):
    status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True}
    if publish_at:
        status.update({"privacyStatus": "private", "publishAt": publish_at})

    body  = {"snippet": {"title": titulo[:100], "description": descripcion[:5000], "tags": tags,
                         "categoryId": "24", "defaultLanguage": "es", "defaultAudioLanguage": "es"},
             "status": status}

    media     = MediaFileUpload(ruta, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req       = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    resp, reintentos = None, 0
    while resp is None:
        try:
            st, resp = req.next_chunk()
            if st:
                print(f"   ⬆️ {int(st.progress() * 100)}%")
        except (HttpError, ssl.SSLEOFError, ConnectionError, socket.timeout, OSError) as e:
            es_reintento = isinstance(e, HttpError) and e.resp.status in (429, 500, 502, 503, 504)
            es_reintento = es_reintento or isinstance(e, (ssl.SSLEOFError, ConnectionError, socket.timeout, OSError))
            if es_reintento and reintentos < 8:
                reintentos += 1
                espera = 2 ** reintentos
                print(f"⚠️ Error red/SSL (intento {reintentos}/8), reintentando en {espera}s...")
                time.sleep(espera)
                continue
            print(f"❌ Error fatal en la subida: {type(e).__name__}: {e}")
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
            youtube.captions().insert(part="snippet",
                                      body={"snippet": {"videoId": vid, "language": "es", "name": "Español", "isDraft": False}},
                                      media_body=MediaFileUpload(srt, mimetype="application/octet-stream")).execute()
            print("✅ Subtítulos subidos")
        except Exception as e:
            print(f"⚠️ Subtítulos: {e}")
    if PLAYLIST_ID:
        try:
            youtube.playlistItems().insert(part="snippet",
                                           body={"snippet": {"playlistId": PLAYLIST_ID,
                                                             "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
            print("✅ Añadido a playlist")
        except Exception as e:
            print(f"⚠️ Playlist: {e}")
    if comentario:
        try:
            youtube.commentThreads().insert(part="snippet",
                                            body={"snippet": {"videoId": vid, "topLevelComment": {
                                                "snippet": {"textOriginal": comentario}}}}).execute()
            print("✅ Comentario publicado (fíjalo a mano en Studio)")
        except Exception as e:
            print(f"⚠️ Comentario: {e}\n   Texto para fijar: {comentario}")

# =================================================================
# SHORT EMBUDO
# =================================================================
def crear_short(segs_orig, plan, fondo, salida="short_final.mp4"):
    segs   = [{**s} for s in segs_orig]
    sel, t = [], 0.0
    for s in segs:
        if sel and t + s["dur"] > 50:
            break
        sel.append(s)
        t += s["dur"]
        if t >= 32:
            break
    t0 = 0.0
    for s in sel:
        s["inicio"] = t0
        t0 += s["dur"]
    t = t0

    cta    = generar_audio("La historia completa ya está en el canal. Suscríbete para no perderte la siguiente.", "cta", "resolucion")
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

# =================================================================
# MÚSICA
# =================================================================
def buscar_archivo(nombre):
    for root, _, files in os.walk("."):
        if "/." in root or "\\." in root:
            continue
        if nombre in files:
            return os.path.join(root, nombre)
    return None

def seleccionar_fondo(estado):
    ultimos = estado["ultimos_fondos"]
    disp    = [f for f in FONDOS_DISPONIBLES if f not in ultimos[-3:]] or FONDOS_DISPONIBLES[:]
    random.shuffle(disp)
    for f in disp + FONDOS_DISPONIBLES:
        ruta = buscar_archivo(f)
        if ruta:
            estado["ultimos_fondos"] = (ultimos + [f])[-10:]
            print(f"🎵 Fondo: {ruta}")
            return ruta
    print("⚠️ Sin música de fondo")
    return None

# =================================================================
# VALIDACIONES
# =================================================================
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
    yt = crear_cliente_youtube()
    if yt is None:
        print("❌ YOUTUBE_USER_TOKEN inválido/expirado")
        sys.exit(1)
    try:
        yt.channels().list(part="id", mine=True).execute()
        print("✅ Credenciales válidas (DeepSeek, Pexels, YouTube).")
    except HttpError as e:
        err_str = str(e)
        if "insufficientPermissions" in err_str or "insufficient authentication scopes" in err_str:
            print("⚠️ Token sin permiso de lectura (youtube.readonly). El bot publica igual.")
        elif "401" in err_str or "invalid_grant" in err_str or "invalid_token" in err_str:
            print(f"❌ YouTube token expirado o revocado: {e}")
            sys.exit(1)
        else:
            print(f"❌ Error autenticando YouTube: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ YouTube token inválido: {e}")
        sys.exit(1)
    return yt

# =================================================================
# MAIN  ← FIX 3: pasa estado_mx a construir_tags
# =================================================================
def main():
    youtube = verificar_envs()
    limpiar_temporales()
    estado  = cargar_estado()

    if os.getenv("FORCE_PUBLISH") == "true":
        print("⚡ FORCE_PUBLISH activo")
    elif not deberia_publicar(estado):
        sys.exit(0)

    print("=" * 70)
    print("👻 SOMBRAS DE MEDIANOCHE - BOT v6.1")
    print(f"📅 {datetime.now(TZ):%Y-%m-%d %H:%M} | 🎤 {VOZ_CANAL['voz']} | 🎬 videos: {USAR_VIDEOS}")
    print(f"📚 Temas disponibles: {len(TEMAS)}")
    print("=" * 70)

    actualizar_rendimiento(youtube, estado)
    tema       = elegir_tema(estado, youtube)
    contexto   = random.choice(tema["contextos"])
    estado_mx  = random.choice(ESTADOS_MEXICO)
    sugerencias = list(dict.fromkeys(
        sugerencias_youtube(tema["seed"]) +
        sugerencias_youtube("relato de terror " + tema["keywords"][0])
    ))[:10]
    print(f"🔎 Sugerencias YouTube: {sugerencias[:5]}")
    fondo = seleccionar_fondo(estado)

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
    print(f"📌 Título: {titulo}")
    print(f"📍 Estado: {estado_mx}")

    capitulos_txt = generar_capitulos(plan, tema, contexto, estado_mx)
    n_caps = len(capitulos_txt)
    segs   = crear_segmentos(capitulos_txt)
    print(f"🧩 {len(segs)} segmentos, {sum(len(c.split()) for c in capitulos_txt)} palabras")

    segs  = sintetizar(segs)
    total = construir_timeline(segs)

    intentos = 0
    while total < DURACION_MINIMA_SEGUNDOS and intentos < MAX_INTENTOS_EXPANSION:
        print(f"⚠️ {total/60:.1f} min < mínimo. Expandiendo ({intentos+1})...")
        extra = expandir_texto(titulo, " ".join(s["texto"] for s in segs))
        intentos += 1
        if not extra:
            break
        nuevos = [{"cap": n_caps - 1, "texto": p, "cap_ini": False, "etapa": "resolucion",
                   "id": f"x{intentos}_{k}", "expansion": True}
                  for k, p in enumerate(dividir_en_segmentos(extra))]
        segs  += sintetizar(nuevos)
        total  = construir_timeline(segs)

    if total > DURACION_MAXIMA_SEGUNDOS:
        print(f"⚠️ {total/60:.1f} min > máximo. Recortando expansiones...")
        while total > DURACION_MAXIMA_SEGUNDOS:
            idx = next((i for i in range(len(segs) - 1, -1, -1) if segs[i].get("expansion")), None)
            if idx is None:
                break
            segs.pop(idx)
            total = construir_timeline(segs)

    if total < DURACION_MINIMA_SEGUNDOS:
        print("❌ Duración insuficiente. Abortando.")
        sys.exit(1)

    outro = [{"cap": n_caps - 1, "texto": random.choice(OUTROS), "cap_ini": False,
              "etapa": "resolucion", "id": "outro", "outro": True}]
    segs  += sintetizar(outro)
    total  = construir_timeline(segs)
    print(f"⏱️ Duración final: {total/60:.1f} min")

    consultas = planificar_consultas(segs, tema, anio)
    for i, s in enumerate(segs):
        n = max(1, round(s["dur"] / SEG_ESCENA))
        print(f"🖼️ {i+1}/{len(segs)} [{s['etapa']}] '{consultas[i]}' x{n}")
        s["medios"] = obtener_medios(i, s["etapa"], consultas[i], n, tema)

    caps_ts = []
    for c in range(n_caps):
        primero = next((s for s in segs if s["cap"] == c), None)
        nombre  = str(plan["capitulos"][c].get("titulo", f"Parte {c+1}"))[:50] if c < len(plan["capitulos"]) else f"Parte {c+1}"
        if primero:
            caps_ts.append((fmt_ts(primero["inicio"]), nombre))
    caps_ts[0] = ("00:00", caps_ts[0][1])

    hashtags    = construir_hashtags(tema)
    descripcion = construir_descripcion(plan, tema, caps_ts, sugerencias, hashtags)
    # FIX 3: pasa estado_mx para tags long-tail de estado
    tags        = construir_tags(plan, tema, sugerencias, estado_mx)
    srt         = generar_srt(segs, "subtitulos.srt")

    print(f"🏷️  Tags ({len(tags)}): {', '.join(tags[:6])}...")

    portada   = elegir_texto_portada(plan.get("palabras_portada"), titulo)
    base_mini = elegir_base_miniatura(
        re.sub(r"[^a-zA-Z ]", " ", str(plan.get("miniatura_escena", "dark hallway door"))) or "dark hallway door"
    )
    miniatura = "miniatura.jpg" if crear_miniatura(base_mini, portada, "miniatura.jpg") else None

    escenas     = construir_escenas(segs)
    audio, _    = mezclar_audio(segs, total, fondo)
    print("🎬 Renderizando video largo...")
    renderizar(escenas, total, audio, (W, H), "video_final.mp4")

    slot = proximo_slot() if PROGRAMAR_PICO else None
    print(f"🕖 Programación: {slot:%Y-%m-%d %H:%M} CDMX" if slot else "📤 Publicación inmediata")

    vid        = subir_video(youtube, "video_final.mp4", titulo, descripcion, tags, utc_iso(slot) if slot else None)
    comentario = str(plan.get("pregunta_comentario") or "¿Tú qué habrías hecho? Te leo 👇")
    extras_post_subida(youtube, vid, miniatura, srt, comentario)

    if GENERAR_SHORT:
        try:
            print("🎞️ Creando Short embudo...")
            crear_short(segs, plan, fondo)
            t_short = str(plan.get("titulo_short") or titulo)[:88] + " #Shorts"
            d_short = (f"Historia completa 👉 https://youtu.be/{vid}\n\n"
                       f"Suscríbete: {CANAL_LINK}?sub_confirmation=1\n\n"
                       f"#Shorts {hashtags}" + (DISCLOSURE_TEXT if ACTIVAR_DISCLOSURE_IA else ""))
            slot_s = utc_iso(slot + timedelta(minutes=30)) if slot else None
            subir_video(youtube, "short_final.mp4", t_short, d_short, tags[:15] + ["shorts"], slot_s)
        except Exception as e:
            print(f"⚠️ Short falló (el video largo ya está subido): {e}")
            traceback.print_exc()

    ahora = datetime.now(TZ).isoformat()
    guardar_titulo_largo(titulo)
    guardar_tema(tema["tema"])
    estado["videos"].append({"id": vid, "titulo": titulo, "tema": tema["tema"], "fecha": ahora})
    estado["videos"]         = estado["videos"][-60:]
    estado["temas_recientes"] = (estado["temas_recientes"] + [tema["tema"]])[-6:]
    estado["ultima_publicacion"]          = ahora
    estado["ultima_publicacion_exitosa"]  = datetime.now(TZ).date().isoformat()
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
