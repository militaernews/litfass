<script lang="ts">
	import { page } from '$app/state';
	import IconHouse from '~icons/lucide/house';
	import IconArrowLeft from '~icons/lucide/arrow-left';
	import IconRefreshCw from '~icons/lucide/refresh-cw';
	import IconSend from '~icons/logos/telegram';
	import { m } from '../lib/paraglide/messages.js';
	import { localeState } from '../lib/locale.svelte';

	const status = $derived(page.status ?? 404);
	const notFound = $derived(status === 404);
	const unauthorized = $derived(status === 401);
	const broken = $derived(status >= 500);
	const s = (key: string, values?: Record<string, string>) => (m as unknown as Record<string, ((v?: Record<string, string>) => string) | undefined>)[key]?.(values) ?? '';
	const title = $derived(
		notFound ? s('error404Title') : unauthorized ? s('error401Title') : broken ? s('error500Title') : s('errorGenericTitle')
	);
	const body = $derived(
		notFound
			? s('error404Body')
			: unauthorized
				? s('error401Body')
				: broken
					? s('error500Body')
					: s('errorGenericBody', { status: String(status) })
	);
</script>

<svelte:head>
	<title>{status} · litfass</title>
	<meta name="robots" content="noindex" />
</svelte:head>
{#key localeState.value}

<main class="error-shell">
	<section class="error-card">
		<span class="error-icon" aria-hidden="true">{#if unauthorized}<IconSend />{:else if notFound}<IconHouse />{:else}<IconRefreshCw />{/if}</span>
		<p class="error-code">{status}</p>
		<h1>{title}</h1>
		<p class="error-body">{body}</p>
		<div class="error-actions">
			{#if unauthorized}
				<a class="button" href="/login"><IconSend /> {s('signIn')}</a>
			{:else}
				<a class="button" href="/"><IconArrowLeft /> {s('backHome')}</a>
			{/if}
			<a class="button secondary" href="https://militaernews.vercel.app">{s('militaerNews')}</a>
			{#if !notFound && !unauthorized}<button onclick={() => location.reload()}><IconRefreshCw /> {s('tryAgain')}</button>{/if}
		</div>
	</section>
</main>

<style>
	.error-shell {
		min-height: 100svh;
		display: grid;
		place-items: center;
		padding: 1.5rem;
		background: radial-gradient(circle at 50% 15%, var(--bg-2), var(--bg) 60%);
	}
	.error-card {
		width: min(100%, 30rem);
		padding: clamp(1.8rem, 7vw, 3rem);
		border: 1px solid var(--bg-2);
		border-radius: 22px;
		background: var(--card);
		box-shadow: 0 20px 60px #0002;
		text-align: center;
	}
	.error-icon {
		display: block;
		font-size: 3.5rem;
		line-height: 1;
	}
	.error-code {
		margin: 0.9rem 0 0;
		color: var(--red);
		font-size: 0.8rem;
		font-weight: 800;
		letter-spacing: 0.2em;
	}
	h1 {
		margin: 0.4rem 0 0.8rem;
		color: var(--green);
		font-size: clamp(1.8rem, 7vw, 2.6rem);
		letter-spacing: -0.04em;
		line-height: 1.05;
	}
	.error-body {
		margin: 0 auto 1.6rem;
		max-width: 24rem;
		color: var(--muted);
	}
	.error-actions {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 10px;
	}
	.error-icon :global(svg) { width: 54px; height: 54px; }
	.error-actions a, .error-actions button { display: inline-flex; align-items: center; gap: 8px; }
	.error-actions :global(svg) { width: 16px; height: 16px; }
</style>
{/key}
