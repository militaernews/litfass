import hljs from 'highlight.js/lib/core';
import bash from 'highlight.js/lib/languages/bash';
import python from 'highlight.js/lib/languages/python';
import typescript from 'highlight.js/lib/languages/typescript';

hljs.registerLanguage('bash', bash);
hljs.registerLanguage('python', python);
hljs.registerLanguage('typescript', typescript);

/** Highlighted, escaped HTML for the code samples on the landing page. */
export function highlight(code: string, language: 'bash' | 'python' | 'typescript'): string {
	return hljs.highlight(code.trim(), { language }).value;
}
