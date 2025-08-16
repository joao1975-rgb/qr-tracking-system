# 📊 Sistema de Tracking QR

Sistema avanzado de tracking y analytics para códigos QR implementado en Caracas, Venezuela.

## 🎯 Objetivo

Crear una landing page intermedia que capture información del dispositivo del usuario que escanea códigos QR configurados, antes de redirigirlos a su destino final (Instagram, páginas web, etc.).

## 🚀 Características

- **Captura de datos del dispositivo:** Tipo, navegador, OS, resolución
- **Tracking temporal:** Fecha, hora, duración en página
- **Geolocalización:** IP y ubicación aproximada
- **Dashboard de estadísticas:** Para anunciantes
- **Generador de códigos QR:** Automático para campañas
- **Base de datos SQLite:** Almacenamiento eficiente

## 📱 URLs del Sistema

- **Página principal:** `https://tu-app.onrender.com/`
- **Tracking:** `https://tu-app.onrender.com/track?campaign=CODIGO`
- **Dashboard:** `https://tu-app.onrender.com/dashboard`
- **Generador QR:** `https://tu-app.onrender.com/generate-qr`

## 🔧 Configuración de Códigos QR

### Formato de URLs para códigos QR:
```
https://tu-app.onrender.com/track?campaign=codigo_campaña
```

### Ejemplos de campañas preconfiguradas:
- `metro_plaza_venezuela` → Coca Cola → Instagram
- `cc_sambil` → Samsung → Sitio web
- `terminal_la_bandera` → McDonald's → Instagram
- `autopista_francisco_fajardo` → Pepsi → Sitio web

## 📊 Datos Capturados

### Información del Dispositivo:
- Tipo de dispositivo (Mobile, Tablet, Desktop)
- Navegador web utilizado
- Sistema operativo
- Resolución de pantalla

### Datos Temporales:
- Fecha y hora del acceso
- Duración en la landing page
- Hora de redirección completada

### Datos de Red:
- Dirección IP
- Página de referencia

### Interacción:
- Si completó la redirección al destino final
- Tiempo de permanencia en la página intermedia

## 🛠 Estructura de Archivos

```
qr-tracking-system/
├── app.py                 # Backend principal con Flask
├── requirements.txt       # Dependencias Python
├── Procfile              # Configuración para Render
├── render.yaml           # Configuración avanzada
├── templates/
│   ├── tracking.html     # Página intermedia
│   ├── dashboard.html    # Panel de estadísticas
│   ├── generate_qr.html  # Generador de códigos
│   └── error.html        # Páginas de error
└── static/
    ├── style.css         # Estilos CSS
    └── script.js         # JavaScript
```

## 🗄 Base de Datos

### Tabla `tracking_data`:
- Datos de cada escaneo QR
- Información del dispositivo
- Timestamps y duración
- Estado de la redirección

### Tabla `campaigns`:
- Configuración de campañas
- Códigos QR y destinos
- Información del cliente
- Estado activo/inactivo

## 📈 Dashboard de Estadísticas

El dashboard proporciona:

- **Estadísticas generales:** Total de escaneos, redirecciones completadas
- **Por campaña:** Rendimiento individual de cada código QR
- **Por dispositivo:** Tipos de dispositivos más utilizados
- **Por horario:** Actividad durante el día
- **Tasa de éxito:** Porcentaje de redirecciones completadas

## 🚀 Despliegue en Render

1. **Crear nuevo Web Service**
2. **Conectar repositorio** de este proyecto
3. **Configurar variables de entorno:**
   - `FLASK_ENV=production`
   - `SECRET_KEY` (generada automáticamente)
4. **Deploy automático**

## 💡 Uso para Anunciantes

1. **Generar QR:** Visitar `/generate-qr`
2. **Descargar imagen:** Del código QR generado
3. **Implementar:** En material publicitario físico
4. **Monitorear:** Estadísticas en `/dashboard`

## 📞 Flujo Completo

```
Usuario escanea QR → Landing intermedia (3 seg) → Captura datos → 
Redirección al destino → Datos guardados → Estadísticas disponibles
```

## 🔐 Seguridad

- Validación de parámetros de entrada
- Protección contra inyección SQL
- Rate limiting en endpoints sensibles
- Logs detallados para auditoría

## 📄 API Endpoints

- `GET /track?campaign=codigo` - Página de tracking
- `POST /collect-data` - Recopilar datos adicionales
- `POST /complete-redirect` - Marcar redirección completada
- `GET /dashboard` - Panel de estadísticas
- `GET /api/campaigns` - Lista de campañas activas

## 🔧 Mantenimiento

- Base de datos SQLite autónoma
- Logs automáticos en Render
- Auto-limpieza de datos antiguos (30 días)
- Backups periódicos recomendados

---

**Desarrollado para campañas QR en Caracas, Venezuela 🇻🇪**