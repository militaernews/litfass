<script lang="ts">
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';
	import type { Draft } from './adForm';

	let {
		draft,
		sections = ['link', 'texts', 'look', 'settings']
	}: { draft: Draft; sections?: string[] } = $props();

	const s = (key: string) => (m as unknown as Record<string, (() => string) | undefined>)[key]?.() ?? '';
	const show = (name: string) => sections.includes(name);

	function suggest() {
		const match = draft.url.match(/t\.me\/([A-Za-z0-9_]+)/);
		const name = match?.[1] ?? '';
		if (!name && !draft.url.startsWith('https://')) return;
		draft.en.title ||= name ? `@${name}` : 'Your project';
		draft.en.body ||= localeState.value === 'de' ? 'Neue Beiträge – direkt aus dem Kanal.' : 'Fresh updates, straight from the source.';
		draft.en.cta ||= 'Open';
	}
	const PLACEMENTS = ['rewarded', 'banner', 'chat'];
	const CATEGORIES = ['news', 'military', 'politics', 'gaming', 'tech', 'humor', 'community', 'education'];
</script>

<div class="form-grid">
	{#if show('link')}
		<label class="wide">{s('link')}<input type="url" bind:value={draft.url} /></label>
		<label>{s('emoji')}<input bind:value={draft.emoji} maxlength="8" /></label>
		<label class="wide">{s('videoField')}<input type="url" bind:value={draft.video} placeholder="https://t.me/channel/123" /><small>{s('videoHint')}</small></label>
		<label class="wide">{s('taskField')}<input bind:value={draft.taskChat} placeholder="@channel" /><small>{s('taskHint')}</small></label>
		<button type="button" class="suggest" onclick={suggest}>✨ {s('suggest')}</button>
	{/if}

	{#if show('texts')}
		<fieldset class="wide">
			<legend>{s('englishText')}</legend>
			<label>{s('titleLabel')}<input bind:value={draft.en.title} maxlength="60" /></label>
			<label>{s('bodyLabel')}<input bind:value={draft.en.body} maxlength="200" /></label>
			<label>{s('buttonLabel')}<input bind:value={draft.en.cta} maxlength="30" /></label>
		</fieldset>
		<fieldset class="wide">
			<legend>{s('abVariant')}</legend>
			<label>{s('titleLabel')}<input bind:value={draft.ab.title} maxlength="60" /></label>
			<label>{s('bodyLabel')}<input bind:value={draft.ab.body} maxlength="200" /></label>
			<label>{s('buttonLabel')}<input bind:value={draft.ab.cta} maxlength="30" /></label>
		</fieldset>
		<fieldset class="wide">
			<legend>{s('germanText')}</legend>
			<label>{s('titleLabel')}<input bind:value={draft.de.title} maxlength="60" /></label>
			<label>{s('bodyLabel')}<input bind:value={draft.de.body} maxlength="200" /></label>
			<label>{s('buttonLabel')}<input bind:value={draft.de.cta} maxlength="30" /></label>
		</fieldset>
	{/if}

	{#if show('look')}
		<fieldset class="wide">
			<legend>{s('look')}</legend>
			<label>{s('variant')}<select bind:value={draft.variant}><option value="card">card</option><option value="banner">banner</option><option value="poster">poster</option></select></label>
			<label>{s('background')}<input type="color" bind:value={draft.background} /></label>
			<label>{s('textColor')}<input type="color" bind:value={draft.color} /></label>
			<label>{s('accent')}<input type="color" bind:value={draft.accent} /></label>
		</fieldset>
		<fieldset>
			<legend>{s('placements')}</legend>
			{#each PLACEMENTS as item}<label class="check"><input type="checkbox" value={item} bind:group={draft.placements} /> {item}</label>{/each}
		</fieldset>
		<fieldset>
			<legend>{s('categories')}</legend>
			{#each CATEGORIES as item}<label class="check"><input type="checkbox" value={item} bind:group={draft.categories} /> {item}</label>{/each}
		</fieldset>
	{/if}

	{#if show('settings')}
		<label>{s('weightLabel')}<input type="number" min="0" max="1000" bind:value={draft.weight} /></label>
		<label>{s('start')}<input type="date" bind:value={draft.start} /></label>
		<label>{s('end')}<input type="date" bind:value={draft.end} /></label>
		<label class="check"><input type="checkbox" bind:checked={draft.paused} /> {s('startPaused')}</label>
		<label class="check wide"><input type="checkbox" bind:checked={draft.paid} /> {s('paidCampaign')}</label>
		<p class="hint wide">{draft.paid ? s('paidHint') : s('freeHint')}</p>
	{/if}
</div>
