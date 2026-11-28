<script lang="ts">
	import IconCopy from '~icons/lucide/copy';
	import IconCheck from '~icons/lucide/check';
	import { highlight } from './highlight';
	import { m } from './paraglide/messages.js';
	import { localeState } from './locale.svelte';

	let {
		code,
		language = 'typescript',
		label = 'Code'
	}: { code: string; language?: 'bash' | 'python' | 'typescript'; label?: string } = $props();

	const s = (key: string) => (m as unknown as Record<string, (() => string) | undefined>)[key]?.() ?? '';
	const html = $derived(highlight(code, language));
	const lines = $derived(code.split('\n').length);
	let copied = $state(false);

	async function copy() {
		await navigator.clipboard.writeText(code);
		copied = true;
		setTimeout(() => (copied = false), 1500);
	}
</script>

{#key localeState.value}
	<div class="code-block">
		<div class="code-toolbar">
			<span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>
			<span class="label">{label}</span>
			<button onclick={copy} aria-label={s('copy')}>
				{#if copied}<IconCheck /> {s('copied')}{:else}<IconCopy /> {s('copy')}{/if}
			</button>
		</div>
		<div class="code-body">
			<pre class="numbers" aria-hidden="true">{#each Array(lines) as _, index}{index + 1}
{/each}</pre>
			<pre class="source"><code class="hljs">{@html html}</code></pre>
		</div>
	</div>
{/key}
