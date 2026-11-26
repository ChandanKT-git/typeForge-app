import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const api = axios.create({
    baseURL: API,
    withCredentials: true,
});

// Bearer fallback (cross-site cookies can be blocked by some browsers)
let bearerToken = null;
try {
    bearerToken = localStorage.getItem("tf_token");
} catch (e) {
    /* ignore */
}

export function setAuthToken(t) {
    bearerToken = t || null;
    try {
        if (t) localStorage.setItem("tf_token", t);
        else localStorage.removeItem("tf_token");
    } catch (e) {
        /* ignore */
    }
}

api.interceptors.request.use((config) => {
    if (bearerToken) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${bearerToken}`;
    }
    return config;
});

api.interceptors.response.use(
    (res) => res,
    async (err) => {
        if (err.response?.status === 401 && !err.config._retry && !err.config.url.includes("/auth/login") && !err.config.url.includes("/auth/refresh")) {
            err.config._retry = true;
            try {
                const { data } = await api.post("/auth/refresh");
                setAuthToken(data.token);
                return api(err.config);
            } catch (e) {
                setAuthToken(null);
                if (window.location.pathname !== "/login" && window.location.pathname !== "/register") {
                    window.location.href = "/login";
                }
            }
        }
        return Promise.reject(err);
    }
);

export default api;
