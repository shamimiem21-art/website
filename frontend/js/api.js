// CUSTOM TOAST NOTIFICATION UTILITY
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;
    
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "info-circle";
    if (type === "success") icon = "check-circle";
    if (type === "error") icon = "exclamation-circle";
    if (type === "warning") icon = "exclamation-triangle";
    
    toast.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove toast after 4 seconds
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// API CLIENT WRAPPER
const API = {
    async request(url, options = {}) {
        // Headers configuration
        options.headers = {
            "Content-Type": "application/json",
            ...options.headers
        };
        
        // Handle request body
        if (options.body && typeof options.body === "object") {
            options.body = JSON.stringify(options.body);
        }
        
        try {
            const response = await fetch(url, options);
            const data = await response.json().catch(() => ({}));
            
            if (!response.ok) {
                const errorMsg = data.error || `HTTP error! status: ${response.status}`;
                throw { status: response.status, message: errorMsg, data };
            }
            
            return data;
        } catch (error) {
            console.error(`[API Error] Request to ${url} failed:`, error);
            throw error;
        }
    },

    // GET Request
    async get(url, params = {}) {
        let queryString = "";
        const keys = Object.keys(params);
        if (keys.length > 0) {
            const searchParams = new URLSearchParams();
            keys.forEach(key => {
                if (params[key] !== undefined && params[key] !== null) {
                    searchParams.append(key, params[key]);
                }
            });
            queryString = "?" + searchParams.toString();
        }
        return this.request(url + queryString, { method: "GET" });
    },

    // POST Request
    async post(url, body = {}) {
        return this.request(url, { method: "POST", body });
    },

    // PUT Request
    async put(url, body = {}) {
        return this.request(url, { method: "PUT", body });
    },

    // DELETE Request
    async delete(url) {
        return this.request(url, { method: "DELETE" });
    }
};
