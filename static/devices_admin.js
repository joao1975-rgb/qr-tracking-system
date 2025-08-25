// ================================
// ADMINISTRACIÓN DE DISPOSITIVOS
// ================================

// Variables globales para manejo de dispositivos
const API_BASE = window.location.origin;
let devices = [];
let editingDeviceId = null;

// Estado de la interfaz
let isLoading = false;
let lastUpdateTime = null;

// ================================
// FUNCIONES DE API
// ================================

// Cargar todos los dispositivos
async function loadDevices() {
    if (isLoading) return;
    
    isLoading = true;
    showLoadingSpinner('Cargando dispositivos...');
    
    try {
        const response = await fetch(`${API_BASE}/api/devices`);
        const data = await response.json();
        
        if (data.success) {
            devices = data.devices || [];
            renderDevicesList(devices);
            lastUpdateTime = new Date();
            showAlert(`✅ ${devices.length} dispositivos cargados exitosamente`, 'success');
        } else {
            throw new Error(data.error || 'Error cargando dispositivos');
        }
    } catch (error) {
        console.error('Error loading devices:', error);
        showAlert('❌ Error cargando dispositivos: ' + error.message, 'error');
        renderDevicesList([]); // Mostrar lista vacía
    } finally {
        isLoading = false;
        hideLoadingSpinner();
    }
}

// Crear nuevo dispositivo
async function createDevice(deviceData) {
    try {
        const response = await fetch(`${API_BASE}/api/devices`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(deviceData)
        });

        const data = await response.json();
        
        if (data.success) {
            await loadDevices(); // Recargar lista
            return { success: true, message: 'Dispositivo creado exitosamente' };
        } else {
            throw new Error(data.error || 'Error creando dispositivo');
        }
    } catch (error) {
        console.error('Error creating device:', error);
        return { success: false, message: error.message };
    }
}

// Actualizar dispositivo existente
async function updateDevice(deviceId, deviceData) {
    try {
        const response = await fetch(`${API_BASE}/api/devices/${deviceId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(deviceData)
        });

        const data = await response.json();
        
        if (data.success) {
            await loadDevices(); // Recargar lista
            return { success: true, message: 'Dispositivo actualizado exitosamente' };
        } else {
            throw new Error(data.error || 'Error actualizando dispositivo');
        }
    } catch (error) {
        console.error('Error updating device:', error);
        return { success: false, message: error.message };
    }
}

// Eliminar dispositivo
async function deleteDevice(deviceId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este dispositivo?')) {
        return { success: false, message: 'Eliminación cancelada' };
    }

    try {
        const response = await fetch(`${API_BASE}/api/devices/${deviceId}`, {
            method: 'DELETE'
        });

        const data = await response.json();
        
        if (data.success) {
            await loadDevices(); // Recargar lista
            return { success: true, message: 'Dispositivo eliminado exitosamente' };
        } else {
            throw new Error(data.error || 'Error eliminando dispositivo');
        }
    } catch (error) {
        console.error('Error deleting device:', error);
        return { success: false, message: error.message };
    }
}

// ================================
// FUNCIONES DE INTERFAZ
// ================================

// Renderizar lista de dispositivos
function renderDevicesList(devicesList) {
    const container = document.getElementById('devicesList') || document.getElementById('devices-container');
    
    if (!container) {
        console.error('Container de dispositivos no encontrado');
        return;
    }

    if (!devicesList || devicesList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🖥️</div>
                <h3>No hay dispositivos registrados</h3>
                <p>Agrega tu primer dispositivo usando el formulario de arriba</p>
                <button onclick="showAddDeviceForm()" class="btn btn-primary">
                    ➕ Agregar Primer Dispositivo
                </button>
            </div>
        `;
        return;
    }

    const devicesHtml = devicesList.map(device => `
        <div class="device-card ${device.active ? 'active' : 'inactive'}" data-device-id="${device.device_id}">
            <div class="device-header">
                <h4>${escapeHtml(device.device_name || device.device_id)}</h4>
                <div class="device-status ${device.active ? 'status-active' : 'status-inactive'}">
                    ${device.active ? '✅ Activo' : '❌ Inactivo'}
                </div>
            </div>
            
            <div class="device-info">
                <div class="info-item">
                    <strong>ID:</strong> 
                    <span class="device-id">${escapeHtml(device.device_id)}</span>
                </div>
                <div class="info-item">
                    <strong>Tipo:</strong> 
                    <span>${escapeHtml(device.device_type || 'N/A')}</span>
                </div>
                <div class="info-item">
                    <strong>Ubicación:</strong> 
                    <span>${escapeHtml(device.location || 'N/A')}</span>
                </div>
                <div class="info-item">
                    <strong>Venue:</strong> 
                    <span>${escapeHtml(device.venue || 'N/A')}</span>
                </div>
                ${device.created_at ? `
                <div class="info-item">
                    <strong>Creado:</strong> 
                    <span>${formatDate(device.created_at)}</span>
                </div>
                ` : ''}
            </div>

            <div class="device-actions">
                <button onclick="selectDeviceForForm('${device.device_id}')" 
                        class="btn btn-sm btn-secondary" title="Usar en formulario">
                    📱 Usar
                </button>
                <button onclick="editDevice('${device.device_id}')" 
                        class="btn btn-sm btn-primary" title="Editar dispositivo">
                    ✏️ Editar
                </button>
                <button onclick="toggleDeviceStatus('${device.device_id}', ${device.active})" 
                        class="btn btn-sm ${device.active ? 'btn-warning' : 'btn-success'}" 
                        title="${device.active ? 'Desactivar' : 'Activar'}">
                    ${device.active ? '⏸️ Pausar' : '▶️ Activar'}
                </button>
                <button onclick="confirmDeleteDevice('${device.device_id}')" 
                        class="btn btn-sm btn-danger" title="Eliminar dispositivo">
                    🗑️ Eliminar
                </button>
            </div>
        </div>
    `).join('');

    container.innerHTML = devicesHtml;
    
    // Actualizar contador si existe
    const counter = document.getElementById('devices-counter');
    if (counter) {
        counter.textContent = `${devicesList.length} dispositivo${devicesList.length !== 1 ? 's' : ''}`;
    }
}

// Mostrar formulario de agregar dispositivo
function showAddDeviceForm() {
    editingDeviceId = null;
    const form = document.getElementById('addDeviceForm') || document.getElementById('device-form');
    
    if (form) {
        form.style.display = 'block';
        clearDeviceForm();
        
        // Cambiar título del formulario
        const title = form.querySelector('h4') || form.querySelector('.form-title');
        if (title) {
            title.textContent = 'Agregar Nuevo Dispositivo';
        }
        
        // Cambiar texto del botón
        const submitBtn = form.querySelector('.btn-primary') || form.querySelector('[onclick*="save"]');
        if (submitBtn) {
            submitBtn.textContent = '💾 Guardar Dispositivo';
        }
        
        // Focus en primer campo
        const firstInput = form.querySelector('input');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

// Editar dispositivo existente
function editDevice(deviceId) {
    const device = devices.find(d => d.device_id === deviceId);
    if (!device) {
        showAlert('❌ Dispositivo no encontrado', 'error');
        return;
    }
    
    editingDeviceId = deviceId;
    const form = document.getElementById('addDeviceForm') || document.getElementById('device-form');
    
    if (form) {
        form.style.display = 'block';
        
        // Llenar formulario con datos existentes
        fillDeviceForm(device);
        
        // Cambiar título del formulario
        const title = form.querySelector('h4') || form.querySelector('.form-title');
        if (title) {
            title.textContent = `Editar: ${device.device_name || device.device_id}`;
        }
        
        // Cambiar texto del botón
        const submitBtn = form.querySelector('.btn-primary') || form.querySelector('[onclick*="save"]');
        if (submitBtn) {
            submitBtn.textContent = '💾 Actualizar Dispositivo';
        }
    }
}

// Seleccionar dispositivo para el formulario principal
function selectDeviceForForm(deviceId) {
    const device = devices.find(d => d.device_id === deviceId);
    if (!device) return;
    
    // Llenar campos del constructor de URLs
    const fields = {
        'device_id': device.device_id,
        'device_name': device.device_name,
        'location': device.location,
        'venue': device.venue,
        'device_type': device.device_type
    };
    
    Object.entries(fields).forEach(([fieldId, value]) => {
        const field = document.getElementById(fieldId);
        if (field && value) {
            field.value = value;
        }
    });
    
    showAlert(`📱 Dispositivo "${device.device_name || device.device_id}" seleccionado`, 'success');
}

// ================================
// FUNCIONES DE UTILIDAD
// ================================

// Escape HTML para prevenir XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Formatear fecha
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        return new Date(dateString).toLocaleDateString('es-ES', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return dateString;
    }
}

// Mostrar spinner de carga
function showLoadingSpinner(message = 'Cargando...') {
    let spinner = document.getElementById('loading-spinner');
    
    if (!spinner) {
        spinner = document.createElement('div');
        spinner.id = 'loading-spinner';
        spinner.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4f46e5;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            z-index: 1000;
            font-weight: 600;
        `;
        document.body.appendChild(spinner);
    }
    
    spinner.textContent = message;
    spinner.style.display = 'block';
}

// Ocultar spinner de carga
function hideLoadingSpinner() {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.style.display = 'none';
    }
}

// ================================
// INICIALIZACIÓN
// ================================

// Cargar dispositivos al iniciar
document.addEventListener('DOMContentLoaded', function() {
    console.log('🖥️ Dispositivos Admin - Inicializando...');
    
    // Cargar dispositivos automáticamente
    loadDevices();
    
    // Configurar auto-refresh cada 2 minutos
    setInterval(() => {
        if (!isLoading && !editingDeviceId) {
            loadDevices();
        }
    }, 120000);
    
    console.log('✅ Sistema de dispositivos inicializado');
});

// Exportar funciones para uso global
window.DevicesAdmin = {
    loadDevices,
    createDevice,
    updateDevice,
    deleteDevice,
    showAddDeviceForm,
    editDevice,
    selectDeviceForForm,
    devices: () => devices,
    isLoading: () => isLoading
};