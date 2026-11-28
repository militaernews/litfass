<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import IconArrowLeft from '~icons/lucide/arrow-left';
	import IconCheck from '~icons/lucide/check';
	import IconTrash2 from '~icons/lucide/trash-2';
	import AdFields from './AdFields.svelte';
	import AdCard from './AdCard.svelte';
	import { call } from './api';
	import { asAd, fromAd, toPayload, type Draft } from './adForm';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';
	import type { Ad } from '@militaernews/litfass';

	const s = (key: string, values: Record<string, string> = {}) => {
		const fn = (m as unknown as Record<string, ((v?: Record<string, string>) => string) | undefined>)[key];
		let text = fn?.(values) ?? '';
		for (const [name, value] of Object.entries(values)) text = text.replace(`{${name}}`, value);
		return text;
	};
	const id = $derived(typeof window === 'undefined' ? '' : (new URLSearchParams(window.location.search).get('id') ?? ''));

	let draft = $state<Draft | null>(null);
	let error = $state('');
	let notice = $state('');
	let busy = $state(false);

	onMount(async () => {
		try {
			await call('me');
			const result = await call<{ ad: Ad }>('get_ad', { id });
			draft = fromAd(result.ad as Ad & { paused?: boolean; paid?: boolean; task?: { type: 'join'; chat: string } });
		} catch (cause) {
			if (cause instanceof Error && /unauthorized/i.test(cause.message)) await goto('/login', { replaceState: true });
			else error = cause instanceof Error ? cause.message : s('adNotFound');
		}
	});

	async function save() {
		if (!draft) return;
		busy = true;
		error = '';
		try {
			await call('update_ad', toPayload(draft, id));
			notice = s('updatedAdvert');
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Could not save';
		} finally {
			busy = false;
		}
	}

	async function remove() {
		if (!confirm(s('deleteConfirm', { title: draft?.en.title ?? id }))) return;
		busy = true;
		try {
			await call('delete_ad', { id });
			await goto('/manage');
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Could not delete';
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head><title>{s('editAdvertPage')} · litfass</title></svelte:head>

{#key localeState.value}
	<main class="manager editor-page">
		<button class="back" onclick={() => goto('/manage')}><IconArrowLeft /> {s('backToManager')}</button>
		<header class="editor-head">
			<h1>{s('editAdvertPage')}</h1>
			<p><code>{id}</code></p>
		</header>

		{#if draft}
			<section class="editor-card">
				<AdFields {draft} />
				<div class="preview-wrap"><h3>{s('preview')}</h3><AdCard ad={asAd(draft, id)} lang={localeState.value} /></div>
				{#if error}<p class="alert" role="alert">{error}</p>{/if}
				{#if notice}<p class="ok" role="status">{notice}</p>{/if}
				<div class="editor-nav">
					<button class="danger" disabled={busy} onclick={remove}><IconTrash2 /> {s('delete')}</button>
					<button class="primary" disabled={busy} onclick={save}><IconCheck /> {busy ? s('saving') : s('saveAdvert')}</button>
				</div>
			</section>
		{:else if error}
			<p class="alert" role="alert">{error}</p>
		{:else}
			<p class="empty">…</p>
		{/if}
	</main>
{/key}
