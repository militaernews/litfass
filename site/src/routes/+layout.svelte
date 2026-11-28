<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import SiteControls from '../lib/SiteControls.svelte';
	import { localeState } from '../lib/locale.svelte';
	import { startPrefs } from '../lib/prefs.svelte';

	let { children } = $props();

	onMount(() => {
		startPrefs();
		if (import.meta.env.PROD && 'serviceWorker' in navigator) {
			navigator.serviceWorker.register('/sw.js').catch(() => {});
		}
	});

	$effect(() => {
		document.documentElement.lang = localeState.value;
	});
</script>

<SiteControls />

{@render children()}
