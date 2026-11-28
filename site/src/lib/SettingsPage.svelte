<script lang="ts">
	import IconMonitor from '~icons/lucide/monitor';
	import IconSun from '~icons/lucide/sun';
	import IconMoon from '~icons/lucide/moon';
	import IconLanguages from '~icons/lucide/languages';
	import IconArrowRight from '~icons/lucide/arrow-right';
	import IconFileText from '~icons/lucide/file-text';
	import IconInfo from '~icons/lucide/info';
	import IconSend from '~icons/logos/telegram';
	import { m } from './paraglide/messages.js';
	import { localeState, changeLocale } from './locale.svelte';
	import { locales } from './paraglide/runtime.js';
	import { prefs, setTheme, THEMES, type Theme } from './prefs.svelte';
	import { CHANGES } from './changelog';

	const s = (key: string) => (m as unknown as Record<string, (() => string) | undefined>)[key]?.() ?? '';
	const icons = { system: IconMonitor, light: IconSun, dark: IconMoon };
	const labels: Record<Theme, string> = { system: s('themeSystem'), light: s('themeLight'), dark: s('themeDark') };
</script>

<svelte:head>
	<title>{s('settingsTitle')} · litfass</title>
	<meta name="description" content={s('settingsLead')} />
</svelte:head>

{#key localeState.value}
	<main class="page settings">
		<header class="settings-head">
			<p class="eyebrow">litfass</p>
			<h1>{s('settingsTitle')}</h1>
			<p class="lead">{s('settingsLead')}</p>
		</header>

		<section>
			<h2><IconMonitor /> {s('appearance')}</h2>
			<div class="options">
				{#each THEMES as theme (theme)}
					{@const Icon = icons[theme]}
					<button class:active={prefs.theme === theme} onclick={() => setTheme(theme)} aria-pressed={prefs.theme === theme}>
						<Icon /> {labels[theme]}
					</button>
				{/each}
			</div>
			{#if prefs.inTelegram && prefs.theme === 'system'}
				<p class="note"><IconSend /> {s('followTelegram')}</p>
			{/if}
		</section>

		<section>
			<h2><IconLanguages /> {s('language')}</h2>
			<div class="options">
				{#each locales as option (option)}
					<button
						class:active={localeState.value === option}
						aria-pressed={localeState.value === option}
						onclick={() => changeLocale(option)}>{option === 'de' ? 'Deutsch' : 'English'}</button
					>
				{/each}
			</div>
		</section>

		<section>
			<h2><IconFileText /> {s('changelog')}</h2>
			<p class="muted">{s('changelogIntro')}</p>
			<div class="changes">
				{#each CHANGES as change (change.version)}
					<article>
						<header><strong>{s('version')} {change.version}</strong><time>{change.date}</time></header>
						<ul>
							{#each localeState.value === 'de' ? change.de : change.en as item}<li>{item}</li>{/each}
						</ul>
					</article>
				{/each}
			</div>
		</section>

		<nav class="links">
			<a href="/about"><IconInfo /> {s('aboutLink')} <IconArrowRight /></a>
			<a href="/guide"><IconFileText /> {s('guideTitle')} <IconArrowRight /></a>
		</nav>
	</main>
{/key}
