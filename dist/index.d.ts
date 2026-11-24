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
/** Validates an ad; returns null for anything a renderer could trip over */
export declare function parseAd(value: unknown): Ad | null;
/** Reads a feed, dropping invalid adverts instead of failing as a whole */
export declare function parseFeed(value: unknown): Feed;
export interface PickOptions {
    placement: Placement;
    now?: Date;
    /** Ids to skip, e.g. the advert shown last */
    exclude?: readonly string[];
    /** Injectable for tests; returns [0, 1) */
    random?: () => number;
}
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
