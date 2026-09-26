import os, time, asyncio, tempfile, threading
from datetime import datetime
from flask import Flask
from pymongo import MongoClient
from bson import ObjectId
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
MONGO_URI = os.environ["MONGO_URI"]
MONGO_DB = os.environ.get("MONGO_DB", "thumbnail_bot")
ADMIN_ID = int(os.environ["ADMIN_ID"])

app = Flask(__name__)

@app.route("/")
def home():
    return "Advanced Thumbnail Bot is Running! 🚀"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = mongo[MONGO_DB]
thumbs = db["thumbnails"]

bot = Client("advanced_thumbnail_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_state = {}

def is_admin(uid):
    return uid == ADMIN_ID

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼️ Thumbnail Manager", callback_data="manager")],
        [InlineKeyboardButton("📚 My Thumbnails", callback_data="list")],
        [InlineKeyboardButton("⭐ Current Thumbnail", callback_data="current")],
        [InlineKeyboardButton("👀 Preview", callback_data="preview")],
        [InlineKeyboardButton("🗑️ Remove Current", callback_data="remove_current")]
    ])

def manager_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Thumbnail", callback_data="add")],
        [InlineKeyboardButton("📚 Saved Thumbnails", callback_data="list")],
        [InlineKeyboardButton("🔄 Change Thumbnail", callback_data="list")],
        [InlineKeyboardButton("⭐ Set Default", callback_data="list")],
        [InlineKeyboardButton("🗑️ Remove Current", callback_data="remove_current")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")]
    ])

HELP = """📖 **Advanced Thumbnail Bot**

/start - Main menu
/help - Help
/setthumb - Add thumbnail
/showthumb - Saved thumbnails
/current - Current thumbnail
/preview - Preview thumbnail
/remove - Remove current
/cancel - Cancel process

📹 Send a Telegram Video OR a video File/Document.
🖼️ Selected thumbnail is applied.
📝 Original caption remains unchanged.
📊 Progress: percentage, size, speed, ETA and elapsed time."""

@bot.on_message(filters.command("start"))
async def start(client, message):
    if not message.from_user or not is_admin(message.from_user.id):
        await message.reply_text("❌ Admin only.")
        return
    await message.reply_text(
        "🎬 **Advanced Video Thumbnail Bot**\n\n"
        "Welcome Admin! 👋\n\n"
        "🖼️ Save multiple thumbnails\n"
        "⭐ Select a default thumbnail\n"
        "📹 Send a video/video-file to apply it\n"
        "📝 Original caption stays unchanged\n\n"
        "Use `/help` for commands.",
        reply_markup=main_menu())

@bot.on_message(filters.command("help"))
async def help_command(client, message):
    if message.from_user and is_admin(message.from_user.id):
        await message.reply_text(HELP)

@bot.on_message(filters.command("setthumb"))
async def setthumb_command(client, message):
    if not message.from_user or not is_admin(message.from_user.id):
        await message.reply_text("❌ Admin only.")
        return
    user_state[message.from_user.id] = {"state": "waiting_photo"}
    await message.reply_text(
        "➕ **Set Thumbnail**\n\n"
        "Send the thumbnail image 🖼️\n"
        "Then send a name, for example: `Naruto`")

@bot.on_message(filters.command("showthumb"))
async def showthumb_command(client, message):
    if message.from_user and is_admin(message.from_user.id):
        await show_thumbnail_list(message)

@bot.on_message(filters.command("current"))
async def current_command(client, message):
    if not message.from_user or not is_admin(message.from_user.id): return
    cur = thumbs.find_one({"is_current": True})
    if not cur:
        await message.reply_text("⭐ **No Current Thumbnail**"); return
    await client.send_photo(message.chat.id, cur["file_id"],
        caption=f"⭐ **Current Thumbnail**\n\n🖼️ Name: `{cur['name']}`\nStatus: ✅ Active")

@bot.on_message(filters.command("preview"))
async def preview_command(client, message):
    if not message.from_user or not is_admin(message.from_user.id): return
    cur = thumbs.find_one({"is_current": True})
    if not cur:
        await message.reply_text("❌ **No Thumbnail Selected**"); return
    await client.send_photo(message.chat.id, cur["file_id"],
        caption=f"👀 **Thumbnail Preview**\n\n🖼️ Name: `{cur['name']}`")

@bot.on_message(filters.command("remove"))
async def remove_command(client, message):
    if not message.from_user or not is_admin(message.from_user.id): return
    cur = thumbs.find_one({"is_current": True})
    if not cur:
        await message.reply_text("❌ **No Current Thumbnail**"); return
    thumbs.update_one({"_id": cur["_id"]}, {"$set": {"is_current": False}})
    await message.reply_text("🗑️ **Current Thumbnail Removed!**")

@bot.on_message(filters.command("cancel"))
async def cancel_command(client, message):
    if message.from_user and is_admin(message.from_user.id):
        user_state.pop(message.from_user.id, None)
        await message.reply_text("❌ **Current process cancelled.**")

@bot.on_callback_query()
async def callbacks(client, query):
    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("❌ Admin only!", show_alert=True); return
    data = query.data
    if data == "home":
        await query.message.edit_text("🎬 **Advanced Thumbnail Bot**\n\nChoose an option:", reply_markup=main_menu())
    elif data == "manager":
        await query.message.edit_text("🖼️ **Thumbnail Manager**\n\nManage your saved thumbnails:", reply_markup=manager_menu())
    elif data == "add":
        user_state[query.from_user.id] = {"state": "waiting_photo"}
        await query.message.reply_text("➕ **Add Thumbnail**\n\nSend thumbnail image 🖼️\nThen send a name.")
    elif data == "list":
        await show_thumbnail_list(query.message)
    elif data in ("current", "preview"):
        cur = thumbs.find_one({"is_current": True})
        if not cur:
            await query.message.reply_text("❌ No current thumbnail selected.")
        else:
            await client.send_photo(query.message.chat.id, cur["file_id"],
                caption=("⭐ **Current Thumbnail**" if data == "current" else "👀 **Thumbnail Preview**") +
                f"\n\nName: `{cur['name']}`")
    elif data == "remove_current":
        cur = thumbs.find_one({"is_current": True})
        if not cur:
            await query.message.reply_text("❌ No current thumbnail.")
        else:
            thumbs.update_one({"_id": cur["_id"]}, {"$set": {"is_current": False}})
            await query.message.reply_text("🗑️ **Current thumbnail removed.**")
    elif data.startswith("select:"):
        try: cur = thumbs.find_one({"_id": ObjectId(data.split(":",1)[1])})
        except Exception: cur = None
        if not cur:
            await query.answer("❌ Thumbnail not found.", show_alert=True); return
        thumbs.update_many({}, {"$set": {"is_current": False}})
        thumbs.update_one({"_id": cur["_id"]}, {"$set": {"is_current": True}})
        await query.message.reply_text(f"⭐ **Thumbnail Changed!**\n\nSelected: `{cur['name']}`")
    elif data.startswith("confirm_delete:"):
        tid = data.split(":",1)[1]
        await query.message.reply_text("⚠️ Delete this thumbnail?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Yes, Delete", callback_data=f"delete:{tid}"),
                InlineKeyboardButton("❌ Cancel", callback_data="list")]]))
    elif data.startswith("delete:"):
        try:
            result = thumbs.delete_one({"_id": ObjectId(data.split(":",1)[1])})
            await query.message.reply_text("🗑️ **Thumbnail deleted.**" if result.deleted_count else "❌ Not found.")
        except Exception:
            await query.message.reply_text("❌ Delete failed.")
    await query.answer()

async def show_thumbnail_list(message):
    items = list(thumbs.find().sort("_id",-1).limit(50))
    if not items:
        await message.reply_text("📚 **No thumbnails saved.**\n\nUse `/setthumb`.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Thumbnail", callback_data="add")]]))
        return
    buttons = []
    for item in items:
        name = item.get("name","Unnamed")
        active = " ⭐" if item.get("is_current") else ""
        buttons.append([InlineKeyboardButton(name+active, callback_data=f"select:{item['_id']}")])
        buttons.append([InlineKeyboardButton("🗑️ Delete "+name, callback_data=f"confirm_delete:{item['_id']}")])
    buttons += [[InlineKeyboardButton("➕ Add New", callback_data="add")],
                [InlineKeyboardButton("🔙 Back", callback_data="manager")]]
    await message.reply_text("📚 **Saved Thumbnails**\n\nTap one to make it active ⭐",
        reply_markup=InlineKeyboardMarkup(buttons))

@bot.on_message(filters.photo)
async def photo_handler(client, message):
    if not message.from_user or not is_admin(message.from_user.id): return
    state = user_state.get(message.from_user.id)
    if not state or state.get("state") != "waiting_photo": return
    user_state[message.from_user.id] = {"state":"waiting_name","file_id":message.photo.file_id}
    await message.reply_text("✅ **Image received!**\n\nNow send a name, e.g. `Naruto`.")

@bot.on_message(filters.text & ~filters.command(
    ["start","help","setthumb","showthumb","current","preview","remove","cancel"]))
async def text_handler(client, message):
    if not message.from_user or not is_admin(message.from_user.id): return
    state = user_state.get(message.from_user.id)
    if not state or state.get("state") != "waiting_name": return
    name = message.text.strip()
    if not name:
        await message.reply_text("❌ Please send a valid name."); return
    thumbs.update_many({}, {"$set":{"is_current":False}})
    thumbs.insert_one({"name":name,"file_id":state["file_id"],"is_current":True,"created_at":datetime.utcnow()})
    user_state.pop(message.from_user.id,None)
    await message.reply_text(f"✅ **Thumbnail Saved!**\n\n🖼️ `{name}`\n⭐ Active\n\nNow send your video/video file.", reply_markup=main_menu())

def fmt_bytes(n):
    n = float(n or 0)
    for u in ("B","KB","MB","GB","TB"):
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"

def fmt_time(s):
    s=max(0,int(s or 0)); h=s//3600; m=(s%3600)//60; sec=s%60
    return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

def bar(p):
    p=max(0,min(100,p)); n=int(p/100*16)
    return "█"*n+"░"*(16-n)

class Progress:
    def __init__(self,message,action):
        self.message=message; self.action=action; self.last=0; self.start=time.monotonic()
    async def update(self,current,total,*args):
        if not total: return
        now=time.monotonic(); elapsed=max(.001,now-self.start); p=current/total*100
        speed=current/elapsed; eta=(total-current)/speed if speed else 0
        if now-self.last<2 and p<100: return
        self.last=now
        text=(f"{self.action}\n\n{bar(p)} **{p:.1f}%**\n\n"
              f"📦 **Size:** {fmt_bytes(current)} / {fmt_bytes(total)}\n"
              f"⚡ **Speed:** {fmt_bytes(speed)}/s\n"
              f"⏱️ **ETA:** {fmt_time(eta)}\n"
              f"🕐 **Elapsed:** {fmt_time(elapsed)}")
        try: await self.message.edit_text(text)
        except Exception: pass

def prepare_thumb(source):
    out=tempfile.mktemp(suffix=".jpg")
    with Image.open(source) as im:
        im=im.convert("RGB"); im.thumbnail((320,320),Image.Resampling.LANCZOS)
        q=85
        while q>=30:
            im.save(out,"JPEG",quality=q,optimize=True)
            if os.path.getsize(out)<=190*1024: break
            q-=10
    return out

@bot.on_message(filters.video | filters.document)
async def video_handler(client, message):
    if not message.from_user or not is_admin(message.from_user.id): return

    is_video=bool(message.video)
    if message.document:
        mime=(message.document.mime_type or "").lower()
        name=(message.document.file_name or "").lower()
        is_video=mime.startswith("video/") or name.endswith(
            (".mp4",".mkv",".mov",".avi",".webm",".m4v",".mpeg",".mpg"))
    if not is_video: return

    cur=thumbs.find_one({"is_current":True})
    if not cur:
        await message.reply_text("❌ **No Thumbnail Selected!**\n\nUse `/setthumb` first.")
        return

    status=await message.reply_text(f"📥 **Starting...**\n\n🖼️ Thumbnail: `{cur['name']}`")
    video_path=thumb_original=thumb_path=None
    try:
        dp=Progress(status,"📥 **Downloading Video...**")
        video_path=await client.download_media(message,file_name=tempfile.mktemp(suffix=".mp4"),progress=dp.update)
        if not video_path: raise RuntimeError("Video download failed.")

        await status.edit_text("🖼️ **Preparing Thumbnail...**")
        thumb_original=await client.download_media(cur["file_id"],file_name=tempfile.mktemp(suffix=".jpg"))
        if not thumb_original: raise RuntimeError("Thumbnail download failed.")
        thumb_path=prepare_thumb(thumb_original)

        up=Progress(status,"📤 **Uploading Video with Thumbnail...**")
        caption=message.caption

        if message.video:
            await client.send_video(
                message.chat.id,video_path,caption=caption,thumb=thumb_path,
                duration=message.video.duration,width=message.video.width,
                height=message.video.height,supports_streaming=True,
                progress=up.update)
        else:
            await client.send_document(
                message.chat.id,video_path,caption=caption,thumb=thumb_path,
                force_document=True,progress=up.update)

        await status.edit_text(
            f"✅ **Completed Successfully!**\n\n"
            f"🖼️ Thumbnail: `{cur['name']}`\n"
            f"🕐 Time: `{fmt_time(time.monotonic()-up.start)}`\n"
            f"📝 Original caption preserved.")
        await asyncio.sleep(3)
        try: await status.delete()
        except Exception: pass
    except Exception as e:
        await status.edit_text(f"❌ **Upload Failed!**\n\n`{str(e)}`")
    finally:
        for p in (video_path,thumb_original,thumb_path):
            if p:
                try:
                    if os.path.exists(p): os.remove(p)
                except Exception: pass

if __name__=="__main__":
    threading.Thread(target=run_flask,daemon=True).start()
    print("🚀 Advanced Thumbnail Bot Started!")
    bot.run()
