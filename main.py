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
        # Leer el arch
