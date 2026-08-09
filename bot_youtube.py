import os
import json
import re
import requests
import time
from datetime import datetime
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips
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

# ================================================================
# ID DEL CANAL "Sombras de Medianoche Terror"
# ================================================================
CANAL_ID_SOMBRAS = "UCBH3NWZ4cILxP5N2qsnb3wQ"

# ================================================================
# LIMPIAR PROMPTS PARA EVITAR ERRORES 400 EN AGNES
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        return "Escena de terror, paisaje oscuro"
    prompt = re.sub(r'\n+', ' ', prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r'[^\x00-\x7F]+', '', prompt)
    prompt = re.sub(r'\s+', ' ', prompt)
    return prompt.strip()[:500]

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
        return json_str.strip()
    return respuesta.strip()

# ================================================================
# GENERAR FALLBACK
# ================================================================
def generar_fallback(respuesta):
    print("⚠️ Usando fallback: generando estructura básica desde el texto.")
    
    titulo_match = re.search(r'"titulo"\s*:\s*"([^"]+)"', respuesta)
    if titulo_match:
        titulo = titulo_match.group(1).strip()
    else:
        titulo = "Relato de terror | Sombras de Medianoche"
    
    texto_limpio = re.sub(r'\n+', ' ', respuesta)
    texto_limpio = re.sub(r'[{}"]', '', texto_limpio)
    
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
Escribe una historia de terror en primera persona de aproximadamente 9000 caracteres.
Divide la historia en 18 segmentos de ~500 caracteres cada uno.
REGLA IMPORTANTE: No uses comillas dobles dentro del texto narrativo, usa comillas simples 'así'.

Genera la respuesta estrictamente en este formato JSON sin markdown adicional:
{
  "titulo": "Título de máximo 60 caracteres",
  "descripcion": "Descripción del video... Síguenos también en Facebook: https://www.facebook.com/profile.php?id=61593237382982",
  "tags": "tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8",
  "miniatura_prompt": "Prompt cinematográfico para la miniatura",
  "segmentos": [
    {"texto": "texto del segmento 1", "imagen_prompt": "descripción visual 1 en inglés o español"},
    {"texto": "texto del segmento 2", "imagen_prompt": "descripción visual 2 en inglés o español"}
  ]
}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.85,
        "max_tokens": 2500,
        "response_format": {"type": "json_object"}
    }
    
    respuesta = ""
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        respuesta = r.json()["choices"][0]["message"]["content"].strip()
        print(f"📄 Respuesta cruda (primeros 300 chars): {respuesta[:300]}...")
        
        json_str = limpiar_respuesta_json(respuesta)
        data = json.loads(json_str)
        
        if "segmentos" not in data or len(data["segmentos"]) == 0:
            raise ValueError("La respuesta no contiene segmentos")
        
        for seg in data["segmentos"]:
            if "imagen_prompt" in seg:
                seg["imagen_prompt"] = limpiar_prompt(seg["imagen_prompt"])
            if "texto" in seg:
                seg["texto"] = seg["texto"].replace('"', "'")
        
        return data
    except Exception as e:
        print(f"❌ Error procesando guion con DeepSeek: {e}")
        return generar_fallback(respuesta)

# ================================================================
# GENERAR IMAGEN CON AGNES AI (con pausas largas)
# ================================================================
def generar_imagen(prompt, width=1024, height=1024, intentos=4):
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
# GENERAR AUDIO CON AZURE TTS (con pausas largas)
# ================================================================
def generar_audio(texto, index, intentos=4):
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
                time.sleep(10)
        except Exception as e:
            print(f"⚠️ Audio {index} error: {e}")
            time.sleep(10)
    return None

# ================================================================
# MONTAR VIDEO CON MOVIEPY
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

    video = concatenate_videoclips(clips_video, method="compose")
    audio_final = concatenate_audioclips(clips_audio)
    
    video = video.set_audio(audio_final)
    video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac", threads=4)
    print(f"✅ Video creado correctamente: {salida}")
    return salida

# ================================================================
# SUBIR A YOUTUBE (FORZANDO EL CANAL CORRECTO)
# ================================================================
def subir_a_youtube(video_path, miniatura_path, titulo, descripcion, etiquetas):
    creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
    youtube = build("youtube", "v3", credentials=creds)
    
    if isinstance(etiquetas, str):
        etiquetas = [tag.strip() for tag in etiquetas.split(",")]
    
    body = {
        "snippet": {
            "title": titulo[:100],
            "description": descripcion[:5000],
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
    
    # 🔑 FORZAR EL CANAL "Sombras de Medianoche Terror"
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
        onBehalfOfContentOwnerChannel=CANAL_ID_SOMBRAS
    )
    response = request.execute()
    video_id = response['id']
    print(f"✅ Video subido: https://youtu.be/{video_id}")
    
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
# MAIN (con pausas entre segmentos para no saturar)
# ================================================================
def main():
    print("🎬 Iniciando Bot de YouTube (con miniatura y IA)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    guion_data = generar_guion()
    if not guion_data:
        print("❌ No se pudo generar el guion. Abortando.")
        return
    
    titulo_video = guion_data.get("titulo", "Relato de terror | Sombras de Medianoche")
    descripcion_video = guion_data.get("descripcion", "Relato de terror basado en leyendas urbanas de México.")
    tags_video = guion_data.get("tags", "relatos de terror, leyendas urbanas, México")
    miniatura_prompt = guion_data.get("miniatura_prompt", "Escena de terror, paisaje oscuro, colores negro y rojo")
    segmentos = guion_data.get("segmentos", [])
    
    if not segmentos:
        print("❌ No se generaron segmentos. Abortando.")
        return
    
    print(f"✅ Guion generado con {len(segmentos)} segmentos")
    print(f"📌 Título: {titulo_video}")
    print(f"📌 Tags: {tags_video}")
    
    elementos_validos = []
    imagen_ultimo_recurso = None
    
    print("🎨 y 🎙️ Generando imágenes y audios para cada segmento...")
    
    for i, seg in enumerate(segmentos):
        print(f"\n--- Procesando segmento {i+1}/{len(segmentos)} ---")
        
        if i > 0:
            print("⏳ Esperando 12 segundos antes de la siguiente imagen...")
            time.sleep(12)
        
        url_img = generar_imagen(seg["imagen_prompt"], width=1024, height=1024)
        if url_img:
            imagen_ultimo_recurso = url_img
            print(f"✅ Imagen {i+1} generada")
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
    time.sleep(8)
    miniatura_path = "miniatura.jpg"
    miniatura_url = generar_imagen(miniatura_prompt, width=1280, height=720)
    
    if miniatura_url:
        try:
            r = requests.get(miniatura_url, timeout=30)
            r.raise_for_status()
            with open(miniatura_path, "wb") as f:
                f.write(r.content)
            print("✅ Miniatura generada")
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
