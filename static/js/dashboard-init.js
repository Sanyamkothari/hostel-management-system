/**
 * Dashboard initialization script for Hostel Management System
 * This handles initializing charts and dynamic content on the dashboard
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Dashboard init script loaded");
    
    // Wait for Chart.js to be available
    if (typeof Chart === 'undefined') {
        console.error("Chart.js is not loaded!");
        return;
    }
    
    console.log("Chart.js version:", Chart.version);
    
    let roomData = [];
    let feeData = {
        paid: 0,
        pending: 0,
        overdue: 0
    };
    
    // First try to get data from global variable (most reliable)
    if (window.dashboardData) {
        console.log("Using global dashboard data");
        roomData = window.dashboardData.roomData;
        feeData = window.dashboardData.feeData;
    } else {
        // Fallback to data attributes
        const chartDataElement = document.getElementById('chart-data');
        if (chartDataElement) {
            try {
                console.log("Chart data element found", chartDataElement.dataset);
                
                // Parse room data - convert from string to object
                const roomDataStr = chartDataElement.dataset.roomData;
                roomData = roomDataStr ? JSON.parse(roomDataStr) : [];
                
                // Fee data - make sure to convert to numbers
                feeData = {
                    paid: parseFloat(chartDataElement.dataset.paidFees || 0),
                    pending: parseFloat(chartDataElement.dataset.pendingFees || 0),
                    overdue: parseFloat(chartDataElement.dataset.overdueFees || 0)
                };
            } catch (err) {
                console.error("Error parsing data from attributes:", err);
            }
        }
    }    // Initialize charts if the functions are available
    console.log("Initializing charts with data:", {roomData, feeData});
    
    if (typeof initOccupancyChart === 'function') {
        initOccupancyChart('roomOccupancyChart', roomData);
    } else {
        console.error("initOccupancyChart function not found");
    }
    
    if (typeof initFeesChart === 'function') {
        initFeesChart('feeStatusChart', feeData);
    } else {
        console.error("initFeesChart function not found");
    }

    // Apply dynamic styling
    const progressBars = document.querySelectorAll('[data-progress-width]');
    progressBars.forEach(bar => {
        const width = bar.getAttribute('data-progress-width');
        if (width) {
            bar.style.width = width + '%';
        }
    });
});
