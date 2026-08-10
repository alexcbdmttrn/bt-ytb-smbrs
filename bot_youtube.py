import os
import json
import re
import requests
import time
import random
import asyncio
import edge_tts
from datetime import datetime
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip
from PIL import Image, ImageOps
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ================================================================
# CONFIGURACIÓN (variables desde GitHub Secrets)
# ================================================================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
AGNES_API_KEY = os.getenv("AGNES_API_KEY")
YOUTUBE_USER_TOKEN = json.loads(os.getenv("YOUTUBE_USER_TOKEN")) if os.getenv("YOUTUBE_USER_TOKEN") else {}

FACEBOOK_LINK = "https://www.facebook.com/profile.php?id=61593237382982"

# ================================================================
# CONFIGURACIÓN DE EDGE-TTS (voz gratuita e ilimitada)
# ================================================================
VOZ_EDGE = "es-MX-JorgeNeural"  # Voz masculina mexicana (también: "es-MX-DaliaNeural" femenina)
VELOCIDAD_EDGE = "+25%"         # 1.25x más rápida
TONO_EDGE = "-2Hz"              # Ligeramente más grave (para atmósfera de terror)

# ================================================================
# LISTA DE ARCHIVOS DE FONDO DISPONIBLES (búsqueda recursiva)
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
    """Busca recursivamente un archivo de música en el repositorio."""
    fondos = FONDOS_DISPONIBLES.copy()
    random.shuffle(fondos)
    
    for root, dirs, files in os.walk("."):
        if "/." in root or "\\." in root:
            continue
        for file in files:
            for fondo in fondos:
                if file.lower() == fondo.lower():
                    full_path = os.path.join(root, file)
                    print(f"✅ Audio de fondo encontrado: {full_path}")
                    return full_path
    
    print("⚠️ No se encontró ningún archivo de fondo disponible.")
    return None

FONDO_AUDIO_FILE = seleccionar_fondo_disponible()
if FONDO_AUDIO_FILE:
    print(f"🎵 Audio de fondo seleccionado: {FONDO_AUDIO_FILE}")
else:
    print("⚠️ No se usará audio de fondo.")

# ================================================================
# LIMPIAR PROMPTS DE IMAGEN (2K 16:9, Sin Gore, Sin Rostros Demacrados)
# ================================================================
def limpiar_prompt(prompt):
    if not prompt:
        prompt = "Cinematic 35mm photograph of an old Mexican street at night, foggy lights, historic architecture"
    
    prompt = re.sub(r'\n+', ' ', prompt)
    prompt = re.sub(r'"', "'", prompt)
    prompt = re.sub(r'[^\x00-\x7F]+', '', prompt)
    
    # Remover palabras no deseadas
    palabras_prohibidas = [
        r'\bterror\b', r'\bhorror\b', r'\bsangre\b', r'\bblood\b', r'\bgore\b',
        r'\bdemacrad[oa]s?\b', r'\bzombies?\b', r'\bmuert[oa]s?\b', r'\bmatanza\b',
        r'\bscary face\b', r'\bmonster\b', r'\bdisfigured\b', r'\bwounds?\b'
    ]
    for pattern in palabras_prohibidas:
        prompt = re.sub(pattern, '', prompt, flags=re.IGNORECASE)
    
    prompt = re.sub(r'\s+', ' ', prompt).strip()
    
    estilo_limpio = (
        ", 35mm film photograph, 16:9 horizontal widescreen format, cinematic lighting, "
        "realistic handsome normal everyday Mexican people, clean healthy skin, fine natural features, "
        "atmospheric night mystery, paranormal ambient, professional photography, 2k resolution, "
        "hyperrealistic, sharp focus, no text, no letters, no words, no signs, no typography, "
        "no writing, no blood, no gore, no demaciated faces, no monsters."
    )
    return (prompt + estilo_limpio)[:500]

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
    print("⚠️ Usando fallback limpiado.")
    
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
                "imagen_prompt": "Cinematic 35mm photograph of a quiet street in Mexico City at night, warm streetlamps, fog, 16:9, 2k, hyperrealistic"
            })
    
    tags_fallback = "relatos paranormales, leyendas urbanas, Mexico, misterio, suspenso, casos reales, historias de miedo, la llorona, nahuales, casas embrujadas, centro historico, testimonios reales, mitos mexicanos, apariciones, espectros, noche, podcast paranormal"
    
    return {
        "titulo": "El Misterio Nocturno de la Calle Madero | Relato Real",
        "descripcion": f"Un sobrecogedor relato paranormal en primera persona. ¿Has sentido la presencia de lo desconocido en la oscuridad?\n\nSíguenos en nuestra página oficial de Facebook: {FACEBOOK_LINK}\n\nSuscríbete al canal para más testimonios e historias paranormales.\n\n#leyendasurbanas #Paranormal #Misterio #mexico #HistoriasDeMiedo",
        "tags": tags_fallback,
        "miniatura_prompt": "Cinematic portrait of a normal Mexican man looking out a window at night with a curious mysterious expression, dark street lights outside, 16:9 landscape, 2k",
        "segmentos": segmentos[:24]
    }

# ================================================================
# GENERAR GUION + SEO CON DEEPSEEK (Español, Paranormal, Sin Gore)
# ================================================================
def generar_guion():
    prompt = f"""Eres un EXPERTO EN SEO DE YOUTUBE Y COPYWRITING para canales de misterio, casos paranormales y leyendas urbanas.
También eres un LOCUTOR PROFESIONAL DE PODCASTS PARANORMALES.

Escribe un relato de eventos PARANORMALES Y CASOS DE MIEDO reales narrado en primera persona, ambientado en México (~10000 caracteres).
Divide el relato en 24 segmentos de ~450 caracteres cada uno.

REGLAS CRÍTICAS DE CONTENIDO (IMPORTANTE):
1. NO trates sobre sangre, masacres, gore, zombies ni violencia física.
2. Céntrate en lo PARANORMAL: ruidos extraños, sombras, apariciones sutiles, lugares antiguos, susurros, la sensación de estar acompañado.
3. Las personas descritas en los prompts deben ser mexicanas normales, sanas y realistas, NUNCA rostros demacrados, deformes ni ensangrentados.

REGLAS DE SEO Y TEXTO (EN ESPAÑOL):
1. TÍTULO: EN ESPAÑOL. Debe tener ENTRE 45 Y 60 CARACTERES exactos. Atractivo e intrigante.
2. DESCRIPCIÓN: EN ESPAÑOL. Sinopsis envolvente. DEBE INCLUIR OBLIGATORIAMENTE: "Síguenos en Facebook: {FACEBOOK_LINK}" y al final 5 hashtags (#leyendasurbanas #Paranormal #Misterio #mexico #HistoriasDeMiedo).
3. TAGS: EN ESPAÑOL. Entre 25 y 30 palabras clave separadas por comas (> 400 caracteres en total).

REGLAS DE REDACCIÓN DE NARRACIÓN:
1. Lenguaje fluido, expresivo y natural ("De pronto...", "Créanme...", "Un frío helado recorrió mi espalda...").
2. NUNCA incluyas paréntesis con acotaciones ni la palabra "prompt".

REGLAS DE IMAGEN (imagen_prompt):
1. Todos los "imagen_prompt" ESTRICTAMENTE EN INGLÉS.
2. Describe escenas fotográficas cinematográficas horizontales (16:9): "35mm photograph, Mexico City, night street, mystery, realistic normal Mexican people, clean skin, 16:9, 2k".
3. SIEMPRE incluye al final: "no text, no letters, no words, no blood, no gore, no demaciated faces".

Responde estrictamente en formato JSON válido:
{{
  "titulo": "Título de misterio entre 45 y 60 caracteres",
  "descripcion": "Sinopsis en español... Síguenos en Facebook: {FACEBOOK_LINK} #leyendasurbanas #Paranormal #Misterio #mexico #HistoriasDeMiedo",
  "tags": "tag1, tag2, tag3, ..., tag30",
  "miniatura_prompt": "Cinematic 16:9 photograph of a Mexican man in an old house at night looking with surprise, warm orange ambient, 2k, no text, no words",
  "segmentos": [
    {{
      "texto": "Texto en español que leerá el narrador...",
      "imagen_prompt": "Detailed English photographic prompt for this scene, 16:9 widescreen, 2k, no text, no blood, no demaciated faces"
    }}
  ]
}}
"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 5000,
        "response_format": {"type": "json_object"}
    }
    
    respuesta = ""
    for intento in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=150)
            r.raise_for_status()
            respuesta = r.json()["choices"][0]["message"]["content"].strip()
            print(f"📄 Respuesta de DeepSeek obtenida ({len(respuesta)} caracteres)")
            
            json_str = limpiar_respuesta_json(respuesta)
            data = json.loads(json_str)
            
            if "segmentos" not in data or len(data["segmentos"]) == 0:
                raise ValueError("La respuesta no contiene segmentos")
            
            titulo = data.get("titulo", "")
            if len(titulo) < 45 or len(titulo) > 60:
                print(f"⚠️ Ajustando longitud del título ({len(titulo)} caracteres)...")
                if len(titulo) > 60:
                    data["titulo"] = titulo[:57] + "..."
                elif len(titulo) < 45:
                    data["titulo"] = f"{titulo} | Relato Paranormal Real"[:60]
            
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
# GENERAR IMAGEN CON AGNES AI (2K Horizontal 16:9)
# ================================================================
def generar_imagen(prompt, width=2048, height=1152, intentos=3):
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
                print(f"⚠️ Intento {i+1}/{intentos} de imagen falló (código {r.status_code})")
                time.sleep(8)
        except Exception as e:
            print(f"⚠️ Intento {i+1}/{intentos} de imagen error: {e}")
            time.sleep(8)
    return None

# ================================================================
# GENERAR AUDIO CON EDGE-TTS (Gratis, Ilimitado, Sin Pausas Artificiales)
# ================================================================
def generar_audio(texto, index):
    """
    Genera audio usando edge-tts (gratis, ilimitado, sin claves API).
    La voz fluye de forma natural sin pausas artificiales.
    """
    texto_limpio = re.sub(r'imagen_prompt.*', '', texto, flags=re.IGNORECASE)
    texto_limpio = texto_limpio.strip()
    
    if not texto_limpio:
        print(f"⚠️ Texto vacío para audio {index}, saltando...")
        return None
    
    filename = f"audio_{index}.mp3"
    
    async def _generar():
        communicate = edge_tts.Communicate(
            texto_limpio,
            VOZ_EDGE,
            rate=VELOCIDAD_EDGE,
            pitch=TONO_EDGE
        )
        await communicate.save(filename)
    
    try:
        # Ejecutar el loop de asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_generar())
        loop.close()
        print(f"✅ Audio {index} generado con edge-tts")
        return filename
    except Exception as e:
        print(f"❌ Error generando audio {index} con edge-tts: {e}")
        return None

# ================================================================
# MONTAR VIDEO CON MOVIEPY (10% VOLUMEN MÚSICA Y RECORTE 16:9 PERFECTO)
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
            
            # Ajustar la imagen con recortado proporcional a 1920x1080 (16:9 sin deformar)
            with Image.open(img_path) as img:
                img_fitted = ImageOps.fit(img, (1920, 1080), Image.Resampling.LANCZOS)
                img_fitted.save(img_path)
            
            video_clip = ImageClip(img_path).set_duration(duracion)
            
            clips_video.append(video_clip)
            clips_audio.append(audio_clip)
        except Exception as e:
            print(f"⚠️ Error procesando segmento {i}: {e}")
            continue

    if not clips_video or not clips_audio:
        raise ValueError("No se pudieron procesar los clips de video o audio")

    video = concatenate_videoclips(clips_video, method="compose")
    audio_narracion = concatenate_audioclips(clips_audio)
    duracion_total = audio_narracion.duration

    # 🎵 Mezclar audio de fondo al 10% de volumen
    fondo_path = FONDO_AUDIO_FILE
    if fondo_path and not os.path.exists(fondo_path):
        print(f"⚠️ El archivo seleccionado ({fondo_path}) no existe físicamente. Re-buscando...")
        fondo_path = seleccionar_fondo_disponible()
    
    if fondo_path and os.path.exists(fondo_path):
        try:
            fondo_clip = AudioFileClip(fondo_path)
            if fondo_clip.duration < duracion_total:
                veces = int(duracion_total / fondo_clip.duration) + 1
                fondo_clip = fondo_clip * veces
            fondo_clip = fondo_clip.subclip(0, duracion_total)
            fondo_clip = fondo_clip.volumex(0.10)  # 10% DE VOLUMEN
            audio_final = CompositeAudioClip([audio_narracion, fondo_clip])
            print(f"🎵 Audio de fondo mezclado exitosamente: {fondo_path} (Volumen: 10%)")
        except Exception as e:
            print(f"⚠️ Error procesando audio de fondo: {e}. Usando solo narración.")
            audio_final = audio_narracion
    else:
        print("⚠️ No se encontró audio de fondo. Se usará solo la voz.")
        audio_final = audio_narracion

    video = video.set_audio(audio_final)
    video.write_videofile(salida, fps=24, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")
    print(f"✅ Video creado correctamente: {salida}")
    return salida

# ================================================================
# SUBIR A YOUTUBE (Configuración Oficial en Español)
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
            "categoryId": "24",
            "defaultLanguage": "es",
            "defaultAudioLanguage": "es"
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
            print("✅ Miniatura 16:9 subida correctamente a YouTube")
        except Exception as e:
            print(f"⚠️ No se pudo subir la miniatura: {e}")
    
    return response

# ================================================================
# MAIN
# ================================================================
def main():
    print("🎬 Iniciando Bot de YouTube (2K 16:9, edge-tts, Música 10%, SEO en Español)")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    guion_data = generar_guion()
    if not guion_data:
        print("❌ No se pudo generar el guion. Abortando.")
        return
    
    titulo_video = guion_data.get("titulo", "El Misterio Nocturno de la Calle Madero | Relato Real")
    descripcion_video = guion_data.get("descripcion", f"Relato de eventos paranormales en México.\n\nSíguenos en Facebook: {FACEBOOK_LINK}")
    tags_video = guion_data.get("tags", "relatos paranormales, leyendas urbanas, Mexico, misterio")
    miniatura_prompt = guion_data.get("miniatura_prompt", "Cinematic portrait of a Mexican man in an old house at night, warm lighting, 16:9 widescreen, 2k")
    segmentos = guion_data.get("segmentos", [])
    
    if not segmentos:
        print("❌ No se generaron segmentos. Abortando.")
        return
    
    print(f"✅ Guion generado con {len(segmentos)} segmentos")
    print(f"📌 Título ({len(titulo_video)} caracteres): {titulo_video}")
    
    elementos_validos = []
    imagen_ultimo_recurso = None
    
    print("\n🎨 y 🎙️ Generando imágenes (2K 16:9) y audios (edge-tts 1.25x)...")
    
    for i, seg in enumerate(segmentos):
        print(f"\n--- Procesando segmento {i+1}/{len(segmentos)} ---")
        
        if i > 0:
            time.sleep(6)
        
        url_img = generar_imagen(seg["imagen_prompt"], width=2048, height=1152)
        if url_img:
            imagen_ultimo_recurso = url_img
            print(f"✅ Imagen {i+1} generada (2K 16:9)")
        elif imagen_ultimo_recurso:
            print(f"⚠️ Reutilizando imagen previa para segmento {i+1}")
            url_img = imagen_ultimo_recurso
        else:
            print(f"❌ Sin imagen disponible para segmento {i+1}, se salta.")
            continue
        
        time.sleep(4)
        
        audio_file = generar_audio(seg["texto"], i)
        if not audio_file:
            print(f"❌ Falló el audio {i+1}, se salta el segmento.")
            continue
        
        elementos_validos.append({
            "imagen_url": url_img,
            "audio_path": audio_file
        })
        print(f"✅ Segmento {i+1} completado")
    
    # Generación y forzado de Miniatura a 1280x720 (Horizontal 16:9)
    print("\n🖼️ Generando y ajustando miniatura horizontal 1280x720...")
    miniatura_path = "miniatura.jpg"
    miniatura_prompt_refinado = f"{miniatura_prompt} 16:9 landscape aspect ratio, cinematic widescreen, 2k, no text, no words, no blood, no demaciated faces"
    miniatura_url = generar_imagen(miniatura_prompt_refinado, width=1280, height=720)
    
    if miniatura_url:
        try:
            r = requests.get(miniatura_url, timeout=30)
            r.raise_for_status()
            with open(miniatura_path, "wb") as f:
                f.write(r.content)
            
            with Image.open(miniatura_path) as img:
                img_fitted = ImageOps.fit(img, (1280, 720), Image.Resampling.LANCZOS)
                img_fitted.save(miniatura_path)
            print("✅ Miniatura ajustada a formato 16:9 (1280x720) correctamente")
        except Exception as e:
            print(f"⚠️ Error al procesar miniatura: {e}")
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
    
    print("\n⬆️ Subiendo video a YouTube con metadatos en español...")
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
