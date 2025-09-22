import os
import discord
from discord.ext import commands
import requests
import time
import asyncio # For asynchronous sleeping

# Tokens from Railway environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LUMA_API_KEY = os.getenv("LUMA_API_KEY")

# Make sure all intents are enabled for more robust functionality
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

def generate_video(prompt: str):
    """
    Handles the synchronous API calls to Luma Labs.
    NOTE: This is a synchronous function and will block the bot.
    For a fully asynchronous bot, use aiohttp instead of requests.
    """
    headers = {
        "Authorization": f"Bearer {LUMA_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        # 1. Submit the prompt with a timeout
        response = requests.post(
            "https://api.lumalabs.ai/v1/ray/generate",
            headers=headers,
            json={"prompt": prompt, "model": "ray-3-reasoning"},
            timeout=10 # Add a timeout to prevent hanging
        )
        response.raise_for_status() # Raise an exception for bad status codes

        data = response.json()
        generation_id = data.get("id")

        if not generation_id:
            return None, "Error: No generation ID returned."

        # 2. Poll until video is ready
        # Using a synchronous sleep here will still block the bot's event loop.
        # This is a key area for improvement with aiohttp.
        for _ in range(30):
            status_resp = requests.get(
                f"https://api.lumalabs.ai/v1/ray/generations/{generation_id}",
                headers=headers,
                timeout=10 # Add a timeout to prevent hanging
            )
            status_resp.raise_for_status()

            status_data = status_resp.json()
            state = status_data.get("status")

            if state == "completed":
                return status_data["output"]["video_url"], None
            elif state == "failed":
                return None, "Generation failed."

            time.sleep(5) # This blocks the entire bot

        return None, "Timeout waiting for video."

    except requests.exceptions.RequestException as e:
        return None, f"An API request error occurred: {e}"
    except Exception as e:
        return None, f"An unexpected error occurred: {e}"

@bot.tree.command(name="luma", description="Generate a video from a text prompt using Luma AI.")
@commands.guild_only() # Optional: Restrict command to a specific server
async def luma(interaction: discord.Interaction, prompt: str):
    """
    Responds to the slash command and calls the video generation function.
    """
    await interaction.response.send_message(f"🎥 Generating video for: `{prompt}` ... please wait!")

    video_url, error = await asyncio.to_thread(generate_video, prompt)

    if error:
        await interaction.followup.send(f"❌ {error}")
    else:
        await interaction.followup.send(f"✅ Done! Here’s your video:\n{video_url}")

# This part is crucial for syncing the commands
@bot.event
async def on_ready():
    """
    Syncs the slash commands to Discord when the bot connects.
    """
    print(f'Logged in as {bot.user}!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

bot.run(DISCORD_TOKEN)