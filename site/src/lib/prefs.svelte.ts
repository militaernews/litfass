export type Theme = 'system' | 'light' | 'dark';
export const THEMES: Theme[] = ['system', 'light', 'dark'];

const THEME_KEY = 'litfass:theme';

export const prefs = $state({ theme: 'system' as Theme, systemDark: false });

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
	media.addEventListener('change', (event) => (prefs.systemDark = event.matches));
}

export function setTheme(theme: Theme) {
	prefs.theme = theme;
	if (theme === 'system') delete document.documentElement.dataset.theme;
	else document.documentElement.dataset.theme = theme;
	write(THEME_KEY, theme);
}
