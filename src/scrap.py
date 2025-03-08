import os
import time
from datetime import datetime, timedelta
import pandas as pd
import pytz
from dotenv import load_dotenv
from telethon import TelegramClient

# Load environment variables
load_dotenv()
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
phone = os.getenv('PHONE')

client = TelegramClient('session_name', api_id, api_hash)

# Set up directories for saving media
output_dir = "output"
media_dir = os.path.join('D:\\', 'media')
os.makedirs(output_dir, exist_ok=True)
os.makedirs(media_dir, exist_ok=True)


async def fetch_messages(start_date, end_date):
    channels = ['t.me/IsraelWarLive', 't.me/ILTVnews', 't.me/gazanewss01', 't.me/israel']
    messages_list = []
    media_list = []

    for channel in channels:
        async for message in client.iter_messages(channel, limit=None, offset_date=end_date):
            if message.date < start_date:
                break

            message_id = message.id  # Unique message identifier

            # Extract text message reactions
            message_reactions = None
            if message.reactions:
                message_reactions = {reaction.reaction.emoticon: reaction.count for reaction in message.reactions.results if
                                     hasattr(reaction.reaction, 'emoticon')}

            # Extract text message comments
            message_comments = []
            if message.replies and message.replies.replies > 0:
                async for reply in client.iter_messages(channel, reply_to=message_id):
                    message_comments.append(reply.text)

            # Store text message details
            messages_list.append({
                'Message_ID': message_id,
                'Channel': channel,
                'Date': message.date.replace(tzinfo=None),
                'Message': message.text,
                'Text_Reactions': message_reactions,
                'Text_Comments': message_comments,
                'Media File': None  # To be updated if media exists
            })

            # Process media separately
            if message.media:
                media_files = []
                media_reactions = None
                media_comments = []

                # Download media
                media_path = os.path.join(media_dir, f"{channel.replace('t.me/', '')}_{message_id}")
                file = await message.download_media(file=media_path)
                if file:
                    media_files.append(file)

                    # Check if media itself has reactions
                    if message.reactions:
                        media_reactions = {reaction.reaction.emoticon: reaction.count for reaction in message.reactions.results if
                                           hasattr(reaction.reaction, 'emoticon')}

                    # Extract comments on media
                    if message.replies and message.replies.replies > 0:
                        async for reply in client.iter_messages(channel, reply_to=message_id):
                            media_comments.append(reply.text)

                    # Store media details separately
                    media_list.append({
                        'Message_ID': message_id,
                        'Channel': channel,
                        'Date': message.date.replace(tzinfo=None),
                        'Media File': file,
                        'Media_Reactions': media_reactions,
                        'Media_Comments': media_comments
                    })

                # Update the original message entry with media file names
                messages_list[-1]['Media Files'] = ", ".join(media_files) if media_files else None

    return messages_list, media_list


async def main():
    await client.start()

    tz = pytz.UTC
    end_date = tz.localize(datetime(2025, 1, 29, 23, 59))
    start_date = end_date - timedelta(days=30)

    current_start = start_date

    file_name_messages = os.path.join(output_dir, "telegram_messages.xlsx")
    file_name_media = os.path.join(output_dir, "telegram_media.xlsx")

    while current_start < end_date:
        current_end = min(current_start + timedelta(days=2), end_date)

        print(f"Fetching messages from {current_start} to {current_end}...")

        messages_list, media_list = await fetch_messages(current_start, current_end)

        # Convert to DataFrame
        df_messages = pd.DataFrame(messages_list)
        df_media = pd.DataFrame(media_list)

        # Save messages
        if not df_messages.empty:
            if os.path.exists(file_name_messages):
                existing_df = pd.read_excel(file_name_messages)
                df_messages = pd.concat([existing_df, df_messages], ignore_index=True)

            df_messages.to_excel(file_name_messages, index=False)
            print(f"Saved text messages from {current_start} to {current_end}.")

        # Save media data
        if not df_media.empty:
            if os.path.exists(file_name_media):
                existing_df_media = pd.read_excel(file_name_media)
                df_media = pd.concat([existing_df_media, df_media], ignore_index=True)

            df_media.to_excel(file_name_media, index=False)
            print(f"Saved media messages from {current_start} to {current_end}.")

        current_start = current_end
        time.sleep(30)


with client:
    client.loop.run_until_complete(main())
