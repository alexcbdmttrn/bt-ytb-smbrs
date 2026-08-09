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
# LIMPIAR PROMPTS PARA EVITAR ERRORES 400 EN AGNES
# ================================================================
def limpiar_prompt(prompt):
    """Elimina caracteres problemáticos para la API de Agnes."""
    if not prompt:
        return "Escena de terror, paisaje oscuro"
    prompt = re.sub(r'\n+', ' ', prompt)           # Saltos de línea a espacios
    prompt = re.sub(r'"', "'", prompt)             # Comillas dobles a simples
    prompt = re.sub(r'[^\x00-\x7F]+', '', prompt)  # Caracteres no ASCII
    prompt = re.sub(r'\s+', ' ', prompt)           # Múltiples espacios a uno
    return prompt.strip()[:500]  # Limitar longitud

# ================================================================
# LIMPIAR RESPUESTA JSON DE DEEPSEEK
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
        json_str = respuesta[inicio:fin+1]
        # Reparar comas faltantes entre objetos en arrays
        json_str = re.sub(r'}\s*{', '},{', json_str)
        # Eliminar comas finales en arrays y objetos
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*\]', ']', json_str)
        # Escapar comillas internas en valores de texto
        json_str = re.sub(r'(?<!")(\w+)(?=":)', r'"\1"', json_str)
        return json_str
    return respuesta

# ================================================================
# GENERAR FALLBACK CUANDO EL JSON FALLA
# ================================================================
def generar_fallback(respuesta):
    """Genera una estructura básica cuando el JSON falla."""
    print("⚠️ Usando fallback: generando estructura básica desde el texto.")
    
    # Intentar extraer título
    lineas = respuesta.split('\n')
    titulo = "Relato de terror | Sombras de Medianoche"
    for linea in lineas[:5]:
        linea_limpia = linea.strip()
        if len(linea_limpia) > 10 and not linea_limpia.startswith('{'):
            if 'título' in linea_limpia.lower() or 'titulo' in linea_limpia.lower():
                titulo = linea_limpia.replace('título:', '').replace('titulo:', '').strip()
                break
            elif len(linea_limpia) > 20:
                titulo = linea_limpia[:60]
                break
    
    # Limpiar texto
    texto_limpio = re.sub(r'\n+', ' ', respuesta)
    texto_limpio = re.sub(r'[{}"]', '', texto_limpio)
    
    # Dividir en segmentos
    segmentos = []
    chars_por_segmento = 500
    for i in range(0, len(texto_limpio), chars_por_segmento):
        segmento = texto_limpio[i:i+chars_por_segmento]
        if len(segmento.strip()) > 50:
            segmentos.append({
                "texto": segmento,
                "imagen_prompt": f"Escena de terror, {segmento[:50]}..., estilo cinematográfico"
            })
    
    if len(segmentos) == 0:
        segmentos.append({
            "texto": respuesta[:500] if respuesta else "Historia de terror no disponible",
            "imagen_prompt": "Escena de terror, paisaje oscuro"
        })
    
    return {
        "titulo": titulo,
        "descripcion": "Relato de terror basado en leyendas urbanas de México. Síguenos también en Facebook: https://www.facebook.com/profile.php?id=61593237382982",
        "tags": "relatos de terror, leyendas urbanas, México, terror, misterio, miedo, paranormal, historias",
        "miniatura_prompt": "Escena de terror, paisaje oscuro, colores negro y rojo, impactante, estilo cinematográfico",
        "segmentos": segmentos[:18]
    }

# ================================================================
# GENERAR GUION CON DEEPSEEK
# ================================================================
def generar_guion():
    prompt = """Eres un escritor de terror especializado en leyendas urbanas de México.
Escribe una historia de terror de aproximadamente 9000 caracteres (9 minutos de narración).
Debe ser un relato en primera persona, con testimonios realistas.
Divide la historia en 18 segmentos de ~500 caracteres cada uno (cada segmento es una escena).
Para cada segmento, incluye una breve descripción de la imagen que lo acompañará.

Además, genera:
- Un TÍTULO IMPACTANTE para el video (máximo 60 caracteres).
- Una DESCRIPCIÓN atractiva para el video (máximo 200 caracteres) que termine con: "Síguenos también en Facebook: https://www.facebook.com/profile.php?id=61593237382982"
- 8 PALABRAS CLAVE separadas por comas.
- UN PROMPT PARA LA MINIATURA (máximo 200 caracteres) para generar una imagen impactante de 1280x720.

Formato de salida: SOLO JSON válido, sin texto adicional, sin markdown. Usa comillas dobles para todas las cadenas y escapa las comillas internas con \".

{
  "titulo": "El título",
  "descripcion": "La descripción... Síguenos también en Facebook: https://www.facebook.com/profile.php?id=61593237382982",
  "tags": "tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8",
  "miniatura_prompt": "Prompt para la miniatura",
  "segmentos": [
    {"texto": "texto del segmento 1", "imagen_prompt": "descripción de la imagen 1"},
    {"texto": "texto del segmento 2", "imagen_prompt": "descripción de la imagen 2"}
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
        print(f"📄 Respuesta cruda (primeros 300 chars): {respuesta[:300]}...")
        
        json_str = limpiar_respuesta_json(respuesta)
        data = json.loads(json_str)
        
        if "segmentos" not in data or len(data["segmentos"]) == 0:
            raise ValueError("La respuesta no contiene segmentos")
        
        # Limpiar prompts de imagen para evitar errores 400
        for seg in data["segmentos"]:
            if "imagen_prompt" in seg:
                seg["imagen_prompt"] = limpiar_prompt(seg["imagen_prompt"])
            if "texto" in seg:
                seg["texto"] = limpiar_prompt(seg["texto"])
        
        return data
    except json.JSONDecodeError as e:
        print(f"❌ Error decodificando JSON: {e}")
        return generar_fallback(respuesta if 'respuesta' in locals() else "")
    except Exception as e:
        print(f"❌ Error en DeepSeek: {e}")
        return generar_fallback(respuesta if 'respuesta' in locals() else "")

# ================================================================
# GENERAR IMAGEN CON AGNES AI (con reintentos)
# ================================================================
def generar_imagen(prompt, width=1024, height=1024, intentos=3):
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
                time.sleep(5)
        except Exception as e:
            print(f"⚠️ Intento {i+1}/{intentos} error: {e}")
            time.sleep(5)
    return None

# ================================================================
# GENERAR AUDIO CON AZURE TTS (con reintentos)
# ================================================================
def generar_audio(texto, index, intentos=3):
    texto_limpio = texto.replace('"', '&quot;').replace("'", "&apos;")
    url = f"https://{AZURE_TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TTS_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
    }
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
    if len(imagenes) == 0 or len(audios) == 0:
        raise ValueError("No hay suficientes imágenes o audios")
    
    clips_imagen = []
    duracion_total = 0.0
    
    # Cargar duración de audios
    for audio_file in audios:
        clip = AudioFileClip(audio_file)
        duracion_total += clip.duration
    
    duracion_por_imagen = duracion_total / len(imagenes)
    
    for i, img_url in enumerate(imagenes):
        try:
            r = requests.get(img_url, timeout=30)
            r.raise_for_status()
            with open(f"temp_img_{i}.jpg", "wb") as f:
                f.write(r.content)
            clip = ImageClip(f"temp_img_{i}.jpg").set_duration(duracion_por_imagen).resize(width=1920)
            clips_imagen.append(clip)
        except Exception as e:
            print(f"⚠️ Error descargando imagen {i}: {e}")
            continue
    
    if len(clips_imagen) == 0:
        raise ValueError("No se pudo descargar ninguna imagen")
    
    video = concatenate_videoclips(clips_imagen, method="compose")
    
    # Concatenar audios
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
            "title": titulo[:100] if len(titulo) > 100 else titulo,
            "description": descripcion[:5000] if len(descripcion) > 5000 else descripcion,
            "tags": etiquetas[:15],
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
    tags_video = guion_data.get("tags", "relatos de terror, leyendas urbanas, México, terror, misterio, miedo, paranormal, historias")
    miniatura_prompt = guion_data.get("miniatura_prompt", "Escena de terror, paisaje oscuro, colores negro y rojo, impactante, estilo cinematográfico")
    segmentos = guion_data.get("segmentos", [])
    
    if len(segmentos) == 0:
        print("❌ No se generaron segmentos. Abortando.")
        return
    
    print(f"✅ Guion generado con {len(segmentos)} segmentos")
    print(f"📌 Título: {titulo_video}")
    print(f"📌 Tags: {tags_video}")
    
    # 2. Generar imágenes (18 segmentos, pausa de 8 segundos entre cada una)
    print("🎨 Generando imágenes para el video...")
    imagenes = []
    for i, seg in enumerate(segmentos):
        print(f"   Imagen {i+1}/{len(segmentos)}...")
        url = generar_imagen(seg["imagen_prompt"], width=1024, height=1024)
        if url:
            imagenes.append(url)
            print(f"      ✅ Imagen {i+1} generada")
        else:
            print(f"      ❌ Falló imagen {i+1} después de 3 intentos")
        time.sleep(8)
    
    # 3. Generar miniatura (1280x720)
    print("🖼️ Generando miniatura...")
    miniatura_url = generar_imagen(miniatura_prompt, width=1280, height=720)
    if miniatura_url:
        try:
            r = requests.get(miniatura_url, timeout=30)
            r.raise_for_status()
            with open("miniatura.jpg", "wb") as f:
                f.write(r.content)
            print(f"✅ Miniatura generada")
        except Exception as e:
            print(f"⚠️ Error descargando miniatura: {e}")
            if imagenes:
                r = requests.get(imagenes[0], timeout=30)
                with open("miniatura.jpg", "wb") as f:
                    f.write(r.content)
                print("⚠️ Usando primera imagen del video como miniatura")
    else:
        print("⚠️ No se pudo generar miniatura, usando primera imagen del video")
        if imagenes:
            try:
                r = requests.get(imagenes[0], timeout=30)
                with open("miniatura.jpg", "wb") as f:
                    f.write(r.content)
            except Exception as e:
                print(f"⚠️ Error descargando imagen de respaldo: {e}")
    time.sleep(8)
    
    # 4. Generar audios con Azure TTS (pausa de 8 segundos entre cada uno)
    print("🎙️ Generando audios con Azure TTS...")
    audios = []
    for i, seg in enumerate(segmentos):
        print(f"   Audio {i+1}/{len(segmentos)}...")
        audio = generar_audio(seg["texto"], i)
        if audio:
            audios.append(audio)
            print(f"      ✅ Audio {i+1} generado")
        else:
            print(f"      ❌ Falló audio {i+1} después de 3 intentos")
        time.sleep(8)
    
    if len(imagenes) == 0 or len(audios) == 0:
        print("❌ No se generaron suficientes imágenes o audios. Abortando.")
        return
    
    # 5. Montar video
    print("🎬 Montando video con MoviePy...")
    try:
        video_path = montar_video(imagenes, audios, "video_final.mp4")
    except Exception as e:
        print(f"❌ Error montando video: {e}")
        return
    
    # 6. Subir a YouTube
    print("⬆️ Subiendo video y miniatura a YouTube...")
    try:
        subir_a_youtube(video_path, "miniatura.jpg", titulo_video, descripcion_video, tags_video)
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
