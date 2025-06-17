/**
 * Enhanced Socket.IO Client Manager
 * Handles real-time updates and notifications for the Hostel Management System
 */

class SocketManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.connectionHealthInterval = null;
        this.eventListeners = {};
        this.messageQueue = [];
        
        this.init();
    }
    
    init() {
        console.log('Initializing Socket.IO connection...');
        
        // Initialize socket connection
        this.socket = io('/updates', {
            transports: ['websocket', 'polling'],
            upgrade: true,
            rememberUpgrade: true,
            timeout: 20000,
            forceNew: false,
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            maxReconnectionAttempts: this.maxReconnectAttempts
        });
        
        this.setupEventListeners();
        this.startConnectionHealthCheck();
    }
    
    setupEventListeners() {
        // Connection events
        this.socket.on('connect', () => {
            console.log('Connected to real-time updates');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.showConnectionStatus('Connected', 'success');
            this.processMessageQueue();
            this.emit('connected');
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from real-time updates:', reason);
            this.isConnected = false;
            this.showConnectionStatus('Disconnected', 'error');
            this.emit('disconnected', reason);
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Socket.IO connection error:', error);
            this.reconnectAttempts++;
            
            if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                this.showConnectionStatus('Connection failed', 'error');
                this.emit('connection_failed');
            } else {
                this.showConnectionStatus(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'warning');
            }
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`Reconnected after ${attemptNumber} attempts`);
            this.showConnectionStatus('Reconnected', 'success');
            this.emit('reconnected');
        });
        
        // Application-specific events
        this.setupApplicationEvents();
    }
    
    setupApplicationEvents() {
        // Dashboard updates
        this.socket.on('dashboard_stats_updated', (data) => {
            console.log('Dashboard stats updated:', data);
            this.emit('dashboard_update', data);
            if (typeof updateDashboardStats === 'function') {
                updateDashboardStats(data.stats);
            }
        });
        
        // Fee events
        this.socket.on('fee_added', (data) => {
            this.showNotification(`New fee added: $${data.amount} for ${data.student_name}`, 'info');
            this.emit('fee_added', data);
        });
        
        this.socket.on('fee_paid', (data) => {
            this.showNotification(`Fee payment received: $${data.amount} from ${data.student_name}`, 'success');
            this.emit('fee_paid', data);
            this.refreshFeesIfVisible();
        });
        
        this.socket.on('fee_updated', (data) => {
            this.showNotification(`Fee updated for ${data.student_name}: $${data.amount}`, 'info');
            this.emit('fee_updated', data);
            this.refreshFeesIfVisible();
        });
        
        this.socket.on('fee_deleted', (data) => {
            this.showNotification(`Fee deleted: $${data.amount} for ${data.student_name}`, 'info');
            this.emit('fee_deleted', data);
            this.refreshFeesIfVisible();
        });
        
        this.socket.on('fees_batch_added', (data) => {
            this.showNotification(`Batch fees added: $${data.amount} each for ${data.count} students`, 'success');
            this.emit('fees_batch_added', data);
        });
        
        this.socket.on('fees_updated', (data) => {
            this.showNotification(`${data.count} overdue fees were updated`, 'info');
            this.emit('fees_updated', data);
        });
        
        // Student events
        this.socket.on('student_added', (data) => {
            this.showNotification(`New student added: ${data.name}`, 'success');
            this.emit('student_added', data);
            this.refreshStudentsIfVisible();
        });
        
        this.socket.on('student_updated', (data) => {
            this.showNotification(`Student updated: ${data.name}`, 'info');
            this.emit('student_updated', data);
            this.refreshStudentsIfVisible();
        });
        
        this.socket.on('student_deleted', (data) => {
            this.showNotification(`Student deleted: ${data.name}`, 'info');
            this.emit('student_deleted', data);
            this.refreshStudentsIfVisible();
        });
        
        this.socket.on('student_room_transfer', (data) => {
            const message = data.old_room_number ? 
                `${data.student_name} transferred from Room ${data.old_room_number} to Room ${data.new_room_number}` :
                `${data.student_name} assigned to Room ${data.new_room_number}`;
            this.showNotification(message, 'info');
            this.emit('student_room_transfer', data);
        });
        
        this.socket.on('students_bulk_transfer', (data) => {
            this.showNotification(`Bulk transfer: ${data.count} students transferred`, 'info');
            this.emit('students_bulk_transfer', data);
        });
        
        // Room events
        this.socket.on('room_added', (data) => {
            this.showNotification(`New room added: ${data.room_number}`, 'success');
            this.emit('room_added', data);
            this.refreshRoomsIfVisible();
        });
        
        this.socket.on('room_status_changed', (data) => {
            this.showNotification(`Room ${data.room_number} status changed to ${data.status}`, 'info');
            this.emit('room_status_changed', data);
            this.refreshRoomsIfVisible();
        });
        
        this.socket.on('room_deleted', (data) => {
            this.showNotification(`Room deleted: ${data.room_number}`, 'info');
            this.emit('room_deleted', data);
            this.refreshRoomsIfVisible();
        });
        
        this.socket.on('rooms_bulk_updated', (data) => {
            this.showNotification(`Bulk room update: ${data.count} rooms updated to ${data.new_status}`, 'info');
            this.emit('rooms_bulk_updated', data);
        });
        
        // Complaint events
        this.socket.on('new_complaint', (data) => {
            this.showNotification(`New complaint: ${data.message}`, 'warning');
            this.emit('new_complaint', data);
            this.refreshComplaintsIfVisible();
        });
        
        this.socket.on('complaint_updated', (data) => {
            this.showNotification(`Complaint updated: ${data.message}`, 'info');
            this.emit('complaint_updated', data);
            this.refreshComplaintsIfVisible();
        });
        
        this.socket.on('complaint_deleted', (data) => {
            this.showNotification(`Complaint deleted: ${data.message}`, 'info');
            this.emit('complaint_deleted', data);
            this.refreshComplaintsIfVisible();
        });
        
        // System events
        this.socket.on('system_notification', (data) => {
            this.showNotification(data.message, data.type || 'info');
            this.emit('system_notification', data);
        });
        
        this.socket.on('system_broadcast', (data) => {
            this.showNotification(`${data.sender}: ${data.message}`, 'info', true);
            this.emit('system_broadcast', data);
        });
        
        this.socket.on('system_alert', (data) => {
            this.showNotification(data.message, data.type || 'warning', true);
            this.emit('system_alert', data);
        });
        
        this.socket.on('user_activity', (data) => {
            console.log('User activity:', data);
            this.emit('user_activity', data);
        });
        
        this.socket.on('maintenance_alert', (data) => {
            const priority = data.priority === 'urgent' ? 'error' : 'warning';
            this.showNotification(`Maintenance: ${data.message}`, priority, data.requires_attention);
            this.emit('maintenance_alert', data);
        });
        
        this.socket.on('financial_alert', (data) => {
            this.showNotification(`Financial Alert: ${data.message}`, 'warning', true);
            this.emit('financial_alert', data);
        });
        
        // Health check response
        this.socket.on('pong', (data) => {
            console.log('Connection health check OK:', data.timestamp);
        });
        
        // Error handling
        this.socket.on('error', (error) => {
            console.error('Socket.IO error:', error);
            this.showNotification('Real-time connection error', 'error');
        });
    }
    
    // Event emitter functionality
    on(event, callback) {
        if (!this.eventListeners[event]) {
            this.eventListeners[event] = [];
        }
        this.eventListeners[event].push(callback);
    }
    
    off(event, callback) {
        if (!this.eventListeners[event]) return;
        
        const index = this.eventListeners[event].indexOf(callback);
        if (index > -1) {
            this.eventListeners[event].splice(index, 1);
        }
    }
    
    emit(event, data) {
        if (!this.eventListeners[event]) return;
        
        this.eventListeners[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in event listener for ${event}:`, error);
            }
        });
    }
    
    // Utility methods
    sendMessage(event, data) {
        if (this.isConnected) {
            this.socket.emit(event, data);
        } else {
            this.messageQueue.push({ event, data });
            console.log('Message queued - not connected');
        }
    }
    
    processMessageQueue() {
        while (this.messageQueue.length > 0) {
            const { event, data } = this.messageQueue.shift();
            this.socket.emit(event, data);
        }
    }
    
    joinHostelRoom(hostelId) {
        this.sendMessage('join_hostel_room', { hostel_id: hostelId });
    }
    
    leaveHostelRoom(hostelId) {
        this.sendMessage('leave_hostel_room', { hostel_id: hostelId });
    }
    
    requestDashboardUpdate(hostelId = null) {
        this.sendMessage('request_dashboard_update', { hostel_id: hostelId });
    }
    
    subscribeToNotifications(types) {
        this.sendMessage('subscribe_to_notifications', { types });
    }
    
    broadcastMessage(message, target = 'all') {
        this.sendMessage('broadcast_message', { message, target });
    }
    
    startConnectionHealthCheck() {
        this.connectionHealthInterval = setInterval(() => {
            if (this.isConnected) {
                this.socket.emit('ping');
            }
        }, 30000); // Check every 30 seconds
    }
    
    stopConnectionHealthCheck() {
        if (this.connectionHealthInterval) {
            clearInterval(this.connectionHealthInterval);
            this.connectionHealthInterval = null;
        }
    }
    
    showConnectionStatus(message, type) {
        // Create or update connection status indicator
        let statusEl = document.getElementById('connection-status');
        if (!statusEl) {
            statusEl = document.createElement('div');
            statusEl.id = 'connection-status';
            statusEl.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                z-index: 10000;
                transition: all 0.3s ease;
            `;
            document.body.appendChild(statusEl);
        }
        
        const colors = {
            success: '#d4edda',
            error: '#f8d7da',
            warning: '#fff3cd',
            info: '#d1ecf1'
        };
        
        statusEl.textContent = message;
        statusEl.style.backgroundColor = colors[type] || colors.info;
        statusEl.style.display = 'block';
        
        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => {
                statusEl.style.display = 'none';
            }, 3000);
        }
    }
    
    showNotification(message, type = 'info', persistent = false) {
        // Use existing notification system if available
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            // Fallback notification
            console.log(`Notification [${type}]: ${message}`);
        }
        
        // For persistent notifications, also show browser notification if permitted
        if (persistent && 'Notification' in window && Notification.permission === 'granted') {
            new Notification('Hostel Management System', {
                body: message,
                icon: '/static/favicon.ico'
            });
        }
    }
    
    // Page-specific refresh functions
    refreshFeesIfVisible() {
        if (window.location.pathname.includes('/fees') && typeof refreshFeesTable === 'function') {
            setTimeout(refreshFeesTable, 1000);
        }
    }
    
    refreshStudentsIfVisible() {
        if (window.location.pathname.includes('/students') && typeof refreshStudentsTable === 'function') {
            setTimeout(refreshStudentsTable, 1000);
        }
    }
    
    refreshRoomsIfVisible() {
        if (window.location.pathname.includes('/rooms') && typeof refreshRoomsTable === 'function') {
            setTimeout(refreshRoomsTable, 1000);
        }
    }
    
    refreshComplaintsIfVisible() {
        if (window.location.pathname.includes('/complaints') && typeof refreshComplaintsTable === 'function') {
            setTimeout(refreshComplaintsTable, 1000);
        }
    }
    
    // Cleanup
    destroy() {
        this.stopConnectionHealthCheck();
        if (this.socket) {
            this.socket.disconnect();
        }
        this.eventListeners = {};
        this.messageQueue = [];
    }
}

// Initialize socket manager when DOM is ready
let socketManager;

document.addEventListener('DOMContentLoaded', function() {
    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    // Initialize socket manager
    socketManager = new SocketManager();
    
    // Make it globally available
    window.socketManager = socketManager;
    
    // Setup page-specific event listeners
    setupPageSpecificListeners();
});

function setupPageSpecificListeners() {
    // Dashboard specific
    if (window.location.pathname === '/' || window.location.pathname.includes('/dashboard')) {
        socketManager.on('dashboard_update', (data) => {
            console.log('Dashboard update received');
            // Update dashboard elements if they exist
        });
        
        // Request initial dashboard update
        socketManager.requestDashboardUpdate();
    }
    
    // Auto-refresh tables when data changes
    socketManager.on('fee_added', () => setTimeout(refreshPageIfNeeded, 500));
    socketManager.on('fee_updated', () => setTimeout(refreshPageIfNeeded, 500));
    socketManager.on('fee_deleted', () => setTimeout(refreshPageIfNeeded, 500));
    socketManager.on('student_added', () => setTimeout(refreshPageIfNeeded, 500));
    socketManager.on('student_updated', () => setTimeout(refreshPageIfNeeded, 500));
    socketManager.on('room_added', () => setTimeout(refreshPageIfNeeded, 500));
    socketManager.on('room_status_changed', () => setTimeout(refreshPageIfNeeded, 500));
}

function refreshPageIfNeeded() {
    // Only refresh if user hasn't interacted recently
    const lastInteraction = sessionStorage.getItem('lastUserInteraction');
    const now = Date.now();
    
    if (!lastInteraction || (now - parseInt(lastInteraction)) > 5000) {
        // Check if we're on a data table page and refresh accordingly
        if (document.querySelector('table')) {
            location.reload();
        }
    }
}

// Track user interactions to avoid refreshing during active use
document.addEventListener('click', () => {
    sessionStorage.setItem('lastUserInteraction', Date.now().toString());
});

document.addEventListener('keydown', () => {
    sessionStorage.setItem('lastUserInteraction', Date.now().toString());
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (socketManager) {
        socketManager.destroy();
    }
});
