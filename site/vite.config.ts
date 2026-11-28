import adapter from '@sveltejs/adapter-static';
import tailwindcss from '@tailwindcss/vite';
import { paraglideVitePlugin } from '@inlang/paraglide-js';
import { sveltekit } from '@sveltejs/kit/vite';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import Icons from 'unplugin-icons/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		paraglideVitePlugin({
			project: './project.inlang',
			outdir: './src/lib/paraglide',
			// A manual choice is remembered; otherwise the browser language decides
			strategy: ['localStorage', 'preferredLanguage', 'baseLocale']
		}),
		sveltekit({ preprocess: vitePreprocess(), adapter: adapter() }),
		Icons({ compiler: 'svelte' })
	],
	server: {
		host: '0.0.0.0',
		// The feed server runs next to its database; in dev it is reached through this proxy.
		proxy: { '/litfass': { target: import.meta.env?.VITE_API_ORIGIN ?? 'http://localhost:3792', changeOrigin: true } }
	}
});
