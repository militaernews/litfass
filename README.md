<p align="center"><img src="brand/social.png" alt="litfass: house adverts for web games, Mini Apps and Telegram bots" width="720"></p>

# litfass

House adverts for web games, Telegram Mini Apps, bots and channels. A *Litfaßsäule* is the round
advertising pillar on German streets. Like the pillar, litfass only shows posters you put up yourself:
your channels, other projects, partners.

- **No ad network, no tracking.** Statistics are daily totals per advert and placement. No IP addresses,
  user ids or cookies, and no access log on the feed server.
- **Managed in Telegram.** Admins create and style adverts in [@litfass_advertisement_bot](https://t.me/litfass_advertisement_bot).
  Anyone can register a placement (website, Mini App, bot, channel), pick the content it publishes and get
  a feed that only carries adverts for that content.
- **One feed format** for the web (`@militaernews/litfass`, TypeScript) and for bots (`litfass`, Python).
- **Labelled as adverts.** German law (§ 6 DDG, § 5a UWG) requires adverts to be recognisable as such,
  so the renderers add "Anzeige" by default.

| Folder | What it is |
| --- | --- |
| `src/`, `dist/` | Web package: parse, pick (placement, schedule, weight, categories), render with styles, report events |
| `python/` | Python package for bots: the same feed rendered as Telegram messages, frequency caps, event reports |
| `server/` | Management bot plus feed server (python-telegram-bot, aiohttp, SQLite) |
| `site/`, `vercel.json` | The landing page |
| `brand/` | Logo and social image, drawn from `brand/brand.json` with the brand generator in [militaernews/tools](https://github.com/militaernews/tools) |

## The bot

**Everyone**

- `/register`: name your placement, choose where the ads appear and which content you publish. You get a
  feed URL. Keep it to yourself, because it identifies your placement in the statistics.
- `/mine`: your placements. Change their content, rename them, get a new key, delete them, see their stats.
- `/stats`: views, clicks (and click rate) and completed rewarded views for the last 7 and 30 days, a
  14-day sparkline, and the numbers per advert.

**Admins** (`LITFASS_ADMIN_IDS`)

- `/newad`, `/ads`: the link, texts per language, emoji or image, content categories, placements
  (rewarded, banner, chat), weight, schedule, and a style: colour presets (radar, olive, night, paper,
  alert, sky) or your own colours, as a card, banner or poster. New adverts start paused.
- `/publishers`: every placement, with block/unblock.
- `/stats` and the 📊 button on each advert: the same overview, broken down per placement.

Matching: an advert without categories runs everywhere, a placement without categories takes every
advert, otherwise they must share a category.

The bot speaks English and German, following the user's Telegram language. Its texts live in
`server/res/strings/en.json` and `de.json` (loaded with [ptb-kit](https://github.com/militaernews/ptb-kit));
another language is one more JSON file there, and keys it leaves out fall back to English.

## Feed format

```json
{
	"version": 1,
	"ads": [
		{
			"id": "channel",
			"emoji": "📰",
			"url": "https://t.me/yourchannel",
			"placements": ["rewarded", "banner", "chat"],
			"categories": ["news", "military"],
			"weight": 2,
			"start": "2026-12-01",
			"end": "2027-01-07",
			"style": { "variant": "card", "background": "#0c3a6b", "color": "#e6f6ff", "accent": "#2ec5ff" },
			"text": {
				"en": { "title": "Our channel", "body": "Daily updates.", "cta": "Open" },
				"de": { "title": "Unser Kanal", "body": "Täglich aktuell.", "cta": "Öffnen" }
			}
		}
	]
}
```

`id`, `url` (https only) and an `en` text are required. Invalid adverts are dropped, so one typo doesn't
take down the whole feed, and style values that aren't plain colours are ignored. See
[`feed.schema.json`](feed.schema.json). A bundled feed in this format works without any server.

## Server API

| Request | What it does |
| --- | --- |
| `GET /v1/feed/<key>` | The placement's feed, already matched to its content (CORS open, cached 5 min) |
| `POST /v1/event/<key>` | `{ ad, event }` or `{ events: [...] }` with `view`, `click` or `reward`; counted into daily totals, at most 600 a minute per key |
| `GET /v1/stats/<key>` | The placement's own numbers: totals for 7 and 30 days, each of the last 30 days, per advert |
| `GET /v1/admin/stats` | The whole network (every advert and placement); needs `Authorization: Bearer <LITFASS_STATS_TOKEN>` |
| `GET /v1/media/<ad>` | An advert's image (uploaded to the bot as a photo) |

Routes also answer under `/litfass/…` for reverse proxies that keep the prefix.

## Web

```sh
bun add github:militaernews/litfass#v0.2.1
```

```ts
import { createReporter, eventUrl, fetchFeed, injectAdStyles, pickAd, renderAd, rewardedCountdown } from '@militaernews/litfass';

const feed = await fetchFeed(FEED_URL, { fallback: bundledFeed });
const reporter = createReporter(eventUrl(FEED_URL));

const ad = pickAd(feed, { placement: 'banner' });
if (ad) {
	injectAdStyles();
	slot.append(renderAd(ad, { onClick: (ad) => reporter.report(ad, 'click') }));
	reporter.report(ad, 'view');
}
```

The look comes from the advert's `style`. Override it with the CSS variables `--litfass-bg`,
`--litfass-fg` and `--litfass-accent`, or with the `.litfass-ad`, `.litfass-ad--card|banner|poster` and
`.litfass-ad__*` classes. Apps with their own markup can use `adStyleVars(ad.style)`. For rewarded slots,
`rewardedCountdown(seconds, { onTick, onDone })` runs the timer, and your app grants the reward and
reports `reward`. `openAdLink` opens `t.me` links inside Telegram when running as a Mini App.

Loading the feed from the browser sends the visitor's IP address to the feed server for that request.
Nothing is logged, but if you want to avoid even that, fetch the feed (and send events) from your own backend.

## Telegram bots

```sh
pip install "litfass[telegram] @ https://github.com/militaernews/litfass/archive/refs/tags/v0.2.1.tar.gz#subdirectory=python"   # no git needed
```

```python
from litfass import FrequencyCap, fetch_feed, pick_ad, report_events, send_ad

CAP = FrequencyCap(max_views=1, window=6 * 3600)  # one advert per chat every six hours

async def maybe_advertise(bot, chat_id: int, lang: str | None):
    ads = await fetch_feed(FEED_URL)
    ad = pick_ad(ads, "chat")
    if ad and CAP.record(chat_id):
        await send_ad(bot, chat_id, ad, lang)
        await report_events(FEED_URL, [(ad.id, "view")])
```

## Running the server

```sh
cd server
pip install -r requirements.txt
LITFASS_TOKEN=… LITFASS_ADMIN_IDS=123,456 LITFASS_PUBLIC_URL=https://ads.example.org python -m litfass_server
python -m litfass_server.profile   # once: name, descriptions and the logo as profile photo
```

`LITFASS_DB` (default `data/litfass.db`), `LITFASS_PORT` (default 3792) and `LITFASS_STATS_TOKEN` (unlocks `/v1/admin/stats`) are optional.

## Web app and manager

`site/` is a static SvelteKit app and the Vercel project's Root Directory. `vercel.json` at the
repository root is the whole deployment contract: Vercel installs and builds in `site/`, serves
`site/build/`, and forwards `/litfass/*` through the single function `site/api/proxy.ts` to the
feed server, which runs next to its database outside Vercel. Set `API_ORIGIN` in the Vercel project
to the feed server's origin — that address is never part of a feed URL or the repository.
Set `LITFASS_PUBLIC_URL` on the server to
`https://<your-site>/litfass` so feeds, events, images and statistics all use the site's address.

Open `/manage` from [@litfass_advertisement_bot](https://t.me/litfass_advertisement_bot) to create,
edit, pause, publish and delete adverts and read the statistics. The manager sends the Mini App
`initData` to `POST /v1/admin/ui`; the server checks it against `LITFASS_TOKEN` and only
`LITFASS_ADMIN_IDS` may change adverts. Outside Telegram the page is read-only. Locally,
`VITE_API_ORIGIN` points the dev proxy at a feed server on `localhost:3792`.

## Development

```sh
bun install && bun test src && bun run build    # dist/ is committed so git installs need no build step
cd site && bun install && bun run check && bun run build
cd python && pytest -q
cd server && pip install -r requirements.txt pytest-asyncio pytest-aiohttp && pytest -q
```

CI runs all three suites, checks that `dist/` matches the sources and validates the example feed.

MIT licensed.
