<script lang="ts">
	import { goto } from '$app/navigation';
	import { call, setDevInitData } from './api';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';
	import { isTelegramLaunch } from './telegram';

	const s = (key: string, values?: Record<string, string>) => (m as unknown as Record<string, ((v?: Record<string, string>) => string) | undefined>)[key]?.(values) ?? '';

	const botLink = 'https://t.me/litfass_advertisement_bot?startapp=manage';
	let devKey = $state('');
	let error = $state('');
	let busy = $state(false);

	async function connect() {
		busy = true;
		error = '';
		try {
			await call('me');
			await goto('/manage');
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Could not sign in';
		} finally {
			busy = false;
		}
	}

	function useDevKey() {
		setDevInitData(devKey);
		localStorage.setItem('litfass-dev-init-data', devKey.trim());
		connect();
	}
</script>

<svelte:head>
	<title>{s('loginTitle')} · litfass</title>
	<meta name="robots" content="noindex" />
</svelte:head>
{#key localeState.value}

<main class="login-shell">
	<section class="login-card">
		<span class="icon" aria-hidden="true">📰</span>
		<p class="eyebrow">{s('loginEyebrow')}</p>
		<h1>{s('loginTitle')}</h1>
		<p class="lead">{s('loginLead')}</p>

		<a class="button" href={botLink}>{s('loginButton')}</a>
		<p class="hint">{s('loginHint')}</p>

		{#if error}<p class="alert" role="alert">{error}</p>{/if}

		{#if import.meta.env.DEV && !isTelegramLaunch(typeof window === 'undefined' ? '' : window.location.hash)}
			<div class="dev-panel">
				<label>
					{s('devInitData')}
					<input bind:value={devKey} placeholder="user=…&auth_date=…&hash=…" />
				</label>
				<button disabled={busy} onclick={useDevKey}>{busy ? s('connecting') : s('connect')}</button>
			</div>
		{/if}

		<a class="back" href={'/'}>{s('back')}</a>
	</section>
</main>

<style>
	.login-shell {
		min-height: 100svh;
		display: grid;
		place-items: center;
		padding: 1.5rem;
		background: radial-gradient(circle at 50% 15%, var(--bg-2), var(--bg) 60%);
	}
	.login-card {
		width: min(100%, 30rem);
		padding: clamp(1.8rem, 7vw, 3rem);
		border: 1px solid var(--bg-2);
		border-radius: 22px;
		background: var(--card);
		box-shadow: 0 20px 60px #0002;
		text-align: center;
	}
	.icon {
		display: block;
		font-size: 3.5rem;
		line-height: 1;
	}
	.eyebrow {
		margin: 0.9rem 0 0;
		color: var(--red);
		font-size: 0.8rem;
		font-weight: 800;
		letter-spacing: 0.2em;
		text-transform: uppercase;
	}
	h1 {
		margin: 0.4rem 0 0.8rem;
		color: var(--green);
		font-size: clamp(1.8rem, 7vw, 2.6rem);
		letter-spacing: -0.04em;
		line-height: 1.05;
	}
	.lead {
		margin: 0 auto 1.6rem;
		max-width: 24rem;
		color: var(--muted);
	}
	.button {
		display: inline-block;
		padding: 0.7rem 1.3rem;
		border-radius: 999px;
		background: var(--green);
		color: var(--bg);
		font-weight: 700;
		text-decoration: none;
	}
	.hint {
		margin: 0.8rem 0 0;
		color: var(--muted);
		font-size: 0.85rem;
	}
	.alert {
		margin: 1rem 0 0;
		border-radius: 10px;
		padding: 10px 14px;
		background: #ffe3e0;
		color: #8a1c13;
	}
	.dev-panel {
		display: grid;
		gap: 8px;
		margin-top: 1.5rem;
		padding-top: 1.5rem;
		border-top: 1px solid var(--bg-2);
		text-align: start;
	}
	.dev-panel label {
		display: grid;
		gap: 5px;
		font-size: 0.85rem;
		font-weight: 600;
	}
	.dev-panel input {
		width: 100%;
		font: inherit;
		padding: 0.5rem 0.65rem;
		border: 1px solid var(--bg-2);
		border-radius: 9px;
		background: var(--bg);
		color: var(--ink);
	}
	.back {
		display: inline-block;
		margin-top: 1.5rem;
		color: var(--muted);
		font-size: 0.85rem;
		text-decoration: none;
	}
</style>
{/key}
