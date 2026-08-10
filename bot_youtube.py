import os
import json
import re
import requests
import time
import random
from datetime import datetime
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip
from PIL import Image
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ================================================================
# CONFIGURACIÓN (variables desde GitHub Secrets)
# ================================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
AZURE_TTS_KEY = os.getenv("AZURE_TTS_KEY")
AZURE_TTS_REGION = os.getenv("AZURE_TTS_REGION")
AGNES_API_KEY = os.getenv("AGNES_API_KEY")
YOUTUBE_USER_TOKEN = json.loads(os.getenv("YOUTUBE_USER_TOKEN")) if os.getenv("YOUTUBE_USER_TOKEN") else {}

FACEBOOK_LINK = "https://www.facebook.com/profile.php?id=61593237382982"

# ================================================================
# LISTA DE ARCHIVOS DE FONDO DISPONIBLES
# ================================================================
FONDOS_DISPONIBLES = [
    "Ash and Marrow.mp3",
    "Black Maw.mp3",
    "Cold Hollow.mp3",
    "Hollow Marrow.mp3",
    "Sunken Dread.mp3",
    "Sunless Vault.mp3",
    "The Deep Rot.mp3"
]

def seleccionar_fondo_disponible():
    """
    Busca un archivo de fondo disponible en la lista.
    Devuelve el primer archivo que exista, o None si ninguno existe.
    """
    fondos = FONDOS_DISPONIBLES.copy()
    random.shuffle(fondos)
    
    for fondo in fondos:
        if os.path.exists(fondo):
            print(f"✅ Audio de fondo encontrado: {fondo}")
            return fondo
    
    print("⚠️ No se encontró ningún archivo de fondo disponible.")
    return None

# Elegir un fondo disponible al inicio
FONDO_AUDIO_FILE = seleccionar_fondo_disponible()
if FONDO_AUDIO_FILE:
    print(f"🎵 Audio de fondo seleccionado: {FONDO_AUDIO_FILE}")
else:
    print("⚠️ No se usará audio de fondo.")

# ================================================================
# LIMPIAR PROMPTS DE IMAGEN (2K, Inglés, Sin Gore, Sin Texto)
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        return "Cinematic photo of Mexico City historic center at night, streetlights, 35mm photograph, hyperrealistic, 2k, ultra detailed, no text, no letters"
    prompt = re.sub(r'\n+', ' ', prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r'[^\x00-\x7F]+', '', prompt)
    prompt = re.sub(r'\s+', ' ', prompt)
    estilo_limpio = " Cinematic lighting, 35mm film photograph, realistic everyday Mexican people, clean skin, no blood, no zombies, no gore, professional photography, 2k, hyperrealistic, ultra detailed, sharp focus, no text, no words, no signs, no typography, no writing."
    return (prompt.strip() + estilo_limpio)[:500]

# ================================================================
# LIMPIAR RESPUESTA JSON DE DEEPSEEK
# ================================================================
def limpiar_respuesta_json(respuesta):
    respuesta = re.sub(r'```json\s*', '', respuesta)
    respuesta = re.sub(r'```\s*', '', respuesta)
    inicio = respuesta.find('{')
    fin = respuesta.rfind('}')
    if inicio != -1 and fin != -1:
        json_str = respuesta[inicio:fin+1]
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*\]', ']', json_str)
        return json_str
    return respuesta

# ================================================================
# GENERAR FALLBACK LIMPIO
# ================================================================
def generar_fallback(respuesta):
    print("⚠️ Usando fallback limpiado: removiendo etiquetas de prompt del audio.")
    
    texto_narrativo = re.sub(r'imagen_prompt.*?(?=(texto|$))', '', respuesta, flags=re.DOTALL | re.IGNORECASE)
    texto_narrativo = re.sub(r'prompt.*?:', '', texto_narrativo, flags=re.IGNORECASE)
    texto_narrativo = re.sub(r'[\{\}\[\]"]', '', texto_narrativo)
    texto_narrativo = re.sub(r'\s+', ' ', texto_narrativo).strip()
    
    segmentos = []
    chars_por_segmento = 450
    for i in range(0, len(texto_narrativo), chars_por_segmento):
        segmento = texto_narrativo[i:i+chars_por_segmento]
        if len(segmento.strip()) > 40:
            segmentos.append({
                "texto": segmento,
                "imagen_prompt": "Cinematic photograph of an empty street in Mexico City at night, street lamps, fog, realistic 35mm photo, 2k, no text, no writing"
            })
    
    tags_fallback = "relatos de terror, leyendas urbanas, Mexico, misterio, suspenso, terror mexicano, historias de miedo, casos paranormales, la llorona, el charro negro, nahuales, casas embrujadas, centro historico, calle Madero, testimonios reales, creepypasta, cuentos de terror, mitos mexicanos, apariciones, espectros, miedo, noche, terror en vivo, podcast de terror, leyendas reales"
    
    return {
        "titulo": "El Terror Nocturno de la Calle Madero | Leyenda Real",
        "descripcion": f"Una terrorífica leyenda urbana mexicana contada en primera persona. ¿Has sentido el aliento de lo desconocido en la oscuridad?\n\nSíguenos en nuestra página oficial de Facebook: {FACEBOOK_LINK}\n\nSuscríbete al canal para más historias y testimonios de terror.\n\n#leyendasurbanas #Terror #Misterio #mexico #HistoriasDeMiedo",
        "tags": tags_fallback,
        "miniatura_prompt": "Close-up portrait of a middle-aged Mexican man with a terrified expression, looking off-screen, dark alley background with orange and red neon reflections, cinematic lighting, shallow depth of field, hyperrealistic, 2k, no text, no words",
        "segmentos": segmentos[:24]
    }

# ================================================================
# GENERAR GUION + SEO CON DEEPSEEK (24 segmentos, voz natural)
# ================================================================
def generar_guion():
    prompt = f"""Eres un EXPERTO EN SEO DE YOUTUBE Y COPYWRITING para canales de terror, leyendas urbanas y misterio.
También eres un LOCUTOR PROFESIONAL DE PODCASTS DE TERROR.

Tu tarea es escribir una historia de terror en primera persona ambientada en México (aproximadamente 10000 caracteres).
Divide la historia en 24 segmentos de ~450 caracteres cada uno.

REGLAS STRICTAS DE ESTRUCTURA Y SEO:
1. TÍTULO: OBLIGATORIAMENTE debe tener ENTRE 45 Y 60 CARACTERES exactos. Debe ser impactante, dar miedo y llamar al clic.
2. DESCRIPCIÓN: Debe ser una sinopsis envolvente de 3 a 4 oraciones. DEBE INCLUIR OBLIGATORIAMENTE la frase: "Síguenos en Facebook: {FACEBOOK_LINK}" y al final 5 hashtags relevantes (#leyendasurbanas #Terror #Misterio #mexico #HistoriasDeMiedo).
3. TAGS: Genera entre 25 y 30 palabras clave separadas por comas. El texto total de los tags DEBE SUPERAR LOS 400 CARACTERES.

REGLAS OBLIGATORIAS DE REDACCIÓN PARA VOZ (Para evitar que suene robótica):
1. RITMO Y DINAMISMO: Usa oraciones cortas e intercala preguntas y exclamaciones de forma fluida.
2. PAUSAS NATURALES: Usa puntos y comas de forma orgánica. Usa puntos suspensivos (...) solo en revelaciones o giros dramáticos.
3. ESTILO ORAL: Usa lenguaje narrativo directo y expresivo ("De pronto...", "Créanme...", "Sentí cómo se me helaba la sangre...").
4. SIN TEXTO TÉCNICO: Jamás incluyas paréntesis con acotaciones teatrales como (suspirando) o (susurrando).

REGLAS CRÍTICAS DE IMAGEN (imagen_prompt):
1. Escribe TODOS los "imagen_prompt" ESTRICTAMENTE EN INGLÉS.
2. Prompts fotográficos cinematográficos: "35mm film photo, Mexico City, night, fog, realistic, no gore, no zombies, 2k".
3. ABSOLUTAMENTE NINGÚN TEXTO EN LA IMAGEN: Agrega siempre "no text, no letters, no words, no signs, no typography" para evitar errores tipográficos.

REGLA DE TEXTO (texto):
1. Solamente pon lo que el narrador habla. NUNCA incluyas la palabra "prompt" ni instrucciones.
2. Usa comillas simples 'así' para diálogos.

Genera la respuesta estrictamente en formato JSON válido:
{{
  "titulo": "Título de terror impactante entre 45 y 60 caracteres",
  "descripcion": "Sinopsis atrayente... Síguenos en Facebook: {FACEBOOK_LINK} #leyendasurbanas #Terror #Misterio #mexico #HistoriasDeMiedo",
  "tags": "tag1, tag2, tag3, ..., tag30 (extensión total > 400 caracteres)",
  "miniatura_prompt": "Close-up portrait of a Mexican man with a terrified expression, dark alley, neon reflections, cinematic lighting, 2k, no text, no words",
  "segmentos": [
    {{
      "texto": "Texto narrativo que leerá la voz...",
      "imagen_prompt": "Detailed English photographic prompt for this scene, 2k, no text, no letters"
    }}
  ]
}}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.75,
        "max_tokens": 5000,
        "response_format": {"type": "json_object"}
    }
    
    respuesta = ""
    for intento in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=150)
            r.raise_for_status()
            respuesta = r.json()["choices"][0]["message"]["content"].strip()
            print(f"📄 Respuesta obtenida ({len(respuesta)} caracteres)")
            
            json_str = limpiar_respuesta_json(respuesta)
            data = json.loads(json_str)
            
            if "segmentos" not in data or len(data["segmentos"]) == 0:
                raise ValueError("La respuesta no contiene segmentos")
            
            # Validación y ajuste del título (Rango 45 - 60 caracteres)
            titulo = data.get("titulo", "")
            if len(titulo) < 45 or len(titulo) > 60:
                print(f"⚠️ Ajustando longitud del título original ({len(titulo)} caracteres)...")
                if len(titulo) > 60:
                    data["titulo"] = titulo[:57] + "..."
                elif len(titulo) < 45:
                    data["titulo"] = f"{titulo} | Relato de Terror Real"[:60]
            
            # Asegurar link de Facebook en la descripción
            if FACEBOOK_LINK not in data.get("descripcion", ""):
                data["descripcion"] = f"{data.get('descripcion', '')}\n\nSíguenos en Facebook: {FACEBOOK_LINK}"

            for seg in data["segmentos"]:
                if "imagen_prompt" in seg:
                    seg["imagen_prompt"] = limpiar_prompt(seg["imagen_prompt"])
                if "texto" in seg:
                    seg["texto"] = seg["texto"].replace('"', "'")
                    seg["texto"] = re.sub(r'imagen_prompt.*', '', seg["texto"], flags=re.IGNORECASE)
            
            return data
        except Exception as e:
            print(f"❌ Intento {intento+1}/3 falló: {e}")
            time.sleep(3)
    
    print("❌ Todos los intentos fallaron. Usando fallback.")
    return generar_fallback(respuesta)

# ================================================================
# GENERAR IMAGEN CON AGNES AI (2K, Sin Texto)
# ================================================================
def generar_imagen(prompt, width=2048, height=2048, intentos=3):
    prompt_limpio = limpiar_prompt(prompt)
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "agnes-image-2.1-flash", "prompt": prompt_limpio, "width": width, "height": height, "num_images": 1}
    
    for i in range(intentos):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code == 200:
                return r.json()["data"][0]["url"]
            else:
                print(f"⚠️ Intento {i+1}/{intentos} falló (código {r.status_code})")
                time.sleep(10)
        except Exception as e:
            print(f"⚠️ Intento {i+1}/{intentos} error: {e}")
            time.sleep(10)
    return None

# ================================================================
# GENERAR AUDIO CON AZURE TTS (CandelaNeural, Ritmo Humano Normal)
# ================================================================
def generar_audio(texto, index, intentos=3):
    texto_limpio = re.sub(r'imagen_prompt.*', '', texto, flags=re.IGNORECASE)
    texto_limpio = texto_limpio.replace('"', '&quot;').replace("'", "&apos;")
    
    texto_ssml = texto_limpio.replace('...', '<break time="500ms"/>')
    texto_ssml = texto_ssml.replace('. ', '. <break time="250ms"/>')
    texto_ssml = texto_ssml.replace(', ', ', <break time="100ms"/>')
    texto_ssml = texto_ssml.replace('! ', '! <break time="300ms"/>')
    texto_ssml = texto_ssml.replace('? ', '? <break time="300ms"/>')
    
    url = f"https://{AZURE_TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TTS_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3"
    }
    
    ssml = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-MX">
        <voice name="es-MX-CandelaNeural">
            <prosody rate="0%" pitch="-1%">
                {texto_ssml}
            </prosody>
        </voice>
    </speak>
    """
    for i in range(intentos):
        try:
            r = requests.post(url, headers=headers, data=ssml.encode('utf-8'), timeout=60)
            if r.status_code == 200:
                filename = f"audio_{index}.mp3"
                with open(filename, "wb") as f:
                    f.write(r.content)
                return filename
            else:
                print(f"⚠️ Audio {index} intento {i+1}/{intentos} falló (código {r.status_code})")
                time.sleep(10)
        except Exception as e:
            print(f"⚠️ Audio {index} error: {e}")
            time.sleep(10)
    return None

# ================================================================
# MONTAR VIDEO CON MOVIEPY (CON FONDO ALEATORIO CON REINTENTOS)
# ================================================================
def montar_video(elementos, salida="video_final.mp4"):
    if not elementos:
        raise ValueError("No hay elementos para montar el video")
    
    clips_video = []
    clips_audio = []
    
    for i, elem in enumerate(elementos):
        img_url = elem["imagen_url"]
        audio_path = elem["audio_path"]
        
        try:
            audio_clip = AudioFileClip(audio_path)
            duracion = audio_clip.duration
            
            r = requests.get(img_url, timeout=30)
            r.raise_for_status()
            img_path = f"temp_img_{i}.jpg"
            with open(img_path, "wb") as f:
                f.write(r.content)
            
            with Image.open(img_path) as img:
                img_resized = img.resize((1920, 1080), Image.Resampling.LANCZOS)
                img_resized.save(img_path)
            
            video_clip = ImageClip(img_path).set_duration(duracion)
            
            clips_video.append(video_clip)
            clips_audio.append(audio_clip)
        except Exception as e:
            print(f"⚠️ Error procesando segmento {i}: {e}")
            continue

    if not clips_video or not clips_audio:
        raise ValueError("No se pudieron procesar los clips de video o audio")

    # Crear video y audio principal
    video = concatenate_videoclips(clips_video, method="compose")
    audio_narracion = concatenate_audioclips(clips_audio)
    duracion_total = audio_narracion.duration

    # 🎵 Agregar audio de fondo (con reintentos)
    fondo_path = FONDO_AUDIO_FILE
    if fondo_path and not os.path.exists(fondo_path):
        print(f"⚠️ El archivo seleccionado ({fondo_path}) no existe. Buscando otro...")
        fondo_path = seleccionar_fondo_disponible()
    
    if fondo_path and os.path.exists(fondo_path):
        try:
            fondo_clip = AudioFileClip(fondo_path)
            if fondo_clip.duration < duracion_total:
                veces = int(duracion_total / fondo_clip.duration) + 1
                fondo_clip = fondo_clip * veces
            fondo_clip = fondo_clip.subclip(0, duracion_total)
            fondo_clip = fondo_clip.volumex(0.15)
            audio_final = CompositeAudioClip([audio_narracion, fondo_clip])
            print(f"🎵 Audio de fondo mezclado: {fondo_path} (volumen 15%)")
        except Exception as e:
            print(f"⚠️ Error procesando fondo: {e}. Usando solo narración.")
            audio_final = audio_narracion
    else:
        print("⚠️ No se encontró ningún archivo de fondo. Usando solo narración.")
        audio_final = audio_narracion

    video = video.set_audio(audio_final)
    video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")
    print(f"✅ Video creado correctamente: {salida}")
    return salida

# ================================================================
# SUBIR A YOUTUBE
# ================================================================
def subir_a_youtube(video_path, miniatura_path, titulo, descripcion, etiquetas):
    creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
    youtube = build("youtube", "v3", credentials=creds)
    
    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]
    
    body = {
        "snippet": {
            "title": titulo[:100],
            "description": descripcion[:5000],
            "tags": etiquetas[:30],
            "categoryId": "24"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True
        }
    }
    
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    response = request.execute()
    
    video_id = response['id']
    print(f"✅ Video subido a YouTube: https://youtu.be/{video_id}")
    
    if miniatura_path and os.path.exists(miniatura_path):
        try:
            media_thumb = MediaFileUpload(miniatura_path, chunksize=-1, resumable=True)
            thumb_request = youtube.thumbnails().set(videoId=video_id, media_body=media_thumb)
            thumb_request.execute()
            print("✅ Miniatura subida correctamente")
        except Exception as e:
            print(f"⚠️ No se pudo subir la miniatura: {e}")
    
    return response

# ================================================================
# MAIN
# ================================================================
def main():
    print("🎬 Iniciando Bot de YouTube (2K, 24 segmentos, Voz Dinámica, SEO Optimizado)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if FONDO_AUDIO_FILE:
        print(f"🎵 Archivo de fondo seleccionado: {FONDO_AUDIO_FILE}")
    else:
        print("⚠️ No hay archivo de fondo disponible.")
    
    guion_data = generar_guion()
    if not guion_data:
        print("❌ No se pudo generar el guion. Abortando.")
        return
    
    titulo_video = guion_data.get("titulo", "El Terror Nocturno de la Calle Madero | Leyenda Real")
    descripcion_video = guion_data.get("descripcion", f"Relato de terror basado en leyendas urbanas de México.\n\nSíguenos en Facebook: {FACEBOOK_LINK}")
    tags_video = guion_data.get("tags", "relatos de terror, leyendas urbanas, Mexico, misterio, suspenso")
    miniatura_prompt = guion_data.get("miniatura_prompt", "Close-up portrait of a Mexican man with terrified expression, dark alley, orange and red neon, cinematic, 2k, no text")
    segmentos = guion_data.get("segmentos", [])
    
    if not segmentos:
        print("❌ No se generaron segmentos. Abortando.")
        return
    
    print(f"✅ Guion generado con {len(segmentos)} segmentos")
    print(f"📌 Título ({len(titulo_video)} caracteres): {titulo_video}")
    print(f"📌 Tags ({len(str(tags_video))} caracteres): {str(tags_video)[:100]}...")
    print(f"📌 Descripción: {descripcion_video[:150]}...")
    
    elementos_validos = []
    imagen_ultimo_recurso = None
    
    print("🎨 y 🎙️ Generando imágenes y audios para cada segmento...")
    
    for i, seg in enumerate(segmentos):
        print(f"\n--- Procesando segmento {i+1}/{len(segmentos)} ---")
        
        if i > 0:
            print("⏳ Esperando 8 segundos antes de la siguiente imagen...")
            time.sleep(8)
        
        url_img = generar_imagen(seg["imagen_prompt"], width=2048, height=2048)
        if url_img:
            imagen_ultimo_recurso = url_img
            print(f"✅ Imagen {i+1} generada (2K)")
        elif imagen_ultimo_recurso:
            print(f"⚠️ Reutilizando imagen previa para segmento {i+1}")
            url_img = imagen_ultimo_recurso
        else:
            print(f"❌ Sin imagen disponible para segmento {i+1}, se salta.")
            continue
        
        print("⏳ Esperando 5 segundos antes del audio...")
        time.sleep(5)
        
        audio_file = generar_audio(seg["texto"], i)
        if not audio_file:
            print(f"❌ Falló el audio {i+1}, se salta el segmento.")
            continue
        
        elementos_validos.append({
            "imagen_url": url_img,
            "audio_path": audio_file
        })
        print(f"✅ Segmento {i+1} completado")
    
    print("\n🖼️ Generando miniatura...")
    time.sleep(5)
    miniatura_path = "miniatura.jpg"
    
    miniatura_prompt_refinado = f"{miniatura_prompt} High contrast, orange and red tones, dark background, ultra detailed, 2k, no text, no letters"
    
    miniatura_url = generar_imagen(miniatura_prompt_refinado, width=1280, height=720)
    
    if miniatura_url:
        try:
            r = requests.get(miniatura_url, timeout=30)
            r.raise_for_status()
            with open(miniatura_path, "wb") as f:
                f.write(r.content)
            print("✅ Miniatura generada con colores llamativos")
        except Exception as e:
            print(f"⚠️ Error al guardar miniatura: {e}")
            miniatura_path = None
    else:
        miniatura_path = None

    if not elementos_validos:
        print("❌ No hay elementos válidos para construir el video. Abortando.")
        return
    
    print("\n🎬 Montando video con MoviePy...")
    try:
        video_path = montar_video(elementos_validos, "video_final.mp4")
    except Exception as e:
        print(f"❌ Error montando video: {e}")
        return
    
    print("⬆️ Subiendo video a YouTube...")
    try:
        subir_a_youtube(video_path, miniatura_path, titulo_video, descripcion_video, tags_video)
    except Exception as e:
        print(f"❌ Error subiendo a YouTube: {e}")
        return
    
    print("🎉 Proceso completado exitosamente")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
