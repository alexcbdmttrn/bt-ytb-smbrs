import os
import json
import requests
import random
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
# GENERAR GUION CON DEEPSEEK (historia + título + descripción + tags)
# ================================================================
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

Formato de salida: JSON con esta estructura:
{
  "titulo": "El título impactante del video",
  "descripcion": "Descripción atractiva del video... Síguenos también en Facebook: https://www.facebook.com/profile.php?id=61593237382982",
  "tags": "tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8",
  "segmentos": [
    {"texto": "texto del segmento 1", "imagen_prompt": "descripción de la imagen 1"},
    {"texto": "texto del segmento 2", "imagen_prompt": "descripción de la imagen 2"},
    ...
  ]
}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.85, "max_tokens": 2200}
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        respuesta = r.json()["choices"][0]["message"]["content"].strip()
        # Limpiar la respuesta si viene con markdown
        if respuesta.startswith("```json"):
            respuesta = respuesta.replace("```json", "").replace("```", "").strip()
        return json.loads(respuesta)
    except Exception as e:
        print(f"❌ Error en DeepSeek: {e}")
        return None

# ================================================================
# GENERAR IMAGEN CON AGNES AI (con reintentos)
# ================================================================
def generar_imagen(prompt, intentos=3):
    url = "https://apihub.agnes-ai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {AGNES_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "agnes-image-2.1-flash", "prompt": prompt, "width": 1024, "height": 1024, "num_images": 1}
    
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
    ssml = f"""
    <speak version="1.0" xml:lang="es-MX">
        <voice name="es-MX-DaliaNeural">
            {texto}
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
    
    # Calcular duración total de todos los audios
    for audio_file in audios:
        clip = AudioFileClip(audio_file)
        duracion_total += clip.duration
    
    # Calcular duración por imagen (repartir uniformemente)
    duracion_por_imagen = duracion_total / len(imagenes)
    
    for i, img_url in enumerate(imagenes):
        # Descargar imagen desde URL
        r = requests.get(img_url)
        with open(f"temp_img_{i}.jpg", "wb") as f:
            f.write(r.content)
        
        clip = ImageClip(f"temp_img_{i}.jpg").set_duration(duracion_por_imagen).resize(width=1920)
        clips_imagen.append(clip)
    
    # Concatenar imágenes
    video = concatenate_videoclips(clips_imagen, method="compose")
    
    # Concatenar audios
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.audio.AudioClip import concatenate_audioclips
    audios_clips = [AudioFileClip(a) for a in audios]
    audio_final = concatenate_audioclips(audios_clips)
    
    # Unir video y audio
    video = video.set_audio(audio_final)
    
    # Exportar
    video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac", threads=4)
    print(f"✅ Video creado: {salida}")
    return salida

# ================================================================
# SUBIR A YOUTUBE
# ================================================================
def subir_a_youtube(video_path, titulo, descripcion, etiquetas):
    creds = Credentials.from_authorized_user_info(YOUTUBE_CLIENT_SECRET)
    youtube = build("youtube", "v3", credentials=creds)
    
    # Convertir etiquetas a lista si vienen como string separado por comas
    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",")]
    
    body = {
        "snippet": {
            "title": titulo,
            "description": descripcion,
            "tags": etiquetas,
            "categoryId": "24"  # Entretenimiento
        },
        "status": {
            "privacyStatus": "public"  # Cambiar a "unlisted" para pruebas
        }
    }
    
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    print(f"✅ Video subido a YouTube: https://youtu.be/{response['id']}")
    return response

# ================================================================
# MAIN
# ================================================================
def main():
    print("🎬 Iniciando Bot de YouTube")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Generar guion completo (historia + metadatos)
    print("📝 Generando guion y metadatos con DeepSeek...")
    guion_data = generar_guion()
    if not guion_data:
        print("❌ No se pudo generar el guion.")
        return
    
    titulo_video = guion_data.get("titulo", "Relato de terror | Sombras de Medianoche")
    descripcion_video = guion_data.get("descripcion", "Relato de terror basado en leyendas urbanas de México. Síguenos también en Facebook: https://www.facebook.com/profile.php?id=61593237382982")
    tags_video = guion_data.get("tags", "relatos de terror, leyendas urbanas, México, terror, misterio")
    segmentos = guion_data["segmentos"]
    
    print(f"✅ Guion generado con {len(segmentos)} segmentos")
    print(f"📌 Título: {titulo_video}")
    print(f"📌 Tags: {tags_video}")
    
    # 2. Generar imágenes (con pausa de 8 segundos entre cada una)
    print("🎨 Generando imágenes con Agnes AI...")
    imagenes = []
    for i, seg in enumerate(segmentos):
        print(f"   Imagen {i+1}/{len(segmentos)}...")
        url = generar_imagen(seg["imagen_prompt"])
        if url:
            imagenes.append(url)
            print(f"      ✅ Imagen {i+1} generada")
        else:
            print(f"      ❌ Falló imagen {i+1}")
        time.sleep(8)  # Pausa de 8 segundos para no saturar
    
    # 3. Generar audios (con pausa de 8 segundos entre cada uno)
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
        time.sleep(8)  # Pausa de 8 segundos para no saturar
    
    if len(imagenes) == 0 or len(audios) == 0:
        print("❌ No se generaron suficientes imágenes o audios. Abortando.")
        return
    
    # 4. Montar video
    print("🎬 Montando video con MoviePy...")
    video_path = montar_video(imagenes, audios, "video_final.mp4")
    
    # 5. Subir a YouTube
    print("⬆️ Subiendo video a YouTube...")
    subir_a_youtube(video_path, titulo_video, descripcion_video, tags_video)
    
    print("🎉 Proceso completado")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
