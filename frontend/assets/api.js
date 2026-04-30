// HolyRead — minimal API client. CORS-protected, retried once on 5xx.
(function () {
  const cfg = window.HOLYREAD_CONFIG || {};
  const API_BASE = (cfg.API_BASE || '').replace(/\/$/, '');

  async function apiGet(path, { retries = 1 } = {}) {
    const url = API_BASE + path;
    let lastErr = null;
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(url, {
          method: 'GET',
          headers: { 'Accept': 'application/json' },
          // Browser enforces CORS via the server's Allow-Origin response.
          credentials: 'omit',
          mode: 'cors',
        });
        if (res.status >= 500 && attempt < retries) {
          await new Promise(r => setTimeout(r, 250 * (attempt + 1)));
          continue;
        }
        if (!res.ok) {
          let detail = res.statusText;
          try { detail = (await res.json()).detail || detail; } catch {}
          const e = new Error(`API ${res.status}: ${detail}`);
          e.status = res.status;
          throw e;
        }
        return await res.json();
      } catch (e) {
        lastErr = e;
        if (attempt >= retries) break;
      }
    }
    throw lastErr;
  }

  const api = {
    apiBase: API_BASE,
    async listVersions() {
      return (await apiGet('/api/bible/versions')).versions;
    },
    async loadVersion(version) {
      return await apiGet(`/api/bible/${encodeURIComponent(version)}`);
    },
    async chapter(version, book, chapter) {
      return await apiGet(`/api/bible/${encodeURIComponent(version)}/${book}/${chapter}`);
    },
    async search(version, q, limit = 40) {
      const params = new URLSearchParams({ q, limit: String(limit) });
      return await apiGet(`/api/bible/${encodeURIComponent(version)}/search?${params}`);
    },
    async hebrew(book, chapter, verse, lang = 'en') {
      const qs = `?lang=${encodeURIComponent(lang)}`;
      return await apiGet(`/api/original/hebrew/${book}/${chapter}/${verse}${qs}`);
    },
    async greek(book, chapter, verse, lang = 'en') {
      const qs = `?lang=${encodeURIComponent(lang)}`;
      return await apiGet(`/api/original/greek/${book}/${chapter}/${verse}${qs}`);
    },
  };

  window.HolyReadAPI = api;
})();
