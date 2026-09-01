import os
import re
import tempfile
import asyncio
from pathlib import Path

import yt_dlp
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك!\n\n"
        "أرسل رابط الفيديو من TikTok أو Instagram أو Facebook أو Snapchat "
        "وسأحاول تنزيله لك. 🎬"
    )


def clean_url(text):
    match = re.search(r"https?://\S+", text)
    return match.group(0) if match else None


def download_video(url, folder):
    output = str(Path(folder) / "video.%(ext)s")

    options = {
        "outtmpl": output,
        "format": "best[ext=mp4]/best",
        "merge_output_format": "mp4",
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
    url = clean_url(update.message.text)

    if not url:
        await update.message.reply_text("❌ أرسل رابط فيديو صحيح.")
        return

    msg = await update.message.reply_text("⏳ جاري تنزيل الفيديو...")

    try:
        with tempfile.TemporaryDirectory() as folder:
            video = await asyncio.to_thread(download_video, url, folder)

            if not video or not video.exists():
                await msg.edit_text("❌ لم أستطع تنزيل هذا الفيديو.")
                return

            await msg.edit_text("📤 جاري إرسال الفيديو...")

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
            "❌ حدث خطأ أثناء التنزيل.\n"
            "تأكد أن الرابط عام ويؤدي إلى فيديو."
        )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url)
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
