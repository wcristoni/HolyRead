// HolyRead — frontend runtime config
// Override this file per deployment (or load via env-templated build).
window.HOLYREAD_CONFIG = {
  // Backend base URL (no trailing slash). For local dev, point to FastAPI.
  // For prod, set to your Railway URL: https://holyread-backend.up.railway.app
  API_BASE: (() => {
    // If served from localhost or LAN IP, default backend on port 8000 of same host.
    const { protocol, hostname } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1' || /^\d+\.\d+\.\d+\.\d+$/.test(hostname)) {
      return `${protocol}//${hostname}:8000`;
    }
    // Production fallback — replace at deploy time.
    return 'https://CHANGE_ME.up.railway.app';
  })(),
};
