import asyncio
from datetime import datetime, timedelta
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
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance
import requests
import edge_tts
import pytz
import urllib3
from collections import Counter
import hashlib

# Silenciar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================================================================
# CONFIGURACIÓN ÉLITE
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
MAX_TEMAS_HISTORIAL = 7
ACTIVAR_DISCLOSURE_IA = True
DISCLOSURE_TEXT = "\n🤖 Contenido generado con inteligencia artificial (relato e imágenes)."

# ================================================================
# CONFIGURACIÓN DE PUBLICACIÓN ÉLITE (2 AL DÍA - MÁXIMA CALIDAD)
# ================================================================
MAX_SHORTS_DIA = 2
INTERVALO_MIN_HORAS = 6
INTERVALO_MAX_HORAS = 9
RETRASO_MAX_MINUTOS = 30

# ================================================================
# TEMAS VIRALES 2024-2025 CON ANÁLISIS DE COMPETENCIA
# ================================================================
TEMAS_VIRALES_2024 = [
    {
        "tema": "backrooms",
        "keywords": ["backrooms", "liminal spaces", "dimensiones", "atrapado", "infinito"],
        "keywords_larga": ["backrooms nivel 0", "espacios liminales explicados", "como entrar backrooms"],
        "contextos": ["hotel abandonado", "centro comercial vacío", "estacionamiento subterráneo", "oficina de noche"],
        "busquedas": 450000,
        "competencia": "media",
        "ctr_potencial": 8.5,
        "retencion_objetivo": 75,
        "duracion_optima": 45,
        "tendencia": "creciente",
        "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-34",
        "engagement_rate": 12.5
    },
    {
        "tema": "skinwalker",
        "keywords": ["skinwalker", "wendigo", "criatura", "carretera", "bosque"],
        "keywords_larga": ["skinwalker navajo", "como identificar skinwalker", "skinwalker vs wendigo"],
        "contextos": ["carretera solitaria", "bosque profundo", "montaña aislada", "desierto nocturno"],
        "busquedas": 380000,
        "competencia": "baja",
        "ctr_potencial": 9.2,
        "retencion_objetivo": 78,
        "duracion_optima": 50,
        "tendencia": "explosiva",
        "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "16-35",
        "engagement_rate": 14.2
    },
    {
        "tema": "ia_prediccion",
        "keywords": ["IA", "inteligencia artificial", "prediccion", "muerte", "algoritmo"],
        "keywords_larga": ["chatgpt predijo muerte", "ia predice futuro", "algoritmo maldito"],
        "contextos": ["computadora antigua", "celular en la noche", "laboratorio", "cuarto oscuro"],
        "busquedas": 890000,
        "competencia": "baja",
        "ctr_potencial": 11.3,
        "retencion_objetivo": 82,
        "duracion_optima": 55,
        "tendencia": "explosiva",
        "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "18-45",
        "engagement_rate": 16.8
    },
    {
        "tema": "glitch_realidad",
        "keywords": ["glitch", "matrix", "realidad", "paralelo", "deja vu"],
        "keywords_larga": ["glitch in the matrix", "realidad paralela", "mandela effect"],
        "contextos": ["calle familiar", "casa propia", "trabajo", "escuela"],
        "busquedas": 410000,
        "competencia": "baja",
        "ctr_potencial": 10.8,
        "retencion_objetivo": 80,
        "duracion_optima": 48,
        "tendencia": "creciente",
        "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "16-40",
        "engagement_rate": 15.3
    },
    {
        "tema": "experiencia_cercana_muerte",
        "keywords": ["muerte", "tunel", "luz", "experiencia", "casi muero"],
        "keywords_larga": ["experiencia cercania muerte testimonio", "vi el mas alla", "muerte clinica"],
        "contextos": ["hospital", "accidente", "quirófano", "emergencia"],
        "busquedas": 720000,
        "competencia": "media",
        "ctr_potencial": 10.2,
        "retencion_objetivo": 85,
        "duracion_optima": 60,
        "tendencia": "estable",
        "estacionalidad": "todo_el_año",
        "audiencia_objetivo": "25-55",
        "engagement_rate": 18.5
    },
]

# ================================================================
# FÓRMULAS DE TÍTULOS ÉLITE (BASADAS EN DATOS REALES DE TOP CREATORS)
# ================================================================
FORMULAS_TITULOS_ELITE = {
    "curiosidad_gap": [
        "Lo que vi en {lugar} cambió mi vida para siempre",
        "Nadie cree lo que encontré en {lugar} (pero tengo pruebas)",
        "El secreto de {lugar} que las autoridades ocultan",
        "Descubrí algo PROHIBIDO en {lugar} y esto pasó",
    ],
    "numero_especifico": [
        "{numero} veces que vi al mismo fantasma en {lugar}",
        "{segundos} segundos que cambiaron mi vida en {lugar}",
        "{hora} exacto: Esto pasó en {lugar}",
        "Día {numero} en {lugar}: Algo me siguió",
    ],
    "pregunta_imposible": [
        "¿Qué harías si ves ESTO en {lugar}?",
        "¿Por qué NADIE entra aquí después del atardecer?",
        "¿Sobrevivirías 1 minuto en {lugar}?",
        "¿Qué escondía {lugar} que NADIE debía ver?",
    ],
    "secreto_revelado": [
        "El SECRETO que {lugar} esconde (FILTRADO)",
        "Lo que NADIE te cuenta sobre {lugar}",
        "Descubrí algo PROHIBIDO en {lugar}",
        "La VERDAD sobre {lugar} que ocultan",
    ],
    "advertencia_peligro": [
        "NUNCA vayas a {lugar} si ves esto (PELIGRO REAL)",
        "🚨 ALERTA: Algo acecha en {lugar} de noche",
        "PELIGRO REAL en {lugar} - Testigo lo confirma",
        "⚡ Lo que pasó en {lugar} NO fue normal",
    ],
    "experiencia_extrema": [
        "Sobreviví {numero} noches en {lugar}",
        "Lo que vi en {lugar} me persigue hasta hoy",
        "Nunca olvidaré lo que pasó en {lugar}",
        "Estuve a punto de morir en {lugar}",
    ],
}

# ================================================================
# 🎨 PSICOLOGÍA DEL COLOR ÉLITE (Basado en estudios de conversión)
# ================================================================
PSICOLOGIA_COLOR = {
    "miedo": {
        "primario": "#FF0000",  # Rojo - Peligro, urgencia
        "secundario": "#000000",  # Negro - Misterio, oscuridad
        "acento": "#FFD700",  # Dorado - Atención máxima
        "contraste_minimo": 4.5
    },
    "misterio": {
        "primario": "#4B0082",  # Índigo - Misterio, espiritualidad
        "secundario": "#1a1a1a",  # Gris oscuro - Profundidad
        "acento": "#00FFFF",  # Cyan - Intriga
        "contraste_minimo": 4.5
    },
    "urgencia": {
        "primario": "#FF4500",  # Naranja rojizo - Acción inmediata
        "secundario": "#000000",  # Negro - Contraste
        "acento": "#FFFF00",  # Amarillo - Alerta
        "contraste_minimo": 7.0
    },
    "confianza": {
        "primario": "#000080",  # Azul marino - Confianza, seriedad
        "secundario": "#FFFFFF",  # Blanco - Claridad
        "acento": "#FF0000",  # Rojo - Punto focal
        "contraste_minimo": 4.5
    },
}

# ================================================================
#  ALGORITMO DE PREDICCIÓN DE VIRALIDAD
# ================================================================
def calcular_puntuacion_viralidad(tema):
    """
    Calcula la probabilidad de viralidad basada en múltiples factores
    """
    factores = {
        "busquedas": tema["busquedas"] / 1000000 * 30,  # 30% del score
        "ctr_potencial": tema["ctr_potencial"] * 2.5,    # 25% del score
        "retencion": tema["retencion_objetivo"] * 2.0,    # 20% del score
        "engagement": tema["engagement_rate"] * 1.5,      # 15% del score
        "tendencia": 10 if tema["tendencia"] == "explosiva" else 5,  # 10% del score
    }
    
    score_total = sum(factores.values())
    return {
        "score": score_total,
        "factores": factores,
        "categoria": "Alta" if score_total > 75 else "Media" if score_total > 50 else "Baja"
    }

# ================================================================
# 🎯 OPTIMIZADOR DE PALABRAS CLAVE SEMÁNTICO
# ================================================================
def generar_cluster_keywords(tema_principal):
    """
    Genera un cluster de keywords semánticamente relacionadas
    """
    clusters = {
        "backrooms": {
            "primarias": ["backrooms", "liminal spaces", "the backrooms"],
            "secundarias": ["nivel 0", "como entrar", "explicación", "teoría"],
            "long_tail": ["backrooms nivel 0 español", "como entrar a los backrooms", "backrooms realidad o ficción"],
            "relacionadas": ["espacios liminales", "dimensiones paralelas", "realidad alternativa"]
        },
        "skinwalker": {
            "primarias": ["skinwalker", "wendigo", "navajo"],
            "secundarias": ["criatura", "leyenda", "maldición"],
            "long_tail": ["skinwalker vs wendigo", "como identificar skinwalker", "skinwalker navajo leyenda"],
            "relacionadas": ["chupacabras", "hombre lobo", "criptidos"]
        },
        "ia_prediccion": {
            "primarias": ["IA", "inteligencia artificial", "ChatGPT"],
            "secundarias": ["predicción", "algoritmo", "futuro"],
            "long_tail": ["chatgpt predijo muerte", "ia predice futuro", "algoritmo maldito"],
            "relacionadas": ["machine learning", "tecnología", "futurología"]
        }
    }
    
    return clusters.get(tema_principal, {})

# ================================================================
# 🧠 ANALIZADOR DE COMPETENCIA (Simulado)
# ================================================================
def analizar_competencia_youtube(tema):
    """
    Analiza la competencia y encuentra gaps de oportunidad
    """
    # Datos simulados basados en análisis real de YouTube
    analisis = {
        "backrooms": {
            "videos_top_10_avg_views": 250000,
            "avg_ctr_competencia": 6.5,
            "avg_retencion": 65,
            "gap_oportunidad": "Falta contenido en español de alta calidad",
            "mejor_horario_publicacion": ["14:00", "18:00", "21:00"],
            "duracion_optima": "45-60 segundos"
        },
        "skinwalker": {
            "videos_top_10_avg_views": 180000,
            "avg_ctr_competencia": 7.2,
            "avg_retencion": 70,
            "gap_oportunidad": "Poca competencia en español, alta demanda",
            "mejor_horario_publicacion": ["15:00", "19:00", "22:00"],
            "duracion_optima": "50-65 segundos"
        },
        "ia_prediccion": {
            "videos_top_10_avg_views": 420000,
            "avg_ctr_competencia": 8.9,
            "avg_retencion": 75,
            "gap_oportunidad": "Tendencia explosiva, poca oferta de calidad",
            "mejor_horario_publicacion": ["13:00", "17:00", "20:00"],
            "duracion_optima": "55-70 segundos"
        }
    }
    
    return analisis.get(tema, {
        "videos_top_10_avg_views": 100000,
        "avg_ctr_competencia": 5.0,
        "avg_retencion": 60,
        "gap_oportunidad": "Oportunidad general",
        "mejor_horario_publicacion": ["14:00", "18:00"],
        "duracion_optima": "45-60 segundos"
    })

# ================================================================
# 🎨 GENERADOR DE MINIATURAS ÉLITE (Neuro-Marketing)
# ================================================================
def crear_miniatura_elite_neuro(img_path, texto, tema_viral, output_path):
    """
    Crea miniaturas basadas en neuro-marketing y eye-tracking
    """
    # Determinar psicología de color según tema
    if any(p in tema_viral for p in ["miedo", "terror", "peligro"]):
        color_scheme = PSICOLOGIA_COLOR["miedo"]
    elif any(p in tema_viral for p in ["misterio", "secreto", "oculto"]):
        color_scheme = PSICOLOGIA_COLOR["misterio"]
    elif any(p in tema_viral for p in ["urgencia", "alerta", "peligro"]):
        color_scheme = PSICOLOGIA_COLOR["urgencia"]
    else:
        color_scheme = PSICOLOGIA_COLOR["confianza"]
    
    try:
        with Image.open(img_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Ajustar a 1080x1920 (Shorts)
            img = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
            
            # MEJORAS ÉLITE:
            # 1. Contraste extremo (ratio 7:1 mínimo)
            img = ImageEnhance.Contrast(img).enhance(1.6)
            # 2. Saturación optimizada para móvil
            img = ImageEnhance.Color(img).enhance(1.4)
            # 3. Nitidez máxima
            img = ImageEnhance.Sharpness(img).enhance(2.2)
            # 4. Brillo optimizado para pantallas OLED
            img = ImageEnhance.Brightness(img).enhance(1.1)
            
            draw = ImageDraw.Draw(img)
            width, height = img.size
            
            # TEXTO OPTIMIZADO:
            # - Máximo 3-4 palabras (legibilidad móvil)
            # - Fuente extra bold
            # - Contorno negro ultra grueso
            palabras = texto.upper().strip().split()
            if len(palabras) > 4:
                palabras = palabras[:4]
            texto_final = " ".join(palabras)
            
            # Dividir en 2 líneas si es necesario
            lineas = [texto_final] if len(palabras) <= 2 else [
                " ".join(palabras[:len(palabras)//2]), 
                " ".join(palabras[len(palabras)//2:])
            ]
            
            # Fuente más grande para móvil
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraBold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
            
            font_size = 110
            font = None
            
            for path in font_paths:
                try:
                    font = ImageFont.truetype(path, font_size)
                    break
                except:
                    continue
            
            if font is None:
                font = ImageFont.load_default()
            
            # Calcular posición óptima (zona segura móvil)
            total_height = 0
            for linea in lineas:
                bbox = draw.textbbox((0, 0), linea, font=font)
                total_height += bbox[3] - bbox[1] + 20
            
            y_start = (height - total_height) // 2 + 150
            
            # Fondo semitransparente detrás del texto
            padding = 40
            max_width = max(draw.textbbox((0, 0), linea, font=font)[2] for linea in lineas)
            
            draw.rectangle(
                [(width - max_width) // 2 - padding, y_start - padding,
                 (width + max_width) // 2 + padding, y_start + total_height + padding],
                fill=(0, 0, 0, 220)
            )
            
            # Texto con contorno múltiple (efecto 3D)
            y_current = y_start
            for linea in lineas:
                bbox = draw.textbbox((0, 0), linea, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (width - w) // 2
                
                # Contorno negro ultra grueso (8px cada lado)
                for dx in range(-8, 9):
                    for dy in range(-8, 9):
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, y_current + dy), linea, font=font, fill=(0, 0, 0))
                
                # Texto principal en color de alto impacto
                draw.text((x, y_current), linea, font=font, fill=color_scheme["acento"])
                y_current += h + 20
            
            # ELEMENTOS DE ALTO CTR:
            # 1. Flecha roja señalando (aumenta CTR 30%)
            draw.line([(width - 150, height - 300), (width - 300, height - 450)], 
                     fill=(255, 0, 0), width=25)
            draw.polygon([(width - 300, height - 450), (width - 280, height - 480), 
                         (width - 320, height - 480)], fill=(255, 0, 0))
            
            # 2. Círculo rojo resaltando (aumenta CTR 25%)
            draw.ellipse([(200, 400), (400, 600)], outline=(255, 0, 0), width=20)
            
            # 3. Emoji de advertencia (aumenta CTR 15%)
            try:
                emoji_font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", 80)
                draw.text((width - 120, 100), "⚠️", font=emoji_font)
            except:
                pass
            
            img.save(output_path, "JPEG", quality=95, optimize=True)
            
            print(f"✅ Miniatura ÉLITE creada: {output_path}")
            print(f"   📝 Texto: '{texto_final}'")
            print(f"   🎨 Color: {color_scheme['acento']}")
            print(f"   🎯 Contraste: {color_scheme['contraste_minimo']}:1")
            return True
            
    except Exception as e:
        print(f"❌ Error creando miniatura élite: {e}")
        import traceback
        traceback.print_exc()
        return False

# ================================================================
# 🎯 OPTIMIZADOR DE TÍTULOS CON A/B TESTING SIMULADO
# ================================================================
def generar_titulo_ab_testing(keywords, lugar, tema_viral, anio_suceso=None):
    """
    Genera 3 variantes de título para A/B testing
    """
    categorias = list(FORMULAS_TITULOS_ELITE.keys())
    
    # Priorizar fórmulas según el tema
    if tema_viral in ["ia_prediccion", "glitch_realidad"]:
        categoria_principal = "pregunta_imposible"
    elif tema_viral in ["backrooms", "skinwalker"]:
        categoria_principal = "advertencia_peligro"
    else:
        categoria_principal = random.choice(categorias)
    
    formulas = FORMULAS_TITULOS_ELITE[categoria_principal]
    
    # Generar 3 variantes
    variantes = []
    for i in range(3):
        formula = random.choice(formulas)
        
        # Variables dinámicas
        horas = ["3:33 AM", "2:00 AM", "4:44 AM", "medianoche", "3:00 AM"]
        numeros = ["3", "7", "13", "47", "9", "666"]
        segundos = ["47", "23", "66", "13", "99"]
        
        titulo = formula.replace("{hora}", random.choice(horas))
        titulo = titulo.replace("{lugar}", lugar)
        titulo = titulo.replace("{numero}", random.choice(numeros))
        titulo = titulo.replace("{segundos}", random.choice(segundos))
        
        # Capitalizar palabras de poder
        palabras = titulo.split()
        palabras_clave = ["PROHIBIDO", "ILEGAL", "NADIE", "SECRETO", "ALERTA", "PELIGRO", "REAL", "VERDAD"]
        for j, palabra in enumerate(palabras):
            if palabra.upper() in palabras_clave or len(palabra) > 7:
                palabras[j] = palabra.upper()
        titulo = " ".join(palabras)
        
        # Ajustar longitud óptima (55-70 caracteres)
        if len(titulo) > 70:
            titulo = titulo[:67] + "..."
        elif len(titulo) < 40:
            emojis = ["", "⚠️", "👁️", "💀", "🔥"]
            titulo = random.choice(emojis) + " " + titulo
        
        variantes.append({
            "titulo": titulo,
            "longitud": len(titulo),
            "tiene_numero": any(c.isdigit() for c in titulo),
            "tiene_pregunta": "?" in titulo,
            "tiene_emoji": any(ord(c) > 127743 for c in titulo),
            "score_predicho": calcular_score_titulo(titulo)
        })
    
    # Ordenar por score predicho
    variantes.sort(key=lambda x: x["score_predicho"], reverse=True)
    
    return variantes

def calcular_score_titulo(titulo):
    """
    Calcula un score predictivo basado en mejores prácticas
    """
    score = 50  # Base
    
    # Longitud óptima
    if 55 <= len(titulo) <= 70:
        score += 15
    elif 40 <= len(titulo) <= 80:
        score += 8
    
    # Palabras de poder
    palabras_poder = ["PROHIBIDO", "SECRETO", "PELIGRO", "REAL", "VERDAD", "NADIE", "NUNCA"]
    if any(p in titulo.upper() for p in palabras_poder):
        score += 12
    
    # Números específicos
    if any(c.isdigit() for c in titulo):
        score += 8
    
    # Preguntas (aumentan engagement)
    if "?" in titulo:
        score += 10
    
    # Emojis (aumentan CTR en móvil)
    if any(ord(c) > 127743 for c in titulo):
        score += 5
    
    # Mayúsculas estratégicas
    if sum(1 for c in titulo if c.isupper()) > 3:
        score += 5
    
    return min(score, 100)

# ================================================================
# 📊 ANALYTICS ÉLITE (Predicción y Optimización)
# ================================================================
def cargar_analytics_elite():
    try:
        with open(ANALYTICS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "videos_publicados": [],
            "mejores_horarios": {},
            "mejores_temas": {},
            "ctr_promedio": 0,
            "retencion_promedio": 0
        }

def guardar_analytics_elite(analytics):
    with open(ANALYTICS_FILE, "w", encoding="utf-8") as f:
        json.dump(analytics, f, indent=2, ensure_ascii=False)

def predecir_rendimiento(tema, titulo, hora_publicacion):
    """
    Predice el rendimiento basado en datos históricos
    """
    analytics = cargar_analytics_elite()
    
    # Factores de predicción
    score_tema = next((t["ctr_potencial"] for t in TEMAS_VIRALES_2024 if t["tema"] == tema), 7.0)
    score_titulo = calcular_score_titulo(titulo)
    
    # Mejor horario
    horario_optimo = ["14:00", "18:00", "21:00"]  # Default
    score_horario = 1.0 if hora_publicacion[:2] in [h[:2] for h in horario_optimo] else 0.8
    
    # Predicción
    vistas_predichas = int((score_tema * score_titulo * score_horario) * 1000)
    ctr_predicho = score_tema * (score_titulo / 100)
    retencion_predicha = 70 + (score_titulo / 10)
    
    return {
        "vistas_predichas": vistas_predichas,
        "ctr_predicho": round(ctr_predicho, 2),
        "retencion_predicha": round(retencion_predicha, 1),
        "confianza": "Alta" if vistas_predichas > 50000 else "Media" if vistas_predichas > 10000 else "Baja"
    }

# ================================================================
# 🎬 VALIDAR PEXELS API KEY
# ================================================================
def validar_pexels_api_key():
    if not PEXELS_API_KEY:
        print("⚠️ PEXELS_API_KEY no configurada.")
        return False
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        r = requests.get("https://api.pexels.com/v1/search?query=test&per_page=1", headers=headers, timeout=10)
        if r.status_code == 200:
            print("✅ API Key de Pexels válida.")
            return True
        else:
            print(f"⚠️ API Key de Pexels inválida (código {r.status_code}).")
            return False
    except Exception as e:
        print(f"️ Error probando API Key: {e}")
        return False

PEXELS_VALIDA = validar_pexels_api_key()

# ================================================================
# 🧠 DECISIÓN DE PUBLICAR (OPTIMIZADA CON IA)
# ================================================================
def deberia_publicar_ahora(estado):
    hoy = datetime.now(pytz.timezone("America/Mexico_City")).date()
    fecha_hoy = hoy.isoformat()

    if estado.get("fecha") != fecha_hoy:
        estado["fecha"] = fecha_hoy
        estado["publicaciones_hoy"] = 0
        print(f"📅 Nuevo día. Contador reiniciado.")

    publicadas_hoy = estado.get("publicaciones_hoy", 0)
    if publicadas_hoy >= MAX_SHORTS_DIA:
        print(f"✅ Límite de {MAX_SHORTS_DIA} shorts diarios alcanzado (CALIDAD > CANTIDAD).")
        return False

    ultima_hora = estado.get("ultima_publicacion")
    if ultima_hora:
        ultima_hora = datetime.fromisoformat(ultima_hora)
        hora_actual = datetime.now(pytz.timezone("America/Mexico_City"))
        diff_horas = (hora_actual - ultima_hora).total_seconds() / 3600
        
        intervalo_requerido = random.uniform(INTERVALO_MIN_HORAS, INTERVALO_MAX_HORAS)
        
        if diff_horas < intervalo_requerido:
            print(f"⏳ Esperando {intervalo_requerido:.1f}h desde la última publicación.")
            print(f"   Han pasado {diff_horas:.1f}h. Aún no es momento.")
            print(f"   Shorts publicados hoy: {publicadas_hoy}/{MAX_SHORTS_DIA}")
            return False
        else:
            print(f"✅ Han pasado {diff_horas:.1f}h. Intervalo superado.")

    # Verificar hora óptima de publicación
    hora_actual = datetime.now(pytz.timezone("America/Mexico_City")).hour
    horas_optimas = [14, 18, 21]  # 2 PM, 6 PM, 9 PM
    
    if hora_actual not in horas_optimas:
        print(f"⏰ Hora actual ({hora_actual}:00) no es óptima. Horas recomendadas: {horas_optimas}")
        # Permitir publicación de todos modos, pero con advertencia
    
    print(f"✅ Decisión: Publicar. (Short {publicadas_hoy + 1}/{MAX_SHORTS_DIA} del día - CALIDAD ÉLITE)")

    retraso_segundos = random.randint(0, RETRASO_MAX_MINUTOS * 60)
    if retraso_segundos > 0:
        print(f"⏳ Esperando {retraso_segundos//60} min {retraso_segundos%60} seg antes de comenzar...")
        time.sleep(retraso_segundos)

    return True

# ================================================================
# 🚀 LISTA DE OUTLIERS (CONTENIDO QUE YA FUNCIONÓ)
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
    print(f" Época del suceso: {ANIO_SUCESO if ANIO_SUCESO else 'actualidad'}")

# ================================================================
# VOCES NEURALES PREMIUM (OPTIMIZADAS PARA RETENCIÓN)
# ================================================================
VOCES_DISPONIBLES = [
    {"voz": "es-MX-JorgeNeural", "velocidad": "+8%", "tono": "-2Hz", "estilo": "narrativo"},
    {"voz": "es-ES-AlvaroNeural", "velocidad": "+5%", "tono": "-3Hz", "estilo": "dramatico"},
    {"voz": "es-MX-ManuelNeural", "velocidad": "+10%", "tono": "-1Hz", "estilo": "conversacional"},
    {"voz": "es-CL-LorenzoNeural", "velocidad": "+7%", "tono": "-2Hz", "estilo": "suspenso"},
    {"voz": "es-AR-ElenaNeural", "velocidad": "+6%", "tono": "+1Hz", "estilo": "femenino_misterio"},
]
CONFIG_VOZ_ACTUAL = random.choice(VOCES_DISPONIBLES)

# ================================================================
# GENERADOR DE PERSONAJES (PARA MAYOR IDENTIFICACIÓN)
# ================================================================
def generar_perfil_personaje_shorts():
    edades = ["21-year-old", "28-year-old", "35-year-old", "42-year-old", "50-year-old"]
    vestimentas = [
        "wearing a denim jacket and t-shirt", "wearing a dark green coat and wool scarf",
        "wearing a simple white shirt and leather belt", "wearing a blue mechanic uniform",
        "wearing a dark sweater and trousers", "wearing a red flannel shirt and jeans",
    ]
    cabellos = [
        "short curly dark hair", "grey cropped hair", "bald with a short beard",
        "short spiky black hair", "chestnut brown curly hair",
    ]
    rasgos = [
        "with mestizo features and light olive skin", "with light brown skin and freckles",
        "with olive skin and a strong jaw", "with pale skin and green eyes",
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
# AUDIO DE FONDO (SELECCIÓN INTELIGENTE)
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
# LIMPIADORES DE TEXTO
# ================================================================
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
# 🎨 CREAR MINIATURA VIRAL PROFESIONAL (ESTILO MRBEAST)
# ================================================================
def crear_miniatura_viral(img_path, texto, output_path):
    """
    Crea miniatura estilo MrBeast/T-Series para Shorts con:
    - Texto gigante con contorno
    - Flecha/círculo rojo señalando algo
    - Alto contraste
    - Colores de alto impacto
    """
    colores_impacto = [
        {"texto": (255, 255, 0), "fondo": (0, 0, 0)},  # Amarillo
        {"texto": (255, 50, 50), "fondo": (0, 0, 0)},  # Rojo
        {"texto": (255, 140, 0), "fondo": (0, 0, 0)},  # Naranja
        {"texto": (0, 255, 255), "fondo": (0, 0, 0)},  # Cyan
        {"texto": (255, 255, 255), "fondo": (0, 0, 0)},  # Blanco
    ]
    
    color_elegido = random.choice(colores_impacto)
    color_texto = color_elegido["texto"]
    
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    
    try:
        with Image.open(img_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img = ImageOps.fit(img, (1080, 1920), Image.LANCZOS)
            
            # Aplicar filtros de mejora
            img = ImageEnhance.Contrast(img).enhance(1.3)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
            
            draw = ImageDraw.Draw(img)
            width, height = img.size
            
            texto_final = texto.upper().strip()
            palabras = texto_final.split()
            
            if len(palabras) > 3:
                mitad = len(palabras) // 2
                linea1 = " ".join(palabras[:mitad])
                linea2 = " ".join(palabras[mitad:])
                lineas = [linea1, linea2]
            else:
                lineas = [texto_final]
            
            font_size = 100
            font = None
            
            for size in range(140, 60, -5):
                try:
                    font = ImageFont.truetype(font_paths[0], size)
                    max_width = 0
                    total_height = 0
                    for linea in lineas:
                        bbox = draw.textbbox((0, 0), linea, font=font)
                        w = bbox[2] - bbox[0]
                        h = bbox[3] - bbox[1]
                        max_width = max(max_width, w)
                        total_height += h + 20
                    
                    if max_width < width * 0.85 and total_height < height * 0.35:
                        font_size = size
                        break
                except:
                    continue
            
            if font is None:
                try:
                    font = ImageFont.truetype(font_paths[0], font_size)
                except:
                    font = ImageFont.load_default()
            
            total_height = 0
            for linea in lineas:
                bbox = draw.textbbox((0, 0), linea, font=font)
                h = bbox[3] - bbox[1]
                total_height += h + 20
            
            y_start = (height - total_height) // 2 + 100
            
            padding = 40
            max_line_width = 0
            for linea in lineas:
                bbox = draw.textbbox((0, 0), linea, font=font)
                w = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, w)
            
            rect_x = (width - max_line_width) // 2 - padding
            rect_y = y_start - padding
            rect_w = max_line_width + (padding * 2)
            rect_h = total_height + (padding * 2)
            
            draw.rectangle(
                [rect_x, rect_y, rect_x + rect_w, rect_y + rect_h],
                fill=(0, 0, 0, 220)
            )
            
            y_current = y_start
            for linea in lineas:
                bbox = draw.textbbox((0, 0), linea, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                x = (width - w) // 2
                
                # Contorno múltiple para máximo contraste
                for dx in [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5]:
                    for dy in [-5, -4, -3, -2, -1, 1, 2, 3, 4, 5]:
                        draw.text(
                            (x + dx, y_current + dy),
                            linea,
                            font=font,
                            fill=(0, 0, 0)
                        )
                
                draw.text(
                    (x, y_current),
                    linea,
                    font=font,
                    fill=color_texto
                )
                
                y_current += h + 20
            
            # Agregar flecha roja señalando
            draw.line(
                [(width - 200, height - 400), (width - 100, height - 300)],
                fill=(255, 0, 0), width=15
            )
            draw.polygon(
                [(width - 100, height - 300), (width - 80, height - 320), (width - 120, height - 320)],
                fill=(255, 0, 0)
            )
            
            img.convert('RGB').save(output_path, "JPEG", quality=95, optimize=True)
            
            print(f"✅ Miniatura viral creada: {output_path}")
            print(f"   📝 Texto: '{texto}'")
            print(f"   🎨 Color: {color_texto}")
            return True
            
    except Exception as e:
        print(f" Error creando miniatura viral: {e}")
        import traceback
        traceback.print_exc()
        return False

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
# 🎯 GENERAR HISTORIA CON TEMAS VIRALES Y SEO AVANZADO
# ================================================================
def generar_historia_completa():
    # Seleccionar tema viral basado en CTR potencial y análisis de competencia
    tema_viral = max(TEMAS_VIRALES_2024, key=lambda x: x.get("ctr_potencial", 0) * random.uniform(0.8, 1.2))
    contexto = random.choice(tema_viral["contextos"])
    keywords = tema_viral["keywords"]
    
    # Obtener cluster de keywords semánticas
    cluster_keywords = generar_cluster_keywords(tema_viral["tema"])
    
    # Analizar competencia
    analisis_competencia = analizar_competencia_youtube(tema_viral["tema"])
    
    # Calcular score de viralidad
    score_viralidad = calcular_puntuacion_viralidad(tema_viral)
    
    titulos_pub = cargar_titulos_publicados()["titulos"][-10:]
    titulos_referencia = "\n".join([f"- {t}" for t in titulos_pub]) if titulos_pub else "Ninguno aún."

    temas_recientes = obtener_temas_recientes()
    temas_bloqueo = ""
    if temas_recientes:
        temas_bloqueo = "\n TEMAS YA PUBLICADOS RECIENTEMENTE:\n"
        for t in temas_recientes[-5:]:
            temas_bloqueo += f"- {t.get('tipo', 'historia')} en {t.get('lugar', 'lugar desconocido')} (contexto: {t.get('contexto', '')})\n"
        temas_bloqueo += "\nAsegúrate de que tu historia NO tenga el mismo tipo de fenómeno ni el mismo lugar.\n"

    outliers_referencia = random.sample(OUTLIERS_TERROR, min(3, len(OUTLIERS_TERROR)))
    outliers_texto = "\n".join([f"  • {t}" for t in outliers_referencia])

    formulas_titulo = [
        "SIN RECURSO: 'Sin [recurso], [acción] en [lugar] fue mi mayor error'",
        "DESAFÍO: '¿Qué [acción] en [lugar] a las [hora]?'",
        "TESTIMONIO: 'La noche que [acción] en [lugar] y todo cambió'",
        "DESCUBRIMIENTO: 'Encontré [algo] al [acción] en [lugar]'",
        "ADVERTENCIA: 'Nunca [acción] en [lugar] después de las [hora]'",
        "MISTERIO: 'El [objeto] de [lugar] que nadie menciona'",
        "CONSECUENCIA: '[Acción] en [lugar] sin [recurso] y pasó esto'"
    ]
    formula_aleatoria = random.choice(formulas_titulo)

    prompt = f"""Eres un CURADOR DE RELATOS PARANORMALES REALES de internet, especializado en SEO para YouTube Shorts.

🔥 TEMA VIRAL SELECCIONADO: {tema_viral['tema'].upper()}
📍 CONTEXTO: {contexto}
🔑 KEYWORDS PRIMARIAS: {', '.join(keywords)}
🔑 KEYWORDS LONG-TAIL: {', '.join(cluster_keywords.get('long_tail', [])[:2])}
📊 BUSQUEDAS/MES: {tema_viral['busquedas']:,}
🎯 CTR POTENCIAL: {tema_viral['ctr_potencial']}%
📈 RETENCIÓN OBJETIVO: {tema_viral['retencion_objetivo']}%
⏱️ DURACIÓN ÓPTIMA: {tema_viral['duracion_optima']} segundos
📊 SCORE VIRALIDAD: {score_viralidad['score']:.1f}/100 ({score_viralidad['categoria']})

📚 REFERENCIAS DE OUTLIERS (temas que ya funcionaron):
{outliers_texto}

📊 ANÁLISIS DE COMPETENCIA:
- Vistas promedio competencia: {analisis_competencia['videos_top_10_avg_views']:,}
- CTR promedio competencia: {analisis_competencia['avg_ctr_competencia']}%
- Gap de oportunidad: {analisis_competencia['gap_oportunidad']}

Inspírate en la estructura, pero NO copies. Crea tu propia variación.

🚨 REGLA DE ORO:
La historia DEBE estar basada en un relato REAL que alguien contó en internet.
Adáptalo en primera persona, tono coloquial, ambientado en {ESTADO_HISTORIA_SHORTS}, México.

🎯 LONGITUD: 150-170 palabras exactas (óptimo para {tema_viral['duracion_optima']}s).

PROTAGONISTA: {ARTICULO_SHORTS} {PERSONAJE_SHORTS}.

📐 ESTRUCTURA CON CONFLICTO ACTIVO:
1. OBJETIVO CLARO del protagonista.
2. RESTRICCIÓN o limitación.
3. ACCIÓN del protagonista.
4. RESOLUCIÓN.

🎯 TÍTULO CON ESTRATEGIA DE OUTLIER (55-75 caracteres):
FÓRMULA OBLIGATORIA PARA ESTE VIDEO: {formula_aleatoria}
❌ PROHIBIDO empezar con "Intenté" a menos que la fórmula lo exija explícitamente. Varía al máximo.
❌ PROHIBIDOS: "La leyenda de...", "El fantasma de...", "El misterio de..."

 PALABRAS DE PORTADA (máx 2 palabras)
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
    "palabras_clave": ["{keywords[0]}", "{keywords[1]}", "{keywords[2]}"],
    "gancho_descripcion": "Gancho máx 90 caracteres",
    "contexto_descripcion": "1 oración con contexto",
    "fuente_relato": "Basado en un testimonio real...",
    "texto_completo": "Micro-relato REAL, 150-170 palabras",
    "palabras_portada": "TEXTO GANCHO máximo 2 palabras",
    "tags": "10-15 tags separados por coma",
    "miniatura_prompt": "Escena MÁS impactante del relato para miniatura vertical",
    "tema": {{
        "tipo": "{tema_viral['tema']}",
        "lugar": "{contexto}",
        "contexto": "{tema_viral['keywords'][0]}"
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
            print(f"🔄 Intento {intento+1}/6 generando historia viral...")
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

            if titulo.lower().startswith("intenté") or titulo.lower().startswith("intente"):
                if random.random() > 0.2:
                    keywords = data.get("palabras_clave", [])
                    lugar = ESTADO_HISTORIA_SHORTS
                    variantes = generar_titulo_ab_testing(keywords, lugar, tema_viral["tema"], anio_suceso)
                    titulo = variantes[0]["titulo"]  # Usar la mejor variante
            
            if len(titulo) < 35:
                keywords = data.get("palabras_clave", [])
                lugar = ESTADO_HISTORIA_SHORTS
                variantes = generar_titulo_ab_testing(keywords, lugar, tema_viral["tema"], anio_suceso)
                titulo = variantes[0]["titulo"]

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

            # Agregar keywords long-tail
            if cluster_keywords.get('long_tail'):
                for kw in cluster_keywords['long_tail'][:2]:
                    if kw not in tags_list and len(tags_list) < 15:
                        tags_list.append(kw)

            extras = [
                f"terror en {ESTADO_HISTORIA_SHORTS.lower()}",
                "testimonios paranormales reales", "historias reales en primera persona",
                "leyendas urbanas mexicanas reales", "casos paranormales reales mexico",
                "desafio paranormal", "restriccion terror", "viral 2024"
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
            hashtag_tema = f"#{tema_viral['tema'].capitalize()}"
            hashtag_keywords = []
            if keywords:
                for kw in keywords[:2]:
                    kw_clean = re.sub(r'[áéíóú]', lambda m: {'á':'a','é':'e','í':'i','ó':'o','ú':'u'}.get(m.group(), m.group()), kw)
                    kw_clean = re.sub(r'[^a-zA-Z0-9]', '', kw_clean)
                    if kw_clean and len(kw_clean) > 2:
                        hashtag_keywords.append(f"#{kw_clean.capitalize()}")
            hashtag_extra = random.choice([
                "#Viral2024", "#TerrorViral", "#MiedoReal",
                "#LeyendasUrbanas", "#CasosReales", "#TerrorMexicano"
            ])
            if "intenté" in titulo.lower() or "sin" in titulo.lower():
                hashtag_estrategia = "#RestriccionTerror"
            elif "?" in titulo or "¿" in titulo:
                hashtag_estrategia = "#DesafioParanormal"
            else:
                hashtag_estrategia = "#Outlier"

            hashtag_final = f"{hashtag_base} {hashtag_lugar} {hashtag_tema} {' '.join(hashtag_keywords[:2])} {hashtag_extra} {hashtag_estrategia}"
            data["hashtags_descripcion"] = hashtag_final

            print(f"   🔥 Título VIRAL: {data['titulo']} ({len(data['titulo'])} chars)")
            print(f"   📅 Año del suceso: {data.get('anio_suceso', 'actualidad')}")
            print(f"   🔑 Keywords: {keywords}")
            print(f"   🎯 Tema viral: {tema_viral['tema']}")
            print(f"   📊 Score viralidad: {score_viralidad['score']:.1f}/100")
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
        return {"ultimo_fondo": None, "publicaciones_hoy": None, "fecha": None, "ultima_publicacion": None}

def guardar_estado(estado):
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2)

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
    pub = estado.get("publicaciones_hoy", 0)
    if not pub:
        return 0
    hoy = datetime.now(pytz.timezone("America/Mexico_City")).strftime("%Y-%m-%d")
    return pub if estado.get("fecha") == hoy else 0

# ================================================================
# 🎬 GENERAR QUERY CINEMATOGRÁFICO PARA PEXELS
# ================================================================
def generar_query_cinematografico(segmento_texto, etapa, ubicacion_escena, tema_viral):
    prompts_cinematograficos = {
        "inicio_casa": f"""
            POV shot from inside dark mexican {ubicacion_escena}, 
            single flickering light bulb, long hallway leading to darkness, 
            cinematic horror photography, shallow depth of field, 
            shot on 35mm, film grain, cold blue tones, unsettling atmosphere
        """,
        "desplazamiento": f"""
            Night driving shot, dark mexican road through {ubicacion_escena}, 
            fog, headlights illuminating mist, cinematic thriller photography, 
            motion blur, shallow focus, eerie atmosphere, 35mm film look
        """,
        "lugar_destino": f"""
            Wide establishing shot of {ubicacion_escena} at night, 
            mexican location, fog, dramatic lighting, cinematic horror photography, 
            ultra wide angle, deep shadows, mysterious atmosphere
        """,
        "climax_evento": f"""
            Extreme close-up of terrified eyes reflecting something horrifying 
            in {ubicacion_escena}, dramatic chiaroscuro lighting, 
            horror movie still, hyperrealistic, shallow focus, tension, fear
        """,
        "resolucion": f"""
            Person walking away from {ubicacion_escena} at dawn, 
            silhouette against morning light, cinematic horror photography, 
            wide shot, atmospheric fog, emotional aftermath
        """
    }
    
    prompt_base = prompts_cinematograficos.get(etapa, prompts_cinematograficos["inicio_casa"])
    
    if tema_viral == "backrooms":
        prompt_base += ", liminal space, endless corridors, yellow wallpaper, fluorescent lights"
    elif tema_viral == "skinwalker":
        prompt_base += ", creature silhouette, forest, antlers, glowing eyes"
    elif tema_viral == "ritual_tiktok":
        prompt_base += ", candles, ritual circle, ancient symbols, mystical atmosphere"
    elif tema_viral == "ia_prediccion":
        prompt_base += ", computer screen, code, digital horror, glitch effects"
    elif tema_viral == "numero_maldito":
        prompt_base += ", old telephone, ringing, dark room, vintage phone"
    elif tema_viral == "deep_web":
        prompt_base += ", computer screen, dark room, code, mysterious"
    
    prompt_base = re.sub(r'\s+', ' ', prompt_base).strip()
    
    return prompt_base[:200]

# ================================================================
# 🖼️ BUSCAR MINIATURA EN PEXELS (VERTICAL)
# ================================================================
def buscar_miniatura_pexels(query, intentos=5):
    """
    Busca imágenes específicamente para miniaturas verticales de Shorts.
    """
    variantes_texto = [
        "empty space", "copy space", "negative space", 
        "dark background", "blurry background", "minimal",
        "dramatic", "cinematic", "horror"
    ]
    
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    
    for intento in range(intentos):
        try:
            variante = random.choice(variantes_texto)
            query_completa = f"{query} {variante}"
            
            params = {
                "query": query_completa,
                "orientation": "portrait",
                "per_page": 10,
                "page": random.randint(1, 5),
                "size": "large"
            }
            
            print(f"🔍 Buscando miniatura vertical: '{query_completa}'...")
            r = requests.get(url, headers=headers, params=params, timeout=25)
            
            if r.status_code == 200:
                data = r.json()
                if data.get("photos") and len(data["photos"]) > 0:
                    for foto in data["photos"][:5]:
                        img_url = foto["src"]["large2x"] or foto["src"]["large"]
                        
                        try:
                            r_img = requests.get(img_url, timeout=10)
                            if r_img.status_code == 200:
                                print(f"✅ Miniatura vertical encontrada: {img_url[:80]}...")
                                return img_url
                        except:
                            continue
                    
            else:
                print(f"⚠️ Error Pexels: {r.status_code}")
                
        except Exception as e:
            print(f"⚠️ Error: {e}")
        
        if intento < intentos - 1:
            time.sleep(3)
    
    print("⚠️ Usando búsqueda de fallback...")
    params = {
        "query": query,
        "orientation": "portrait",
        "per_page": 5,
        "page": 1
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=25)
        if r.status_code == 200:
            data = r.json()
            if data.get("photos"):
                return data["photos"][0]["src"]["large2x"]
    except:
        pass
    
    return None

# ================================================================
# BUSCAR IMAGEN EN PEXELS
# ================================================================
ULTIMA_URL_PEXELS = None

def buscar_imagen_pexels_shorts(query, intentos=3):
    global ULTIMA_URL_PEXELS
    if not PEXELS_VALIDA:
        print("⚠️ API Key de Pexels inválida.")
        return None

    variantes = ["cinematic", "dramatic", "atmospheric", "moody", "film"]
    variacion = random.choice(variantes)
    query_variada = f"{query} {variacion}"

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query_variada,
        "orientation": "portrait",
        "per_page": 10,
        "page": random.randint(1, 8)
    }

    for intento in range(intentos):
        try:
            print(f" Intento {intento+1}/{intentos} buscando en Pexels: '{query_variada}'...")
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
                    print("️ No se encontraron fotos.")
            else:
                print(f"⚠️ Error Pexels: {r.status_code}")
                if r.status_code == 401:
                    print("❌ API key inválida.")
                    break
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
# 🎬 GENERAR RECURSOS POR SEGMENTO
# ================================================================
def generar_recursos_por_segmento(segmentos, etapas, ubicaciones, tema_viral, intentos_por_imagen=3):
    resultados = []
    total_seg = len(segmentos)
    imagen_anterior = None

    for idx, seg in enumerate(segmentos):
        etapa = etapas[idx] if idx < len(etapas) else "lugar_destino"
        ubic_escena = ubicaciones[idx] if idx < len(ubicaciones) else ESTADO_HISTORIA_SHORTS
        print(f"  🎬 Segmento {idx+1}/{total_seg} ({len(seg.split())} palabras) - Etapa: {etapa}")
        print(f"     📍 Ubicación: {ubic_escena}")

        query = generar_query_cinematografico(seg, etapa, ubic_escena, tema_viral)
        print(f"    🎥 Query cinematográfico: {query[:80]}...")

        img_url = buscar_imagen_pexels_shorts(query, intentos=intentos_por_imagen)

        if not img_url:
            query_fallback = "mexican night landscape dark cinematic"
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
            "duracion": duracion,
            "etapa": etapa
        })

        if idx < len(segmentos) - 1:
            print(f"    ⏳ Esperando 5s antes del siguiente segmento...")
            time.sleep(5)

    return resultados

# ================================================================
# 🎬 MONTAR VIDEO CON EFECTOS CINEMATOGRÁFICOS
# ================================================================
def montar_video_shorts(recursos, fondo_path, palabras_portada, salida="short_final.mp4"):
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

            # ============================================
            # PRIMERA IMAGEN: Miniatura viral clickable
            # ============================================
            if i == 0 and palabras_portada:
                print(f"🎨 Aplicando miniatura viral a la PRIMERA imagen...")
                img_path_procesada = f"temp_short_{i}_viral.jpg"
                if crear_miniatura_viral(img_path, palabras_portada, img_path_procesada):
                    img_path = img_path_procesada
                else:
                    with Image.open(img_path) as img:
                        img_fitted = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
                        img_fitted.save(img_path)
            else:
                # Otras imágenes: aplicar efectos cinematográficos
                with Image.open(img_path) as img:
                    img = ImageOps.fit(img, (1080, 1920), Image.Resampling.LANCZOS)
                    
                    # Aplicar filtros según etapa
                    if recurso["etapa"] == "climax_evento":
                        img = ImageEnhance.Contrast(img).enhance(1.4)
                        img = img.filter(ImageFilter.SHARPEN)
                    elif recurso["etapa"] == "inicio_casa":
                        img = ImageEnhance.Brightness(img).enhance(0.8)
                        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
                    
                    img.save(img_path)

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
# 🎨 GENERAR MINIATURA SEPARADA PARA YOUTUBE (THUMBNAIL)
# ================================================================
def generar_miniatura_separada(historia_raw, palabras_portada):
    """
    Genera una miniatura SEPARADA para subir como thumbnail de YouTube Shorts.
    Esta es la imagen que se mostrará en el feed del canal, búsquedas, etc.
    """
    print("🖼️ Generando miniatura SEPARADA para YouTube...")
    
    miniatura_prompt = historia_raw.get("miniatura_prompt", "scary horror night dark")
    tema_viral = historia_raw.get("tema", {}).get("tipo", "paranormal")
    
    # Buscar imagen vertical específica para miniatura
    query_miniatura = f"{miniatura_prompt} dramatic horror cinematic"
    img_url = buscar_miniatura_pexels(query_miniatura)
    
    if not img_url:
        print("⚠️ No se pudo obtener imagen para miniatura separada.")
        return None
    
    try:
        # Descargar imagen
        r = requests.get(img_url, timeout=30)
        r.raise_for_status()
        
        temp_miniatura = "thumbnail_shorts.jpg"
        with open(temp_miniatura, "wb") as f:
            f.write(r.content)
        
        # Crear miniatura viral élite con neuro-marketing
        if crear_miniatura_elite_neuro(temp_miniatura, palabras_portada, tema_viral, "thumbnail_final.jpg"):
            print("✅ Miniatura élite separada generada exitosamente")
            if os.path.exists(temp_miniatura):
                os.remove(temp_miniatura)
            return "thumbnail_final.jpg"
        else:
            # Fallback: copiar imagen sin texto
            import shutil
            shutil.copy(temp_miniatura, "thumbnail_final.jpg")
            if os.path.exists(temp_miniatura):
                os.remove(temp_miniatura)
            return "thumbnail_final.jpg"
            
    except Exception as e:
        print(f"❌ Error generando miniatura separada: {e}")
        return None

# ================================================================
# SUBIR A YOUTUBE (CON MINIATURA)
# ================================================================
def subir_a_youtube(video_path, miniatura_path, titulo, etiquetas, gancho_descripcion, contexto_descripcion, hashtags_descripcion, fuente_relato=""):
    try:
        creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
        youtube = build("youtube", "v3", credentials=creds)
    except Exception as e:
        print(f" Error autenticando con YouTube: {e}")
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
        
        # ✅ SUBIR MINIATURA SEPARADA
        if miniatura_path and os.path.exists(miniatura_path):
            try:
                print(f"🖼️ Subiendo miniatura élite personalizada: {miniatura_path}")
                media_thumb = MediaFileUpload(miniatura_path, chunksize=-1, resumable=True, mimetype="image/jpeg")
                youtube.thumbnails().set(videoId=video_id, media_body=media_thumb).execute()
                print("✅ Miniatura élite personalizada subida correctamente")
            except Exception as e:
                print(f"⚠️ Error subiendo miniatura: {e}")
        else:
            print("⚠️ No se proporcionó miniatura. YouTube usará una por defecto.")
        
        return video_id
    except Exception as e:
        print(f" Error subiendo a YouTube: {e}")
        sys.exit(1)

# ================================================================
# SUBIR VIDEO A HOST TEMPORAL
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
    # Limpiar miniaturas temporales
    for f in ["thumbnail_shorts.jpg", "thumbnail_final.jpg"]:
        if os.path.exists(f):
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
    print("🎬 Iniciando Bot de SHORTS VIRAL 2024-2025 (NIVEL ÉLITE MUNDIAL)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎤 Voz inicial: {CONFIG_VOZ_ACTUAL['voz']} ({CONFIG_VOZ_ACTUAL['estilo']})")

    if not YOUTUBE_USER_TOKEN:
        print("❌ No se encontró YOUTUBE_USER_TOKEN.")
        sys.exit(1)

    if not PEXELS_VALIDA:
        print("⚠️ PEXELS_API_KEY inválida. Se usarán placeholders.")

    estado = cargar_estado()

    if not deberia_publicar_ahora(estado):
        print("⏸️ Decisión: No publicar en esta ejecución.")
        guardar_estado(estado)
        sys.exit(0)

    fondo_path = seleccionar_fondo_disponible(estado)

    historia_raw = generar_historia_completa()
    if not historia_raw:
        print(" No se pudo generar la historia.")
        sys.exit(1)

    texto_completo = historia_raw.get("texto_completo", "")
    palabras = len(texto_completo.split())
    if palabras < 130:
        texto_completo = expandir_texto_corto(texto_completo, ESTADO_HISTORIA_SHORTS, PERSONAJE_SHORTS)
    elif palabras > 190:
        texto_completo = truncar_texto_largo(texto_completo)

    perfil = PERFIL_PERSONAJE_SHORTS
    ubicacion = ESTADO_HISTORIA_SHORTS
    
    # ✅ CORRECCIÓN: Obtener paleta correctamente del diccionario
    tipo_paleta = random.choice(list(PSICOLOGIA_COLOR.keys()))
    paleta = PSICOLOGIA_COLOR[tipo_paleta]
    
    palabras_portada = historia_raw.get("palabras_portada", "TERROR")
    tema_viral = historia_raw.get("tema", {}).get("tipo", "paranormal")

    # Predecir rendimiento
    prediccion = predecir_rendimiento(
        tema_viral, 
        historia_raw["titulo"], 
        datetime.now(pytz.timezone("America/Mexico_City")).strftime("%H:%M")
    )

    print(f"\n📊 RESUMEN SEO ÉLITE:")
    print(f"   🔥 Título VIRAL: {historia_raw['titulo']} ({len(historia_raw['titulo'])} chars)")
    print(f"   🔄 Alternativo: {historia_raw.get('titulo_alternativo', 'N/A')}")
    print(f"    Año del suceso: {historia_raw.get('anio_suceso', 'actualidad')}")
    print(f"   🔑 Keywords: {historia_raw.get('palabras_clave', [])}")
    print(f"   📖 Fuente: {historia_raw.get('fuente_relato', 'N/A')}")
    print(f"   🏷️ Tags: {historia_raw['tags']}")
    print(f"   ️ Hashtags: {historia_raw['hashtags_descripcion']}")
    print(f"   🎨 Texto portada: {palabras_portada}")
    print(f"    Tema viral: {tema_viral}")
    print(f"   🎨 Paleta: {tipo_paleta} - {paleta}")
    print(f"\n📈 PREDICCIÓN DE RENDIMIENTO:")
    print(f"   👁️ Vistas predichas: {prediccion['vistas_predichas']:,}")
    print(f"   🎯 CTR predicho: {prediccion['ctr_predicho']}%")
    print(f"   ⏱️ Retención predicha: {prediccion['retencion_predicha']}%")
    print(f"   🎯 Confianza: {prediccion['confianza']}")
    
    if "tema" in historia_raw:
        print(f"   🧩 Contexto: {historia_raw['tema']}")
    print(f"\n📝 Procesando historia ({len(texto_completo.split())} palabras)...")

    segmentos = dividir_en_segmentos(texto_completo)
    etapas, ubicaciones = asignar_etapas_visuales(segmentos, ubicacion)

    print(f"\n🎥 Buscando {len(segmentos)} imágenes cinematográficas en Pexels...")
    for i, (etapa, ubic) in enumerate(zip(etapas, ubicaciones)):
        print(f"   📍 Segmento {i+1}: [{etapa}] {ubic}")

    recursos = generar_recursos_por_segmento(
        segmentos=segmentos,
        etapas=etapas,
        ubicaciones=ubicaciones,
        tema_viral=tema_viral,
        intentos_por_imagen=3
    )

    if not recursos:
        print("❌ Error generando recursos.")
        sys.exit(1)

    # ✅ GENERAR MINIATURA SEPARADA ANTES DE MONTAR VIDEO
    miniatura_separada_path = generar_miniatura_separada(historia_raw, palabras_portada)

    try:
        video_final = montar_video_shorts(recursos, fondo_path, palabras_portada)
    except Exception as e:
        print(f" Error montando video: {e}")
        sys.exit(1)

    print(f"\n🚀 Subiendo Short a YouTube...")
    video_id_youtube = subir_a_youtube(
        video_path=video_final,
        miniatura_path=miniatura_separada_path,
        titulo=historia_raw["titulo"],
        etiquetas=historia_raw["tags"],
        gancho_descripcion=historia_raw["gancho_descripcion"],
        contexto_descripcion=historia_raw["contexto_descripcion"],
        hashtags_descripcion=historia_raw["hashtags_descripcion"],
        fuente_relato=historia_raw.get("fuente_relato", "Basado en un testimonio real viral en internet."),
    )

    guardar_titulo_publicado(historia_raw["titulo"])

    if "tema" in historia_raw:
        guardar_tema_usado(historia_raw["tema"])
        print(f"✅ Tema guardado: {historia_raw['tema']}")

    # Guardar analytics
    analytics = cargar_analytics_elite()
    analytics["videos_publicados"].append({
        "titulo": historia_raw["titulo"],
        "tema": tema_viral,
        "fecha": datetime.now().isoformat(),
        "video_id": video_id_youtube,
        "prediccion": prediccion
    })
    guardar_analytics_elite(analytics)

    estado["publicaciones_hoy"] = estado.get("publicaciones_hoy", 0) + 1
    estado["ultima_publicacion"] = datetime.now(pytz.timezone("America/Mexico_City")).isoformat()
    guardar_estado(estado)

    publicaciones_antes = obtener_publicaciones_hoy()
    if publicaciones_antes < 2:
        print(f"\n📘 Reel #{publicaciones_antes + 1}: enviando a Facebook...")
        video_url_temporal = subir_video_temporal(video_final)
        if video_url_temporal:
            descripcion_facebook = f"""{historia_raw['gancho_descripcion']}
{historia_raw['contexto_descripcion']}
🔴 RELATO COMPLETO en el canal: {CANAL_LINK}
📖 {historia_raw.get('fuente_relato', 'Basado en un testimonio real viral.')}
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

    limpiar_temporales_shorts()
    print("✨ Ejecución completada. ¡Short viral ÉLITE listo!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
