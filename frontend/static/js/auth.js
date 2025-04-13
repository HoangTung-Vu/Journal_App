// Authentication and User Session Management

// Import API service and utility functions
import { apiService } from './api.js';
import { showNotification } from './utils.js'; // Assuming utils.js exports this

class AuthService {
  constructor() {
    // DOM elements related to authentication (might be on index.html or journal.html)
    this.authContainer = document.getElementById("auth-container"); // On index.html
    this.journalContainer = document.getElementById("journal-container"); // On journal.html (used conceptually)
    this.userEmailSpan = document.getElementById("user-email"); // On journal.html
    this.logoutBtn = document.getElementById("logout-btn"); // On journal.html

    // Forms (on index.html)
    this.loginForm = document.getElementById("login");
    this.registerForm = document.getElementById("register");
    this.tabButtons = document.querySelectorAll(".tab-btn");
    this.authForms = document.querySelectorAll(".auth-form");
    this.notificationAreaAuth = document.getElementById("notification-auth"); // Specific area on auth page

    // Internal state
    this.currentUser = null;

    // Check if user is already logged in when service is created
    // this.checkAuthStatus(); // Moved to explicit init methods
  }

  // Initialization specific to the Authentication page (index.html)
  initAuthPage() {
    console.log("Initializing Auth Page Logic");
     this.redirectIfLoggedIn(); // Redirect if already logged in

    if (!this.authContainer) {
         console.warn("Auth container not found. Skipping auth page event listeners.");
         return;
    }

    // Setup event listeners for tab switching
    this.tabButtons.forEach(button => {
      button.addEventListener("click", (e) => {
         e.preventDefault(); // Prevent default if it's a button inside a form
        const tabName = button.getAttribute("data-tab");
        this.switchTab(tabName);
      });
    });

    // Setup form submission handlers
    if (this.loginForm) {
      this.loginForm.addEventListener("submit", this.handleLogin.bind(this));
    } else {
        console.warn("Login form not found.");
    }
    if (this.registerForm) {
      this.registerForm.addEventListener("submit", this.handleRegister.bind(this));
    } else {
         console.warn("Register form not found.");
    }
  }

  // Initialization specific to the Journal page (journal.html)
  initJournalPage() {
     console.log("Initializing Journal Page Auth Logic");
     if (!apiService.token) {
          console.log("No token found, redirecting to login.");
          this.redirectToLogin();
          return; // Stop initialization if not logged in
     }

     // Setup logout button listener
     if (this.logoutBtn) {
          this.logoutBtn.addEventListener("click", this.handleLogout.bind(this));
     } else {
          console.warn("Logout button not found.");
     }

     // Load user info for display
     this.loadUserInfo();
  }

  // --- Auth Page Methods ---

   redirectIfLoggedIn() {
       if (apiService.token) {
            console.log("Token exists, redirecting to journal page.");
            window.location.href = '/journal.html';
       }
   }

   redirectToLogin() {
        apiService.clearToken(); // Ensure token is cleared before redirect
        window.location.href = '/'; // Redirect to root (index.html)
   }

   showAuthNotification(message, isError = false) {
        const area = this.notificationAreaAuth;
        if (!area) return;
        area.textContent = message;
        area.className = isError ? 'error' : 'success'; // Use simple classes
        area.style.display = 'block';

         // Optional: auto-hide after a delay
        // setTimeout(() => {
        //     area.style.display = 'none';
        //     area.textContent = '';
        //     area.className = '';
        // }, 5000);
   }

  switchTab(tabName) {
    console.log("Switching to tab:", tabName);
     this.clearAuthNotifications();

    // Update active tab button
    this.tabButtons.forEach(button => {
        button.classList.toggle("active", button.getAttribute("data-tab") === tabName);
    });

    // Show corresponding form
    this.authForms.forEach(form => {
        form.classList.toggle("active", form.id === `${tabName}-form`);
    });

     // Focus the first input field of the active form
     const activeForm = document.querySelector(`.auth-form.active`);
     if (activeForm) {
         const firstInput = activeForm.querySelector('input');
         if (firstInput) {
             firstInput.focus();
         }
     }
  }

  async handleLogin(event) {
    event.preventDefault();
    this.clearAuthNotifications();
    const emailInput = document.getElementById("login-email");
    const passwordInput = document.getElementById("login-password");
    const email = emailInput.value.trim();
    const password = passwordInput.value; // Don't trim password

    if (!email || !password) {
        this.showAuthNotification("Vui lòng nhập email và mật khẩu.", true);
        return;
    }

    const submitButton = this.loginForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Đang đăng nhập...';

    try {
      const result = await apiService.login(email, password);
      if (result && result.access_token) {
         apiService.setToken(result.access_token);
         this.showAuthNotification("Đăng nhập thành công! Đang chuyển hướng...", false);
         // Redirect to the main journal page after successful login
         setTimeout(() => {
             window.location.href = '/journal.html';
         }, 1000); // Short delay to show message
      } else {
          // This case might not happen if apiService throws error on failure
           throw new Error("Login failed: No access token received.");
      }
    } catch (error) {
      console.error("Login error:", error);
      // Display error message from the API or a generic one
      this.showAuthNotification(`Đăng nhập thất bại: ${error.message}`, true);
      passwordInput.value = ''; // Clear password field on error
      submitButton.disabled = false;
      submitButton.textContent = 'Đăng nhập';
    }
  }

  async handleRegister(event) {
    event.preventDefault();
     this.clearAuthNotifications();
    const emailInput = document.getElementById("register-email");
    const passwordInput = document.getElementById("register-password");
    const confirmPasswordInput = document.getElementById("register-confirm-password");

    const email = emailInput.value.trim();
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    if (!email || !password || !confirmPassword) {
         this.showAuthNotification("Vui lòng điền đầy đủ thông tin.", true);
         return;
    }
    if (password !== confirmPassword) {
      this.showAuthNotification("Mật khẩu xác nhận không khớp.", true);
      return;
    }
     if (password.length < 6) {
          this.showAuthNotification("Mật khẩu phải có ít nhất 6 ký tự.", true);
          return;
     }

     const submitButton = this.registerForm.querySelector('button[type="submit"]');
     submitButton.disabled = true;
     submitButton.textContent = 'Đang đăng ký...';

    try {
      await apiService.register(email, password);
      this.showAuthNotification("Đăng ký thành công! Vui lòng đăng nhập.", false);
      // Switch to the login tab after successful registration
      this.switchTab('login');
       // Optionally clear registration form
       emailInput.value = '';
       passwordInput.value = '';
       confirmPasswordInput.value = '';
       document.getElementById('login-email').value = email; // Pre-fill login email
       document.getElementById('login-password').focus();
    } catch (error) {
      console.error("Registration error:", error);
      this.showAuthNotification(`Đăng ký thất bại: ${error.message}`, true);
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Đăng ký';
    }
  }

  clearAuthNotifications() {
       if (this.notificationAreaAuth) {
           this.notificationAreaAuth.style.display = 'none';
           this.notificationAreaAuth.textContent = '';
           this.notificationAreaAuth.className = '';
       }
   }


  // --- Journal Page Methods ---

  async loadUserInfo() {
     if (!this.userEmailSpan) return; // Only run if element exists

     try {
         const user = await apiService.getCurrentUser();
         this.currentUser = user;
         if (this.userEmailSpan) {
              this.userEmailSpan.textContent = `Chào, ${user.email}`;
         }
     } catch (error) {
         console.error("Failed to load user info:", error);
         // If fetching user fails (e.g., token invalid/expired), redirect to login
         showNotification("Phiên đăng nhập không hợp lệ hoặc đã hết hạn.", true);
         setTimeout(() => {
             this.redirectToLogin();
         }, 1500);
     }
   }

  handleLogout() {
    console.log("Logging out...");
    apiService.clearToken();
    this.currentUser = null;
    // Redirect to the login page after logout
    showNotification("Đăng xuất thành công.", false);
     setTimeout(() => {
        this.redirectToLogin();
     }, 1000);
  }

}

// Export the class for use in HTML modules
export { AuthService };