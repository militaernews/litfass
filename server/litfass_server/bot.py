"""The Telegram side: admins manage adverts, anyone can register a place that shows them.

Free-text answers (links, texts, colours, dates) are collected through a per-user "awaiting" state:
a button sets what the next message means, the text handler fills it in.
"""

from __future__ import annotations

import logging
import random
import re
import datetime
from datetime import date
from html import escape

from telegram import InlineKeyboardButton as Button
from telegram import InlineKeyboardMarkup as Markup
from telegram import LabeledPrice, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from litfass_server.api import campaign_report
from litfass_server.feed import CATEGORIES, KINDS, PLACEMENTS, STYLE_PRESETS, VARIANTS
from litfass_server.pricing import STAR_PACKAGE
from litfass_server.stats import overview
from litfass_server.store import Store
from litfass_server.texts import labels, lang_of, t

logger = logging.getLogger(__name__)

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
LANG = re.compile(r"^[a-z]{2}(-[A-Za-z]{2})?$")
MAX_TEXT = {"title": 60, "body": 200, "cta": 30}


class Ctx:
    """What the handlers share, attached to the application's bot_data."""

    def __init__(self, store: Store, admins: set[int], public_url: str) -> None:
        self.store = store
        self.admins = admins
        self.public_url = public_url


def ctx(context: ContextTypes.DEFAULT_TYPE) -> Ctx:
    return context.application.bot_data["litfass"]


def is_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    return user_id in ctx(context).admins


def toggle(values: list[str], value: str) -> list[str]:
    return [v for v in values if v != value] if value in values else [*values, value]


def check_rows(options: dict[str, str], chosen: list[str], prefix: str, per_row: int = 2) -> list[list[Button]]:
    buttons = [Button(("✅ " if key in chosen else "▫️ ") + label, callback_data=f"{prefix}:{key}") for key, label in options.items()]
    return [buttons[i : i + per_row] for i in range(0, len(buttons), per_row)]


# Ad cards -----------------------------------------------------------------------------------------


def ad_title(ad: dict) -> str:
    text = ad["text"].get("en") or next(iter(ad["text"].values()), None)
    return text["title"] if text else ad["url"]


def ad_card(ad: dict, lang: str = "en") -> tuple[str, Markup]:
    status = t(lang, "paused") if ad["paused"] else t(lang, "live")
    text = ad["text"].get("en")
    preview = (
        f"<i>Anzeige</i>\n{escape(ad['emoji'] or '')} <b>{escape(text['title'])}</b>\n{escape(text['body'])}\n[{escape(text['cta'])}]"
        if text
        else t(lang, "no_en_text")
    )
    style = ad["style"]
    style_line = ", ".join(f"{k} {v}" for k, v in style.items()) if style else t(lang, "default")
    schedule = f"{ad['start'] or '…'} → {ad['end'] or '…'}" if ad["start"] or ad["end"] else t(lang, "always")
    lines = [
        preview,
        "",
        t(lang, "ad_line", id=ad["id"], status=status, weight=ad["weight"]),
        f"🔗 {escape(ad['url'])}",
        f"🌐 {', '.join(ad['text']) or '–'} · 🖼 {t(lang, 'yes') if ad['image_file_id'] else t(lang, 'no')}",
        f"🗂 {', '.join(ad['categories']) or t(lang, 'all_content')}",
        f"📍 {', '.join(ad['placements']) or t(lang, 'all_placements')}",
        f"🎨 {escape(style_line)}",
        f"📅 {schedule}",
        f"{'💎' if ad['paid'] else '🆓'} {t(lang, 'b_paid' if ad['paid'] else 'b_free')}",
    ]
    a = f"ad:{ad['id']}"
    markup = Markup(
        [
            [
                Button(t(lang, "b_pause") if not ad["paused"] else t(lang, "b_live"), callback_data=f"{a}:live"),
                Button(t(lang, "b_delete"), callback_data=f"{a}:del"),
            ],
            [
                Button(t(lang, "b_texts"), callback_data=f"{a}:texts"),
                Button(t(lang, "b_link"), callback_data=f"{a}:link"),
                Button(t(lang, "b_emoji"), callback_data=f"{a}:emoji"),
            ],
            [
                Button(t(lang, "b_content"), callback_data=f"{a}:cats"),
                Button(t(lang, "b_placements"), callback_data=f"{a}:places"),
                Button(t(lang, "b_style"), callback_data=f"{a}:style"),
            ],
            [
                Button(t(lang, "b_weight"), callback_data=f"{a}:weight"),
                Button(t(lang, "b_schedule"), callback_data=f"{a}:sched"),
                Button(t(lang, "b_image"), callback_data=f"{a}:image"),
            ],
            [Button(t(lang, "b_stats"), callback_data=f"{a}:stats"), Button(t(lang, "b_all_ads"), callback_data="ads"), Button(t(lang, "b_main_menu"), callback_data="menu")],
        ]
    )
    return "\n".join(lines), markup


def ads_list(store: Store, lang: str = "en", owner_id: int | None = None) -> tuple[str, Markup]:
    ads = store.list_ads()
    if owner_id is not None:
        ads = [ad for ad in ads if ad.get("created_by") == owner_id]
    rows = [[Button(("⏸ " if ad["paused"] else "🟢 ") + ad_title(ad)[:40], callback_data=f"ad:{ad['id']}:show")] for ad in ads]
    rows.append([Button(t(lang, "b_new_ad"), callback_data="newad"), Button(t(lang, "b_stats"), callback_data="stats"), Button(t(lang, "b_main_menu"), callback_data="menu")])
    return (t(lang, "campaigns_title") if owner_id is not None else t(lang, "n_ads", n=len(ads))) if ads else t(lang, "campaigns_empty" if owner_id is not None else "no_ads"), Markup(rows)


def style_keyboard(ad: dict, lang: str = "en") -> Markup:
    a = f"ad:{ad['id']}"
    presets = [Button(name, callback_data=f"{a}:sty:{name}") for name in STYLE_PRESETS]
    current = ad["style"].get("variant", "card")
    variants = [Button(("✅ " if key == current else "") + label, callback_data=f"{a}:var:{key}") for key, label in labels(VARIANTS, lang).items()]
    return Markup(
        [
            presets[:3],
            presets[3:],
            variants,
            [Button(t(lang, "b_own_colors"), callback_data=f"{a}:colors"), Button(t(lang, "b_reset"), callback_data=f"{a}:sty:none")],
            [Button(t(lang, "b_done"), callback_data=f"{a}:show")],
        ]
    )


# Publisher cards ----------------------------------------------------------------------------------


def feed_url(c: Ctx, publisher: dict) -> str:
    return f"{c.public_url}/v1/feed/{publisher['key']}"


def publisher_card(c: Ctx, publisher: dict, admin: bool, lang: str = "en") -> tuple[str, Markup]:
    categories, kinds = labels(CATEGORIES, lang), labels(KINDS, lang)
    cats = ", ".join(categories.get(k, k) for k in publisher["categories"]) or t(lang, "everything")
    lines = [
        f"<b>{escape(publisher['name'])}</b> · {kinds.get(publisher['kind'], publisher['kind'])}",
        t(lang, "content", cats=cats),
        t(lang, "blocked") if publisher["blocked"] else "",
        t(lang, "earnings_line", n=c.store.earnings(publisher["id"])),
        t(lang, "b_free_on") if publisher["allow_free"] else t(lang, "b_free_off"),
        "",
        t(lang, "feed_url"),
        f"<code>{escape(feed_url(c, publisher))}</code>",
        "",
        t(lang, "feed_howto"),
    ]
    p = f"pub:{publisher['id']}"
    rows = [
        [Button(t(lang, "b_content"), callback_data=f"{p}:cats"), Button(t(lang, "b_rename"), callback_data=f"{p}:rename")],
        [Button(t(lang, "b_new_key"), callback_data=f"{p}:key"), Button(t(lang, "b_delete"), callback_data=f"{p}:del")],
        [Button(t(lang, "b_stats"), callback_data=f"{p}:stats"), Button(t(lang, "b_allow_free"), callback_data=f"{p}:free")],
        [Button(t(lang, "b_main_menu"), callback_data="menu")],
    ]
    if admin:
        rows.append([Button(t(lang, "b_unblock") if publisher["blocked"] else t(lang, "b_block"), callback_data=f"{p}:block")])
    return "\n".join(line for line in lines if line is not None), Markup(rows)


def may_edit(context: ContextTypes.DEFAULT_TYPE, user_id: int, publisher: dict | None) -> bool:
    return bool(publisher) and (publisher["owner_id"] == user_id or is_admin(context, user_id))


# Navigation ----------------------------------------------------------------------------------------


def menu_markup(c: Ctx, user_id: int, lang: str) -> Markup:
    rows = [
        [
            Button(t(lang, "b_my_placements"), callback_data="menu:mine"),
            Button(t(lang, "b_my_campaigns"), callback_data="menu:campaigns"),
        ],
        [Button(t(lang, "b_stats"), callback_data="menu:stats"), Button(t(lang, "b_buy_stars"), callback_data="menu:stars")],
        [
            Button(t(lang, "b_manage_app"), url=f"{c.public_url}/manage"),
            Button(t(lang, "b_support"), url="https://t.me/MilitaernewsKontakt"),
        ],
    ]
    if user_id in c.admins:
        rows.append(
            [
                Button(t(lang, "b_all_ads"), callback_data="ads"),
                Button(t(lang, "b_placements"), callback_data="menu:publishers"),
                Button(t(lang, "b_new_ad"), callback_data="newad"),
            ]
        )
    return Markup(rows)


async def send_stars_invoice(target, lang: str) -> None:
    await target.reply_invoice(
        title="litfass Stars",
        description=("Stars to publish and click paid adverts." if lang == "en" else "Stars für bezahlte Anzeigen und Klicks."),
        payload="stars:package",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice("Stars", STAR_PACKAGE)],
        start_parameter="stars",
    )


# Commands -----------------------------------------------------------------------------------------


def lang(update: Update) -> str:
    return lang_of(update.effective_user)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lg = lang(update)
    c = ctx(context)
    balance = c.store.stars(update.effective_user.id)
    text = (
        t(lg, "menu_title")
        + "\n"
        + t(lg, "stars_line", n=balance)
        + ("\n\n" + t(lg, "start_admin") if is_admin(context, update.effective_user.id) else "")
    )
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=menu_markup(c, update.effective_user.id, lg))


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("awaiting", None)
    context.user_data.pop("draft", None)
    await update.effective_message.reply_text(t(lang(update), "cancelled"))


async def ads_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    c = ctx(context)
    user_id = update.effective_user.id
    admin = is_admin(context, user_id)
    text, markup = ads_list(c.store, lang(update), None if admin else user_id)
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def campaigns_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ads_command(update, context)


async def newad_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting"] = ("new_url", None)
    await update.effective_message.reply_text(t(lang(update), "ask_new_url"))


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Post one live advert into the chat the bot was added to."""
    lg = lang(update)
    ads = [ad for ad in ctx(context).store.list_ads() if not ad["paused"] and ad["text"].get("en")]
    if not ads:
        await update.effective_message.reply_text(t(lg, "post_empty"))
        return
    ad = random.choice(ads)
    text = ad["text"]["en"]
    message = (
        f"<i>Anzeige</i>\n{escape(ad['emoji'] or '')} <b>{escape(text['title'])}</b>\n{escape(text['body'])}"
    )
    markup = Markup([[Button(text["cta"], url=ad["url"])]])
    try:
        await update.effective_message.reply_text(
            message, parse_mode=ParseMode.HTML, reply_markup=markup, disable_web_page_preview=True
        )
    except TelegramError:
        await update.effective_message.reply_text(t(lg, "post_fail"))


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting"] = ("pub_name", None)
    await update.effective_message.reply_text(t(lang(update), "ask_pub_name"))


async def mine_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_publishers(update, context, ctx(context).store.publishers(update.effective_user.id), t(lang(update), "register_hint"))


def ad_names(store: Store) -> dict:
    return {ad["id"]: ad_title(ad) for ad in store.list_ads()}


def publisher_names(store: Store) -> dict:
    return {p["id"]: p["name"] for p in store.publishers()}


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    c = ctx(context)
    user_id = update.effective_user.id
    lg = lang(update)
    admin = is_admin(context, user_id)
    campaigns = campaign_report(c.store, None if admin else user_id)
    lines = [t(lg, "campaigns_title")]
    if campaigns:
        for campaign in campaigns:
            lines.append(
                f"<b>{escape(campaign['title'])}</b> · {campaign['views']} 👁 · {campaign['clicks']} 👆 · {campaign['ctr']}% CTR"
            )
    else:
        lines.append(t(lg, "campaigns_empty"))
    lines.append(t(lg, "stars_line", n=c.store.stars(user_id)))
    if admin:
        lines.append(overview(c.store, t(lg, "all_adverts"), ad_names(c.store), by="ad_id", lang=lg))
    else:
        own = c.store.publishers(user_id)
        if own:
            lines.append("\n\n".join(overview(c.store, p["name"], ad_names(c.store), by="ad_id", publisher_id=p["id"], lang=lg) for p in own))
    markup = Markup([[Button(t(lg, "b_main_menu"), callback_data="menu")]])
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=markup)


async def send_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Daily summary for one chat, sent by the job queue."""
    job = context.job
    if job is None:
        return
    c = ctx(context)
    user_id = job.chat_id
    lg = "de" if job.data == "de" else "en"
    campaigns = campaign_report(c.store, user_id)
    stars = c.store.stars(user_id)
    lines = [("📊 <b>litfass Daily</b>" if lg == "en" else "📊 <b>litfass Tagesüberblick</b>")]
    if campaigns:
        for campaign in campaigns[:5]:
            lines.append(f"• {escape(campaign['title'])}: {campaign['views']} 👁 · {campaign['clicks']} 👆 · {campaign['ctr']}% CTR")
    else:
        lines.append("No campaigns yet." if lg == "en" else "Noch keine Kampagnen.")
    lines.append(f"{'⭐' if lg == 'en' else '⭐'} {stars} Stars")
    await context.bot.send_message(job.chat_id, "\n".join(lines), parse_mode=ParseMode.HTML)


async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if context.job_queue:
        context.job_queue.run_daily(send_digest, datetime.time(hour=9, minute=0), chat_id=user_id, data=lang(update), name=f"digest:{user_id}")
    await update.effective_message.reply_text(
        "Daily digest enabled — 09:00." if lang(update) == "en" else "Tagesüberblick aktiviert – 09:00."
    )


async def publishers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(context, update.effective_user.id):
        return
    await send_publishers(update, context, ctx(context).store.publishers(), t(lang(update), "nobody"))


async def send_publishers(update: Update, context: ContextTypes.DEFAULT_TYPE, publishers: list[dict], empty: str) -> None:
    if not publishers:
        await update.effective_message.reply_text(empty)
        return
    rows = [[Button(("⛔️ " if p["blocked"] else "") + p["name"][:40], callback_data=f"pub:{p['id']}:show")] for p in publishers]
    rows.append([Button(t(lang(update), "b_main_menu"), callback_data="menu")])
    await update.effective_message.reply_text(t(lang(update), "n_placements", n=len(publishers)), parse_mode=ParseMode.HTML, reply_markup=Markup(rows))


# Free-text input ----------------------------------------------------------------------------------

# What each free-text answer is asked with (text keys in texts.py)
PROMPTS = {"texts": "p_texts", "url": "p_url", "emoji": "p_emoji", "colors": "p_colors", "sched": "p_sched", "image": "p_image"}


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return
    kind, target = awaiting
    message = update.effective_message
    text = (message.text or "").strip()
    c = ctx(context)
    user_id = update.effective_user.id
    lg = lang(update)

    if kind == "pub_name":
        if not 2 <= len(text) <= 60:
            await message.reply_text(t(lg, "e_name"))
            return
        context.user_data["draft"] = {"name": text, "categories": []}
        context.user_data.pop("awaiting")
        rows = [[Button(label, callback_data=f"reg:kind:{key}")] for key, label in labels(KINDS, lg).items()]
        await message.reply_text(t(lg, "where"), reply_markup=Markup(rows))
        return

    if kind == "pub_rename":
        publisher = c.store.get_publisher(target)
        if not may_edit(context, user_id, publisher) or not 2 <= len(text) <= 60:
            await message.reply_text(t(lg, "e_name"))
            return
        c.store.update_publisher(target, name=text)
        context.user_data.pop("awaiting")
        card, markup = publisher_card(c, c.store.get_publisher(target), is_admin(context, user_id), lg)
        await message.reply_text(card, parse_mode=ParseMode.HTML, reply_markup=markup)
        return

    # Everything below edits adverts; their owner may edit them
    if kind != "new_url":
        ad = c.store.get_ad(target)
        if not ad or (ad.get("created_by") != user_id and not is_admin(context, user_id)):
            context.user_data.pop("awaiting", None)
            return

    if kind == "new_url":
        if not text.startswith("https://") or " " in text:
            await message.reply_text(t(lg, "e_https_retry"))
            return
        ad_id = c.store.create_ad(text, user_id)
        context.user_data["awaiting"] = ("texts", ad_id)
        await message.reply_text(t(lg, "now_texts") + t(lg, PROMPTS["texts"]), parse_mode=ParseMode.HTML)
        return

    ad = c.store.get_ad(target)
    if not ad:
        context.user_data.pop("awaiting", None)
        await message.reply_text(t(lg, "e_gone"))
        return

    error = apply_ad_input(c.store, ad, kind, text, lg)
    if error:
        await message.reply_text(error + t(lg, "e_retry"), parse_mode=ParseMode.HTML)
        return
    context.user_data.pop("awaiting", None)
    card, markup = ad_card(c.store.get_ad(target), lg)
    await message.reply_text(card, parse_mode=ParseMode.HTML, reply_markup=markup, disable_web_page_preview=True)


def apply_ad_input(store: Store, ad: dict, kind: str, text: str, lang: str = "en") -> str | None:
    """Stores one free-text answer; returns an error message when the input does not fit."""
    if kind == "texts":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) == 1 and lines[0].endswith(" -") and LANG.match(lines[0][:-2].strip()):
            store.delete_text(ad["id"], lines[0][:-2].strip())
            return None
        if len(lines) != 4 or not LANG.match(lines[0]):
            return t(lang, "e_four_lines")
        lang, title, body, cta = lines
        for field, value in (("title", title), ("body", body), ("cta", cta)):
            if len(value) > MAX_TEXT[field]:
                return t(lang, "e_too_long", field=t(lang, f"f_{field}"), max=MAX_TEXT[field])
        store.set_text(ad["id"], lang, title, body, cta)
        return None
    if kind == "url":
        if not text.startswith("https://") or " " in text:
            return t(lang, "e_https")
        store.update_ad(ad["id"], url=text)
        return None
    if kind == "emoji":
        if text != "-" and len(text) > 8:
            return t(lang, "e_emoji")
        store.update_ad(ad["id"], emoji=None if text == "-" else text)
        return None
    if kind == "colors":
        colors = text.split()
        if len(colors) != 3 or not all(HEX.match(color) for color in colors):
            return t(lang, "e_colors")
        style = {**ad["style"], "background": colors[0], "color": colors[1], "accent": colors[2]}
        store.update_ad(ad["id"], style=style)
        return None
    if kind == "sched":
        if text == "-":
            store.update_ad(ad["id"], start=None, end=None)
            return None
        parts = text.split()
        if len(parts) != 2:
            return t(lang, "e_two_dates")
        try:
            start, end = (None if part == "-" else date.fromisoformat(part).isoformat() for part in parts)
        except ValueError:
            return t(lang, "e_date")
        if start and end and end <= start:
            return t(lang, "e_end")
        store.update_ad(ad["id"], start=start, end=end)
        return None
    if kind == "image":
        if text == "-":
            store.update_ad(ad["id"], image_file_id=None, image_rev=ad["image_rev"] + 1)
            return None
        return t(lang, "e_photo")
    return t(lang, "e_unexpected")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    awaiting = context.user_data.get("awaiting")
    if not awaiting or awaiting[0] != "image" or not is_admin(context, update.effective_user.id):
        return
    c = ctx(context)
    ad = c.store.get_ad(awaiting[1])
    if not ad:
        return
    photo = update.effective_message.photo[-1]
    c.store.update_ad(ad["id"], image_file_id=photo.file_id, image_rev=ad["image_rev"] + 1)
    context.user_data.pop("awaiting", None)
    card, markup = ad_card(c.store.get_ad(ad["id"]), lang(update))
    await update.effective_message.reply_text(card, parse_mode=ParseMode.HTML, reply_markup=markup, disable_web_page_preview=True)


# Buttons ------------------------------------------------------------------------------------------


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""
    user_id = query.from_user.id
    c = ctx(context)
    lg = lang_of(query.from_user)

    async def show(text: str, markup: Markup | None = None) -> None:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup, disable_web_page_preview=True)

    async def ask(kind: str, target, prompt: str) -> None:
        context.user_data["awaiting"] = (kind, target)
        await query.message.reply_text(prompt, parse_mode=ParseMode.HTML)

    parts = data.split(":")

    # Main navigation
    if parts[0] == "menu":
        c = ctx(context)
        if len(parts) > 1 and parts[1] == "publishers":
            if not is_admin(context, user_id):
                await query.answer(t(lg, "admin_only"), show_alert=True)
                return
            await query.answer()
            await send_publishers(update, context, c.store.publishers(), t(lg, "nobody"))
            return
        if len(parts) > 1 and parts[1] == "stars":
            await query.answer()
            await send_stars_invoice(query.message, lg)
            return
        await query.answer()
        balance = c.store.stars(user_id)
        text = t(lg, "menu_title") + "\n" + t(lg, "stars_line", n=balance)
        await show(text, menu_markup(c, user_id, lg))
        return
    if data in ("campaigns", "newad", "stats", "ads"):
        await query.answer()
        c = ctx(context)
        admin = is_admin(context, user_id)
        if data == "newad":
            await ask("new_url", None, t(lg, "ask_new_url"))
        elif data == "stats":
            campaigns = campaign_report(c.store, None if admin else user_id)
            text = t(lg, "campaigns_title") + "\n" + (
                "\n".join(f"• {escape(camp['title'])}: {camp['views']} 👁 · {camp['clicks']} 👆 · {camp['ctr']}% CTR" for camp in campaigns)
                if campaigns
                else t(lg, "campaigns_empty")
            )
            await show(text, Markup([[Button(t(lg, "b_main_menu"), callback_data="menu")]]))
        elif data == "ads" and not admin:
            await show(*ads_list(c.store, lg, user_id))
        elif data == "ads":
            await show(*ads_list(c.store, lg))
        else:
            await show(*ads_list(c.store, lg, user_id))
        return

    # Registration of a new placement
    if parts[0] == "reg":
        draft = context.user_data.get("draft")
        if not draft:
            await query.answer(t(lg, "restart_register"), show_alert=True)
            return
        if parts[1] == "kind":
            draft["kind"] = parts[2]
        elif parts[1] == "cat":
            draft["categories"] = toggle(draft["categories"], parts[2])
        elif parts[1] == "done":
            publisher = c.store.create_publisher(user_id, draft["name"], draft.get("kind", "web"), draft["categories"])
            context.user_data.pop("draft", None)
            await query.answer(t(lg, "registered"))
            text, markup = publisher_card(c, publisher, is_admin(context, user_id), lg)
            await show(t(lg, "registered_card") + text, markup)
            return
        await query.answer()
        rows = check_rows(labels(CATEGORIES, lg), draft["categories"], "reg:cat")
        rows.append([Button(t(lg, "b_done"), callback_data="reg:done")])
        await show(t(lg, "pick_content", name=escape(draft["name"])), Markup(rows))
        return

    # Placements
    if parts[0] == "pub":
        publisher = c.store.get_publisher(int(parts[1]))
        if not may_edit(context, user_id, publisher):
            await query.answer(t(lg, "not_yours"), show_alert=True)
            return
        action = parts[2]
        admin = is_admin(context, user_id)
        if action == "cats":
            await query.answer()
            rows = check_rows(labels(CATEGORIES, lg), publisher["categories"], f"pub:{publisher['id']}:cat")
            rows.append([Button(t(lg, "b_done"), callback_data=f"pub:{publisher['id']}:show")])
            await show(t(lg, "what_content"), Markup(rows))
            return
        if action == "cat":
            c.store.update_publisher(publisher["id"], categories=toggle(publisher["categories"], parts[3]))
            publisher = c.store.get_publisher(publisher["id"])
            await query.answer()
            rows = check_rows(labels(CATEGORIES, lg), publisher["categories"], f"pub:{publisher['id']}:cat")
            rows.append([Button(t(lg, "b_done"), callback_data=f"pub:{publisher['id']}:show")])
            await query.edit_message_reply_markup(Markup(rows))
            return
        if action == "free":
            c.store.update_publisher(publisher["id"], allow_free=0 if publisher["allow_free"] else 1)
            await query.answer()
        elif action == "stats":
            await query.answer()
            back = Markup([[Button(t(lg, "b_back"), callback_data=f"pub:{publisher['id']}:show")]])
            await show(overview(c.store, publisher["name"], ad_names(c.store), by="ad_id", publisher_id=publisher["id"], lang=lg), back)
            return
        if action == "rename":
            await query.answer()
            await ask("pub_rename", publisher["id"], t(lg, "p_rename"))
            return
        if action == "key":
            c.store.rotate_key(publisher["id"])
            await query.answer(t(lg, "new_key"), show_alert=True)
        elif action == "del":
            await query.answer()
            await show(
                t(lg, "delete_pub", name=escape(publisher["name"])),
                Markup([[Button(t(lg, "b_delete"), callback_data=f"pub:{publisher['id']}:delyes"), Button(t(lg, "b_keep"), callback_data=f"pub:{publisher['id']}:show")]]),
            )
            return
        elif action == "delyes":
            c.store.delete_publisher(publisher["id"])
            await query.answer(t(lg, "deleted"))
            await show(t(lg, "deleted_full"))
            return
        elif action == "block" and admin:
            c.store.update_publisher(publisher["id"], blocked=0 if publisher["blocked"] else 1)
            await query.answer()
        else:
            await query.answer()
        text, markup = publisher_card(c, c.store.get_publisher(publisher["id"]), admin, lg)
        await show(text, markup)
        return

    if parts[0] != "ad":
        await query.answer()
        return
    ad = c.store.get_ad(parts[1])
    if not ad:
        await query.answer(t(lg, "e_gone"), show_alert=True)
        return
    if not is_admin(context, user_id) and ad.get("created_by") != user_id:
        await query.answer(t(lg, "not_yours"), show_alert=True)
        return
    action = parts[2]
    arg = parts[3] if len(parts) > 3 else None
    a = f"ad:{ad['id']}"

    if action in PROMPTS or action == "link":
        await query.answer()
        kind = "url" if action == "link" else action
        await ask(kind, ad["id"], t(lg, PROMPTS[kind]))
        return
    if action == "stats":
        await query.answer()
        back = Markup([[Button(t(lg, "b_back"), callback_data=f"{a}:show")]])
        await show(overview(c.store, ad_title(ad), publisher_names(c.store), by="publisher_id", ad_id=ad["id"], lang=lg), back)
        return
    if action == "live":
        if ad["paused"] and "en" not in ad["text"]:
            await query.answer(t(lg, "need_en"), show_alert=True)
            return
        c.store.update_ad(ad["id"], paused=0 if ad["paused"] else 1)
    elif action == "del":
        await query.answer()
        await show(
            t(lg, "delete_ad", name=escape(ad_title(ad))),
            Markup([[Button(t(lg, "b_delete"), callback_data=f"{a}:delyes"), Button(t(lg, "b_keep"), callback_data=f"{a}:show")]]),
        )
        return
    elif action == "delyes":
        c.store.delete_ad(ad["id"])
        await query.answer(t(lg, "deleted"))
        await show(*ads_list(c.store, lg))
        return
    elif action in ("cats", "cat"):
        if action == "cat":
            c.store.update_ad(ad["id"], categories=toggle(ad["categories"], arg))
            ad = c.store.get_ad(ad["id"])
        await query.answer()
        rows = check_rows(labels(CATEGORIES, lg), ad["categories"], f"{a}:cat")
        rows.append([Button(t(lg, "b_done"), callback_data=f"{a}:show")])
        await show(t(lg, "ad_content"), Markup(rows))
        return
    elif action in ("places", "pl"):
        if action == "pl":
            c.store.update_ad(ad["id"], placements=toggle(ad["placements"], arg))
            ad = c.store.get_ad(ad["id"])
        await query.answer()
        rows = check_rows(labels(PLACEMENTS, lg), ad["placements"], f"{a}:pl", per_row=1)
        rows.append([Button(t(lg, "b_done"), callback_data=f"{a}:show")])
        await show(t(lg, "ad_places"), Markup(rows))
        return
    elif action == "style":
        await query.answer()
        await show(t(lg, "ad_style"), style_keyboard(ad, lg))
        return
    elif action == "sty":
        variant = ad["style"].get("variant")
        style = {} if arg == "none" else dict(STYLE_PRESETS.get(arg, {}))
        if variant and arg != "none":
            style["variant"] = variant
        c.store.update_ad(ad["id"], style=style)
        await query.answer(t(lg, "style_set", name=arg))
        await query.edit_message_reply_markup(style_keyboard(c.store.get_ad(ad["id"]), lg))
        return
    elif action == "var" and arg in VARIANTS:
        c.store.update_ad(ad["id"], style={**ad["style"], "variant": arg})
        await query.answer(t(lg, "layout_set", name=labels(VARIANTS, lg)[arg]))
        await query.edit_message_reply_markup(style_keyboard(c.store.get_ad(ad["id"]), lg))
        return
    elif action == "weight":
        await query.answer()
        rows = [[Button(("✅ " if ad["weight"] == n else "") + str(n), callback_data=f"{a}:w:{n}") for n in (1, 2, 3, 5, 10)]]
        rows.append([Button(t(lg, "b_done"), callback_data=f"{a}:show")])
        await show(t(lg, "ad_weight"), Markup(rows))
        return
    elif action == "w" and arg and arg.isdigit():
        c.store.update_ad(ad["id"], weight=int(arg))
    await query.answer()
    text, markup = ad_card(c.store.get_ad(ad["id"]), lg)
    await show(text, markup)


async def stars_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sell a package of Stars that pays for paid advert campaigns."""
    await send_stars_invoice(update.effective_message, lang_of(update))


async def on_pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    ok = query.invoice_payload == "stars:package"
    await query.answer(ok=ok, error_message=None if ok else "Unknown product")


async def on_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment = update.message.successful_payment
    if payment.invoice_payload != "stars:package":
        return
    ctx(context).store.credit_stars(update.effective_user.id, payment.total_amount, payment.telegram_payment_charge_id)
    await update.effective_message.reply_text(
        f"+{payment.total_amount} Stars — " + ("ready for paid campaigns." if lang_of(update) == "en" else "bereit für bezahlte Anzeigen.")
    )


async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Paid campaigns: a one-time Stars activation fee and one Star per click, credited to the placement that showed the advert."
        if lang_of(update) == "en"
        else "Bezahlte Anzeigen: einmalige Stars-Aktivierung und ein Star pro Klick, gutgeschrieben an den Werbeplatz."
    )


async def paysupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Payment support: @militaernewskontakt" if lang_of(update) == "en" else "Zahlungssupport: @militaernewskontakt"
    )


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("update failed", exc_info=context.error)


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler(["start", "help", "menu"], start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler(["campaigns", "ads"], campaigns_command))
    app.add_handler(CommandHandler("newad", newad_command))
    app.add_handler(CommandHandler("register", register_command))
    app.add_handler(
        CommandHandler("post", post_command, filters=filters.ChatType.GROUPS | filters.ChatType.CHANNEL)
    )
    app.add_handler(CommandHandler("mine", mine_command))
    app.add_handler(CommandHandler("publishers", publishers_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("stars", stars_command))
    app.add_handler(CommandHandler("digest", digest_command))
    app.add_handler(CommandHandler("terms", terms_command))
    app.add_handler(CommandHandler(["paysupport", "support"], paysupport_command))
    app.add_handler(PreCheckoutQueryHandler(on_pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, on_text))
    app.add_error_handler(on_error)
