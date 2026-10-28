import os
import json
import random
import subprocess
import sqlite3
import time
import requests
from groq import Groq

# Configuración de credenciales y variables de entorno
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL", "")

# IDs de Afiliado
CLICKBANK_AFFILIATE_ID = os.environ.get("CLICKBANK_AFFILIATE_ID", "tu_usuario_clickbank")
DIGISTORE_AFFILIATE_ID = os.environ.get("DIGISTORE_AFFILIATE_ID", "tu_usuario_digistore")
NICHO_REPOSITORIO = os.environ.get("NICHO_NAME", "SaaS_Tools_Global")

if not GROQ_API_KEY:
    print("❌ ERROR CRÍTICO: La variable GROQ_API_KEY no está configurada.")
if not MAKE_WEBHOOK_URL:
    print("⚠️ AVISO: MAKE_WEBHOOK_URL no configurado. Modo local autónomo.")

# Canales de Telegram ampliados para incluir nichos SaaS y recurrentes
TELEGRAM_CHANNELS = {
    "B2B_Finance_Global": "https://t.me/tu_canal_finanzas",
    "Salud_Nutricion_Global": "https://t.me/tu_canal_salud",
    "Relaciones_Pareja_Global": "https://t.me/tu_canal_relaciones",
    "Desarrollo_Personal_Global": "https://t.me/tu_canal_desarrollo",
    "Supervivencia_Hobbies_Global": "https://t.me/tu_canal_supervivencia",
    "SaaS_Tools_Global": "https://t.me/tu_canal_saas_ia", # Nuevo canal enfocado en software mensual
    "Marketing_Automation_Global": "https://t.me/tu_canal_marketing" # Nuevo canal enfocado en herramientas de trafico/ventas
}

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
DB_FILE = "swarm_metrics.db"

def inicializar_bd():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ejecuciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                nicho TEXT,
                idioma TEXT,
                producto TEXT,
                plataforma TEXT,
                estado TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Error inicializando SQLite: {e}")

def llamar_groq_con_fallback(messages, temperature=0.75, max_tokens=300):
    if not client:
        raise Exception("Cliente Groq no inicializado.")
        
    modelos_candidatos = []
    try:
        response_models = client.models.list()
        todos_los_ids = [m.id for m in response_models.data]
        palabras_prohibidas = ["guard", "embed", "vision", "audio", "whisper", "safeguard", "orpheus", "tts", "stt"]
        modelos_candidatos = [
            m_id for m_id in todos_los_ids 
            if not any(bad in m_id.lower() for bad in palabras_prohibidas)
        ]
    except Exception as e:
        print(f"⚠️ Error listando modelos: {e}")
        
    if not modelos_candidatos:
        modelos_candidatos = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "allam-2-7b"]
        
    for modelo in modelos_candidatos:
        try:
            res = client.chat.completions.create(
                model=modelo,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            contenido = res.choices[0].message.content
            if contenido:
                return contenido
        except Exception:
            continue
            
    raise Exception("❌ Todos los modelos de chat fallaron.")

def obtener_oferta_aprobacion_instantanea(nicho):
    plataforma = random.choice(["ClickBank", "Digistore24"])
    aff_id = CLICKBANK_AFFILIATE_ID if plataforma == "ClickBank" else DIGISTORE_AFFILIATE_ID
    
    # Prompt ajustado específicamente para buscar software SaaS de alta retención o suscripciones mensuales
    prompt = (
        f"You are a master affiliate marketing engine focused ONLY on recurring monthly revenue (SaaS, AI Tools, Marketing Software). "
        f"Select the absolute HIGHEST-RETENTION recurring subscription program or SaaS tool from '{plataforma}' "
        f"for the niche '{nicho}' optimized for high purchasing power markets (US, EU, UK). "
        f"Return ONLY a valid JSON object without markdown codeblocks or extra text: "
        f'{{"id": "saas_recurring_profit", "nicho": "{nicho}", "nombre": "Top SaaS Software", '
        f'"plataforma": "{plataforma}", "hook_tematica": "automated software solution", "vendor_id": "vendor_code"}}'
    )
    
    for intento in range(3):
        try:
            texto_res = llamar_groq_con_fallback([{"role": "user", "content": prompt}], temperature=0.7, max_tokens=250).strip()
            if "```json" in texto_res:
                texto_res = texto_res.split("```json")[1].split("```")[0].strip()
            elif "```" in texto_res:
                texto_res = texto_res.split("```")[1].split("```")[0].strip()
                
            oferta = json.loads(texto_res)
            vendor = oferta.get("vendor_id", "vendor")
            
            if plataforma == "ClickBank":
                oferta["link_afiliado"] = f"https://{aff_id}.{vendor}.hop.clickbank.net"
            else:
                oferta["link_afiliado"] = f"https://www.digistore24.com/redir/{vendor}/{aff_id}/"
                
            return oferta
        except Exception as e:
            time.sleep(2)
            
    return {
        "id": "fallback_saas", "nicho": nicho, "nombre": "Global AI SaaS Pro",
        "plataforma": "ClickBank", "hook_tematica": "automated workflow software",
        "link_afiliado": f"https://{aff_id}.vendor.hop.clickbank.net"
    }

def generar_contenido_ia(nicho_repo):
    oferta = obtener_oferta_aprobacion_instantanea(nicho_repo)
    idioma = random.choice(["en", "es", "pt", "de", "fr"])
    link_telegram = TELEGRAM_CHANNELS.get(nicho_repo, "https://t.me/tu_canal_general")
    
    prompts = {
        "en": f"Write a high-converting viral script for software tool '{oferta.get('nombre', 'SaaS Offer')}' ({oferta.get('hook_tematica', 'solution')}). Include hashtags, direct affiliate link: {oferta.get('link_afiliado', '')}, and CTA to join our VIP Telegram channel: {link_telegram}.",
        "es": f"Escribe un guión viral para el software '{oferta.get('nombre', 'SaaS Offer')}' ({oferta.get('hook_tematica', 'solución')}). Incluye hashtags, enlace de afiliado: {oferta.get('link_afiliado', '')}, y llamada a la acción para unirse al canal de Telegram: {link_telegram}.",
        "pt": f"Escreva um roteiro viral para a ferramenta '{oferta.get('nombre', 'SaaS Offer')}' ({oferta.get('hook_tematica', 'solução')}). Inclua hashtags, link de afiliado: {oferta.get('link_afiliado', '')}, e CTA para o canal do Telegram: {link_telegram}.",
        "de": f"Schreiben Sie ein virales Skript für die Software '{oferta.get('nombre', 'SaaS Offer')}' ({oferta.get('hook_tematica', 'Lösung')}). Inklusive Hashtags, Affiliate-Link: {oferta.get('link_afiliado', '')} und Telegram-CTA: {link_telegram}.",
        "fr": f"Écrivez un script vidéo viral pour le logiciel '{oferta.get('nombre', 'SaaS Offer')}' ({oferta.get('hook_tematica', 'solution')}). Incluez des hashtags, lien d'affiliation: {oferta.get('link_afiliado', '')} et CTA vers Telegram: {link_telegram}."
    }
    
    try:
        texto = llamar_groq_con_fallback([{"role": "user", "content": prompts.get(idioma, prompts["en"])}], temperature=0.8, max_tokens=450)
    except Exception:
        texto = f"Access software tool now: {oferta.get('link_afiliado', '')} | Join Telegram: {link_telegram}"

    cabecera = f"🚀 **RECURRING SWARM NICHO:** `{nicho_repo.upper()}` | 🌍 **LANG:** [{idioma.upper()}]\n🛒 **SOFTWARE [{oferta.get('plataforma', 'ClickBank')}]:** {oferta.get('nombre', 'SaaS Offer')}\n\n"
    return cabecera + texto, oferta, idioma, link_telegram

def procesar_video_ffmepg_pro():
    output_video = "output_swarm.mp4"
    color_rand = f"0x{random.randint(0, 16777215):06x}"
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color_rand}:s=1080x1920:r=30",
        "-t", "5", "-c:v", "libx264", "-pix_fmt", "yuv420p", output_video
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=40)
        return output_video
    except Exception:
        return output_video

def enviar_a_make_webhook(payload):
    if not MAKE_WEBHOOK_URL:
        return False
    for _ in range(3):
        try:
            res = requests.post(MAKE_WEBHOOK_URL, json=payload, timeout=20)
            if res.status_code == 200:
                return True
        except Exception:
            time.sleep(3)
    return False

def auto_commit_db_eterno():
    try:
        subprocess.run(["git", "config", "--global", "user.name", "Eternal Autonomous Swarm"], stdout=subprocess.DEVNULL)
        subprocess.run(["git", "config", "--global", "user.email", "eternal.swarm@github.local"], stdout=subprocess.DEVNULL)
        subprocess.run(["git", "checkout", "--", "."], stdout=subprocess.DEVNULL)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], stdout=subprocess.DEVNULL)
        subprocess.run(["git", "add", DB_FILE], stdout=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "🔄 SaaS Swarm Autonomous Sync [skip ci]"], stdout=subprocess.DEVNULL)
        subprocess.run(["git", "push", "origin", "main"], stdout=subprocess.DEVNULL)
    except Exception:
        pass

if __name__ == "__main__":
    print(f"♾️ Iniciando Ciclo SaaS Recurrente para: {NICHO_REPOSITORIO}")
    inicializar_bd()
    
    mensaje, oferta, idioma, link_telegram = generar_contenido_ia(NICHO_REPOSITORIO)
    video_generado = procesar_video_ffmepg_pro()
    
    payload_make = {
        "nicho": NICHO_REPOSITORIO,
        "idioma": idioma,
        "plataforma_afiliados": oferta.get("plataforma"),
        "producto_nombre": oferta.get("nombre"),
        "link_afiliado": oferta.get("link_afiliado"),
        "link_telegram": link_telegram,
        "contenido_texto": mensaje,
        "video_path": video_generado,
        "target_platforms": ["tiktok", "instagram", "facebook", "youtube_shorts", "telegram"]
    }
    
    webhook_status = enviar_a_make_webhook(payload_make)
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        estado_final = "SAAS_SYNC_SUCCESS" if webhook_status else "LOCAL_SAAS_SUCCESS"
        cursor.execute("INSERT INTO ejecuciones (timestamp, nicho, idioma, producto, plataforma, estado) VALUES (datetime('now'), ?, ?, ?, ?, ?)",
                       (NICHO_REPOSITORIO, idioma, oferta.get('nombre'), oferta.get('plataforma'), estado_final))
        conn.commit()
        conn.close()
    except Exception:
        pass
        
    auto_commit_db_eterno()
