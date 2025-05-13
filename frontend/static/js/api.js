// API service for making requests to the backend

// Use relative URL so it works both in development and production with Docker
const API_BASE_URL = ""; // Empty means use current host
const API_V1_PREFIX = "/api/v1";

class ApiService {
  constructor(baseURL = API_BASE_URL) {
    this.baseURL = baseURL;
    this.token = localStorage.getItem("journalToken"); // Use a specific key
    console.log("ApiService Initialized. Token found:", !!this.token);
    // Retry logic might be too aggressive for general use, remove or refine if needed
    // this.maxRetries = 1; // Reduce default retries maybe
    // this.retryDelay = 1500;
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
    const headers = {
        // Standard headers
        'Accept': 'application/json',
    };

    if (!isFormData) {
        // Only set Content-Type for non-FormData requests where body exists
        headers["Content-Type"] = "application/json";
    }
    // Add Authorization header if token exists
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    return headers;
  }

  // Unified request function
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    // Determine if headers need Content-Type based on body presence and type
    const isFormData = options.body instanceof FormData || options.body instanceof URLSearchParams;
    const headers = this.getHeaders(isFormData);

    let body = options.body;
    // Adjust Content-Type for specific body types if necessary
    if (options.body && typeof options.body === 'object' && !isFormData) {
      body = JSON.stringify(body);
      // Ensure Content-Type is application/json if not already set
      if (!headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
      }
    } else if (isFormData) {
         // Let the browser set the Content-Type for FormData/URLSearchParams
         delete headers['Content-Type'];
    }

    console.log(`API Request: ${options.method || 'GET'} ${url}`);
    // Avoid logging body if it contains sensitive info like passwords
    // if(body && !url.includes('token') && !url.includes('register')) {
    //     console.log("Request Body:", body);
    // }

    try {
      const response = await fetch(url, {
        method: options.method || 'GET',
        headers: headers,
        // Only include body if it exists
        body: body
      });

      // Pass the response object to handleResponse
      return await this.handleResponse(response); // Added await here

    } catch (error) {
       // Network errors or other fetch-related issues
      console.error(`API request failed for ${url}: ${error.message}`, error);
       // Throw a more specific error or re-throw
       throw new Error(`Network error or failed to fetch: ${error.message}`);
    }
  }

  // Handle API response
  async handleResponse(response) {
    console.log(`API Response Status: ${response.status} for ${response.url}`);
    const contentType = response.headers.get("content-type");

    // --- Error Handling ---
    if (!response.ok) {
        let errorData = { detail: `Request failed with status ${response.status}` }; // Default error
        try {
            if (contentType && contentType.includes("application/json")) {
                const jsonError = await response.json();
                // Use the 'detail' field if available, otherwise stringify
                errorData.detail = jsonError.detail || JSON.stringify(jsonError);
                console.error("API Error Response (JSON):", jsonError);
            } else {
                 // Attempt to read non-JSON error text
                 const textError = await response.text();
                 errorData.detail = textError || errorData.detail; // Use text if available
                 console.error("API Error Response (Non-JSON):", textError);
            }
        } catch (e) {
             // Failed to parse error body, stick with status code default
             console.error("Failed to parse error response body:", e);
        }

         // Add status code to the error object/message for better context
         const errorMessage = `Error ${response.status}: ${errorData.detail}`;
         console.error(errorMessage); // Log the final consolidated error

        // Special handling for 401 Unauthorized (e.g., token expired)
        if (response.status === 401) {
             console.warn("Received 401 Unauthorized. Clearing token.");
             this.clearToken();
             // Throw specific error for UI to potentially trigger redirect
             throw new Error("401: Authentication required or session expired. Please log in again.");
        }

        // Throw a generic error containing the detail message and status
         throw new Error(errorMessage);
    }

    // --- Success Handling ---
    // Handle 204 No Content specifically
    if (response.status === 204) {
        console.log("Response has no content (204).")
        return null; // Return null for successful deletion/no content responses
    }

    // Check content type for JSON parsing
    if (contentType && contentType.includes("application/json")) {
        try {
             const data = await response.json();
             // console.log("API Success Response (JSON):", data); // Optional: Log success data
             return data;
        } catch (e) {
             console.error("Failed to parse successful JSON response:", e);
             throw new Error("Failed to parse JSON response from server.");
        }
    } else {
        // Handle successful non-JSON responses (e.g., plain text) if expected
        try {
             const textData = await response.text();
             console.log("API Success Response (Non-JSON):", textData.substring(0, 100) + '...'); // Log preview
             return textData;
        } catch (e) {
             console.error("Failed to read successful text response:", e);
             throw new Error("Failed to read text response from server.");
        }
    }
  }

  // --- Authentication API Calls ---
  async login(email, password) {
    console.log("Attempting login for:", email);
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    return this.request(`${API_V1_PREFIX}/auth/token`, {
        method: 'POST',
        body: formData,
        // isFormData: true // Request function handles this type detection
    });
  }

  async register(email, password) {
    console.log("Attempting registration for:", email);
    return this.request(`${API_V1_PREFIX}/auth/register`, {
        method: 'POST',
        body: { email, password }, // Body is JSON
    });
  }

  async getCurrentUser() {
    console.log("Fetching current user (/users/me)");
    return this.request(`${API_V1_PREFIX}/auth/users/me`, {
         method: 'GET'
    });
  }

  // --- Journal API Calls ---
  async getJournalEntries(skip = 0, limit = 100) {
    console.log(`Fetching journal entries (skip=${skip}, limit=${limit})`);
    return this.request(`${API_V1_PREFIX}/journal/?skip=${skip}&limit=${limit}`);
  }

  async getJournalEntry(id) {
    console.log("Fetching journal entry:", id);
    return this.request(`${API_V1_PREFIX}/journal/${id}`);
  }

  async createJournalEntry(title, content) {
    console.log("Creating journal entry:", title);
    return this.request(`${API_V1_PREFIX}/journal/`, {
        method: 'POST',
        body: { title, content } // JSON body
    });
  }

   async updateJournalEntry(id, updateData) {
     console.log("Updating journal entry:", id);
     return this.request(`${API_V1_PREFIX}/journal/${id}`, {
         method: 'PUT',
         body: updateData // JSON body with optional fields
     });
   }

   async deleteJournalEntry(id) {
     console.log("Deleting journal entry:", id);
     return this.request(`${API_V1_PREFIX}/journal/${id}`, {
         method: 'DELETE' // Expects 204 No Content on success
     });
   }


  async getAIConsultation(entryId) {
    console.log("Getting AI consultation for entry:", entryId);
    return this.request(`${API_V1_PREFIX}/journal/${entryId}/consult`, {
        method: 'POST' // No request body needed
    });
  }

  // --- Chat API Calls ---
  async sendChatMessage(message) {
    console.log("Sending chat message to API:", message.substring(0, 50) + '...');
    // try/catch is useful here but primarily handled in request method
    return this.request(`${API_V1_PREFIX}/chat/`, {
        method: 'POST',
        body: { message: message } // JSON body
    });
    // Errors thrown by request/handleResponse will propagate up
  }

  async getChatContext() {
    console.log("Getting chat context from API");
    // Useful for checking if user has entries before allowing chat UI interaction
    return this.request(`${API_V1_PREFIX}/chat/context`, {
        method: 'GET'
    });
     // Expects List[JournalEntry] or 404 if no entries
  }

}

// Create and export a single instance of the API service
const apiService = new ApiService();

export { apiService }; // Export the instance
