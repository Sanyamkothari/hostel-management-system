/**
 * Debug utility for dashboard charts
 * This file helps diagnose issues with chart data and initialization
 */

function logChartData() {
    const chartDataElement = document.getElementById('chart-data');
    if (chartDataElement) {
        console.log('Chart data element found:', chartDataElement);
        
        // Log all data attributes
        console.log('Data attributes:');
        const datasetProps = Object.keys(chartDataElement.dataset);
        datasetProps.forEach(prop => {
            console.log(`  ${prop}: ${chartDataElement.dataset[prop]}`);
        });
        
        try {
            // Try to parse room data
            const roomData = JSON.parse(chartDataElement.dataset.roomData || '[]');
            console.log('Room data parsed successfully:', roomData);
            
            // Fee data
            const paidFees = parseFloat(chartDataElement.dataset.paidFees || 0);
            const pendingFees = parseFloat(chartDataElement.dataset.pendingFees || 0);
            const overdueFees = parseFloat(chartDataElement.dataset.overdueFees || 0);
            
            console.log('Fee data:', {
                paid: paidFees,
                pending: pendingFees,
                overdue: overdueFees
            });
        } catch (err) {
            console.error('Error parsing chart data:', err);
        }
    } else {
        console.error('Chart data element not found! Make sure an element with id="chart-data" exists.');
    }
}

// Execute when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard debug script loaded');
    logChartData();
    
    // Check if chart containers exist
    const roomChartContainer = document.getElementById('roomOccupancyChart');
    const feeChartContainer = document.getElementById('feeStatusChart');
    
    console.log('Room chart container exists:', !!roomChartContainer);
    console.log('Fee chart container exists:', !!feeChartContainer);
});
