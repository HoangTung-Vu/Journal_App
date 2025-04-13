// Utility functions shared across the application

/**
 * Displays a notification message to the user.
 * @param {string} message The message to display.
 * @param {boolean} [isError=false] If true, styles the notification as an error.
 * @param {string} [elementId='notification'] The ID of the notification container element.
 */
function showNotification(message, isError = false, elementId = 'notification') {
    const notification = document.getElementById(elementId);
    if (!notification) {
        console.warn(`Notification element with ID '${elementId}' not found.`);
        // Fallback to alert if container not found
        alert(`${isError ? 'Error: ' : ''}${message}`);
        return;
    }

    notification.textContent = message;
    // Use specific classes for styling success/error
    notification.className = 'notification'; // Reset classes first
    if (isError) {
        notification.classList.add('error');
    } else {
        notification.classList.add('success'); // Use 'success' for non-errors
    }
    notification.classList.add('show'); // Trigger visibility/animation

    // Automatically hide the notification after a delay
    setTimeout(() => {
        notification.classList.remove('show');
        // Optional: Clear text and classes after fade out
        // setTimeout(() => {
        //     notification.textContent = '';
        //     notification.className = 'notification';
        // }, 500); // Adjust timing based on CSS transition duration
    }, 3000); // Notification visible for 3 seconds
}

// Export the function(s) for use in other modules
export { showNotification };