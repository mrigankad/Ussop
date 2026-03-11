// Token management
const Auth = {
    getToken() {
        return localStorage.getItem('access_token');
    },

    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },

    getUser() {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    },

    setTokens(accessToken, refreshToken) {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
    },

    clear() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
    },

    isAuthenticated() {
        return !!this.getToken();
    },

    // API request with auth header
    async api(url, options = {}) {
        const token = this.getToken();

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(url, { ...options, headers });

        if (response.status === 401 && this.getRefreshToken()) {
            const refreshed = await this.refreshToken();
            if (refreshed) {
                return this.api(url, options);
            } else {
                this.redirectToLogin();
                return null;
            }
        }

        return response;
    },

    async refreshToken() {
        try {
            const response = await fetch('/api/v1/auth/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: this.getRefreshToken() })
            });

            if (response.ok) {
                const data = await response.json();
                this.setTokens(data.access_token, this.getRefreshToken());
                return true;
            }
        } catch (e) {
            console.error('Token refresh failed:', e);
        }
        return false;
    },

    async logout() {
        try {
            const token = this.getToken();
            if (token) {
                await fetch('/api/v1/auth/logout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token })
                });
            }
        } catch (e) {
            console.error('Logout error:', e);
        } finally {
            this.clear();
            this.redirectToLogin();
        }
    },

    redirectToLogin() {
        if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
        }
    },

    async checkAuth() {
        if (window.location.pathname.includes('/login')) return;

        const token = this.getToken();
        if (!token) {
            this.redirectToLogin();
            return;
        }

        try {
            const response = await fetch('/api/v1/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                const refreshed = await this.refreshToken();
                if (!refreshed) this.redirectToLogin();
            } else {
                const user = await response.json();
                localStorage.setItem('user', JSON.stringify(user));
                this.updateUI(user);
            }
        } catch (e) {
            console.error('Auth check failed:', e);
            this.redirectToLogin();
        }
    },

    updateUI(user) {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && !document.querySelector('.user-info')) {
            const userDiv = document.createElement('div');
            userDiv.className = 'user-info';
            userDiv.innerHTML = `
                <div class="user-name">${user.username}</div>
                <div class="user-role">${user.roles.join(', ')}</div>
                <button onclick="Auth.logout()" class="btn-logout">Logout</button>
            `;
            sidebar.appendChild(userDiv);
        }
    }
};

// ─── Toast notification system ────────────────────────────────────────────────
const Toast = {
    container: null,

    _ensureContainer() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            document.body.appendChild(this.container);
        }
    },

    show(message, type = 'info', duration = 3500) {
        this._ensureContainer();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icons = { success: '&#10003;', error: '&#10007;', warning: '&#9888;', info: '&#9432;' };
        toast.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span class="toast-msg">${message}</span>`;

        this.container.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    success(msg) { this.show(msg, 'success'); },
    error(msg)   { this.show(msg, 'error', 5000); },
    warning(msg) { this.show(msg, 'warning'); },
    info(msg)    { this.show(msg, 'info'); }
};

document.addEventListener('DOMContentLoaded', () => {
    Auth.checkAuth();
});
