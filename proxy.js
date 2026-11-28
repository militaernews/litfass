// Routing middleware: expose the feed server under /litfass on the site's domain.
// Its address is a Vercel environment variable, so no backend host is committed.
// Set LITFASS_ORIGIN to the origin (scheme, host and port) of the feed server.

export default async function proxy(request) {
	const origin = process.env.LITFASS_ORIGIN;
	if (!origin) {
		return new Response("Feed proxy is not configured", { status: 503 });
	}

	const { pathname, search } = new URL(request.url);
	const target = new URL(`${pathname}${search}`, origin);
	const headers = new Headers(request.headers);
	headers.delete("host");

	const init = { method: request.method, headers, redirect: "manual" };
	if (request.method !== "GET" && request.method !== "HEAD") {
		init.body = request.body;
		init.duplex = "half";
	}
	return fetch(target, init);
}
