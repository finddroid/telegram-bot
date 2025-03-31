import os
import uuid
import urllib.parse
import aiohttp
import asyncio
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from keep_alive import keep_alive
keep_alive()
# Bot token from BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")
TRACE_FILE_BOOL = False
Join_channel = "Join : https://t.me/+53k_M8_xKcE3NmI1".replace("_", "\\_")
# Channel IDs
PRIVATE_CHANNEL_ID = -1002377701369  # Private channel ID
PUBLIC_CHANNEL_ID = -1002584737841  # Public channel ID
BOT_USERNAME = "ShadowWorld_Filebot"

# User API keys for URL shortener
user_obj = {
    "HuiHola": os.getenv("HHAPI"),
    "The_Shadow_73":os.getenv("TSAPI")
}

# Temporary storage for file links (cache)
file_links = {}
STORE_FILE = "store.txt"  # File to store metadata
file_groups = defaultdict(list)  # Stores files grouped by sender session


# Async function to shorten URLs
async def shorten_url(long_url, api_token, alias=""):
    """Shortens a URL using an external API asynchronously."""
    encoded_url = urllib.parse.quote(long_url)
    api_url = f"https://shortyfi.site/api?api={api_token}&url={encoded_url}&alias={alias}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                result = await response.json()
                return result.get("shortenedUrl") if result.get("status") != "error" else None
        except Exception as e:
            print(f"Request failed: {e}")
            return None


# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    args = context.args  # Get arguments passed in the /start command
    if args:
        link_id = args[0]

        # Check cache first
        file_info_list = file_links.get(link_id)
        if not file_info_list:
            file_info_list = fetch_metadata_from_file(link_id)  # Fetch from stored file if not cached

        if file_info_list:
            for file_info in file_info_list:
                caption = file_info.get("caption", "")
                await update.message.reply_document(
                    document=file_info["file_id"],
                    caption=f"Here is your file: {file_info['file_name']}\n{caption}\n\n{Join_channel}",
                    parse_mode="Markdown",
                )
        else:
            await update.message.reply_text("❌ Invalid or expired link.")
    else:
        await update.message.reply_text("Welcome! Use a valid link to access files.")


# Function to delay and send grouped files
async def file_sender_delay(user_name, sender_id, context, main_caption):
    global TRACE_FILE_BOOL
    await asyncio.sleep(10)
    TRACE_FILE_BOOL = False
    await check_and_send_file_group(user_name, sender_id, context, main_caption)


# Function to check and send grouped file links
async def check_and_send_file_group(user_name, sender_id, context, main_caption):
    """Checks if multiple files are sent and generates a link."""
    if len(file_groups[sender_id]) != 0:  # Ensure multiple files exist before sending
        link_id = str(uuid.uuid4())
        file_links[link_id] = file_groups[sender_id]
        store_metadata_in_file(link_id, file_groups[sender_id])

        bot_link = f"https://t.me/{BOT_USERNAME}?start={link_id}"
        api_id = user_obj.get(user_name)

        # Shorten the URL asynchronously
        if(api_id):
            link = await shorten_url(bot_link, api_id)
        else:
            Hopi = user_obj.get("HuiHola")
            link = await shorten_url(bot_link,Hopi)
        # Send grouped file message
        await context.bot.send_message(
            chat_id=PUBLIC_CHANNEL_ID,
            text=f"{Join_channel}  \n\n 📁 **New File Group Added!**\n\n{main_caption}\n\n📂 Files: {len(file_groups[sender_id])} items\n\n🔗 [Click here]({link}) to get the files.\n\nNOTE : Open link in Chrome or Other browser.",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        # Clear stored files after sending
        file_groups[sender_id].clear()


# Message handler for file uploads
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles files sent to the private channel."""
    global TRACE_FILE_BOOL
    try:
        if update.channel_post:
            message = update.channel_post
            if message.chat_id == PRIVATE_CHANNEL_ID:
                sender_id = message.sender_chat.id if message.sender_chat else message.from_user.id
                main_caption = message.caption or ""
                truncated_caption = main_caption[:400] + "..." if len(main_caption) > 400 else main_caption

                if message.document:
                    file_name = message.document.file_name
                    file_id = message.document.file_id
                elif message.video:
                    file_name = "video.mp4"
                    file_id = message.video.file_id
                elif message.photo:
                    await context.bot.send_photo(
                        chat_id=PUBLIC_CHANNEL_ID,
                        photo=message.photo[-1].file_id,
                        caption=f"{message.caption}\n\n{Join_channel}\n\nAll Files are \n⬇⬇⬇⬇",
                    )
                    return  # Exit after sending the photo
                else:
                    return  # Ignore unsupported file types

                # Store file info in sender's session group
                file_groups[sender_id].append({
                    "file_name": file_name,
                    "file_id": file_id,
                    "caption": truncated_caption,
                })
                user_name = message.from_user.username if message.from_user else None

                # Schedule function to check for multiple files
                if not TRACE_FILE_BOOL:
                    TRACE_FILE_BOOL = True
                    asyncio.create_task(file_sender_delay(user_name, sender_id, context, main_caption))

    except Exception as e:
        await context.bot.send_message(chat_id=PRIVATE_CHANNEL_ID, text=f"❌ An error occurred: {e}")
        print("Error:", e)


# Function to store metadata in a file
def store_metadata_in_file(link_id: str, file_info_list: list) -> None:
    """Stores file metadata in a text file."""
    with open(STORE_FILE, "a") as file:
        for file_info in file_info_list:
            metadata_line = f"{link_id}|{file_info['file_name']}|{file_info['file_id']}|{file_info['caption']}\n"
            file.write(metadata_line)


# Function to fetch metadata from a file
def fetch_metadata_from_file(link_id: str) -> list:
    """Fetches file metadata from a text file."""
    if not os.path.exists(STORE_FILE):
        return None

    file_info_list = []
    with open(STORE_FILE, "r") as file:
        for line in file:
            parts = line.strip().split("|")
            if parts[0] == link_id:
                file_info_list.append({
                    "file_name": parts[1],
                    "file_id": parts[2],
                    "caption": parts[3],
                })
    return file_info_list if file_info_list else None


# Main function to start the bot
def main() -> None:
    """Starts the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Chat(PRIVATE_CHANNEL_ID), handle_file))

    print("Bot is running...")
    application.run_polling()


# Run the bot
if __name__ == "__main__":
    main()

