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
# LIMPIAR PROMPTS DE IMAGEN (2K, Inglés, Sin Gore)
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        return "Cinematic photo of Mexico City historic center at night, streetlights, 35mm photograph, hyperrealistic, 2k, ultra detailed"
    prompt = re.sub(r'\n+', ' ', prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r'[^\x00-\x7F]+', '', prompt)
    prompt = re.sub(r'\s+', ' ', prompt)
    estilo_limpio = " Cinematic lighting, 35mm film photograph, realistic everyday Mexican people, clean skin, no blood, no zombies, no gore, professional photography, 2k, hyperrealistic, ultra detailed, sharp focus."
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
                "imagen_prompt": "Cinematic photograph of an empty street in Mexico City at night, street lamps, fog, realistic 35mm photo, 2k"
            })
    
    return {
        "titulo": "El Silencio de la Calle Madero | Relato de Terror",
        "descripcion": "Relato de misterio y leyendas urbanas en México. Síguenos en Facebook: https://www.facebook.com/profile.php?id=61593237382982 #TerrorMexicano #LeyendasUrbanas #Misterio #Paranormal #HistoriasDeMiedo",
        "tags": "relatos de terror, leyendas urbanas, Mexico, misterio, suspension, terror mexicano, historias de miedo, casos paranormales, la llorona, el charro negro, nahuales, casas embrujadas, centro historico, calle Madero, testimonios reales",
        "miniatura_prompt": "Close-up portrait of a middle-aged Mexican man with a terrified expression, looking off-screen, dark alley background with orange and red neon reflections, cinematic lighting, shallow depth of field, hyperrealistic, 2k, space for text at bottom",
        "segmentos": segmentos[:24]
    }

# ================================================================
# GENERAR GUION + SEO CON DEEPSEEK (24 segmentos, voz natural)
# ================================================================
def generar_guion():
    prompt = """Eres un EXPERTO EN SEO DE YOUTUBE Y COPYWRITING para canales de terror, leyendas urbanas y misterio.
También eres un LOCUTOR PROFESIONAL DE PODCASTS DE TERROR.

Tu tarea es escribir una historia de terror en primera persona ambientada en México (aproximadamente 10000 caracteres).
Divide la historia en 24 segmentos de ~450 caracteres cada uno.

REGLAS OBLIGATORIAS DE REDACCIÓN PARA VOZ (Para evitar que suene robótica):
1. RITMO Y PAUSAS: Usa oraciones CORTAS. Abusa de los puntos suspensivos (...) y los guiones largos (—) para forzar pausas dramáticas y silencios tensos.
2. DIÁLOGOS Y EXCLAMACIONES: Usa signos de interrogación (¿?) y exclamación (¡!) en los momentos de miedo, duda o sorpresa.
3. ESTILO ORAL: Usa lenguaje natural de una persona asustada contando su historia (ej. "Y entonces... no lo van a creer, pero...", "Se los juro, me quedé helado...").
4. PALABRAS OMATOPÉYICAS O SUSTOS: Escribe interjecciones como "¡Ah!", "Shhh...", "Escuchen...", "Uff..." para darle matices orgánicos.
5. SIN TEXTO TÉCNICO: Jamás pongas paréntesis con acotaciones teatrales como (suspirando) o (susurrando), solo escribe el texto puro que la voz deba pronunciar.

REGLAS CRÍTICAS DE IMAGEN (imagen_prompt):
1. Escribe TODOS los "imagen_prompt" ESTRICTAMENTE EN INGLÉS.
2. Prompts fotográficos cinematográficos: "35mm film photo, Mexico City, night, fog, realistic, no gore, no zombies, 2k".
3. Describe escenas FOTOGRÁFICAS REALISTAS de personajes comunes de México.
4. Usa estilo cinematográfico: "Cinematic 35mm photograph, realistic lighting, Mexico City architecture, nocturnal, atmospheric mystery".

REGLA DE TEXTO (texto):
1. Solamente pon lo que el narrador habla. NUNCA incluyas la palabra "prompt" o instrucciones.
2. Usa comillas simples 'así' para diálogos.

Genera la respuesta estrictamente en formato JSON válido:
{
  "titulo": "Título atractivo de máximo 60 caracteres",
  "descripcion": "Descripción del video con palabras clave y 5 hashtags... Síguenos en Facebook: https://www.facebook.com/profile.php?id=61593237382982",
  "tags": "tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9, tag10, tag11, tag12, tag13, tag14, tag15",
  "miniatura_prompt": "Close-up portrait of a middle-aged Mexican man with a terrified expression, looking off-screen, dark alley background with orange and red neon reflections, cinematic lighting, shallow depth of field, hyperrealistic, 2k, space for text at bottom",
  "segmentos": [
    {
      "texto": "Texto que solo leerá la voz en español...",
      "imagen_prompt": "Detailed English photographic prompt for this specific scene, 2k"
    }
  ]
}
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
# GENERAR IMAGEN CON AGNES AI (2K)
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
# GENERAR AUDIO CON AZURE TTS (CandelaNeural + SSML con pausas)
# ================================================================
def generar_audio(texto, index, intentos=3):
    texto_limpio = re.sub(r'imagen_prompt.*', '', texto, flags=re.IGNORECASE)
    texto_limpio = texto_limpio.replace('"', '&quot;').replace("'", "&apos;")
    
    # Inyectar pausas SSML automáticas basadas en la puntuación
    texto_ssml = texto_limpio.replace('...', '<break time="800ms"/>')
    texto_ssml = texto_ssml.replace('. ', '. <break time="400ms"/>')
    texto_ssml = texto_ssml.replace(', ', ', <break time="200ms"/>')
    texto_ssml = texto_ssml.replace('! ', '! <break time="500ms"/>')
    texto_ssml = texto_ssml.replace('? ', '? <break time="500ms"/>')
    
    url = f"https://{AZURE_TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TTS_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3"
    }
    
    ssml = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="es-MX">
        <voice name="es-MX-CandelaNeural">
            <prosody rate="-8%" pitch="-3%">
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
    print("🎬 Iniciando Bot de YouTube (2K, 24 segmentos, Voz Natural)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    guion_data = generar_guion()
    if not guion_data:
        print("❌ No se pudo generar el guion. Abortando.")
        return
    
    titulo_video = guion_data.get("titulo", "Relato de terror | Sombras de Medianoche")
    descripcion_video = guion_data.get("descripcion", "Relato de terror basado en leyendas urbanas de México.")
    tags_video = guion_data.get("tags", "relatos de terror, leyendas urbanas, Mexico")
    miniatura_prompt = guion_data.get("miniatura_prompt", "Close-up portrait of a Mexican man with terrified expression, dark alley, orange and red neon, cinematic, 2k")
    segmentos = guion_data.get("segmentos", [])
    
    if not segmentos:
        print("❌ No se generaron segmentos. Abortando.")
        return
    
    print(f"✅ Guion generado con {len(segmentos)} segmentos")
    print(f"📌 Título: {titulo_video}")
    print(f"📌 Tags: {tags_video}")
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
    
    miniatura_prompt_refinado = f"{miniatura_prompt} High contrast, orange and red tones, dark background, text space at bottom, ultra detailed, 2k"
    
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
