export interface Change {
	version: string;
	date: string;
	de: string[];
	en: string[];
}

export const CHANGES: Change[] = [
	{
		version: '1.4',
		date: '2026-11-28',
		de: [
			'Pflicht-Tasks: Kanal beitreten, per Bot Mitgliedschaft prüfen, ohne Timer und ohne Überspringen.',
			'Video-Anzeigen aus Telegram-Kanalposts mit Modal- und Vollbild-Interstitials.',
			'Deutsch und Englisch per Paraglide, Auswahl in den Einstellungen.'
		],
		en: [
			'Required join tasks verified by the bot, with no timer and no skipping.',
			'Video adverts from Telegram channel posts with modal and fullscreen interstitials.',
			'German and English via Paraglide, switchable in settings.'
		]
	},
	{
		version: '1.3',
		date: '2026-11-28',
		de: [
			'Installierbare PWA mit Service Worker und smartem Caching.',
			'Telegram Stars: Kampagnen aktivieren, Klicks vergüten, Werbeplätze erhalten Stars.',
			'Statistiken pro Kampagne mit CTR und werbeplatzbasierte Zahlen.'
		],
		en: [
			'Installable PWA with a service worker and smart caching.',
			'Telegram Stars: activate campaigns, pay per click, credit placements.',
			'Per-campaign statistics with CTR and placement totals.'
		]
	},
	{
		version: '1.2',
		date: '2026-11-28',
		de: [
			'Anzeigen-Verwaltung im Web: Anzeigen, Werbeplätze und Statistiken.',
			'Einrichtungshandler für Bot, Web und Python.'
		],
		en: [
			'Web manager for adverts, placements and statistics.',
			'Setup guide for the bot, web and Python integrations.'
		]
	},
	{
		version: '1.1',
		date: '2026-11-28',
		de: ['Dunkles Design im Stil von MilitärNews.', 'Neues Menü und nützliche Bot-Befehle.'],
		en: ['Dark theme in the MilitärNews style.', 'New bot menu and useful commands.']
	}
];
