// Journal Entries Management

// Import API service and utility functions
import { apiService } from './api.js';
import { showNotification } from './utils.js';

class JournalService {
  constructor() {
    // DOM elements for the journal interface (on journal.html)
    this.entriesList = document.getElementById("entries-list");
    this.entryView = document.getElementById("entry-view");
    this.entryEditor = document.getElementById("entry-editor");
    this.entryForm = document.getElementById("entry-form");
    this.titleInput = document.getElementById("entry-title-input");
    this.contentInput = document.getElementById("entry-content-input");
    this.entryIdInput = document.getElementById("entry-id-input"); // Hidden input for editing
    this.entryTitle = document.getElementById("entry-title");
    this.entryDate = document.getElementById("entry-date");
    this.entryContent = document.getElementById("entry-content");
    this.editorTitle = document.getElementById("editor-title");
    this.newEntryBtn = document.getElementById("new-entry-btn");
    this.cancelBtn = document.getElementById("cancel-btn");
    this.getAiBtn = document.getElementById("get-ai-btn");
    this.aiConsultation = document.getElementById("ai-consultation");
    this.aiContent = document.getElementById("ai-content");
    this.aiLoading = document.getElementById("ai-loading");
    this.editEntryBtn = document.getElementById("edit-entry-btn");
    this.deleteEntryBtn = document.getElementById("delete-entry-btn");
    this.noEntrySelectedView = document.getElementById("no-entry-selected");


    // State
    this.entries = []; // Local cache of entries
    this.currentEntryId = null; // ID of the currently viewed/edited entry
    this.isEditing = false;

    // Ensure essential elements exist before proceeding
    if (!this.entriesList || !this.entryView || !this.entryEditor || !this.newEntryBtn) {
        console.error("Essential Journal UI elements not found. JournalService may not function correctly.");
        // Optional: throw an error or display a persistent message
        // showNotification("Lỗi giao diện người dùng nghiêm trọng. Vui lòng tải lại trang.", true);
    }
  }

  init() {
    // Check if token exists. If not, Auth service should have redirected.
    if (!apiService.token) {
        console.log("JournalService init: No token found. Aborting.");
        return;
    }
    console.log("JournalService init: Token found. Initializing...");


    // Setup event listeners only if elements exist
    if (this.newEntryBtn) this.newEntryBtn.addEventListener("click", this.showNewEntryForm.bind(this));
    if (this.cancelBtn) this.cancelBtn.addEventListener("click", this.cancelEditOrView.bind(this));
    if (this.entryForm) this.entryForm.addEventListener("submit", this.handleSaveEntry.bind(this));
    if (this.getAiBtn) this.getAiBtn.addEventListener("click", this.handleGetAIConsultation.bind(this));
    if (this.editEntryBtn) this.editEntryBtn.addEventListener("click", this.showEditEntryForm.bind(this));
    if (this.deleteEntryBtn) this.deleteEntryBtn.addEventListener("click", this.handleDeleteEntry.bind(this));


    // Initial load of journal entries
    this.loadEntries();
  }

  async loadEntries() {
     if (!this.entriesList) return;
     this.entriesList.innerHTML = '<p class="text-center text-muted">Đang tải danh sách...</p>';
    try {
      this.entries = await apiService.getJournalEntries();
      this.renderEntriesList();

      // Automatically select the first entry if available, otherwise show placeholder
      if (this.entries.length > 0) {
         // If there was a previously selected entry, try to re-select it
         const entryToSelect = this.currentEntryId
                               ? this.entries.find(e => e.id === this.currentEntryId)
                               : this.entries[0]; // Default to first
         if (entryToSelect) {
             this.viewEntry(entryToSelect.id);
         } else {
              // If previous ID not found (e.g., deleted), select the first one
              this.viewEntry(this.entries[0].id);
         }
      } else {
        this.showPlaceholderView(); // Show "No entries" placeholder
      }
    } catch (error) {
      console.error("Failed to load entries:", error);
      showNotification("Không thể tải danh sách bài viết.", true);
      this.entriesList.innerHTML = '<p class="text-center error">Lỗi khi tải danh sách.</p>';
       this.showPlaceholderView(); // Show placeholder on error too
    }
  }

  renderEntriesList() {
     if (!this.entriesList) return;
    this.entriesList.innerHTML = ""; // Clear existing list

    if (this.entries.length === 0) {
      this.entriesList.innerHTML = '<p class="text-center text-muted">Chưa có bài viết nào.</p>';
      return;
    }

    // Sort entries by creation date descending (API might already do this)
    // this.entries.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    this.entries.forEach((entry) => {
      const entryItem = document.createElement("div");
      entryItem.className = `entry-item ${entry.id === this.currentEntryId ? "active" : ""}`;
      entryItem.dataset.id = entry.id;

      const date = new Date(entry.created_at);
      // More concise date format for the list
      const formattedDate = date.toLocaleDateString("vi-VN", {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });

      entryItem.innerHTML = `
                <h3>${this.escapeHtml(entry.title)}</h3>
                <div class="date">${formattedDate}</div>
            `;

      // Add click listener to view the entry
      entryItem.addEventListener("click", () => this.viewEntry(entry.id));
      this.entriesList.appendChild(entryItem);
    });
  }

  async viewEntry(id) {
    console.log(`Attempting to view entry ${id}`);
    if (!id) {
         console.warn("viewEntry called with invalid ID.");
         this.showPlaceholderView();
         return;
     }

    try {
       // Fetch the specific entry data (even if we have it cached, ensures freshness)
       // API service handles 401/404 appropriately
      const entry = await apiService.getJournalEntry(id);
      this.currentEntryId = entry.id;
      this.isEditing = false; // Ensure we are in view mode

      // Update entry view elements
      this.entryTitle.textContent = this.escapeHtml(entry.title);
      const date = new Date(entry.created_at);
      this.entryDate.textContent = `Viết lúc: ${date.toLocaleString("vi-VN", {
        weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
      })}`;
      // Use textContent for safety, assuming content is plain text
      // If content can be HTML, careful sanitization is needed on backend/frontend
      this.entryContent.textContent = entry.content;

      // Show entry view, hide editor and placeholder
      this.entryView.classList.remove("hidden");
      this.entryEditor.classList.add("hidden");
      this.noEntrySelectedView.classList.add("hidden");

      // Hide AI section initially when viewing a new entry
      this.aiConsultation.classList.add("hidden");
      this.aiContent.textContent = ""; // Clear previous AI content
      this.getAiBtn.disabled = false; // Re-enable AI button
      this.getAiBtn.innerHTML = '<i class="fas fa-robot"></i> Nhận tư vấn AI';

      // Update active selection in the list
      this.renderEntriesList();

    } catch (error) {
      console.error(`Failed to load entry ${id}:`, error);
      showNotification("Không thể tải chi tiết bài viết.", true);
      // If loading fails, potentially show the placeholder again
      this.showPlaceholderView();
      this.currentEntryId = null; // Reset current entry ID
      this.renderEntriesList(); // Update list highlighting
    }
  }

  // Shows the form for creating a *new* entry
  showNewEntryForm() {
    console.log("Showing new entry form");
    this.isEditing = false;
    this.currentEntryId = null; // No active entry when creating new
    this.entryForm.reset(); // Clear form fields
    this.entryIdInput.value = ''; // Clear hidden ID field
    this.editorTitle.textContent = "Tạo bài viết mới"; // Set editor title

    // Show editor, hide entry view and placeholder
    this.entryView.classList.add("hidden");
    this.noEntrySelectedView.classList.add("hidden");
    this.entryEditor.classList.remove("hidden");
    this.titleInput.focus(); // Focus on the title field

    // Update list highlighting (remove any active state)
    this.renderEntriesList();
  }

  // Shows the form for *editing* the current entry
  showEditEntryForm() {
     if (!this.currentEntryId) {
          showNotification("Vui lòng chọn bài viết để chỉnh sửa.", true);
          return;
     }
     console.log(`Showing edit form for entry ${this.currentEntryId}`);
     this.isEditing = true;

     // Find the current entry data from cache (assuming it's loaded)
     const entry = this.entries.find(e => e.id === this.currentEntryId);
     if (!entry) {
         showNotification("Không tìm thấy dữ liệu bài viết để chỉnh sửa.", true);
         return;
     }

     // Populate form fields
     this.entryForm.reset(); // Clear first
     this.entryIdInput.value = entry.id;
     this.titleInput.value = entry.title;
     this.contentInput.value = entry.content;
     this.editorTitle.textContent = "Chỉnh sửa bài viết"; // Set editor title

     // Show editor, hide entry view and placeholder
     this.entryView.classList.add("hidden");
     this.noEntrySelectedView.classList.add("hidden");
     this.entryEditor.classList.remove("hidden");
     this.titleInput.focus(); // Focus on the title field
   }


  cancelEditOrView() {
     console.log("Cancel action triggered");
    // If currently editing, go back to viewing that entry
    if (this.isEditing && this.currentEntryId) {
      this.viewEntry(this.currentEntryId);
    }
    // If creating new, but entries exist, view the first one
    else if (!this.isEditing && this.entries.length > 0) {
        const entryToView = this.currentEntryId ? this.currentEntryId : this.entries[0].id;
        this.viewEntry(entryToView);
    }
    // If creating new and no entries exist, show placeholder
    else {
      this.showPlaceholderView();
    }
     this.isEditing = false; // Reset editing state
  }

  // Handles both creating and updating entries
  async handleSaveEntry(event) {
    event.preventDefault();

    const title = this.titleInput.value.trim();
    const content = this.contentInput.value.trim();
    const entryId = this.entryIdInput.value; // Get ID from hidden input

    if (!title || !content) {
        showNotification("Tiêu đề và nội dung không được để trống.", true);
        return;
    }

     const submitButton = this.entryForm.querySelector('button[type="submit"]');
     submitButton.disabled = true;
     submitButton.textContent = 'Đang lưu...';

    try {
        let savedEntry;
        if (this.isEditing && entryId) {
             // Update existing entry
             console.log(`Updating entry ${entryId}`);
             // Send only updated fields if API supports partial updates via PUT/PATCH
             // Here, we send both title and content as per the schemas.py definition
             savedEntry = await apiService.updateJournalEntry(entryId, { title, content });
             showNotification("Bài viết đã được cập nhật!");
             // Update the entry in the local cache
             const index = this.entries.findIndex(e => e.id === savedEntry.id);
             if (index !== -1) {
                 this.entries[index] = savedEntry;
             } else {
                  // Should not happen if update was successful, but handle defensively
                  this.entries.unshift(savedEntry); // Add if somehow missing
             }

        } else {
            // Create new entry
            console.log("Creating new entry");
            savedEntry = await apiService.createJournalEntry(title, content);
            showNotification("Bài viết mới đã được lưu!");
             // Add the new entry to the beginning of the local cache
            this.entries.unshift(savedEntry);
        }

        // Refresh the list and view the saved entry
        this.currentEntryId = savedEntry.id; // Set current ID to the saved one
        this.isEditing = false; // Ensure back to view mode state
        this.renderEntriesList(); // Update list display
        this.viewEntry(savedEntry.id); // View the newly saved/updated entry

    } catch (error) {
        console.error("Failed to save entry:", error);
        showNotification(`Lưu bài viết thất bại: ${error.message}`, true);
    } finally {
        submitButton.disabled = false;
         submitButton.textContent = 'Lưu bài viết';
    }
  }

   async handleDeleteEntry() {
     if (!this.currentEntryId) {
          showNotification("Vui lòng chọn bài viết để xóa.", true);
          return;
     }

     // Confirm deletion
     if (!confirm(`Bạn có chắc chắn muốn xóa bài viết "${this.entryTitle.textContent}" không? Hành động này không thể hoàn tác.`)) {
         return;
     }

      console.log(`Attempting to delete entry ${this.currentEntryId}`);
      this.deleteEntryBtn.disabled = true; // Disable button during request

     try {
          await apiService.deleteJournalEntry(this.currentEntryId);
          showNotification("Bài viết đã được xóa.");

          // Remove the entry from the local cache
          this.entries = this.entries.filter(entry => entry.id !== this.currentEntryId);

          // Clear current selection and load list (will select first or show placeholder)
          this.currentEntryId = null;
          this.loadEntries(); // Reload the list view

     } catch (error) {
          console.error(`Failed to delete entry ${this.currentEntryId}:`, error);
          showNotification(`Xóa bài viết thất bại: ${error.message}`, true);
          this.deleteEntryBtn.disabled = false; // Re-enable button on error
     }
   }


  async handleGetAIConsultation() {
    if (!this.currentEntryId) {
        showNotification("Vui lòng chọn một bài viết để nhận tư vấn.", true);
        return;
    }
     if (!this.aiConsultation || !this.aiContent || !this.aiLoading || !this.getAiBtn) return;


     console.log(`Requesting AI consultation for entry ${this.currentEntryId}`);
     this.getAiBtn.disabled = true;
     this.getAiBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang lấy tư vấn...';
     this.aiConsultation.classList.remove("hidden"); // Show the section
     this.aiLoading.classList.remove("hidden"); // Show loading indicator
     this.aiContent.classList.add("hidden"); // Hide previous content
     this.aiContent.textContent = ""; // Clear previous content

    try {
      const result = await apiService.getAIConsultation(this.currentEntryId);

      if (result && result.consultation) {
          this.aiContent.textContent = result.consultation; // Display new content
           this.aiContent.classList.remove("hidden"); // Show content area
          showNotification("Đã nhận được tư vấn từ AI!");
      } else {
          throw new Error("Phản hồi AI không hợp lệ.");
      }

    } catch (error) {
      console.error("Failed to get AI consultation:", error);
      this.aiContent.innerHTML = `<p class="error"><i>Lỗi khi lấy tư vấn AI: ${error.message}</i></p>`; // Show error in content area
       this.aiContent.classList.remove("hidden"); // Show error area
      showNotification("Lấy tư vấn AI thất bại.", true);
    } finally {
        this.getAiBtn.disabled = false;
        this.getAiBtn.innerHTML = '<i class="fas fa-robot"></i> Nhận tư vấn AI';
        this.aiLoading.classList.add("hidden"); // Hide loading indicator regardless of outcome
    }
  }

   showPlaceholderView() {
     if (!this.entryView || !this.entryEditor || !this.noEntrySelectedView) return;
     console.log("Showing placeholder view");
     this.entryView.classList.add("hidden");
     this.entryEditor.classList.add("hidden");
     this.noEntrySelectedView.classList.remove("hidden");
     this.currentEntryId = null; // No entry is selected
     this.isEditing = false;
      this.renderEntriesList(); // Ensure list highlights are cleared
   }

  // Utility to escape HTML for safe display
  escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) return '';
    return unsafe
      .toString()
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
}

// Export the class for use in HTML modules
export { JournalService };