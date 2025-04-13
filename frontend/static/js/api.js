// API service for making requests to the backend

const API_BASE_URL = "http://127.0.0.1:8000"; // Ensure no trailing slash initially
const API_V1_PREFIX = "/api/v1";

class ApiService {
  constructor(baseURL = API_BASE_URL) {
    this.baseURL = baseURL;
    this.token = localStorage.getItem("journalToken"); // Use a specific key
    console.log("ApiService Initialized. Token found:", !!this.token);
  }

  // Set authentication token
  setToken(token) {
    if (token) {
      this.token = token;
      localStorage.setItem("journalToken", token);
      console.log("Token set in localStorage");
    } else {
      this.clearToken(); // Clear if null/undefined token is passed
    }
  }

  // Clear authentication token
  clearToken() {
    this.token = null;
    localStorage.removeItem("journalToken");
    console.log("Token cleared from localStorage");
  }

  // Get headers for requests
  getHeaders(isFormData = false) {
    const headers = {};

    if (!isFormData) {
        headers["Content-Type"] = "application/json";
    }
    // Only add Authorization header if token exists
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    // console.log("Request Headers:", headers); // Debug headers
    return headers;
  }

  // Unified request function
  async request(endpoint, options = {}) {
      const url = this.baseURL + endpoint;
      const method = options.method || 'GET';
      const isFormData = options.isFormData || false;
      const skipAuth = options.skipAuth || false;

      // Prepare body
      let body = options.body;
      if (isFormData && body) {
          // Convert object to URLSearchParams for x-www-form-urlencoded
          const formData = new URLSearchParams();
          for (const key in body) {
              if (Object.hasOwnProperty.call(body, key)) {
                  formData.append(key, body[key]);
              }
          }
          body = formData;
      } else if (body && typeof body !== 'string' && !(body instanceof FormData)) {
          // Default to JSON stringify if not FormData or already string
          body = JSON.stringify(body);
      }

      const fetchOptions = {
          method: method,
          headers: this.getHeaders(isFormData),
          body: body // Body can be string, URLSearchParams, FormData, null
      };

       console.log(`Making ${method} request to: ${url}`);
       // console.log("Fetch Options:", fetchOptions); // Debug fetch options


      try {
          const response = await fetch(url, fetchOptions);
          return this.handleResponse(response);
      } catch (error) {
          console.error(`Network or other error fetching ${url}:`, error);
           if (error instanceof TypeError && error.message === "Failed to fetch") {
                throw new Error("Network error: Could not connect to the server. Please check if the backend is running.");
            }
          throw error; // Re-throw the error for the caller to handle
      }
  }


  // Handle API response
  async handleResponse(response) {
    console.log(`Response status: ${response.status} from ${response.url}`);
    const contentType = response.headers.get("content-type");

    if (!response.ok) {
        let errorData;
        try {
            if (contentType && contentType.includes("application/json")) {
                errorData = await response.json();
                 console.error("API Error Response (JSON):", errorData);
            } else {
                 const text = await response.text();
                 errorData = { detail: text || `Request failed with status ${response.status}` };
                 console.error("API Error Response (Non-JSON):", text);
            }
        } catch (e) {
             errorData = { detail: `Failed to parse error response. Status: ${response.status}` };
              console.error("Failed to parse error response:", e);
        }

        // Special handling for 401 Unauthorized (e.g., token expired)
        if (response.status === 401) {
             console.warn("Received 401 Unauthorized. Clearing token and potentially redirecting.");
             this.clearToken();
             // Optional: Redirect to login page or trigger a global event
             // window.location.href = '/'; // Or use a more sophisticated method
             throw new Error(errorData.detail || "Authentication required or session expired.");
        }

        throw new Error(errorData.detail || `HTTP error ${response.status}`);
    }

    // Handle successful responses
    if (response.status === 204 || response.headers.get('content-length') === '0') {
        console.log("Response has no content (204 or zero length).")
        return null; // Or return an empty object/true based on context
    }

    if (contentType && contentType.includes("application/json")) {
        const data = await response.json();
        // console.log("API Success Response (JSON):", data);
        return data;
    } else {
        // Handle non-JSON success responses if necessary
        const text = await response.text();
        console.log("API Success Response (Non-JSON):", text);
        return text;
    }
  }

  // --- Authentication API Calls ---
  async login(email, password) {
    console.log("Attempting login for:", email);
    // FastAPI's OAuth2PasswordRequestForm expects x-www-form-urlencoded
    // with 'username' and 'password' fields.
    return this.request(`${API_V1_PREFIX}/auth/token`, {
        method: 'POST',
        body: { username: email, password: password }, // request() will convert this
        isFormData: true, // Signal to use URLSearchParams
        skipAuth: true    // Don't send Authorization header for login itself
    });
    // No need to call setToken here, handleResponse doesn't automatically do it.
    // The caller (AuthService) should call setToken with the result.
  }

  async register(email, password) {
    console.log("Attempting registration for:", email);
    return this.request(`${API_V1_PREFIX}/auth/register`, {
        method: 'POST',
        body: { email, password }, // Body is JSON
        skipAuth: true
    });
  }

  async getCurrentUser() {
    console.log("Fetching current user (/users/me)");
    // This request requires authentication (token)
    return this.request(`${API_V1_PREFIX}/auth/users/me`, {
         method: 'GET' // Default method is GET, explicitly stated for clarity
         // skipAuth: false (default)
    });
  }

  // --- Journal API Calls ---
  async getJournalEntries(skip = 0, limit = 100) {
    console.log(`Fetching journal entries (skip=${skip}, limit=${limit})`);
    // Requires auth
    return this.request(`${API_V1_PREFIX}/journal/?skip=${skip}&limit=${limit}`);
  }

  async getJournalEntry(id) {
    console.log("Fetching journal entry:", id);
    // Requires auth
    return this.request(`${API_V1_PREFIX}/journal/${id}`);
  }

  async createJournalEntry(title, content) {
    console.log("Creating journal entry:", title);
    // Requires auth
    return this.request(`${API_V1_PREFIX}/journal/`, {
        method: 'POST',
        body: { title, content } // JSON body
    });
  }

   async updateJournalEntry(id, updateData) {
     console.log("Updating journal entry:", id);
     // Requires auth
     // updateData should be an object like { title: "new title", content: "new content"}
     // Only include fields to be updated.
     return this.request(`${API_V1_PREFIX}/journal/${id}`, {
         method: 'PUT',
         body: updateData // JSON body with optional fields
     });
   }

   async deleteJournalEntry(id) {
     console.log("Deleting journal entry:", id);
     // Requires auth
     return this.request(`${API_V1_PREFIX}/journal/${id}`, {
         method: 'DELETE'
         // Expects 204 No Content on success
     });
   }


  async getAIConsultation(entryId) {
    console.log("Getting AI consultation for entry:", entryId);
    // Requires auth
    return this.request(`${API_V1_PREFIX}/journal/${entryId}/consult`, {
        method: 'POST'
        // No request body needed for this endpoint currently
    });
  }
}

// Create and export a single instance of the API service
const apiService = new ApiService();

export { apiService }; // Export the instance