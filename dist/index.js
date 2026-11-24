/**
 * litfass: house adverts for web games and Telegram Mini Apps.
 *
 * A feed is a small JSON document listing your own adverts (channels, other projects, partners).
 * Nothing here talks to an ad network or tracks anyone: the feed is bundled or fetched by the app,
 * a frequency cap lives in the viewer's storage, and the reward is granted by the app itself.
 */
const PLACEMENTS = ['rewarded', 'banner', 'chat'];
function isText(value) {
    if (!value || typeof value !== 'object')
        return false;
    const text = value;
    return ['title', 'body', 'cta'].every((key) => typeof text[key] === 'string' && text[key] !== '');
}
function isDate(value) {
    return value === undefined || (typeof value === 'string' && !Number.isNaN(Date.parse(value)));
}
const COLOR = /^#[0-9a-fA-F]{3,8}$/;
const VARIANTS = ['card', 'banner', 'poster'];
/** Keeps only the style fields that are safe to put into CSS */
function parseStyle(value) {
    if (!value || typeof value !== 'object')
        return null;
    const raw = value;
    const style = {};
    if (VARIANTS.includes(raw.variant))
        style.variant = raw.variant;
    for (const key of ['background', 'color', 'accent']) {
        if (typeof raw[key] === 'string' && COLOR.test(raw[key]))
            style[key] = raw[key];
    }
    return Object.keys(style).length ? style : null;
}
/** Validates an ad; returns null for anything a renderer could trip over */
export function parseAd(value) {
    if (!value || typeof value !== 'object')
        return null;
    const ad = value;
    if (typeof ad.id !== 'string' || !ad.id)
        return null;
    if (typeof ad.url !== 'string' || !/^https:\/\//.test(ad.url))
        return null;
    if (!ad.text || typeof ad.text !== 'object')
        return null;
    const text = Object.fromEntries(Object.entries(ad.text).filter(([, entry]) => isText(entry)));
    if (!text.en)
        return null;
    if (ad.weight !== undefined && (typeof ad.weight !== 'number' || ad.weight < 0))
        return null;
    if (!isDate(ad.start) || !isDate(ad.end))
        return null;
    if (ad.placements !== undefined &&
        (!Array.isArray(ad.placements) || !ad.placements.every((p) => PLACEMENTS.includes(p)))) {
        return null;
    }
    if (ad.image !== undefined && typeof ad.image !== 'string')
        return null;
    if (ad.emoji !== undefined && typeof ad.emoji !== 'string')
        return null;
    if (ad.categories !== undefined && (!Array.isArray(ad.categories) || !ad.categories.every((c) => typeof c === 'string'))) {
        return null;
    }
    const style = parseStyle(ad.style);
    const parsed = { ...ad, text: text };
    if (style)
        parsed.style = style;
    else
        delete parsed.style;
    return parsed;
}
/** Reads a feed, dropping invalid adverts instead of failing as a whole */
export function parseFeed(value) {
    const feed = value && typeof value === 'object' ? value : {};
    const ads = Array.isArray(feed.ads) ? feed.ads.map(parseAd).filter((ad) => !!ad) : [];
    return { version: 1, ads };
}
/** An advert without categories fits everywhere, as does a placement without categories */
export function fitsCategories(ad, categories) {
    return !ad.categories?.length || !categories?.length || ad.categories.some((c) => categories.includes(c));
}
/** The adverts that may run in a placement right now */
export function activeAds(feed, placement, now = new Date()) {
    const time = now.getTime();
    return feed.ads.filter((ad) => (ad.weight ?? 1) > 0 &&
        (!ad.placements || ad.placements.includes(placement)) &&
        (!ad.start || Date.parse(ad.start) <= time) &&
        (!ad.end || time < Date.parse(ad.end)));
}
/** A weighted random advert; falls back to excluded ones rather than showing nothing */
export function pickAd(feed, options) {
    const active = activeAds(feed, options.placement, options.now).filter((ad) => fitsCategories(ad, options.categories));
    const fresh = active.filter((ad) => !options.exclude?.includes(ad.id));
    const pool = fresh.length ? fresh : active;
    const total = pool.reduce((sum, ad) => sum + (ad.weight ?? 1), 0);
    if (!total)
        return null;
    let roll = (options.random ?? Math.random)() * total;
    for (const ad of pool) {
        roll -= ad.weight ?? 1;
        if (roll < 0)
            return ad;
    }
    return pool[pool.length - 1];
}
/** The advert's texts in a language, e.g. `de` or `pt-BR`, falling back to the base language and English */
export function localize(ad, lang) {
    const base = lang.toLowerCase().split(/[-_]/)[0];
    return ad.text[lang] ?? ad.text[base] ?? ad.text.en;
}
/**
 * At most `max` views per `windowMs`, kept in the viewer's own storage. Storage that throws
 * (private mode, blocked site data) degrades to an in-memory cap for the page's lifetime.
 */
export function frequencyCap(options) {
    let memory = [];
    const read = (now) => {
        let views = memory;
        try {
            const raw = options.storage?.getItem(options.key);
            if (raw)
                views = JSON.parse(raw).filter((v) => typeof v === 'number');
        }
        catch {
            // fall back to memory
        }
        return views.filter((time) => now - time < options.windowMs);
    };
    const write = (views) => {
        memory = views;
        try {
            options.storage?.setItem(options.key, JSON.stringify(views));
        }
        catch {
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
            if (views.length >= options.max)
                return false;
            write([...views, time]);
            return true;
        }
    };
}
function telegramWebApp() {
    const webApp = globalThis.Telegram?.WebApp;
    return webApp?.initData ? webApp : undefined;
}
/** Opens an advert's link: inside Telegram through the Mini App API, elsewhere in a new tab */
export function openAdLink(url) {
    const webApp = telegramWebApp();
    if (webApp && /^https:\/\/t\.me\//.test(url) && webApp.openTelegramLink) {
        webApp.openTelegramLink(url);
    }
    else if (webApp?.openLink) {
        webApp.openLink(url);
    }
    else {
        globalThis.open?.(url, '_blank', 'noopener');
    }
}
/**
 * A rewarded viewing: counts down `seconds`, then reports that the reward may be granted.
 * Rendering is up to the app; `cancel` ends the viewing without a reward.
 */
export function rewardedCountdown(seconds, handlers) {
    let left = Math.max(0, Math.ceil(seconds));
    handlers.onTick?.(left);
    if (left === 0) {
        handlers.onDone();
        return { cancel: () => { } };
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
export async function fetchFeed(url, options = {}) {
    const doFetch = options.fetch ?? fetch;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeoutMs ?? 5000);
    try {
        const response = await doFetch(url, { signal: controller.signal, credentials: 'omit' });
        if (!response.ok)
            throw new Error(`feed ${response.status}`);
        const feed = parseFeed(await response.json());
        if (!feed.ads.length && options.fallback)
            return parseFeed(options.fallback);
        return feed;
    }
    catch {
        return parseFeed(options.fallback ?? null);
    }
    finally {
        clearTimeout(timer);
    }
}
/** The event endpoint that belongs to a feed URL (`…/v1/feed/<key>` → `…/v1/event/<key>`) */
export function eventUrl(feedUrl) {
    return feedUrl.replace(/\/v1\/feed\/([^/?#]+).*$/, '/v1/event/$1');
}
/**
 * Reports views, clicks and completed rewarded viewings. The server keeps daily totals per advert
 * and placement only. Events are batched and sent with sendBeacon (text/plain, no preflight).
 */
export function createReporter(url, options = {}) {
    let queue = [];
    let timer;
    const flush = () => {
        timer = undefined;
        if (!queue.length)
            return;
        const body = JSON.stringify({ events: queue.splice(0, 50) });
        const beacon = globalThis.navigator?.sendBeacon?.bind(globalThis.navigator);
        if (!beacon?.(url, new Blob([body], { type: 'text/plain' }))) {
            void fetch(url, { method: 'POST', body, keepalive: true, headers: { 'Content-Type': 'text/plain' } }).catch(() => { });
        }
        if (queue.length)
            timer = setTimeout(flush, 0);
    };
    return {
        report(ad, event) {
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
.litfass-ad__media img{display:block;width:3.5rem;height:3.5rem;object-fit:cover;border-radius:8px}
.litfass-ad__body{display:flex;flex-direction:column;gap:.15rem;min-width:0}
.litfass-ad__title{font-weight:700;font-size:1.05rem}
.litfass-ad__text{font-size:.9rem;opacity:.9}
.litfass-ad__cta{align-self:flex-start;margin-top:.35rem;padding:.35rem .8rem;border:0;border-radius:999px;background:var(--litfass-accent);color:var(--litfass-bg);font:inherit;font-weight:700;font-size:.85rem;cursor:pointer}
.litfass-ad--banner{padding:.5rem .8rem}.litfass-ad--banner .litfass-ad__text{display:none}.litfass-ad--banner .litfass-ad__cta{margin:0 0 0 auto;align-self:center}
.litfass-ad--poster{flex-direction:column;text-align:center;padding:1.4rem 1rem}.litfass-ad--poster .litfass-ad__media{font-size:3rem}.litfass-ad--poster .litfass-ad__media img{width:100%;height:auto;max-height:12rem}.litfass-ad--poster .litfass-ad__body{align-items:center}.litfass-ad--poster .litfass-ad__title{font-size:1.35rem}.litfass-ad--poster .litfass-ad__cta{align-self:center}
`;
/** Adds AD_CSS to the document once */
export function injectAdStyles(doc = document) {
    if (doc.getElementById('litfass-styles'))
        return;
    const style = doc.createElement('style');
    style.id = 'litfass-styles';
    style.textContent = AD_CSS;
    doc.head.append(style);
}
/** The CSS variables for an advert's own colours, for renderers that build their own markup */
export function adStyleVars(style) {
    const vars = {};
    if (style?.background)
        vars['--litfass-bg'] = style.background;
    if (style?.color)
        vars['--litfass-fg'] = style.color;
    if (style?.accent)
        vars['--litfass-accent'] = style.accent;
    return vars;
}
/**
 * Builds the advert as a DOM element with the label German law asks for (default „Anzeige“).
 * Call injectAdStyles() once, or style the `litfass-ad*` classes yourself.
 */
export function renderAd(ad, options = {}) {
    const doc = options.doc ?? document;
    const text = localize(ad, options.lang ?? doc.documentElement.lang ?? 'en');
    const variant = options.variant ?? ad.style?.variant ?? 'card';
    const root = doc.createElement('aside');
    root.className = `litfass-ad litfass-ad--${variant}`;
    root.dataset.adId = ad.id;
    for (const [name, value] of Object.entries(adStyleVars(ad.style)))
        root.style.setProperty(name, value);
    const el = (tag, cls, content) => {
        const node = doc.createElement(tag);
        node.className = cls;
        if (content !== undefined)
            node.textContent = content;
        return node;
    };
    root.append(el('span', 'litfass-ad__label', options.label ?? 'Anzeige'));
    if (ad.image || ad.emoji) {
        const media = el('div', 'litfass-ad__media');
        if (ad.image) {
            const img = doc.createElement('img');
            img.src = ad.image;
            img.alt = '';
            img.loading = 'lazy';
            media.append(img);
        }
        else {
            media.textContent = ad.emoji ?? '';
            media.setAttribute('aria-hidden', 'true');
        }
        root.append(media);
    }
    const body = el('div', 'litfass-ad__body');
    body.append(el('strong', 'litfass-ad__title', text.title), el('span', 'litfass-ad__text', text.body));
    const cta = el('button', 'litfass-ad__cta', text.cta);
    cta.type = 'button';
    cta.addEventListener('click', () => {
        options.onClick?.(ad);
        openAdLink(ad.url);
    });
    body.append(cta);
    root.append(body);
    return root;
}
