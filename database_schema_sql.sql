-- QR Tracking System - Esquema de Base de Datos Completo
-- Versión: 2.5.0 - Soporte completo para Campañas, Dispositivos y Analytics

-- ===================================
-- 1. TABLA DE CAMPAÑAS
-- ===================================
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

-- Índices para campaigns
CREATE INDEX IF NOT EXISTS idx_campaigns_code ON campaigns(campaign_code);
CREATE INDEX IF NOT EXISTS idx_campaigns_active ON campaigns(active);
CREATE INDEX IF NOT EXISTS idx_campaigns_client ON campaigns(client);

-- ===================================
-- 2. TABLA DE DISPOSITIVOS FÍSICOS
-- ===================================
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

-- Índices para physical_devices
CREATE INDEX IF NOT EXISTS idx_devices_device_id ON physical_devices(device_id);
CREATE INDEX IF NOT EXISTS idx_devices_active ON physical_devices(active);
CREATE INDEX IF NOT EXISTS idx_devices_venue ON physical_devices(venue);
CREATE INDEX IF NOT EXISTS idx_devices_type ON physical_devices(device_type);

-- ===================================
-- 3. TABLA DE TRACKING DE ESCANEOS
-- ===================================
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_code TEXT NOT NULL,
    client TEXT,
    destination TEXT,
    device_id TEXT,
    device_name TEXT,
    location TEXT,
    venue TEXT,
    
    -- Información del dispositivo del usuario (quien escanea)
    user_device_type TEXT, -- Mobile, Tablet, Desktop
    browser TEXT,
    operating_system TEXT,
    screen_resolution TEXT,
    user_agent TEXT,
    
    -- Información de red/conexión
    ip_address TEXT,
    country TEXT,
    city TEXT,
    
    -- Información de la sesión
    session_id TEXT,
    scan_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    redirect_completed BOOLEAN DEFAULT 0,
    redirect_timestamp DATETIME,
    duration_seconds REAL,
    
    -- Referencias a las tablas principales
    campaign_id INTEGER,
    physical_device_id INTEGER,
    
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (physical_device_id) REFERENCES physical_devices(id)
);

-- Índices para scans
CREATE INDEX IF NOT EXISTS idx_scans_campaign ON scans(campaign_code);
CREATE INDEX IF NOT EXISTS idx_scans_device ON scans(device_id);
CREATE INDEX IF NOT EXISTS idx_scans_timestamp ON scans(scan_timestamp);
CREATE INDEX IF NOT EXISTS idx_scans_client ON scans(client);
CREATE INDEX IF NOT EXISTS idx_scans_completed ON scans(redirect_completed);
CREATE INDEX IF NOT EXISTS idx_scans_session ON scans(session_id);

-- ===================================
-- 4. TABLA DE GENERACIONES DE QR (ANALYTICS)
-- ===================================
CREATE TABLE IF NOT EXISTS qr_generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER,
    physical_device_id INTEGER,
    qr_size INTEGER,
    generated_by TEXT, -- IP o identificador de quien generó
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
    FOREIGN KEY (physical_device_id) REFERENCES physical_devices(id)
);

-- Índices para qr_generations
CREATE INDEX IF NOT EXISTS idx_qr_gen_campaign ON qr_generations(campaign_id);
CREATE INDEX IF NOT EXISTS idx_qr_gen_device ON qr_generations(physical_device_id);
CREATE INDEX IF NOT EXISTS idx_qr_gen_timestamp ON qr_generations(generated_at);

-- ===================================
-- 5. DATOS DE EJEMPLO PARA DESARROLLO
-- ===================================

-- Campañas de ejemplo
INSERT OR IGNORE INTO campaigns (campaign_code, client, destination, description, active) VALUES
('promo_verano_2024', 'Nike', 'https://instagram.com/nike', 'Promoción de verano 2024', 1),
('black_friday_tech', 'Samsung', 'https://www.samsung.com/ve/promociones', 'Black Friday Tech 2024', 1),
('nuevos_productos', 'Coca Cola', 'https://instagram.com/cocacola', 'Lanzamiento nuevos productos', 1),
('campaña_deportes', 'Adidas', 'https://www.adidas.com.ve', 'Campaña equipos deportivos', 1),
('promo_electronica', 'LG', 'https://www.lg.com/ve', 'Promoción electrónicos', 0);

-- Dispositivos físicos de ejemplo
INSERT OR IGNORE INTO physical_devices (device_id, device_name, device_type, location, venue, description, active) VALUES
('totem_centro_comercial_01', 'Totem Principal Entrada', 'Totem Interactivo', 'Entrada Principal - Planta Baja', 'Centro Comercial Plaza Venezuela', 'Totem principal en la entrada del centro comercial', 1),
('pantalla_food_court', 'Pantalla Food Court', 'Pantalla LED', 'Área de Comidas', 'Centro Comercial Plaza Venezuela', 'Pantalla LED en el área de comidas', 1),
('kiosco_metro_plaza_vzla', 'Kiosco Metro Plaza Venezuela', 'Kiosco Digital', 'Estación Metro Plaza Venezuela', 'Metro de Caracas', 'Kiosco digital en estación de metro', 1),
('valla_digital_autopista', 'Valla Digital Autopista', 'Valla Digital', 'Autopista Francisco Fajardo', 'Vía Pública', 'Valla publicitaria digital en autopista', 1),
('display_movil_cc_sambil', 'Display Móvil Sambil', 'Display Móvil', 'Lobby Principal', 'Centro Comercial Sambil', 'Display móvil en lobby del Sambil', 1),
('pantalla_universidad_ucv', 'Pantalla Universidad UCV', 'Pantalla LED', 'Biblioteca Central', 'Universidad Central de Venezuela', 'Pantalla informativa en biblioteca', 0);

-- Datos de ejemplo de escaneos (para testing)
INSERT OR IGNORE INTO scans (
    campaign_code, client, destination, device_id, device_name, location, venue,
    user_device_type, browser, operating_system, ip_address, country, city,
    session_id, scan_timestamp, redirect_completed, duration_seconds,
    campaign_id, physical_device_id
) VALUES
('promo_verano_2024', 'Nike', 'https://instagram.com/nike', 'totem_centro_comercial_01', 'Totem Principal Entrada', 'Entrada Principal - Planta Baja', 'Centro Comercial Plaza Venezuela',
 'Mobile', 'Chrome', 'Android', '192.168.1.100', 'Venezuela', 'Caracas', 
 'session_001', '2024-08-20 15:30:00', 1, 12.5, 1, 1),

('black_friday_tech', 'Samsung', 'https://www.samsung.com/ve/promociones', 'pantalla_food_court', 'Pantalla Food Court', 'Área de Comidas', 'Centro Comercial Plaza Venezuela',
 'Mobile', 'Safari', 'iOS', '192.168.1.101', 'Venezuela', 'Caracas',
 'session_002', '2024-08-19 20:15:00', 1, 8.2, 2, 2),

('nuevos_productos', 'Coca Cola', 'https://instagram.com/cocacola', 'kiosco_metro_plaza_vzla', 'Kiosco Metro Plaza Venezuela', 'Estación Metro Plaza Venezuela', 'Metro de Caracas',
 'Desktop', 'Chrome', 'Windows', '192.168.1.102', 'Venezuela', 'Caracas',
 'session_003', '2024-08-18 11:45:00', 1, 15.8, 3, 3);

-- ===================================
-- 6. VISTAS PARA ANALYTICS
-- ===================================

-- Vista de estadísticas por campaña
CREATE VIEW IF NOT EXISTS campaign_stats AS
SELECT 
    c.id,
    c.campaign_code,
    c.client,
    c.destination,
    c.description,
    c.active,
    COUNT(s.id) as total_scans,
    COUNT(CASE WHEN s.redirect_completed = 1 THEN 1 END) as completed_redirects,
    ROUND(AVG(s.duration_seconds), 2) as avg_duration,
    MAX(s.scan_timestamp) as last_scan,
    ROUND(
        (COUNT(CASE WHEN s.redirect_completed = 1 THEN 1 END) * 100.0) / 
        NULLIF(COUNT(s.id), 0), 2
    ) as success_rate
FROM campaigns c
LEFT JOIN scans s ON c.id = s.campaign_id OR c.campaign_code = s.campaign_code
GROUP BY c.id, c.campaign_code, c.client, c.destination, c.description, c.active;

-- Vista de estadísticas por dispositivo físico
CREATE VIEW IF NOT EXISTS device_stats AS
SELECT 
    pd.id,
    pd.device_id,
    pd.device_name,
    pd.device_type,
    pd.location,
    pd.venue,
    pd.active,
    COUNT(s.id) as total_scans,
    COUNT(CASE WHEN s.redirect_completed = 1 THEN 1 END) as completed_redirects,
    ROUND(AVG(s.duration_seconds), 2) as avg_duration,
    MAX(s.scan_timestamp) as last_scan,
    ROUND(
        (COUNT(CASE WHEN s.redirect_completed = 1 THEN 1 END) * 100.0) / 
        NULLIF(COUNT(s.id), 0), 2
    ) as success_rate
FROM physical_devices pd
LEFT JOIN scans s ON pd.id = s.physical_device_id OR pd.device_id = s.device_id
GROUP BY pd.id, pd.device_id, pd.device_name, pd.device_type, pd.location, pd.venue, pd.active;

-- Vista de dispositivos de usuarios más comunes
CREATE VIEW IF NOT EXISTS user_device_stats AS
SELECT 
    user_device_type,
    browser,
    operating_system,
    COUNT(*) as scan_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM scans), 2) as percentage
FROM scans 
WHERE user_device_type IS NOT NULL
GROUP BY user_device_type, browser, operating_system
ORDER BY scan_count DESC;

-- Vista de actividad por horas
CREATE VIEW IF NOT EXISTS hourly_activity AS
SELECT 
    strftime('%H', scan_timestamp) as hour,
    COUNT(*) as scan_count,
    COUNT(CASE WHEN redirect_completed = 1 THEN 1 END) as completed_count
FROM scans
WHERE scan_timestamp >= datetime('now', '-24 hours')
GROUP BY strftime('%H', scan_timestamp)
ORDER BY hour;

-- Vista de top venues
CREATE VIEW IF NOT EXISTS venue_stats AS
SELECT 
    venue,
    COUNT(*) as total_scans,
    COUNT(CASE WHEN redirect_completed = 1 THEN 1 END) as completed_redirects,
    COUNT(DISTINCT device_id) as devices_count,
    ROUND(AVG(duration_seconds), 2) as avg_duration
FROM scans 
WHERE venue IS NOT NULL AND venue != ''
GROUP BY venue
ORDER BY total_scans DESC;

-- ===================================
-- 7. TRIGGERS PARA MANTENER DATOS ACTUALIZADOS
-- ===================================

-- Trigger para actualizar updated_at en campaigns
CREATE TRIGGER IF NOT EXISTS update_campaigns_timestamp 
AFTER UPDATE ON campaigns
FOR EACH ROW
BEGIN
    UPDATE campaigns SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger para actualizar updated_at en physical_devices
CREATE TRIGGER IF NOT EXISTS update_devices_timestamp 
AFTER UPDATE ON physical_devices
FOR EACH ROW
BEGIN
    UPDATE physical_devices SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger para vincular campaign_id automáticamente en scans
CREATE TRIGGER IF NOT EXISTS link_campaign_id_in_scans
AFTER INSERT ON scans
FOR EACH ROW
WHEN NEW.campaign_id IS NULL
BEGIN
    UPDATE scans 
    SET campaign_id = (SELECT id FROM campaigns WHERE campaign_code = NEW.campaign_code LIMIT 1)
    WHERE id = NEW.id;
END;

-- Trigger para vincular physical_device_id automáticamente en scans
CREATE TRIGGER IF NOT EXISTS link_device_id_in_scans
AFTER INSERT ON scans
FOR EACH ROW
WHEN NEW.physical_device_id IS NULL
BEGIN
    UPDATE scans 
    SET physical_device_id = (SELECT id FROM physical_devices WHERE device_id = NEW.device_id LIMIT 1)
    WHERE id = NEW.id;
END;

-- ===================================
-- 8. CONSULTAS DE VERIFICACIÓN
-- ===================================

-- Verificar que todo se creó correctamente
SELECT 'Tabla campaigns creada: ' || COUNT(*) || ' registros' FROM campaigns;
SELECT 'Tabla physical_devices creada: ' || COUNT(*) || ' registros' FROM physical_devices;
SELECT 'Tabla scans creada: ' || COUNT(*) || ' registros' FROM scans;
SELECT 'Tabla qr_generations creada' AS status;

-- Mostrar estadísticas de ejemplo
SELECT 'ESTADÍSTICAS POR CAMPAÑA:' as section;
SELECT * FROM campaign_stats LIMIT 5;

SELECT 'ESTADÍSTICAS POR DISPOSITIVO:' as section;
SELECT * FROM device_stats LIMIT 5;

SELECT 'DISPOSITIVOS DE USUARIOS MÁS COMUNES:' as section;
SELECT * FROM user_device_stats LIMIT 5;

-- ===================================
-- 9. INFORMACIÓN ADICIONAL
-- ===================================

-- Para obtener estadísticas generales del sistema:
-- SELECT 
--     (SELECT COUNT(*) FROM campaigns WHERE active = 1) as active_campaigns,
--     (SELECT COUNT(*) FROM physical_devices WHERE active = 1) as active_devices,
--     (SELECT COUNT(*) FROM scans) as total_scans,
--     (SELECT COUNT(*) FROM scans WHERE redirect_completed = 1) as completed_redirects;

-- Para limpiar datos de prueba (NO ejecutar en producción):
-- DELETE FROM scans;
-- DELETE FROM qr_generations;
-- UPDATE campaigns SET id = NULL;
-- UPDATE physical_devices SET id = NULL;