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


@app.route("/health")
def health():
    return "OK"


def run_flask():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
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

    return (
        user_id == ADMIN_ID
    )


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
# MANAGER MENU
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
# START COMMAND
# =========================================================

@bot.on_message(
    filters.command("start")
)
async def start(
    client,
    message
):

    if not is_admin(
        message.from_user.id
    ):

        await message.reply_text(
            "❌ **Admin Only**\n\n"
            "This bot is private."
        )

        return


    await message.reply_text(

        "🎬 **Advanced Thumbnail Bot**\n\n"

        "Welcome Admin! 👋🏻\n\n"

        "🖼️ Manage multiple thumbnails\n"
        "⭐ Select default thumbnail\n"
        "🔄 Change thumbnail anytime\n"
        "👀 Preview thumbnail\n"
        "🗑️ Remove/delete thumbnails\n"
        "📹 Send video to apply thumbnail\n\n"

        "📝 **Original video caption will remain unchanged.**\n\n"

        "Choose an option below 👇",

        reply_markup=main_menu()

    )


# =========================================================
# HELP
# =========================================================

@bot.on_message(
    filters.command("help")
)
async def help_command(
    client,
    message
):

    if not is_admin(
        message.from_user.id
    ):

        return


    await message.reply_text(

        "📖 **Bot Help**\n\n"

        "➕ **Add Thumbnail**\n"
        "Save a new thumbnail.\n\n"

        "📚 **Saved Thumbnails**\n"
        "View all saved thumbnails.\n\n"

        "⭐ **Select Thumbnail**\n"
        "Choose the thumbnail that will be used.\n\n"

        "👀 **Preview**\n"
        "View your current thumbnail.\n\n"

        "🗑️ **Remove Current**\n"
        "Disable the current thumbnail.\n\n"

        "📹 **Send Video**\n"
        "The selected thumbnail will be applied.\n\n"

        "📝 **Caption**\n"
        "Original caption stays unchanged.\n\n"

        "📊 **Progress**\n"
        "• Percentage\n"
        "• Speed\n"
        "• Size\n"
        "• ETA\n"
        "• Elapsed Time"

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


    data = query.data


    # =====================================================
    # HOME
    # =====================================================

    if data == "home":

        await query.message.edit_text(

            "🎬 **Advanced Thumbnail Bot**\n\n"
            "Choose an option 👇",

            reply_markup=main_menu()

        )

        await query.answer()


    # =====================================================
    # MANAGER
    # =====================================================

    elif data == "manager":

        await query.message.edit_text(

            "🖼️ **Thumbnail Manager**\n\n"
            "Manage your thumbnails below 👇",

            reply_markup=manager_menu()

        )

        await query.answer()


    # =====================================================
    # ADD
    # =====================================================

    elif data == "add":

        user_state[
            query.from_user.id
        ] = {
            "state": "waiting_photo"
        }


        await query.message.reply_text(

            "➕ **Add Thumbnail**\n\n"

            "Send your thumbnail image 📸\n\n"

            "Recommended:\n"
            "• JPG/JPEG\n"
            "• 16:9 image\n"
            "• Good quality"

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

                "⭐ **No Current Thumbnail**\n\n"
                "Please select a thumbnail first."

            )

        else:

            await client.send_photo(

                query.message.chat.id,

                current["file_id"],

                caption=(

                    "⭐ **Current Thumbnail**\n\n"

                    f"🖼️ Name: `{current['name']}`\n"
                    "📌 Status: Active"

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

                "❌ **No Current Thumbnail**\n\n"
                "Select a thumbnail first."

            )

        else:

            await client.send_photo(

                query.message.chat.id,

                current["file_id"],

                caption=(

                    "👀 **Thumbnail Preview**\n\n"

                    f"🖼️ Name: `{current['name']}`\n"
                    "⭐ Status: Active"

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

                "❌ **No Current Thumbnail**"

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

                "🗑️ **Current Thumbnail Removed**\n\n"

                f"Thumbnail: `{current['name']}`\n\n"

                "Send a new video only after selecting "
                "another thumbnail."

            )


        await query.answer()


    # =====================================================
    # SELECT THUMBNAIL
    # =====================================================

    elif data.startswith(
        "select:"
    ):

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


        # Remove current from all
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

            f"🖼️ Selected: `{selected['name']}`\n\n"

            "📹 Now send your video."

        )


        await query.answer(
            "Thumbnail Selected ⭐"
        )


    # =====================================================
    # DELETE CONFIRMATION
    # =====================================================

    elif data.startswith(
        "confirm_delete:"
    ):

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


        keyboard = InlineKeyboardMarkup([

            [

                InlineKeyboardButton(
                    "✅ Yes, Delete",
                    callback_data=(
                        "delete:" +
                        thumb_id
                    )
                ),

                InlineKeyboardButton(
                    "❌ Cancel",
                    callback_data="list"
                )

            ]

        ])


        await query.message.reply_text(

            "⚠️ **Delete Thumbnail?**\n\n"

            f"🖼️ Name: `{selected['name']}`\n\n"

            "This action cannot be undone.",

            reply_markup=keyboard

        )


        await query.answer()


    # =====================================================
    # DELETE THUMBNAIL
    # =====================================================

    elif data.startswith(
        "delete:"
    ):

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


            if not selected:

                await query.answer(

                    "❌ Thumbnail not found.",

                    show_alert=True

                )

                return


            result = thumbs.delete_one(

                {
                    "_id": ObjectId(
                        thumb_id
                    )
                }

            )


            if result.deleted_count:

                await query.message.reply_text(

                    "🗑️ **Thumbnail Deleted Successfully!**\n\n"

                    f"`{selected['name']}` has been deleted."

                )

            else:

                await query.message.reply_text(

                    "❌ Could not delete thumbnail."

                )


        except Exception as error:

            await query.message.reply_text(

                "❌ **Delete Failed**\n\n"
                f"`{str(error)}`"

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

            "Tap below to add one.",

            reply_markup=InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(
                        "➕ Add Thumbnail",
                        callback_data="add"
                    )

                ],

                [

                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data="manager"
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


        active = (

            " ⭐ ACTIVE"

            if item.get(
                "is_current",
                False
            )

            else ""

        )


        buttons.append([

            InlineKeyboardButton(

                f"🖼️ {name}{active}",

                callback_data=(

                    "select:" +

                    str(
                        item["_id"]
                    )

                )

            )

        ])


        buttons.append([

            InlineKeyboardButton(

                f"🗑️ Delete {name}",

                callback_data=(

                    "confirm_delete:" +

                    str(
                        item["_id"]
                    )

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

        "⭐ ACTIVE = currently selected\n\n"

        "Tap a thumbnail to make it active.",

        reply_markup=InlineKeyboardMarkup(
            buttons
        )

    )


# =========================================================
# /setthumb COMMAND
# =========================================================

@bot.on_message(filters.command("setthumb"))
async def setthumb_command(client, message):

    if not message.from_user:
        return

    if not is_admin(message.from_user.id):
        await message.reply_text("❌ Admin only.")
        return

    user_state[message.from_user.id] = {
        "state": "waiting_photo"
    }

    await message.reply_text(
        "➕ **Set Thumbnail**\n\n"
        "Please send the thumbnail image 🖼️\n\n"
        "After sending the image, I will ask you for a name.\n\n"
        "Example:\n"
        "Send Image → `Naruto`"
    )
@bot.on_message(filters.command("showthumb"))
async def showthumb_command(client, message):

    if not message.from_user:
        return

    if not is_admin(message.from_user.id):
        await message.reply_text("❌ Admin only.")
        return

    await show_thumbnail_list(message)

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


    user_state[
        message.from_user.id
    ] = {

        "state": "waiting_name",

        "file_id": message.photo.file_id

    }


    await message.reply_text(

        "✅ **Thumbnail Received!**\n\n"

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
        [
            "start",
            "help"
        ]
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


    # Make all previous thumbnails inactive
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

        "📹 Send a video now.\n\n"

        "📝 Original caption will remain unchanged.",

        reply_markup=main_menu()

    )


# =========================================================
# PROGRESS FORMAT
# =========================================================

def format_bytes(
    size
):

    if size is None:

        return "0 B"


    size = float(
        size
    )


    for unit in [
        "B",
        "KB",
        "MB",
        "GB"
    ]:

        if size < 1024:

            return (
                f"{size:.1f} "
                f"{unit}"
            )


        size /= 1024


    return (
        f"{size:.1f} TB"
    )


def format_time(
    seconds
):

    if seconds is None:

        return "00:00"


    seconds = max(
        0,
        int(seconds)
    )


    hours = (
        seconds // 3600
    )


    minutes = (
        seconds % 3600
    ) // 60


    secs = (
        seconds % 60
    )


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

    percentage = max(
        0,
        min(
            100,
            percentage
        )
    )


    filled = int(

        percentage /
        100 *
        length

    )


    return (

        "█" * filled +

        "░" * (
            length - filled
        )

    )


# =========================================================
# PROGRESS CLASS
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

        self.start_time = (
            time.monotonic()
        )


    async def update(
        self,
        current,
        total
    ):

        if not total:

            return


        now = (
            time.monotonic()
        )


        percentage = (

            current /
            total *
            100

        )


        elapsed = (

            now -
            self.start_time

        )


        if elapsed <= 0:

            elapsed = 0.001


        speed = (

            current /
            elapsed

        )


        remaining = max(

            0,

            total -
            current

        )


        if speed > 0:

            eta = (

                remaining /
                speed

            )

        else:

            eta = 0


        # Update every 2 seconds
        if (

            now -
            self.last_update < 2

            and

            percentage < 100

        ):

            return


        self.last_update = now


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

        except Exception:

            pass


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


    # =====================================================
    # GET CURRENT THUMBNAIL
    # =====================================================

    current = thumbs.find_one(

        {
            "is_current": True
        }

    )


    if not current:

        await message.reply_text(

            "❌ **No Thumbnail Selected!**\n\n"

            "Please select a thumbnail first."

        )

        return


    thumbnail_file_id = (
        current["file_id"]
    )


    thumbnail_name = (
        current["name"]
    )


    # =====================================================
    # STATUS MESSAGE
    # =====================================================

    status = await message.reply_text(

        "📥 **Starting...**\n\n"

        f"🖼️ Thumbnail: `{thumbnail_name}`"

    )


    video_path = None

    thumb_original = None

    thumb_path = None


    try:

        # =================================================
        # DOWNLOAD VIDEO
        # =================================================

        download_progress = Progress(

            status,

            "📥 **Downloading Video...**"

        )


        video_path = tempfile.mktemp(
            suffix=".mp4"
        )


        video_path = await client.download_media(

            message,

            file_name=video_path,

            progress=download_progress.update

        )


        if not video_path:

            raise Exception(
                "Video download failed."
            )


        # =================================================
        # DOWNLOAD THUMBNAIL
        # =================================================

        await status.edit_text(

            "🖼️ **Preparing Thumbnail...**\n\n"

            f"Thumbnail: `{thumbnail_name}`"

        )


        thumb_original = tempfile.mktemp(
            suffix=".jpg"
        )


        thumb_original = await client.download_media(

            thumbnail_file_id,

            file_name=thumb_original

        )


        if not thumb_original:

            raise Exception(
                "Thumbnail download failed."
            )


        # =================================================
        # OPTIMIZE THUMBNAIL
        # =================================================

        thumb_path = tempfile.mktemp(
            suffix=".jpg"
        )


        with Image.open(
            thumb_original
        ) as image:

            image = image.convert(
                "RGB"
            )


            # Telegram-friendly dimensions
            image.thumbnail(

                (320, 320),

                Image.Resampling.LANCZOS

            )


            image.save(

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
        # UPLOAD VIDEO
        # =================================================

        upload_progress = Progress(

            status,

            "📤 **Uploading Video...**"

        )


        await client.send_video(

            chat_id=message.chat.id,

            video=video_path,

            caption=original_caption,

            thumb=thumb_path,

            duration=message.video.duration,

            width=message.video.width,

            height=message.video.height,

            supports_streaming=True,

            progress=upload_progress.update

        )


        # =================================================
        # COMPLETE
        # =================================================

        elapsed = (

            time.monotonic()

            - upload_progress.start_time

        )


        await status.edit_text(

            "✅ **Completed Successfully!**\n\n"

            f"🖼️ Thumbnail: `{thumbnail_name}`\n"

            f"🕐 Upload Time: "
            f"`{format_time(elapsed)}`\n\n"

            "📝 Original caption preserved.\n"

            "📹 Video uploaded successfully."

        )


        await asyncio.sleep(
            3
        )


        try:

            await status.delete()

        except Exception:

            pass


    # =====================================================
    # ERROR
    # =====================================================

    except Exception as error:

        try:

            await status.edit_text(

                "❌ **Upload Failed!**\n\n"

                f"Error:\n`{str(error)}`"

            )

        except Exception:

            pass


    # =====================================================
    # CLEAN TEMP FILES
    # =====================================================

    finally:

        for path in [

            video_path,

            thumb_original,

            thumb_path

        ]:

            if path:

                try:

                    if os.path.exists(
                        path
                    ):

                        os.remove(
                            path
                        )

                except Exception:

                    pass


# =========================================================
# RENDER + BOT START
# =========================================================

if __name__ == "__main__":

    threading.Thread(

        target=run_flask,

        daemon=True

    ).start()


    print(
        "🚀 Advanced Thumbnail Bot Started!"
    )


    bot.run()
