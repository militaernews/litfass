<script lang="ts">
	import { m } from './paraglide/messages.js';
	import { locales } from './paraglide/runtime.js';
	import { localeState, changeLocale } from './locale.svelte';
	import { THEMES, prefs, setTheme, type Theme } from './prefs.svelte';

	const themeLabel: Record<Theme, string> = {
		system: m.themeSystem(),
		light: m.themeLight(),
		dark: m.themeDark()
	};
	const icons: Record<Theme, string> = { system: '🖥', light: '☀', dark: '☾' };
</script>

{#key localeState.value}
	<div class="controls">
		<div class="group" role="group" aria-label={m.appearance()}>
			{#each THEMES as option (option)}
				<button
					type="button"
					class:active={prefs.theme === option}
					aria-pressed={prefs.theme === option}
					title={themeLabel[option]}
					aria-label={themeLabel[option]}
					onclick={() => setTheme(option)}>{icons[option]}</button
				>
			{/each}
		</div>
		<div class="group" role="group" aria-label={m.language()}>
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
		inset-block-start: 12px;
		inset-inline-end: 12px;
		z-index: 30;
		display: flex;
		gap: 8px;
	}
	.group {
		display: flex;
		gap: 2px;
		padding: 3px;
		border: 1px solid var(--bg-2);
		border-radius: 999px;
		background: var(--card);
		box-shadow: 0 6px 20px #0002;
	}
	button {
		min-width: 30px;
		height: 28px;
		padding: 0 6px;
		border: 0;
		border-radius: 999px;
		background: transparent;
		color: var(--muted);
		font: inherit;
		font-size: 0.8rem;
		font-weight: 700;
		cursor: pointer;
	}
	button.active {
		background: var(--green);
		color: var(--bg);
	}
	button:hover:not(.active) {
		color: var(--green);
	}
	@media (max-width: 640px) {
		.controls {
			inset-block-start: 8px;
			inset-inline-end: 8px;
			transform: scale(0.9);
			transform-origin: top right;
		}
	}
</style>
