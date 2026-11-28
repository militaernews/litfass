<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { injectAdStyles, renderAd, type Ad, type AdStyle } from '@militaernews/litfass';
	import { call, setDevInitData } from '../../lib/api';
	import { getTelegramUser, isTelegramLaunch, type TelegramUser } from '../../lib/telegram';

	interface Events {
		view: number;
		click: number;
		reward: number;
	}
	interface Stats {
		totals: { 7: Events; 30: Events };
		days: Array<{ day: string } & Events>;
		ads: Array<{ id: string; title: string | null } & Events>;
	}
	interface ManagedAd extends Ad {
		paused?: boolean;
		created_by?: number;
	}
	interface Me {
		user: TelegramUser;
		admin: boolean;
	}
	interface Draft {
		url: string;
		emoji: string;
		weight: number;
		start: string;
		end: string;
		paused: boolean;
		placements: string[];
		categories: string[];
		variant: 'card' | 'banner' | 'poster';
		background: string;
		color: string;
		accent: string;
		en: { title: string; body: string; cta: string };
		de: { title: string; body: string; cta: string };
	}

	const PLACEMENTS = ['rewarded', 'banner', 'chat'];
	const CATEGORIES = ['news', 'military', 'politics', 'gaming', 'tech', 'humor', 'community', 'education'];
	const emptyDraft = (): Draft => ({
		url: 'https://t.me/',
		emoji: '📰',
		weight: 1,
		start: '',
		end: '',
		paused: true,
		placements: [],
		categories: [],
		variant: 'card',
		background: '#0c3a6b',
		color: '#e6f6ff',
		accent: '#2ec5ff',
		en: { title: '', body: '', cta: '' },
		de: { title: '', body: '', cta: '' }
	});

	let me = $state<Me | null>(null);
	let ads = $state<ManagedAd[]>([]);
	let publishers = $state<Array<{ id: number; name: string; key: string; kind: string; blocked: boolean }>>([]);
	let stats = $state<Stats | null>(null);
	let tab = $state<'ads' | 'placements' | 'stats'>('ads');
	let draft = $state<Draft>(emptyDraft());
	let editingId = $state<string | null>(null);
	let formOpen = $state(false);
	let devKey = $state('');
	let error = $state('');
	let notice = $state('');
	let busy = $state(false);
	let preview: HTMLDivElement | undefined = $state();

	const asAd = (d: Draft): Ad => ({
		id: editingId ?? 'preview',
		url: d.url,
		emoji: d.emoji || undefined,
		weight: d.weight,
		start: d.start || undefined,
		end: d.end || undefined,
		text: { en: d.en, ...(d.de.title ? { de: d.de } : {}) },
		style: { variant: d.variant, background: d.background, color: d.color, accent: d.accent } satisfies AdStyle
	});

	async function reload() {
		const [identity, adverts, placements, overview] = await Promise.all([
			call<Me>('me'),
			call<{ ads: ManagedAd[] }>('list_ads'),
			call<{ publishers: typeof publishers }>('publishers'),
			call<{ stats: Stats }>('stats')
		]);
		me = identity;
		ads = adverts.ads;
		publishers = placements.publishers;
		stats = overview.stats;
	}

	onMount(async () => {
		injectAdStyles();
		if (import.meta.env.DEV && !isTelegramLaunch(window.location.hash)) {
			const saved = localStorage.getItem('litfass-dev-init-data');
			if (saved) setDevInitData(saved);
		}
		const user = await getTelegramUser();
		if (user?.first_name) me = { user, admin: false };
		try {
			await reload();
		} catch (cause) {
			if (cause instanceof Error && /unauthorized/i.test(cause.message)) {
				await goto('/login', { replaceState: true });
				return;
			}
			error = cause instanceof Error ? cause.message : 'Could not load the dashboard';
		}
	});

	$effect(() => {
		if (!preview || !formOpen) return;
		preview.replaceChildren(renderAd(asAd(draft), { lang: 'en', label: 'Anzeige' }));
	});

	function openCreate() {
		editingId = null;
		draft = emptyDraft();
		formOpen = true;
		error = '';
	}

	function openEdit(ad: ManagedAd) {
		editingId = ad.id;
		draft = {
			...emptyDraft(),
			url: ad.url,
			emoji: ad.emoji ?? '',
			weight: ad.weight ?? 1,
			start: ad.start ?? '',
			end: ad.end ?? '',
			paused: Boolean(ad.paused),
			placements: [...(ad.placements ?? [])],
			categories: [...(ad.categories ?? [])],
			variant: ad.style?.variant ?? 'card',
			background: ad.style?.background ?? '#0c3a6b',
			color: ad.style?.color ?? '#e6f6ff',
			accent: ad.style?.accent ?? '#2ec5ff',
			en: ad.text.en ?? { title: '', body: '', cta: '' },
			de: ad.text.de ?? { title: '', body: '', cta: '' }
		};
		formOpen = true;
		error = '';
	}

	async function save() {
		busy = true;
		error = '';
		try {
			await call(editingId ? 'update_ad' : 'create_ad', {
				...(editingId ? { id: editingId } : {}),
				url: draft.url,
				emoji: draft.emoji || null,
				weight: Number(draft.weight),
				start: draft.start || null,
				end: draft.end || null,
				paused: draft.paused,
				placements: draft.placements,
				categories: draft.categories,
				style: { variant: draft.variant, background: draft.background, color: draft.color, accent: draft.accent },
				text: { en: draft.en, ...(draft.de.title ? { de: draft.de } : {}) }
			});
			formOpen = false;
			notice = editingId ? 'Advert updated.' : 'Advert created — it starts paused.';
			await reload();
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Could not save';
		} finally {
			busy = false;
		}
	}

	async function remove(ad: ManagedAd) {
		if (!confirm(`Delete “${ad.text.en?.title ?? ad.id}”?`)) return;
		busy = true;
		try {
			await call('delete_ad', { id: ad.id });
			notice = 'Advert deleted.';
			await reload();
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Could not delete';
		} finally {
			busy = false;
		}
	}

	function useDevKey() {
		setDevInitData(devKey);
		localStorage.setItem('litfass-dev-init-data', devKey.trim());
		reload().catch((cause) => (error = String(cause)));
	}

	const ctr = (events: Events) => (events.view ? `${((events.click / events.view) * 100).toFixed(1)}%` : '–');
	const title = (ad: { text?: Record<string, { title: string }> }, id: string) => ad.text?.en?.title ?? id;
	const maxViews = $derived(Math.max(1, ...(stats?.days.map((day) => day.view) ?? [])));
</script>

<svelte:head>
	<title>Manage adverts · litfass</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="manager">
	<header class="manager-head">
		<a class="brand" href="/">litfass</a>
		<div>
			<h1>Advert manager</h1>
			<p>
				{#if me}
					Signed in as {me.user.first_name ?? me.user.id}{#if me.admin} <span class="badge">admin</span>{/if}
				{:else}
					Open this page from @litfass_advertisement_bot
				{/if}
			</p>
		</div>
	</header>

	{#if error}<p class="alert" role="alert">{error}</p>{/if}
	{#if notice}<p class="ok" role="status">{notice}</p>{/if}

	{#if import.meta.env.DEV && !me}
		<div class="dev-panel">
			<label>
				Dev initData
				<input bind:value={devKey} placeholder="user=…&auth_date=…&hash=…" />
			</label>
			<button onclick={useDevKey}>Connect</button>
		</div>
	{/if}

	<nav class="tabs" aria-label="Manager sections">
		<button class:active={tab === 'ads'} onclick={() => (tab = 'ads')}>Adverts</button>
		<button class:active={tab === 'placements'} onclick={() => (tab = 'placements')}>Placements</button>
		<button class:active={tab === 'stats'} onclick={() => (tab = 'stats')}>Statistics</button>
	</nav>

	{#if tab === 'ads'}
		<div class="toolbar">
			<p>Adverts your placement can show. New ones start paused.</p>
			{#if me?.admin}<button class="primary" onclick={openCreate}>+ New advert</button>{/if}
		</div>
		{#if ads.length === 0}
			<p class="empty">No adverts yet.</p>
		{:else}
			<ul class="ad-list">
				{#each ads as ad (ad.id)}
					<li>
						<div class="ad-main">
							<span class="emoji">{ad.emoji ?? '📰'}</span>
							<div>
								<strong>{title(ad, ad.id)}</strong>
								<a href={ad.url} target="_blank" rel="noreferrer">{ad.url}</a>
								<div class="chips">
									<span class:live={!ad.paused} class="badge">{ad.paused ? 'paused' : 'live'}</span>
									<span class="badge">weight {ad.weight ?? 1}</span>
									{#each ad.categories ?? [] as category}<span class="badge">{category}</span>{/each}
								</div>
							</div>
						</div>
						{#if me?.admin}
							<div class="row-actions">
								<button onclick={() => openEdit(ad)}>Edit</button>
								<button class="danger" disabled={busy} onclick={() => remove(ad)}>Delete</button>
							</div>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	{:else if tab === 'placements'}
		{#if publishers.length === 0}
			<p class="empty">No placements yet. Register one in the bot with /register.</p>
		{:else}
			<ul class="ad-list">
				{#each publishers as publisher (publisher.id)}
					<li>
						<div>
							<strong>{publisher.name}</strong>
							<div class="chips">
								<span class="badge">{publisher.kind}</span>
								{#if publisher.blocked}<span class="badge">blocked</span>{/if}
							</div>
							<code class="key">{publisher.key}</code>
						</div>
						<button onclick={() => navigator.clipboard.writeText(publisher.key)}>Copy key</button>
					</li>
				{/each}
			</ul>
		{/if}
	{:else}
		{#if stats}
			<div class="stat-grid">
				<div class="stat"><span>Views · 7 days</span><strong>{stats.totals['7'].view.toLocaleString()}</strong></div>
				<div class="stat"><span>Clicks · 7 days</span><strong>{stats.totals['7'].click.toLocaleString()}</strong></div>
				<div class="stat"><span>Rewarded views</span><strong>{stats.totals['7'].reward.toLocaleString()}</strong></div>
				<div class="stat"><span>Click rate</span><strong>{ctr(stats.totals['7'])}</strong></div>
			</div>
			<h2>Last 30 days</h2>
			<div class="chart">
				{#each stats.days as day (day.day)}
					<div class="bar" title={`${day.day}: ${day.view} views`}>
						<div style={`height: ${Math.max(2, (day.view / maxViews) * 100)}%`}></div>
					</div>
				{/each}
			</div>
			<h2>Per advert</h2>
			<ul class="ad-list">
				{#each stats.ads as ad (ad.id)}
					<li>
						<strong>{ad.title ?? ad.id}</strong>
						<span>{ad.view.toLocaleString()} views · {ad.click.toLocaleString()} clicks · {ad.reward.toLocaleString()} rewarded</span>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="empty">No statistics yet.</p>
		{/if}
	{/if}
</div>

{#if formOpen}
	<div class="modal" role="dialog" aria-modal="true" aria-label="Advert editor">
		<div class="sheet">
			<header>
				<h2>{editingId ? 'Edit advert' : 'New advert'}</h2>
				<button onclick={() => (formOpen = false)} aria-label="Close">×</button>
			</header>
			<div class="form-grid">
				<label class="wide">Link<input type="url" bind:value={draft.url} /></label>
				<label>Emoji<input bind:value={draft.emoji} maxlength="8" /></label>
				<label>Weight<input type="number" min="0" max="1000" bind:value={draft.weight} /></label>
				<label>Start<input type="date" bind:value={draft.start} /></label>
				<label>End<input type="date" bind:value={draft.end} /></label>
				<label class="check"><input type="checkbox" bind:checked={draft.paused} /> Start paused</label>
				<fieldset>
					<legend>Placements</legend>
					{#each PLACEMENTS as item}<label class="check"><input type="checkbox" value={item} bind:group={draft.placements} /> {item}</label>{/each}
				</fieldset>
				<fieldset>
					<legend>Categories</legend>
					{#each CATEGORIES as item}<label class="check"><input type="checkbox" value={item} bind:group={draft.categories} /> {item}</label>{/each}
				</fieldset>
				<fieldset class="wide">
					<legend>Look</legend>
					<label>Variant<select bind:value={draft.variant}><option value="card">card</option><option value="banner">banner</option><option value="poster">poster</option></select></label>
					<label>Background<input type="color" bind:value={draft.background} /></label>
					<label>Text<input type="color" bind:value={draft.color} /></label>
					<label>Accent<input type="color" bind:value={draft.accent} /></label>
				</fieldset>
				{#each ['en', 'de'] as lang}
					<fieldset class="wide">
						<legend>{lang === 'en' ? 'English' : 'German'} text {lang === 'de' ? '(optional)' : ''}</legend>
						<label>Title<input bind:value={draft[lang as 'en' | 'de'].title} maxlength="60" /></label>
						<label>Body<input bind:value={draft[lang as 'en' | 'de'].body} maxlength="200" /></label>
						<label>Button<input bind:value={draft[lang as 'en' | 'de'].cta} maxlength="30" /></label>
					</fieldset>
				{/each}
			</div>
			<div class="preview-wrap">
				<h3>Preview</h3>
				<div class="preview" bind:this={preview}></div>
			</div>
			{#if error}<p class="alert" role="alert">{error}</p>{/if}
			<footer>
				<button onclick={() => (formOpen = false)}>Cancel</button>
				<button class="primary" disabled={busy} onclick={save}>{busy ? 'Saving…' : 'Save advert'}</button>
			</footer>
		</div>
	</div>
{/if}
