import type { Ad } from '@militaernews/litfass';

export interface Draft {
	url: string;
	emoji: string;
	video: string;
	taskChat: string;
	weight: number;
	start: string;
	end: string;
	paused: boolean;
	paid: boolean;
	placements: string[];
	categories: string[];
	variant: 'card' | 'banner' | 'poster';
	background: string;
	color: string;
	accent: string;
	en: { title: string; body: string; cta: string };
	de: { title: string; body: string; cta: string };
}

export const emptyDraft = (): Draft => ({
	url: 'https://t.me/',
	emoji: '📰',
	video: '',
	taskChat: '',
	weight: 1,
	start: '',
	end: '',
	paused: true,
	paid: false,
	placements: [],
	categories: [],
	variant: 'card',
	background: '#0c3a6b',
	color: '#e6f6ff',
	accent: '#2ec5ff',
	en: { title: '', body: '', cta: '' },
	de: { title: '', body: '', cta: '' }
});

export function fromAd(ad: Ad & { paused?: boolean; paid?: boolean; task?: { type: 'join'; chat: string } }): Draft {
	return {
		...emptyDraft(),
		url: ad.url,
		emoji: ad.emoji ?? '',
		video: ad.video ?? '',
		taskChat: ad.task?.chat ?? '',
		weight: ad.weight ?? 1,
		start: ad.start ?? '',
		end: ad.end ?? '',
		paused: Boolean(ad.paused),
		paid: Boolean(ad.paid),
		placements: [...(ad.placements ?? [])],
		categories: [...(ad.categories ?? [])],
		variant: ad.style?.variant ?? 'card',
		background: ad.style?.background ?? '#0c3a6b',
		color: ad.style?.color ?? '#e6f6ff',
		accent: ad.style?.accent ?? '#2ec5ff',
		en: ad.text.en ?? { title: '', body: '', cta: '' },
		de: ad.text.de ?? { title: '', body: '', cta: '' }
	};
}

export function toPayload(draft: Draft, id?: string): Record<string, unknown> {
	return {
		...(id ? { id } : {}),
		url: draft.url,
		emoji: draft.emoji || null,
		video: draft.video || null,
		taskChat: draft.taskChat || null,
		weight: Number(draft.weight),
		start: draft.start || null,
		end: draft.end || null,
		paused: draft.paused,
		paid: draft.paid,
		placements: draft.placements,
		categories: draft.categories,
		style: { variant: draft.variant, background: draft.background, color: draft.color, accent: draft.accent },
		text: { en: draft.en, ...(draft.de.title ? { de: draft.de } : {}) }
	};
}

export function asAd(draft: Draft, id = 'preview'): Ad {
	return {
		id,
		url: draft.url,
		emoji: draft.emoji || undefined,
		video: draft.video || undefined,
		weight: draft.weight,
		start: draft.start || undefined,
		end: draft.end || undefined,
		text: { en: draft.en, ...(draft.de.title ? { de: draft.de } : {}) },
		style: { variant: draft.variant, background: draft.background, color: draft.color, accent: draft.accent },
		...(draft.taskChat ? { task: { type: 'join' as const, chat: draft.taskChat } } : {})
	};
}
