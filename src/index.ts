/**
 * litfass: house adverts for web games and Telegram Mini Apps.
 *
 * A feed is a small JSON document listing your own adverts (channels, other projects, partners).
 * Nothing here talks to an ad network or tracks anyone: the feed is bundled or fetched by the app,
 * a frequency cap lives in the viewer's storage, and the reward is granted by the app itself.
 */

export type Placement = 'rewarded' | 'banner' | 'chat';

export interface AdText {
	title: string;
	body: string;
	/** Label of the link button */
	cta: string;
}

export interface Ad {
	id: string;
	/** Where the advert may appear; all placements when omitted */
	placements?: Placement[];
	/** Relative chance of being picked; 1 when omitted, 0 disables the advert */
	weight?: number;
	/** ISO dates (inclusive start, exclusive end) limiting when the advert runs */
	start?: string;
	end?: string;
	/** An emoji shown when there is no image */
	emoji?: string;
	/** An image URL; keep it on your own origin to avoid third-party requests */
	image?: string;
	/** Where the button leads; t.me links open inside Telegram */
	url: string;
	/** Texts per language code; `en` is the fallback */
	text: Record<string, AdText>;
}

export interface Feed {
	version: 1;
	ads: Ad[];
}

const PLACEMENTS: readonly Placement[] = ['rewarded', 'banner', 'chat'];

function isText(value: unknown): value is AdText {
	if (!value || typeof value !== 'object') return false;
	const text = value as Record<string, unknown>;
	return ['title', 'body', 'cta'].every((key) => typeof text[key] === 'string' && text[key] !== '');
}

function isDate(value: unknown): boolean {
	return value === undefined || (typeof value === 'string' && !Number.isNaN(Date.parse(value)));
}

/** Validates an ad; returns null for anything a renderer could trip over */
export function parseAd(value: unknown): Ad | null {
	if (!value || typeof value !== 'object') return null;
	const ad = value as Record<string, unknown>;
	if (typeof ad.id !== 'string' || !ad.id) return null;
	if (typeof ad.url !== 'string' || !/^https:\/\//.test(ad.url)) return null;
	if (!ad.text || typeof ad.text !== 'object') return null;
	const text = Object.fromEntries(Object.entries(ad.text).filter(([, entry]) => isText(entry)));
	if (!text.en) return null;
	if (ad.weight !== undefined && (typeof ad.weight !== 'number' || ad.weight < 0)) return null;
	if (!isDate(ad.start) || !isDate(ad.end)) return null;
	if (
		ad.placements !== undefined &&
		(!Array.isArray(ad.placements) || !ad.placements.every((p) => PLACEMENTS.includes(p)))
	) {
		return null;
	}
	if (ad.image !== undefined && typeof ad.image !== 'string') return null;
	if (ad.emoji !== undefined && typeof ad.emoji !== 'string') return null;
	return { ...(ad as unknown as Ad), text: text as Record<string, AdText> };
}

/** Reads a feed, dropping invalid adverts instead of failing as a whole */
export function parseFeed(value: unknown): Feed {
	const feed = value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
	const ads = Array.isArray(feed.ads) ? feed.ads.map(parseAd).filter((ad): ad is Ad => !!ad) : [];
	return { version: 1, ads };
}

export interface PickOptions {
	placement: Placement;
	now?: Date;
	/** Ids to skip, e.g. the advert shown last */
	exclude?: readonly string[];
	/** Injectable for tests; returns [0, 1) */
	random?: () => number;
}

/** The adverts that may run in a placement right now */
export function activeAds(feed: Feed, placement: Placement, now: Date = new Date()): Ad[] {
	const time = now.getTime();
	return feed.ads.filter(
		(ad) =>
			(ad.weight ?? 1) > 0 &&
			(!ad.placements || ad.placements.includes(placement)) &&
			(!ad.start || Date.parse(ad.start) <= time) &&
			(!ad.end || time < Date.parse(ad.end))
	);
}

/** A weighted random advert; falls back to excluded ones rather than showing nothing */
export function pickAd(feed: Feed, options: PickOptions): Ad | null {
	const active = activeAds(feed, options.placement, options.now);
	const fresh = active.filter((ad) => !options.exclude?.includes(ad.id));
	const pool = fresh.length ? fresh : active;
	const total = pool.reduce((sum, ad) => sum + (ad.weight ?? 1), 0);
	if (!total) return null;
	let roll = (options.random ?? Math.random)() * total;
	for (const ad of pool) {
		roll -= ad.weight ?? 1;
		if (roll < 0) return ad;
	}
	return pool[pool.length - 1];
}

/** The advert's texts in a language, e.g. `de` or `pt-BR`, falling back to the base language and English */
export function localize(ad: Ad, lang: string): AdText {
	const base = lang.toLowerCase().split(/[-_]/)[0];
	return ad.text[lang] ?? ad.text[base] ?? ad.text.en;
}

/** Minimal storage interface so a cap works with localStorage, sessionStorage or a test double */
export interface CapStorage {
	getItem(key: string): string | null;
	setItem(key: string, value: string): void;
}

export interface FrequencyCap {
	/** Views left in the current window */
	remaining(now?: Date): number;
	/** Records a view; false when the cap was already reached */
	record(now?: Date): boolean;
}

/**
 * At most `max` views per `windowMs`, kept in the viewer's own storage. Storage that throws
 * (private mode, blocked site data) degrades to an in-memory cap for the page's lifetime.
 */
export function frequencyCap(options: {
	key: string;
	max: number;
	windowMs: number;
	storage?: CapStorage | null;
}): FrequencyCap {
	let memory: number[] = [];
	const read = (now: number): number[] => {
		let views = memory;
		try {
			const raw = options.storage?.getItem(options.key);
			if (raw) views = (JSON.parse(raw) as unknown[]).filter((v): v is number => typeof v === 'number');
		} catch {
			// fall back to memory
		}
		return views.filter((time) => now - time < options.windowMs);
	};
	const write = (views: number[]) => {
		memory = views;
		try {
			options.storage?.setItem(options.key, JSON.stringify(views));
		} catch {
			// memory only
		}
	};
	return {
		remaining(now = new Date()) {
			return Math.max(0, options.max - read(now.getTime()).length);
		},
		record(now = new Date()) {
			const time = now.getTime();
			const views = read(time);
			if (views.length >= options.max) return false;
			write([...views, time]);
			return true;
		}
	};
}

interface TelegramWebApp {
	openTelegramLink?: (url: string) => void;
	openLink?: (url: string) => void;
	initData?: string;
}

function telegramWebApp(): TelegramWebApp | undefined {
	const webApp = (globalThis as { Telegram?: { WebApp?: TelegramWebApp } }).Telegram?.WebApp;
	return webApp?.initData ? webApp : undefined;
}

/** Opens an advert's link: inside Telegram through the Mini App API, elsewhere in a new tab */
export function openAdLink(url: string): void {
	const webApp = telegramWebApp();
	if (webApp && /^https:\/\/t\.me\//.test(url) && webApp.openTelegramLink) {
		webApp.openTelegramLink(url);
	} else if (webApp?.openLink) {
		webApp.openLink(url);
	} else {
		globalThis.open?.(url, '_blank', 'noopener');
	}
}

/**
 * A rewarded viewing: counts down `seconds`, then reports that the reward may be granted.
 * Rendering is up to the app; `cancel` ends the viewing without a reward.
 */
export function rewardedCountdown(
	seconds: number,
	handlers: { onTick?: (secondsLeft: number) => void; onDone: () => void }
): { cancel: () => void } {
	let left = Math.max(0, Math.ceil(seconds));
	handlers.onTick?.(left);
	if (left === 0) {
		handlers.onDone();
		return { cancel: () => {} };
	}
	const timer = setInterval(() => {
		left -= 1;
		handlers.onTick?.(left);
		if (left <= 0) {
			clearInterval(timer);
			handlers.onDone();
		}
	}, 1000);
	return { cancel: () => clearInterval(timer) };
}
