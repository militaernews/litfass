<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import SiteControls from '../lib/SiteControls.svelte';
	import { localeState } from '../lib/locale.svelte';
	import { startPrefs } from '../lib/prefs.svelte';

	let { children } = $props();

	onMount(startPrefs);

	$effect(() => {
		document.documentElement.lang = localeState.value;
	});
</script>

<SiteControls />

{@render children()}
