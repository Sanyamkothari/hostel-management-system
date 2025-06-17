/**
 * Accessibility and Styling Fixes for Hostel Management System
 * This script fixes accessibility issues and removes inline styles by 
 * applying the necessary CSS classes programmatically
 */

document.addEventListener('DOMContentLoaded', function() {
    // 1. Fix progress bars and dynamic widths
    document.querySelectorAll('[data-progress-width]').forEach(element => {
        const width = element.getAttribute('data-progress-width');
        element.style.width = width + '%';
    });
      // 2. Convert inline forms with style="display: inline" to use classes
    // First try to find forms with inline style
    document.querySelectorAll('form[style*="display: inline"]').forEach(form => {
        form.removeAttribute('style');
        form.classList.add('d-inline');
    });
    
    // Then find forms that might have it in the HTML source but are not caught by the selector
    // This is specifically for the view_rooms.html file with known issues
    document.querySelectorAll('form[action*="delete_room"]').forEach(form => {
        // If it doesn't already have d-inline class
        if (!form.classList.contains('d-inline')) {
            form.classList.add('d-inline');
        }
        
        // Remove any style attribute
        if (form.hasAttribute('style')) {
            form.removeAttribute('style');
        }
    });
    
    // 3. Handle other dynamic display properties
    document.querySelectorAll('[data-display]').forEach(element => {
        const display = element.getAttribute('data-display');
        element.style.display = display;
    });
    
    // 4. Add missing accessibility attributes to buttons and links
    document.querySelectorAll('button:not([title])').forEach(button => {
        // If button has text content or aria-label, we don't need to add title
        if (!button.textContent.trim() && !button.getAttribute('aria-label')) {
            // Try to use icon name as title
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
    
    // 5. Add missing labels to form elements
    document.querySelectorAll('select:not([title]):not([aria-label])').forEach(select => {
        // If select has an id, look for a label
        const id = select.getAttribute('id');
        if (id) {
            const label = document.querySelector(`label[for="${id}"]`);
            if (!label) {
                // Create a visually hidden label
                const labelText = select.getAttribute('name') || id;
                const formattedLabel = labelText
                    .replace(/([A-Z])/g, ' $1')
                    .replace(/_/g, ' ')
                    .replace(/^\w/, c => c.toUpperCase());
                    
                select.setAttribute('title', formattedLabel);
            }
        } else {
            // No id, so add title attribute
            const labelText = select.getAttribute('name') || 'Select option';
            const formattedLabel = labelText
                .replace(/([A-Z])/g, ' $1')
                .replace(/_/g, ' ')
                .replace(/^\w/, c => c.toUpperCase());
                
            select.setAttribute('title', formattedLabel);
        }
    });
    
    // 6. Add missing text for screen readers to icon-only buttons and links
    document.querySelectorAll('a.btn > i:only-child, button.btn > i:only-child').forEach(iconElement => {
        const parent = iconElement.parentElement;
        
        // Skip if the parent already has sr-only text
        if (parent.querySelector('.sr-only')) return;
        
        // Get icon name
        const iconClass = Array.from(iconElement.classList)
            .find(cls => cls.startsWith('fa-'))
            ?.replace('fa-', '');
            
        if (iconClass) {
            const srText = document.createElement('span');
            srText.className = 'sr-only';
            srText.textContent = iconClass.charAt(0).toUpperCase() + iconClass.slice(1).replace(/-/g, ' ');
            parent.appendChild(srText);
        }
    });
});
