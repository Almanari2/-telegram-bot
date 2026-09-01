import os
import re
import tempfile
import asyncio
from pathlib import Path

import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

CHANNELS = [
    ("القناة الأولى", "@Departing19", "https://t.me/Departing19"),
    ("القناة الثانية", "@doamoh2", "https://t.me/doamoh2"),
    ("القناة الثالثة", "@O_R_not", "https://t.me/O_R_not"),
]


async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    for name, username, link in CHANNELS:
        try:
            member = await context.bot.get_chat_member(
                chat_id=username,
                user_id=user.id
            )

            if member.status in ["left", "kicked"]:
                return False

        except Exception:
            return False

    return True


async def subscription_message(update: Update):
    buttons = []

    for name, username, link in CHANNELS:
        buttons.append([
            InlineKeyboardButton(
                f"📢 الاشتراك في {name}",
                url=link
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "✅ تحقّق من الاشتراك",
            callback_data="check_subscription"
        )
    ])

    await update.message.reply_text(
        "🔒 يجب الاشتراك في القنوات الثلاث أولاً.\n\n"
        "بعد الاشتراك اضغط «تحقّق من الاشتراك» ثم أرسل رابط الفيديو.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribed = await check_subscription(update, context)

    if not subscribed:
        await subscription_message(update)
        return

    await update.message.reply_text(
        "👋 أهلاً بك!\n\n"
        "🎬 أرسل رابط فيديو من TikTok أو Instagram أو Facebook "
        "وسأحاول تنزيله لك."
    )


def clean_url(text):
    match = re.search(r"https?://\S+", text)
    return match.group(0) if match else None


def download_video(url, folder):
    output = str(Path(folder) / "video.%(ext)s")

    options = {
        "outtmpl": output,
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "max_filesize": 49 * 1024 * 1024,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([url])

    files = list(Path(folder).glob("video.*"))
    return files[0] if files else None


async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribed = await check_subscription(update, context)

    if not subscribed:
        await subscription_message(update, context)
        return

    url = clean_url(update.message.text)

    if not url:
        await update.message.reply_text(
            "❌ أرسل رابط فيديو صحيح."
        )
        return

    msg = await update.message.reply_text(
        "⏳ جاري تحميل الفيديو..."
    )

    try:
        with tempfile.TemporaryDirectory() as folder:
            video = await asyncio.to_thread(
                download_video,
                url,
                folder
            )

            if not video or not video.exists():
                await msg.edit_text(
                    "❌ لم أستطع تنزيل الفيديو."
                )
                return

            await msg.edit_text(
                "📤 جاري إرسال الفيديو..."
            )

            with open(video, "rb") as file:
                await update.message.reply_video(
                    video=file,
                    supports_streaming=True,
                    caption="✅ تم التنزيل"
                )

            await msg.delete()

    except Exception as e:
        print("ERROR:", e)
        await msg.edit_text(
            "❌ حدث خطأ أثناء تحميل الفيديو.\n"
            "تأكد من أن الرابط عام وصحيح."
        )


async def check_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    all_subscribed = True

    for name, username, link in CHANNELS:
        try:
            member = await context.bot.get_chat_member(
                chat_id=username,
                user_id=user.id
            )

            if member.status in ["left", "kicked"]:
                all_subscribed = False

        except Exception:
            all_subscribed = False

    if all_subscribed:
        await query.edit_message_text(
            "✅ تم التحقق من اشتراكك!\n\n"
            "🎬 الآن أرسل رابط الفيديو."
        )
    else:
        await query.answer(
            "❌ لم تشترك في جميع القنوات.",
            show_alert=True
        )


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 البوت يعمل بنجاح!")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN غير موجود في Environment Variables")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("health", health))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url)
    )

    app.add_handler(
        __import__("telegram").ext.CallbackQueryHandler(
            check_button,
            pattern="^check_subscription$"
        )
    )

    print("BOT IS RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
