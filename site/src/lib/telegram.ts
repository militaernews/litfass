/** Telegram Mini App launch, in the same shape ww3-sv uses: initData only inside a launch. */

const SCRIPT_URL = 'https://telegram.org/js/telegram-web-app.js';

export interface TelegramUser {
	id: number;
	first_name?: string;
	username?: string;
	photo_url?: string;
}

interface TelegramWebApp {
	initData?: string;
	initDataUnsafe?: { user?: TelegramUser };
	colorScheme?: 'light' | 'dark';
	themeParams?: Record<string, string>;
	ready?: () => void;
	expand?: () => void;
	onEvent?: (event: string, callback: () => void) => void;
	offEvent?: (event: string, callback: () => void) => void;
}

type TelegramWindow = Window & { Telegram?: { WebApp?: TelegramWebApp } };

export function isTelegramLaunch(hash: string): boolean {
	const raw = hash.startsWith('#') ? hash.slice(1) : hash;
	return Boolean(new URLSearchParams(raw).get('tgWebAppData'));
}

function webApp(): TelegramWebApp | undefined {
	return typeof window === 'undefined' ? undefined : (window as TelegramWindow).Telegram?.WebApp;
}

let loading: Promise<TelegramWebApp | null> | null = null;

/** Loads Telegram's script once, only in a Mini App; resolves to null in a normal browser. */
export function loadTelegram(): Promise<TelegramWebApp | null> {
	if (typeof window === 'undefined') return Promise.resolve(null);
	const existing = webApp();
	if (existing?.initData) return Promise.resolve(existing);
	if (!isTelegramLaunch(window.location.hash)) return Promise.resolve(null);
	if (loading) return loading;
	loading = new Promise((resolve) => {
		const script = document.createElement('script');
		script.src = SCRIPT_URL;
		script.async = true;
		script.onload = () => {
			const app = webApp();
			app?.ready?.();
			app?.expand?.();
			resolve(app?.initData ? app : null);
		};
		script.onerror = () => resolve(null);
		document.head.append(script);
	});
	return loading;
}

/** Raw initData for the API header, or '' outside Telegram. */
export async function getInitData(): Promise<string> {
	return (await loadTelegram())?.initData ?? '';
}

export async function getTelegramUser(): Promise<TelegramUser | null> {
	return (await loadTelegram())?.initDataUnsafe?.user ?? null;
}

/** Follows the Telegram client's light/dark scheme and theme colours while the Mini App is open. */
export function watchTelegramTheme(callback: (scheme: 'light' | 'dark' | undefined, params?: Record<string, string>) => void) {
	let stopped = false;
	let unsubscribe: (() => void) | undefined;
	void loadTelegram().then((app) => {
		if (!app || stopped) return;
		const update = () => callback(app.colorScheme, app.themeParams);
		update();
		app.onEvent?.('themeChanged', update);
		unsubscribe = () => app.offEvent?.('themeChanged', update);
	});
	return () => {
		stopped = true;
		unsubscribe?.();
	};
}
