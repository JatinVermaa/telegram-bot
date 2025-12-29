from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os
import uuid

# ------------- CONFIG ----------------

API_ID = 36001520
API_HASH = "1dec0f6809024516068a0fbb92d6dc55"
BOT_TOKEN = "8028378886:AAFQj1E2H8CeeBEgFGkyCFlZoYeVLIL6UU4"

ADMIN_ID = 7945454951

DB_FILE = "messages.json"
# -------- DATABASE --------
# --------------------------------

SAVE_STATE = {}
ADD_BUTTON_STATE = {}


# ------------ DATABASE ------------
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
# ---------------------------------


app = Client(
    "message_link_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


# ------------ USER START ------------
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    parts = message.text.split(maxsplit=1)

    if len(parts) == 1:
        await message.reply("Send a valid message link.")
        return

    code = parts[1].strip()
    db = load_db()

    if code not in db:
        await message.reply("Invalid or expired link.")
        return

    data = db[code]

    keyboard = None
    if data.get("button"):
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(
                data["button"]["text"],
                url=data["button"]["url"]
            )]]
        )

    await client.send_message(
        chat_id=message.chat.id,
        text=data["text"],
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
        disable_web_page_preview=False
    )
# ----------------------------------


# ------------ SAVE NEW MESSAGE ------------
@app.on_message(filters.command("save") & filters.private)
async def save_cmd(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("YOU ARE NOT PERMITTED TO USE THIS BOT.")
        return

    SAVE_STATE[ADMIN_ID] = {"step": "text"}
    await message.reply("Send the message text.")
# -----------------------------------------


# ------------ ADD BUTTON TO OLD MESSAGE ------------
@app.on_message(filters.command("addbutton") & filters.private)
async def add_button_cmd(client, message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("YOU ARE NOT PERMITTED TO USE THIS BOT.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.reply("Usage:\n/addbutton <code>")
        return

    code = parts[1].strip()
    db = load_db()

    if code not in db:
        await message.reply("Invalid code.")
        return

    ADD_BUTTON_STATE[ADMIN_ID] = {
        "step": "text",
        "code": code
    }

    await message.reply("Send button text.")
# ----------------------------------------------


# ------------ ADMIN TEXT HANDLER ------------
@app.on_message(filters.private & filters.text)
async def admin_text_handler(client, message):
    if message.from_user.id != ADMIN_ID:
        return

    if message.text.startswith("/"):
        return

    # ---- SAVE FLOW ----
    save_state = SAVE_STATE.get(ADMIN_ID)
    if save_state:
        if save_state["step"] == "text":
            db = load_db()
            code = str(uuid.uuid4())[:8]

            db[code] = {
                "text": message.text.html
            }

            save_db(db)
            SAVE_STATE.pop(ADMIN_ID)

            bot_username = (await client.get_me()).username
            link = f"https://t.me/{bot_username}?start={code}"

            await message.reply(
                "Message saved successfully ✅\n\n"
                f"Link:\n{link}"
            )
        return

    # ---- ADD BUTTON FLOW ----
    add_state = ADD_BUTTON_STATE.get(ADMIN_ID)
    if add_state:
        if add_state["step"] == "text":
            add_state["button_text"] = message.text.strip()
            add_state["step"] = "url"
            await message.reply("Send button URL.")
            return

        if add_state["step"] == "url":
            db = load_db()
            code = add_state["code"]

            db[code]["button"] = {
                "text": add_state["button_text"],
                "url": message.text.strip()
            }

            save_db(db)
            ADD_BUTTON_STATE.pop(ADMIN_ID)

            await message.reply("Button added successfully ✅")
            return
# ------------------------------------------


print("Bot is running...")
app.run()
