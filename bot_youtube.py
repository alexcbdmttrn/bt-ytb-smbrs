import os
import json
import re
import requests
import time
from datetime import datetime
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
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
YOUTUBE_CLIENT_SECRET = json.loads(os.getenv("YOUTUBE_CLIENT_SECRET"))

# ================================================================
# GENERAR GUION CON DEEPSEEK (con limpieza de JSON)
# ================================================================
def limpiar_respuesta_json(respuesta):
    """Limpia la respuesta de DeepSeek para extraer un JSON válido."""
    # Eliminar bloques de código markdown
    respuesta = re.sub(r'```json\s*', '', respuesta)
    respuesta = re.sub(r'```\s*', '', respuesta)
    
    # Buscar la primera llave de apertura y la última de cierre
    inicio = respuesta.find('{')
    fin = respuesta.rfind('}')
    if inicio != -1 and fin != -1:
        return respuesta[inicio:fin+1]
    return respuesta

def generar_guion():
    prompt = """Eres un escritor de terror especializado en leyendas urbanas de México.
Escribe una historia de terror de aproximadamente 9000 caracteres (9 minutos de narración).
Debe ser un relato en primera persona, con testimonios realistas.
Divide la historia en 18 segmentos de ~500 caracteres cada uno (cada segmento es una escena).
Para cada segmento, incluye una breve descripción de la imagen que lo acompañará.

Además, genera:
- Un TÍTULO IMPACTANTE para el video (máximo 60 caracteres) que capture la esencia de la historia.
- Una DESCRIPCIÓN atractiva para el video (máximo 200 caracteres) que invite a ver el video y termine con este llamado: "Síguenos también en Facebook: https://www.facebook.com/profile.php?id=61593237382982"
- 8 PALABRAS CLAVE (tags) relevantes para el video, separadas por comas.
- UN PROMPT PARA LA MINIATURA: descripción detallada para generar una imagen de 1280x720 píxeles que sea impactante, con colores contrastantes (negro, rojo, naranja, blanco), que represente la escena más aterradora de la historia. La miniatura debe tener espacio para texto (título del video) en la parte inferior o superior. Debe ser visualmente llamativa y dar miedo.

Formato de salida: JSON con esta estructura:
{
  "titulo": "El título impactante del video",
  "descripcion": "Descripción atractiva del video... Síguenos también en Facebook: https://www.facebook.com/profile.php?id=61593237382982",
  "tags": "tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8",
  "miniatura_prompt": "Prompt detallado para generar la miniatura",
  "segmentos": [
    {"texto": "texto del segmento 1", "imagen_prompt": "descripción de la imagen 1"},
    {"texto": "texto del segmento 2", "imagen_prompt": "descripción de la imagen 2"},
    ...
  ]
}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.85, "max_tokens": 2300}
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        respuesta = r.json()["choices"][0]["message"]["content"].strip()
        
        # Limpiar y extraer JSON
        json_str = limpiar_respuesta_json(respuesta)
        data = json.loads(json_str)
        
        # Validar estructura básica
        if "segmentos" not in data or len(data["segmentos"]) == 0:
            raise ValueError("La respuesta no contiene segmentos")
        
        return data
    except json.JSONDecodeError as e:
        print(f"❌ Error decodificando JSON: {e}")
        print(f"📄 Respuesta cruda (primeros 500 chars): {respuesta[:500]}")
        # Fallback: crear estructura mínima desde el texto
        return generar_fallback(respuesta)
    except Exception as e:
        print(f"❌ Error en DeepSeek: {e}")
        return None

def generar_fallback(respuesta):
    """Genera una estructura básica cuando el JSON falla."""
    print("⚠️ Usando fallback: generando estructura básica desde el texto.")
    # Dividir el texto en segmentos aproximados (cada ~500 caracteres)
    texto_limpio = re.sub(r'\n+', ' ', respuesta)
    segmentos = []
    chars_por_segmento = 500
    for i in range(0, len(texto_limpio), chars_por_segmento):
        segmento = texto_limpio[i:i+chars_por_segmento]
        if len(segmento.strip()) > 50:
            segmentos.append({
                "texto": segmento,
                "imagen_prompt": f"Escena de terror, {segmento[:50]}..., estilo cinematográfico"
            })
    
    return {
        "titulo": "Relato de terror | Sombras de Medianoche",
        "descripcion": "Relato de terror basado en leyendas urbanas de México. Síguenos también en Facebook: https://www.facebook.com/profile.php?id=61593237382982",
        "tags": "relatos de terror, leyendas urbanas, México, terror, misterio, miedo, paranormal, historias",
        "miniatura_prompt": "Escena de terror, paisaje oscuro, colores negro y rojo, impactante, estilo cinematográfico",
        "segmentos": segmentos[:18]  # máximo 18 segmentos
    }

# ================================================================
# GENERAR IMAGEN CON AGNES AI (con reintentos)
# ================================================================
def generar_imagen(prompt, width=1024, height=1024, intentos=3):
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "agnes-image-2.1-flash", "prompt": prompt, "width": width, "height": height, "num_images": 1}
    
    for i in range(intentos):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            if r.status_code == 200:
                return r.json()["data"][0]["url"]
            else:
                print(f"⚠️ Intento {i+1}/{intentos} falló (código {r.status_code})")
                time.sleep(5)
        except Exception as e:
            print(f"⚠️ Intento {i+1}/{intentos} error: {e}")
            time.sleep(5)
    return None

# ================================================================
# GENERAR AUDIO CON AZURE TTS (con reintentos)
# ================================================================
def generar_audio(texto, index, intentos=3):
    url = f"https://{AZURE_TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TTS_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
    }
    # Limpiar texto para SSML (escapar caracteres especiales)
    texto_limpio = texto.replace('"', '&quot;').replace("'", "&apos;")
    ssml = f"""
    <speak version="1.0" xml:lang="es-MX">
        <voice name="es-MX-DaliaNeural">
            {texto_limpio}
        </voice>
    </speak>
    """
    for i in range(intentos):
        try:
            r = requests.post(url, headers=headers, data=ssml, timeout=60)
            if r.status_code == 200:
                filename = f"audio_{index}.mp3"
                with open(filename, "wb") as f:
                    f.write(r.content)
                return filename
            else:
                print(f"⚠️ Audio {index} intento {i+1}/{intentos} falló (código {r.status_code})")
                time.sleep(5)
        except Exception as e:
            print(f"⚠️ Audio {index} error: {e}")
            time.sleep(5)
    return None

# ================================================================
# MONTAR VIDEO CON MOVIEPY
# ================================================================
def montar_video(imagenes, audios, salida="video_final.mp4"):
    clips_imagen = []
    duracion_total = 0.0
    
    for audio_file in audios:
        clip = AudioFileClip(audio_file)
        duracion_total += clip.duration
    
    duracion_por_imagen = duracion_total / len(imagenes) if imagenes else 10
    
    for i, img_url in enumerate(imagenes):
        r = requests.get(img_url)
        with open(f"temp_img_{i}.jpg", "wb") as f:
            f.write(r.content)
        clip = ImageClip(f"temp_img_{i}.jpg").set_duration(duracion_por_imagen).resize(width=1920)
        clips_imagen.append(clip)
    
    video = concatenate_videoclips(clips_imagen, method="compose")
    
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.audio.AudioClip import concatenate_audioclips
    audios_clips = [AudioFileClip(a) for a in audios]
    audio_final = concatenate_audioclips(audios_clips)
    
    video = video.set_audio(audio_final)
    video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac", threads=4)
    print(f"✅ Video creado: {salida}")
    return salida

# ================================================================
# SUBIR A YOUTUBE (con miniatura y marcado de IA)
# ================================================================
def subir_a_youtube(video_path, miniatura_path, titulo, descripcion, etiquetas):
    creds = Credentials.from_authorized_user_info(YOUTUBE_CLIENT_SECRET)
    youtube = build("youtube", "v3", credentials=creds)
    
    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",")]
    
    body = {
        "snippet": {
            "title": titulo,
            "description": descripcion,
            "tags": etiquetas,
            "categoryId": "24"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True
        }
    }
    
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    video_id = response['id']
    print(f"✅ Video subido: https://youtu.be/{video_id}")
    
    try:
        media_thumb = MediaFileUpload(miniatura_path, chunksize=-1, resumable=True)
        thumb_request = youtube.thumbnails().set(videoId=video_id, media_body=media_thumb)
        thumb_request.execute()
        print(f"✅ Miniatura subida correctamente")
    except Exception as e:
        print(f"⚠️ No se pudo subir la miniatura: {e}")
    
    return response

# ================================================================
# MAIN
# ================================================================
def main():
    print("🎬 Iniciando Bot de YouTube (con miniatura y IA)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Generar guion
    print("📝 Generando guion y metadatos con DeepSeek...")
    guion_data = generar_guion()
    if not guion_data:
        print("❌ No se pudo generar el guion. Abortando.")
        return
    
    titulo_video = guion_data.get("titulo", "Relato de terror | Sombras de Medianoche")
    descripcion_video = guion_data.get("descripcion", "Relato de terror basado en leyendas urbanas de México. Síguenos también en Facebook: https://www.facebook.com/profile.php?id=61593237382982")
    tags_video = guion_data.get("tags", "relatos de terror, leyendas urbanas, México, terror")
    miniatura_prompt = guion_data.get("miniatura_prompt", "Escena de terror, paisaje oscuro, colores negro y rojo")
    segmentos = guion_data.get("segmentos", [])
    
    if len(segmentos) == 0:
        print("❌ No se generaron segmentos. Abortando.")
        return
    
    print(f"✅ Guion generado con {len(segmentos)} segmentos")
    print(f"📌 Título: {titulo_video}")
    
    # 2. Generar imágenes
    print("🎨 Generando imágenes para el video...")
    imagenes = []
    for i, seg in enumerate(segmentos):
        print(f"   Imagen {i+1}/{len(segmentos)}...")
        url = generar_imagen(seg["imagen_prompt"], width=1024, height=1024)
        if url:
            imagenes.append(url)
            print(f"      ✅ Imagen {i+1} generada")
        else:
            print(f"      ❌ Falló imagen {i+1}")
        time.sleep(8)
    
    # 3. Generar miniatura
    print("🖼️ Generando miniatura...")
    miniatura_url = generar_imagen(miniatura_prompt, width=1280, height=720)
    if miniatura_url:
        r = requests.get(miniatura_url)
        with open("miniatura.jpg", "wb") as f:
            f.write(r.content)
        print(f"✅ Miniatura generada")
    else:
        print("⚠️ No se pudo generar miniatura, usando primera imagen del video")
        if imagenes:
            r = requests.get(imagenes[0])
            with open("miniatura.jpg", "wb") as f:
                f.write(r.content)
    time.sleep(8)
    
    # 4. Generar audios
    print("🎙️ Generando audios con Azure TTS...")
    audios = []
    for i, seg in enumerate(segmentos):
        print(f"   Audio {i+1}/{len(segmentos)}...")
        audio = generar_audio(seg["texto"], i)
        if audio:
            audios.append(audio)
            print(f"      ✅ Audio {i+1} generado")
        else:
            print(f"      ❌ Falló audio {i+1}")
        time.sleep(8)
    
    if len(imagenes) == 0 or len(audios) == 0:
        print("❌ No se generaron suficientes imágenes o audios. Abortando.")
        return
    
    # 5. Montar video
    print("🎬 Montando video con MoviePy...")
    video_path = montar_video(imagenes, audios, "video_final.mp4")
    
    # 6. Subir a YouTube
    print("⬆️ Subiendo video y miniatura a YouTube...")
    subir_a_youtube(video_path, "miniatura.jpg", titulo_video, descripcion_video, tags_video)
    
    print("🎉 Proceso completado")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
