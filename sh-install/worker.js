// Serve the canonical Mycelium installer at https://sh.fungos.dev/install.sh.
// The Worker proxies the repository copy with a short cache, so the URL is
// stable while the installer keeps shipping from one place.

const UPSTREAM =
  "https://raw.githubusercontent.com/fungOS-linux/mycelium/master/install.sh";

export default {
  async fetch(request) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("method not allowed\n", {
        status: 405,
        headers: { allow: "GET, HEAD" },
      });
    }

    const response = await fetch(UPSTREAM, {
      cf: { cacheTtl: 300, cacheEverything: true },
    });
    if (!response.ok) {
      return new Response("installer temporarily unavailable\n", { status: 502 });
    }

    const headers = new Headers(response.headers);
    headers.set("content-type", "text/x-shellscript; charset=utf-8");
    headers.set("cache-control", "public, max-age=300");
    headers.set("x-content-type-options", "nosniff");

    return new Response(request.method === "HEAD" ? null : response.body, {
      status: 200,
      headers,
    });
  },
};
