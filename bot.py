import os
import time
import asyncio
import tempfile
import threading
from datetime import datetime

from flask import Flask
from pymongo import MongoClient
from bson import ObjectId
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
# FLASK - RENDER WEB SERVICE
# =========================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "Advanced Thumbnail Bot is Running! 🚀"


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

thumbs = db["thumbnails"]


# =========================================================
# PYROGRAM
# =========================================================

bot = Client(
    "advanced_thumbnail_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# =========================================================
# USER STATE
# =========================================================

user_state = {}


# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(user_id):

    return user_id == ADMIN_ID


# =========================================================
# MAIN MENU
# =========================================================

def main_menu():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🖼️ Thumbnail Manager",
                callback_data="manager"
            )
        ],
        [
            InlineKeyboardButton(
                "📚 My Thumbnails",
                callback_data="list"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ Current Thumbnail",
                callback_data="current"
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
                "🗑️ Remove Current",
                callback_data="remove_current"
            )
        ]
    ])


# =========================================================
# THUMBNAIL MANAGER
# =========================================================

def manager_menu():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Add Thumbnail",
                callback_data="add"
            )
        ],
        [
            InlineKeyboardButton(
                "📚 Saved Thumbnails",
                callback_data="list"
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Change Thumbnail",
                callback_data="list"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ Set Default",
                callback_data="list"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑️ Remove Current",
                callback_data="remove_current"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="home"
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
        await message.reply_text(
            "❌ Admin only."
        )
        return

    await message.reply_text(
        "🎬 **Advanced Video Thumbnail Bot**\n\n"
        "Welcome Admin! 👋🏻\n\n"
        "🖼️ Set/manage your thumbnails\n"
        "📚 Save multiple thumbnails\n"
        "⭐ Select a default thumbnail\n"
        "📹 Send a video to apply it\n\n"
        "**Video caption will remain unchanged.**",
        reply_markup=main_menu()
    )


# =========================================================
# HELP
# =========================================================

@bot.on_message(
    filters.command("help")
)
async def help_command(client, message):

    if not is_admin(
        message.from_user.id
    ):
        return

    await message.reply_text(
        "📖 **Bot Help**\n\n"

        "➕ Add Thumbnail\n"
        "Save a new thumbnail.\n\n"

        "📚 My Thumbnails\n"
        "View all saved thumbnails.\n\n"

        "⭐ Current Thumbnail\n"
        "See selected thumbnail.\n\n"

        "🗑️ Remove Current\n"
        "Remove the active thumbnail.\n\n"

        "📹 Send Video\n"
        "Bot will upload the same video "
        "with the selected thumbnail.\n\n"

        "📊 Upload progress includes:\n"
        "• Percentage\n"
        "• Speed\n"
        "• Size\n"
        "• ETA\n"
        "• Elapsed time"
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
            "❌ Admin only!",
            show_alert=True
        )

        return


    data = query.data


    # =====================================================
    # HOME
    # =====================================================

    if data == "home":

        await query.message.edit_text(
            "🎬 **Advanced Thumbnail Bot**\n\n"
            "Choose an option:",
            reply_markup=main_menu()
        )

        await query.answer()


    # =====================================================
    # MANAGER
    # =====================================================

    elif data == "manager":

        await query.message.edit_text(
            "🖼️ **Thumbnail Manager**\n\n"
            "Manage your saved thumbnails:",
            reply_markup=manager_menu()
        )

        await query.answer()


    # =====================================================
    # ADD THUMBNAIL
    # =====================================================

    elif data == "add":

        user_state[
            query.from_user.id
        ] = {
            "state": "waiting_photo"
        }

        await query.message.reply_text(
            "➕ **Add Thumbnail**\n\n"
            "Please send the thumbnail image.\n\n"
            "Tip: JPG/JPEG works best."
        )

        await query.answer()


    # =====================================================
    # LIST
    # =====================================================

    elif data == "list":

        await show_thumbnail_list(
            query.message
        )

        await query.answer()


    # =====================================================
    # CURRENT
    # =====================================================

    elif data == "current":

        current = thumbs.find_one(
            {
                "is_current": True
            }
        )

        if not current:

            await query.message.reply_text(
                "⭐ No thumbnail is currently selected."
            )

        else:

            await client.send_photo(
                query.message.chat.id,
                current["file_id"],
                caption=(
                    "⭐ **Current Thumbnail**\n\n"
                    f"Name: `{current['name']}`"
                )
            )

        await query.answer()


    # =====================================================
    # PREVIEW
    # =====================================================

    elif data == "preview":

        current = thumbs.find_one(
            {
                "is_current": True
            }
        )

        if not current:

            await query.message.reply_text(
                "❌ No current thumbnail selected."
            )

        else:

            await client.send_photo(
                query.message.chat.id,
                current["file_id"],
                caption=(
                    "👀 **Thumbnail Preview**\n\n"
                    f"Name: `{current['name']}`\n"
                    "Status: ⭐ Active"
                )
            )

        await query.answer()


    # =====================================================
    # REMOVE CURRENT
    # =====================================================

    elif data == "remove_current":

        current = thumbs.find_one(
            {
                "is_current": True
            }
        )

        if not current:

            await query.message.reply_text(
                "❌ No current thumbnail."
            )

        else:

            thumbs.update_one(
                {
                    "_id": current["_id"]
                },
                {
                    "$set": {
                        "is_current": False
                    }
                }
            )

            await query.message.reply_text(
                "🗑️ **Current thumbnail removed.**"
            )

        await query.answer()


    # =====================================================
    # SELECT THUMBNAIL
    # =====================================================

    elif data.startswith("select:"):

        thumb_id = data.split(
            ":",
            1
        )[1]

        try:

            selected = thumbs.find_one(
                {
                    "_id": ObjectId(
                        thumb_id
                    )
                }
            )

        except Exception:

            selected = None


        if not selected:

            await query.answer(
                "❌ Thumbnail not found.",
                show_alert=True
            )

            return


        # Remove current status
        thumbs.update_many(
            {},
            {
                "$set": {
                    "is_current": False
                }
            }
        )


        # Set selected
        thumbs.update_one(
            {
                "_id": selected["_id"]
            },
            {
                "$set": {
                    "is_current": True
                }
            }
        )


        await query.message.reply_text(
            "⭐ **Thumbnail Changed Successfully!**\n\n"
            f"Selected: `{selected['name']}`"
        )

        await query.answer()


    # =====================================================
    # DELETE THUMBNAIL
    # =====================================================

    elif data.startswith("delete:"):

        thumb_id = data.split(
            ":",
            1
        )[1]

        try:

            result = thumbs.delete_one(
                {
                    "_id": ObjectId(
                        thumb_id
                    )
                }
            )

            if result.deleted_count:

                await query.message.reply_text(
                    "🗑️ **Thumbnail deleted successfully.**"
                )

            else:

                await query.message.reply_text(
                    "❌ Thumbnail not found."
                )

        except Exception:

            await query.message.reply_text(
                "❌ Could not delete thumbnail."
            )

        await query.answer()


    # =====================================================
    # DELETE CONFIRM
    # =====================================================

    elif data.startswith("confirm_delete:"):

        thumb_id = data.split(
            ":",
            1
        )[1]

        try:

            result = thumbs.delete_one(
                {
                    "_id": ObjectId(
                        thumb_id
                    )
                }
            )

            if result.deleted_count:

                await query.message.reply_text(
                    "✅ Thumbnail permanently deleted."
                )

            else:

                await query.message.reply_text(
                    "❌ Thumbnail not found."
                )

        except Exception:

            await query.message.reply_text(
                "❌ Delete failed."
            )

        await query.answer()


# =========================================================
# SHOW THUMBNAIL LIST
# =========================================================

async def show_thumbnail_list(
    message
):

    items = list(
        thumbs.find().sort(
            "_id",
            -1
        ).limit(50)
    )


    if not items:

        await message.reply_text(
            "📚 **My Thumbnails**\n\n"
            "No thumbnails saved yet.\n\n"
            "Use ➕ Add Thumbnail to create one.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "➕ Add Thumbnail",
                        callback_data="add"
                    )
                ]
            ])
        )

        return


    buttons = []


    for item in items:

        name = item.get(
            "name",
            "Unnamed"
        )

        active = " ⭐" if item.get(
            "is_current",
            False
        ) else ""


        buttons.append([
            InlineKeyboardButton(
                f"{name}{active}",
                callback_data=(
                    "select:" +
                    str(item["_id"])
                )
            )
        ])


        buttons.append([
            InlineKeyboardButton(
                f"🗑️ Delete {name}",
                callback_data=(
                    "confirm_delete:" +
                    str(item["_id"])
                )
            )
        ])


    buttons.append([
        InlineKeyboardButton(
            "➕ Add New",
            callback_data="add"
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 Back",
            callback_data="manager"
        )
    ])


    await message.reply_text(
        "📚 **Saved Thumbnails**\n\n"
        "Tap a thumbnail to make it active ⭐\n"
        "Then send your video.",
        reply_markup=InlineKeyboardMarkup(
            buttons
        )
    )


# =========================================================
# PHOTO HANDLER
# =========================================================

@bot.on_message(
    filters.photo
)
async def photo_handler(
    client,
    message
):

    if not is_admin(
        message.from_user.id
    ):
        return


    state = user_state.get(
        message.from_user.id
    )


    if not state:

        return


    if state.get(
        "state"
    ) != "waiting_photo":

        return


    # Save temporary state
    user_state[
        message.from_user.id
    ] = {
        "state": "waiting_name",
        "file_id": message.photo.file_id
    }


    await message.reply_text(
        "✅ **Thumbnail image received!**\n\n"
        "Now send a name for this thumbnail.\n\n"
        "Example:\n"
        "`Naruto`\n"
        "`Boruto`\n"
        "`Black Clover`"
    )


# =========================================================
# TEXT HANDLER
# =========================================================

@bot.on_message(
    filters.text
    & ~filters.command(
        ["start", "help"]
    )
)
async def text_handler(
    client,
    message
):

    if not is_admin(
        message.from_user.id
    ):
        return


    state = user_state.get(
        message.from_user.id
    )


    if not state:
        return


    if state.get(
        "state"
    ) != "waiting_name":

        return


    name = message.text.strip()


    if not name:

        await message.reply_text(
            "❌ Please send a valid name."
        )

        return


    file_id = state.get(
        "file_id"
    )


    # Remove previous current status
    thumbs.update_many(
        {},
        {
            "$set": {
                "is_current": False
            }
        }
    )


    # Save new thumbnail
    thumbs.insert_one({
        "name": name,
        "file_id": file_id,
        "is_current": True,
        "created_at": datetime.utcnow()
    })


    user_state.pop(
        message.from_user.id,
        None
    )


    await message.reply_text(
        "✅ **Thumbnail Saved Successfully!**\n\n"
        f"🖼️ Name: `{name}`\n"
        "⭐ Status: Active\n\n"
        "Now send a video 📹",
        reply_markup=main_menu()
    )


# =========================================================
# PROGRESS FORMAT
# =========================================================

def format_bytes(size):

    if size is None:
        return "0 B"

    size = float(size)

    for unit in [
        "B",
        "KB",
        "MB",
        "GB"
    ]:

        if size < 1024:
            return f"{size:.1f} {unit}"

        size /= 1024

    return f"{size:.1f} TB"


def format_time(seconds):

    if seconds is None:
        return "00:00"

    seconds = max(
        0,
        int(seconds)
    )

    hours = seconds // 3600

    minutes = (
        seconds % 3600
    ) // 60

    secs = seconds % 60


    if hours:

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    return (
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


def progress_bar(
    percentage,
    length=16
):

    filled = int(
        percentage / 100 * length
    )

    return (
        "█" * filled +
        "░" * (length - filled)
    )


# =========================================================
# PROGRESS MESSAGE
# =========================================================

class Progress:

    def __init__(
        self,
        message,
        action
    ):

        self.message = message
        self.action = action

        self.last_update = 0
        self.last_percent = -1
        self.start_time = time.monotonic()


    async def update(
        self,
        current,
        total
    ):

        if not total:
            return


        now = time.monotonic()

        percentage = (
            current / total
        ) * 100


        # Speed
        elapsed = (
            now - self.start_time
        )

        if elapsed <= 0:
            elapsed = 0.001


        speed = (
            current / elapsed
        )


        remaining = max(
            0,
            total - current
        )


        if speed > 0:

            eta = (
                remaining / speed
            )

        else:

            eta = 0


        # Don't spam Telegram API
        if (
            now - self.last_update < 2
            and int(percentage) != 100
        ):
            return


        self.last_update = now
        self.last_percent = int(
            percentage
        )


        text = (
            f"{self.action}\n\n"

            f"{progress_bar(percentage)} "
            f"**{percentage:.1f}%**\n\n"

            f"📦 **Size:** "
            f"{format_bytes(current)} / "
            f"{format_bytes(total)}\n"

            f"⚡ **Speed:** "
            f"{format_bytes(speed)}/s\n"

            f"⏱️ **ETA:** "
            f"{format_time(eta)}\n"

            f"🕐 **Elapsed:** "
            f"{format_time(elapsed)}"
        )


        try:

            await self.message.edit_text(
                text
            )

        except E
