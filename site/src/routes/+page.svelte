<script lang="ts">
	import { onMount } from 'svelte';
	import { injectAdStyles, renderAd, type Ad, type AdStyle } from '@militaernews/litfass';
	import { highlight } from '../lib/highlight';

	const webCode = `// Web: bun add github:militaernews/litfass
import { createReporter, eventUrl, fetchFeed, injectAdStyles, pickAd, renderAd } from '@militaernews/litfass';

const feed = await fetchFeed(FEED_URL);
const reporter = createReporter(eventUrl(FEED_URL));
const ad = pickAd(feed, { placement: 'banner' });
if (ad) {
	injectAdStyles();
	slot.append(renderAd(ad, { onClick: (ad) => reporter.report(ad, 'click') }));
	reporter.report(ad, 'view');
}`;
	const botCode = `# Telegram bots: pip install "litfass[telegram] @ https://github.com/militaernews/litfass/archive/refs/tags/v0.2.1.tar.gz#subdirectory=python"
from litfass import FrequencyCap, fetch_feed, pick_ad, report_events, send_ad

ads = await fetch_feed(FEED_URL)
ad = pick_ad(ads, "chat")
if ad and CAP.record(chat_id):
    await send_ad(bot, chat_id, ad, lang)
    await report_events(FEED_URL, [(ad.id, "view")])`;
	const webHtml = highlight(webCode, 'typescript');
	const botHtml = highlight(botCode, 'python');

	const ad = (variant: NonNullable<AdStyle['variant']>, style: AdStyle, extra: Partial<Ad> = {}): Ad => ({
		id: variant,
		url: 'https://t.me/litfass_advertisement_bot',
		emoji: '📰',
		style: { variant, ...style },
		text: { en: { title: 'Your channel here', body: 'Daily updates, no noise. Register your placement in the bot.', cta: 'Open the bot' } },
		...extra
	});

	let demo: HTMLDivElement | undefined = $state();

	onMount(() => {
		injectAdStyles();
		demo?.append(
			renderAd(ad('card', { background: '#0c3a6b', color: '#e6f6ff', accent: '#2ec5ff' }), { lang: 'en', label: 'Anzeige' }),
			renderAd(ad('banner', { background: '#14161a', color: '#f5f5f5', accent: '#e5484d' }, { emoji: '🎮' }), { lang: 'en' }),
			renderAd(ad('poster', { background: '#ffd60a', color: '#111111', accent: '#d00000' }, { emoji: '🏆' }), { lang: 'en' })
		);
	});
</script>

<svelte:head>
	<title>litfass</title>
	<meta name="description" content="House adverts for web games, Mini Apps and Telegram bots. No ad network, no tracking, one JSON feed." />
	<meta property="og:title" content="litfass" />
	<meta property="og:description" content="House adverts for web games, Mini Apps and Telegram bots. No ad network, no tracking." />
	<meta property="og:image" content="/social.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<link rel="icon" href="/logo.png" />
</svelte:head>

<main>
	<header>
		<img src="/logo.png" alt="An advertising pillar on a radar screen" width="180" height="180" />
		<div>
			<h1>litfass</h1>
			<p class="lead">House adverts for web games, Mini Apps, Telegram bots and channels.</p>
			<p class="tags">No ad network · no tracking · one JSON feed</p>
			<div class="actions">
				<a class="button" href="https://t.me/litfass_advertisement_bot">Open the bot</a>
				<a class="button secondary" href="/manage">Manage adverts</a>
				<a class="button secondary" href="https://militaernews.vercel.app">Militär News</a>
				<a class="button secondary" href="https://github.com/militaernews/litfass">GitHub</a>
			</div>
		</div>
	</header>

	<h2>What it does</h2>
	<div class="grid">
		<div class="card">
			<h3>📮 Your own posters</h3>
			<p>Adverts for your channels, projects and partners, managed in a Telegram bot: texts per language, link, image, schedule and weight.</p>
		</div>
		<div class="card">
			<h3>🗂 Adverts that fit</h3>
			<p>Placements register themselves and pick the content they publish (news, gaming, tech …). Their feed only carries adverts for that content.</p>
		</div>
		<div class="card">
			<h3>🎨 Styled to match</h3>
			<p>Colour presets or your own colours, as a card, banner or poster. On the web it's themable with CSS variables.</p>
		</div>
		<div class="card">
			<h3>📊 Honest numbers</h3>
			<p>Views, clicks and completed rewarded views as daily totals per advert and placement. No IP addresses, no profiles, no cookies.</p>
		</div>
	</div>

	<h2>Looks like this</h2>
	<div class="demo" bind:this={demo}></div>

	<h2>Show adverts in your project</h2>
	<ol>
		<li>Open <a href="https://t.me/litfass_advertisement_bot">@litfass_advertisement_bot</a> and send <code>/register</code>.</li>
		<li>Name your site, bot or channel and pick the content you publish.</li>
		<li>Use the feed URL the bot gives you with one of the packages below. <code>/stats</code> shows how it's going.</li>
	</ol>
	<pre><code class="hljs">{@html webHtml}</code></pre>
	<p></p>
	<pre><code class="hljs">{@html botHtml}</code></pre>

	<h2>Keep it legal</h2>
	<p>
		Adverts have to be recognisable as adverts (in Germany § 6 DDG and § 5a UWG), so the renderers label them „Anzeige“ by default.
		The feed and the statistics hold no personal data. If you load the feed straight from a visitor's browser, their IP address
		reaches the feed server for that request, but it isn't logged or stored. To keep even that off, fetch the feed on your own server.
	</p>

	<footer>
		MIT licensed · <a href="https://github.com/militaernews/litfass">github.com/militaernews/litfass</a>
		· Built by <a href="https://militaernews.vercel.app">Militär News</a>
	</footer>
</main>
