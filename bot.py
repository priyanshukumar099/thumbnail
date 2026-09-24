import os
import asyncio
import tempfile

from flask import Flask
from pymongo import MongoClient
from PIL import Image

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton
)


# =========================================================
# CONFIG
# =========================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

MONGO_URI = os.environ["MONGO_URI"]
MONGO_DB = os.environ.get(
    "MONGO_DB",
    "thumbnail_bot"
)

ADMIN_ID = int(os.environ["ADMIN_ID"])


# =========================================================
# FLASK SERVER
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Thumbnail Bot is Running!"


def run_flask():
    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )


# =========================================================
# MONGODB
# =========================================================

mongo = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

db = mongo[MONGO_DB]

settings = db["settings"]


# =========================================================
# PYROGRAM
# =========================================================

bot = Client(
    "thumbnail_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id):

    return user_id == ADMIN_ID


# =========================================================
# KEYBOARD
# =========================================================

def main_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🖼️ Set Thumbnail",
                callback_data="set_thumbnail"
            )
        ],
        [
            InlineKeyboardButton(
                "👀 Preview",
                callback_data="preview"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑️ Clear Thumbnail",
                callback_data="clear_thumbnail"
            )
        ]
    ])


# =========================================================
# START
# =========================================================

@bot.on_message(
    filters.command("start")
)
async def start(client, message):

    if not is_admin(
        message.from_user.id
    ):
        return

    await message.reply_text(
        "🤖 **Video Thumbnail Bot**\n\n"
        "यह Bot केवल Video का Thumbnail "
        "change करेगा.\n\n"
        "🖼️ Thumbnail Set करें\n"
        "📹 फिर Video भेजें\n\n"
        "Video का original caption "
        "जैसा है वैसा ही रहेगा.",
        reply_markup=main_keyboard()
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

@bot.on_callback_query()
async def callback_handler(
    client,
    query
):

    if not is_admin(
        query.from_user.id
    ):

        await query.answer(
            "❌ Admin Only!",
            show_alert=True
        )

        return


    # -----------------------------------------
    # SET THUMBNAIL
    # -----------------------------------------

    if query.data == "set_thumbnail":

        await query.message.reply_text(
            "🖼️ अब वह **Photo भेजें** जिसे "
            "आप Video का Thumbnail बनाना चाहते हैं."
        )

        # Admin के लिए next photo को thumbnail
        # बनाने का temporary flag
        settings.update_one(
            {"_id": "main"},
            {
                "$set": {
                    "waiting_for_thumbnail": True
                }
            },
            upsert=True
        )

        await query.answer()


    # -----------------------------------------
    # PREVIEW
    # -----------------------------------------

    elif query.data == "preview":

        data = settings.find_one(
            {"_id": "main"}
        )

        thumbnail = None

        if data:
            thumbnail = data.get(
                "thumbnail"
            )

        if not thumbnail:

            await query.message.reply_text(
                "❌ अभी कोई Thumbnail Set नहीं है."
            )

            await query.answer()

            return

        await client.send_photo(
            chat_id=query.message.chat.id,
            photo=thumbnail,
            caption="🖼️ **Current Thumbnail**"
        )

        await query.answer()


    # -----------------------------------------
    # CLEAR
    # -----------------------------------------

    elif query.data == "clear_thumbnail":

        settings.update_one(
            {"_id": "main"},
            {
                "$unset": {
                    "thumbnail": ""
                },
                "$set": {
                    "waiting_for_thumbnail": False
                }
            },
            upsert=True
        )

        await query.message.reply_text(
            "🗑️ **Thumbnail Clear हो गया.**"
        )

        await query.answer()


# =========================================================
# PHOTO → SET THUMBNAIL
# =========================================================

@bot.on_message(
    filters.photo
)
async def thumbnail_handler(
    client,
    message
):

    if not is_admin(
        message.from_user.id
    ):
        return

    data = settings.find_one(
        {"_id": "main"}
    )

    waiting = False

    if data:
        waiting = data.get(
            "waiting_for_thumbnail",
            False
        )

    if not waiting:

        return

    # Telegram Photo File ID
    file_id = message.photo.file_id

    settings.update_one(
        {"_id": "main"},
        {
            "$set": {
                "thumbnail": file_id,
                "waiting_for_thumbnail": False
            }
        },
        upsert=True
    )

    await message.reply_text(
        "✅ **Thumbnail Successfully Saved!**\n\n"
        "अब अपना Video भेजें 📹"
    )


# =========================================================
# VIDEO HANDLER
# =========================================================

@bot.on_message(
    filters.video
)
async def video_handler(
    client,
    message
):

    if not is_admin(
        message.from_user.id
    ):
        return

    data = settings.find_one(
        {"_id": "main"}
    )

    if not data:

        await message.reply_text(
            "❌ पहले Thumbnail Set करें."
        )

        return

    thumbnail_id = data.get(
        "thumbnail"
    )

    if not thumbnail_id:

        await message.reply_text(
            "❌ पहले Thumbnail Set करें."
        )

        return


    status = await message.reply_text(
        "⏳ **Video Processing...**\n\n"
        "कृपया wait करें."
    )


    # Temporary files
    video_path = None
    thumb_path = None


    try:

        # =================================================
        # DOWNLOAD VIDEO
        # =================================================

        video_path = await client.download_media(
            message,
            file_name=tempfile.mktemp(
                suffix=".mp4"
            )
        )


        # =================================================
        # DOWNLOAD THUMBNAIL
        # =================================================

        original_thumb = await client.download_media(
            thumbnail_id,
            file_name=tempfile.mktemp(
                suffix=".jpg"
            )
        )


        # =================================================
        # CONVERT / RESIZE THUMBNAIL
        # =================================================

        thumb_path = tempfile.mktemp(
            suffix=".jpg"
        )

        with Image.open(
            original_thumb
        ) as img:

            img = img.convert("RGB")

            # Telegram thumbnail friendly size
            img.thumbnail(
                (320, 320)
            )

            img.save(
                thumb_path,
                "JPEG",
                quality=85,
                optimize=True
            )


        # =================================================
        # ORIGINAL CAPTION
        # =================================================

        original_caption = (
            message.caption
            if message.caption
            else None
        )


        # =================================================
        # SEND VIDEO WITH THUMBNAIL
        # =================================================

        await client.send_video(
            chat_id=message.chat.id,
            video=video_path,

            # Original caption remains unchanged
            caption=original_caption,

            # Custom thumbnail
            thumb=thumb_path,

            # Keep video information
            duration=message.video.duration,
            width=message.video.width,
            height=message.video.height,

            supports_streaming=True
        )


        await status.delete()


    except Exception as e:

        await status.edit_text(
            "❌ **Thumbnail लगाने में Error आया.**\n\n"
            f"`{str(e)}`"
        )


    finally:

        # =================================================
        # CLEAN TEMP FILES
        # =================================================

        for path in [
            video_path,
            thumb_path,
            original_thumb if "original_thumb" in locals() else None
        ]:

            if path:

                try:

                    if os.path.exists(path):
                        os.remove(path)

                except Exception:
                    pass


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    # Start Flask
    flask_thread = asyncio.get_event_loop()

    import threading

    threading.Thread(
        target=run_flask,
        daemon=True
    ).start()


    print(
        "🤖 Video Thumbnail Bot Started!"
    )

    bot.run()
