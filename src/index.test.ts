import { describe, expect, test } from 'bun:test';
import { activeAds, frequencyCap, localize, parseAd, parseFeed, pickAd, type CapStorage } from './index';

test('video ads keep their playable media', () => {
	const ad = parseAd({ id: 'v', url: 'https://x.example', video: 'https://t.me/channel/1', videoKind: 'gif', text: { en: text } });
	expect(ad?.video).toBe('https://t.me/channel/1');
	expect(ad?.videoKind).toBe('gif');
	expect(parseAd({ id: 'v', url: 'https://x.example', video: 'http://x', text: { en: text } })).toBeNull();
	expect(parseAd({ id: 'v', url: 'https://x.example', videoKind: 'bad', text: { en: text } })).toBeNull();
	const task = parseAd({
		id: 't',
		url: 'https://x.example',
		task: { type: 'join', chat: '@channel' },
		text: { en: text }
	});
	expect(task?.task?.chat).toBe('@channel');
	expect(parseAd({ id: 't', url: 'https://x.example', task: { type: 'skip', chat: '@x' }, text: { en: text } })).toBeNull();
});

const text = { title: 'T', body: 'B', cta: 'Go' };
const feed = parseFeed({
	version: 1,
	ads: [
		{ id: 'a', url: 'https://t.me/a', text: { en: text, de: { title: 'D', body: 'B', cta: 'Los' } } },
		{ id: 'b', url: 'https://t.me/b', text: { en: text }, placements: ['chat'] },
		{ id: 'c', url: 'https://t.me/c', text: { en: text }, end: '2026-01-01' },
		{ id: 'off', url: 'https://t.me/x', text: { en: text }, weight: 0 },
		{ id: 'bad-url', url: 'http://x', text: { en: text } },
		{ id: 'no-en', url: 'https://t.me/y', text: { de: text } },
		'junk'
	]
});

describe('parseFeed', () => {
	test('drops invalid adverts', () => {
		expect(feed.ads.map((ad) => ad.id)).toEqual(['a', 'b', 'c', 'off']);
	});
	test('tolerates garbage', () => {
		expect(parseFeed(null).ads).toEqual([]);
	});
});

describe('activeAds and pickAd', () => {
	const now = new Date('2026-06-01');
	test('filters by placement, schedule and weight', () => {
		expect(activeAds(feed, 'rewarded', now).map((ad) => ad.id)).toEqual(['a']);
		expect(activeAds(feed, 'chat', now).map((ad) => ad.id)).toEqual(['a', 'b']);
	});
	test('skips excluded adverts unless nothing else is left', () => {
		expect(pickAd(feed, { placement: 'chat', now, exclude: ['a'], random: () => 0 })?.id).toBe('b');
		expect(pickAd(feed, { placement: 'rewarded', now, exclude: ['a'] })?.id).toBe('a');
	});
	test('returns null when nothing runs', () => {
		expect(pickAd(parseFeed({ ads: [] }), { placement: 'banner' })).toBeNull();
	});
});

test('localize falls back to the base language and English', () => {
	const ad = feed.ads[0];
	expect(localize(ad, 'de-AT').cta).toBe('Los');
	expect(localize(ad, 'fa').cta).toBe('Go');
});

describe('frequencyCap', () => {
	const store = new Map<string, string>();
	const storage: CapStorage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => void store.set(k, v) };
	test('limits views per window', () => {
		const cap = frequencyCap({ key: 'k', max: 2, windowMs: 1000, storage });
		const t0 = new Date(0);
		expect(cap.record(t0)).toBe(true);
		expect(cap.record(t0)).toBe(true);
		expect(cap.record(t0)).toBe(false);
		expect(cap.remaining(new Date(1500))).toBe(2);
	});
	test('works when storage throws', () => {
		const broken: CapStorage = {
			getItem: () => {
				throw new Error('blocked');
			},
			setItem: () => {
				throw new Error('blocked');
			}
		};
		const cap = frequencyCap({ key: 'k', max: 1, windowMs: 1000, storage: broken });
		expect(cap.record(new Date(0))).toBe(true);
		expect(cap.record(new Date(0))).toBe(false);
	});
});

describe('v0.2', () => {
	test('keeps safe style fields and categories', async () => {
		const { parseAd, adStyleVars, eventUrl } = await import('./index');
		const ad = parseAd({
			id: 's',
			url: 'https://t.me/s',
			text: { en: text },
			categories: ['news'],
			style: { variant: 'poster', background: '#000', color: 'red;}body{x', accent: '#ff0000' }
		});
		expect(ad?.style).toEqual({ variant: 'poster', background: '#000', accent: '#ff0000' });
		expect(adStyleVars(ad?.style)).toEqual({ '--litfass-bg': '#000', '--litfass-accent': '#ff0000' });
		expect(eventUrl('https://x.example/litfass/v1/feed/abc?x=1')).toBe('https://x.example/litfass/v1/event/abc');
	});

	test('pickAd matches categories', async () => {
		const tagged = parseFeed({
			ads: [
				{ id: 'news', url: 'https://t.me/n', text: { en: text }, categories: ['news'] },
				{ id: 'game', url: 'https://t.me/g', text: { en: text }, categories: ['gaming'] }
			]
		});
		expect(pickAd(tagged, { placement: 'banner', categories: ['gaming'] })?.id).toBe('game');
		expect(pickAd(tagged, { placement: 'banner', categories: ['tech'] })).toBeNull();
	});

	test('fetchFeed falls back when the server fails', async () => {
		const { fetchFeed } = await import('./index');
		const failing = (async () => {
			throw new Error('offline');
		}) as unknown as typeof fetch;
		const feed = await fetchFeed('https://x/v1/feed/k', { fetch: failing, fallback: { ads: [{ id: 'f', url: 'https://t.me/f', text: { en: text } }] } });
		expect(feed.ads.map((ad) => ad.id)).toEqual(['f']);
	});
});
