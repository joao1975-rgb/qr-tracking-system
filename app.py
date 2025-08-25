#!/usr/bin/env python3
"""
QR Tracking System - Backend Completo
Versión: 2.5.0 - Soporte completo para Campañas, Dispositivos y Analytics
Autor: Sistema QR Tracking
Fecha: 2024

Funcionalidades:
- Gestión completa de campañas
- Gestión de dispositivos físicos
- Tracking avanzado de escaneos
- Analytics en tiempo real
- APIs RESTful completas
- Servir archivos HTML estáticos
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import sqlite3
import json
import os
import logging
from datetime import datetime, timedelta
import uuid
import user_agents
import ipaddress
from urllib.parse import urlparse, parse_qs

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================================
# CONFIGURACIÓN DE LA APLICACIÓN
# ================================

app = FastAPI(
    title="QR Tracking System",
    description="Sistema avanzado de tracking para códigos QR",
    version="2.5.0"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base de datos
DATABASE_PATH = "qr_tracking.db"

# ================================
# MODELOS PYDANTIC
# ================================

class CampaignCreate(BaseModel):
    campaign_code: str = Field(..., min_length=1, max_length=100)
    client: str = Field(..., min_length=1, max_length=200)
    destination: str = Field(..., min_length=1)
    description: Optional[str] = None
    active: bool = True

class CampaignUpdate(BaseModel):
    client: Optional[str] = None
    destination: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None

class DeviceCreate(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=100)
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    location: Optional[str] = None
    venue: Optional[str] = None
    description: Optional[str] = None
    active: bool = True

class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    location: Optional[str] = None
    venue: Optional[str] = None
    description: Optional[str] = None
    active: Optional[bool] = None

class ScanCreate(BaseModel):
    campaign_code: str
    client: Optional[str] = None
    destination: Optional[str] = None
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    location: Optional[str] = None
    venue: Optional[str] = None
    session_id: Optional[str] = None

class QRGenerationLog(BaseModel):
    campaign_id: Optional[int] = None
    physical_device_id: Optional[int] = None
    qr_size: int = 256
    generated_by: Optional[str] = None

# ================================
# FUNCIONES DE BASE DE DATOS
# ================================

def init_database():
    """Inicializar la base de datos con el esquema"""
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            # Leer el esquema SQL
            schema_path = "database_schema.sql"
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    conn.executescript(f.read())
            else:
                # Crear esquema básico si no existe el archivo
                create_basic_schema(conn)
        logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {e}")

def create_basic_schema(conn):
    """Crear esquema básico si no existe el archivo SQL"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_code TEXT NOT NULL UNIQUE,
            client TEXT NOT NULL,
            destination TEXT NOT NULL,
            description TEXT,
            active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS physical_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL UNIQUE,
            device_name TEXT,
            device_type TEXT,
            location TEXT,
            venue TEXT,
            description TEXT,
            active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_code TEXT NOT NULL,
            client TEXT,
            destination TEXT,
            device_id TEXT,
            device_name TEXT,
            location TEXT,
            venue TEXT,
            user_device_type TEXT,
            browser TEXT,
            operating_system TEXT,
            screen_resolution TEXT,
            user_agent TEXT,
            ip_address TEXT,
            country TEXT,
            city TEXT,
            session_id TEXT,
            scan_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            redirect_completed BOOLEAN DEFAULT 0,
            redirect_timestamp DATETIME,
            duration_seconds REAL,
            campaign_id INTEGER,
            physical_device_id INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS qr_generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            physical_device_id INTEGER,
            qr_size INTEGER,
            generated_by TEXT,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

def get_db_connection():
    """Obtener conexión a la base de datos"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Para acceder a columnas por nombre
    return conn

# ================================
# FUNCIONES DE UTILIDAD
# ================================

def detect_device_info(user_agent_string: str) -> Dict[str, str]:
    """Detectar información del dispositivo desde User-Agent"""
    try:
        user_agent = user_agents.parse(user_agent_string)
        
        # Determinar tipo de dispositivo
        if user_agent.is_mobile:
            device_type = "Mobile"
        elif user_agent.is_tablet:
            device_type = "Tablet"
        elif user_agent.is_pc:
            device_type = "Desktop"
        else:
            device_type = "Unknown"
        
        return {
            "device_type": device_type,
            "browser": f"{user_agent.browser.family} {user_agent.browser.version_string}",
            "operating_system": f"{user_agent.os.family} {user_agent.os.version_string}",
            "is_mobile": user_agent.is_mobile,
            "is_tablet": user_agent.is_tablet,
            "is_pc": user_agent.is_pc
        }
    except Exception as e:
        logger.warning(f"Error detectando dispositivo: {e}")
        return {
            "device_type": "Unknown",
            "browser": "Unknown",
            "operating_system": "Unknown",
            "is_mobile": False,
            "is_tablet": False,
            "is_pc": False
        }

def get_client_ip(request: Request) -> str:
    """Obtener IP del cliente"""
    # Intentar obtener IP real detrás de proxies
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"

# ================================
# ENDPOINTS DE PÁGINAS HTML
# ================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """Página principal"""
    try:
        # Leer el archivo HTML del index
        with open(os.path.join(os.path.dirname(__file__), "templates", "index.html"), "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Reemplazar variables del template
        base_url = "http://localhost:8000"  # Cambiar según configuración
        html_content = html_content.replace("{{ base_url }}", base_url)
        
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
        <head><title>QR Tracking System</title></head>
        <body>
            <h1>QR Tracking System v2.5.0</h1>
            <p>Sistema funcionando. Archivos HTML no encontrados.</p>
            <ul>
                <li><a href="/dashboard">Dashboard</a></li>
                <li><a href="/admin/campaigns">Admin Campañas</a></li>
                <li><a href="/generate-qr">Generar QR</a></li>
                <li><a href="/health">Estado del Sistema</a></li>
            </ul>
        </body>
        </html>
        """)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Dashboard con analytics"""
    try:
        with open(os.path.join(os.path.dirname(__file__), "templates", "dashboard.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Dashboard</h1><p>Archivo dashboard.html no encontrado</p>")

@app.get("/admin/campaigns", response_class=HTMLResponse)
async def admin_campaigns():
    """Panel de administración de campañas"""
    try:
        with open(os.path.join(os.path.dirname(__file__), "templates", "admin_campaigns.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Admin Campañas</h1><p>Archivo admin_campaigns.html no encontrado</p>")

@app.get("/generate-qr", response_class=HTMLResponse)
async def generate_qr():
    """Generador de códigos QR"""
    try:
        with open(os.path.join(os.path.dirname(__file__), "templates", "generate_qr.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Generar QR</h1><p>Archivo generate_qr.html no encontrado</p>")

@app.get("/devices", response_class=HTMLResponse)
async def devices_page():
    """Página de gestión de dispositivos"""
    try:
        with open(os.path.join(os.path.dirname(__file__), "templates", "devices.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html>
        <head><title>Dispositivos - QR Tracking</title></head>
        <body>
            <h1>Gestión de Dispositivos</h1>
            <p>Archivo devices.html no encontrado</p>
            <a href="/">← Volver al inicio</a>
        </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Verificación de estado del sistema"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM campaigns")
            campaigns_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM physical_devices")
            devices_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM scans")
            scans_count = cursor.fetchone()[0]
        
        return {
            "status": "healthy",
            "version": "2.5.0",
            "database": "connected",
            "stats": {
                "campaigns": campaigns_count,
                "devices": devices_count,
                "scans": scans_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# ================================
# ENDPOINT DE TRACKING PRINCIPAL
# ================================

@app.get("/track")
async def track_qr_scan(request: Request):
    """Endpoint principal de tracking de QR"""
    try:
        # Obtener parámetros de la URL
        params = dict(request.query_params)
        
        # Parámetros requeridos
        campaign_code = params.get("campaign")
        if not campaign_code:
            raise HTTPException(status_code=400, detail="Parámetro 'campaign' requerido")
        
        # Parámetros opcionales
        client = params.get("client", "")
        destination = params.get("destination", "")
        device_id = params.get("device_id", "")
        device_name = params.get("device_name", "")
        location = params.get("location", "")
        venue = params.get("venue", "")
        
        # Generar session_id único
        session_id = str(uuid.uuid4())
        
        # Detectar información del dispositivo del usuario
        user_agent = request.headers.get("User-Agent", "")
        device_info = detect_device_info(user_agent)
        client_ip = get_client_ip(request)
        
        # Si no se proporciona destino, buscar en la base de datos
        if not destination and campaign_code:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT destination FROM campaigns WHERE campaign_code = ?", (campaign_code,))
                result = cursor.fetchone()
                if result:
                    destination = result["destination"]
        
        # Si aún no hay destino, usar uno por defecto
        if not destination:
            destination = f"https://google.com/search?q={campaign_code}"
        
        # Registrar el escaneo en la base de datos
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scans (
                    campaign_code, client, destination, device_id, device_name, 
                    location, venue, user_device_type, browser, operating_system, 
                    user_agent, ip_address, session_id, scan_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                campaign_code, client, destination, device_id, device_name,
                location, venue, device_info["device_type"], device_info["browser"],
                device_info["operating_system"], user_agent, client_ip, session_id,
                datetime.now().isoformat()
            ))
            conn.commit()
            scan_id = cursor.lastrowid
        
        # Log del escaneo
        logger.info(f"QR escaneado: {campaign_code} desde {device_info['device_type']} - IP: {client_ip}")
        
        # Crear respuesta HTML con redirección automática
        html_response = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Redirigiendo...</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-align: center;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.1);
                    padding: 40px;
                    border-radius: 15px;
                    backdrop-filter: blur(10px);
                }}
                .loading {{
                    width: 40px;
                    height: 40px;
                    border: 4px solid rgba(255,255,255,0.3);
                    border-radius: 50%;
                    border-top-color: white;
                    animation: spin 1s ease-in-out infinite;
                    margin: 20px auto;
                }}
                @keyframes spin {{
                    to {{ transform: rotate(360deg); }}
                }}
            </style>
            <meta http-equiv="refresh" content="3;url={destination}">
        </head>
        <body>
            <div class="container">
                <h1>🎯 QR Tracking</h1>
                <div class="loading"></div>
                <p>Redirigiendo a {client or 'destino'}...</p>
                <p><small>Campaña: {campaign_code}</small></p>
                <p><a href="{destination}" style="color: white;">Ir manualmente si no redirije</a></p>
            </div>
            <script>
                // Registrar que la redirección se completó después de 3 segundos
                setTimeout(() => {{
                    fetch('/api/track/complete', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{
                            session_id: '{session_id}',
                            scan_id: {scan_id},
                            completion_time: new Date().toISOString()
                        }})
                    }}).catch(console.error);
                    
                    // Redirigir
                    window.location.href = '{destination}';
                }}, 3000);
                
                // Registrar tiempo de permanencia al salir
                window.addEventListener('beforeunload', () => {{
                    navigator.sendBeacon('/api/track/complete', JSON.stringify({{
                        session_id: '{session_id}',
                        scan_id: {scan_id},
                        completion_time: new Date().toISOString()
                    }}));
                }});
            </script>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en tracking: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ================================
# APIs DE CAMPAÑAS
# ================================

@app.get("/api/campaigns")
async def get_campaigns():
    """Obtener todas las campañas"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM campaigns 
                ORDER BY created_at DESC
            """)
            campaigns = [dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "campaigns": campaigns,
            "total": len(campaigns)
        }
    except Exception as e:
        logger.error(f"Error obteniendo campañas: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/campaigns")
async def create_campaign(campaign: CampaignCreate):
    """Crear nueva campaña"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO campaigns (campaign_code, client, destination, description, active)
                VALUES (?, ?, ?, ?, ?)
            """, (
                campaign.campaign_code, campaign.client, campaign.destination,
                campaign.description, campaign.active
            ))
            conn.commit()
            campaign_id = cursor.lastrowid
            
            # Obtener la campaña creada
            cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
            new_campaign = dict(cursor.fetchone())
        
        logger.info(f"Campaña creada: {campaign.campaign_code}")
        return {
            "success": True,
            "message": "Campaña creada exitosamente",
            "campaign": new_campaign
        }
    except sqlite3.IntegrityError:
        return {"success": False, "error": "El código de campaña ya existe"}
    except Exception as e:
        logger.error(f"Error creando campaña: {e}")
        return {"success": False, "error": str(e)}

@app.put("/api/campaigns/{campaign_code}")
async def update_campaign(campaign_code: str, campaign_update: CampaignUpdate):
    """Actualizar campaña existente"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la campaña existe
            cursor.execute("SELECT id FROM campaigns WHERE campaign_code = ?", (campaign_code,))
            if not cursor.fetchone():
                return {"success": False, "error": "Campaña no encontrada"}
            
            # Construir query de actualización dinámicamente
            update_fields = []
            values = []
            
            if campaign_update.client is not None:
                update_fields.append("client = ?")
                values.append(campaign_update.client)
            if campaign_update.destination is not None:
                update_fields.append("destination = ?")
                values.append(campaign_update.destination)
            if campaign_update.description is not None:
                update_fields.append("description = ?")
                values.append(campaign_update.description)
            if campaign_update.active is not None:
                update_fields.append("active = ?")
                values.append(campaign_update.active)
            
            if not update_fields:
                return {"success": False, "error": "No hay campos para actualizar"}
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(campaign_code)
            
            query = f"UPDATE campaigns SET {', '.join(update_fields)} WHERE campaign_code = ?"
            cursor.execute(query, values)
            conn.commit()
        
        logger.info(f"Campaña actualizada: {campaign_code}")
        return {"success": True, "message": "Campaña actualizada exitosamente"}
    except Exception as e:
        logger.error(f"Error actualizando campaña: {e}")
        return {"success": False, "error": str(e)}


@app.delete("/api/campaigns/{campaign_code}/delete-permanently")
async def delete_campaign_permanently(campaign_code: str):
    """ELIMINAR campaña PERMANENTEMENTE - Endpoint alternativo para mayor claridad"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la campaña existe y obtener información
            cursor.execute("SELECT * FROM campaigns WHERE campaign_code = ?", (campaign_code,))
            campaign = cursor.fetchone()
            if not campaign:
                return {"success": False, "error": "Campaña no encontrada"}
            
            campaign_info = dict(campaign)
            
            # Contar scans relacionados
            cursor.execute("SELECT COUNT(*) FROM scans WHERE campaign_code = ?", (campaign_code,))
            scans_count = cursor.fetchone()[0]
            
            # ELIMINAR FÍSICAMENTE la campaña
            cursor.execute("DELETE FROM campaigns WHERE campaign_code = ?", (campaign_code,))
            
            # Opcional: Eliminar también los scans (descomenta si quieres limpieza completa)
            # cursor.execute("DELETE FROM scans WHERE campaign_code = ?", (campaign_code,))
            
            conn.commit()
        
        logger.warning(f"CAMPAÑA ELIMINADA PERMANENTEMENTE: {campaign_code} - Cliente: {campaign_info.get('client')} - Scans afectados: {scans_count}")
        
        return {
            "success": True,
            "message": f"Campaña '{campaign_code}' eliminada permanentemente",
            "deleted_campaign": campaign_info,
            "affected_scans": scans_count
        }
    except Exception as e:
        logger.error(f"Error eliminando campaña permanentemente: {e}")
        return {"success": False, "error": str(e)}
    

@app.patch("/api/campaigns/{campaign_code}/deactivate")
async def deactivate_campaign(campaign_code: str):
    """DESACTIVAR campaña (no eliminar) - Para pausar temporalmente"""

@app.delete("/api/campaigns/{campaign_code}")
async def delete_campaign(campaign_code: str):
    """Eliminar campaña (desactivar)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE campaigns 
                SET active = 0, updated_at = CURRENT_TIMESTAMP 
                WHERE campaign_code = ?
            """, (campaign_code,))
            
            if cursor.rowcount == 0:
                return {"success": False, "error": "Campaña no encontrada"}
            
            conn.commit()
        
        logger.info(f"Campaña eliminada (desactivada): {campaign_code}")
        return {"success": True, "message": "Campaña eliminada exitosamente"}
    except Exception as e:
        logger.error(f"Error eliminando campaña: {e}")
        return {"success": False, "error": str(e)}

# ================================
# APIs DE DISPOSITIVOS - COMPLETAS
# ================================

@app.get("/api/devices")
async def get_devices():
    """Obtener todos los dispositivos"""
>>>>>>> fb48b359afc889170368b7375b332b1c3585d2ab
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""

                UPDATE campaigns 
                SET active = 0, updated_at = CURRENT_TIMESTAMP 
                WHERE campaign_code = ?
            """, (campaign_code,))
            
            if cursor.rowcount == 0:
                return {"success": False, "error": "Campaña no encontrada"}
            
            conn.commit()
        
        logger.info(f"Campaña desactivada: {campaign_code}")
        return {"success": True, "message": "Campaña desactivada exitosamente"}
    except Exception as e:
        logger.error(f"Error desactivando campaña: {e}")
        return {"success": False, "error": str(e)}
    
# ================================
# APIs DE DISPOSITIVOS - COMPLETAS
# ================================

@app.get("/api/devices")
async def get_devices():
    """Obtener todos los dispositivos"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
=======
>>>>>>> fb48b359afc889170368b7375b332b1c3585d2ab
                SELECT * FROM physical_devices 
                ORDER BY created_at DESC
            """)
            devices = [dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "devices": devices,
            "total": len(devices)
        }
    except Exception as e:
        logger.error(f"Error obteniendo dispositivos: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    """Obtener un dispositivo específico"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM physical_devices WHERE device_id = ?", (device_id,))
            device_row = cursor.fetchone()
            
            if not device_row:
                return {"success": False, "error": "Dispositivo no encontrado"}
            
            device = dict(device_row)
        
        return {
            "success": True,
            "device": device
        }
    except Exception as e:
        logger.error(f"Error obteniendo dispositivo: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/devices")
async def create_device(device: DeviceCreate):
    """Crear nuevo dispositivo"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO physical_devices (device_id, device_name, device_type, location, venue, description, active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                device.device_id, device.device_name, device.device_type,
                device.location, device.venue, device.description, device.active
            ))
            conn.commit()
            device_id = cursor.lastrowid
            
            # Obtener el dispositivo creado
            cursor.execute("SELECT * FROM physical_devices WHERE id = ?", (device_id,))
            new_device = dict(cursor.fetchone())
        
        logger.info(f"Dispositivo creado: {device.device_id}")
        return {
            "success": True,
            "message": "Dispositivo creado exitosamente",
            "device": new_device
        }
    except sqlite3.IntegrityError:
        return {"success": False, "error": "El ID del dispositivo ya existe"}
    except Exception as e:
        logger.error(f"Error creando dispositivo: {e}")
        return {"success": False, "error": str(e)}

@app.put("/api/devices/{device_id}")
async def update_device(device_id: str, device_update: DeviceUpdate):
    """Actualizar dispositivo existente"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que el dispositivo existe
            cursor.execute("SELECT id FROM physical_devices WHERE device_id = ?", (device_id,))
            if not cursor.fetchone():
                return {"success": False, "error": "Dispositivo no encontrado"}
            
            # Construir query de actualización dinámicamente
            update_fields = []
            values = []
            
            if device_update.device_name is not None:
                update_fields.append("device_name = ?")
                values.append(device_update.device_name)
            if device_update.device_type is not None:
                update_fields.append("device_type = ?")
                values.append(device_update.device_type)
            if device_update.location is not None:
                update_fields.append("location = ?")
                values.append(device_update.location)
            if device_update.venue is not None:
                update_fields.append("venue = ?")
                values.append(device_update.venue)
            if device_update.description is not None:
                update_fields.append("description = ?")
                values.append(device_update.description)
            if device_update.active is not None:
                update_fields.append("active = ?")
                values.append(device_update.active)
            
            if not update_fields:
                return {"success": False, "error": "No hay campos para actualizar"}
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(device_id)
            
            query = f"UPDATE physical_devices SET {', '.join(update_fields)} WHERE device_id = ?"
            cursor.execute(query, values)
            conn.commit()
<<<<<<< HEAD
        
        logger.info(f"Dispositivo actualizado: {device_id}")
        return {"success": True, "message": "Dispositivo actualizado exitosamente"}
=======
            
            # Obtener el dispositivo actualizado
            cursor.execute("SELECT * FROM physical_devices WHERE device_id = ?", (device_id,))
            updated_device = dict(cursor.fetchone())
        
        logger.info(f"Dispositivo actualizado: {device_id}")
        return {
            "success": True, 
            "message": "Dispositivo actualizado exitosamente",
            "device": updated_device
        }
>>>>>>> fb48b359afc889170368b7375b332b1c3585d2ab
    except Exception as e:
        logger.error(f"Error actualizando dispositivo: {e}")
        return {"success": False, "error": str(e)}

<<<<<<< HEAD
@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    """Obtener un dispositivo específico"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM physical_devices 
                WHERE device_id = ?
            """, (device_id,))
            device = cursor.fetchone()
            
            if not device:
                return {"success": False, "error": "Dispositivo no encontrado"}
            
            return {
                "success": True,
                "device": dict(device)
            }
    except Exception as e:
        logger.error(f"Error obteniendo dispositivo: {e}")
        return {"success": False, "error": str(e)}
    
@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str):
    """Eliminar dispositivo FÍSICAMENTE de la base de datos"""
=======
@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str):
    """Eliminar dispositivo completamente"""
>>>>>>> fb48b359afc889170368b7375b332b1c3585d2ab
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que el dispositivo existe
<<<<<<< HEAD
            cursor.execute("SELECT id FROM physical_devices WHERE device_id = ?", (device_id,))
            device_record = cursor.fetchone()
            if not device_record:
                return {"success": False, "error": "Dispositivo no encontrado"}
            
            # ELIMINAR FÍSICAMENTE el registro (no solo desactivar)
            cursor.execute("""
                DELETE FROM physical_devices 
                WHERE device_id = ?
            """, (device_id,))
            
            # También limpiar scans relacionados (opcional - para mantener integridad)
            # cursor.execute("DELETE FROM scans WHERE device_id = ?", (device_id,))
            
            conn.commit()
        
        logger.info(f"Dispositivo ELIMINADO FÍSICAMENTE: {device_id}")
        return {"success": True, "message": "Dispositivo eliminado permanentemente"}
    except Exception as e:
        logger.error(f"Error eliminando dispositivo físicamente: {e}")
        return {"success": False, "error": str(e)}
    
# ================================
# AGREGAR TAMBIÉN este nuevo endpoint para PAUSAR/ACTIVAR
# ================================

@app.patch("/api/devices/{device_id}/toggle-status")
async def toggle_device_status(device_id: str):
    """Alternar estado activo/inactivo del dispositivo (para el botón Pausa)"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener estado actual
            cursor.execute("SELECT active FROM physical_devices WHERE device_id = ?", (device_id,))
            result = cursor.fetchone()
            if not result:
                return {"success": False, "error": "Dispositivo no encontrado"}
            
            current_active = result["active"]
            new_active = 0 if current_active == 1 else 1
            
            # Cambiar estado
            cursor.execute("""
                UPDATE physical_devices 
                SET active = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE device_id = ?
            """, (new_active, device_id))
            
            conn.commit()
            
            status_text = "activado" if new_active == 1 else "pausado"
        
        logger.info(f"Dispositivo {status_text}: {device_id}")
        return {
            "success": True, 
            "message": f"Dispositivo {status_text} exitosamente",
            "active": new_active
        }
    except Exception as e:
        logger.error(f"Error cambiando estado del dispositivo: {e}")
=======
            cursor.execute("SELECT id, device_name FROM physical_devices WHERE device_id = ?", (device_id,))
            device_row = cursor.fetchone()
            if not device_row:
                return {"success": False, "error": "Dispositivo no encontrado"}
            
            device_name = device_row["device_name"]
            
            # Eliminar el dispositivo completamente
            cursor.execute("DELETE FROM physical_devices WHERE device_id = ?", (device_id,))
            
            if cursor.rowcount == 0:
                return {"success": False, "error": "No se pudo eliminar el dispositivo"}
            
            conn.commit()
        
        logger.info(f"Dispositivo eliminado: {device_id} - {device_name}")
        return {
            "success": True, 
            "message": f"Dispositivo '{device_name}' eliminado exitosamente"
        }
    except Exception as e:
        logger.error(f"Error eliminando dispositivo: {e}")
>>>>>>> fb48b359afc889170368b7375b332b1c3585d2ab
        return {"success": False, "error": str(e)}

# ================================
# APIs DE ANALYTICS
# ================================

@app.get("/api/analytics/dashboard")
async def get_dashboard_analytics():
    """Obtener datos completos para el dashboard"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Estadísticas generales
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM campaigns WHERE active = 1) as active_campaigns,
                    (SELECT COUNT(*) FROM physical_devices WHERE active = 1) as active_devices,
                    (SELECT COUNT(*) FROM scans) as total_scans,
                    (SELECT COUNT(*) FROM scans WHERE redirect_completed = 1) as completed_redirects,
                    (SELECT COUNT(DISTINCT client) FROM scans WHERE client != '') as total_clients
            """)
            stats = dict(cursor.fetchone())
            
            # Estadísticas por campaña
            cursor.execute("""
                SELECT 
                    s.campaign_code as campaign,
                    s.client,
                    COUNT(*) as scans,
                    COUNT(CASE WHEN s.redirect_completed = 1 THEN 1 END) as completions,
                    ROUND(AVG(s.duration_seconds), 2) as avg_duration,
                    MAX(s.scan_timestamp) as last_scan
                FROM scans s
                GROUP BY s.campaign_code, s.client
                ORDER BY scans DESC
                LIMIT 10
            """)
            campaigns = [dict(row) for row in cursor.fetchall()]
            
            # Dispositivos de usuarios
            cursor.execute("""
                SELECT user_device_type as device_type, browser, operating_system, COUNT(*) as count
                FROM scans 
                WHERE user_device_type IS NOT NULL
                GROUP BY user_device_type, browser, operating_system
                ORDER BY count DESC
                LIMIT 10
            """)
            user_devices = [dict(row) for row in cursor.fetchall()]
            
            # Dispositivos físicos
            cursor.execute("""
                SELECT 
                    pd.device_id,
                    pd.device_name,
                    pd.location,
                    pd.venue,
                    pd.device_type,
                    COUNT(s.id) as scans,
                    COUNT(CASE WHEN s.redirect_completed = 1 THEN 1 END) as completions,
                    ROUND(AVG(s.duration_seconds), 2) as avg_duration
                FROM physical_devices pd
                LEFT JOIN scans s ON pd.device_id = s.device_id
                WHERE pd.active = 1
                GROUP BY pd.id
                ORDER BY scans DESC
                LIMIT 10
            """)
            physical_devices = [dict(row) for row in cursor.fetchall()]
            
            # Actividad por horas (últimas 24 horas)
            cursor.execute("""
                SELECT 
                    CAST(strftime('%H', scan_timestamp) AS INTEGER) as hour,
                    COUNT(*) as scans
                FROM scans
                WHERE scan_timestamp >= datetime('now', '-24 hours')
                GROUP BY strftime('%H', scan_timestamp)
                ORDER BY hour
            """)
            hourly = [dict(row) for row in cursor.fetchall()]
            
            # Top venues
            cursor.execute("""
                SELECT 
                    venue,
                    COUNT(*) as scans,
                    COUNT(CASE WHEN redirect_completed = 1 THEN 1 END) as completions,
                    COUNT(DISTINCT device_id) as devices_count
                FROM scans 
                WHERE venue IS NOT NULL AND venue != ''
                GROUP BY venue
                ORDER BY scans DESC
                LIMIT 5
            """)
            venues = [dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "stats": stats,
            "campaigns": campaigns,
            "user_devices": user_devices,
            "physical_devices": physical_devices,
            "hourly": hourly,
            "venues": venues
        }
    except Exception as e:
        logger.error(f"Error obteniendo analytics: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/track/complete")
async def complete_tracking(request: Request):
    """Marcar tracking como completado"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        scan_id = data.get("scan_id")
        completion_time = data.get("completion_time")
        
        if not session_id or not scan_id:
            return {"success": False, "error": "session_id y scan_id requeridos"}
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Calcular duración si es posible
            cursor.execute("""
                SELECT scan_timestamp FROM scans 
                WHERE id = ? AND session_id = ?
            """, (scan_id, session_id))
            result = cursor.fetchone()
            
            duration = None
            if result and completion_time:
                start_time = datetime.fromisoformat(result["scan_timestamp"].replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(completion_time.replace("Z", "+00:00"))
                duration = (end_time - start_time).total_seconds()
            
            # Actualizar el registro
            cursor.execute("""
                UPDATE scans 
                SET redirect_completed = 1, 
                    redirect_timestamp = CURRENT_TIMESTAMP,
                    duration_seconds = ?
                WHERE id = ? AND session_id = ?
            """, (duration, scan_id, session_id))
            conn.commit()
        
        return {"success": True, "message": "Tracking completado"}
    except Exception as e:
        logger.error(f"Error completando tracking: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/analytics/qr-generated")
async def log_qr_generation(qr_log: QRGenerationLog, request: Request):
    """Registrar generación de QR para analytics"""
    try:
        generated_by = qr_log.generated_by or get_client_ip(request)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO qr_generations (campaign_id, physical_device_id, qr_size, generated_by)
                VALUES (?, ?, ?, ?)
            """, (
                qr_log.campaign_id, qr_log.physical_device_id, 
                qr_log.qr_size, generated_by
            ))
            conn.commit()
        
        return {"success": True, "message": "Generación de QR registrada"}
    except Exception as e:
        logger.error(f"Error registrando generación de QR: {e}")
        return {"success": False, "error": str(e)}

# ================================
# APIs ADICIONALES ÚTILES
# ================================

@app.get("/api/scans")
async def get_scans(
    limit: Optional[int] = 50,
    offset: Optional[int] = 0,
    campaign_code: Optional[str] = None,
    device_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Obtener escaneos con filtros opcionales"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Construir query con filtros
            query = "SELECT * FROM scans WHERE 1=1"
            params = []
            
            if campaign_code:
                query += " AND campaign_code = ?"
                params.append(campaign_code)
            
            if device_id:
                query += " AND device_id = ?"
                params.append(device_id)
            
            if start_date:
                query += " AND scan_timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND scan_timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY scan_timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            scans = [dict(row) for row in cursor.fetchall()]
            
            # Contar total de registros
            count_query = query.replace("SELECT *", "SELECT COUNT(*)").split("ORDER BY")[0]
            cursor.execute(count_query, params[:-2])  # Sin limit y offset
            total = cursor.fetchone()[0]
        
        return {
            "success": True,
            "scans": scans,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error obteniendo escaneos: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/campaigns/{campaign_code}/stats")
async def get_campaign_stats(campaign_code: str):
    """Obtener estadísticas específicas de una campaña"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que la campaña existe
            cursor.execute("SELECT * FROM campaigns WHERE campaign_code = ?", (campaign_code,))
            campaign = cursor.fetchone()
            if not campaign:
                return {"success": False, "error": "Campaña no encontrada"}
            
            # Estadísticas básicas
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_scans,
                    COUNT(CASE WHEN redirect_completed = 1 THEN 1 END) as completed_redirects,
                    ROUND(AVG(duration_seconds), 2) as avg_duration,
                    MIN(scan_timestamp) as first_scan,
                    MAX(scan_timestamp) as last_scan,
                    COUNT(DISTINCT ip_address) as unique_visitors,
                    COUNT(DISTINCT device_id) as unique_devices
                FROM scans 
                WHERE campaign_code = ?
            """, (campaign_code,))
            stats = dict(cursor.fetchone())
            
            # Dispositivos más utilizados
            cursor.execute("""
                SELECT device_id, device_name, location, venue, COUNT(*) as scans
                FROM scans 
                WHERE campaign_code = ? AND device_id IS NOT NULL
                GROUP BY device_id
                ORDER BY scans DESC
                LIMIT 5
            """, (campaign_code,))
            top_devices = [dict(row) for row in cursor.fetchall()]
            
            # Tipos de dispositivos de usuarios
            cursor.execute("""
                SELECT user_device_type, COUNT(*) as count
                FROM scans 
                WHERE campaign_code = ?
                GROUP BY user_device_type
                ORDER BY count DESC
            """, (campaign_code,))
            device_types = [dict(row) for row in cursor.fetchall()]
            
            # Actividad por día (últimos 30 días)
            cursor.execute("""
                SELECT 
                    DATE(scan_timestamp) as date,
                    COUNT(*) as scans
                FROM scans
                WHERE campaign_code = ? AND scan_timestamp >= datetime('now', '-30 days')
                GROUP BY DATE(scan_timestamp)
                ORDER BY date
            """, (campaign_code,))
            daily_activity = [dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "campaign": dict(campaign),
            "stats": stats,
            "top_devices": top_devices,
            "device_types": device_types,
            "daily_activity": daily_activity
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de campaña: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/devices/{device_id}/stats")
async def get_device_stats(device_id: str):
    """Obtener estadísticas específicas de un dispositivo"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que el dispositivo existe
            cursor.execute("SELECT * FROM physical_devices WHERE device_id = ?", (device_id,))
            device = cursor.fetchone()
            if not device:
                return {"success": False, "error": "Dispositivo no encontrado"}
            
            # Estadísticas básicas
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_scans,
                    COUNT(CASE WHEN redirect_completed = 1 THEN 1 END) as completed_redirects,
                    ROUND(AVG(duration_seconds), 2) as avg_duration,
                    MIN(scan_timestamp) as first_scan,
                    MAX(scan_timestamp) as last_scan,
                    COUNT(DISTINCT ip_address) as unique_visitors,
                    COUNT(DISTINCT campaign_code) as unique_campaigns
                FROM scans 
                WHERE device_id = ?
            """, (device_id,))
            stats = dict(cursor.fetchone())
            
            # Campañas más escaneadas en este dispositivo
            cursor.execute("""
                SELECT campaign_code, client, COUNT(*) as scans
                FROM scans 
                WHERE device_id = ?
                GROUP BY campaign_code
                ORDER BY scans DESC
                LIMIT 5
            """, (device_id,))
            top_campaigns = [dict(row) for row in cursor.fetchall()]
            
            # Actividad por hora del día
            cursor.execute("""
                SELECT 
                    CAST(strftime('%H', scan_timestamp) AS INTEGER) as hour,
                    COUNT(*) as scans
                FROM scans
                WHERE device_id = ?
                GROUP BY strftime('%H', scan_timestamp)
                ORDER BY hour
            """, (device_id,))
            hourly_activity = [dict(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "device": dict(device),
            "stats": stats,
            "top_campaigns": top_campaigns,
            "hourly_activity": hourly_activity
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de dispositivo: {e}")
        return {"success": False, "error": str(e)}

# ================================
# ENDPOINT PARA EXPORTAR DATOS
# ================================

@app.get("/api/export/scans")
async def export_scans(
    format: str = "json",  # json, csv
    campaign_code: Optional[str] = None,
    device_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Exportar datos de escaneos"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Construir query con filtros
            query = """
                SELECT 
                    s.*,
                    c.client as campaign_client,
                    c.description as campaign_description,
                    pd.device_name,
                    pd.location as device_location,
                    pd.venue as device_venue
                FROM scans s
                LEFT JOIN campaigns c ON s.campaign_code = c.campaign_code
                LEFT JOIN physical_devices pd ON s.device_id = pd.device_id
                WHERE 1=1
            """
            params = []
            
            if campaign_code:
                query += " AND s.campaign_code = ?"
                params.append(campaign_code)
            
            if device_id:
                query += " AND s.device_id = ?"
                params.append(device_id)
            
            if start_date:
                query += " AND s.scan_timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND s.scan_timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY s.scan_timestamp DESC"
            
            cursor.execute(query, params)
            scans = [dict(row) for row in cursor.fetchall()]
        
        if format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            if scans:
                writer = csv.DictWriter(output, fieldnames=scans[0].keys())
                writer.writeheader()
                writer.writerows(scans)
            
            from fastapi.responses import StreamingResponse
            
            def iter_csv():
                output.seek(0)
                yield output.read()
            
            return StreamingResponse(
                iter_csv(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=qr_scans_export.csv"}
            )
        
        return {
            "success": True,
            "data": scans,
            "total": len(scans),
            "export_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error exportando datos: {e}")
        return {"success": False, "error": str(e)}

# ================================
# INICIALIZACIÓN
# ================================

@app.on_event("startup")
async def startup_event():
    """Inicialización al arrancar la aplicación"""
    logger.info("Iniciando QR Tracking System v2.5.0")
    init_database()
    logger.info("Sistema iniciado correctamente")

@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al cerrar la aplicación"""
    logger.info("Cerrando QR Tracking System")

# ================================
# EJECUTAR APLICACIÓN
# ================================

if __name__ == "__main__":
    import uvicorn
    
    # Crear datos de ejemplo si la base de datos está vacía
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM campaigns")
            if cursor.fetchone()[0] == 0:
                logger.info("Creando datos de ejemplo...")
                
                # Campañas de ejemplo
                example_campaigns = [
                    ("promo_verano_2024", "Nike", "https://instagram.com/nike", "Promoción de verano 2024"),
                    ("black_friday_tech", "Samsung", "https://www.samsung.com/ve/promociones", "Black Friday Tech 2024"),
                    ("nuevos_productos", "Coca Cola", "https://instagram.com/cocacola", "Lanzamiento nuevos productos"),
                ]
                
                for campaign_code, client, destination, description in example_campaigns:
                    cursor.execute("""
                        INSERT INTO campaigns (campaign_code, client, destination, description)
                        VALUES (?, ?, ?, ?)
                    """, (campaign_code, client, destination, description))
                
                # Dispositivos de ejemplo
                example_devices = [
                    ("totem_centro_comercial_01", "Totem Principal Entrada", "Totem Interactivo", 
                     "Entrada Principal - Planta Baja", "Centro Comercial Plaza Venezuela"),
                    ("pantalla_food_court", "Pantalla Food Court", "Pantalla LED", 
                     "Área de Comidas", "Centro Comercial Plaza Venezuela"),
                    ("kiosco_metro_plaza_vzla", "Kiosco Metro Plaza Venezuela", "Kiosco Digital", 
                     "Estación Metro Plaza Venezuela", "Metro de Caracas"),
                ]
                
                for device_id, device_name, device_type, location, venue in example_devices:
                    cursor.execute("""
                        INSERT INTO physical_devices (device_id, device_name, device_type, location, venue)
                        VALUES (?, ?, ?, ?, ?)
                    """, (device_id, device_name, device_type, location, venue))
                
                conn.commit()
                logger.info("Datos de ejemplo creados")
    except Exception as e:
        logger.error(f"Error creando datos de ejemplo: {e}")
    
    # Ejecutar servidor
    uvicorn.run(
        "app:app",  # Nombre del archivo principal
        host="0.0.0.0",
        port=8000,
        reload=True,  # Para desarrollo, cambiar a False en producción
        log_level="info"
    )