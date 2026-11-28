<script lang="ts">
	import { goto } from '$app/navigation';
	import IconArrowRight from '~icons/lucide/arrow-right';
	import IconTelegram from '~icons/logos/telegram';
	import { call, setDevInitData } from './api';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';
	import { isTelegramLaunch } from './telegram';

	const s = (key: string) => (m as unknown as Record<string, (() => string) | undefined>)[key]?.() ?? '';
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
			<img src="/icon.png" alt="litfass" width="72" height="72" />
			<p class="eyebrow">{s('loginEyebrow')}</p>
			<h1>{s('welcome')}</h1>
			<p class="lead">{s('signInContinue')}</p>

			<a class="tg" href={botLink} target="_blank" rel="noreferrer">
				<IconTelegram /> <span>{s('signUp')}</span> <IconArrowRight />
			</a>

			{#if error}<p class="alert" role="alert">{error}</p>{/if}

			<p class="support">
				<a href="https://t.me/MilitaernewsKontakt" target="_blank" rel="noreferrer">{s('support')}</a>
			</p>

			{#if import.meta.env.DEV && !isTelegramLaunch(typeof window === 'undefined' ? '' : window.location.hash)}
				<details class="dev-panel">
					<summary>{s('devInitData')}</summary>
					<input bind:value={devKey} placeholder="user=…&auth_date=…&hash=…" />
					<button disabled={busy} onclick={useDevKey}>{busy ? s('connecting') : s('connect')}</button>
				</details>
			{/if}
		</section>
	</main>
{/key}

<style>
	.login-shell {
		min-height: 100svh;
		display: grid;
		place-items: center;
		padding: 80px 16px calc(24px + env(safe-area-inset-bottom));
		background: radial-gradient(ellipse 70% 40% at 50% 0%, var(--bg-2), transparent), var(--bg);
	}
	.login-card {
		width: min(100%, 24rem);
		padding: clamp(26px, 6vw, 40px);
		border: 1px solid var(--line);
		border-radius: 22px;
		background: var(--card);
		box-shadow: 0 20px 60px #0002;
		text-align: center;
	}
	img {
		width: 72px;
		height: 72px;
		border-radius: 18px;
	}
	.eyebrow {
		margin: 18px 0 0;
		color: var(--red);
		font-size: 0.75rem;
		font-weight: 800;
		letter-spacing: 0.18em;
		text-transform: uppercase;
	}
	h1 {
		margin: 6px 0;
		color: var(--green);
		font-size: clamp(1.8rem, 8vw, 2.4rem);
		letter-spacing: -0.05em;
	}
	.lead {
		margin: 0 0 24px;
		color: var(--muted);
	}
	.tg {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 10px;
		width: 100%;
		padding: 0.9rem 1.2rem;
		border-radius: 14px;
		background: #229ed9;
		color: #fff;
		font-weight: 800;
		text-decoration: none;
		box-shadow: 0 12px 30px #229ed944;
		transition: transform 0.18s ease, background 0.18s ease;
	}
	.tg:hover {
		transform: translateY(-2px);
		background: #1d8ec4;
	}
	.tg :global(svg) {
		width: 20px;
		height: 20px;
	}
	.alert {
		margin: 14px 0 0;
		padding: 10px 14px;
		border-radius: 10px;
		background: #ffe3e0;
		color: #8a1c13;
	}
	.support {
		margin: 18px 0 0;
		font-size: 0.8rem;
	}
	.dev-panel {
		display: grid;
		gap: 8px;
		margin-top: 20px;
		padding-top: 16px;
		border-top: 1px solid var(--line);
		text-align: start;
		font-size: 0.8rem;
	}
	.dev-panel input {
		width: 100%;
		font: inherit;
		padding: 0.5rem 0.65rem;
		border: 1px solid var(--line);
		border-radius: 9px;
		background: var(--bg);
		color: var(--ink);
	}
</style>
