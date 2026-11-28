<script lang="ts">
	import IconUsersRound from '~icons/lucide/users-round';
	import IconCodeXml from '~icons/lucide/code-xml';
	import IconBot from '~icons/lucide/bot';
	import IconArrowRight from '~icons/lucide/arrow-right';
	import IconArrowLeft from '~icons/lucide/arrow-left';
	import IconCheck from '~icons/lucide/check';
	import IconCircleHelp from '~icons/lucide/circle-help';
	import IconLightbulb from '~icons/lucide/lightbulb';
	import IconTelegram from '~icons/logos/telegram';
	import CodeBlock from './CodeBlock.svelte';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';

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
		code?: string;
		language?: 'bash' | 'python' | 'typescript';
		label?: string;
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

	const paths: Record<Path, { card: string; text: string; icon: typeof IconBot; accent: string; steps: Step[] }> = {
		bot: {
			card: 'pathBotCard',
			text: 'pathBotText',
			icon: IconUsersRound,
			accent: 'from-sky-500/20 to-cyan-400/5',
			steps: [
				{ title: 'botS1Title', body: 'botS1Text', href: 'https://t.me/litfass_advertisement_bot?startgroup=new', hrefLabel: 'addBot' },
				{ title: 'botS2Title', body: 'botS2Text' },
				{ title: 'botS3Title', body: 'botS3Text', code: '/post', language: 'bash', label: 'Telegram' },
				{ title: 'botS4Title', body: 'botS4Text', href: 'https://t.me/litfass_advertisement_bot', hrefLabel: 'openBot' }
			]
		},
		web: {
			card: 'pathWebCard',
			text: 'pathWebText',
			icon: IconCodeXml,
			accent: 'from-violet-500/20 to-fuchsia-400/5',
			steps: [
				{ title: 'webS1Title', body: 'webS1Text', code: webInstall, language: 'bash', label: 'Terminal' },
				{ title: 'webS2Title', body: 'webS2Text', code: webCode, language: 'typescript', label: 'page.svelte' },
				{ title: 'webS3Title', body: 'webS3Text', href: 'https://t.me/litfass_advertisement_bot', hrefLabel: 'openBot' },
				{ title: 'webS4Title', body: 'webS4Text' }
			]
		},
		python: {
			card: 'pathPyCard',
			text: 'pathPyText',
			icon: IconBot,
			accent: 'from-amber-500/20 to-orange-400/5',
			steps: [
				{ title: 'pyS1Title', body: 'pyS1Text', code: pyInstall, language: 'bash', label: 'Terminal' },
				{ title: 'pyS2Title', body: 'pyS2Text', code: pyCode, language: 'python', label: 'bot.py' },
				{ title: 'pyS3Title', body: 'pyS3Text', href: 'https://t.me/litfass_advertisement_bot', hrefLabel: 'openBot' },
				{ title: 'pyS4Title', body: 'pyS4Text' }
			]
		}
	};

	let chosen = $state<Path | null>(null);
	let step = $state(0);
	const current = $derived(chosen ? paths[chosen].steps[step] : null);

	function choose(path: Path) {
		chosen = path;
		step = 0;
	}
	function go(index: number) {
		if (chosen && index >= 0 && index < paths[chosen].steps.length) step = index;
	}
</script>

<svelte:head><title>{s('guideTitle')} · litfass</title></svelte:head>

{#key localeState.value}
	<main class="page guide">
		<header class="guide-hero">
			<p class="eyebrow">litfass</p>
			<h1>{s('guideTitle')}</h1>
			<p class="lead">{s('guideLead')}</p>
		</header>

		{#if !chosen}
			<h2 class="choose-title">{s('choosePath')}</h2>
			<div class="path-grid">
				{#each Object.entries(paths) as [id, path] (id)}
					{@const Icon = path.icon}
					<button class="path-card" onclick={() => choose(id as Path)}>
						<span class="path-bg {path.accent}"></span>
						<span class="path-icon"><Icon /></span>
						<strong>{s(path.card)}</strong>
						<span class="path-text">{s(path.text)}</span>
						<span class="path-go">{s('startPath')} <IconArrowRight /></span>
					</button>
				{/each}
			</div>
		{:else if current}
			<div class="wizard-layout">
				<aside class="step-rail">
					<a class="rail-back" href="/guide"><IconArrowLeft /> {s('choosePath')}</a>
					{#each paths[chosen!].steps as item, index (item.title)}
						{@const Icon = index === step ? IconArrowRight : index < step ? IconCheck : paths[chosen!].icon}
						<button class:active={index === step} class:finished={index < step} onclick={() => go(index)}>
							<span class="rail-num">{index + 1}</span>
							<span>{s(item.title)}</span>
							<Icon />
						</button>
					{/each}
				</aside>

				<section class="wizard-panel">
					<div class="wizard-progress">
						<span>{s('stepOf', { n: String(step + 1), total: String(paths[chosen!].steps.length) })}</span>
						<div class="progress-track"><span style={`width:${((step + 1) / paths[chosen!].steps.length) * 100}%`}></span></div>
					</div>
					<h2>{s(current.title)}</h2>
					<p class="wizard-lead">{s(current.body)}</p>
					{#if current.href}
						<a class="action" href={current.href} target="_blank" rel="noreferrer">
							<IconTelegram /> {current.hrefLabel ? s(current.hrefLabel) : s('openBot')} <IconArrowRight />
						</a>
					{/if}
					{#if current.code}
						<CodeBlock code={current.code} language={current.language ?? 'typescript'} label={current.label ?? 'Code'} />
					{/if}
					<div class="wizard-nav">
						<button onclick={() => (step > 0 ? go(step - 1) : (chosen = null))}><IconArrowLeft /> {s('back')}</button>
						{#if step < paths[chosen!].steps.length - 1}
							<button class="primary" onclick={() => go(step + 1)}>{s('next')} <IconArrowRight /></button>
						{:else}
							<a class="primary" href="/manage"><IconCheck /> {s('finish')}</a>
						{/if}
					</div>
				</section>
			</div>
		{/if}

		<aside class="hint-card">
			<IconLightbulb />
			<div>
				<strong>{s('whatIsFeed')}</strong><p>{s('feedExplainer')}</p>
				<a class="support-text" href="https://t.me/litfass_advertisement_bot?start=onboarding" target="_blank" rel="noreferrer">
					<IconTelegram /> {s('oneLink')} <IconArrowRight />
				</a>
			</div>
		</aside>

		<section class="faq">
			<h2><IconCircleHelp /> {s('troubleTitle')}</h2>
			<details><summary>{s('trouble1Q')}</summary><p>{s('trouble1A')}</p></details>
			<details><summary>{s('trouble2Q')}</summary><p>{s('trouble2A')}</p></details>
			<details><summary>{s('trouble3Q')}</summary><p>{s('trouble3A')}</p></details>
			<a class="support-text" href="https://t.me/MilitaernewsKontakt" target="_blank" rel="noreferrer">
				<IconTelegram /> {s('support')}
			</a>
		</section>
	</main>
{/key}
