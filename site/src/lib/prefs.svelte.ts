export type Theme = 'system' | 'light' | 'dark';
export const THEMES: Theme[] = ['system', 'light', 'dark'];

const THEME_KEY = 'litfass:theme';

export const prefs = $state({
	theme: 'system' as Theme,
	systemDark: false,
	telegramDark: null as boolean | null,
	inTelegram: false
});

let started = false;

function read(key: string): string | null {
	try {
		return localStorage.getItem(key);
	} catch {
		return null;
	}
}

function write(key: string, value: string) {
	try {
		localStorage.setItem(key, value);
	} catch {
		// still applied for this visit
	}
}

/** Reads the remembered choice once; app.html already applied it before the first paint. */
export function startPrefs() {
	if (started) return;
	started = true;
	const theme = read(THEME_KEY);
	prefs.theme = theme === 'light' || theme === 'dark' ? theme : 'system';
	const media = matchMedia('(prefers-color-scheme: dark)');
	prefs.systemDark = media.matches;
	media.addEventListener('change', (event) => {
		prefs.systemDark = event.matches;
		applyTheme();
	});
	applyTheme();
}

/** Telegram's client theme takes over when "system" is selected inside a Mini App. */
export function setTelegramTheme(scheme: 'light' | 'dark' | undefined, params: Record<string, string> | undefined) {
	prefs.inTelegram = Boolean(scheme);
	prefs.telegramDark = scheme === 'dark' ? true : scheme === 'light' ? false : null;
	const root = document.documentElement;
	if (scheme) root.dataset.telegram = 'true';
	else delete root.dataset.telegram;
	if (params) {
		for (const [key, value] of Object.entries(params)) {
			if (/^[a-zA-Z0-9-]+$/.test(key) && value.startsWith('#')) root.style.setProperty(`--tg-${key}`, value);
		}
	}
	applyTheme();
}

function applyTheme() {
	const dark = prefs.theme === 'dark' || (prefs.theme === 'system' && (prefs.telegramDark ?? prefs.systemDark));
	const root = document.documentElement;
	if (dark) root.dataset.theme = 'dark';
	else if (prefs.theme === 'light') root.dataset.theme = 'light';
	else delete root.dataset.theme;
}

export function setTheme(theme: Theme) {
	prefs.theme = theme;
	write(THEME_KEY, theme);
	applyTheme();
}
