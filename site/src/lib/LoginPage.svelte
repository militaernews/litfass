<script lang="ts">
	import { goto } from '$app/navigation';
	import IconArrowLeft from '~icons/lucide/arrow-left';
	import IconShieldCheck from '~icons/lucide/shield-check';
	import IconExternalLink from '~icons/lucide/external-link';
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
			<img src="/logo.png" alt="litfass" width="76" height="76" />
			<p class="eyebrow">{s('loginEyebrow')}</p>
			<h1>{s('welcome')}</h1>
			<p class="lead">{s('signInContinue')}</p>

			<a class="tg" href={botLink} target="_blank" rel="noreferrer">
				<IconTelegram /> <span>{s('signUp')}</span>
			</a>
			<p class="hint">{s('loginHint')}</p>

			<a class="secondary" href="https://t.me/litfass_advertisement_bot" target="_blank" rel="noreferrer">
				{s('openInTelegram')} <IconExternalLink />
			</a>

			<p class="privacy"><IconShieldCheck /> {s('privacyNote')}</p>
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

			<a class="back" href="/"><IconArrowLeft /> {s('back')}</a>
		</section>
	</main>
{/key}

<style>
	.login-shell {
		min-height: 100svh;
		display: grid;
		place-items: center;
		padding: 90px 16px 32px;
		background: radial-gradient(ellipse 70% 40% at 50% 0%, var(--bg-2), transparent), var(--bg);
	}
	.login-card {
		width: min(100%, 26rem);
		padding: clamp(28px, 6vw, 44px);
		border: 1px solid var(--line);
		border-radius: 24px;
		background: var(--card);
		box-shadow: 0 30px 80px #0002;
		text-align: center;
	}
	.login-card > img { width: 76px; height: 76px; border-radius: 50%; box-shadow: 0 12px 30px #0002; }
	.eyebrow { margin: 20px 0 0; color: var(--red); font-size: 0.75rem; font-weight: 800; letter-spacing: 0.18em; text-transform: uppercase; }
	h1 { margin: 6px 0; font-size: clamp(2rem, 8vw, 2.8rem); letter-spacing: -0.05em; color: var(--green); }
	.lead { margin: 0 0 26px; color: var(--muted); }
	.tg {
		display: flex; align-items: center; justify-content: center; gap: 12px;
		padding: 0.9rem 1.4rem; border-radius: 14px; background: #229ed9; color: #fff;
		font-weight: 800; text-decoration: none; box-shadow: 0 12px 30px #229ed944;
		transition: transform .18s ease, background .18s ease;
	}
	.tg:hover { transform: translateY(-2px); background: #1d8ec4; }
	.tg :global(svg) { width: 24px; height: 24px; }
	.hint { margin: 10px 0 18px; color: var(--muted); font-size: 0.8rem; }
	.secondary { display: inline-flex; align-items: center; gap: 8px; color: var(--red); font-size: 0.9rem; font-weight: 700; }
	.secondary :global(svg) { width: 14px; height: 14px; }
	.privacy { display: flex; align-items: center; justify-content: center; gap: 8px; margin: 24px 0 0; color: var(--muted); font-size: 0.78rem; }
	.privacy :global(svg) { width: 15px; height: 15px; color: var(--red); }
	.alert { margin: 16px 0 0; padding: 10px 14px; border-radius: 10px; background: #ffe3e0; color: #8a1c13; }
	.dev-panel { display: grid; gap: 8px; margin-top: 22px; padding-top: 22px; border-top: 1px solid var(--line); text-align: start; }
	.dev-panel label { display: grid; gap: 5px; font-size: 0.85rem; font-weight: 600; }
	.dev-panel input { width: 100%; font: inherit; padding: 0.5rem 0.65rem; border: 1px solid var(--line); border-radius: 9px; background: var(--bg); color: var(--ink); }
	.back { display: inline-flex; align-items: center; gap: 7px; margin-top: 24px; color: var(--muted); font-size: 0.85rem; text-decoration: none; }
	.back :global(svg) { width: 15px; height: 15px; }
</style>
