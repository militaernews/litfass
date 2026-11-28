/*
 * The only Vercel function: forwards every /litfass/* request to the feed server
 * (server/litfass_server/web.py), which runs next to its SQLite database. API_ORIGIN,
 * set in the Vercel project, says where that server is; the address is never in the repo
 * or in a public feed URL.
 */
const FORWARDED_HEADERS = ['authorization', 'content-type', 'accept', 'user-agent', 'x-telegram-init-data'];
const TIMEOUT_MS = 25_000;

export async function proxy(request: Request, origin = process.env.API_ORIGIN ?? ''): Promise<Response> {
	if (!origin) return Response.json({ ok: false, error: 'api_not_configured' }, { status: 503 });
	const incoming = new URL(request.url);
	const path = (incoming.searchParams.get('path') ?? '').replace(/^\/+/u, '');
	if (!/^[a-z0-9/_-]*$/iu.test(path)) return Response.json({ ok: false, error: 'not_found' }, { status: 404 });
	const target = new URL(`${origin.replace(/\/+$/u, '')}/litfass/${path}`);
	incoming.searchParams.forEach((value, key) => {
		if (key !== 'path') target.searchParams.append(key, value);
	});
	const headers = new Headers();
	for (const name of FORWARDED_HEADERS) {
		const value = request.headers.get(name);
		if (value) headers.set(name, value);
	}
	try {
		const response = await fetch(target, {
			method: request.method,
			headers,
			body: request.method === 'GET' || request.method === 'HEAD' ? null : await request.arrayBuffer(),
			signal: AbortSignal.timeout(TIMEOUT_MS)
		});
		const forward = (name: string) => response.headers.get(name);
		return new Response(response.body, {
			status: response.status,
			headers: {
				'content-type': forward('content-type') ?? 'application/json; charset=utf-8',
				'cache-control': forward('cache-control') ?? 'no-store',
				'access-control-allow-origin': forward('access-control-allow-origin') ?? '*',
				'access-control-allow-methods': forward('access-control-allow-methods') ?? 'GET, POST, OPTIONS',
				'access-control-allow-headers': forward('access-control-allow-headers') ?? 'Content-Type'
			}
		});
	} catch {
		return Response.json({ ok: false, error: 'unavailable' }, { status: 503 });
	}
}

export const GET = (request: Request) => proxy(request);
export const POST = (request: Request) => proxy(request);
export const OPTIONS = (request: Request) => proxy(request);
