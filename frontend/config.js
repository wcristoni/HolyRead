// HolyRead — frontend runtime config
window.HOLYREAD_CONFIG = {
  // In dev (localhost / LAN IP) → local FastAPI on :8000.
  // In prod → backend deployed at Railway.
  API_BASE: (() => {
    const { protocol, hostname } = window.location;
    if (hostname === 'localhost' || hostname === '127.0.0.1' || /^\d+\.\d+\.\d+\.\d+$/.test(hostname)) {
      return `${protocol}//${hostname}:8000`;
    }
    return 'https://holyread-production.up.railway.app';
  })(),
};
