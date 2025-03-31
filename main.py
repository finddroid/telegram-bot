import os
import uuid
import urllib.parse
import aiohttp
import asyncio
import base64
import requests
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from keep_alive import keep_alive

keep_alive()

# GitHub details
GITHUB_TOKEN = os.getenv("GIT_TOKEN")
GITHUB_USERNAME = "finddroid"
REPO_NAME = "file-storage"
FILE_PATH = "store.txt"

# Bot token from BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN")
TRACE_FILE_BOOL = False
Join_channel = "Join : https://t.me/+53k_M8_xKcE3NmI1".replace("_", "\\_")
PRIVATE_CHANNEL_ID = -1002377701369  
PUBLIC_CHANNEL_ID = -1002584737841  
BOT_USERNAME = "ShadowWorld_Filebot"

# User API keys for URL shortener
user_obj = {
    "HuiHola": os.getenv("HHAPI"),
    "The_Shadow_73": os.getenv("TSAPI")
}

# Temporary storage
file_links = {}
file_groups = defaultdict(list)

# GitHub API URL
GITHUB_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}/contents/{FILE_PATH}"

# Function to store metadata on GitHub
def store_metadata_in_github(link_id: str, file_info_list: list):
    """Stores file metadata in GitHub repository instead of local file."""
    try:
        # Fetch existing content
        response = requests.get(GITHUB_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        sha = response.json().get("sha", "") if response.status_code == 200 else None
        existing_content = base64.b64decode(response.json()["content"]).decode("utf-8") if response.status_code == 200 else ""

        # Append new data
        new_data = "\n".join([f"{link_id}|{file['file_name']}|{file['file_id']}|{file['caption']}" for file in file_info_list])
        updated_content = existing_content + "\n" + new_data if existing_content else new_data

        # Encode and upload to GitHub
        encoded_content = base64.b64encode(updated_content.encode()).decode()
        payload = {"message": "Update store.txt", "content": encoded_content, "sha": sha}

        response = requests.put(GITHUB_URL, json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        return response.status_code == 200

    except Exception as e:
        print(f"GitHub Upload Error: {e}")
        return False

# Function to fetch metadata from GitHub
def fetch_metadata_from_github(link_id: str):
    """Fetches stored metadata from GitHub repository."""
    try:
        response = requests.get(GITHUB_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        if response.status_code == 200:
            file_content = base64.b64decode(response.json()["content"]).decode("utf-8")
            file_info_list = [line.split("|") for line in file_content.strip().split("\n") if line.startswith(link_id)]
            return [{"file_name": f[1], "file_id": f[2], "caption": f[3]} for f in file_info_list]
        return None
    except Exception as e:
        print(f"GitHub Fetch Error: {e}")
        return None

# Async function to shorten URLs
async def shorten_url(long_url, api_token):
    """Shortens a URL using an external API asynchronously."""
    encoded_url = urllib.parse.quote(long_url)
    api_url = f"https://shortyfi.site/api?api={api_token}&url={encoded_url}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                result = await response.json()
                return result.get("shortenedUrl") if result.get("status") != "error" else None
        except Exception as e:
            print(f"URL Shortener Error: {e}")
            return None

# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    args = context.args  
    if args:
        link_id = args[0]

        # Fetch metadata from GitHub
        file_info_list = fetch_metadata_from_github(link_id)

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

# Function to check and send grouped file links
async def check_and_send_file_group(user_name, sender_id, context, main_caption):
    """Checks if multiple files are sent and generates a link."""
    if len(file_groups[sender_id]) != 0:  
        link_id = str(uuid.uuid4())
        file_links[link_id] = file_groups[sender_id]
        store_metadata_in_github(link_id, file_groups[sender_id])

        bot_link = f"https://t.me/{BOT_USERNAME}?start={link_id}"
        api_id = user_obj.get(user_name) or user_obj.get("HuiHola")
        short_link = await shorten_url(bot_link, api_id)

        await context.bot.send_message(
            chat_id=PUBLIC_CHANNEL_ID,
            text=f"{Join_channel}  \n\n 📁 **New File Group Added!**\n\n{main_caption}\n\n📂 Files: {len(file_groups[sender_id])} items\n\n🔗 [Click here]({short_link}) to get the files.\n\nNOTE: Open link in Chrome or another browser.",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        file_groups[sender_id].clear()

# Main function to start the bot
def main():
    """Starts the bot."""
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
