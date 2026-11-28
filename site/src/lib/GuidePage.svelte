<script lang="ts">
	import IconUsersRound from '~icons/lucide/users-round';
	import IconCodeXml from '~icons/lucide/code-xml';
	import IconBot from '~icons/lucide/bot';
	import IconArrowRight from '~icons/lucide/arrow-right';
	import IconArrowLeft from '~icons/lucide/arrow-left';
	import IconCopy from '~icons/lucide/copy';
	import IconCheck from '~icons/lucide/check';
	import IconCircleHelp from '~icons/lucide/circle-help';
	import IconLightbulb from '~icons/lucide/lightbulb';
	import IconTelegram from '~icons/logos/telegram';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';
	import { highlight } from './highlight';

	const s = (key: string, values: Record<string, string> = {}) => {
		const fn = (m as unknown as Record<string, ((v?: Record<string, string>) => string) | undefined>)[key];
		let text = fn?.(values) ?? '';
		for (const [name, value] of Object.entries(values)) text = text.replace(`{${name}}`, value);
		return text;
	};

	type Path = 'bot' | 'web' | 'python';
	interface Step {
		title: string;
		body: string;
		href?: string;
		hrefLabel?: string;
		install?: string;
		code?: string;
		language?: 'typescript' | 'python';
	}
	const webInstall = 'bun add github:militaernews/litfass';
	const pyInstall = 'pip install "litfass[telegram] @ https://github.com/militaernews/litfass/archive/refs/tags/v0.2.1.tar.gz#subdirectory=python"';
	const webCode = `import { createReporter, eventUrl, fetchFeed, injectAdStyles, pickAd, renderAd } from '@militaernews/litfass';

const feed = await fetchFeed(FEED_URL);
const reporter = createReporter(eventUrl(FEED_URL));
const ad = pickAd(feed, { placement: 'banner' });
if (ad) {
	injectAdStyles();
	slot.append(renderAd(ad, { onClick: (ad) => reporter.report(ad, 'click') }));
	reporter.report(ad, 'view');
}`;
	const pyCode = `from litfass import FrequencyCap, fetch_feed, pick_ad, report_events, send_ad

CAP = FrequencyCap(max_views=1, window=6 * 3600)

feed = await fetch_feed(FEED_URL)
ad = pick_ad(feed, "chat")
if ad and CAP.record(chat_id):
    await send_ad(bot, chat_id, ad, lang)
    await report_events(FEED_URL, [(ad.id, "view")])`;

	const paths: Record<Path, { card: string; text: string; icon: typeof IconBot; steps: Step[] }> = {
		bot: {
			card: 'pathBotCard',
			text: 'pathBotText',
			icon: IconUsersRound,
			steps: [
				{ title: 'botS1Title', body: 'botS1Text', href: 'https://t.me/litfass_advertisement_bot?startgroup=new', hrefLabel: 'addBot' },
				{ title: 'botS2Title', body: 'botS2Text' },
				{ title: 'botS3Title', body: 'botS3Text', code: '/post', language: 'typescript' },
				{ title: 'botS4Title', body: 'botS4Text', href: 'https://t.me/litfass_advertisement_bot', hrefLabel: 'openBot' }
			]
		},
		web: {
			card: 'pathWebCard',
			text: 'pathWebText',
			icon: IconCodeXml,
			steps: [
				{ title: 'webS1Title', body: 'webS1Text', install: webInstall },
				{ title: 'webS2Title', body: 'webS2Text', code: webCode, language: 'typescript' },
				{ title: 'webS3Title', body: 'webS3Text', href: 'https://t.me/litfass_advertisement_bot', hrefLabel: 'openBot' },
				{ title: 'webS4Title', body: 'webS4Text' }
			]
		},
		python: {
			card: 'pathPyCard',
			text: 'pathPyText',
			icon: IconBot,
			steps: [
				{ title: 'pyS1Title', body: 'pyS1Text', install: pyInstall },
				{ title: 'pyS2Title', body: 'pyS2Text', code: pyCode, language: 'python' },
				{ title: 'pyS3Title', body: 'pyS3Text', href: 'https://t.me/litfass_advertisement_bot', hrefLabel: 'openBot' },
				{ title: 'pyS4Title', body: 'pyS4Text' }
			]
		}
	};

	let chosen = $state<Path | null>(null);
	let step = $state(0);
	let copied = $state('');
	const current = $derived(chosen ? paths[chosen].steps[step] : null);

	async function copy(text: string, key: string) {
		await navigator.clipboard.writeText(text);
		copied = key;
		setTimeout(() => (copied = ''), 1500);
	}

	function choose(path: Path) {
		chosen = path;
		step = 0;
	}

	function next() {
		if (chosen && step < paths[chosen].steps.length - 1) step += 1;
	}
	function back() {
		if (step > 0) step -= 1;
		else chosen = null;
	}
</script>

<svelte:head>
	<title>{s('guideTitle')} · litfass</title>
	<meta name="description" content={s('guideLead')} />
</svelte:head>

{#key localeState.value}
	<main class="page guide">
		<header class="guide-head">
			<p class="eyebrow">litfass</p>
			<h1>{s('guideTitle')}</h1>
			<p class="lead">{s('guideLead')}</p>
		</header>

		{#if !chosen}
			<h2 class="choose-title">{s('choosePath')}</h2>
			<div class="path-cards">
				{#each Object.entries(paths) as [id, path] (id)}
					{@const Icon = path.icon}
					<button onclick={() => choose(id as Path)}>
						<span class="path-icon"><Icon /></span>
						<strong>{s(path.card)}</strong>
						<span class="path-text">{s(path.text)}</span>
						<span class="path-go">{s('startPath')} <IconArrowRight /></span>
					</button>
				{/each}
			</div>
		{:else if current}
			<section class="wizard">
				<div class="wizard-top">
					<span>{s('stepOf', { n: String(step + 1), total: String(paths[chosen!].steps.length) })}</span>
					<div class="progress">
						{#each paths[chosen!].steps as _, index (index)}
							<span class:on={index <= step}></span>
						{/each}
					</div>
				</div>
				<h2>{s(current.title)}</h2>
				<p>{s(current.body)}</p>

				{#if current.href}
					<a class="action" href={current.href} target="_blank" rel="noreferrer">
						<IconTelegram /> {current.hrefLabel ? s(current.hrefLabel) : s('openBot')} <IconArrowRight />
					</a>
				{/if}
				{#if current.install}
					<div class="code">
						<div class="code-head">
							<span>Terminal</span>
							<button onclick={() => copy(current.install!, 'install')} aria-label={s('copy')}>
								{#if copied === 'install'}<IconCheck />{:else}<IconCopy />{/if} {s(copied === 'install' ? 'copied' : 'copy')}
							</button>
						</div>
						<pre><code>{current.install}</code></pre>
					</div>
				{/if}
				{#if current.code}
					<div class="code">
						<div class="code-head">
							<span>{current.language === 'python' ? 'Python' : 'TypeScript'}</span>
							<button onclick={() => copy(current.code!, 'code')} aria-label={s('copy')}>
								{#if copied === 'code'}<IconCheck />{:else}<IconCopy />{/if} {s(copied === 'code' ? 'copied' : 'copy')}
							</button>
						</div>
						<pre><code class="hljs">{@html highlight(current.code, current.language ?? 'typescript')}</code></pre>
					</div>
				{/if}

				<div class="wizard-nav">
					<button onclick={back}><IconArrowLeft /> {s('back')}</button>
					{#if step < paths[chosen!].steps.length - 1}
						<button class="primary" onclick={next}>{s('next')} <IconArrowRight /></button>
					{:else}
						<button class="primary" onclick={() => (chosen = null)}><IconCheck /> {s('finish')}</button>
					{/if}
				</div>
			</section>
		{/if}

		<aside class="hint">
			<IconLightbulb />
			<div><strong>{s('whatIsFeed')}</strong><p>{s('feedExplainer')}</p></div>
		</aside>

		<section class="trouble">
			<h2><IconCircleHelp /> {s('troubleTitle')}</h2>
			<details><summary>{s('trouble1Q')}</summary><p>{s('trouble1A')}</p></details>
			<details><summary>{s('trouble2Q')}</summary><p>{s('trouble2A')}</p></details>
			<details><summary>{s('trouble3Q')}</summary><p>{s('trouble3A')}</p></details>
		</section>

		<footer>
			<a class="support-link" href="https://t.me/MilitaernewsKontakt" target="_blank" rel="noreferrer">
				<IconTelegram /> {s('support')} <IconArrowRight />
			</a>
		</footer>
	</main>
{/key}
