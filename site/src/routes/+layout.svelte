<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { localeState } from '../lib/locale.svelte';
	import { setTelegramTheme, startPrefs } from '../lib/prefs.svelte';
	import { watchTelegramTheme } from '../lib/telegram';

	let { children } = $props();

	onMount(() => {
		startPrefs();
		const stop = watchTelegramTheme(setTelegramTheme);
		if (import.meta.env.PROD && 'serviceWorker' in navigator) {
			navigator.serviceWorker.register('/sw.js').catch(() => {});
		}
		return stop;
	});

	$effect(() => {
		document.documentElement.lang = localeState.value;
	});
</script>

{@render children()}
