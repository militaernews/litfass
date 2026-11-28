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
/** Validates an ad; returns null for anything a renderer could trip over */
export declare function parseAd(value: unknown): Ad | null;
/** Reads a feed, dropping invalid adverts instead of failing as a whole */
export declare function parseFeed(value: unknown): Feed;
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
export declare function fitsCategories(ad: Ad, categories?: readonly string[]): boolean;
/** The adverts that may run in a placement right now */
export declare function activeAds(feed: Feed, placement: Placement, now?: Date): Ad[];
/** A weighted random advert; falls back to excluded ones rather than showing nothing */
export declare function pickAd(feed: Feed, options: PickOptions): Ad | null;
/** The advert's texts in a language, e.g. `de` or `pt-BR`, falling back to the base language and English */
export declare function localize(ad: Ad, lang: string): AdText;
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
export declare function frequencyCap(options: {
    key: string;
    max: number;
    windowMs: number;
    storage?: CapStorage | null;
}): FrequencyCap;
/** Opens an advert's link: inside Telegram through the Mini App API, elsewhere in a new tab */
export declare function openAdLink(url: string): void;
/**
 * A rewarded viewing: counts down `seconds`, then reports that the reward may be granted.
 * Rendering is up to the app; `cancel` ends the viewing without a reward.
 */
export declare function rewardedCountdown(seconds: number, handlers: {
    onTick?: (secondsLeft: number) => void;
    onDone: () => void;
}): {
    cancel: () => void;
};
/**
 * Loads a feed from a litfass server (or any URL serving the format). Falls back to `fallback`
 * (e.g. a bundled feed) when the request fails, so an outage never leaves the slot empty.
 */
export declare function fetchFeed(url: string, options?: {
    fallback?: unknown;
    timeoutMs?: number;
    fetch?: typeof fetch;
}): Promise<Feed>;
export type AdEvent = 'view' | 'click' | 'reward';
/** The event endpoint that belongs to a feed URL (`…/v1/feed/<key>` → `…/v1/event/<key>`) */
export declare function eventUrl(feedUrl: string): string;
/**
 * Reports views, clicks and completed rewarded viewings. The server keeps daily totals per advert
 * and placement only. Events are batched and sent with sendBeacon (text/plain, no preflight).
 */
export declare function createReporter(url: string, options?: {
    flushMs?: number;
}): {
    report(ad: Pick<Ad, "id">, event: AdEvent): void;
    flush: () => void;
};
/** Default look of `renderAd`; themable through the CSS variables or by overriding the classes */
export declare const AD_CSS = "\n.litfass-ad{--litfass-bg:#f4ecd8;--litfass-fg:#1d1d1b;--litfass-accent:#9c2f2f;position:relative;display:flex;gap:.75rem;align-items:center;box-sizing:border-box;padding:.9rem 1rem;border-radius:12px;background:var(--litfass-bg);color:var(--litfass-fg);font:inherit;line-height:1.3;text-align:start;overflow:hidden}\n.litfass-ad__label{position:absolute;top:.35rem;inset-inline-end:.5rem;font-size:.65rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;opacity:.75}\n.litfass-ad__media{flex:none;font-size:2rem;line-height:1}\n.litfass-ad__media img,.litfass-ad__media video{display:block;width:3.5rem;height:3.5rem;object-fit:cover;border-radius:8px}\n.litfass-ad__body{display:flex;flex-direction:column;gap:.15rem;min-width:0}\n.litfass-ad__title{font-weight:700;font-size:1.05rem}\n.litfass-ad__text{font-size:.9rem;opacity:.9}\n.litfass-ad__cta{align-self:flex-start;margin-top:.35rem;padding:.35rem .8rem;border:0;border-radius:999px;background:var(--litfass-accent);color:var(--litfass-bg);font:inherit;font-weight:700;font-size:.85rem;cursor:pointer}\n.litfass-ad--banner{padding:.5rem .8rem}.litfass-ad--banner .litfass-ad__text{display:none}.litfass-ad--banner .litfass-ad__cta{margin:0 0 0 auto;align-self:center}\n.litfass-ad--poster{flex-direction:column;text-align:center;padding:1.4rem 1rem}.litfass-ad--poster .litfass-ad__media{font-size:3rem}.litfass-ad--poster .litfass-ad__media img,.litfass-ad--poster .litfass-ad__media video{width:100%;height:auto;max-height:12rem;object-fit:contain}.litfass-ad--poster .litfass-ad__body{align-items:center}.litfass-ad--poster .litfass-ad__title{font-size:1.35rem}.litfass-ad--poster .litfass-ad__cta{align-self:center}\n.litfass-interstitial{position:fixed;inset:0;z-index:2147483647;display:grid;place-items:center;padding:16px;background:#000b;color:#fff;font:inherit}\n.litfass-interstitial--fullscreen{padding:0}\n.litfass-interstitial__card{position:relative;width:min(100%,26rem);overflow:hidden;border-radius:20px;background:var(--litfass-bg,#0c2547);color:var(--litfass-fg,#e6f6ff);box-shadow:0 24px 80px #0008;text-align:center}\n.litfass-interstitial--fullscreen .litfass-interstitial__card{width:100%;height:100%;border-radius:0;display:flex;flex-direction:column;justify-content:space-between}\n.litfass-interstitial__label{position:absolute;top:10px;left:12px;z-index:1;border-radius:999px;padding:.15rem .55rem;background:#0008;color:#fff;font-size:.7rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}\n.litfass-interstitial__close{position:absolute;top:8px;right:8px;z-index:1;width:36px;height:36px;border:0;border-radius:50%;background:#0009;color:#fff;font-size:1.3rem;line-height:1;cursor:pointer}\n.litfass-interstitial__media{width:100%;background:#000;display:grid;place-items:center}\n.litfass-interstitial__media img,.litfass-interstitial__media video{display:block;width:100%;max-height:60vh;object-fit:contain}\n.litfass-interstitial--fullscreen .litfass-interstitial__media img,.litfass-interstitial--fullscreen .litfass-interstitial__media video{max-height:74vh}\n.litfass-interstitial__body{padding:18px}\n.litfass-interstitial__title{display:block;font-size:1.15rem;font-weight:800}\n.litfass-interstitial__text{display:block;margin-top:4px;opacity:.85;font-size:.9rem}\n.litfass-interstitial__cta{margin-top:14px;padding:.7rem 1.2rem;border:0;border-radius:999px;background:var(--litfass-accent,#2ec5ff);color:#06142a;font:inherit;font-weight:800;cursor:pointer}\n";
/** Adds AD_CSS to the document once */
export declare function injectAdStyles(doc?: Document): void;
/** The CSS variables for an advert's own colours, for renderers that build their own markup */
export declare function adStyleVars(style?: AdStyle): Record<string, string>;
/**
 * Builds the advert as a DOM element with the label German law asks for (default „Anzeige“).
 * Call injectAdStyles() once, or style the `litfass-ad*` classes yourself.
 */
export declare function renderAd(ad: Ad, options?: {
    lang?: string;
    label?: string;
    variant?: AdStyle['variant'];
    onClick?: (ad: Ad) => void;
    doc?: Document;
}): HTMLElement;
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
export declare function showInterstitial(ad: Ad, options?: InterstitialOptions): HTMLElement;
