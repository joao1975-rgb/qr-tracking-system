// Variables globales para el manejo del escáner
let video, canvas, context;
let scanning = false;
let stream = null;
let jsQRReady = false;

// Elementos del DOM que utilizaremos frecuentemente
const startBtn = document.getElementById('start-scan');
const stopBtn = document.getElementById('stop-scan');
const fileInput = document.getElementById('file-input');
const statusDiv = document.getElementById('status');
const modal = document.getElementById('result-modal');
const loadingOverlay = document.getElementById('loading-overlay');

// Función principal que se ejecuta cuando la página está completamente cargada
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado, inicializando aplicación...');
    
    // Verificar disponibilidad de jsQR con reintentos
    checkJsQRAvailability();
});

function checkJsQRAvailability(retries = 10) {
    console.log(`Verificando jsQR... Intentos restantes: ${retries}`);
    
    if (typeof jsQR !== 'undefined') {
        console.log('jsQR disponible:', typeof jsQR);
        jsQRReady = true;
        initializeScanner();
        setupEventListeners();
        return;
    }
    
    if (retries > 0) {
        setTimeout(() => checkJsQRAvailability(retries - 1), 500);
    } else {
        console.error('jsQR no se pudo cargar después de múltiples intentos');
        updateStatus('Error: No se pudo cargar la librería de detección QR. Verifica tu conexión a internet y recarga la página.', 'error');
        if (startBtn) startBtn.disabled = true;
    }
}

function initializeScanner() {
    console.log('Inicializando escáner...');
    
    // Obtener referencias a los elementos de video y canvas
    video = document.getElementById('video');
    canvas = document.getElementById('canvas');
    
    if (!video || !canvas) {
        console.error('Elementos video o canvas no encontrados');
        updateStatus('Error: Elementos de video o canvas no encontrados', 'error');
        return;
    }
    
    context = canvas.getContext('2d');
    
    // Verificar si el navegador soporta getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('getUserMedia no soportado');
        updateStatus('Tu navegador no soporta acceso a la cámara', 'error');
        if (startBtn) startBtn.disabled = true;
        return;
    }
    
    console.log('Escáner inicializado correctamente');
    updateStatus('Presiona "Iniciar Escáner" para comenzar', 'ready');
}

function setupEventListeners() {
    console.log('Configurando event listeners...');
    
    // Event listeners para los botones de control
    if (startBtn) {
        startBtn.addEventListener('click', startScanning);
        console.log('Event listener para start-scan configurado');
    }
    if (stopBtn) {
        stopBtn.addEventListener('click', stopScanning);
        console.log('Event listener para stop-scan configurado');
    }
    
    // Event listener para subir archivos
    if (fileInput) {
        fileInput.addEventListener('change', handleFileUpload);
        console.log('Event listener para file-input configurado');
    }
    
    // Event listeners para el modal
    const closeModal = document.getElementById('close-modal');
    const cancelRedirect = document.getElementById('cancel-redirect');
    const confirmRedirect = document.getElementById('confirm-redirect');
    
    if (closeModal) closeModal.addEventListener('click', hideModal);
    if (cancelRedirect) cancelRedirect.addEventListener('click', hideModal);
    if (confirmRedirect) confirmRedirect.addEventListener('click', handleRedirect);
    
    // Cerrar modal al hacer click fuera de él
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                hideModal();
            }
        });
    }
    
    // Manejar tecla Escape para cerrar modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && modal.style.display === 'flex') {
            hideModal();
        }
    });
    
    console.log('Event listeners configurados correctamente');
}

async function startScanning() {
    if (!jsQRReady) {
        updateStatus('Error: Librería de detección QR no está lista', 'error');
        return;
    }
    
    try {
        console.log('Iniciando cámara...');
        showLoading('Iniciando cámara...');
        
        // Configuración de la cámara con preferencia por la cámara trasera
        const constraints = {
            video: {
                facingMode: { ideal: 'environment' },
                width: { ideal: 640 },
                height: { ideal: 480 }
            }
        };
        
        console.log('Solicitando acceso a la cámara con constraints:', constraints);
        
        // Solicitar acceso a la cámara
        stream = await navigator.mediaDevices.getUserMedia(constraints);
        console.log('Stream obtenido:', stream);
        
        video.srcObject = stream;
        
        // Esperar a que el video esté listo
        await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout esperando metadatos del video'));
            }, 10000);
            
            video.onloadedmetadata = () => {
                clearTimeout(timeout);
                console.log('Metadatos del video cargados:', video.videoWidth, 'x', video.videoHeight);
                resolve();
            };
            
            video.onerror = (error) => {
                clearTimeout(timeout);
                console.error('Error en elemento video:', error);
                reject(error);
            };
        });
        
        // Configurar el canvas con las mismas dimensiones que el video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        console.log('Canvas configurado:', canvas.width, 'x', canvas.height);
        
        scanning = true;
        if (startBtn) startBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'inline-block';
        
        updateStatus('Escanea tu código QR...', 'scanning');
        hideLoading();
        
        console.log('Iniciando bucle de escaneo');
        // Comenzar el bucle de escaneo
        scanLoop();
        
    } catch (error) {
        console.error('Error al acceder a la cámara:', error);
        hideLoading();
        
        let errorMessage = 'Error al acceder a la cámara';
        
        if (error.name === 'NotAllowedError') {
            errorMessage = 'Acceso a la cámara denegado. Por favor, permite el acceso y recarga la página.';
        } else if (error.name === 'NotFoundError') {
            errorMessage = 'No se encontró una cámara en tu dispositivo.';
        } else if (error.name === 'NotSupportedError') {
            errorMessage = 'Tu navegador no soporta acceso a la cámara.';
        } else if (error.name === 'NotReadableError') {
            errorMessage = 'La cámara está siendo usada por otra aplicación.';
        } else {
            errorMessage = `Error de cámara: ${error.message}`;
        }
        
        updateStatus(errorMessage, 'error');
    }
}

function stopScanning() {
    console.log('Deteniendo escáner...');
    scanning = false;
    
    // Detener el stream de video
    if (stream) {
        stream.getTracks().forEach(track => {
            console.log('Deteniendo track:', track.kind);
            track.stop();
        });
        stream = null;
    }
    
    if (video) video.srcObject = null;
    if (startBtn) startBtn.style.display = 'inline-block';
    if (stopBtn) stopBtn.style.display = 'none';
    
    updateStatus('Escáner detenido. Presiona "Iniciar Escáner" para comenzar nuevamente.', 'ready');
    console.log('Escáner detenido correctamente');
}

function scanLoop() {
    if (!scanning || !jsQRReady) {
        console.log('Bucle de escaneo detenido:', { scanning, jsQRReady });
        return;
    }
    
    try {
        if (video.readyState === video.HAVE_ENOUGH_DATA) {
            // Dibujar el frame actual del video en el canvas
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            // Obtener los datos de imagen del canvas
            const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
            
            // Intentar decodificar el código QR
            const code = tryDecodeQR(imageData);
            
            if (code) {
                console.log('Código QR detectado:', code.data);
                stopScanning();
                processQRCode(code.data);
                return;
            }
        }
        
        // Continuar escaneando
        requestAnimationFrame(scanLoop);
        
    } catch (error) {
        console.error('Error en scanLoop:', error);
        // Continuar el bucle incluso si hay errores
        requestAnimationFrame(scanLoop);
    }
}

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) {
        console.log('No se seleccionó archivo');
        return;
    }
    
    if (!jsQRReady) {
        updateStatus('Error: Librería de detección QR no disponible. Recarga la página.', 'error');
        return;
    }
    
    console.log('Archivo seleccionado:', {
        name: file.name,
        type: file.type,
        size: file.size
    });
    
    // Verificar que sea una imagen
    if (!file.type.startsWith('image/')) {
        updateStatus(`Tipo de archivo no válido: ${file.type}. Usa JPG, PNG, WebP o BMP.`, 'error');
        return;
    }
    
    // Verificar tamaño del archivo (máximo 10MB)
    if (file.size > 10 * 1024 * 1024) {
        updateStatus('La imagen es demasiado grande. Máximo 10MB permitido.', 'error');
        return;
    }
    
    showLoading('Procesando imagen...');
    
    try {
        const result = await processImageFile(file);
        
        if (result.success) {
            console.log('Código QR detectado en imagen:', result.data);
            updateStatus('¡Código QR detectado correctamente!', 'scanning');
            processQRCode(result.data);
        } else {
            console.log('No se detectó QR:', result.error);
            updateStatus(result.error, 'error');
        }
        
    } catch (error) {
        console.error('Error procesando imagen:', error);
        updateStatus(`Error inesperado: ${error.message}`, 'error');
    } finally {
        hideLoading();
        fileInput.value = '';
    }
}

function processImageFile(file) {
    return new Promise((resolve) => {
        const img = new Image();
        const imageUrl = URL.createObjectURL(file);
        
        img.onload = function() {
            try {
                console.log(`Imagen cargada: ${img.width}x${img.height} píxeles`);
                
                // Verificar dimensiones mínimas
                if (img.width < 50 || img.height < 50) {
                    URL.revokeObjectURL(imageUrl);
                    resolve({ success: false, error: 'La imagen es demasiado pequeña. Mínimo 50x50 píxeles.' });
                    return;
                }
                
                // Configurar el canvas con las dimensiones de la imagen
                canvas.width = img.width;
                canvas.height = img.height;
                
                // Dibujar la imagen en el canvas
                context.drawImage(img, 0, 0);
                
                // Obtener los datos de imagen
                const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
                console.log(`Datos de imagen obtenidos: ${imageData.data.length} bytes`);
                
                // Intentar decodificar el código QR con múltiples técnicas
                const code = tryDecodeQRAdvanced(imageData);
                
                URL.revokeObjectURL(imageUrl);
                
                if (code) {
                    resolve({ success: true, data: code.data });
                } else {
                    resolve({ 
                        success: false, 
                        error: `No se detectó código QR en la imagen. Verifica que tenga un QR visible y nítido. Dimensiones: ${img.width}x${img.height}px` 
                    });
                }
                
            } catch (processingError) {
                console.error('Error procesando imagen:', processingError);
                URL.revokeObjectURL(imageUrl);
                resolve({ success: false, error: 'Error al procesar los datos de la imagen' });
            }
        };
        
        img.onerror = function(error) {
            console.error('Error cargando imagen:', error);
            URL.revokeObjectURL(imageUrl);
            resolve({ success: false, error: `Error al cargar la imagen: ${file.name}. Verifica que no esté corrupta.` });
        };
        
        img.src = imageUrl;
    });
}

// Función mejorada para intentar decodificar QR con múltiples técnicas
function tryDecodeQR(imageData) {
    if (!jsQRReady || !imageData || !imageData.data) {
        console.error('jsQR no está listo o imageData es inválido');
        return null;
    }
    
    try {
        console.log('Intentando decodificar QR:', {
            width: imageData.width,
            height: imageData.height,
            dataLength: imageData.data.length
        });
        
        // Intento 1: Configuración estándar
        let code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: "dontInvert"
        });
        if (code) {
            console.log('QR detectado con configuración estándar');
            return code;
        }
        
        // Intento 2: Con inversión
        code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: "onlyInvert"
        });
        if (code) {
            console.log('QR detectado con inversión');
            return code;
        }
        
        // Intento 3: Ambas opciones
        code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: "attemptBoth"
        });
        if (code) {
            console.log('QR detectado con ambas opciones');
            return code;
        }
        
        return null;
        
    } catch (error) {
        console.error('Error en tryDecodeQR:', error);
        return null;
    }
}

// Función avanzada de decodificación para imágenes subidas
function tryDecodeQRAdvanced(imageData) {
    if (!jsQRReady || !imageData || !imageData.data) {
        console.error('jsQR no está listo o imageData es inválido');
        return null;
    }
    
    console.log('Iniciando decodificación avanzada...', {
        width: imageData.width,
        height: imageData.height,
        dataLength: imageData.data.length
    });
    
    const techniques = [
        { name: 'estándar', options: { inversionAttempts: "dontInvert" } },
        { name: 'inversión', options: { inversionAttempts: "onlyInvert" } },
        { name: 'dual', options: { inversionAttempts: "attemptBoth" } }
    ];
    
    // Probar técnicas básicas
    for (const technique of techniques) {
        try {
            console.log(`Probando técnica: ${technique.name}`);
            const code = jsQR(imageData.data, imageData.width, imageData.height, technique.options);
            if (code) {
                console.log(`Detectado con técnica: ${technique.name}`);
                return code;
            }
        } catch (error) {
            console.error(`Error con técnica ${technique.name}:`, error);
        }
    }
    
    // Técnicas avanzadas si las básicas fallan
    try {
        // Escala de grises
        console.log('Probando con escala de grises...');
        const grayImageData = convertToGrayscale(imageData);
        let code = jsQR(grayImageData.data, grayImageData.width, grayImageData.height, { 
            inversionAttempts: "attemptBoth" 
        });
        if (code) {
            console.log('Detectado en escala de grises');
            return code;
        }
        
        // Aumentar contraste
        console.log('Probando con mayor contraste...');
        const contrastImageData = increaseContrast(imageData, 1.5);
        code = jsQR(contrastImageData.data, contrastImageData.width, contrastImageData.height, { 
            inversionAttempts: "attemptBoth" 
        });
        if (code) {
            console.log('Detectado con mayor contraste');
            return code;
        }
        
        // Binarización
        console.log('Probando con binarización...');
        const binaryImageData = binarizeImage(imageData);
        code = jsQR(binaryImageData.data, binaryImageData.width, binaryImageData.height, { 
            inversionAttempts: "attemptBoth" 
        });
        if (code) {
            console.log('Detectado con binarización');
            return code;
        }
        
    } catch (error) {
        console.error('Error en técnicas avanzadas:', error);
    }
    
    console.log('No se pudo detectar código QR con ninguna técnica');
    return null;
}

async function processQRCode(qrData) {
    console.log('Procesando código QR:', qrData);
    showLoading('Procesando código QR...');
    
    try {
        const response = await fetch('/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                qr_data: qrData
            })
        });
        
        if (!response.ok) {
            throw new Error(`Error HTTP: ${response.status}`);
        }
        
        const result = await response.json();
        hideLoading();
        
        console.log('Respuesta del servidor:', result);
        
        if (result.success) {
            if (result.redirect_url) {
                showModal(
                    'Código QR Válido',
                    `¿Deseas continuar a: ${result.redirect_url}?`,
                    result.redirect_url
                );
            } else {
                showModal(
                    'Contenido QR',
                    `Contenido: ${result.content}`,
                    null
                );
            }
        } else {
            showModal(
                'Error en el Código QR',
                result.error || 'No se pudo procesar el código QR',
                null
            );
        }
        
    } catch (error) {
        console.error('Error enviando QR al servidor:', error);
        hideLoading();
        showModal(
            'Error de Conexión',
            'No se pudo conectar con el servidor. Verifica tu conexión a internet.',
            null
        );
    }
}

function showModal(title, message, redirectUrl) {
    const modalTitle = document.getElementById('modal-title');
    const modalMessage = document.getElementById('modal-message');
    const confirmBtn = document.getElementById('confirm-redirect');
    
    if (modalTitle) modalTitle.textContent = title;
    if (modalMessage) modalMessage.textContent = message;
    
    if (confirmBtn) {
        if (redirectUrl) {
            confirmBtn.style.display = 'inline-block';
            confirmBtn.onclick = () => window.open(redirectUrl, '_blank');
        } else {
            confirmBtn.style.display = 'none';
        }
    }
    
    if (modal) modal.style.display = 'flex';
}

function hideModal() {
    if (modal) modal.style.display = 'none';
    
    if (!scanning) {
        updateStatus('Presiona "Iniciar Escáner" para escanear otro código', 'ready');
    }
}

function handleRedirect() {
    const confirmBtn = document.getElementById('confirm-redirect');
    if (confirmBtn && confirmBtn.onclick) {
        confirmBtn.onclick();
    }
    hideModal();
}

function updateStatus(message, type) {
    if (!statusDiv) return;
    
    console.log('Status actualizado:', message, type);
    statusDiv.innerHTML = `<p>${message}</p>`;
    statusDiv.className = 'scanner-status';
    
    switch (type) {
        case 'error':
            statusDiv.style.background = 'rgba(239, 68, 68, 0.9)';
            break;
        case 'scanning':
            statusDiv.style.background = 'rgba(34, 197, 94, 0.9)';
            break;
        case 'ready':
            statusDiv.style.background = 'rgba(59, 130, 246, 0.9)';
            break;
        default:
            statusDiv.style.background = 'rgba(0, 0, 0, 0.7)';
    }
}

function showLoading(message = 'Cargando...') {
    if (!loadingOverlay) return;
    
    const loadingText = loadingOverlay.querySelector('p');
    if (loadingText) loadingText.textContent = message;
    loadingOverlay.style.display = 'flex';
    console.log('Mostrando loading:', message);
}

function hideLoading() {
    if (loadingOverlay) loadingOverlay.style.display = 'none';
    console.log('Ocultando loading');
}

// FUNCIONES AUXILIARES PARA PROCESAMIENTO DE IMAGEN

function convertToGrayscale(imageData) {
    const data = new Uint8ClampedArray(imageData.data);
    
    for (let i = 0; i < data.length; i += 4) {
        const gray = Math.round(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
        data[i] = gray;
        data[i + 1] = gray;
        data[i + 2] = gray;
    }
    
    return new ImageData(data, imageData.width, imageData.height);
}

function increaseContrast(imageData, contrast = 1.5) {
    const data = new Uint8ClampedArray(imageData.data);
    const factor = (259 * (contrast * 255 + 255)) / (255 * (259 - contrast * 255));
    
    for (let i = 0; i < data.length; i += 4) {
        data[i] = Math.max(0, Math.min(255, factor * (data[i] - 128) + 128));
        data[i + 1] = Math.max(0, Math.min(255, factor * (data[i + 1] - 128) + 128));
        data[i + 2] = Math.max(0, Math.min(255, factor * (data[i + 2] - 128) + 128));
    }
    
    return new ImageData(data, imageData.width, imageData.height);
}

function binarizeImage(imageData, threshold = 128) {
    const data = new Uint8ClampedArray(imageData.data);
    
    for (let i = 0; i < data.length; i += 4) {
        const gray = Math.round(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
        const binary = gray > threshold ? 255 : 0;
        data[i] = binary;
        data[i + 1] = binary;
        data[i + 2] = binary;
    }
    
    return new ImageData(data, imageData.width, imageData.height);
}

// Manejo de errores globales
window.addEventListener('error', function(event) {
    console.error('Error global:', event.error);
    hideLoading();
    updateStatus('Ha ocurrido un error inesperado', 'error');
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('Promise rechazada:', event.reason);
    hideLoading();
    updateStatus('Error de conexión o procesamiento', 'error');
});

// Detectar dispositivo móvil
function isMobileDevice() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// Optimizaciones para móviles
if (isMobileDevice()) {
    document.addEventListener('DOMContentLoaded', function() {
        const videoElement = document.getElementById('video');
        if (videoElement) {
            videoElement.style.height = '250px';
        }
    });
}