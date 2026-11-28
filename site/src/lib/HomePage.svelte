<script lang="ts">
	import { onMount } from 'svelte';
	import IconArrowRight from '~icons/lucide/arrow-right';
	import IconExternalLink from '~icons/lucide/external-link';
	import IconBookOpen from '~icons/lucide/book-open';
	import IconLayoutGrid from '~icons/lucide/layout-grid';
	import IconGamepad2 from '~icons/lucide/gamepad-2';
	import IconUsersRound from '~icons/lucide/users-round';
	import IconChart from '~icons/lucide/chart-no-axes-column-increasing';
	import IconGlobe from '~icons/lucide/globe';
	import IconScanEye from '~icons/lucide/scan-eye';
	import IconRadio from '~icons/lucide/radio';
	import IconMegaphone from '~icons/lucide/megaphone';
	import IconShieldCheck from '~icons/lucide/shield-check';
	import IconSparkles from '~icons/lucide/sparkles';
	import IconSend from '~icons/lucide/send';
	import IconTelegram from '~icons/logos/telegram';
	import IconCode from '~icons/lucide/code-xml';
	import IconTerminal from '~icons/lucide/terminal';
	import IconPlay from '~icons/lucide/play';
	import IconMaximize from '~icons/lucide/maximize';
	import { injectAdStyles, renderAd, showInterstitial, showTaskInterstitial, type Ad, type AdStyle } from '@militaernews/litfass';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';
	import { highlight } from './highlight';

	const s = (key: string) => (m as unknown as Record<string, (() => string) | undefined>)[key]?.() ?? '';

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

	const features = [
		{ icon: IconGlobe, title: 'card1Title', text: 'card1Text' },
		{ icon: IconLayoutGrid, title: 'card2Title', text: 'card2Text' },
		{ icon: IconSparkles, title: 'card3Title', text: 'card3Text' },
		{ icon: IconChart, title: 'card4Title', text: 'card4Text' }
	];

	let demo: HTMLDivElement | undefined = $state();
	const demoPost = 'https://t.me/blog_itisinteresting/6536';

	function taskDemo() {
		showTaskInterstitial(
			{ ...ad('poster', { background: '#0c3a6b', color: '#e6f6ff', accent: '#2ec5ff' }), task: { type: 'join', chat: 'blog_itisinteresting' } },
			{
				mode: 'fullscreen',
				onVerify: async () => {
					await new Promise((done) => setTimeout(done, 600));
					return true;
				},
				labels: { join: s('join'), verify: s('verify'), notJoined: s('notJoined'), botMissing: s('botMissing') }
			}
		);
	}

	async function play(mode: 'modal' | 'fullscreen') {
		const response = await fetch(`/litfass/v1/video?url=${encodeURIComponent(demoPost)}`);
		if (!response.ok) return;
		const media = (await response.json()) as { url: string; kind: 'video' | 'gif' };
		showInterstitial(
			{
				...ad('poster', { background: '#0c3a6b', color: '#e6f6ff', accent: '#2ec5ff' }),
				video: media.url,
				videoKind: media.kind
			},
			{ mode, label: 'Anzeige' }
		);
	}


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
	<link rel="icon" href="/icon.png" />
	<link rel="apple-touch-icon" href="/icon.png" />
</svelte:head>

{#key localeState.value}
	<main class="page">
		<section class="hero">
			<img class="hero-mark" src="/logo.png" alt="An advertising pillar on a radar screen" width="148" height="148" />
			<h1>litfass<span>.</span></h1>
			<p class="lead">{s('lead')}</p>
			<div class="actions">
				<a class="tg" href="https://t.me/litfass_advertisement_bot?startapp=manage" target="_blank" rel="noreferrer">
					<IconSend /> <span>{s('signUp')}</span>
				</a>
				<a class="button" href="/guide"><IconBookOpen /> {s('guideTitle')}</a>
				<a class="button" href="/manage"><IconArrowRight /> {s('manage')}</a>
				<a class="button ghost" href="https://militaernews.vercel.app" target="_blank" rel="noreferrer">
					{s('militaerNews')} <IconExternalLink />
				</a>
			</div>
			<p class="privacy"><IconShieldCheck /> {s('privacyNote')}</p>
		</section>

		<section>
			<h2>{s('whatItDoes')}</h2>
			<div class="grid">
				{#each features as feature (feature.title)}
					<article class="feature">
						<span class="feature-icon"><feature.icon /></span>
						<h3>{s(feature.title)}</h3>
						<p>{s(feature.text)}</p>
					</article>
				{/each}
			</div>
		</section>

		<section>
			<h2>{s('looksLike')}</h2>
			<div class="showcase">
				<div class="showcase-head"><IconBookOpen /> {s('looksLike')}</div>
				<div class="demo" bind:this={demo}></div>
			</div>
		</section>

		<section>
			<h2>{s('showInProject')}</h2>
			<div class="codes">
				<div class="code">
					<div class="code-head"><IconCode /> Web · TypeScript</div>
					<pre><code class="hljs">{@html webHtml}</code></pre>
				</div>
				<div class="code">
					<div class="code-head"><IconTerminal /> Telegram · Python</div>
					<pre><code class="hljs">{@html botHtml}</code></pre>
				</div>
			</div>
		</section>

		<section class="video-demo">
			<h2>{s('videoDemo')}</h2>
			<p>{s('videoHint')}</p>
			<div class="video-actions">
				<button onclick={() => play('modal')}><IconPlay /> {s('modal')}</button>
				<button onclick={() => play('fullscreen')}><IconMaximize /> {s('fullscreen')}</button>
				<button onclick={taskDemo}><IconTelegram /> {s('taskDemo')}</button>
			</div>
		</section>

		<section class="legal">
			<IconShieldCheck />
			<div><h2>{s('keepLegal')}</h2><p>{s('legalText')}</p></div>
		</section>

		<footer>
			<a class="support-link" href="https://t.me/MilitaernewsKontakt" target="_blank" rel="noreferrer">
				<IconTelegram /> {s('footer')} <IconArrowRight />
			</a>
			<nav class="site-links">
				<a href="/guide">{s('guideTitle')}</a>
				<a href="/settings">{s('settingsLink')}</a>
				<a href="/about">{s('aboutLink')}</a>
			</nav>
		</footer>
	</main>
{/key}
