/**
 * Cloudflare Worker: Streamlit Proxy dengan WebSocket Support
 * -----------------------------------------------------------
 * Forward semua request dari larisai.my.id ke laris-ai.streamlit.app
 * - HTTP biasa: rewrite HTML agar tidak redirect ke streamlit.app
 * - WebSocket:  bypass proxy (Streamlit perlu ini untuk real-time)
 * - Auto-deploy dari GitHub (lihat wrangler.toml)
 */

const STREAMLET_HOST = "laris-ai.streamlit.app";
const CUSTOM_HOST = "larisai.my.id";
const CUSTOM_WWW = "www.larisai.my.id";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const targetUrl = new URL(request.url);

    // 1. Ganti tujuan ke Streamlit asli
    targetUrl.hostname = STREAMLET_HOST;
    targetUrl.protocol = "https:";

    // 2. Set headers yang benar untuk Streamlit
    const headers = new Headers(request.headers);
    headers.set("Host", STREAMLET_HOST);
    headers.set("X-Forwarded-Host", url.hostname);
    headers.set("X-Forwarded-Proto", "https");

    // 3. WebSocket Upgrade: bypass proxy, langsung forward
    if (request.headers.get("Upgrade") === "websocket") {
      const newRequest = new Request(targetUrl, {
        method: request.method,
        headers: headers,
        body: request.body,
      });
      return fetch(newRequest);
    }

    // 4. Request biasa: rewrite response
    const newRequest = new Request(targetUrl, {
      method: request.method,
      headers: headers,
      body: request.body,
      redirect: "manual",
    });

    let response = await fetch(newRequest);

    // 5. Handle redirects (301/302/307/308) — ganti tujuan balik ke domain kita
    if ([301, 302, 307, 308].includes(response.status)) {
      const location = response.headers.get("Location");
      if (location) {
        const newLocation = location
          .replace(`https://${STREAMLET_HOST}`, `https://${url.hostname}`)
          .replace(`//${STREAMLET_HOST}`, `//${url.hostname}`);
        const newHeaders = new Headers(response.headers);
        newHeaders.set("Location", newLocation);
        return new Response(response.body, {
          status: response.status,
          statusText: response.statusText,
          headers: newHeaders,
        });
      }
    }

    // 6. Rewrite HTML/JS — ganti semua sebutan streamlit.app ke domain kita
    const contentType = response.headers.get("Content-Type") || "";
    if (contentType.includes("text/html") || contentType.includes("javascript")) {
      let text = await response.text();
      const customHost = url.hostname;
      text = text.split(STREAMLET_HOST).join(customHost);

      // Hapus header keamanan yang memblokir iframe/proxy
      const newHeaders = new Headers(response.headers);
      newHeaders.delete("Content-Security-Policy");
      newHeaders.delete("Content-Security-Policy-Report-Only");
      newHeaders.delete("X-Frame-Options");

      return new Response(text, {
        status: response.status,
        statusText: response.statusText,
        headers: newHeaders,
      });
    }

    // 7. Aset lain (gambar, css) — teruskan apa adanya
    return response;
  },
};
