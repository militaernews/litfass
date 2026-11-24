"""The Telegram side: admins manage adverts, anyone can register a place that shows them.

Free-text answers (links, texts, colours, dates) are collected through a per-user "awaiting" state:
a button sets what the next message means, the text handler fills it in.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from html import escape

from telegram import InlineKeyboardButton as Button
from telegram import InlineKeyboardMarkup as Markup
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from litfass_server.feed import CATEGORIES, KINDS, PLACEMENTS, STYLE_PRESETS, VARIANTS
from litfass_server.stats import overview
from litfass_server.store import Store

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


def ad_card(ad: dict) -> tuple[str, Markup]:
    status = "⏸ paused" if ad["paused"] else "🟢 live"
    text = ad["text"].get("en")
    preview = (
        f"<i>Anzeige</i>\n{escape(ad['emoji'] or '')} <b>{escape(text['title'])}</b>\n{escape(text['body'])}\n[{escape(text['cta'])}]"
        if text
        else "<i>No English text yet: tap 🌐 Texts.</i>"
    )
    style = ad["style"]
    style_line = ", ".join(f"{k} {v}" for k, v in style.items()) if style else "default"
    schedule = f"{ad['start'] or '…'} → {ad['end'] or '…'}" if ad["start"] or ad["end"] else "always"
    lines = [
        preview,
        "",
        f"<b>Ad</b> <code>{ad['id']}</code> · {status} · weight {ad['weight']}",
        f"🔗 {escape(ad['url'])}",
        f"🌐 {', '.join(ad['text']) or '–'} · 🖼 {'yes' if ad['image_file_id'] else 'no'}",
        f"🗂 {', '.join(ad['categories']) or 'all content'}",
        f"📍 {', '.join(ad['placements']) or 'all placements'}",
        f"🎨 {escape(style_line)}",
        f"📅 {schedule}",
    ]
    a = f"ad:{ad['id']}"
    markup = Markup(
        [
            [
                Button("⏸ Pause" if not ad["paused"] else "▶️ Go live", callback_data=f"{a}:live"),
                Button("🗑 Delete", callback_data=f"{a}:del"),
            ],
            [
                Button("🌐 Texts", callback_data=f"{a}:texts"),
                Button("🔗 Link", callback_data=f"{a}:link"),
                Button("😀 Emoji", callback_data=f"{a}:emoji"),
            ],
            [
                Button("🗂 Content", callback_data=f"{a}:cats"),
                Button("📍 Placements", callback_data=f"{a}:places"),
                Button("🎨 Style", callback_data=f"{a}:style"),
            ],
            [
                Button("⚖️ Weight", callback_data=f"{a}:weight"),
                Button("📅 Schedule", callback_data=f"{a}:sched"),
                Button("🖼 Image", callback_data=f"{a}:image"),
            ],
            [Button("📊 Stats", callback_data=f"{a}:stats"), Button("⬅️ All ads", callback_data="ads")],
        ]
    )
    return "\n".join(lines), markup


def ads_list(store: Store) -> tuple[str, Markup]:
    ads = store.list_ads()
    rows = [[Button(("⏸ " if ad["paused"] else "🟢 ") + ad_title(ad)[:40], callback_data=f"ad:{ad['id']}:show")] for ad in ads]
    rows.append([Button("➕ New ad", callback_data="newad"), Button("📊 Stats", callback_data="stats")])
    return (f"<b>{len(ads)} ads</b>" if ads else "No ads yet."), Markup(rows)


def style_keyboard(ad: dict) -> Markup:
    a = f"ad:{ad['id']}"
    presets = [Button(name, callback_data=f"{a}:sty:{name}") for name in STYLE_PRESETS]
    current = ad["style"].get("variant", "card")
    variants = [Button(("✅ " if key == current else "") + label, callback_data=f"{a}:var:{key}") for key, label in VARIANTS.items()]
    return Markup(
        [
            presets[:3],
            presets[3:],
            variants,
            [Button("🎨 Own colours", callback_data=f"{a}:colors"), Button("↺ Reset", callback_data=f"{a}:sty:none")],
            [Button("✓ Done", callback_data=f"{a}:show")],
        ]
    )


# Publisher cards ----------------------------------------------------------------------------------


def feed_url(c: Ctx, publisher: dict) -> str:
    return f"{c.public_url}/v1/feed/{publisher['key']}"


def publisher_card(c: Ctx, publisher: dict, admin: bool) -> tuple[str, Markup]:
    cats = ", ".join(CATEGORIES.get(k, k) for k in publisher["categories"]) or "everything"
    lines = [
        f"<b>{escape(publisher['name'])}</b> · {KINDS.get(publisher['kind'], publisher['kind'])}",
        f"Content: {cats}",
        "⛔️ blocked" if publisher["blocked"] else "",
        "",
        "Feed URL (keep it to yourself, it identifies your placement):",
        f"<code>{escape(feed_url(c, publisher))}</code>",
        "",
        "Web: <code>fetchFeed(url)</code> from <code>@militaernews/litfass</code>, bots: the <code>litfass</code> Python package.",
        "Adverts must stay labelled as adverts (e.g. „Anzeige“).",
    ]
    p = f"pub:{publisher['id']}"
    rows = [
        [Button("🗂 Content", callback_data=f"{p}:cats"), Button("✏️ Rename", callback_data=f"{p}:rename")],
        [Button("🔑 New key", callback_data=f"{p}:key"), Button("🗑 Delete", callback_data=f"{p}:del")],
        [Button("📊 Stats", callback_data=f"{p}:stats")],
    ]
    if admin:
        rows.append([Button("✅ Unblock" if publisher["blocked"] else "⛔️ Block", callback_data=f"{p}:block")])
    return "\n".join(line for line in lines if line is not None), Markup(rows)


def may_edit(context: ContextTypes.DEFAULT_TYPE, user_id: int, publisher: dict | None) -> bool:
    return bool(publisher) and (publisher["owner_id"] == user_id or is_admin(context, user_id))


# Commands -----------------------------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = [
        "<b>litfass</b>: house adverts for websites, Mini Apps, bots and channels.",
        "",
        "/register – show adverts in your site, bot or channel",
        "/mine – your placements and their feed URLs",
        "/cancel – stop the current input",
    ]
    if is_admin(context, update.effective_user.id):
        lines += ["", "<b>Admin</b>", "/ads – manage adverts", "/newad – create an advert", "/publishers – all placements", "/stats – how the adverts are doing"]
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("awaiting", None)
    context.user_data.pop("draft", None)
    await update.effective_message.reply_text("Cancelled.")


async def ads_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(context, update.effective_user.id):
        return
    text, markup = ads_list(ctx(context).store)
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def newad_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(context, update.effective_user.id):
        return
    context.user_data["awaiting"] = ("new_url", None)
    await update.effective_message.reply_text("Send the link the advert leads to (https://…).")


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting"] = ("pub_name", None)
    await update.effective_message.reply_text("What is the name of your website, bot or channel?")


async def mine_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_publishers(update, context, ctx(context).store.publishers(update.effective_user.id), "/register to add one.")


def ad_names(store: Store) -> dict:
    return {ad["id"]: ad_title(ad) for ad in store.list_ads()}


def publisher_names(store: Store) -> dict:
    return {p["id"]: p["name"] for p in store.publishers()}


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    c = ctx(context)
    user_id = update.effective_user.id
    if is_admin(context, user_id):
        text = overview(c.store, "All adverts", ad_names(c.store), by="ad_id")
    else:
        own = c.store.publishers(user_id)
        if not own:
            await update.effective_message.reply_text("/register a placement first.")
            return
        text = "\n\n".join(overview(c.store, p["name"], ad_names(c.store), by="ad_id", publisher_id=p["id"]) for p in own)
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def publishers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(context, update.effective_user.id):
        return
    await send_publishers(update, context, ctx(context).store.publishers(), "Nobody registered yet.")


async def send_publishers(update: Update, context: ContextTypes.DEFAULT_TYPE, publishers: list[dict], empty: str) -> None:
    if not publishers:
        await update.effective_message.reply_text(empty)
        return
    rows = [[Button(("⛔️ " if p["blocked"] else "") + p["name"][:40], callback_data=f"pub:{p['id']}:show")] for p in publishers]
    await update.effective_message.reply_text(f"<b>{len(publishers)} placements</b>", parse_mode=ParseMode.HTML, reply_markup=Markup(rows))


# Free-text input ----------------------------------------------------------------------------------

PROMPTS = {
    "texts": (
        "Send the language code on the first line (en, de, ru, …), then title, text and button label on one line each.\n"
        "Example:\n<code>de\nUnser Kanal\nTäglich aktuell.\nKanal öffnen</code>\n\n"
        "To remove a language send only <code>de -</code>."
    ),
    "url": "Send the new link (https://…).",
    "emoji": "Send one emoji, or - to remove it.",
    "colors": "Send three colours: background, text and accent, e.g. <code>#14161a #f5f5f5 #e5484d</code>",
    "sched": "Send start and end as <code>2026-12-01 2027-01-07</code>; use - for an open side (<code>- 2027-01-07</code>), or just - to run always. The end day is not included.",
    "image": "Send a photo, or - to remove the image.",
}


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return
    kind, target = awaiting
    message = update.effective_message
    text = (message.text or "").strip()
    c = ctx(context)
    user_id = update.effective_user.id

    if kind == "pub_name":
        if not 2 <= len(text) <= 60:
            await message.reply_text("Please send a name between 2 and 60 characters.")
            return
        context.user_data["draft"] = {"name": text, "categories": []}
        context.user_data.pop("awaiting")
        rows = [[Button(label, callback_data=f"reg:kind:{key}")] for key, label in KINDS.items()]
        await message.reply_text("Where will the adverts appear?", reply_markup=Markup(rows))
        return

    if kind == "pub_rename":
        publisher = c.store.get_publisher(target)
        if not may_edit(context, user_id, publisher) or not 2 <= len(text) <= 60:
            await message.reply_text("Please send a name between 2 and 60 characters.")
            return
        c.store.update_publisher(target, name=text)
        context.user_data.pop("awaiting")
        card, markup = publisher_card(c, c.store.get_publisher(target), is_admin(context, user_id))
        await message.reply_text(card, parse_mode=ParseMode.HTML, reply_markup=markup)
        return

    # Everything below edits adverts
    if not is_admin(context, user_id):
        context.user_data.pop("awaiting", None)
        return

    if kind == "new_url":
        if not text.startswith("https://") or " " in text:
            await message.reply_text("That is not an https:// link. Try again or /cancel.")
            return
        ad_id = c.store.create_ad(text, user_id)
        context.user_data["awaiting"] = ("texts", ad_id)
        await message.reply_text("Now the texts. " + PROMPTS["texts"], parse_mode=ParseMode.HTML)
        return

    ad = c.store.get_ad(target)
    if not ad:
        context.user_data.pop("awaiting", None)
        await message.reply_text("That advert no longer exists.")
        return

    error = apply_ad_input(c.store, ad, kind, text)
    if error:
        await message.reply_text(error + " Try again or /cancel.", parse_mode=ParseMode.HTML)
        return
    context.user_data.pop("awaiting", None)
    card, markup = ad_card(c.store.get_ad(target))
    await message.reply_text(card, parse_mode=ParseMode.HTML, reply_markup=markup, disable_web_page_preview=True)


def apply_ad_input(store: Store, ad: dict, kind: str, text: str) -> str | None:
    """Stores one free-text answer; returns an error message when the input does not fit."""
    if kind == "texts":
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) == 1 and lines[0].endswith(" -") and LANG.match(lines[0][:-2].strip()):
            store.delete_text(ad["id"], lines[0][:-2].strip())
            return None
        if len(lines) != 4 or not LANG.match(lines[0]):
            return "I need four lines: language, title, text, button label."
        lang, title, body, cta = lines
        for field, value in (("title", title), ("body", body), ("cta", cta)):
            if len(value) > MAX_TEXT[field]:
                return f"The {field} is too long (at most {MAX_TEXT[field]} characters)."
        store.set_text(ad["id"], lang, title, body, cta)
        return None
    if kind == "url":
        if not text.startswith("https://") or " " in text:
            return "That is not an https:// link."
        store.update_ad(ad["id"], url=text)
        return None
    if kind == "emoji":
        if text != "-" and len(text) > 8:
            return "Send a single emoji."
        store.update_ad(ad["id"], emoji=None if text == "-" else text)
        return None
    if kind == "colors":
        colors = text.split()
        if len(colors) != 3 or not all(HEX.match(color) for color in colors):
            return "Send three colours like <code>#14161a #f5f5f5 #e5484d</code>."
        style = {**ad["style"], "background": colors[0], "color": colors[1], "accent": colors[2]}
        store.update_ad(ad["id"], style=style)
        return None
    if kind == "sched":
        if text == "-":
            store.update_ad(ad["id"], start=None, end=None)
            return None
        parts = text.split()
        if len(parts) != 2:
            return "Send two dates (or - for an open side)."
        try:
            start, end = (None if part == "-" else date.fromisoformat(part).isoformat() for part in parts)
        except ValueError:
            return "Dates look like 2026-12-01."
        if start and end and end <= start:
            return "The end has to be after the start."
        store.update_ad(ad["id"], start=start, end=end)
        return None
    if kind == "image":
        if text == "-":
            store.update_ad(ad["id"], image_file_id=None, image_rev=ad["image_rev"] + 1)
            return None
        return "Send a photo (or - to remove the image)."
    return "Unexpected input."


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
    card, markup = ad_card(c.store.get_ad(ad["id"]))
    await update.effective_message.reply_text(card, parse_mode=ParseMode.HTML, reply_markup=markup, disable_web_page_preview=True)


# Buttons ------------------------------------------------------------------------------------------


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""
    user_id = query.from_user.id
    c = ctx(context)

    async def show(text: str, markup: Markup | None = None) -> None:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup, disable_web_page_preview=True)

    async def ask(kind: str, target, prompt: str) -> None:
        context.user_data["awaiting"] = (kind, target)
        await query.message.reply_text(prompt, parse_mode=ParseMode.HTML)

    parts = data.split(":")

    # Registration of a new placement
    if parts[0] == "reg":
        draft = context.user_data.get("draft")
        if not draft:
            await query.answer("Start again with /register.", show_alert=True)
            return
        if parts[1] == "kind":
            draft["kind"] = parts[2]
        elif parts[1] == "cat":
            draft["categories"] = toggle(draft["categories"], parts[2])
        elif parts[1] == "done":
            publisher = c.store.create_publisher(user_id, draft["name"], draft.get("kind", "web"), draft["categories"])
            context.user_data.pop("draft", None)
            await query.answer("Registered")
            text, markup = publisher_card(c, publisher, is_admin(context, user_id))
            await show("✅ Registered.\n\n" + text, markup)
            return
        await query.answer()
        rows = check_rows(CATEGORIES, draft["categories"], "reg:cat")
        rows.append([Button("✓ Done", callback_data="reg:done")])
        await show(
            f"<b>{escape(draft['name'])}</b>\nWhat kind of content do you publish? Pick all that fit; adverts are chosen to match. "
            "Pick none to take every advert.",
            Markup(rows),
        )
        return

    # Placements
    if parts[0] == "pub":
        publisher = c.store.get_publisher(int(parts[1]))
        if not may_edit(context, user_id, publisher):
            await query.answer("Not yours.", show_alert=True)
            return
        action = parts[2]
        admin = is_admin(context, user_id)
        if action == "cats":
            await query.answer()
            rows = check_rows(CATEGORIES, publisher["categories"], f"pub:{publisher['id']}:cat")
            rows.append([Button("✓ Done", callback_data=f"pub:{publisher['id']}:show")])
            await show("What kind of content do you publish?", Markup(rows))
            return
        if action == "cat":
            c.store.update_publisher(publisher["id"], categories=toggle(publisher["categories"], parts[3]))
            publisher = c.store.get_publisher(publisher["id"])
            await query.answer()
            rows = check_rows(CATEGORIES, publisher["categories"], f"pub:{publisher['id']}:cat")
            rows.append([Button("✓ Done", callback_data=f"pub:{publisher['id']}:show")])
            await query.edit_message_reply_markup(Markup(rows))
            return
        if action == "stats":
            await query.answer()
            back = Markup([[Button("⬅️ Back", callback_data=f"pub:{publisher['id']}:show")]])
            await show(overview(c.store, publisher["name"], ad_names(c.store), by="ad_id", publisher_id=publisher["id"]), back)
            return
        if action == "rename":
            await query.answer()
            await ask("pub_rename", publisher["id"], "Send the new name.")
            return
        if action == "key":
            c.store.rotate_key(publisher["id"])
            await query.answer("New key: the old feed URL stops working.", show_alert=True)
        elif action == "del":
            await query.answer()
            await show(
                f"Delete <b>{escape(publisher['name'])}</b>? Its feed URL stops working.",
                Markup([[Button("🗑 Delete", callback_data=f"pub:{publisher['id']}:delyes"), Button("Keep", callback_data=f"pub:{publisher['id']}:show")]]),
            )
            return
        elif action == "delyes":
            c.store.delete_publisher(publisher["id"])
            await query.answer("Deleted")
            await show("Deleted.")
            return
        elif action == "block" and admin:
            c.store.update_publisher(publisher["id"], blocked=0 if publisher["blocked"] else 1)
            await query.answer()
        else:
            await query.answer()
        text, markup = publisher_card(c, c.store.get_publisher(publisher["id"]), admin)
        await show(text, markup)
        return

    # Everything below is for admins
    if not is_admin(context, user_id):
        await query.answer()
        return

    if data == "ads":
        await query.answer()
        await show(*ads_list(c.store))
        return
    if data == "stats":
        await query.answer()
        await show(overview(c.store, "All adverts", ad_names(c.store), by="ad_id"), Markup([[Button("⬅️ All ads", callback_data="ads")]]))
        return
    if data == "newad":
        await query.answer()
        await ask("new_url", None, "Send the link the advert leads to (https://…).")
        return

    if parts[0] != "ad":
        await query.answer()
        return
    ad = c.store.get_ad(parts[1])
    if not ad:
        await query.answer("That advert no longer exists.", show_alert=True)
        return
    action = parts[2]
    arg = parts[3] if len(parts) > 3 else None
    a = f"ad:{ad['id']}"

    if action in PROMPTS or action == "link":
        await query.answer()
        kind = "url" if action == "link" else action
        await ask(kind, ad["id"], PROMPTS[kind])
        return
    if action == "stats":
        await query.answer()
        back = Markup([[Button("⬅️ Back", callback_data=f"{a}:show")]])
        await show(overview(c.store, ad_title(ad), publisher_names(c.store), by="publisher_id", ad_id=ad["id"]), back)
        return
    if action == "live":
        if ad["paused"] and "en" not in ad["text"]:
            await query.answer("Add an English text first.", show_alert=True)
            return
        c.store.update_ad(ad["id"], paused=0 if ad["paused"] else 1)
    elif action == "del":
        await query.answer()
        await show(
            f"Delete the advert <b>{escape(ad_title(ad))}</b>?",
            Markup([[Button("🗑 Delete", callback_data=f"{a}:delyes"), Button("Keep", callback_data=f"{a}:show")]]),
        )
        return
    elif action == "delyes":
        c.store.delete_ad(ad["id"])
        await query.answer("Deleted")
        await show(*ads_list(c.store))
        return
    elif action in ("cats", "cat"):
        if action == "cat":
            c.store.update_ad(ad["id"], categories=toggle(ad["categories"], arg))
            ad = c.store.get_ad(ad["id"])
        await query.answer()
        rows = check_rows(CATEGORIES, ad["categories"], f"{a}:cat")
        rows.append([Button("✓ Done", callback_data=f"{a}:show")])
        await show("Which content does this advert fit? None means every placement.", Markup(rows))
        return
    elif action in ("places", "pl"):
        if action == "pl":
            c.store.update_ad(ad["id"], placements=toggle(ad["placements"], arg))
            ad = c.store.get_ad(ad["id"])
        await query.answer()
        rows = check_rows(PLACEMENTS, ad["placements"], f"{a}:pl", per_row=1)
        rows.append([Button("✓ Done", callback_data=f"{a}:show")])
        await show("Where may this advert appear? None means everywhere.", Markup(rows))
        return
    elif action == "style":
        await query.answer()
        await show("Pick a colour preset and a layout, or set your own colours.", style_keyboard(ad))
        return
    elif action == "sty":
        variant = ad["style"].get("variant")
        style = {} if arg == "none" else dict(STYLE_PRESETS.get(arg, {}))
        if variant and arg != "none":
            style["variant"] = variant
        c.store.update_ad(ad["id"], style=style)
        await query.answer(f"Style: {arg}")
        await query.edit_message_reply_markup(style_keyboard(c.store.get_ad(ad["id"])))
        return
    elif action == "var" and arg in VARIANTS:
        c.store.update_ad(ad["id"], style={**ad["style"], "variant": arg})
        await query.answer(f"Layout: {arg}")
        await query.edit_message_reply_markup(style_keyboard(c.store.get_ad(ad["id"])))
        return
    elif action == "weight":
        await query.answer()
        rows = [[Button(("✅ " if ad["weight"] == n else "") + str(n), callback_data=f"{a}:w:{n}") for n in (1, 2, 3, 5, 10)]]
        rows.append([Button("✓ Done", callback_data=f"{a}:show")])
        await show("How often should this advert come up compared to the others?", Markup(rows))
        return
    elif action == "w" and arg and arg.isdigit():
        c.store.update_ad(ad["id"], weight=int(arg))
    await query.answer()
    text, markup = ad_card(c.store.get_ad(ad["id"]))
    await show(text, markup)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("update failed", exc_info=context.error)


def register_handlers(app: Application) -> None:
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("ads", ads_command))
    app.add_handler(CommandHandler("newad", newad_command))
    app.add_handler(CommandHandler("register", register_command))
    app.add_handler(CommandHandler("mine", mine_command))
    app.add_handler(CommandHandler("publishers", publishers_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, on_text))
    app.add_error_handler(on_error)
