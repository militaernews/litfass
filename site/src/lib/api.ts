/** Calls the Telegram-authenticated management API on the feed server. */

import { getInitData } from './telegram';

let devInitData = '';

/** In dev, a pasted initData can stand in for a Mini App launch. */
export function setDevInitData(value: string): void {
	devInitData = value.trim();
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
