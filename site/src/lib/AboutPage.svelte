<script lang="ts">
	import IconInfo from '~icons/lucide/info';
	import IconScale from '~icons/lucide/scale';
	import IconArrowRight from '~icons/lucide/arrow-right';
	import IconShieldCheck from '~icons/lucide/shield-check';
	import IconSend from '~icons/logos/telegram';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';

	const s = (key: string) => (m as unknown as Record<string, (() => string) | undefined>)[key]?.() ?? '';
	const legal = [
		{ slug: 'imprint', label: 'legalImprint' },
		{ slug: 'privacy', label: 'legalPrivacy' },
		{ slug: 'terms', label: 'legalTerms' },
		{ slug: 'withdrawal', label: 'legalWithdrawal' }
	];
	const site = 'https://militaernews.vercel.app';
</script>

<svelte:head>
	<title>{s('aboutTitle')} · litfass</title>
	<meta name="description" content={s('aboutLead')} />
</svelte:head>

{#key localeState.value}
	<main class="page about">
		<header class="about-head">
			<img src="/logo.png" alt="litfass" width="104" height="104" />
			<p class="eyebrow">litfass</p>
			<h1>{s('aboutTitle')}</h1>
			<p class="lead">{s('aboutLead')}</p>
		</header>

		<section>
			<h2><IconShieldCheck /> {s('legal')}</h2>
			<p class="muted">{s('keepLegal')}</p>
			<ul class="legal-list">
				{#each legal as item (item.slug)}
					<li>
						<a href={`${site}/legal/${item.slug}`} target="_blank" rel="noreferrer">
							<IconScale /> {s(item.label)} <IconArrowRight />
						</a>
					</li>
				{/each}
			</ul>
		</section>

		<section class="contact">
			<IconSend />
			<h2>{s('support')}</h2>
			<a class="support-link" href="https://t.me/MilitaernewsKontakt" target="_blank" rel="noreferrer">
				<IconSend /> @MilitaernewsKontakt <IconArrowRight />
			</a>
		</section>

		<nav class="links">
			<a href="/settings"><IconInfo /> {s('settingsLink')} <IconArrowRight /></a>
			<a href="/guide"><IconInfo /> {s('guideTitle')} <IconArrowRight /></a>
		</nav>
	</main>
{/key}
