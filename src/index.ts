/**
 * litfass: house adverts for web games and Telegram Mini Apps.
 *
 * A feed is a small JSON document listing your own adverts (channels, other projects, partners).
 * Nothing here talks to an ad network or tracks anyone: the feed is bundled or fetched by the app,
 * a frequency cap lives in the viewer's storage, and the reward is granted by the app itself.
 */

export type Placement = 'rewarded' | 'banner' | 'chat';

/** How an advert looks on the web; every field is optional and falls back to the renderer's theme */
export interface AdStyle {
	variant?: 'card' | 'banner' | 'poster';
	/** CSS colours, e.g. `#14161a` */
	background?: string;
	color?: string;
	accent?: string;
}

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
	/** A playable video or animated GIF URL, resolved from a Telegram channel post */
	video?: string;
	/** How to play `video`: a real video element or an animated image */
	videoKind?: 'video' | 'gif';
	/** A required action before the reward is granted, e.g. joining a channel */
	task?: { type: 'join'; chat: string };
	/** Where the button leads; t.me links open inside Telegram */
	url: string;
	/** Texts per language code; `en` is the fallback */
	text: Record<string, AdText>;
	/** Content the advert fits, e.g. `news` or `gaming`; empty or omitted fits every placement */
	categories?: string[];
	style?: AdStyle;
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

const COLOR = /^#[0-9a-fA-F]{3,8}$/;
const VARIANTS = ['card', 'banner', 'poster'] as const;

/** Keeps only the style fields that are safe to put into CSS */
function parseStyle(value: unknown): AdStyle | null {
	if (!value || typeof value !== 'object') return null;
	const raw = value as Record<string, unknown>;
	const style: AdStyle = {};
	if (VARIANTS.includes(raw.variant as AdStyle['variant'] & string)) style.variant = raw.variant as AdStyle['variant'];
	for (const key of ['background', 'color', 'accent'] as const) {
		if (typeof raw[key] === 'string' && COLOR.test(raw[key] as string)) style[key] = raw[key] as string;
	}
	return Object.keys(style).length ? style : null;
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
	if (ad.video !== undefined && (typeof ad.video !== 'string' || !/^https:\/\//.test(ad.video))) return null;
	if (ad.videoKind !== undefined && ad.videoKind !== 'video' && ad.videoKind !== 'gif') return null;
	if (
		ad.task !== undefined &&
		(typeof ad.task !== 'object' ||
			(ad.task as Record<string, unknown>).type !== 'join' ||
			typeof (ad.task as Record<string, unknown>).chat !== 'string')
	)
		return null;
	if (ad.emoji !== undefined && typeof ad.emoji !== 'string') return null;
	if (ad.categories !== undefined && (!Array.isArray(ad.categories) || !ad.categories.every((c) => typeof c === 'string'))) {
		return null;
	}
	const style = parseStyle(ad.style);
	const parsed = { ...(ad as unknown as Ad), text: text as Record<string, AdText> };
	if (style) parsed.style = style;
	else delete parsed.style;
	return parsed;
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
	/** The content of the placement; adverts with categories must share one. Feeds from a litfass
	 * server are already matched to the publisher, so this is for bundled feeds. */
	categories?: readonly string[];
	/** Injectable for tests; returns [0, 1) */
	random?: () => number;
}

/** An advert without categories fits everywhere, as does a placement without categories */
export function fitsCategories(ad: Ad, categories?: readonly string[]): boolean {
	return !ad.categories?.length || !categories?.length || ad.categories.some((c) => categories.includes(c));
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
	const active = activeAds(feed, options.placement, options.now).filter((ad) => fitsCategories(ad, options.categories));
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

/**
 * Loads a feed from a litfass server (or any URL serving the format). Falls back to `fallback`
 * (e.g. a bundled feed) when the request fails, so an outage never leaves the slot empty.
 */
export async function fetchFeed(
	url: string,
	options: { fallback?: unknown; timeoutMs?: number; fetch?: typeof fetch } = {}
): Promise<Feed> {
	const doFetch = options.fetch ?? fetch;
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), options.timeoutMs ?? 5000);
	try {
		const response = await doFetch(url, { signal: controller.signal, credentials: 'omit' });
		if (!response.ok) throw new Error(`feed ${response.status}`);
		const feed = parseFeed(await response.json());
		if (!feed.ads.length && options.fallback) return parseFeed(options.fallback);
		return feed;
	} catch {
		return parseFeed(options.fallback ?? null);
	} finally {
		clearTimeout(timer);
	}
}

export type AdEvent = 'view' | 'click' | 'reward';

/** The event endpoint that belongs to a feed URL (`…/v1/feed/<key>` → `…/v1/event/<key>`) */
export function eventUrl(feedUrl: string): string {
	return feedUrl.replace(/\/v1\/feed\/([^/?#]+).*$/, '/v1/event/$1');
}

/**
 * Reports views, clicks and completed rewarded viewings. The server keeps daily totals per advert
 * and placement only. Events are batched and sent with sendBeacon (text/plain, no preflight).
 */
export function createReporter(url: string, options: { flushMs?: number } = {}) {
	let queue: { ad: string; event: AdEvent }[] = [];
	let timer: ReturnType<typeof setTimeout> | undefined;
	const flush = () => {
		timer = undefined;
		if (!queue.length) return;
		const body = JSON.stringify({ events: queue.splice(0, 50) });
		const beacon = (globalThis.navigator as Navigator | undefined)?.sendBeacon?.bind(globalThis.navigator);
		if (!beacon?.(url, new Blob([body], { type: 'text/plain' }))) {
			void fetch(url, { method: 'POST', body, keepalive: true, headers: { 'Content-Type': 'text/plain' } }).catch(() => {});
		}
		if (queue.length) timer = setTimeout(flush, 0);
	};
	return {
		report(ad: Pick<Ad, 'id'>, event: AdEvent) {
			queue.push({ ad: ad.id, event });
			timer ??= setTimeout(flush, options.flushMs ?? 1000);
		},
		flush
	};
}

/** Default look of `renderAd`; themable through the CSS variables or by overriding the classes */
export const AD_CSS = `
.litfass-ad{--litfass-bg:#f4ecd8;--litfass-fg:#1d1d1b;--litfass-accent:#9c2f2f;position:relative;display:flex;gap:.75rem;align-items:center;box-sizing:border-box;padding:.9rem 1rem;border-radius:12px;background:var(--litfass-bg);color:var(--litfass-fg);font:inherit;line-height:1.3;text-align:start;overflow:hidden}
.litfass-ad__label{position:absolute;top:.35rem;inset-inline-end:.5rem;font-size:.65rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;opacity:.75}
.litfass-ad__media{flex:none;font-size:2rem;line-height:1}
.litfass-ad__media img,.litfass-ad__media video{display:block;width:3.5rem;height:3.5rem;object-fit:cover;border-radius:8px}
.litfass-ad__body{display:flex;flex-direction:column;gap:.15rem;min-width:0}
.litfass-ad__title{font-weight:700;font-size:1.05rem}
.litfass-ad__text{font-size:.9rem;opacity:.9}
.litfass-ad__cta{align-self:flex-start;margin-top:.35rem;padding:.35rem .8rem;border:0;border-radius:999px;background:var(--litfass-accent);color:var(--litfass-bg);font:inherit;font-weight:700;font-size:.85rem;cursor:pointer}
.litfass-ad--banner{padding:.5rem .8rem}.litfass-ad--banner .litfass-ad__text{display:none}.litfass-ad--banner .litfass-ad__cta{margin:0 0 0 auto;align-self:center}
.litfass-ad--poster{flex-direction:column;text-align:center;padding:1.4rem 1rem}.litfass-ad--poster .litfass-ad__media{font-size:3rem}.litfass-ad--poster .litfass-ad__media img,.litfass-ad--poster .litfass-ad__media video{width:100%;height:auto;max-height:12rem;object-fit:contain}.litfass-ad--poster .litfass-ad__body{align-items:center}.litfass-ad--poster .litfass-ad__title{font-size:1.35rem}.litfass-ad--poster .litfass-ad__cta{align-self:center}
.litfass-interstitial{position:fixed;inset:0;z-index:2147483647;display:grid;place-items:center;padding:16px;background:#000b;color:#fff;font:inherit}
.litfass-interstitial--fullscreen{padding:0}
.litfass-interstitial__card{position:relative;width:min(100%,26rem);overflow:hidden;border-radius:20px;background:var(--litfass-bg,#0c2547);color:var(--litfass-fg,#e6f6ff);box-shadow:0 24px 80px #0008;text-align:center}
.litfass-interstitial--fullscreen .litfass-interstitial__card{width:100%;height:100%;border-radius:0;display:flex;flex-direction:column;justify-content:space-between}
.litfass-interstitial__label{position:absolute;top:10px;left:12px;z-index:1;border-radius:999px;padding:.15rem .55rem;background:#0008;color:#fff;font-size:.7rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}
.litfass-interstitial__close{position:absolute;top:8px;right:8px;z-index:1;width:36px;height:36px;border:0;border-radius:50%;background:#0009;color:#fff;font-size:1.3rem;line-height:1;cursor:pointer}
.litfass-interstitial__media{width:100%;background:#000;display:grid;place-items:center}
.litfass-interstitial__media img,.litfass-interstitial__media video{display:block;width:100%;max-height:60vh;object-fit:contain}
.litfass-interstitial--fullscreen .litfass-interstitial__media img,.litfass-interstitial--fullscreen .litfass-interstitial__media video{max-height:74vh}
.litfass-interstitial__body{padding:18px}
.litfass-interstitial__title{display:block;font-size:1.15rem;font-weight:800}
.litfass-interstitial__text{display:block;margin-top:4px;opacity:.85;font-size:.9rem}
.litfass-interstitial__cta{margin-top:14px;padding:.7rem 1.2rem;border:0;border-radius:999px;background:var(--litfass-accent,#2ec5ff);color:#06142a;font:inherit;font-weight:800;cursor:pointer}
.litfass-interstitial__actions{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-top:14px}
.litfass-interstitial__join,.litfass-interstitial__verify{padding:.7rem 1.2rem;border:0;border-radius:999px;font:inherit;font-weight:800;text-decoration:none;cursor:pointer}
.litfass-interstitial__join{background:#229ed9;color:#fff}
.litfass-interstitial__verify{background:var(--litfass-accent,#2ec5ff);color:#06142a}
.litfass-interstitial__verify:disabled{opacity:.6;cursor:wait}
.litfass-interstitial__error{display:block;margin-top:10px;color:#ffb4a8;font-size:.8rem}
`;

/** Adds AD_CSS to the document once */
export function injectAdStyles(doc: Document = document): void {
	if (doc.getElementById('litfass-styles')) return;
	const style = doc.createElement('style');
	style.id = 'litfass-styles';
	style.textContent = AD_CSS;
	doc.head.append(style);
}

/** The CSS variables for an advert's own colours, for renderers that build their own markup */
export function adStyleVars(style?: AdStyle): Record<string, string> {
	const vars: Record<string, string> = {};
	if (style?.background) vars['--litfass-bg'] = style.background;
	if (style?.color) vars['--litfass-fg'] = style.color;
	if (style?.accent) vars['--litfass-accent'] = style.accent;
	return vars;
}

/**
 * Builds the advert as a DOM element with the label German law asks for (default „Anzeige“).
 * Call injectAdStyles() once, or style the `litfass-ad*` classes yourself.
 */
export function renderAd(
	ad: Ad,
	options: { lang?: string; label?: string; variant?: AdStyle['variant']; onClick?: (ad: Ad) => void; doc?: Document } = {}
): HTMLElement {
	const doc = options.doc ?? document;
	const text = localize(ad, options.lang ?? doc.documentElement.lang ?? 'en');
	const variant = options.variant ?? ad.style?.variant ?? 'card';
	const root = doc.createElement('aside');
	root.className = `litfass-ad litfass-ad--${variant}`;
	root.dataset.adId = ad.id;
	for (const [name, value] of Object.entries(adStyleVars(ad.style))) root.style.setProperty(name, value);
	const el = (tag: string, cls: string, content?: string) => {
		const node = doc.createElement(tag);
		node.className = cls;
		if (content !== undefined) node.textContent = content;
		return node;
	};
	root.append(el('span', 'litfass-ad__label', options.label ?? 'Anzeige'));
	if (ad.video) {
		const media = el('div', 'litfass-ad__media');
		if (ad.videoKind === 'video') {
			const video = doc.createElement('video');
			video.src = ad.video;
			video.autoplay = true;
			video.muted = true;
			video.loop = true;
			video.playsInline = true;
			media.append(video);
		} else {
			const img = doc.createElement('img');
			img.src = ad.video;
			img.alt = '';
			img.loading = 'lazy';
			media.append(img);
		}
		root.append(media);
	} else if (ad.image || ad.emoji) {
		const media = el('div', 'litfass-ad__media');
		if (ad.image) {
			const img = doc.createElement('img');
			img.src = ad.image;
			img.alt = '';
			img.loading = 'lazy';
			media.append(img);
		} else {
			media.textContent = ad.emoji ?? '';
			media.setAttribute('aria-hidden', 'true');
		}
		root.append(media);
	}
	const body = el('div', 'litfass-ad__body');
	body.append(el('strong', 'litfass-ad__title', text.title), el('span', 'litfass-ad__text', text.body));
	const cta = el('button', 'litfass-ad__cta', text.cta) as HTMLButtonElement;
	cta.type = 'button';
	cta.addEventListener('click', () => {
		options.onClick?.(ad);
		openAdLink(ad.url);
	});
	body.append(cta);
	root.append(body);
	return root;
}

/** Options for a video interstitial */
export interface InterstitialOptions {
	/** A centered modal (default) or an edge-to-edge fullscreen overlay */
	mode?: 'modal' | 'fullscreen';
	/** Override the "Anzeige" label */
	label?: string;
	lang?: string;
	onClick?: (ad: Ad) => void;
	onClose?: () => void;
	/** Automatically close after this many milliseconds */
	autoCloseMs?: number;
	doc?: Document;
}

/** Shows an ad as a modal or fullscreen interstitial, with a close button and CTA. */
export function showInterstitial(ad: Ad, options: InterstitialOptions = {}): HTMLElement {
	const doc = options.doc ?? document;
	const text = localize(ad, options.lang ?? doc.documentElement.lang ?? 'en');
	const mode = options.mode ?? 'modal';
	const overlay = doc.createElement('div');
	overlay.className = `litfass-interstitial litfass-interstitial--${mode}`;
	overlay.setAttribute('role', 'dialog');
	overlay.setAttribute('aria-modal', 'true');

	const card = doc.createElement('div');
	card.className = 'litfass-interstitial__card';
	for (const [name, value] of Object.entries(adStyleVars(ad.style))) card.style.setProperty(name, value);

	const label = doc.createElement('span');
	label.className = 'litfass-interstitial__label';
	label.textContent = options.label ?? 'Anzeige';
	card.append(label);

	const closeButton = doc.createElement('button');
	closeButton.className = 'litfass-interstitial__close';
	closeButton.type = 'button';
	closeButton.textContent = '×';
	closeButton.setAttribute('aria-label', 'Close');
	card.append(closeButton);

	if (ad.video) {
		const media = doc.createElement('div');
		media.className = 'litfass-interstitial__media';
		if (ad.videoKind === 'video') {
			const video = doc.createElement('video');
			video.src = ad.video;
			video.autoplay = true;
			video.muted = true;
			video.loop = true;
			video.playsInline = true;
			video.setAttribute('playsinline', '');
			media.append(video);
		} else {
			const img = doc.createElement('img');
			img.src = ad.video;
			img.alt = '';
			media.append(img);
		}
		card.append(media);
	} else if (ad.image || ad.emoji) {
		const media = doc.createElement('div');
		media.className = 'litfass-interstitial__media';
		if (ad.image) {
			const img = doc.createElement('img');
			img.src = ad.image;
			img.alt = '';
			media.append(img);
		} else {
			media.textContent = ad.emoji ?? '';
			media.style.fontSize = '4rem';
		}
		card.append(media);
	}

	const body = doc.createElement('div');
	body.className = 'litfass-interstitial__body';
	const title = doc.createElement('strong');
	title.className = 'litfass-interstitial__title';
	title.textContent = text.title;
	const description = doc.createElement('span');
	description.className = 'litfass-interstitial__text';
	description.textContent = text.body;
	const cta = doc.createElement('button');
	cta.className = 'litfass-interstitial__cta';
	cta.type = 'button';
	cta.textContent = text.cta;
	body.append(title, description, cta);
	card.append(body);
	overlay.append(card);

	let timer: ReturnType<typeof setTimeout> | undefined;
	const close = () => {
		if (timer) clearTimeout(timer);
		overlay.remove();
		options.onClose?.();
	};
	closeButton.addEventListener('click', close);
	overlay.addEventListener('click', (event) => {
		if (event.target === overlay) close();
	});
	cta.addEventListener('click', () => {
		options.onClick?.(ad);
		openAdLink(ad.url);
		close();
	});
	doc.addEventListener(
		'keydown',
		(event) => {
			if (event.key === 'Escape') close();
		},
		{ once: true }
	);
	if (options.autoCloseMs) timer = setTimeout(close, options.autoCloseMs);
	doc.body.append(overlay);
	return overlay;
}

/** Options for a required join task */
export interface TaskInterstitialOptions {
	mode?: 'modal' | 'fullscreen';
	label?: string;
	lang?: string;
	/** Called when the user asks to verify; resolve true only after the server confirmed the join */
	onVerify: () => Promise<boolean>;
	onDone?: () => void;
	labels?: { join?: string; verify?: string; notJoined?: string; botMissing?: string };
	doc?: Document;
}

/**
 * Shows a join-task ad with no timer, countdown, skip or close button. The only way out is
 * joining the channel and a successful verification through `onVerify`.
 */
export function showTaskInterstitial(ad: Ad, options: TaskInterstitialOptions): HTMLElement {
	const doc = options.doc ?? document;
	const text = localize(ad, options.lang ?? doc.documentElement.lang ?? 'en');
	const chat = ad.task?.chat.replace(/^@/, '') ?? '';
	const overlay = doc.createElement('div');
	overlay.className = `litfass-interstitial litfass-interstitial--${options.mode ?? 'fullscreen'}`;
	overlay.setAttribute('role', 'dialog');
	overlay.setAttribute('aria-modal', 'true');

	const card = doc.createElement('div');
	card.className = 'litfass-interstitial__card';
	for (const [name, value] of Object.entries(adStyleVars(ad.style))) card.style.setProperty(name, value);

	const label = doc.createElement('span');
	label.className = 'litfass-interstitial__label';
	label.textContent = options.label ?? 'Anzeige';
	card.append(label);

	if (ad.video) {
		const media = doc.createElement('div');
		media.className = 'litfass-interstitial__media';
		if (ad.videoKind === 'video') {
			const video = doc.createElement('video');
			video.src = ad.video;
			video.autoplay = true;
			video.muted = true;
			video.loop = true;
			video.playsInline = true;
			media.append(video);
		} else {
			const img = doc.createElement('img');
			img.src = ad.video;
			img.alt = '';
			media.append(img);
		}
		card.append(media);
	}

	const body = doc.createElement('div');
	body.className = 'litfass-interstitial__body';
	const title = doc.createElement('strong');
	title.className = 'litfass-interstitial__title';
	title.textContent = text.title;
	const description = doc.createElement('span');
	description.className = 'litfass-interstitial__text';
	description.textContent = text.body;
	body.append(title, description);

	const actions = doc.createElement('div');
	actions.className = 'litfass-interstitial__actions';
	const join = doc.createElement('a') as HTMLAnchorElement;
	join.className = 'litfass-interstitial__join';
	join.href = `https://t.me/${chat}`;
	join.target = '_blank';
	join.rel = 'noreferrer';
	join.textContent = `${options.labels?.join ?? 'Join'} @${chat}`;
	const verify = doc.createElement('button');
	verify.className = 'litfass-interstitial__verify';
	verify.type = 'button';
	verify.textContent = options.labels?.verify ?? 'I joined — verify';
	const error = doc.createElement('span');
	error.className = 'litfass-interstitial__error';
	actions.append(join, verify);
	body.append(actions, error);
	card.append(body);
	overlay.append(card);

	verify.addEventListener('click', async () => {
		verify.disabled = true;
		error.textContent = '';
		try {
			const ok = await options.onVerify();
			if (ok) {
				overlay.remove();
				options.onDone?.();
			} else {
				error.textContent = options.labels?.notJoined ?? 'Not a member yet — join the channel and try again.';
				verify.disabled = false;
			}
		} catch {
			error.textContent = options.labels?.botMissing ?? 'The bot must be a member of that chat to verify.';
			verify.disabled = false;
		}
	});

	doc.body.append(overlay);
	return overlay;
}
