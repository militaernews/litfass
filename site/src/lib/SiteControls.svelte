<script lang="ts">
	import IconMonitor from '~icons/lucide/monitor';
	import IconSun from '~icons/lucide/sun';
	import IconMoon from '~icons/lucide/moon';
	import IconLanguages from '~icons/lucide/languages';
	import { m } from './paraglide/messages.js';
	import { locales } from './paraglide/runtime.js';
	import { localeState, changeLocale } from './locale.svelte';
	import { THEMES, prefs, setTheme, type Theme } from './prefs.svelte';

	const s = (key: string) => (m as unknown as Record<string, (() => string) | undefined>)[key]?.() ?? '';
	const icons = { system: IconMonitor, light: IconSun, dark: IconMoon };
	const labels: Record<Theme, string> = { system: s('themeSystem'), light: s('themeLight'), dark: s('themeDark') };
</script>

{#key localeState.value}
	<div class="controls">
		<div class="group" role="group" aria-label={s('appearance')}>
			{#each THEMES as option (option)}
				{@const Icon = icons[option]}
				<button
					type="button"
					class:active={prefs.theme === option}
					aria-pressed={prefs.theme === option}
					title={labels[option]}
					aria-label={labels[option]}
					onclick={() => setTheme(option)}><Icon /></button
				>
			{/each}
		</div>
		<div class="group" role="group" aria-label={s('language')}>
			<button type="button" aria-hidden="true" tabindex="-1" class="marker"><IconLanguages /></button>
			{#each locales as option (option)}
				<button
					type="button"
					class:active={localeState.value === option}
					aria-pressed={localeState.value === option}
					aria-label={option}
					onclick={() => changeLocale(option)}>{option.toUpperCase()}</button
				>
			{/each}
		</div>
	</div>
{/key}

<style>
	.controls {
		position: fixed;
		inset-block-start: 14px;
		inset-inline-end: 14px;
		z-index: 30;
		display: flex;
		gap: 8px;
	}
	.group {
		display: flex;
		align-items: center;
		gap: 2px;
		padding: 3px;
		border: 1px solid var(--line);
		border-radius: 999px;
		background: var(--card);
		box-shadow: 0 6px 24px #0002;
	}
	button {
		display: grid;
		place-items: center;
		min-width: 30px;
		height: 28px;
		padding: 0 7px;
		border: 0;
		border-radius: 999px;
		background: transparent;
		color: var(--muted);
		font: inherit;
		font-size: 0.75rem;
		font-weight: 800;
		cursor: pointer;
	}
	button :global(svg) {
		width: 15px;
		height: 15px;
	}
	button.active {
		background: var(--green);
		color: var(--bg);
	}
	button:hover:not(.active):not(.marker) {
		color: var(--green);
	}
	button.marker {
		cursor: default;
		opacity: 0.6;
	}
	@media (max-width: 640px) {
		.controls {
			inset-block-start: 8px;
			inset-inline-end: 8px;
			transform: scale(0.88);
			transform-origin: top right;
		}
	}
</style>
