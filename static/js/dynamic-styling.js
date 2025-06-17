/**
 * Dynamic element styling for Hostel Management System
 * Handles elements that need dynamic styling without using inline styles
 */

document.addEventListener('DOMContentLoaded', function() {
    // Apply width to progress bars with data-progress-width attribute
    const progressBars = document.querySelectorAll('[data-progress-width]');
    progressBars.forEach(bar => {
        const width = bar.getAttribute('data-progress-width');
        if (width) {
            bar.style.width = width + '%';
        }
    });

    // Also handle the old data-width attribute for backward compatibility
    const oldProgressBars = document.querySelectorAll('.dynamic-progress[data-width]');
    oldProgressBars.forEach(bar => {
        const width = bar.getAttribute('data-width');
        if (width) {
            bar.style.width = width + '%';
            console.log('Found deprecated data-width attribute on progress bar. Using width: ' + width + '%');
        }
    });

    // Apply width to other elements needing dynamic width
    const dynamicWidthElements = document.querySelectorAll('[data-width]');
    dynamicWidthElements.forEach(element => {
        const width = element.getAttribute('data-width');
        if (width) {
            element.style.width = width + '%';
        }
    });
    
    // Apply dynamic background colors
    const colorElements = document.querySelectorAll('[data-bg-color]');
    colorElements.forEach(element => {
        const color = element.getAttribute('data-bg-color');
        if (color) {
            element.style.backgroundColor = color;
        }
    });
    
    // Apply dynamic opacity
    const opacityElements = document.querySelectorAll('[data-opacity]');
    opacityElements.forEach(element => {
        const opacity = element.getAttribute('data-opacity');
        if (opacity) {
            element.style.opacity = opacity;
        }
    });
});
