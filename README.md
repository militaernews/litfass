# litfass

House adverts for web games, Telegram Mini Apps and Telegram bots. A *Litfaßsäule* is the round
advertising pillar on German streets. Like the pillar, litfass only shows posters that you put up
yourself: your own channels, other projects, partners.

- **No ad network, no tracking.** The feed is a JSON file you bundle or host on your own server. No
  third-party requests means no cookie banner under § 25 TDDDG, as long as your images stay on your own origin.
- **One feed format** for the web (`@militaernews/litfass`, TypeScript) and for bots (`litfass`, Python).
- **Rewarded viewings** come as a countdown. Your app grants the reward, e.g. continuing a run.
- **Labelled as adverts.** German law (§ 6 DDG, § 5a UWG) requires adverts to be recognisable as such.
  `ad_html` prefixes "Anzeige", and web renderers should show a label too.

## Feed

```json
{
	"version": 1,
	"ads": [
		{
			"id": "channel",
			"emoji": "📰",
			"url": "https://t.me/yourchannel",
			"placements": ["rewarded", "banner", "chat"],
			"weight": 2,
			"start": "2026-12-01",
			"end": "2027-01-07",
			"text": {
				"en": { "title": "Our channel", "body": "Daily updates.", "cta": "Open" },
				"de": { "title": "Unser Kanal", "body": "Täglich aktuell.", "cta": "Öffnen" }
			}
		}
	]
}
```

`id`, `url` (https only) and an `en` text are required. Everything else is optional. Invalid adverts are
dropped, so one typo doesn't take down the whole feed. See [`feed.schema.json`](feed.schema.json) and
[`examples/feed.json`](examples/feed.json).

## Web

```sh
bun add github:militaernews/litfass#v0.1.0
```

```ts
import { frequencyCap, localize, openAdLink, parseFeed, pickAd, rewardedCountdown } from '@militaernews/litfass';
import raw from './feed.json';

const feed = parseFeed(raw);
const cap = frequencyCap({ key: 'litfass:rewarded', max: 5, windowMs: 86_400_000, storage: localStorage });

const ad = pickAd(feed, { placement: 'rewarded' });
if (ad && cap.remaining() > 0) {
	const { title, body, cta } = localize(ad, navigator.language);
	// render title/body/cta in your own UI, the button calls openAdLink(ad.url)
	rewardedCountdown(5, { onTick: (s) => render(s), onDone: () => { cap.record(); grantReward(); } });
}
```

`openAdLink` opens `t.me` links inside Telegram when running as a Mini App (`Telegram.WebApp.openTelegramLink`)
and opens anything else in a new tab.

## Telegram bots

```sh
pip install "litfass[telegram] @ git+https://github.com/militaernews/litfass@v0.1.0#subdirectory=python"
```

```python
from litfass import FrequencyCap, load_feed, pick_ad, send_ad

ADS = load_feed("feed.json")
CAP = FrequencyCap(max_views=1, window=6 * 3600)  # one advert per chat every six hours

async def maybe_advertise(bot, chat_id: int, lang: str | None):
    ad = pick_ad(ADS, "chat")
    if ad and CAP.record(chat_id):
        await send_ad(bot, chat_id, ad, lang)
```

## Development

```sh
bun install && bun test src && bun run build   # dist/ is committed so git installs need no build step
cd python && pytest -q
```

MIT licensed.
