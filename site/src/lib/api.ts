/** Calls the Telegram-authenticated management API on the feed server. */

import { getInitData } from './telegram';

let devInitData = '';

/** In dev, a pasted initData can stand in for a Mini App launch. */
export function setDevInitData(value: string): void {
	devInitData = value.trim();
}

/** Verifies a join task through the feed server; the bot checks membership with getChatMember. */
export async function verifyTask(ad: string, feedUrl: string): Promise<{ joined: boolean; counted: boolean }> {
	const initData = devInitData || (await getInitData());
	const key = feedUrl.match(/\/v1\/feed\/([^/?#]+)/)?.[1] ?? '';
	const response = await fetch('/litfass/v1/task/verify', {
		method: 'POST',
		headers: { 'content-type': 'application/json', 'x-telegram-init-data': initData },
		body: JSON.stringify({ ad, key })
	});
	const data = await response.json();
	if (!response.ok || !data.ok) throw new Error(String(data.error ?? `Server returned ${response.status}`));
	return data as { joined: boolean; counted: boolean };
}

export async function call<T>(action: string, payload: Record<string, unknown> = {}): Promise<T> {
	const initData = devInitData || (await getInitData());
	const response = await fetch('/litfass/v1/admin/ui', {
		method: 'POST',
		headers: { 'content-type': 'application/json', 'x-telegram-init-data': initData },
		body: JSON.stringify({ action, ...payload })
	});
	let data: Record<string, unknown>;
	try {
		data = await response.json();
	} catch {
		throw new Error(`Server returned ${response.status}`);
	}
	if (!response.ok || data.ok !== true) throw new Error(String(data.error ?? `Server returned ${response.status}`));
	return data as T;
}
