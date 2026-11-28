<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import IconPlus from '~icons/lucide/plus';
	import IconPencil from '~icons/lucide/pencil';
	import IconTrash2 from '~icons/lucide/trash-2';
	import IconCopy from '~icons/lucide/copy';
	import IconEye from '~icons/lucide/eye';
	import IconMousePointerClick from '~icons/lucide/mouse-pointer-click';
	import IconGift from '~icons/lucide/gift';
	import IconChart from '~icons/lucide/chart-no-axes-column-increasing';
	import IconLayoutGrid from '~icons/lucide/layout-grid';
	import IconMapPin from '~icons/lucide/map-pinned';
	import IconSettings2 from '~icons/lucide/settings-2';
	import IconX from '~icons/lucide/x';
	import { injectAdStyles, renderAd, type Ad, type AdStyle } from '@militaernews/litfass';
	import { call, setDevInitData } from './api';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';
	import { getTelegramUser, isTelegramLaunch, type TelegramUser } from './telegram';

	const s = (key: string, values?: Record<string, string>) => (m as unknown as Record<string, ((v?: Record<string, string>) => string) | undefined>)[key]?.(values) ?? '';

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
		preview.replaceChildren(renderAd(asAd(draft), { lang: localeState.value, label: 'Anzeige' }));
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
			notice = s(editingId ? 'updated' : 'created');
			await reload();
		} catch (cause) {
			error = cause instanceof Error ? cause.message : 'Could not save';
		} finally {
			busy = false;
		}
	}

	async function remove(ad: ManagedAd) {
		if (!confirm(s('deleteConfirm', { title: ad.text[localeState.value]?.title ?? ad.text.en?.title ?? ad.id }))) return;
		busy = true;
		try {
			await call('delete_ad', { id: ad.id });
			notice = s('deleted');
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
	const title = (ad: { text?: Record<string, { title: string }> }, id: string) => ad.text?.[localeState.value]?.title ?? ad.text?.en?.title ?? id;
	const maxViews = $derived(Math.max(1, ...(stats?.days.map((day) => day.view) ?? [])));
</script>

<svelte:head>
	<title>{s('managerTitle')} · litfass</title>
	<meta name="robots" content="noindex" />
</svelte:head>
{#key localeState.value}

<div class="manager">
	<header class="manager-head">
		<a class="brand" href={'/'}>litfass</a>
		<div>
			<h1>{s('managerTitle')}</h1>
			<p>
				{#if me}
					{s('signedInAs')} {me.user.first_name ?? me.user.id}{#if me.admin} <span class="badge">{s('admin')}</span>{/if}
				{:else}
					{s('openFromBot')}
				{/if}
			</p>
		</div>
	</header>

	{#if error}<p class="alert" role="alert">{error}</p>{/if}
	{#if notice}<p class="ok" role="status">{notice}</p>{/if}

	{#if import.meta.env.DEV && !me}
		<div class="dev-panel">
			<label>
				{s('devInitData')}
				<input bind:value={devKey} placeholder="user=…&auth_date=…&hash=…" />
			</label>
			<button onclick={useDevKey}>{s('connect')}</button>
		</div>
	{/if}

	<nav class="tabs" aria-label={s('managerTitle')}>
		<button class:active={tab === 'ads'} onclick={() => (tab = 'ads')}><IconLayoutGrid /> {s('tabsAds')}</button>
		<button class:active={tab === 'placements'} onclick={() => (tab = 'placements')}><IconMapPin /> {s('tabsPlacements')}</button>
		<button class:active={tab === 'stats'} onclick={() => (tab = 'stats')}><IconChart /> {s('tabsStats')}</button>
	</nav>

	{#if tab === 'ads'}
		<div class="toolbar">
			<p>{s('adsHint')}</p>
			{#if me?.admin}<button class="primary" onclick={openCreate}><IconPlus /> {s('newAdvert')}</button>{/if}
		</div>
		{#if ads.length === 0}
			<p class="empty">{s('noAds')}</p>
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
									<span class:live={!ad.paused} class="badge">{ad.paused ? s('paused') : s('live')}</span>
									<span class="badge">{s('weight')} {ad.weight ?? 1}</span>
									{#each ad.categories ?? [] as category}<span class="badge">{category}</span>{/each}
								</div>
							</div>
						</div>
						{#if me?.admin}
							<div class="row-actions">
								<button onclick={() => openEdit(ad)}><IconPencil /> {s('edit')}</button>
								<button class="danger" disabled={busy} onclick={() => remove(ad)}><IconTrash2 /> {s('delete')}</button>
							</div>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	{:else if tab === 'placements'}
		{#if publishers.length === 0}
			<p class="empty">{s('noPlacements')}</p>
		{:else}
			<ul class="ad-list">
				{#each publishers as publisher (publisher.id)}
					<li>
						<div>
							<strong>{publisher.name}</strong>
							<div class="chips">
								<span class="badge">{publisher.kind}</span>
								{#if publisher.blocked}<span class="badge">{s('blocked')}</span>{/if}
							</div>
							<code class="key">{publisher.key}</code>
						</div>
						<button onclick={() => navigator.clipboard.writeText(publisher.key)}><IconCopy /> {s('copyKey')}</button>
					</li>
				{/each}
			</ul>
		{/if}
	{:else}
		{#if stats}
			<div class="stat-grid">
				<div class="stat"><span><IconEye /> {s('views7')}</span><strong>{stats.totals['7'].view.toLocaleString()}</strong></div>
				<div class="stat"><span><IconMousePointerClick /> {s('clicks7')}</span><strong>{stats.totals['7'].click.toLocaleString()}</strong></div>
				<div class="stat"><span><IconGift /> {s('rewarded7')}</span><strong>{stats.totals['7'].reward.toLocaleString()}</strong></div>
				<div class="stat"><span><IconChart /> {s('clickRate')}</span><strong>{ctr(stats.totals['7'])}</strong></div>
			</div>
			<h2>{s('last30')}</h2>
			<div class="chart">
				{#each stats.days as day (day.day)}
					<div class="bar" title={`${day.day}: ${day.view} ${s('views')}`}>
						<div style={`height: ${Math.max(2, (day.view / maxViews) * 100)}%`}></div>
					</div>
				{/each}
			</div>
			<h2>{s('perAdvert')}</h2>
			<ul class="ad-list">
				{#each stats.ads as ad (ad.id)}
					<li>
						<strong>{ad.title ?? ad.id}</strong>
						<span>{ad.view.toLocaleString()} {s('views')} · {ad.click.toLocaleString()} {s('clicks')} · {ad.reward.toLocaleString()} {s('rewarded')}</span>
					</li>
				{/each}
			</ul>
		{:else}
			<p class="empty">{s('noStats')}</p>
		{/if}
	{/if}
</div>

{#if formOpen}
	<div class="modal" role="dialog" aria-modal="true" aria-label={s('managerTitle')}>
		<div class="sheet">
			<header>
				<h2><IconSettings2 /> {editingId ? s('editAdvert') : s('createAdvert')}</h2>
				<button onclick={() => (formOpen = false)} aria-label={s('close')}><IconX /></button>
			</header>
			<div class="form-grid">
				<label class="wide">{s('link')}<input type="url" bind:value={draft.url} /></label>
				<label>{s('emoji')}<input bind:value={draft.emoji} maxlength="8" /></label>
				<label>{s('weightLabel')}<input type="number" min="0" max="1000" bind:value={draft.weight} /></label>
				<label>{s('start')}<input type="date" bind:value={draft.start} /></label>
				<label>{s('end')}<input type="date" bind:value={draft.end} /></label>
				<label class="check"><input type="checkbox" bind:checked={draft.paused} /> {s('startPaused')}</label>
				<fieldset>
					<legend>{s('placements')}</legend>
					{#each PLACEMENTS as item}<label class="check"><input type="checkbox" value={item} bind:group={draft.placements} /> {item}</label>{/each}
				</fieldset>
				<fieldset>
					<legend>{s('categories')}</legend>
					{#each CATEGORIES as item}<label class="check"><input type="checkbox" value={item} bind:group={draft.categories} /> {item}</label>{/each}
				</fieldset>
				<fieldset class="wide">
					<legend>{s('look')}</legend>
					<label>{s('variant')}<select bind:value={draft.variant}><option value="card">card</option><option value="banner">banner</option><option value="poster">poster</option></select></label>
					<label>{s('background')}<input type="color" bind:value={draft.background} /></label>
					<label>{s('textColor')}<input type="color" bind:value={draft.color} /></label>
					<label>{s('accent')}<input type="color" bind:value={draft.accent} /></label>
				</fieldset>
				{#each ['en', 'de'] as textLang}
					<fieldset class="wide">
						<legend>{s(textLang === 'en' ? 'englishText' : 'germanText')}</legend>
						<label>{s('titleLabel')}<input bind:value={draft[textLang as 'en' | 'de'].title} maxlength="60" /></label>
						<label>{s('bodyLabel')}<input bind:value={draft[textLang as 'en' | 'de'].body} maxlength="200" /></label>
						<label>{s('buttonLabel')}<input bind:value={draft[textLang as 'en' | 'de'].cta} maxlength="30" /></label>
					</fieldset>
				{/each}
			</div>
			<div class="preview-wrap">
				<h3>{s('preview')}</h3>
				<div class="preview" bind:this={preview}></div>
			</div>
			{#if error}<p class="alert" role="alert">{error}</p>{/if}
			<footer>
				<button onclick={() => (formOpen = false)}>{s('cancel')}</button>
				<button class="primary" disabled={busy} onclick={save}>{busy ? s('saving') : s('save')}</button>
			</footer>
		</div>
	</div>
{/if}
{/key}
