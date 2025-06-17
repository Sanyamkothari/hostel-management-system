/**
 * Optimized Common JavaScript Utilities for Hostel Management System
 * Consolidated utilities to reduce redundancy and improve performance
 */

// Performance optimization utilities
const PerformanceUtils = {
    // Debounce function for search inputs
    debounce: function(func, wait, immediate) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func(...args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func(...args);
        };
    },

    // Throttle function for scroll events
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // Lazy loading for images
    lazyLoadImages: function() {
        const images = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    },

    // Virtual scrolling for large lists
    virtualScroll: function(container, items, itemHeight, visibleCount) {
        let startIndex = 0;
        
        const updateView = () => {
            const scrollTop = container.scrollTop;
            startIndex = Math.floor(scrollTop / itemHeight);
            const endIndex = Math.min(startIndex + visibleCount, items.length);
            
            container.innerHTML = '';
            for (let i = startIndex; i < endIndex; i++) {
                const item = items[i];
                const element = document.createElement('div');
                element.style.height = itemHeight + 'px';
                element.innerHTML = item;
                container.appendChild(element);
            }
        };

        container.addEventListener('scroll', this.throttle(updateView, 16));
        updateView();
    }
};

// Common filtering functionality
const FilterUtils = {
    // Generic table filter
    filterTable: function(tableSelector, filters, options = {}) {
        const table = document.querySelector(tableSelector);
        if (!table) return;

        const rows = table.querySelectorAll('tbody tr');
        let visibleCount = 0;

        rows.forEach(row => {
            if (row.cells.length <= 1) return; // Skip empty or header rows

            const rowData = this.extractRowData(row, options.dataAttributes || []);
            const matches = this.checkFilters(rowData, filters);

            row.style.display = matches ? '' : 'none';
            if (matches) visibleCount++;
        });

        // Update statistics if callback provided
        if (options.updateStatsCallback) {
            options.updateStatsCallback(visibleCount);
        }

        return visibleCount;
    },

    // Extract data from table row
    extractRowData: function(row, dataAttributes) {
        const data = {};
        
        // Extract from data attributes
        dataAttributes.forEach(attr => {
            data[attr] = row.dataset[attr] || '';
        });

        // Extract from cell content
        Array.from(row.cells).forEach((cell, index) => {
            data[`cell_${index}`] = cell.textContent.trim().toLowerCase();
        });

        return data;
    },

    // Check if row matches filters
    checkFilters: function(rowData, filters) {
        return Object.entries(filters).every(([key, value]) => {
            if (!value) return true; // Empty filter matches all
            
            const rowValue = rowData[key] || '';
            
            if (typeof value === 'object' && value.min !== undefined && value.max !== undefined) {
                const numValue = parseFloat(rowValue) || 0;
                return numValue >= value.min && numValue <= value.max;
            }
            
            return rowValue.toLowerCase().includes(value.toLowerCase());
        });
    },

    // Generic card filter
    filterCards: function(cardSelector, filters, options = {}) {
        const cards = document.querySelectorAll(cardSelector);
        let visibleCount = 0;

        cards.forEach(card => {
            const cardData = this.extractCardData(card, options.dataAttributes || []);
            const matches = this.checkFilters(cardData, filters);

            card.style.display = matches ? 'block' : 'none';
            if (matches) visibleCount++;
        });

        if (options.updateStatsCallback) {
            options.updateStatsCallback(visibleCount);
        }

        return visibleCount;
    },

    // Extract data from card
    extractCardData: function(card, dataAttributes) {
        const data = {};
        
        dataAttributes.forEach(attr => {
            data[attr] = card.dataset[attr] || '';
        });

        // Extract text content
        data.text = card.textContent.toLowerCase();

        return data;
    }
};

// Export functionality
const ExportUtils = {
    // Export table to CSV
    exportTableToCSV: function(tableSelector, filename) {
        const table = document.querySelector(tableSelector);
        if (!table) return;

        const rows = table.querySelectorAll('tr');
        const csv = [];

        rows.forEach(row => {
            const rowData = [];
            // Skip action columns (usually last column)
            for (let i = 0; i < row.cells.length - 1; i++) {
                const cellText = row.cells[i].textContent.trim().replace(/\s+/g, ' ');
                rowData.push('"' + cellText.replace(/"/g, '""') + '"');
            }
            csv.push(rowData.join(','));
        });

        this.downloadCSV(csv.join('\n'), filename);
    },

    // Download CSV file
    downloadCSV: function(csvContent, filename) {
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'export_' + new Date().toISOString().split('T')[0] + '.csv';
        a.click();
        window.URL.revokeObjectURL(url);
    },

    // Print functionality
    printTable: function(tableSelector, title) {
        const table = document.querySelector(tableSelector);
        if (!table) return;

        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>${title || 'Print'}</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        table { width: 100%; border-collapse: collapse; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f5f5f5; }
                        .no-print { display: none; }
                    </style>
                </head>
                <body>
                    <h1>${title || 'Print Report'}</h1>
                    ${table.outerHTML}
                </body>
            </html>
        `);
        printWindow.document.close();
        printWindow.print();
    }
};

// Sort functionality
const SortUtils = {
    // Generic table sorting
    sortTable: function(tableSelector, columnIndex, sortType = 'auto') {
        const table = document.querySelector(tableSelector);
        if (!table) return;

        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr')).filter(row => row.cells.length > 1);

        const isNumeric = sortType === 'numeric' || (sortType === 'auto' && this.isNumericColumn(rows, columnIndex));
        const isDate = sortType === 'date' || (sortType === 'auto' && this.isDateColumn(rows, columnIndex));

        rows.sort((a, b) => {
            let valueA = a.cells[columnIndex].textContent.trim();
            let valueB = b.cells[columnIndex].textContent.trim();

            if (isNumeric) {
                valueA = parseFloat(valueA.replace(/[^\d.-]/g, '')) || 0;
                valueB = parseFloat(valueB.replace(/[^\d.-]/g, '')) || 0;
                return valueB - valueA; // Descending
            } else if (isDate) {
                valueA = new Date(valueA === 'N/A' || valueA === 'Not Paid' ? '1900-01-01' : valueA);
                valueB = new Date(valueB === 'N/A' || valueB === 'Not Paid' ? '1900-01-01' : valueB);
                return valueB - valueA; // Most recent first
            } else {
                return valueA.localeCompare(valueB);
            }
        });

        // Clear tbody and append sorted rows
        tbody.innerHTML = '';
        rows.forEach(row => tbody.appendChild(row));

        // Add empty state if no rows
        if (rows.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${table.querySelectorAll('th').length}" class="empty-state">
                        <i class="fas fa-inbox fa-3x"></i>
                        <h5>No data found</h5>
                        <p>Try adjusting your filters</p>
                    </td>
                </tr>
            `;
        }
    },

    // Check if column contains numeric values
    isNumericColumn: function(rows, columnIndex) {
        const sampleSize = Math.min(5, rows.length);
        let numericCount = 0;

        for (let i = 0; i < sampleSize; i++) {
            const value = rows[i].cells[columnIndex].textContent.trim();
            if (!isNaN(parseFloat(value.replace(/[^\d.-]/g, '')))) {
                numericCount++;
            }
        }

        return numericCount > sampleSize / 2;
    },

    // Check if column contains date values
    isDateColumn: function(rows, columnIndex) {
        const sampleSize = Math.min(5, rows.length);
        let dateCount = 0;

        for (let i = 0; i < sampleSize; i++) {
            const value = rows[i].cells[columnIndex].textContent.trim();
            if (value !== 'N/A' && !isNaN(Date.parse(value))) {
                dateCount++;
            }
        }

        return dateCount > sampleSize / 2;
    }
};

// View management
const ViewUtils = {
    // Toggle between table and card views
    toggleView: function(viewType, config) {
        const { tableView, cardView, tableBtn, cardBtn } = config;

        if (viewType === 'table') {
            tableView.style.display = 'block';
            cardView.style.display = 'none';
            tableBtn.classList.add('active');
            cardBtn.classList.remove('active');
        } else {
            tableView.style.display = 'none';
            cardView.style.display = 'grid';
            cardBtn.classList.add('active');
            tableBtn.classList.remove('active');
        }

        // Save preference
        localStorage.setItem('viewPreference', viewType);
    },

    // Load saved view preference
    loadViewPreference: function(config) {
        const savedView = localStorage.getItem('viewPreference');
        if (savedView) {
            this.toggleView(savedView, config);
        }
    },

    // Toggle filter panels
    toggleFilterPanel: function(contentId, iconId) {
        const content = document.getElementById(contentId);
        const icon = document.getElementById(iconId);

        if (content.style.display === 'none') {
            content.style.display = 'block';
            icon.className = 'fas fa-chevron-up';
        } else {
            content.style.display = 'none';
            icon.className = 'fas fa-chevron-down';
        }
    }
};

// Dynamic styling utilities
const StyleUtils = {
    // Apply progress bar widths
    applyProgressBars: function() {
        const progressBars = document.querySelectorAll('[data-progress-width]');
        progressBars.forEach(bar => {
            const width = bar.getAttribute('data-progress-width');
            if (width) {
                bar.style.width = width + '%';
            }
        });
    },

    // Apply dynamic colors
    applyDynamicColors: function() {
        const colorElements = document.querySelectorAll('[data-bg-color]');
        colorElements.forEach(element => {
            const color = element.getAttribute('data-bg-color');
            if (color) {
                element.style.backgroundColor = color;
            }
        });
    },

    // Apply theme
    applyTheme: function(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    },

    // Load saved theme
    loadTheme: function() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.applyTheme(savedTheme);
    }
};

// Initialize common functionality
document.addEventListener('DOMContentLoaded', function() {
    // Apply dynamic styles
    StyleUtils.applyProgressBars();
    StyleUtils.applyDynamicColors();
    StyleUtils.loadTheme();

    // Initialize lazy loading
    PerformanceUtils.lazyLoadImages();

    // Initialize accessibility fixes
    document.querySelectorAll('form[action*="delete"]').forEach(form => {
        if (!form.classList.contains('d-inline')) {
            form.classList.add('d-inline');
        }
        if (form.hasAttribute('style')) {
            form.removeAttribute('style');
        }
    });

    // Add missing accessibility attributes
    document.querySelectorAll('button:not([title])').forEach(button => {
        if (!button.textContent.trim() && !button.getAttribute('aria-label')) {
            const icon = button.querySelector('i[class*="fa-"]');
            if (icon) {
                const iconClass = Array.from(icon.classList)
                    .find(cls => cls.startsWith('fa-'))
                    ?.replace('fa-', '');
                
                if (iconClass) {
                    button.setAttribute('title', iconClass.charAt(0).toUpperCase() + iconClass.slice(1).replace(/-/g, ' '));
                }
            }
        }
    });

    // Add missing labels to form elements
    document.querySelectorAll('select:not([title]):not([aria-label])').forEach(select => {
        const id = select.getAttribute('id');
        if (id) {
            const label = document.querySelector(`label[for="${id}"]`);
            if (!label) {
                const labelText = select.getAttribute('name') || id;
                const formattedLabel = labelText
                    .replace(/([A-Z])/g, ' $1')
                    .replace(/_/g, ' ')
                    .replace(/^\w/, c => c.toUpperCase());
                
                select.setAttribute('title', formattedLabel);
            }
        }
    });

    // Initialize capacity bars with data attributes
    function initializeCapacityBars() {
        const capacityFills = document.querySelectorAll('.capacity-fill[data-width], .progress-bar[data-width]');
        
        capacityFills.forEach(fill => {
            const width = fill.getAttribute('data-width');
            const status = fill.getAttribute('data-status');
            
            // Set width with animation
            requestAnimationFrame(() => {
                fill.style.width = width + '%';
            });
            
            // Add status-based colors if not already set
            if (status && !fill.classList.contains('bg-')) {
                fill.classList.add(`capacity-${status}`);
            }
        });
    }

    // Initialize progress bars with proper accessibility
    function initializeProgressBars() {
        const progressBars = document.querySelectorAll('.progress-bar[data-width]');
        
        progressBars.forEach(bar => {
            const width = bar.getAttribute('data-width');
            
            // Set ARIA attributes
            bar.setAttribute('aria-valuenow', Math.round(width));
            bar.setAttribute('aria-valuemin', '0');
            bar.setAttribute('aria-valuemax', '100');
            
            // Set width
            bar.style.width = width + '%';
            
            // Add screen reader text if not present
            if (!bar.getAttribute('aria-label')) {
                bar.setAttribute('aria-label', `${Math.round(width)}% complete`);
            }
        });
    }

    // Call initialization functions
    initializeCapacityBars();
    initializeProgressBars();
});

// Global utilities object
window.HostelUtils = {
    Performance: PerformanceUtils,
    Filter: FilterUtils,
    Export: ExportUtils,
    Sort: SortUtils,
    View: ViewUtils,
    Style: StyleUtils
};
