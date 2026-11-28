<script lang="ts">
	import { onMount } from 'svelte';
	import { injectAdStyles, renderAd, type Ad, type AdStyle } from '@militaernews/litfass';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';
	import { highlight } from './highlight';

	const s = (key: string, values?: Record<string, string>) => (m as unknown as Record<string, ((v?: Record<string, string>) => string) | undefined>)[key]?.(values) ?? '';

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
		text: {
			en: { title: 'Your channel here', body: 'Daily updates, no noise. Register your placement in the bot.', cta: 'Open the bot' },
			de: { title: 'Dein Kanal hier', body: 'Tägliche Updates, ohne Lärm. Registriere deinen Werbeplatz im Bot.', cta: 'Bot öffnen' }
		},
		...extra
	});

	let demo: HTMLDivElement | undefined = $state();

	onMount(() => {
		injectAdStyles();
		demo?.append(
			renderAd(ad('card', { background: '#0c3a6b', color: '#e6f6ff', accent: '#2ec5ff' }), { lang: localeState.value, label: 'Anzeige' }),
			renderAd(ad('banner', { background: '#14161a', color: '#f5f5f5', accent: '#e5484d' }, { emoji: '🎮' }), { lang: localeState.value }),
			renderAd(ad('poster', { background: '#ffd60a', color: '#111111', accent: '#d00000' }, { emoji: '🏆' }), { lang: localeState.value })
		);
	});
</script>

<svelte:head>
	<title>litfass</title>
	<meta name="description" content={s('description')} />
	<meta property="og:title" content="litfass" />
	<meta property="og:description" content={s('description')} />
	<meta property="og:image" content="/social.png" />
	<meta name="twitter:card" content="summary_large_image" />
	<link rel="icon" href="/logo.png" />
</svelte:head>
{#key localeState.value}

<main>
	<header>
		<img src="/logo.png" alt="An advertising pillar on a radar screen" width="180" height="180" />
		<div>
			<h1>litfass</h1>
			<p class="lead">{s('lead')}</p>
			<p class="tags">{s('tags')}</p>
			<div class="actions">
				<a class="button" href="https://t.me/litfass_advertisement_bot">{s('openBot')}</a>
				<a class="button secondary" href={'/manage'}>{s('manage')}</a>
				<a class="button secondary" href="https://militaernews.vercel.app">{s('militaerNews')}</a>
			</div>
		</div>
	</header>

	<h2>{s('whatItDoes')}</h2>
	<div class="grid">
		<div class="card">
			<h3>{s('card1Title')}</h3>
			<p>{s('card1Text')}</p>
		</div>
		<div class="card">
			<h3>{s('card2Title')}</h3>
			<p>{s('card2Text')}</p>
		</div>
		<div class="card">
			<h3>{s('card3Title')}</h3>
			<p>{s('card3Text')}</p>
		</div>
		<div class="card">
			<h3>{s('card4Title')}</h3>
			<p>{s('card4Text')}</p>
		</div>
	</div>

	<h2>{s('looksLike')}</h2>
	<div class="demo" bind:this={demo}></div>

	<h2>{s('showInProject')}</h2>
	<ol>
		<li>{s('step1')} <a href="https://t.me/litfass_advertisement_bot">@litfass_advertisement_bot</a> {@html s('step1b')}</li>
		<li>{s('step2')}</li>
		<li>{@html s('step3')}</li>
	</ol>
	<pre><code class="hljs">{@html webHtml}</code></pre>
	<p></p>
	<pre><code class="hljs">{@html botHtml}</code></pre>

	<h2>{s('keepLegal')}</h2>
	<p>{s('legalText')}</p>

	<footer>
		{s('footer')} <a href="https://militaernews.vercel.app">{s('militaerNews')}</a>
	</footer>
</main>
{/key}
