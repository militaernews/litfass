<script lang="ts">
	import { page } from '$app/state';

	const status = $derived(page.status ?? 404);
	const notFound = $derived(status === 404);
	const broken = $derived(status >= 500);
	const title = $derived(notFound ? 'This page went missing' : broken ? 'Something broke' : 'Something went wrong');
	const body = $derived(
		notFound
			? 'The link may be old, or the page may have moved. The posters are still here.'
			: broken
				? 'The server had a bad moment. Try again in a little while.'
				: `The page could not be loaded (${status}).`
	);
</script>

<svelte:head>
	<title>{status} · litfass</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<main class="error-shell">
	<section class="error-card">
		<span class="error-icon" aria-hidden="true">{notFound ? '🪧' : '📰'}</span>
		<p class="error-code">{status}</p>
		<h1>{title}</h1>
		<p class="error-body">{body}</p>
		<div class="error-actions">
			<a class="button" href="/">Back to litfass</a>
			<a class="button secondary" href="https://militaernews.vercel.app">Militär News</a>
			{#if !notFound}<button onclick={() => location.reload()}>Try again</button>{/if}
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
</style>
