// --- START OF FILE frontend/static/js/auth.js ---
// Authentication and User Session Management

// Import API service and utility functions
import { apiService } from './api.js';
import { showNotification } from './utils.js';

class AuthService {
  constructor() {
    // DOM elements related to authentication (might be on index.html or journal.html/chat.html)
    this.authContainer = document.getElementById("auth-container"); // On index.html
    // User display/logout elements (common to journal.html & chat.html)
    this.userEmailSpan = document.getElementById("user-email");
    this.logoutBtn = document.getElementById("logout-btn");

    // Auth page specific forms/elements
    this.loginForm = document.getElementById("login");
    this.registerForm = document.getElementById("register");
    this.tabButtons = document.querySelectorAll(".tab-btn");
    this.authForms = document.querySelectorAll(".auth-form");
    this.notificationAreaAuth = document.getElementById("notification-auth");

    // Internal state
    this.currentUser = null;
  }

  // Initialization specific to the Authentication page (index.html)
  initAuthPage() {
    console.log("Initializing Auth Page Logic");
    this.redirectIfLoggedIn('/journal.html'); // Redirect logged-in users away from auth page

    if (!this.authContainer) {
         console.warn("Auth container not found. Skipping auth page event listeners.");
         return;
    }
    // Setup event listeners for tab switching
    this.tabButtons.forEach(button => {
      button.addEventListener("click", (e) => {
         e.preventDefault();
        const tabName = button.getAttribute("data-tab");
        this.switchTab(tabName);
      });
    });
    // Setup form submission handlers
    if (this.loginForm) this.loginForm.addEventListener("submit", this.handleLogin.bind(this));
    if (this.registerForm) this.registerForm.addEventListener("submit", this.handleRegister.bind(this));
  }

  // Initialization specific to the Journal page (journal.html)
  initJournalPage() {
     console.log("Initializing Journal Page Auth Logic");
     this.checkLoginStatusAndSetupUserUI();
  }

  // Initialization specific to the Chat page (chat.html) <-- ADD THIS
  initChatPage() {
     console.log("Initializing Chat Page Auth Logic");
     this.checkLoginStatusAndSetupUserUI();
  }

  // Common logic for authenticated pages (Journal, Chat)
  checkLoginStatusAndSetupUserUI() {
     if (!apiService.token) {
          console.log("No token found, redirecting to login.");
          this.redirectToLogin();
          return false; // Indicate user is not logged in
     }
     // Setup logout button listener if it exists on the page
     if (this.logoutBtn) {
          this.logoutBtn.addEventListener("click", this.handleLogout.bind(this));
     } else {
          console.warn("Logout button not found on this page.");
     }
     // Load user info for display if the element exists
     if (this.userEmailSpan) {
          this.loadUserInfo();
     } else {
          console.warn("User email display element not found on this page.");
     }
     return true; // Indicate user is logged in
  }


  // --- Auth Page Methods ---

   redirectIfLoggedIn(targetUrl = '/journal.html') {
       if (apiService.token) {
            console.log(`Token exists, redirecting from auth page to ${targetUrl}.`);
            window.location.href = targetUrl;
       }
   }

   redirectToLogin() {
        console.log("Redirecting to login page.");
        apiService.clearToken(); // Ensure token is cleared before redirect
        window.location.href = '/'; // Redirect to root (index.html)
   }

   showAuthNotification(message, isError = false) {
        const area = this.notificationAreaAuth;
        if (!area) return;
        area.textContent = message;
        area.className = ''; // Clear previous classes
        area.classList.add('notification-auth', isError ? 'error' : 'success');
        area.style.display = 'block';
   }

  switchTab(tabName) {
    console.log("Switching to tab:", tabName);
     this.clearAuthNotifications();
    this.tabButtons.forEach(button => {
        button.classList.toggle("active", button.getAttribute("data-tab") === tabName);
    });
    this.authForms.forEach(form => {
        form.classList.toggle("active", form.id === `${tabName}-form`);
    });
     const activeForm = document.querySelector(`.auth-form.active`);
     if (activeForm) activeForm.querySelector('input')?.focus();
  }

  async handleLogin(event) {
    event.preventDefault();
    this.clearAuthNotifications();
    const emailInput = document.getElementById("login-email");
    const passwordInput = document.getElementById("login-password");
    const email = emailInput?.value.trim();
    const password = passwordInput?.value;

    if (!email || !password) {
        this.showAuthNotification("Vui lòng nhập email và mật khẩu.", true);
        return;
    }

    const submitButton = this.loginForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Đang đăng nhập...';

    try {
      const result = await apiService.login(email, password);
      if (result?.access_token) {
         apiService.setToken(result.access_token);
         this.showAuthNotification("Đăng nhập thành công! Đang chuyển hướng...", false);
         setTimeout(() => { window.location.href = '/journal.html'; }, 1000);
      } else { throw new Error("Login failed: No access token received."); }
    } catch (error) {
      console.error("Login error:", error);
      const errorMsg = error.message.includes('401') ? "Sai email hoặc mật khẩu." : `Đăng nhập thất bại: ${error.message}`;
      this.showAuthNotification(errorMsg, true);
      if (passwordInput) passwordInput.value = ''; // Clear password field
    } finally {
         if (submitButton) {
             submitButton.disabled = false;
             submitButton.textContent = 'Đăng nhập';
         }
    }
  }

  async handleRegister(event) {
    event.preventDefault();
     this.clearAuthNotifications();
    const emailInput = document.getElementById("register-email");
    const passwordInput = document.getElementById("register-password");
    const confirmPasswordInput = document.getElementById("register-confirm-password");

    const email = emailInput?.value.trim();
    const password = passwordInput?.value;
    const confirmPassword = confirmPasswordInput?.value;

    // Input validation
    if (!email || !password || !confirmPassword) { this.showAuthNotification("Vui lòng điền đầy đủ thông tin.", true); return; }
    if (password !== confirmPassword) { this.showAuthNotification("Mật khẩu xác nhận không khớp.", true); return; }
    if (password.length < 6) { this.showAuthNotification("Mật khẩu phải có ít nhất 6 ký tự.", true); return; }
     // Basic email format check (browser usually handles this via type="email")
     if (!/\S+@\S+\.\S+/.test(email)) { this.showAuthNotification("Vui lòng nhập địa chỉ email hợp lệ.", true); return; }


     const submitButton = this.registerForm.querySelector('button[type="submit"]');
     submitButton.disabled = true;
     submitButton.textContent = 'Đang đăng ký...';

    try {
      await apiService.register(email, password);
      this.showAuthNotification("Đăng ký thành công! Vui lòng chuyển qua tab Đăng nhập.", false);
      this.switchTab('login');
       // Pre-fill login email after successful registration
       const loginEmailInput = document.getElementById('login-email');
       if (loginEmailInput) loginEmailInput.value = email;
       document.getElementById('login-password')?.focus();
       // Clear registration form
       if (emailInput) emailInput.value = '';
       if (passwordInput) passwordInput.value = '';
       if (confirmPasswordInput) confirmPasswordInput.value = '';

    } catch (error) {
      console.error("Registration error:", error);
       const errorMsg = error.message.includes('400') && error.message.includes('Email already registered')
                       ? "Email này đã được đăng ký. Vui lòng sử dụng email khác hoặc đăng nhập."
                       : `Đăng ký thất bại: ${error.message}`;
      this.showAuthNotification(errorMsg, true);
    } finally {
         if (submitButton) {
             submitButton.disabled = false;
             submitButton.textContent = 'Đăng ký';
         }
    }
  }

  clearAuthNotifications() {
       if (this.notificationAreaAuth) {
           this.notificationAreaAuth.style.display = 'none';
           this.notificationAreaAuth.textContent = '';
           this.notificationAreaAuth.className = 'notification-auth'; // Reset class
       }
   }


  // --- Authenticated Page Methods ---

  async loadUserInfo() {
     if (!this.userEmailSpan) return; // Only run if element exists
     this.userEmailSpan.textContent = 'Đang tải...'; // Placeholder

     try {
         const user = await apiService.getCurrentUser();
         this.currentUser = user;
         this.userEmailSpan.textContent = `Chào, ${user.email}`;
     } catch (error) {
         console.error("Failed to load user info:", error);
         this.userEmailSpan.textContent = 'Lỗi tải thông tin';
         // If fetching user fails (e.g., token invalid/expired), redirect to login
         showNotification("Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Đang chuyển hướng...", true, 'notification'); // Use global notification
         setTimeout(() => { this.redirectToLogin(); }, 2000);
     }
   }

  handleLogout() {
    console.log("Logging out...");
    apiService.clearToken();
    this.currentUser = null;
    showNotification("Đăng xuất thành công. Đang chuyển hướng...", false, 'notification'); // Use global notification
     setTimeout(() => { this.redirectToLogin(); }, 1000);
  }

}

// Export the class for use in HTML modules
export { AuthService };
// --- END OF FILE frontend/static/js/auth.js ---