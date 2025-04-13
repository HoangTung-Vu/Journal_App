// Import necessary modules
import { authService } from "./auth.js"
import { journalService } from "./journal.js"

// Main application initialization

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

// Export showNotification for use in other modules
export { showNotification }

// Global error handler
window.addEventListener("error", (event) => {
  console.error("Unhandled error:", event.error)
  showNotification("An unexpected error occurred", true)
})
