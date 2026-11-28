<script lang="ts">
	import IconUsersRound from '~icons/lucide/users-round';
	import IconCodeXml from '~icons/lucide/code-xml';
	import IconBot from '~icons/lucide/bot';
	import IconCopy from '~icons/lucide/copy';
	import IconCheck from '~icons/lucide/check';
	import IconArrowRight from '~icons/lucide/arrow-right';
	import IconTelegram from '~icons/logos/telegram';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';
	import { highlight } from './highlight';

	const s = (key: string) => (m as unknown as Record<string, (() => string) | undefined>)[key]?.() ?? '';
	type Tab = 'bot' | 'web' | 'python';
	const tabs: { id: Tab; icon: typeof IconBot; label: string }[] = [
		{ id: 'bot', icon: IconUsersRound, label: 'guide1Title' },
		{ id: 'web', icon: IconCodeXml, label: 'guide2Title' },
		{ id: 'python', icon: IconBot, label: 'guide3Title' }
	];

	const webInstall = 'bun add github:militaernews/litfass';
	const webCode = `import { createReporter, eventUrl, fetchFeed, injectAdStyles, pickAd, renderAd } from '@militaernews/litfass';

const feed = await fetchFeed(FEED_URL);
const reporter = createReporter(eventUrl(FEED_URL));
const ad = pickAd(feed, { placement: 'banner' });
if (ad) {
	injectAdStyles();
	slot.append(renderAd(ad, { onClick: (ad) => reporter.report(ad, 'click') }));
	reporter.report(ad, 'view');
}`;
	const pyInstall = 'pip install "litfass[telegram] @ https://github.com/militaernews/litfass/archive/refs/tags/v0.2.1.tar.gz#subdirectory=python"';
	const pyCode = `from litfass import FrequencyCap, fetch_feed, pick_ad, report_events, send_ad

CAP = FrequencyCap(max_views=1, window=6 * 3600)

feed = await fetch_feed(FEED_URL)
ad = pick_ad(feed, "chat")
if ad and CAP.record(chat_id):
    await send_ad(bot, chat_id, ad, lang)
    await report_events(FEED_URL, [(ad.id, "view")])`;
	const webHtml = highlight(webCode, 'typescript');
	const pyHtml = highlight(pyCode, 'python');

	let tab = $state<Tab>('bot');
	let copied = $state('');

	async function copy(text: string, key: string) {
		await navigator.clipboard.writeText(text);
		copied = key;
		setTimeout(() => (copied = ''), 1500);
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

		<nav class="guide-tabs" aria-label={s('guideTitle')}>
			{#each tabs as item (item.id)}
				{@const Icon = item.icon}
				<button class:active={tab === item.id} onclick={() => (tab = item.id)}>
					<Icon /> {s(item.label)}
				</button>
			{/each}
		</nav>

		{#if tab === 'bot'}
			<section class="guide-panel">
				<h2>{s('guide1Title')}</h2>
				<p>{s('guide1Text')}</p>
				<ol class="steps">
					{#each ['guide1Step1', 'guide1Step2', 'guide1Step3'] as step, index (step)}
						<li><span>{index + 1}</span>{s(step)}</li>
					{/each}
				</ol>
				<a class="primary" href="https://t.me/litfass_advertisement_bot?startgroup=new" target="_blank" rel="noreferrer">
					<IconTelegram /> {s('addBot')} <IconArrowRight />
				</a>
			</section>
		{:else}
			<section class="guide-panel">
				<h2>{s(tab === 'web' ? 'guide2Title' : 'guide3Title')}</h2>
				<p>{s(tab === 'web' ? 'guide2Text' : 'guide3Text')}</p>
				<div class="code">
					<div class="code-head">
						<span>{tab === 'web' ? 'Terminal' : 'pip'}</span>
						<button onclick={() => copy(tab === 'web' ? webInstall : pyInstall, 'install')} aria-label={s('copy')}>
							{#if copied === 'install'}<IconCheck />{:else}<IconCopy />{/if} {s(copied === 'install' ? 'copied' : 'copy')}
						</button>
					</div>
					<pre><code>{tab === 'web' ? webInstall : pyInstall}</code></pre>
				</div>
				<div class="code">
					<div class="code-head">
						<span>{tab === 'web' ? 'TypeScript' : 'Python'}</span>
						<button onclick={() => copy(tab === 'web' ? webCode : pyCode, 'code')} aria-label={s('copy')}>
							{#if copied === 'code'}<IconCheck />{:else}<IconCopy />{/if} {s(copied === 'code' ? 'copied' : 'copy')}
						</button>
					</div>
					<pre><code class="hljs">{@html tab === 'web' ? webHtml : pyHtml}</code></pre>
				</div>
			</section>
		{/if}

		<aside class="feed-hint">
			<IconBot />
			<div>
				<strong>{s('getFeed')}</strong>
				<p>{s('feedHint')}</p>
			</div>
			<a href="https://t.me/litfass_advertisement_bot" target="_blank" rel="noreferrer"><IconTelegram /></a>
		</aside>

		<footer>
			<a class="support-link" href="https://t.me/MilitaernewsKontakt" target="_blank" rel="noreferrer">
				<IconTelegram /> {s('needHelp')}
			</a>
		</footer>
	</main>
{/key}
