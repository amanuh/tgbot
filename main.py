import os
import ffmpeg
import asyncio
import speedtest
from pyrogram import Client, filters
from pyrogram.types import Message
from queue import Queue

# Initialize bot client
api_id = "12997033"
api_hash = "31ee7eb1bf2139d96a1147f3553e0364"
bot_token = "5174264179:AAGxbF9h_mIQ1Eui01GeENFZzjqx4sx86lM"
admin_id = "1352973730"

# List of authorized user IDs (admin can add more later)
authorized_users = [admin_id]

app = Client("video_converter_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Queue to manage video conversion requests
video_queue = Queue()
# Lock to ensure only one conversion at a time
conversion_lock = asyncio.Lock()

# Function to check if a user is authorized
def is_authorized(user_id):
    return str(user_id) in authorized_users

# /start command handler
@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    if is_authorized(message.from_user.id):
        await message.reply_text("Hello! 👋 Welcome to the Video Converter Bot. Send me any video and I'll convert it to MKV format for you.\nUse /convert to get started!")
    else:
        await message.reply_text("You are not authorized to use this bot.")

# /ping command handler (Admin only)
@app.on_message(filters.command("ping") & filters.user(admin_id))
async def ping_command(client: Client, message: Message):
    if is_authorized(message.from_user.id):
        # Use speedtest-cli to check internet speed
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 1_000_000  # Convert to Mbps
        upload_speed = st.upload() / 1_000_000      # Convert to Mbps
        
        await message.reply_text(f"Ping Results:\nDownload: {download_speed:.2f} Mbps\nUpload: {upload_speed:.2f} Mbps")
    else:
        await message.reply_text("You are not authorized to use this command.")

# /convert command handler to add video to queue
@app.on_message(filters.command("convert") & filters.private)
async def convert_command(client: Client, message: Message):
    if is_authorized(message.from_user.id):
        if message.reply_to_message and message.reply_to_message.video:
            video_message = message.reply_to_message
            video_queue.put(video_message)
            await message.reply_text("Video added to the queue for conversion. You will receive the MKV file once it's processed.")
            
            # If only one video in the queue, start processing
            if video_queue.qsize() == 1:
                await process_queue(client, message.chat.id)
        else:
            await message.reply_text("Please reply to a video file with the /convert command.")
    else:
        await message.reply_text("You are not authorized to use this bot.")

# Function to process video queue with locking to ensure one at a time
async def process_queue(client: Client, chat_id: int):
    while not video_queue.empty():
        # Ensure only one video is processed at a time
        async with conversion_lock:
            video_message = video_queue.get()
            await client.send_message(chat_id, "Processing video...")

            # Download video file
            video_file = await video_message.download()

            # Define the output mkv file path
            output_file = os.path.splitext(video_file)[0] + ".mkv"
            
            # Convert the video to mkv using ffmpeg
            try:
                ffmpeg.input(video_file).output(output_file).run()
                await client.send_video(chat_id, video=output_file, caption="Here is your MKV video.")
            except Exception as e:
                await client.send_message(chat_id, f"An error occurred during conversion: {str(e)}")
            finally:
                # Clean up files
                if os.path.exists(video_file):
                    os.remove(video_file)
                if os.path.exists(output_file):
                    os.remove(output_file)

# Run the bot
app.run()
