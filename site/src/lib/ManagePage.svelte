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
	import IconSparkles from '~icons/lucide/sparkles';
	import IconArrowRight from '~icons/lucide/arrow-right';
	import IconTelegram from '~icons/logos/telegram';
	import type { Ad } from '@militaernews/litfass';
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
		days: number;
		totals: Events;
		previous: Events;
		ctr: number;
		previousCtr: number;
		series: Array<{ day: string } & Events>;
		ads: Array<{ id: string; title: string; views: number; clicks: number; rewards: number; ctr: number }>;
		placements: Array<{ id: number; name: string; views: number; clicks: number; rewards: number; ctr: number }>;
	}
	interface ManagedAd extends Ad {
		paused?: boolean;
		paid?: boolean;
		created_by?: number;
		trackId?: string;
		boosted?: boolean;
		task?: { type: 'join'; chat: string };
	}
	interface Me {
		user: TelegramUser;
		admin: boolean;
		stars?: number;
		earnings?: number;
	}
	let me = $state<Me | null>(null);
	let ads = $state<ManagedAd[]>([]);
	let publishers = $state<Array<{ id: number; name: string; key: string; kind: string; blocked: boolean; allow_free: number | boolean; price_per_click?: number; audience_size?: number; boost_only?: number | boolean }>>([]);
	let stats = $state<Stats | null>(null);
	let days = $state<7 | 30 | 90>(30);
	let visible = $state({ view: true, click: true, reward: true });
	let tab = $state<'ads' | 'placements' | 'stats'>('ads');
	let devKey = $state('');
	let error = $state('');
	let notice = $state('');
	let busy = $state(false);



	async function reload() {
		const [identity, adverts, placements, overview] = await Promise.all([
			call<Me>('me'),
			call<{ ads: ManagedAd[] }>('list_ads'),
			call<{ publishers: typeof publishers }>('publishers'),
			call<{ stats: Stats }>('stats', { days })
		]);
		me = identity;
		ads = adverts.ads;
		publishers = placements.publishers;
		stats = overview.stats;
	}

	onMount(async () => {
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

	function openCreate() {
		goto('/manage/new');
	}

	function openEdit(ad: ManagedAd) {
		goto(`/manage/ad?id=${encodeURIComponent(ad.id)}`);
	}

	async function remove(ad: ManagedAd) {
		if (!confirm(s('deleteConfirm', { title: ad.text.en?.title ?? ad.id }))) return;
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

	async function boost(ad: ManagedAd) {
		await call('boost_ad', { id: ad.id });
		notice = s('boosted');
		await reload();
	}

	async function updatePublisher(publisher: { id: number; price_per_click?: number; audience_size?: number; boost_only?: number | boolean }, fields: Record<string, unknown>) {
		await call('set_publisher', { id: publisher.id, ...fields });
		await reload();
	}

	function setPrice(publisher: { id: number; price_per_click?: number }) {
		const value = prompt(s('pricePerClick'), String(publisher.price_per_click ?? 1));
		if (value && Number.isFinite(Number(value))) updatePublisher(publisher, { price_per_click: Number(value) });
	}

	async function toggleFree(publisher: { id: number; allow_free: number | boolean }) {
		await call('set_publisher', { id: publisher.id, allow_free: !publisher.allow_free });
		await reload();
	}

	function useDevKey() {
		setDevInitData(devKey);
		localStorage.setItem('litfass-dev-init-data', devKey.trim());
		reload().catch((cause) => (error = String(cause)));
	}

	const ctr = (events: Events) => (events.view ? `${((events.click / events.view) * 100).toFixed(1)}%` : '–');
	const delta = (current: number, previous: number) => (previous ? Math.round(((current - previous) / previous) * 100) : 0);
	const title = (ad: { text?: Record<string, { title: string }> }, id: string) => ad.text?.[localeState.value]?.title ?? ad.text?.en?.title ?? id;

	const lines = $derived.by(() => {
		const data = stats?.series ?? [];
		const max = Math.max(1, ...data.flatMap((day) => [day.view, day.click, day.reward]));
		const points = (key: keyof Events) =>
			data
				.map((day, index) => `${data.length < 2 ? 50 : (index / (data.length - 1)) * 100},${100 - (day[key] / max) * 100}`)
				.join(' ');
		return { view: points('view'), click: points('click'), reward: points('reward'), max };
	});

	async function setDays(value: 7 | 30 | 90) {
		days = value;
		await reload();
	}

	function exportCsv() {
		const rows = [['day', 'views', 'clicks', 'rewards'], ...(stats?.series ?? []).map((d) => [d.day, d.view, d.click, d.reward])];
		const blob = new Blob([rows.map((row) => row.join(',')).join('\n')], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const link = document.createElement('a');
		link.href = url;
		link.download = `litfass-stats-${days}d.csv`;
		link.click();
		URL.revokeObjectURL(url);
	}
</script>

<svelte:head>
	<title>{s('managerTitle')} · litfass</title>
	<meta name="robots" content="noindex" />
</svelte:head>
{#key localeState.value}

<div class="manager">
	<header class="manager-head">
		<a class="brand" href="/">litfass</a>
		<div>
			<h1>{s('managerTitle')}</h1>
			<p>
				{#if me}
					{s('signedInAs')} {me.user.first_name ?? me.user.id}{#if me.admin} <span class="badge">{s('admin')}</span>{/if}
				{:else}
					{s('openFromBot')}
				{/if}
			</p>
			{#if me}
				<div class="wallet">
					<span><IconSparkles /> {me.stars ?? 0} · {s('starsBalance')}</span>
					<span><IconGift /> {me.earnings ?? 0} · {s('earnings')}</span>
					<a href="https://t.me/litfass_advertisement_bot?start=stars" target="_blank" rel="noreferrer">{s('buyStars')}</a>
					<a class="support-link" href="https://t.me/MilitaernewsKontakt" target="_blank" rel="noreferrer"><IconTelegram /> {s('footer')} <IconArrowRight /></a>
				</div>
			{/if}
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
		<div class="next-steps">
			<h2>{s('nextSteps')}</h2>
			{#if publishers.length === 0}
				<a href="/guide" class="step-card"><IconMapPin /> {s('stepNoPlacement')} <IconArrowRight /></a>
			{:else if ads.length === 0}
				<button class="step-card" onclick={openCreate}><IconPlus /> {s('stepNoAds')} <IconArrowRight /></button>
			{:else if stats && stats.ctr < 2}
				<button class="step-card" onclick={openCreate}><IconSparkles /> {s('stepLowCtr')} <IconArrowRight /></button>
			{:else}
				<p class="empty">{s('stepAllDone')}</p>
			{/if}
		</div>
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
								{#if ad.trackId}<code class="track-id">{s('trackingId')}: {ad.trackId}</code>{/if}
								<div class="chips">
									<span class:live={!ad.paused} class="badge">{ad.paused ? s('paused') : s('live')}</span>
									<span class="badge">{s('weight')} {ad.weight ?? 1}</span>
									{#each ad.categories ?? [] as category}<span class="badge">{category}</span>{/each}
								</div>
							</div>
						</div>
						{#if me?.admin}
							<div class="row-actions">
								<button onclick={() => boost(ad)} title={s('boostCost')}>★ {ad.boosted ? s('boosted') : s('boost')}</button>
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
							<div class="chips">
								<span class="badge">{s('pricePerClick')}: {publisher.price_per_click ?? 1}</span>
								<span class="badge">{s('audienceSize')}: {publisher.audience_size ?? 0}</span>
								{#if publisher.boost_only}<span class="badge">{s('boostOnly')}</span>{/if}
							</div>
						</div>
						<div class="row-actions">
							<button onclick={() => navigator.clipboard.writeText(publisher.key)}><IconCopy /> {s('copyKey')}</button>
							<button onclick={() => toggleFree(publisher)}>{publisher.allow_free ? s('deny') : s('allow')} · {s('allowFree')}</button>
							<button onclick={() => setPrice(publisher)}>{s('pricePerClick')}</button>
							<button onclick={() => updatePublisher(publisher, { boost_only: !publisher.boost_only })}>{s('boostOnly')}</button>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	{:else}
		{#if stats}
			<div class="stats-head">
				<div class="range">
					<button class:active={days === 7} onclick={() => setDays(7)}>{s('last7')}</button>
					<button class:active={days === 30} onclick={() => setDays(30)}>{s('last30')}</button>
					<button class:active={days === 90} onclick={() => setDays(90)}>{s('last90')}</button>
				</div>
				<button onclick={exportCsv}><IconCopy /> {s('exportCsv')}</button>
			</div>

			<div class="stat-grid">
				<div class="stat"><span><IconEye /> {s('views')}</span><strong>{stats.totals.view.toLocaleString()}</strong><small class:up={delta(stats.totals.view, stats.previous.view) >= 0} class:down={delta(stats.totals.view, stats.previous.view) < 0}>{delta(stats.totals.view, stats.previous.view)}% {s('vsPrevious')}</small></div>
				<div class="stat"><span><IconMousePointerClick /> {s('clicks')}</span><strong>{stats.totals.click.toLocaleString()}</strong><small class:up={delta(stats.totals.click, stats.previous.click) >= 0} class:down={delta(stats.totals.click, stats.previous.click) < 0}>{delta(stats.totals.click, stats.previous.click)}% {s('vsPrevious')}</small></div>
				<div class="stat"><span><IconGift /> {s('rewarded')}</span><strong>{stats.totals.reward.toLocaleString()}</strong><small class:up={delta(stats.totals.reward, stats.previous.reward) >= 0} class:down={delta(stats.totals.reward, stats.previous.reward) < 0}>{delta(stats.totals.reward, stats.previous.reward)}% {s('vsPrevious')}</small></div>
				<div class="stat"><span><IconChart /> {s('avgCtr')}</span><strong>{stats.ctr}% CTR</strong><small class:up={stats.ctr >= stats.previousCtr} class:down={stats.ctr < stats.previousCtr}>{Math.round(stats.ctr - stats.previousCtr)}% {s('vsPrevious')}</small></div>
			</div>

			<section class="stats-panel">
				<h2>{s('trend')}</h2>
				<div class="series-toggles">
					<button class:active={visible.view} onclick={() => (visible.view = !visible.view)}>{s('viewsSeries')}</button>
					<button class:active={visible.click} onclick={() => (visible.click = !visible.click)}>{s('clicksSeries')}</button>
					<button class:active={visible.reward} onclick={() => (visible.reward = !visible.reward)}>{s('rewardSeries')}</button>
				</div>
				<svg class="line-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={s('trend')}>
					{#if visible.view}<polyline points={lines.view} fill="none" stroke="var(--green)" stroke-width="1.5" vector-effect="non-scaling-stroke" />{/if}
					{#if visible.click}<polyline points={lines.click} fill="none" stroke="var(--red)" stroke-width="1.5" vector-effect="non-scaling-stroke" />{/if}
					{#if visible.reward}<polyline points={lines.reward} fill="none" stroke="#e8c547" stroke-width="1.5" vector-effect="non-scaling-stroke" />{/if}
				</svg>
				<div class="axis"><span>{stats.series[0]?.day}</span><span>{stats.series[stats.series.length - 1]?.day}</span></div>
			</section>

			<section class="stats-panel">
				<h2>{s('funnel')}</h2>
				<div class="funnel">
					<div><span>{s('views')}</span><strong>{stats.totals.view.toLocaleString()}</strong><div class="funnel-bar" style={`width:${Math.max(2, (stats.totals.view / Math.max(1, stats.totals.view)) * 100)}%`}></div></div>
					<div><span>{s('clicks')} · {stats.ctr}% CTR</span><strong>{stats.totals.click.toLocaleString()}</strong><div class="funnel-bar" style={`width:${Math.max(2, (stats.totals.click / Math.max(1, stats.totals.view)) * 100)}%`}></div></div>
					<div><span>{s('rewardSeries')}</span><strong>{stats.totals.reward.toLocaleString()}</strong><div class="funnel-bar" style={`width:${Math.max(2, (stats.totals.reward / Math.max(1, stats.totals.view)) * 100)}%`}></div></div>
				</div>
			</section>

			<section class="stats-panel">
				<h2>{s('topCampaigns')}</h2>
				{#if stats.ads.length}
					<div class="table-wrap"><table>
						<thead><tr><th>{s('campaigns')}</th><th>{s('views')}</th><th>{s('clicks')}</th><th>{s('ctr')}</th></tr></thead>
						<tbody>{#each stats.ads as ad (ad.id)}<tr><td>{ad.title}</td><td>{ad.views.toLocaleString()}</td><td>{ad.clicks.toLocaleString()}</td><td>{ad.ctr}%</td></tr>{/each}</tbody>
					</table></div>
				{:else}<p class="empty">{s('noData')}</p>{/if}
			</section>

			<section class="stats-panel">
				<h2>{s('placementsBreakdown')}</h2>
				{#if stats.placements.length}
					<div class="table-wrap"><table>
						<thead><tr><th>{s('tabsPlacements')}</th><th>{s('views')}</th><th>{s('clicks')}</th><th>{s('ctr')}</th></tr></thead>
						<tbody>{#each stats.placements as place (place.id)}<tr><td>{place.name}</td><td>{place.views.toLocaleString()}</td><td>{place.clicks.toLocaleString()}</td><td>{place.ctr}%</td></tr>{/each}</tbody>
					</table></div>
				{:else}<p class="empty">{s('noData')}</p>{/if}
			</section>

			<section class="stats-panel">
				<h2>{s('daily')}</h2>
				<div class="table-wrap"><table>
					<thead><tr><th>{s('start')}</th><th>{s('views')}</th><th>{s('clicks')}</th><th>{s('rewardSeries')}</th></tr></thead>
					<tbody>{#each [...stats.series].reverse().slice(0, 14) as day (day.day)}<tr><td>{day.day}</td><td>{day.view}</td><td>{day.click}</td><td>{day.reward}</td></tr>{/each}</tbody>
				</table></div>
			</section>
		{:else}
			<p class="empty">{s('noStats')}</p>
		{/if}
	{/if}
</div>

{/key}
