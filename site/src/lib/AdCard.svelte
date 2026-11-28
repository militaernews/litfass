<script lang="ts">
	import type { Ad } from '@militaernews/litfass';
	import IconMegaphone from '~icons/lucide/megaphone';
	import IconArrowUpRight from '~icons/lucide/arrow-up-right';
	import IconSparkles from '~icons/lucide/sparkles';
	import IconInfo from '~icons/lucide/info';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';

	let {
		ad,
		lang = 'en',
		label = 'Anzeige'
	}: { ad: Ad; lang?: string; label?: string } = $props();

	const text = $derived(ad.text[lang] ?? ad.text.en);
	const style = $derived(
		[
			`--litfass-bg:${ad.style?.background ?? '#0c3a6b'}`,
			`--litfass-fg:${ad.style?.color ?? '#e6f6ff'}`,
			`--litfass-accent:${ad.style?.accent ?? '#2ec5ff'}`
		].join(';')
	);
	const variant = $derived(ad.style?.variant ?? 'card');
	const s = (key: string) => (m as unknown as Record<string, (() => string) | undefined>)[key]?.() ?? '';
	let showWhy = $state(false);
</script>

<article
	class="card relative overflow-hidden border border-base-300 bg-base-100 shadow-md transition-all duration-200 hover:-translate-y-1 hover:shadow-xl"
	class:card-side={variant === 'banner'}
	class:flex-col={variant === 'poster'}
	class:text-center={variant === 'poster'}
	{style}
>
	<div class="absolute right-3 top-3 z-10 flex items-center gap-1 rounded-full bg-black/20 px-2 py-0.5 text-[0.65rem] font-bold uppercase tracking-wider text-white backdrop-blur">
		<IconMegaphone /> {label}
		{#if (ad as any).boosted}<span class="rounded-full bg-amber-400 px-1.5 text-black">★</span>{/if}
		<button class="rounded-full p-0.5 hover:bg-white/20" onclick={() => (showWhy = !showWhy)} aria-label={s('whyAd')}><IconInfo class="size-3" /></button>
	</div>
	{#if showWhy}
		<p class="absolute inset-x-3 top-10 z-10 rounded-lg bg-black/75 px-2.5 py-1.5 text-[0.7rem] text-white backdrop-blur">
			<strong>{s('whyAd')}</strong> {s('whyAdText')}
		</p>
	{/if}

	<div class="flex items-center gap-3 p-4" class:flex-col={variant === 'poster'}>
		<div class="grid size-14 shrink-0 place-items-center overflow-hidden rounded-xl bg-base-200 text-3xl">
			{#if ad.video}
				{#if ad.videoKind === 'video'}
					<video src={ad.video} class="size-full object-cover" autoplay muted loop playsinline></video>
				{:else}
					<img src={ad.video} alt="" class="size-full object-cover" loading="lazy" />
				{/if}
			{:else if ad.image}
				<img src={ad.image} alt="" class="size-full object-cover" loading="lazy" />
			{:else}
				<span aria-hidden="true">{ad.emoji ?? '📰'}</span>
			{/if}
		</div>

		<div class="min-w-0 flex-1">
			<strong class="block truncate text-base font-extrabold tracking-tight">{text.title}</strong>
			<span class="mt-0.5 block text-sm opacity-70">{text.body}</span>
			<div class="mt-3 flex flex-wrap items-center gap-2">
				<a class="btn btn-sm rounded-full" style={`background:var(--litfass-accent);color:#06142a;border:0`} href={ad.url} target="_blank" rel="noreferrer">
					{text.cta} <IconArrowUpRight />
				</a>
				{#if ad.categories?.length}
					<span class="badge badge-outline badge-sm gap-1"><IconSparkles /> {ad.categories[0]}</span>
				{/if}
			</div>
		</div>
	</div>
</article>
