# -*- coding: utf-8 -*-
"""
SOMBRAS DE MEDIANOCHE - Bot de Shorts v7.2
Cambios v7.2:
  - acciones limpiadas a verbos simples en pasado (sin frases como "entré a su casa")
  - fórmulas divididas en FORMULAS_NARRATIVAS (usan {pasado}) y FORMULAS_NEUTRAS (solo {lugar})
  - Facebook vía MAKE REINTEGRADO (se había perdido en v7.1)
  - calcular_score_titulo penaliza TESTIMONIO/ADVERTENCIA/3:33 con -12
v7.1 - 35 temas, sin prefijos rígidos
v6.3 - Validación tolerante de token
"""
import asyncio
import json
import os
import random
import re
import sys
import time
import traceback
from datetime import datetime, timedelta
import pytz

import edge_tts
import numpy as np
import requests
import urllib3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from moviepy.editor import (
    AudioFileClip, CompositeAudioClip, ImageClip,
    concatenate_videoclips,
)
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance

try:
    import json5
except ImportError:
    json5 = None

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
ANALYTICS_FILE = "analytics_elite.json"
MAX_TEMAS_HISTORIAL = 20
ACTIVAR_DISCLOSURE_IA = True

DISCLOSURE_TEXT = (
    "\n📖 Relato compartido por un oyente de la comunidad, narrado con voz "
    "sintética y mejorado con IA para una mayor inmersión."
)

MAX_SHORTS_DIA = 2

# ================================================================
# 35 TEMAS PARANORMALES
# acciones = verbos simples en pasado 1ª persona (sin frases).
# lugares_t = lugares con artículo (el/la/los/las...).
# ================================================================
TEMAS_VIRALES_2024 = [
    # === CRIATURAS Y SERES (9) ===
    {
        "tema": "brujas", "keywords": ["bruja", "hechicería", "pueblo"],
        "contextos": ["casa al final del pueblo", "cerro de noche", "camino al panteón", "mercado viejo"],
        "acciones": ["consulté", "busqué", "entré", "toqué"],
        "lugares_t": ["la casa de la bruja", "el cerro", "el camino al panteón", "el mercado viejo"],
        "criaturas": ["old woman dark", "candles ritual night", "herbs hanging dark"],
        "emoji": "🧙", "hashtags": ["#Brujas", "#Hechicería"],
        "busquedas": 480000, "competencia": "media", "ctr_potencial": 9.8, "retencion_objetivo": 82,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 16.0,
    },
    {
        "tema": "duendes", "keywords": ["duende", "casa", "travesuras"],
        "contextos": ["casa del pueblo", "rancho familiar", "milpa", "casa antigua"],
        "acciones": ["escuché", "encontré", "vi", "sentí"],
        "lugares_t": ["la casa del pueblo", "el rancho", "la milpa", "el cuarto de los niños"],
        "criaturas": ["old mexican house night", "small footprints dust", "rustic ranch night"],
        "emoji": "👺", "hashtags": ["#Duendes", "#DuendesReales"],
        "busquedas": 420000, "competencia": "baja", "ctr_potencial": 9.5, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "16-50", "engagement_rate": 15.5,
    },
    {
        "tema": "aluxes", "keywords": ["alux", "mayas", "milpa"],
        "contextos": ["milpa yucateca", "ruinas mayas", "cenote", "selva"],
        "acciones": ["entré", "toqué", "corté", "crucé"],
        "lugares_t": ["la milpa", "las ruinas mayas", "el cenote", "la selva"],
        "criaturas": ["mayan ruins night", "jungle fog night", "cenote dark water"],
        "emoji": "🗿", "hashtags": ["#Aluxes", "#LeyendasMayas"],
        "busquedas": 320000, "competencia": "baja", "ctr_potencial": 9.2, "retencion_objetivo": 78,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 14.5,
    },
    {
        "tema": "chupacabras", "keywords": ["chupacabras", "ganado", "rancho"],
        "contextos": ["rancho ganadero", "monte", "sierra", "desierto"],
        "acciones": ["vi", "escuché", "encontré", "perseguí"],
        "lugares_t": ["el rancho", "el monte", "la sierra", "el corral"],
        "criaturas": ["mexican ranch night", "dead livestock field night", "desert ranch night"],
        "emoji": "🐐", "hashtags": ["#Chupacabras", "#CriaturasReales"],
        "busquedas": 550000, "competencia": "media", "ctr_potencial": 9.7, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 16.0,
    },
    {
        "tema": "nahual", "keywords": ["nahual", "brujo", "animal"],
        "contextos": ["pueblo viejo", "cerro", "camino de tierra", "casa del brujo"],
        "acciones": ["vi", "seguí", "enfrenté", "descubrí"],
        "lugares_t": ["el cerro", "el camino de tierra", "la casa del vecino", "el pueblo"],
        "criaturas": ["mexican village night", "dirt road night fog", "coyote eyes dark"],
        "emoji": "🐺", "hashtags": ["#Nahual", "#LeyendasMexicanas"],
        "busquedas": 390000, "competencia": "media", "ctr_potencial": 9.4, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.0,
    },
    {
        "tema": "llorona", "keywords": ["llorona", "río", "llanto"],
        "contextos": ["río del pueblo", "panteón", "puente viejo", "camino a la iglesia"],
        "acciones": ["escuché", "seguí", "vi", "crucé"],
        "lugares_t": ["el río", "el panteón", "el puente viejo", "el camino a la iglesia"],
        "criaturas": ["mexican river night fog", "old bridge night", "woman silhouette river"],
        "emoji": "💧", "hashtags": ["#LaLlorona", "#LeyendasMexicanas"],
        "busquedas": 720000, "competencia": "alta", "ctr_potencial": 10.2, "retencion_objetivo": 84,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "16-60", "engagement_rate": 17.5,
    },
    {
        "tema": "charro_negro", "keywords": ["charro", "jinete", "diablo"],
        "contextos": ["camino de terracería", "carretera solitaria", "encrucijada", "puente viejo"],
        "acciones": ["encontré", "vi", "esquivé", "rechacé"],
        "lugares_t": ["el camino de terracería", "la encrucijada", "el puente viejo", "la carretera"],
        "criaturas": ["dark horseman silhouette", "black horse night fog", "crossroads night mexico"],
        "emoji": "🐎", "hashtags": ["#CharroNegro", "#LeyendasMexicanas"],
        "busquedas": 480000, "competencia": "media", "ctr_potencial": 9.6, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.5,
    },
    {
        "tema": "skinwalker", "keywords": ["skinwalker", "criatura", "bosque"],
        "contextos": ["carretera solitaria", "bosque profundo", "sierra aislada", "desierto"],
        "acciones": ["vi", "seguí", "escapé", "enfrenté"],
        "lugares_t": ["el bosque", "la carretera", "la sierra", "el desierto"],
        "criaturas": ["dark forest fog", "desert road night", "eyes in the dark"],
        "emoji": "👁️", "hashtags": ["#Skinwalker", "#CriaturasDeLaNoche"],
        "busquedas": 410000, "competencia": "media", "ctr_potencial": 9.0, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-45", "engagement_rate": 15.0,
    },
    {
        "tema": "aliens", "keywords": ["ovni", "extraterrestre", "luces"],
        "contextos": ["campo abierto", "carretera solitaria", "sierra", "rancho"],
        "acciones": ["vi", "seguí", "grabé", "escapé"],
        "lugares_t": ["el campo", "la carretera", "la sierra", "el rancho"],
        "criaturas": ["ufo lights sky night", "strange light rural night", "desert night sky object"],
        "emoji": "🛸", "hashtags": ["#Ovnis", "#Extraterrestres"],
        "busquedas": 580000, "competencia": "alta", "ctr_potencial": 9.5, "retencion_objetivo": 82,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 16.0,
    },
    # === ENTIDADES PARANORMALES (7) ===
    {
        "tema": "fantasmas", "keywords": ["fantasma", "aparición", "casa"],
        "contextos": ["casa antigua", "departamento", "habitación de hotel", "edificio viejo"],
        "acciones": ["escuché", "vi", "sentí", "entré"],
        "lugares_t": ["la casa antigua", "el departamento", "la habitación", "el edificio viejo"],
        "criaturas": ["dark hallway ghost shadow", "old house interior night", "door half open dark"],
        "emoji": "👻", "hashtags": ["#Fantasmas", "#Aparecidos"],
        "busquedas": 620000, "competencia": "alta", "ctr_potencial": 9.0, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-60", "engagement_rate": 15.5,
    },
    {
        "tema": "demonios", "keywords": ["demonio", "posesión", "invocación"],
        "contextos": ["casa abandonada", "sótano", "iglesia abandonada", "cementerio"],
        "acciones": ["consulté", "entré", "recé", "toqué"],
        "lugares_t": ["el sótano", "la iglesia abandonada", "la casa abandonada", "el cementerio"],
        "criaturas": ["dark basement horror", "abandoned church night", "candles dark room"],
        "emoji": "😈", "hashtags": ["#Demonios", "#TerrorOculto"],
        "busquedas": 490000, "competencia": "media", "ctr_potencial": 9.8, "retencion_objetivo": 82,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-50", "engagement_rate": 16.0,
    },
    {
        "tema": "posesion", "keywords": ["posesión", "familia", "cambio"],
        "contextos": ["casa familiar", "habitación", "iglesia", "convento"],
        "acciones": ["vi", "ayudé", "recé", "enfrenté"],
        "lugares_t": ["la casa familiar", "la habitación", "la iglesia", "el convento"],
        "criaturas": ["dark bedroom horror", "candlelit church interior", "priest silhouette dark"],
        "emoji": "🕯️", "hashtags": ["#Posesión", "#Exorcismo"],
        "busquedas": 440000, "competencia": "media", "ctr_potencial": 9.6, "retencion_objetivo": 82,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.5,
    },
    {
        "tema": "exorcismo", "keywords": ["exorcismo", "sacerdote", "demonio"],
        "contextos": ["iglesia vieja", "casa del pueblo", "convento abandonado", "capilla"],
        "acciones": ["presencié", "ayudé", "recé", "grabé"],
        "lugares_t": ["la iglesia vieja", "la capilla", "el convento", "la casa del pueblo"],
        "criaturas": ["candlelit church dark", "priest silhouette", "rosary candle dark"],
        "emoji": "✝️", "hashtags": ["#Exorcismo", "#TerrorReligioso"],
        "busquedas": 420000, "competencia": "media", "ctr_potencial": 9.5, "retencion_objetivo": 82,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.0,
    },
    {
        "tema": "poltergeist", "keywords": ["poltergeist", "objetos", "casa"],
        "contextos": ["casa familiar", "departamento", "ático", "habitación"],
        "acciones": ["escuché", "vi", "sentí", "viví"],
        "lugares_t": ["la casa", "el departamento", "el ático", "la habitación"],
        "criaturas": ["objects flying room dark", "slammed door dark", "scattered objects floor dark"],
        "emoji": "🌀", "hashtags": ["#Poltergeist", "#CasaEmbrujada"],
        "busquedas": 380000, "competencia": "media", "ctr_potencial": 9.0, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 14.5,
    },
    {
        "tema": "muneca_poseida", "keywords": ["muñeca", "poseída", "maldita"],
        "contextos": ["casa antigua", "cuarto de niña", "ático", "tienda de antigüedades"],
        "acciones": ["compré", "encontré", "heredé", "guardé"],
        "lugares_t": ["la tienda de antigüedades", "el cuarto", "el ático", "la casa heredada"],
        "criaturas": ["creepy doll dark room", "old doll chair night", "doll face closeup dark"],
        "emoji": "🎎", "hashtags": ["#MuñecaMaldita", "#ObjetoMaldito"],
        "busquedas": 460000, "competencia": "media", "ctr_potencial": 9.7, "retencion_objetivo": 82,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 16.0,
    },
    {
        "tema": "payaso_maldito", "keywords": ["payaso", "circo", "aparición"],
        "contextos": ["circo abandonado", "parque", "calle solitaria", "feria"],
        "acciones": ["vi", "entré", "crucé", "encontré"],
        "lugares_t": ["el circo abandonado", "el parque", "la calle", "la feria"],
        "criaturas": ["creepy clown dark", "abandoned circus night", "empty carnival night"],
        "emoji": "🤡", "hashtags": ["#PayasoMaldito", "#TerrorPsicológico"],
        "busquedas": 400000, "competencia": "media", "ctr_potencial": 9.4, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "16-45", "engagement_rate": 15.0,
    },
    # === LUGARES EMBRUJADOS (9) ===
    {
        "tema": "casa_embrujada", "keywords": ["casa", "embrujada", "familia"],
        "contextos": ["casa nueva", "casa de campo", "casa heredada", "casa en venta"],
        "acciones": ["compré", "heredé", "renté", "entré"],
        "lugares_t": ["la casa nueva", "la casa del campo", "la casa heredada", "la casa en venta"],
        "criaturas": ["abandoned mexican house night", "haunted house fog", "dark house interior hallway"],
        "emoji": "🏚️", "hashtags": ["#CasaEmbrujada", "#Fantasmas"],
        "busquedas": 520000, "competencia": "media", "ctr_potencial": 9.3, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.5,
    },
    {
        "tema": "hospital", "keywords": ["hospital", "turno", "paciente"],
        "contextos": ["hospital viejo", "clínica cerrada", "ala clausurada", "morgue"],
        "acciones": ["trabajé", "entré", "recorrí", "vi"],
        "lugares_t": ["el hospital viejo", "la clínica", "el ala clausurada", "la morgue"],
        "criaturas": ["hospital corridor dark", "abandoned hospital", "morgue dark"],
        "emoji": "🏥", "hashtags": ["#HospitalEmbrujado", "#TerrorNocturno"],
        "busquedas": 410000, "competencia": "media", "ctr_potencial": 8.9, "retencion_objetivo": 78,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "20-50", "engagement_rate": 14.5,
    },
    {
        "tema": "velador", "keywords": ["velador", "turno", "cámaras"],
        "contextos": ["fábrica abandonada", "bodega", "escuela vacía", "estacionamiento"],
        "acciones": ["trabajé", "entré", "patrullé", "recorrí"],
        "lugares_t": ["la fábrica", "la bodega", "la escuela vacía", "el estacionamiento"],
        "criaturas": ["security guard night", "empty factory night", "warehouse dark"],
        "emoji": "👮", "hashtags": ["#Velador", "#TurnoDeNoche"],
        "busquedas": 460000, "competencia": "baja", "ctr_potencial": 9.5, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-45", "engagement_rate": 15.5,
    },
    {
        "tema": "carretera", "keywords": ["carretera", "viaje", "taxi"],
        "contextos": ["carretera federal", "gasolinera", "túnel", "desvío"],
        "acciones": ["conduje", "viajé", "crucé", "manejé"],
        "lugares_t": ["la carretera", "la gasolinera", "el túnel", "el desvío"],
        "criaturas": ["highway night fog", "taxi night city", "road tunnel dark"],
        "emoji": "🚗", "hashtags": ["#CarreteraMaldita", "#TerrorNocturno"],
        "busquedas": 540000, "competencia": "media", "ctr_potencial": 9.0, "retencion_objetivo": 82,
        "duracion_optima": 55, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 16.0,
    },
    {
        "tema": "hotel_embrujado", "keywords": ["hotel", "habitación", "huésped"],
        "contextos": ["hotel viejo", "motel de carretera", "hostal", "hotel de pueblo"],
        "acciones": ["entré", "renté", "dormí", "vi"],
        "lugares_t": ["el hotel viejo", "el motel", "el hostal", "la habitación"],
        "criaturas": ["hotel corridor dark", "old hotel room night", "motel neon night"],
        "emoji": "🏨", "hashtags": ["#HotelEmbrujado", "#Fantasmas"],
        "busquedas": 480000, "competencia": "media", "ctr_potencial": 9.2, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.0,
    },
    {
        "tema": "cementerio", "keywords": ["panteón", "tumba", "noche"],
        "contextos": ["panteón del pueblo", "cementerio antiguo", "cripta", "mausoleo"],
        "acciones": ["entré", "crucé", "visité", "escuché"],
        "lugares_t": ["el panteón", "el cementerio", "la cripta", "el mausoleo"],
        "criaturas": ["cemetery night fog", "old mexican pantheon", "grave candles night"],
        "emoji": "⚰️", "hashtags": ["#Cementerio", "#TerrorNocturno"],
        "busquedas": 440000, "competencia": "media", "ctr_potencial": 9.3, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.5,
    },
    {
        "tema": "bosque_maldito", "keywords": ["bosque", "sierra", "perdido"],
        "contextos": ["bosque profundo", "sierra", "cabaña", "camino de tierra"],
        "acciones": ["entré", "caminé", "escapé", "acampé"],
        "lugares_t": ["el bosque", "la sierra", "la cabaña", "el camino de tierra"],
        "criaturas": ["dark forest fog night", "cabin in woods night", "tall trees silhouette night"],
        "emoji": "🌲", "hashtags": ["#BosqueMaldito", "#Criaturas"],
        "busquedas": 430000, "competencia": "media", "ctr_potencial": 9.1, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.0,
    },
    {
        "tema": "mina", "keywords": ["mina", "túnel", "accidente"],
        "contextos": ["mina abandonada", "túnel", "cerro", "pueblo minero"],
        "acciones": ["entré", "bajé", "exploré", "escuché"],
        "lugares_t": ["la mina", "el túnel", "el cerro", "el pueblo minero"],
        "criaturas": ["abandoned mine entrance", "mine tunnel dark", "old mining town night"],
        "emoji": "⛏️", "hashtags": ["#MinaAbandonada", "#Fantasmas"],
        "busquedas": 360000, "competencia": "baja", "ctr_potencial": 9.0, "retencion_objetivo": 78,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 14.5,
    },
    {
        "tema": "hacienda", "keywords": ["hacienda", "heredada", "antigua"],
        "contextos": ["hacienda vieja", "ex-hacienda", "rancho heredado", "casona"],
        "acciones": ["heredé", "compré", "visité", "dormí"],
        "lugares_t": ["la hacienda", "la casona", "el rancho heredado", "la ex-hacienda"],
        "criaturas": ["old hacienda night", "colonial house dark", "mexican hacienda night fog"],
        "emoji": "🏛️", "hashtags": ["#HaciendaEmbrujada", "#Fantasmas"],
        "busquedas": 340000, "competencia": "baja", "ctr_potencial": 8.8, "retencion_objetivo": 78,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "20-60", "engagement_rate": 14.0,
    },
    # === OCULTISMO (8) ===
    {
        "tema": "ritual", "keywords": ["ritual", "invocación", "maldición"],
        "contextos": ["cementerio antiguo", "casa abandonada", "cueva", "iglesia en ruinas"],
        "acciones": ["hice", "participé", "encontré", "interrumpí"],
        "lugares_t": ["el cementerio", "la casa abandonada", "la cueva", "la iglesia en ruinas"],
        "criaturas": ["candles dark room", "old cemetery night", "cave darkness"],
        "emoji": "🔮", "hashtags": ["#Rituales", "#Ocultismo"],
        "busquedas": 470000, "competencia": "baja", "ctr_potencial": 9.8, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "16-45", "engagement_rate": 15.5,
    },
    {
        "tema": "ouija", "keywords": ["ouija", "tabla", "espíritus"],
        "contextos": ["casa de amigo", "cuarto oscuro", "sótano", "habitación de hotel"],
        "acciones": ["usé", "encontré", "quemé", "escondí"],
        "lugares_t": ["la tabla", "el cuarto oscuro", "el sótano", "la habitación"],
        "criaturas": ["ouija board candles", "dark room hands", "seance circle dark"],
        "emoji": "🔯", "hashtags": ["#Ouija", "#TerrorOculto"],
        "busquedas": 510000, "competencia": "media", "ctr_potencial": 9.7, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "16-45", "engagement_rate": 16.0,
    },
    {
        "tema": "pacto_demonio", "keywords": ["pacto", "demonio", "trato"],
        "contextos": ["encrucijada", "casa abandonada", "camino solitario", "cementerio"],
        "acciones": ["hice", "acepté", "rompí", "firmé"],
        "lugares_t": ["la encrucijada", "la casa abandonada", "el camino", "el cementerio"],
        "criaturas": ["crossroads night dark", "candles pentagram dark", "old contract candle"],
        "emoji": "📜", "hashtags": ["#Pacto", "#TerrorOculto"],
        "busquedas": 400000, "competencia": "media", "ctr_potencial": 9.5, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-50", "engagement_rate": 15.0,
    },
    {
        "tema": "maldicion", "keywords": ["maldición", "familia", "herencia"],
        "contextos": ["casa familiar", "pueblo", "cementerio", "hacienda"],
        "acciones": ["heredé", "descubrí", "rompí", "cargué"],
        "lugares_t": ["la casa familiar", "el pueblo", "el cementerio", "la hacienda"],
        "criaturas": ["old family photo dark", "abandoned house interior", "old diary pages"],
        "emoji": "🩸", "hashtags": ["#Maldición", "#TerrorFamiliar"],
        "busquedas": 380000, "competencia": "media", "ctr_potencial": 9.3, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.0,
    },
    {
        "tema": "objeto_maldito", "keywords": ["objeto", "maldito", "maldición"],
        "contextos": ["tienda de antigüedades", "tianguis", "casa heredada", "subasta"],
        "acciones": ["compré", "heredé", "encontré", "guardé"],
        "lugares_t": ["la tienda de antigüedades", "el tianguis", "la casa heredada", "la subasta"],
        "criaturas": ["antique shop", "old doll", "old mirror dark"],
        "emoji": "🗿", "hashtags": ["#ObjetoMaldito", "#Coleccionista"],
        "busquedas": 450000, "competencia": "baja", "ctr_potencial": 9.6, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.5,
    },
    {
        "tema": "espejo_maldito", "keywords": ["espejo", "reflejo", "aparición"],
        "contextos": ["casa antigua", "baño", "recámara", "hotel"],
        "acciones": ["compré", "encontré", "limpié", "rompí"],
        "lugares_t": ["el espejo", "el baño", "la recámara", "el hotel"],
        "criaturas": ["old mirror dark room", "cracked mirror dark", "bathroom mirror fog dark"],
        "emoji": "🪞", "hashtags": ["#EspejoMaldito", "#Fantasmas"],
        "busquedas": 410000, "competencia": "media", "ctr_potencial": 9.5, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-50", "engagement_rate": 15.0,
    },
    {
        "tema": "santero", "keywords": ["santero", "trabajo", "espiritual"],
        "contextos": ["casa del santero", "mercado esotérico", "cementerio", "altar"],
        "acciones": ["consulté", "pedí", "pagué", "recibí"],
        "lugares_t": ["el altar", "el mercado esotérico", "el cementerio", "la casa del santero"],
        "criaturas": ["dark altar candles bones", "esoteric shop night", "skull candle dark"],
        "emoji": "💀", "hashtags": ["#Santería", "#TrabajoEspiritual"],
        "busquedas": 340000, "competencia": "baja", "ctr_potencial": 9.2, "retencion_objetivo": 78,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 14.5,
    },
    {
        "tema": "curandero", "keywords": ["curandero", "limpia", "energía"],
        "contextos": ["casa del curandero", "mercado", "pueblo", "temazcal"],
        "acciones": ["consulté", "recibí", "pedí", "entré"],
        "lugares_t": ["la limpia", "el temazcal", "la casa del curandero", "el mercado"],
        "criaturas": ["herbs hanging dark", "smoke ritual dark", "candles eggs limpia"],
        "emoji": "🌿", "hashtags": ["#Curanderos", "#Limpia"],
        "busquedas": 320000, "competencia": "baja", "ctr_potencial": 9.0, "retencion_objetivo": 78,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-60", "engagement_rate": 14.0,
    },
    # === EXTRATERRESTRES (2) ===
    {
        "tema": "abduccion", "keywords": ["abducción", "recuerdo", "marca"],
        "contextos": ["casa de campo", "carretera", "rancho", "montaña"],
        "acciones": ["desperté", "vi", "recordé", "encontré"],
        "lugares_t": ["la casa de campo", "la carretera", "el rancho", "la montaña"],
        "criaturas": ["bright light sky night", "car headlights ufo", "strange marks skin"],
        "emoji": "🛸", "hashtags": ["#Abducción", "#Extraterrestres"],
        "busquedas": 420000, "competencia": "media", "ctr_potencial": 9.3, "retencion_objetivo": 80,
        "duracion_optima": 50, "tendencia": "creciente", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 15.5,
    },
    {
        "tema": "encuentro_cercano", "keywords": ["encuentro", "ser", "objeto"],
        "contextos": ["camino rural", "campo", "sierra", "rancho"],
        "acciones": ["vi", "toqué", "hablé", "escapé"],
        "lugares_t": ["el campo", "el camino rural", "la sierra", "el rancho"],
        "criaturas": ["ufo landed field night", "strange silhouette fog", "alien figure dark"],
        "emoji": "👽", "hashtags": ["#EncuentroCercano", "#Extraterrestres"],
        "busquedas": 390000, "competencia": "media", "ctr_potencial": 9.0, "retencion_objetivo": 78,
        "duracion_optima": 50, "tendencia": "estable", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-55", "engagement_rate": 14.5,
    },
    # === LEYENDA (1) ===
    {
        "tema": "leyenda_mexicana", "keywords": ["leyenda", "pueblo", "mexicana"],
        "contextos": ["pueblo antiguo", "río de noche", "panteón del pueblo", "rancho abandonado"],
        "acciones": ["escuché", "vi", "descubrí", "presencié"],
        "lugares_t": ["el pueblo", "el río", "el panteón", "el rancho"],
        "criaturas": ["old village night", "colonial church night", "river fog night"],
        "emoji": "🌙", "hashtags": ["#LeyendasMexicanas", "#TerrorMexicano"],
        "busquedas": 680000, "competencia": "alta", "ctr_potencial": 10.0, "retencion_objetivo": 84,
        "duracion_optima": 55, "tendencia": "explosiva", "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "16-60", "engagement_rate": 17.5,
    },
]

# ================================================================
# FÓRMULAS DE TÍTULO (v7.2)
# NARRATIVAS usan {pasado} — verbo simple en pasado 1ª persona.
# NEUTRAS usan solo {lugar}, {Lugar}, {estado}.
# Se proveen todas las claves en .format(); las no usadas se ignoran.
# ================================================================
FORMULAS_NARRATIVAS = [
    "Lo que {pasado} en {lugar} no me dejó dormir",
    "La noche que {pasado} en {lugar}",
    "Después de lo que {pasado} en {lugar}, nada fue igual",
    "Nadie sabe lo que {pasado} en {lugar}",
    "Desde que {pasado} en {lugar} no soy el mismo",
]

# Verbos que NO funcionan en fórmulas narrativas — se usan solo en neutras
_VERBOS_NO_NARRATIVOS = {"encontré", "compré", "heredé", "guardé", "usé", "quemé",
                          "escondí", "firmé", "acepté", "rompí", "pagué", "recibí"}

FORMULAS_NEUTRAS = [
    "Cuidado con {lugar}",
    "Nunca más solo en {lugar}",
    "{Lugar} guarda un secreto",
    "Algo vive en {lugar}",
    "Encontré algo en {lugar}",
    "Lo que hay debajo de {lugar}",
    "¿Qué hay en {lugar} a esta hora?",
    "No vuelvas a {lugar}",
    "El velador me advirtió sobre {lugar}",
    "'No me esperen': lo que dijo antes de ir a {lugar}",
    "El {lugar} de {estado} donde pasan cosas",
    "Así empezó todo en {lugar}",
    "No te quedes en {lugar}",
    "Me advirtieron sobre {lugar}",
]

PSICOLOGIA_COLOR = {
    "miedo":    {"primario": "#FF0000", "secundario": "#000000", "acento": "#FFD700", "emoji": "😱"},
    "misterio": {"primario": "#4B0082", "secundario": "#1a1a1a", "acento": "#00FFFF", "emoji": "🔮"},
    "urgencia": {"primario": "#FF4500", "secundario": "#000000", "acento": "#FFFF00", "emoji": "⚠️"},
    "confianza":{"primario": "#000080", "secundario": "#FFFFFF", "acento": "#FF0000", "emoji": "👁️"},
}

# ================================================================
# VOCES / ESTADOS
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural",   "velocidad": "+12%", "tono": "-2Hz", "estilo": "narrativo"},
    {"voz": "es-ES-AlvaroNeural",  "velocidad": "+10%", "tono": "-3Hz", "estilo": "dramatico"},
    {"voz": "es-MX-ManuelNeural",  "velocidad": "+12%", "tono": "-1Hz", "estilo": "conversacional"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+10%", "tono": "-2Hz", "estilo": "suspenso"},
    {"voz": "es-AR-ElenaNeural",   "velocidad": "+10%", "tono": "+1Hz", "estilo": "femenino_misterio"},
]
CONFIG_VOZ_ACTUAL = random.choice(VOCES_DISPONIBLES)

ESTADOS_MEXICO = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche", "Chiapas",
    "Chihuahua", "Ciudad de México", "Coahuila", "Colima", "Durango", "Estado de México",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "Michoacán", "Morelos", "Nayarit",
    "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
    "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas",
]
ESTADO_HISTORIA_SHORTS = random.choice(ESTADOS_MEXICO)

FONDOS_DISPONIBLES = [
    "Ash and Marrow.mp3", "Black Maw.mp3", "Cold Hollow.mp3",
    "Hollow Marrow.mp3", "Sunken Dread.mp3", "Sunless Vault.mp3", "The Deep Rot.mp3",
]

OUTLIERS_TERROR = [
    "Intenté sobrevivir 7 días en el hotel más embrujado de México",
    "¿Qué vi en el espejo del manicomio abandonado?",
    "De creyente a escéptico en una noche en el panteón",
    "El ritual que hice y nunca debí hacer",
    "Sobreviví a la carretera fantasma de Chihuahua sin gasolina",
]

ANIO_SUCESO = None
EPOCA_MOD = "present day contemporary era (2020s), modern vehicles, modern architecture, modern clothing, LED lighting, smartphones era"

# ================================================================
# UTILIDADES - ÉPOCA
# ================================================================
def construir_modificadores_epoca(anio):
    if anio is None or anio >= 2015:
        return "present day contemporary era (2020s), modern vehicles, modern architecture, modern clothing, LED lighting, smartphones era"
    elif anio >= 2000:
        return f"early 2000s era (year {anio}): 2000s cars, CRT televisions, old flip cellphones, 2000s fashion and architecture, no smartphones"
    elif anio >= 1990:
        return f"1990s era (year {anio}): 90s cars, cassette players, CRT TVs, analog phones, 90s fashion, older architecture, no smartphones"
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
# VIRALIDAD
# ================================================================
def calcular_puntuacion_viralidad(tema):
    factores = {
        "busquedas":  tema["busquedas"] / 1_000_000 * 30,
        "ctr":        tema["ctr_potencial"] * 2.5,
        "retencion":  tema["retencion_objetivo"] * 2.0,
        "engagement": tema["engagement_rate"] * 1.5,
        "tendencia":  10 if tema["tendencia"] == "explosiva" else 5,
    }
    score = sum(factores.values())
    return {
        "score": score, "factores": factores,
        "categoria": "Alta" if score > 75 else "Media" if score > 50 else "Baja",
    }

# ================================================================
# TÍTULOS
# ================================================================
def generar_titulo_variado(tema, estado_mx):
    """Genera título coherente con verbos simples en pasado."""
    pasado = random.choice(tema["acciones"])
    lugar  = random.choice(tema["lugares_t"])

    # Si el verbo no encaja en narrativas, forzar fórmula neutra
    usar_narrativa = random.random() < 0.45 and pasado not in _VERBOS_NO_NARRATIVOS
    formula = random.choice(FORMULAS_NARRATIVAS) if usar_narrativa else random.choice(FORMULAS_NEUTRAS)

    try:
        titulo = formula.format(
            pasado=pasado,
            lugar=lugar,
            Lugar=lugar[0].upper() + lugar[1:],
            estado=estado_mx,
        )
    except KeyError:
        titulo = f"Cuidado con {lugar}"

    # Palabra de impacto opcional (35 % de las veces)
    if random.random() < 0.35:
        impacto = random.choice(["NUNCA", "NADIE", "PELIGRO", "SOLO"])
        if not titulo.upper().startswith(impacto):
            titulo = f"{impacto}: {titulo}"

    # Emoji + hashtags (deduplicados)
    hashtag_base   = f"#{tema['tema'].replace('_','').capitalize()}"
    hashtags_extra = [h for h in tema["hashtags"] if h != hashtag_base][:2]
    hashtags = list(dict.fromkeys([hashtag_base] + hashtags_extra + ["#Terror", "#Misterio"]))
    titulo_final = f"{titulo} {tema['emoji']} {' '.join(hashtags)}"

    if len(titulo_final) > 100:
        titulo_final = titulo_final[:97] + "..."
    return titulo_final

def calcular_score_titulo(titulo):
    score = 50
    if 40 <= len(titulo) <= 100: score += 10
    if any(p in titulo.upper() for p in ["NUNCA","NADIE","PELIGRO","PROHIBIDO","SOLO"]): score += 10
    if "?" in titulo: score += 5
    if any(ord(c) > 127743 for c in titulo): score += 3
    if "#" in titulo: score += 3
    # Penalizar horas forzadas
    if re.search(r"\b[0-2]?[0-9]:[0-5][0-9]\b", titulo): score -= 12
    # Penalizar prefijos rígidos
    if "TESTIMONIO" in titulo.upper() or "ADVERTENCIA" in titulo.upper(): score -= 12
    return min(max(score, 0), 100)

# ================================================================
# ANALYTICS
# ================================================================
def cargar_analytics_elite():
    try:
        with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"videos_publicados": [], "mejores_horarios": {}, "mejores_temas": {},
                "ctr_promedio": 0, "retencion_promedio": 0}

def guardar_analytics_elite(analytics):
    tmp = ANALYTICS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(analytics, f, indent=2, ensure_ascii=False)
    os.replace(tmp, ANALYTICS_FILE)

def predecir_rendimiento(tema, titulo, hora_publicacion):
    score_tema   = next((t["ctr_potencial"] for t in TEMAS_VIRALES_2024 if t["tema"] == tema), 7.0)
    score_titulo = calcular_score_titulo(titulo)
    score_hora   = 1.0 if hora_publicacion[:2] in ["14","18","21"] else 0.8
    vistas   = int(score_tema * score_titulo * score_hora * 1000)
    ctr      = round(score_tema * (score_titulo / 100), 2)
    retencion = round(70 + (score_titulo / 10), 1)
    return {
        "vistas_predichas": vistas, "ctr_predicho": ctr, "retencion_predicha": retencion,
        "confianza": "Alta" if vistas > 50000 else "Media" if vistas > 10000 else "Baja",
    }

# ================================================================
# PEXELS
# ================================================================
def validar_pexels_api_key():
    if not PEXELS_API_KEY:
        print("⚠️ PEXELS_API_KEY no configurada.")
        return False
    try:
        r = requests.get("https://api.pexels.com/v1/search?query=test&per_page=1",
                         headers={"Authorization": PEXELS_API_KEY}, timeout=10)
        if r.status_code == 200:
            print("✅ API Key de Pexels válida.")
            return True
        print(f"⚠️ API Key de Pexels inválida (código {r.status_code}).")
        return False
    except Exception as e:
        print(f"⚠️ Error probando Pexels: {e}")
        return False

PEXELS_VALIDA = validar_pexels_api_key()
ULTIMA_URL_PEXELS = None

# ================================================================
# ESTADO / PERSISTENCIA
# ================================================================
def cargar_estado():
    try:
        with open(ESTADO_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "publicaciones_hoy" not in data:
                data["publicaciones_hoy"] = 0
            return data
    except Exception:
        return {"ultimo_fondo": None, "publicaciones_hoy": 0, "fecha": None, "ultima_publicacion": None}

def guardar_estado(estado):
    tmp = ESTADO_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2)
    os.replace(tmp, ESTADO_FILE)

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
        tmp = TITULOS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, TITULOS_FILE)

def cargar_temas_usados():
    try:
        with open(TEMAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"temas": []}

def guardar_tema_usado(tema):
    data = cargar_temas_usados()
    data["temas"] = [t for t in data["temas"] if isinstance(t, str) and len(t) < 80]
    if isinstance(tema, str) and len(tema) < 80 and tema not in data["temas"]:
        data["temas"].append(tema)
    data["temas"] = data["temas"][-MAX_TEMAS_HISTORIAL:]
    tmp = TEMAS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, TEMAS_FILE)

def obtener_temas_recientes():
    return cargar_temas_usados()["temas"]

# ================================================================
# DECISIÓN DE PUBLICAR
# ================================================================
def deberia_publicar_ahora(estado):
    tz   = pytz.timezone("America/Mexico_City")
    hoy  = datetime.now(tz).date().isoformat()

    # Reiniciar contador si es un día nuevo
    if estado.get("fecha") != hoy:
        estado["fecha"] = hoy
        estado["publicaciones_hoy"] = 0
        guardar_estado(estado)
        print(f"📅 Nuevo día ({hoy}). Contador reiniciado.")

    publicadas = estado.get("publicaciones_hoy", 0)
    ultima     = estado.get("ultima_publicacion", "—")
    print(f"📊 Estado actual → publicadas hoy: {publicadas}/{MAX_SHORTS_DIA} | última: {ultima}")

    if publicadas >= MAX_SHORTS_DIA:
        print(f"🛑 Límite diario alcanzado ({MAX_SHORTS_DIA}/día). Saliendo.")
        return False

    print(f"✅ Publicando short #{publicadas + 1}/{MAX_SHORTS_DIA}.")
    return True

# ================================================================
# LIMPIADORES DE TEXTO
# ================================================================
def limpiar_caracteres_para_tts(texto):
    texto = re.sub(r'[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ0-9\s.,;:!?¿¡\'\"]+', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()

def limpiar_texto_para_audio(texto):
    texto = re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
        r'\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF'
        r'\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF'
        r'\U00002700-\U000027BF\U000024C2-\U0001F251]+', '', texto)
    texto = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', texto)
    return re.sub(r'\s+', ' ', texto.replace('"', "'")).strip()

def limpiar_respuesta_json(respuesta):
    respuesta = re.sub(r"```json\s*", "", respuesta)
    respuesta = re.sub(r"```\s*", "", respuesta)
    inicio = respuesta.find("{")
    fin    = respuesta.rfind("}")
    if inicio != -1 and fin != -1:
        json_str = respuesta[inicio: fin + 1]
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*\]", "]", json_str)
        return json_str
    return respuesta

# ================================================================
# PLACEHOLDER LOCAL
# ================================================================
def generar_placeholder_local(texto="TERROR", size=(1080, 1920)):
    try:
        img  = Image.new("RGB", size, (20, 20, 20))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 140)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), texto, font=font)
        x = (size[0] - (bbox[2] - bbox[0])) // 2
        y = (size[1] - (bbox[3] - bbox[1])) // 2
        draw.text((x, y), texto, fill="red", font=font)
        path = f"placeholder_{random.randint(1000, 9999)}.jpg"
        img.save(path)
        return path
    except Exception:
        return None

# ================================================================
# MINIATURA ÉLITE (estilo MrBeast)
# ================================================================
def crear_miniatura_elite_mrbeast(img_path, texto, tema_viral, output_path):
    if any(p in tema_viral for p in ["miedo", "terror", "peligro"]):
        cs = PSICOLOGIA_COLOR["miedo"]
    elif any(p in tema_viral for p in ["misterio", "secreto", "oculto"]):
        cs = PSICOLOGIA_COLOR["misterio"]
    elif any(p in tema_viral for p in ["urgencia", "alerta"]):
        cs = PSICOLOGIA_COLOR["urgencia"]
    else:
        cs = PSICOLOGIA_COLOR["confianza"]

    try:
        with Image.open(img_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img  = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
            img  = ImageEnhance.Contrast(img).enhance(1.8)
            img  = ImageEnhance.Color(img).enhance(1.5)
            img  = ImageEnhance.Sharpness(img).enhance(2.5)
            img  = ImageEnhance.Brightness(img).enhance(1.15)
            draw = ImageDraw.Draw(img)
            w, h = img.size

            palabras = texto.upper().strip().split()[:3]
            lineas = [" ".join(palabras)] if len(palabras) <= 2 else [
                " ".join(palabras[:len(palabras)//2]),
                " ".join(palabras[len(palabras)//2:]),
            ]

            font = None
            for path in [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraBold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            ]:
                try:
                    font = ImageFont.truetype(path, 130); break
                except Exception:
                    continue
            if font is None:
                font = ImageFont.load_default()

            alto_total = sum(
                draw.textbbox((0,0), l, font=font)[3] - draw.textbbox((0,0), l, font=font)[1] + 25
                for l in lineas
            )
            y0 = (h - alto_total) // 2 + 100
            pad = 50
            max_w = max(draw.textbbox((0,0), l, font=font)[2] for l in lineas)

            overlay = Image.new("RGBA", img.size, (0,0,0,0))
            od = ImageDraw.Draw(overlay)
            od.rectangle(
                [(w-max_w)//2-pad, y0-pad, (w+max_w)//2+pad, y0+alto_total+pad],
                fill=(0,0,0,220)
            )
            overlay = overlay.filter(ImageFilter.GaussianBlur(radius=10))
            img  = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

            y = y0
            for linea in lineas:
                bb = draw.textbbox((0,0), linea, font=font)
                lw, lh = bb[2]-bb[0], bb[3]-bb[1]
                x = (w - lw) // 2
                for o in range(12, 0, -2):
                    for dx in [-o, 0, o]:
                        for dy in [-o, 0, o]:
                            if dx or dy:
                                draw.text((x+dx, y+dy), linea, font=font, fill=(0,0,0))
                draw.text((x, y), linea, font=font, fill=cs["acento"])
                y += lh + 25

            draw.line([(w-150, h-300), (w-300, h-450)], fill=(255,0,0), width=35)
            draw.polygon([(w-300, h-450),(w-260, h-500),(w-340, h-500)], fill=(255,0,0))

            try:
                ef = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 120)
                draw.text((w-150, 80), cs["emoji"], font=ef)
            except Exception:
                pass

            img.save(output_path, "JPEG", quality=95, optimize=True)
            print(f"✅ Miniatura élite creada: {output_path}")
            return True
    except Exception as e:
        print(f"❌ Error miniatura élite: {e}")
        traceback.print_exc()
        return False

# ================================================================
# MINIATURA VIRAL (alternativa)
# ================================================================
def crear_miniatura_viral(img_path, texto, output_path):
    colores = [
        (255,255,0), (255,50,50), (255,140,0), (0,255,255), (255,255,255),
    ]
    color_texto = random.choice(colores)
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    try:
        with Image.open(img_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img  = ImageOps.fit(img, (1080, 1920), Image.LANCZOS)
            img  = ImageEnhance.Contrast(img).enhance(1.5)
            img  = ImageEnhance.Sharpness(img).enhance(2.0)
            draw = ImageDraw.Draw(img)
            w, h = img.size

            palabras = texto.upper().strip().split()[:3]
            if len(palabras) > 2:
                m = len(palabras) // 2
                lineas = [" ".join(palabras[:m]), " ".join(palabras[m:])]
            else:
                lineas = [" ".join(palabras)]

            font = None
            for sz in range(130, 80, -5):
                try:
                    font = ImageFont.truetype(font_paths[0], sz)
                    max_w, tot_h = 0, 0
                    for l in lineas:
                        bb = draw.textbbox((0,0), l, font=font)
                        max_w = max(max_w, bb[2]-bb[0])
                        tot_h += bb[3]-bb[1] + 25
                    if max_w < w*0.85 and tot_h < h*0.35:
                        break
                except Exception:
                    continue
            if font is None:
                font = ImageFont.load_default()

            alto_total = sum(
                draw.textbbox((0,0), l, font=font)[3] - draw.textbbox((0,0), l, font=font)[1] + 25
                for l in lineas
            )
            y0  = (h - alto_total) // 2 + 80
            pad = 50
            max_w2 = max(draw.textbbox((0,0), l, font=font)[2] for l in lineas)
            draw.rectangle(
                [(w-max_w2)//2-pad, y0-pad, (w+max_w2)//2+pad, y0+alto_total+pad],
                fill=(0,0,0,240)
            )

            y = y0
            for linea in lineas:
                bb = draw.textbbox((0,0), linea, font=font)
                lw, lh = bb[2]-bb[0], bb[3]-bb[1]
                x = (w - lw) // 2
                for dx in [-8,-6,-4,-2,0,2,4,6,8]:
                    for dy in [-8,-6,-4,-2,0,2,4,6,8]:
                        draw.text((x+dx, y+dy), linea, font=font, fill=(0,0,0))
                draw.text((x, y), linea, font=font, fill=color_texto)
                y += lh + 25

            img.convert("RGB").save(output_path, "JPEG", quality=95, optimize=True)
            print(f"✅ Miniatura viral creada: {output_path}")
            return True
    except Exception as e:
        print(f"❌ Error miniatura viral: {e}")
        traceback.print_exc()
        return False

# ================================================================
# EXPANDIR / TRUNCAR TEXTO
# ================================================================
def expandir_texto_corto(texto_corto, ubicacion, personaje):
    prompt = (
        f"Expande el siguiente relato a 110-130 palabras con detalles sensoriales de {ubicacion}.\n"
        f"IMPORTANTE: Asegúrate de que el relato tenga un OBJETIVO CLARO, una RESTRICCIÓN y que el protagonista ACTÚE.\n"
        f"Mantén trama y tono. Sin CTA. Debe sonar como un relato personal real.\n"
        f"RELATO: {texto_corto}\nDevuelve SOLO el relato."
    )
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model":"deepseek-chat","messages":[{"role":"user","content":prompt}],"temperature":0.8,"max_tokens":700}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        t = r.json()["choices"][0]["message"]["content"].strip()
        return t if len(t.split()) > 110 else texto_corto
    except Exception:
        return texto_corto

def truncar_texto_largo(texto, max_palabras=130):
    palabras = texto.split()
    if len(palabras) <= max_palabras:
        return texto
    for i in range(max_palabras, max_palabras - 30, -1):
        if i < len(palabras) and palabras[i-1].endswith(('.','!','?')):
            return ' '.join(palabras[:i])
    return ' '.join(palabras[:max_palabras])

# ================================================================
# ELEGIR TEMA Y GENERAR HISTORIA
# ================================================================
def elegir_tema_variado():
    recientes = set(obtener_temas_recientes()[-8:])
    pool = [t for t in TEMAS_VIRALES_2024 if t["tema"] not in recientes] or TEMAS_VIRALES_2024[:]
    tema = random.choice(pool)
    print(f"🎯 Tema: {tema['tema']} ({len(pool)} disponibles)")
    return tema

def generar_historia_completa():
    tema_viral = elegir_tema_variado()
    contexto   = random.choice(tema_viral["contextos"])
    keywords   = tema_viral["keywords"]

    titulos_pub = cargar_titulos_publicados()["titulos"][-10:]
    tit_ref = "\n".join([f"- {t}" for t in titulos_pub]) if titulos_pub else "Ninguno aún."

    temas_recientes = obtener_temas_recientes()
    bloqueo = ""
    if temas_recientes:
        bloqueo = "\n🚫 TEMAS YA PUBLICADOS RECIENTEMENTE (no repetir):\n" + \
                  "\n".join(f"- {t}" for t in temas_recientes[-5:])

    outliers = "\n".join(f"  • {t}" for t in random.sample(OUTLIERS_TERROR, 3))
    score_viral = calcular_puntuacion_viralidad(tema_viral)

    prompt = f"""Eres un curador de relatos de terror que la comunidad comparte en foros de internet.
Tu especialidad es adaptar estas historias para hacerlas extremadamente inmersivas, atrapantes y escalofriantes.

🔥 TEMA: {tema_viral['tema'].upper()}
📍 CONTEXTO: {contexto}
🔑 KEYWORDS: {', '.join(keywords)}
📊 SCORE VIRALIDAD: {score_viral['score']:.1f}/100 ({score_viral['categoria']})

📚 OUTLIERS DE REFERENCIA:
{outliers}

🚨 REGLAS DE ORO:
1. Relato personal real. NUNCA menciones IA, ficción o invención.
2. 110-130 palabras EXACTAS (45-55 segundos de audio).
3. Gancho en los primeros 3 segundos.
4. Detalles sensoriales: sonidos, olores, frío, texturas.
5. ⚠️ SI mencionas una hora, VARÍALA. NO uses "3:33 AM", "3:00 AM" ni "4:44 AM". En la MAYORÍA de relatos NO pongas hora.
6. NO empieces con "TESTIMONIO:" ni "ADVERTENCIA:".

🚫 TÍTULOS YA PUBLICADOS:
{tit_ref}
{bloqueo}

Devuelve ESTRICTAMENTE este JSON:
{{
    "texto_completo": "El relato de 110-130 palabras.",
    "palabras_portada": "2 palabras EN MAYÚSCULAS de alto impacto",
    "tags": ["tag1","tag2","tag3","tag4","tag5"]
}}"""

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
    }

    for intento in range(6):
        try:
            print(f"🔄 Intento {intento+1}/6 generando historia...")
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            json_str = limpiar_respuesta_json(raw)
            try:
                data = json.loads(json_str, strict=False)
            except json.JSONDecodeError:
                if json5 is None:
                    raise
                data = json5.loads(json_str)

            if "texto_completo" not in data or len(data["texto_completo"].split()) < 90:
                raise ValueError("Texto demasiado corto")

            palabras = data["texto_completo"].split()
            if len(palabras) > 130:
                data["texto_completo"] = truncar_texto_largo(data["texto_completo"], 130)

            data["tema"]    = tema_viral["tema"]
            data["estado"]  = ESTADO_HISTORIA_SHORTS
            data["contexto"] = contexto
            data["titulo"]  = generar_titulo_variado(tema_viral, ESTADO_HISTORIA_SHORTS)

            data.setdefault("gancho_descripcion", f"Relato de terror: {data['titulo'][:80]}")
            data.setdefault("contexto_descripcion", f"Un relato de fenómenos extraños en {ESTADO_HISTORIA_SHORTS}, México.")
            data.setdefault("fuente_relato", "Compartido por un oyente de la comunidad.")
            hashtags = ["#Shorts"] + tema_viral["hashtags"][:2] + [
                "#Terror", "#Misterio", f"#{ESTADO_HISTORIA_SHORTS.replace(' ','')}"]
            data.setdefault("hashtags_descripcion", " ".join(hashtags))

            return data

        except Exception as e:
            print(f"❌ Intento {intento+1}/6 falló: {e}")
            if intento < 5:
                time.sleep(10 + intento * 5)

    print("❌ TODOS LOS INTENTOS FALLARON.")
    sys.exit(1)

# ================================================================
# QUERIES CINEMATOGRÁFICOS
# ================================================================
def generar_query_cinematografico(segmento_texto, etapa, ubicacion_escena, tema_viral,
                                   segmento_index=0, total_segmentos=1):
    progreso = segmento_index / max(total_segmentos - 1, 1)

    if etapa == "inicio_casa":
        prompts = [
            f"wide shot of dark mexican {ubicacion_escena}, establishing shot, cinematic horror, atmospheric lighting, film grain",
            f"medium shot of {ubicacion_escena} interior, dim lighting, cinematic composition, 35mm film look",
            f"overhead shot of empty {ubicacion_escena}, top-down view, eerie atmosphere",
        ] if progreso < 0.3 else [
            f"POV shot walking through {ubicacion_escena}, handheld camera, cinematic horror, shallow depth of field",
        ]
    elif etapa == "desplazamiento":
        prompts = [
            f"wide shot of dark mexican road at night, {ubicacion_escena}, cinematic thriller",
            f"exterior shot of vehicle on dark road, {ubicacion_escena}, headlights cutting through fog",
            f"street view of empty mexican street at night, {ubicacion_escena}, horror",
        ]
    elif etapa == "lugar_destino":
        prompts = [
            f"wide establishing shot of {ubicacion_escena} at night, ultra wide angle, horror",
            f"exterior shot of {ubicacion_escena}, building facade, night photography",
            f"interior shot of {ubicacion_escena}, exploring inside, flashlight beam",
            f"POV shot inside {ubicacion_escena}, first person perspective, tension",
        ]
    elif etapa == "climax_evento":
        prompts = [
            f"medium shot of person reacting in {ubicacion_escena}, shocked expression, horror film still",
            f"extreme close-up of terrified eyes in {ubicacion_escena}, intense fear, dramatic lighting",
            f"wide shot of dramatic moment in {ubicacion_escena}, action scene, dynamic angle",
        ] if progreso >= 0.7 else [
            f"detail shot of hands trembling in {ubicacion_escena}, tension, cinematic close-up",
        ]
    else:  # resolucion
        prompts = [
            f"wide shot of person leaving {ubicacion_escena} at dawn, silhouette, atmospheric fog",
            f"establishing shot of {ubicacion_escena} in morning light, aftermath, quiet atmosphere",
        ]

    base = random.choice(prompts)
    visuales = next((t["criaturas"] for t in TEMAS_VIRALES_2024 if t["tema"] == tema_viral), [])
    if visuales:
        base += f", {random.choice(visuales)}"
    base += f", {EPOCA_MOD}"
    return re.sub(r'\s+', ' ', base).strip()[:200]

# ================================================================
# DIVIDIR TEXTO EN SEGMENTOS
# ================================================================
def dividir_en_segmentos(texto, max_palabras_por_segmento=45):
    oraciones = re.split(r'(?<=[.!?¿¡])\s+', texto)
    oraciones = [o.strip() for o in oraciones if o.strip()]
    segmentos, actual, cuenta = [], [], 0
    for oracion in oraciones:
        n = len(oracion.split())
        if cuenta + n > max_palabras_por_segmento and actual:
            segmentos.append(" ".join(actual))
            actual, cuenta = [oracion], n
        else:
            actual.append(oracion)
            cuenta += n
    if actual:
        segmentos.append(" ".join(actual))
    return segmentos

def determinar_etapa_narrativa(segmento_index, total_segmentos, segmento_texto):
    progreso = segmento_index / max(total_segmentos - 1, 1)
    texto_lower = segmento_texto.lower()
    palabras_desp   = ["caminé","manejé","conduje","llegué","fui","viajé","crucé"]
    palabras_climax = ["corrí","grité","escapé","huí","cayó","apareció","vi","escuché algo"]
    if progreso <= 0.2:
        return "inicio_casa"
    elif progreso <= 0.4:
        return "desplazamiento" if any(p in texto_lower for p in palabras_desp) else "inicio_casa"
    elif progreso <= 0.7:
        return "lugar_destino"
    elif progreso <= 0.9:
        return "climax_evento" if any(p in texto_lower for p in palabras_climax) else "lugar_destino"
    else:
        return "resolucion"

# ================================================================
# BÚSQUEDA DE IMÁGENES PEXELS
# ================================================================
def buscar_miniatura_pexels(query, intentos=5):
    variantes = ["empty space","copy space","dark background","dramatic","cinematic","horror"]
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    for intento in range(intentos):
        try:
            q = f"{query} {random.choice(variantes)}"
            params = {"query": q, "orientation": "portrait",
                      "per_page": 10, "page": random.randint(1,5), "size": "large"}
            print(f"🖼️ Miniatura vertical: '{q}'...")
            r = requests.get(url, headers=headers, params=params, timeout=25)
            if r.status_code == 200:
                fotos = r.json().get("photos", [])
                for foto in fotos[:5]:
                    img_url = foto["src"]["large2x"] or foto["src"]["large"]
                    try:
                        ri = requests.get(img_url, timeout=10)
                        if ri.status_code == 200:
                            print(f"✅ Miniatura encontrada.")
                            return img_url
                    except Exception:
                        continue
        except Exception as e:
            print(f"⚠️ Error: {e}")
        if intento < intentos - 1:
            time.sleep(3)
    # Fallback simple
    try:
        r = requests.get(url, headers=headers,
                         params={"query": query, "orientation": "portrait", "per_page": 5}, timeout=25)
        if r.status_code == 200:
            fotos = r.json().get("photos", [])
            if fotos:
                return fotos[0]["src"]["large2x"]
    except Exception:
        pass
    return None

def buscar_imagen_pexels_shorts(query, intentos=3):
    global ULTIMA_URL_PEXELS
    if not PEXELS_VALIDA:
        return None
    variantes = ["cinematic","dramatic","atmospheric","moody","film"]
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params  = {"query": f"{query} {random.choice(variantes)}", "orientation": "portrait",
               "per_page": 10, "page": random.randint(1,8)}
    for intento in range(intentos):
        try:
            print(f"🔍 Pexels intento {intento+1}: '{params['query'][:60]}'...")
            r = requests.get(url, headers=headers, params=params, timeout=25)
            if r.status_code == 200:
                fotos = r.json().get("photos", [])
                if fotos:
                    foto = random.choice(fotos[:5])
                    img_url = foto["src"]["large2x"] or foto["src"]["large"]
                    if img_url != ULTIMA_URL_PEXELS:
                        ULTIMA_URL_PEXELS = img_url
                        return img_url
            elif r.status_code == 401:
                print("❌ API key inválida.")
                break
        except Exception as e:
            print(f"⚠️ Pexels error: {e}")
        if intento < intentos - 1:
            time.sleep(5)
    return None

# ================================================================
# DESCARGAR / PROCESAR IMÁGENES
# ================================================================
def descargar_imagen(url, output_path, timeout=30):
    try:
        r = requests.get(url, timeout=timeout, stream=True)
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"✅ Imagen descargada: {output_path}")
            return True
    except Exception as e:
        print(f"❌ Error descargando: {e}")
    return False

def procesar_imagen_para_short(img_path, output_path, size=(1080, 1920)):
    try:
        with Image.open(img_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(1.3)
            img = ImageEnhance.Brightness(img).enhance(0.85)
            img.save(output_path, "JPEG", quality=95)
            print(f"✅ Imagen procesada: {output_path}")
            return True
    except Exception as e:
        print(f"❌ Error procesando imagen: {e}")
    return False

# ================================================================
# MÚSICA DE FONDO
# ================================================================
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
        print("⚠️ No se encontraron archivos de música.")
        return None
    ultimo = estado.get("ultimo_fondo")
    candidatos = [f for f in encontrados if f != ultimo] or list(encontrados.keys())
    seleccionado = random.choice(candidatos)
    estado["ultimo_fondo"] = seleccionado
    print(f"🎵 Música: {seleccionado}")
    return encontrados[seleccionado]

# ================================================================
# GENERACIÓN DE AUDIO
# ================================================================
async def _intentar_voz(texto_limpio, output_path, voz):
    """Intenta generar audio con una voz específica. Devuelve True si el archivo tiene contenido."""
    communicate = edge_tts.Communicate(
        text=texto_limpio,
        voice=voz["voz"],
        rate=voz["velocidad"],
        pitch=voz["tono"],
    )
    await communicate.save(output_path)
    return os.path.exists(output_path) and os.path.getsize(output_path) > 2000

async def generar_audio_edge_tts_con_retry(texto, output_path):
    """Prueba las 5 voces de Edge TTS en orden antes de rendirse."""
    texto_limpio = limpiar_texto_para_audio(texto)
    # La voz actual va primero; el resto en orden aleatorio como fallbacks
    voces_orden = [CONFIG_VOZ_ACTUAL] + [
        v for v in VOCES_DISPONIBLES if v["voz"] != CONFIG_VOZ_ACTUAL["voz"]
    ]
    for voz in voces_orden:
        for intento in range(2):
            try:
                print(f"🎤 Voz: {voz['voz']} — intento {intento+1}/2...")
                if await _intentar_voz(texto_limpio, output_path, voz):
                    print(f"✅ Audio Edge TTS con {voz['voz']}")
                    return True, voz["voz"]
                print(f"⚠️ {voz['voz']}: archivo vacío o muy pequeño.")
            except Exception as e:
                print(f"⚠️ {voz['voz']} intento {intento+1}: {e}")
            await asyncio.sleep(2)
        # Limpiar archivo fallido antes de intentar la siguiente voz
        if os.path.exists(output_path):
            os.remove(output_path)
    return False, None

def generar_audio_gtts_fallback(texto, output_path):
    try:
        from gtts import gTTS
        texto_limpio = limpiar_texto_para_audio(texto)
        gTTS(text=texto_limpio, lang="es", slow=False).save(output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"✅ Audio gTTS fallback: {output_path}")
            return True
    except Exception as e:
        print(f"❌ Error gTTS: {e}")
    return False

def generar_audio_con_fallback(texto, output_path):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        ok, voz_usada = loop.run_until_complete(
            generar_audio_edge_tts_con_retry(texto, output_path)
        )
        if ok:
            return True
        print("⚠️ Todas las voces Edge TTS fallaron. Usando gTTS...")
    except Exception as e:
        print(f"⚠️ Edge TTS error crítico: {e}. Usando gTTS...")
    finally:
        loop.close()
    return generar_audio_gtts_fallback(texto, output_path)

# ================================================================
# MONTAR VIDEO
# ================================================================
def montar_video_short(audio_path, imagenes_paths, musica_path, output_path, palabras_portada, tema_viral):
    try:
        audio_clip    = AudioFileClip(audio_path)
        duracion_total = audio_clip.duration
        print(f"⏱️ Duración audio: {duracion_total:.1f}s")

        dur_img = duracion_total / max(len(imagenes_paths), 1)
        clips_video = []

        for i, img_path in enumerate(imagenes_paths):
            try:
                clip = ImageClip(img_path, duration=dur_img).set_fps(30)

                # Zoom Ken Burns suave
                def make_zoom(dur=dur_img):
                    def zoom(t):
                        return 1.0 + 0.05 * (t / dur)
                    return zoom

                clip = clip.resize(make_zoom())
                clips_video.append(clip)
            except Exception as e:
                print(f"⚠️ Error clip {i+1}: {e}")

        if not clips_video:
            print("❌ Sin clips de video.")
            return False

        video_final = concatenate_videoclips(clips_video, method="compose").set_duration(duracion_total)

        # Música de fondo
        if musica_path and os.path.exists(musica_path):
            try:
                musica     = AudioFileClip(musica_path)
                musica_loop = musica.audio_loop(duration=duracion_total)
                musica_baja = musica_loop.volumex(0.08)
                audio_final = CompositeAudioClip([audio_clip, musica_baja])
            except Exception as e:
                print(f"⚠️ Música falló: {e}")
                audio_final = audio_clip
        else:
            audio_final = audio_clip

        video_final = video_final.set_audio(audio_final)

        print(f"🎬 Renderizando {output_path}...")
        video_final.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp_audio_short.m4a",
            remove_temp=True,
            preset="fast",
            bitrate="4000k",
            audio_bitrate="128k",
            threads=2,
            logger=None,
        )

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"✅ Video listo: {output_path} ({os.path.getsize(output_path)//1024//1024}MB)")
            return True
        return False

    except Exception as e:
        print(f"❌ Error montando video: {e}")
        traceback.print_exc()
        return False

# ================================================================
# SEO — TAGS Y DESCRIPCIÓN
# ================================================================
def generar_tags_seo(tema_obj, estado_mx):
    """
    Tags en 5 niveles estratégicos (vidiq/TubeBuddy style).
    Orden de prioridad respetando el límite de 500 chars de YouTube.

    T1 — 1 palabra, máximo volumen global
    T2 — 2-3 palabras, alto volumen
    T3 — Específicos del tema (keywords + hashtags limpios)
    T4 — Long-tail (4-6 palabras, alta intención de búsqueda)
    T5 — Plataforma
    """
    nombre_tema = tema_obj["tema"].replace("_", " ")

    t1 = [
        "terror", "miedo", "horror", "paranormal",
        "misterio", "suspenso", "escalofriante",
    ]
    t2 = [
        "historias de terror", "relatos de terror", "terror mexicano",
        "terror latino", "relato paranormal", "fenomenos paranormales",
        "terror corto", "historias de miedo", "audio terror",
    ]
    # T3 — keywords y hashtags propios del tema (sin # y en minúsculas)
    t3  = [k.lower() for k in tema_obj["keywords"]]
    t3 += [h.lstrip("#").lower() for h in tema_obj["hashtags"]]

    t4 = [
        f"relatos de terror {nombre_tema}",
        f"historias de {nombre_tema}",
        f"terror en {estado_mx.lower()}",
        f"misterio en {estado_mx.lower()}",
        f"{nombre_tema} paranormal",
        "para no dormir",
        "miedo real",
        "lo inexplicable",
        "experiencia paranormal real",
        "terror que no te deja dormir",
    ]
    t5 = ["shorts", "youtube shorts"]

    todos = list(dict.fromkeys(t1 + t2 + t3 + t4 + t5))
    todos = [t for t in todos if t and len(t) > 2]

    # Respetar límite de 500 chars de YouTube (suma de len(tag)+1 por separador)
    resultado, chars = [], 0
    for tag in todos:
        costo = len(tag) + 1
        if chars + costo > 499:
            break
        resultado.append(tag)
        chars += costo
    return resultado


def generar_descripcion_seo(gancho, contexto_desc, tema_obj, estado_mx,
                             hashtags_desc, fuente_relato):
    """Descripción estructurada y optimizada para SEO."""
    nombre_tema = tema_obj["tema"].replace("_", " ").capitalize()

    hashtags_completos = " ".join([
        "#Terror", "#Misterio", "#Paranormal", "#Shorts",
        "#TerrorMexicano", "#HistoriasDeTerror", "#Miedo",
        "#HorrorShorts", "#Escalofriante", "#Inexplicable",
        f"#{nombre_tema.replace(' ', '')}",
        f"#{estado_mx.replace(' ', '')}",
    ] + [h for h in tema_obj["hashtags"] if h not in ("#Terror", "#Misterio")])

    partes = [
        gancho,
        "",
        contexto_desc,
        "",
        f"📍 {estado_mx}, México  |  🎭 {nombre_tema}",
        "",
        "━" * 34,
        "👻 Suscríbete — nuevos relatos cada semana:",
        f"🎙️ {CANAL_LINK}",
        "📌 Síguenos en Facebook:",
        f"   {FACEBOOK_LINK}",
        "━" * 34,
        "",
        DISCLOSURE_TEXT.strip(),
        f"📖 {fuente_relato}",
        "",
        hashtags_completos,
    ]
    return "\n".join(partes)[:5000]


# ================================================================
# YOUTUBE
# ================================================================
def validar_token_youtube():
    if not YOUTUBE_USER_TOKEN:
        print("⚠️ YOUTUBE_USER_TOKEN no configurado.")
        return None
    try:
        creds = Credentials(
            token=YOUTUBE_USER_TOKEN.get("token"),
            refresh_token=YOUTUBE_USER_TOKEN.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=YOUTUBE_USER_TOKEN.get("client_id"),
            client_secret=YOUTUBE_USER_TOKEN.get("client_secret"),
            scopes=YOUTUBE_USER_TOKEN.get("scopes",
                   ["https://www.googleapis.com/auth/youtube.upload"]),
        )
        service = build("youtube", "v3", credentials=creds)
        print("✅ Cliente YouTube listo.")
        return service
    except Exception as e:
        print(f"❌ Error token YouTube: {e}")
        return None

def subir_a_youtube(video_path, miniatura_path, titulo, tags_seo, descripcion_seo):
    """Sube el short a YouTube con AI disclosure, tags SEO y descripción optimizada."""
    youtube = validar_token_youtube()
    if not youtube:
        return None

    titulo_limpio = titulo[:100]

    body = {
        "snippet": {
            "title":           titulo_limpio,
            "description":     descripcion_seo,
            "tags":            tags_seo,
            "categoryId":      "22",
            "defaultLanguage": "es",
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
            "madeForKids":             False,
            "containsSyntheticMedia":  True,   # ✅ Declara contenido generado con IA
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    try:
        request  = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"📤 Subiendo: {int(status.progress()*100)}%")

        video_id = response["id"]
        print(f"✅ Short publicado: https://youtu.be/{video_id}")

        if miniatura_path and os.path.exists(miniatura_path):
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(miniatura_path)
                ).execute()
                print("✅ Miniatura subida.")
            except HttpError as e:
                print(f"⚠️ Error subiendo miniatura: {e}")

        return video_id

    except HttpError as e:
        print(f"❌ Error HTTP YouTube: {e}")
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"❌ Error YouTube: {e}")
        traceback.print_exc()
        return None



# ================================================================
# LIMPIEZA
# ================================================================
def limpiar_archivos_temporales(archivos):
    for archivo in archivos:
        try:
            if archivo and os.path.exists(archivo):
                os.remove(archivo)
                print(f"🗑️  Eliminado: {archivo}")
        except Exception as e:
            print(f"⚠️ No se pudo eliminar {archivo}: {e}")

# ================================================================
# MAIN
# ================================================================
def main():
    print("=" * 65)
    print("🌙  SOMBRAS DE MEDIANOCHE — BOT DE SHORTS v7.2")
    print("=" * 65)

    estado = cargar_estado()
    if not deberia_publicar_ahora(estado):
        print("💤 No es momento de publicar. Saliendo.")
        sys.exit(0)

    analytics    = cargar_analytics_elite()
    archivos_temp = []

    try:
        # 1. HISTORIA ──────────────────────────────────────────────
        print("\n📝 GENERANDO HISTORIA...")
        datos = generar_historia_completa()

        tema          = datos["tema"]
        titulo        = datos["titulo"]
        texto         = datos["texto_completo"]
        palabras_portada = datos.get("palabras_portada", "TERROR REAL").upper()
        tags          = datos.get("tags", ["#Terror","#Shorts","#Misterio"])
        gancho        = datos.get("gancho_descripcion",   titulo)
        ctx_desc      = datos.get("contexto_descripcion", "")
        hashtags_desc = datos.get("hashtags_descripcion", "#Shorts #Terror #Misterio")
        fuente        = datos.get("fuente_relato",        "Relato de la comunidad.")
        estado_mx     = datos.get("estado", ESTADO_HISTORIA_SHORTS)
        tema_obj      = next((t for t in TEMAS_VIRALES_2024 if t["tema"] == tema), TEMAS_VIRALES_2024[0])

        print(f"\n📌 Título: {titulo}")
        print(f"🎭 Tema: {tema} | 📍 Estado: {estado_mx}")
        print(f"📝 Palabras portada: {palabras_portada}")
        print(f"📊 Score título: {calcular_score_titulo(titulo)}")
        print(f"📖 Texto ({len(texto.split())} palabras): {texto[:180]}...")

        # Detectar época si el relato menciona un año
        anio_match = re.search(r'\b(19[5-9]\d|20[0-2]\d)\b', texto)
        if anio_match:
            actualizar_epoca(int(anio_match.group()))

        # 2. AUDIO ─────────────────────────────────────────────────
        print(f"\n🎤 GENERANDO AUDIO ({CONFIG_VOZ_ACTUAL['voz']})...")
        audio_path = f"audio_{int(time.time())}.mp3"
        archivos_temp.append(audio_path)
        if not generar_audio_con_fallback(limpiar_caracteres_para_tts(texto), audio_path):
            print("❌ No se pudo generar audio.")
            sys.exit(1)

        # 3. MÚSICA ────────────────────────────────────────────────
        musica_path = seleccionar_fondo_disponible(estado)

        # 4. IMÁGENES ──────────────────────────────────────────────
        print("\n🖼️  OBTENIENDO IMÁGENES...")
        segmentos  = dividir_en_segmentos(texto)
        n_imagenes = max(2, min(len(segmentos), 4))
        imagenes   = []

        for i in range(n_imagenes):
            seg_idx    = min(i, len(segmentos)-1)
            segmento   = segmentos[seg_idx]
            etapa      = determinar_etapa_narrativa(i, n_imagenes, segmento)
            ctx_escena = random.choice(tema_obj["contextos"])
            query      = generar_query_cinematografico(segmento, etapa, ctx_escena, tema, i, n_imagenes)

            print(f"🔍 Imagen {i+1}/{n_imagenes} — etapa: {etapa}")
            img_url = buscar_imagen_pexels_shorts(query) or \
                      buscar_imagen_pexels_shorts(f"{random.choice(tema_obj['criaturas'])} dark atmospheric")

            if img_url:
                raw_path  = f"img_raw_{i}_{int(time.time())}.jpg"
                proc_path = f"img_proc_{i}_{int(time.time())}.jpg"
                archivos_temp.extend([raw_path, proc_path])
                if descargar_imagen(img_url, raw_path):
                    if procesar_imagen_para_short(raw_path, proc_path):
                        imagenes.append(proc_path)
                    else:
                        imagenes.append(raw_path)
            else:
                print(f"⚠️ Sin imagen {i+1}. Usando placeholder.")
                ph = generar_placeholder_local(palabras_portada.split()[0])
                if ph:
                    archivos_temp.append(ph)
                    imagenes.append(ph)

        if not imagenes:
            print("❌ Sin imágenes. Saliendo.")
            sys.exit(1)

        print(f"✅ {len(imagenes)} imágenes listas.")

        # 5. MINIATURA ─────────────────────────────────────────────
        print("\n🖼️  CREANDO MINIATURA...")
        miniatura_path = f"miniatura_{int(time.time())}.jpg"
        archivos_temp.append(miniatura_path)
        miniatura_ok = False

        query_mini = buscar_miniatura_pexels(random.choice(tema_obj["criaturas"]))
        if query_mini:
            img_mini = f"img_mini_{int(time.time())}.jpg"
            archivos_temp.append(img_mini)
            if descargar_imagen(query_mini, img_mini):
                miniatura_ok = crear_miniatura_elite_mrbeast(img_mini, palabras_portada, tema, miniatura_path)

        if not miniatura_ok and imagenes:
            miniatura_ok = crear_miniatura_elite_mrbeast(imagenes[0], palabras_portada, tema, miniatura_path)
        if not miniatura_ok:
            miniatura_path = None

        # 6. VIDEO ─────────────────────────────────────────────────
        print("\n🎬 MONTANDO VIDEO...")
        video_path = f"short_{int(time.time())}.mp4"
        archivos_temp.append(video_path)
        if not montar_video_short(audio_path, imagenes, musica_path, video_path, palabras_portada, tema):
            print("❌ Error montando video.")
            sys.exit(1)

        # 7. YOUTUBE ───────────────────────────────────────────────
        print("\n📺 SUBIENDO A YOUTUBE...")
        tags_seo   = generar_tags_seo(tema_obj, estado_mx)
        desc_seo   = generar_descripcion_seo(gancho, ctx_desc, tema_obj, estado_mx,
                                              hashtags_desc, fuente)
        print(f"🏷️  Tags SEO ({len(tags_seo)}): {', '.join(tags_seo[:8])}...")
        video_id = subir_a_youtube(video_path, miniatura_path, titulo, tags_seo, desc_seo)
        if not video_id:
            print("❌ Error subiendo a YouTube.")
            sys.exit(1)
        print(f"\n✅ SHORT PUBLICADO → https://youtu.be/{video_id}")

        # 8. ACTUALIZAR ESTADO ─────────────────────────────────────
        ahora = datetime.now(pytz.timezone("America/Mexico_City"))
        estado["ultima_publicacion"] = ahora.isoformat()
        estado["publicaciones_hoy"]  = estado.get("publicaciones_hoy", 0) + 1
        guardar_estado(estado)
        guardar_titulo_publicado(titulo)
        guardar_tema_usado(tema)

        # 9. ANALYTICS ─────────────────────────────────────────────
        prediccion = predecir_rendimiento(tema, titulo, ahora.strftime("%H:%M"))
        analytics["videos_publicados"].append({
            "video_id":       video_id,
            "titulo":         titulo,
            "tema":           tema,
            "estado":         estado_mx,
            "fecha":          ahora.isoformat(),
            "prediccion":     prediccion,
            "palabras_portada": palabras_portada,
            "score_titulo":   calcular_score_titulo(titulo),
            "voz":            CONFIG_VOZ_ACTUAL["voz"],
            "voz_estilo":     CONFIG_VOZ_ACTUAL["estilo"],
        })
        analytics["videos_publicados"] = analytics["videos_publicados"][-100:]
        guardar_analytics_elite(analytics)

        print("\n📊 PREDICCIÓN DE RENDIMIENTO:")
        print(f"   👁️  Vistas estimadas:  {prediccion['vistas_predichas']:,}")
        print(f"   📈 CTR predicho:       {prediccion['ctr_predicho']}%")
        print(f"   ⏱️  Retención predicha: {prediccion['retencion_predicha']}%")
        print(f"   🎯 Confianza:          {prediccion['confianza']}")

        print("\n" + "=" * 65)
        print(f"🏆 SHORT #{estado['publicaciones_hoy']}/{MAX_SHORTS_DIA} DEL DÍA COMPLETADO")
        print(f"🔗 https://youtu.be/{video_id}")
        print("=" * 65)

    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        traceback.print_exc()
        sys.exit(1)

    finally:
        print("\n🧹 Limpiando archivos temporales...")
        limpiar_archivos_temporales(archivos_temp)

    print("\n✅ Bot de shorts finalizado exitosamente.")


if __name__ == "__main__":
    main()
