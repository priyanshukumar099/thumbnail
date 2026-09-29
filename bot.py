import os
import time
import asyncio
import tempfile
import threading
import logging
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
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


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
        port=port,
        threaded=True
    )


# =========================================================
# MONGODB
# =========================================================

mongo = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=10000
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
# START
# =========================================================

@bot.on_message(filters.command("start"))
async def start_command(client, message):

    if not message.from_user:
        return

    if not is_admin(message.from_user.id):

        await message.reply_text(
            "❌ Admin only."
        )

        return

    await message.reply_text(

        "🎬 **Advanced Thumbnail Bot**\n\n"

        "Welcome Admin! 👋\n\n"

        "🖼️ Multiple Thumbnail Support\n"
        "⭐ Default Thumbnail\n"
        "🔄 Change Thumbnail\n"
        "🗑️ Delete Thumbnail\n"
        "📹 MP4 / Video Support\n"
        "📁 MKV / Document Support\n"
        "📝 Original Caption\n"
        "📁 Original Filename\n"
        "📊 Download / Upload Progress\n\n"

        "Use `/help` to see commands.",

        reply_markup=main_menu()
    )


# =========================================================
# HELP
# =========================================================

@bot.on_message(filters.command("help"))
async def help_command(client, message):

    if not message.from_user:
        return

    if not is_admin(message.from_user.id):
        return

    await message.reply_text(

        "📖 **Bot Commands**\n\n"

        "🏠 `/start`\n"
        "Open main menu.\n\n"

        "➕ `/setthumb`\n"
        "Add a new thumbnail.\n\n"

        "📚 `/showthumb`\n"
        "Show saved thumbnails.\n\n"

        "🗑️ `/deletethumb`\n"
        "Delete a thumbnail.\n\n"

        "📹 **Media Support**\n"
        "• MP4\n"
        "• MKV\n"
        "• AVI\n"
        "• MOV\n"
        "• WEBM\n"
        "• M4V\n"
        "• Other video documents\n\n"

        "✨ **Features**\n"
        "• Original caption preserved\n"
        "• Original filename preserved\n"
        "• Original extension preserved\n"
        "• Selected thumbnail applied\n"
        "• Download progress\n"
        "• Upload progress\n"
        "• Speed\n"
        "• ETA\n"
        "• Elapsed time"
    )


# =========================================================
# SET THUMBNAIL
# =========================================================

@bot.on_message(filters.command("setthumb"))
async def setthumb_command(client, message):

    if not message.from_user:
        return

    if not is_admin(message.from_user.id):

        await message.reply_text(
            "❌ Admin only."
        )

        return

    user_state[
        message.from_user.id
    ] = {
        "state": "waiting_photo"
    }

    await message.reply_text(

        "➕ **Set Thumbnail**\n\n"

        "Please send your thumbnail image 🖼️\n\n"

        "After that, I will ask for a name.\n\n"

        "Example:\n"
        "`Naruto`\n"
        "`Boruto`\n"
        "`Black Clover`"
    )


# =========================================================
# SHOW THUMBNAILS
# =========================================================

@bot.on_message(filters.command("showthumb"))
async def showthumb_command(client, message):

    if not message.from_user:
        return

    if not is_admin(message.from_user.id):
        return

    await show_thumbnail_list(message)


# =========================================================
# DELETE THUMBNAIL
# =========================================================

@bot.on_message(filters.command("deletethumb"))
async def deletethumb_command(client, message):

    if not message.from_user:
        return

    if not is_admin(message.from_user.id):
        return

    items = list(
        thumbs.find().sort(
            "_id",
            -1
        ).limit(50)
    )

    if not items:

        await message.reply_text(
            "❌ No saved thumbnails."
        )

        return

    buttons = []

    for item in items:

        name = item.get(
            "name",
            "Unnamed"
        )

        buttons.append([

            InlineKeyboardButton(

                f"🗑️ {name}",

                callback_data=(
                    "confirm_delete:"
                    + str(item["_id"])
                )
            )
        ])

    buttons.append([

        InlineKeyboardButton(
            "🔙 Back",
            callback_data="home"
        )
    ])

    await message.reply_text(

        "🗑️ **Delete Thumbnail**\n\n"
        "Select a thumbnail:",

        reply_markup=InlineKeyboardMarkup(
            buttons
        )
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

@bot.on_callback_query()
async def callback_handler(client, query):

    if not is_admin(query.from_user.id):

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

        return


    # =====================================================
    # MANAGER
    # =====================================================

    if data == "manager":

        await query.message.edit_text(

            "🖼️ **Thumbnail Manager**\n\n"
            "Manage your thumbnails:",

            reply_markup=manager_menu()
        )

        await query.answer()

        return


    # =====================================================
    # ADD
    # =====================================================

    if data == "add":

        user_state[
            query.from_user.id
        ] = {
            "state": "waiting_photo"
        }

        await query.message.reply_text(

            "➕ **Add Thumbnail**\n\n"
            "Send the thumbnail image 🖼️"
        )

        await query.answer()

        return


    # =====================================================
    # LIST
    # =====================================================

    if data == "list":

        await show_thumbnail_list(
            query.message
        )

        await query.answer()

        return


    # =====================================================
    # CURRENT
    # =====================================================

    if data == "current":

        current = thumbs.find_one({
            "is_current": True
        })

        if not current:

            await query.message.reply_text(
                "⭐ No current thumbnail."
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

        return


    # =====================================================
    # PREVIEW
    # =====================================================

    if data == "preview":

        current = thumbs.find_one({
            "is_current": True
        })

        if not current:

            await query.message.reply_text(
                "❌ No thumbnail selected."
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

        return


    # =====================================================
    # REMOVE CURRENT
    # =====================================================

    if data == "remove_current":

        current = thumbs.find_one({
            "is_current": True
        })

        if not current:

            await query.message.reply_text(
                "❌ No current thumbnail."
            )

        else:

            thumbs.update_many(
                {},
                {
                    "$set": {
                        "is_current": False
                    }
                }
            )

            await query.message.reply_text(

                "🗑️ **Current Thumbnail Removed**\n\n"
                "No thumbnail is active now."
            )

        await query.answer()

        return


    # =====================================================
    # SELECT
    # =====================================================

    if data.startswith("select:"):

        thumb_id = data.split(
            ":",
            1
        )[1]

        try:

            selected = thumbs.find_one({
                "_id": ObjectId(thumb_id)
            })

        except Exception:

            selected = None

        if not selected:

            await query.answer(
                "❌ Thumbnail not found.",
                show_alert=True
            )

            return

        thumbs.update_many(
            {},
            {
                "$set": {
                    "is_current": False
                }
            }
        )

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

        await query.answer(
            "Thumbnail selected!"
        )

        return


    # =====================================================
    # DELETE
    # =====================================================

    if data.startswith("confirm_delete:"):

        thumb_id = data.split(
            ":",
            1
        )[1]

        try:

            item = thumbs.find_one({
                "_id": ObjectId(thumb_id)
            })

            if not item:

                await query.answer(
                    "❌ Thumbnail not found.",
                    show_alert=True
                )

                return

            was_current = item.get(
                "is_current",
                False
            )

            thumbs.delete_one({
                "_id": ObjectId(thumb_id)
            })

            # If current thumbnail was deleted,
            # automatically select newest remaining thumbnail.
            if was_current:

                newest = thumbs.find_one(
                    sort=[
                        ("_id", -1)
                    ]
                )

                if newest:

                    thumbs.update_many(
                        {},
                        {
                            "$set": {
                                "is_current": False
                            }
                        }
                    )

                    thumbs.update_one(
                        {
                            "_id": newest["_id"]
                        },
                        {
                            "$set": {
                                "is_current": True
                            }
                        }
                    )

            await query.message.reply_text(

                "✅ **Thumbnail Deleted!**\n\n"

                f"Deleted: "
                f"`{item.get('name', 'Unnamed')}`"
            )

            await query.answer(
                "Deleted!"
            )

        except Exception as error:

            logger.exception(
                "Delete error"
            )

            await query.message.reply_text(

                "❌ Delete failed.\n\n"
                f"`{str(error)}`"
            )

            await query.answer()

        return


# =========================================================
# SHOW THUMBNAIL LIST
# =========================================================

async def show_thumbnail_list(message):

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

            "Use `/setthumb` to add one."
        )

        return

    buttons = []

    for item in items:

        name = item.get(
            "name",
            "Unnamed"
        )

        active = (
            " ⭐"
            if item.get(
                "is_current",
                False
            )
            else ""
        )

        buttons.append([

            InlineKeyboardButton(

                f"{name}{active}",

                callback_data=(
                    "select:"
                    + str(item["_id"])
                )
            )
        ])

        buttons.append([

            InlineKeyboardButton(

                f"🗑️ Delete {name}",

                callback_data=(
                    "confirm_delete:"
                    + str(item["_id"])
                )
            )
        ])

    buttons.append([

        InlineKeyboardButton(
            "➕ Add Thumbnail",
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

        "⭐ = Current Thumbnail\n\n"

        "Tap a thumbnail to activate it.",

        reply_markup=InlineKeyboardMarkup(
            buttons
        )
    )


# =========================================================
# PHOTO HANDLER
# =========================================================

@bot.on_message(filters.photo)
async def photo_handler(client, message):

    if not message.from_user:
        return

    if not is_admin(message.from_user.id):
        return

    state = user_state.get(
        message.from_user.id
    )

    if not state:
        return

    if state.get("state") != "waiting_photo":
        return

    user_state[
        message.from_user.id
    ] = {

        "state": "waiting_name",

        "file_id":
            message.photo.file_id
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
    & ~filters.command([
        "start",
        "help",
        "setthumb",
        "showthumb",
        "deletethumb"
    ])
)
async def text_handler(client, message):

    if not message.from_user:
        return

    if not is_admin(message.from_user.id):
        return

    state = user_state.get(
        message.from_user.id
    )

    if not state:
        return

    if state.get("state") != "waiting_name":
        return

    name = message.text.strip()

    if not name:

        await message.reply_text(
            "❌ Please send a valid name."
        )

        return

    file_id = state.get("file_id")

    # Make all old thumbnails inactive
    thumbs.update_many(
        {},
        {
            "$set": {
                "is_current": False
            }
        }
    )

    # Save thumbnail
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

        "Now send your video/file 📹",

        reply_markup=main_menu()
    )


# =========================================================
# FORMAT BYTES
# =========================================================

def format_bytes(size):

    if not size:
        return "0 B"

    size = float(size)

    for unit in [
        "B",
        "KB",
        "MB",
        "GB",
        "TB"
    ]:

        if size < 1024:
            return f"{size:.1f} {unit}"

        size /= 1024

    return f"{size:.1f} PB"


# =========================================================
# FORMAT TIME
# =========================================================

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


# =========================================================
# PROGRESS BAR
# =========================================================

def progress_bar(
    percentage,
    length=18
):

    percentage = max(
        0,
        min(
            100,
            percentage
        )
    )

    filled = int(
        percentage
        / 100
        * length
    )

    return (
        "█" * filled
        +
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

        self.start_time = (
            time.monotonic()
        )

        self.last_update = 0
        self.last_text = ""

    async def update(
        self,
        current,
        total
    ):

        if not total:
            return

        now = time.monotonic()

        elapsed = (
            now -
            self.start_time
        )

        if elapsed <= 0:
            elapsed = 0.001

        percentage = (
            current /
            total *
            100
        )

        speed = (
            current /
            elapsed
        )

        remaining = max(
            0,
            total - current
        )

        eta = (
            remaining / speed
            if speed > 0
            else 0
        )

        # Update every 2 seconds
        if (
            now -
            self.last_update
            < 2
            and current < total
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

        if text == self.last_text:
            return

        self.last_text = text

        try:

            await self.message.edit_text(
                text
            )

        except Exception:
            pass


# =========================================================
# PREPARE THUMBNAIL
# =========================================================

async def prepare_thumbnail(
    client,
    file_id,
    workdir
):

    original_path = os.path.join(
        workdir,
        "thumbnail_source"
    )

    thumb_path = os.path.join(
        workdir,
        "thumbnail.jpg"
    )

    downloaded = await client.download_media(
        file_id,
        file_name=original_path
    )

    if not downloaded:
        raise Exception(
            "Thumbnail download failed."
        )

    with Image.open(
        downloaded
    ) as image:

        image = image.convert(
            "RGB"
        )

        image.thumbnail(
            (320, 320),
            Image.Resampling.LANCZOS
        )

        quality = 85

        while quality >= 30:

            image.save(
                thumb_path,
                "JPEG",
                quality=quality,
                optimize=True
            )

            if os.path.getsize(
                thumb_path
            ) < 190 * 1024:
                break

            quality -= 5

    if not os.path.exists(
        thumb_path
    ):

        raise Exception(
            "Thumbnail creation failed."
        )

    if os.path.getsize(
        thumb_path
    ) >= 200 * 1024:

        raise Exception(
            "Thumbnail is larger than 200 KB."
        )

    return thumb_path


# =========================================================
# VIDEO EXTENSIONS
# =========================================================

VIDEO_EXTENSIONS = {

    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".3gp",
    ".ts",
    ".mpeg",
    ".mpg"

}


# =========================================================
# GET MEDIA INFO
# =========================================================

def get_media_info(message):

    # Telegram native video
    if message.video:

        file_name = (
            message.video.file_name
            or
            f"video_{message.id}.mp4"
        )

        return {

            "type": "video",

            "file_id":
                message.video.file_id,

            "file_name":
                file_name,

            "duration":
                message.video.duration,

            "width":
                message.video.width,

            "height":
                message.video.height
        }


    # Telegram document
    if message.document:

        document = message.document

        file_name = (
            document.file_name
            or
            f"file_{message.id}"
        )

        extension = os.path.splitext(
            file_name
        )[1].lower()

        mime = (
            document.mime_type
            or ""
        ).lower()

        is_video = (

            mime.startswith("video/")

            or

            extension in VIDEO_EXTENSIONS
        )

        if not is_video:
            return None

        return {

            "type": "document",

            "file_id":
                document.file_id,

            "file_name":
                file_name
        }

    return None


# =========================================================
# SAFE FILENAME
# =========================================================

def safe_filename(name):

    name = os.path.basename(
        name
    )

    if not name:
        name = "video_file"

    return name


# =========================================================
# PROCESS MEDIA
# =========================================================

async def process_media(
    client,
    message
):

    if not message.from_user:
        return

    if not is_admin(
        message.from_user.id
    ):
        return

    media = get_media_info(
        message
    )

    if not media:

        return

    current = thumbs.find_one({
        "is_current": True
    })

    if not current:

        await message.reply_text(

            "❌ **No Thumbnail Selected!**\n\n"

            "Use `/setthumb` first."
        )

        return

    original_name = safe_filename(
        media["file_name"]
    )

    workdir = tempfile.mkdtemp(
        prefix="thumbbot_"
    )

    video_path = os.path.join(
        workdir,
        original_name
    )

    thumb_path = None

    status = await message.reply_text(

        "📥 **Starting...**\n\n"

        f"📁 File: `{original_name}`\n"
        f"🖼️ Thumbnail: "
        f"`{current['name']}`"
    )

    try:

        # =================================================
        # DOWNLOAD
        # =================================================

        download_progress = Progress(
            status,
            "📥 **Downloading File...**"
        )

        downloaded_path = (
            await client.download_media(

                message,

                file_name=video_path,

                progress=
                    download_progress.update
            )
        )

        if not downloaded_path:

            raise Exception(
                "File download failed."
            )

        video_path = downloaded_path


        # =================================================
        # CHECK
        # =================================================

        if not os.path.exists(
            video_path
        ):

            raise Exception(
                "Downloaded file not found."
            )


        # =================================================
        # PREPARE THUMBNAIL
        # =================================================

        await status.edit_text(

            "🖼️ **Preparing Thumbnail...**\n\n"

            f"📁 File: `{original_name}`\n"
            f"⭐ Selected: "
            f"`{current['name']}`"
        )

        thumb_path = await prepare_thumbnail(

            client,

            current["file_id"],

            workdir
        )


        # =================================================
        # ORIGINAL CAPTION
        # =================================================

        original_caption = (
            message.caption
            or
            ""
        )

        original_entities = (
            message.caption_entities
            if message.caption_entities
            else None
        )


        # =================================================
        # UPLOAD
        # =================================================

        upload_progress = Progress(
            status,
            "📤 **Uploading File...**"
        )


        # -------------------------------------------------
        # NATIVE VIDEO
        # -------------------------------------------------

        if media["type"] == "video":

            await client.send_video(

                chat_id=message.chat.id,

                video=video_path,

                caption=original_caption,

                caption_entities=
                    original_entities,

                thumb=thumb_path,

                duration=
                    media.get("duration"),

                width=
                    media.get("width"),

                height=
                    media.get("height"),

                supports_streaming=True,

                progress=
                    upload_progress.update
            )


        # -------------------------------------------------
        # MKV / VIDEO DOCUMENT
        # -------------------------------------------------

        else:

            # Filename is preserved through
            # the actual downloaded path.
            await client.send_document(

                chat_id=message.chat.id,

                document=video_path,

                thumb=thumb_path,

                caption=original_caption,

                caption_entities=
                    original_entities,

                force_document=True,

                progress=
                    upload_progress.update
            )


        # =================================================
        # COMPLETE
        # =================================================

        total_time = (
            time.monotonic()
            -
            upload_progress.start_time
        )

        await status.edit_text(

            "✅ **Completed Successfully!**\n\n"

            f"📁 **File:** `{original_name}`\n"

            f"🖼️ **Thumbnail:** "
            f"`{current['name']}`\n"

            f"🕐 **Time:** "
            f"`{format_time(total_time)}`\n\n"

            "📝 Caption: **Preserved**\n"
            "📁 Filename: **Preserved**"
        )

        await asyncio.sleep(4)

        try:
            await status.delete()
        except Exception:
            pass


    except Exception as error:

        logger.exception(
            "Media processing error"
        )

        try:

            await status.edit_text(

                "❌ **Processing Failed!**\n\n"

                f"📁 File: `{original_name}`\n\n"

                f"Error:\n"
                f"`{str(error)}`"
            )

        except Exception:
            pass


    finally:

        # =================================================
        # CLEAN TEMP DIRECTORY
        # =================================================

        try:

            for root, dirs, files in os.walk(
                workdir,
                topdown=False
            ):

                for filename in files:

                    try:

                        os.remove(
                            os.path.join(
                                root,
                                filename
                            )
                        )

                    except Exception:
                        pass

                for directory in dirs:

                    try:

                        os.rmdir(
                            os.path.join(
                                root,
                                directory
                            )
                        )

                    except Exception:
                        pass

            try:

                os.rmdir(
                    workdir
                )

            except Exception:
                pass

        except Exception:

            pass


# =========================================================
# VIDEO HANDLER
# =========================================================

@bot.on_message(filters.video)
async def video_handler(
    client,
    message
):

    await process_media(
        client,
        message
    )


# =========================================================
# DOCUMENT / MKV HANDLER
# =========================================================

@bot.on_message(filters.document)
async def document_handler(
    client,
    message
):

    await process_media(
        client,
        message
    )


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.on_error()
async def global_error_handler(
    client,
    update,
    error
):

    logger.exception(
        "Unhandled Pyrogram error: %s",
        error
    )


# =========================================================
# RUN
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
