// Utility functions for the application

// Show notification function
function showNotification(message, isError = false) {
    const notification = document.getElementById("notification")
    notification.textContent = message
    notification.classList.toggle("error", isError)
    notification.classList.add("show")
  
    setTimeout(() => {
      notification.classList.remove("show")
    }, 3000)
  }
  