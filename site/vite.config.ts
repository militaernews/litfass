import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit({ preprocess: vitePreprocess(), adapter: adapter({ fallback: 'index.html' }) })],
	server: {
		host: '0.0.0.0',
		// The feed server runs next to its database; in dev it is reached through this proxy.
		proxy: { '/litfass': { target: import.meta.env?.VITE_API_ORIGIN ?? 'http://localhost:3792', changeOrigin: true } }
	}
});
