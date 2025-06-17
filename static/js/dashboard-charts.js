// Dashboard charts for Hostel Management System
function initOccupancyChart(elementId, roomData) {
    console.log("Initializing occupancy chart with data:", roomData);
    
    const chartElement = document.getElementById(elementId);
    if (!chartElement) {
        console.error("Chart element not found:", elementId);
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    // Check if we have valid data
    if (!roomData || !Array.isArray(roomData) || roomData.length === 0) {
        console.warn("No room data available for chart");
        // Draw an empty chart with a message
        new Chart(ctx, {
            type: 'bar',
            data: { labels: ['No Data'], datasets: [{ data: [0] }] },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'No Room Data Available'
                    }
                }
            }
        });
        return;
    }
    
    // Extract data for the chart
    const labels = roomData.map(room => room.room_number);
    const occupancyData = roomData.map(room => room.current_occupancy);
    const capacityData = roomData.map(room => room.capacity);
    const occupancyPercentage = roomData.map(room => 
        (room.capacity > 0 ? (room.current_occupancy / room.capacity) * 100 : 0).toFixed(1)
    );
    
    // Colors based on occupancy percentage
    const backgroundColors = occupancyPercentage.map(percent => {
        if (percent >= 90) return 'rgba(255, 99, 132, 0.6)'; // Red for high occupancy
        if (percent >= 60) return 'rgba(255, 205, 86, 0.6)'; // Yellow for medium occupancy
        return 'rgba(75, 192, 192, 0.6)'; // Green for low occupancy
    });

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Current Occupancy',
                    data: occupancyData,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors.map(color => color.replace('0.6', '1')),
                    borderWidth: 1
                },
                {
                    label: 'Capacity',
                    data: capacityData,
                    backgroundColor: 'rgba(201, 203, 207, 0.2)',
                    borderColor: 'rgba(201, 203, 207, 1)',
                    borderWidth: 1,
                    type: 'bar'
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Students'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Room Number'
                    }
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        footer: function(tooltipItems) {
                            const index = tooltipItems[0].dataIndex;
                            return `Occupancy: ${occupancyPercentage[index]}%`;
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Room Occupancy Overview'
                }
            }
        }
    });
}

function initFeesChart(elementId, feesData) {
    console.log("Initializing fees chart with data:", feesData);
    
    const chartElement = document.getElementById(elementId);
    if (!chartElement) {
        console.error("Chart element not found:", elementId);
        return;
    }
    
    const ctx = chartElement.getContext('2d');
    
    // Check if we have valid data
    if (!feesData) {
        console.warn("No fee data available for chart");
        // Draw an empty chart with a message
        new Chart(ctx, {
            type: 'doughnut',
            data: { labels: ['No Data'], datasets: [{ data: [1], backgroundColor: ['#f0f0f0'] }] },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'No Fee Data Available'
                    }
                }
            }
        });
        return;
    }
    
    // Extract data for the chart
    const paidAmount = feesData.paid || 0;
    const pendingAmount = feesData.pending || 0;
    const overdueAmount = feesData.overdue || 0;
    
    const total = paidAmount + pendingAmount + overdueAmount;
    const paidPercentage = total > 0 ? ((paidAmount / total) * 100).toFixed(1) : 0;
    const pendingPercentage = total > 0 ? ((pendingAmount / total) * 100).toFixed(1) : 0;
    const overduePercentage = total > 0 ? ((overdueAmount / total) * 100).toFixed(1) : 0;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Paid', 'Pending', 'Overdue'],
            datasets: [{
                data: [paidAmount, pendingAmount, overdueAmount],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.6)',  // Green for paid
                    'rgba(255, 205, 86, 0.6)',  // Yellow for pending
                    'rgba(255, 99, 132, 0.6)'   // Red for overdue
                ],
                borderColor: [
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 205, 86, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                },
                tooltip: {
                    callbacks: {
                        label: function(tooltipItem) {
                            let label = tooltipItem.label || '';
                            let value = tooltipItem.formattedValue;
                            let percentage = 0;
                            
                            switch(label) {
                                case 'Paid': 
                                    percentage = paidPercentage;
                                    break;
                                case 'Pending': 
                                    percentage = pendingPercentage;
                                    break;
                                case 'Overdue': 
                                    percentage = overduePercentage;
                                    break;
                            }
                            
                            return `${label}: $${value} (${percentage}%)`;
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Fee Collection Status'
                }
            }
        }
    });
}
