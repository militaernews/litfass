<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import IconArrowLeft from '~icons/lucide/arrow-left';
	import IconArrowRight from '~icons/lucide/arrow-right';
	import IconCheck from '~icons/lucide/check';
	import IconTelegram from '~icons/logos/telegram';
	import AdFields from './AdFields.svelte';
	import AdCard from './AdCard.svelte';
	import { call } from './api';
	import { asAd, emptyDraft, toPayload, type Draft } from './adForm';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';

	const s = (key: string, values: Record<string, string> = {}) => {
		const fn = (m as unknown as Record<string, ((v?: Record<string, string>) => string) | undefined>)[key];
		let text = fn?.(values) ?? '';
		for (const [name, value] of Object.entries(values)) text = text.replace(`{${name}}`, value);
		return text;
	};
	const steps = [
		{ key: 'stepLink', section: ['link'] },
		{ key: 'stepTexts', section: ['texts'] },
		{ key: 'stepLook', section: ['look'] },
		{ key: 'stepReview', section: [] }
	];

	let draft = $state<Draft>(emptyDraft());
	let step = $state(0);
	let busy = $state(false);
	let error = $state('');

	onMount(async () => {
		try {
			await call('me');
		} catch {
			await goto('/login', { replaceState: true });
		}
	});

	function next() {
		error = '';
		if (step === 0 && (!draft.url.startsWith('https://') || draft.url.includes(' '))) {
			error = s('eHttps');
			return;
		}
		if (step === 1 && (!draft.en.title || !draft.en.cta)) {
			error = s('needText');
			return;
		}
		if (step < steps.length - 1) step += 1;
	}

	async function save() {
		busy = true;
		error = '';
		try {
			await call('create_ad', toPayload(draft));
			await goto('/manage');
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Could not save';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>{s('createAdvertPage')} · litfass</title></svelte:head>

{#key localeState.value}
	<main class="manager editor-page">
		<button class="back" onclick={() => goto('/manage')}><IconArrowLeft /> {s('backToManager')}</button>
		<header class="editor-head">
			<h1>{s('createAdvertPage')}</h1>
			<p>{s('stepOf', { n: String(step + 1), total: String(steps.length) })}</p>
		</header>

		<div class="progress-wide">
			{#each steps as item, index (item.key)}
				<span class:active={index === step} class:done={index < step}>{index + 1}. {s(item.key)}</span>
			{/each}
		</div>

		<section class="editor-card">
			<h2>{s(steps[step].key)}</h2>
			{#if step < 3}
				<AdFields {draft} sections={steps[step].section} />
			{:else}
				<div class="preview-wrap">
					<AdCard ad={asAd(draft)} lang={localeState.value} />
				</div>
				<ul class="summary">
					<li>{s('link')}: {draft.url}</li>
					<li>{s('englishText')}: {draft.en.title} · {draft.en.cta}</li>
					<li>{s('look')}: {draft.variant} · {draft.categories.join(', ') || '–'}</li>
					<li>{draft.paid ? s('b_paid') : s('b_free')}</li>
				</ul>
			{/if}
			{#if error}<p class="alert" role="alert">{error}</p>{/if}
			<div class="editor-nav">
				{#if step > 0}
					<button onclick={() => (step -= 1)}><IconArrowLeft /> {s('back')}</button>
				{:else}
					<button class="btn-ghost" onclick={() => goto('/manage')}><IconArrowLeft /> {s('backToManager')}</button>
				{/if}
				{#if step < 3}
					<button class="primary" onclick={next}>{s('next')} <IconArrowRight /></button>
				{:else}
					<button class="primary" disabled={busy} onclick={save}><IconCheck /> {busy ? s('saving') : s('saveAdvert')}</button>
				{/if}
			</div>
		</section>
		<p class="privacy"><IconTelegram /> {s('privacyNote')}</p>
	</main>
{/key}
