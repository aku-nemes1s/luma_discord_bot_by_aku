import os
import discord
from discord.ext import commands
import requests
import asyncio
import time

# Load tokens from Railway environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LUMA_API_KEY = os.getenv("LUMA_API_KEY")

intents = discord.Intents.default()

class MyBot(commands.Bot):
    def __init__(self):
        # Prefix is irrelevant, we’re using slash commands
        super().__init__(command_prefix=None, intents=intents)

    async def setup_hook(self):
        # Sync slash commands with Discord
        await self.tree.sync()

bot = MyBot()

# ----------------------
# Luma API integration
# ----------------------
def generate_video(prompt: str):
    headers = {
        "Authorization": f"Bearer {LUMA_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # 1. Submit the prompt
    response = requests.post(
        "https://api.lumalabs.ai/dream-machine/v1/generations",
        headers=headers,
        json={
            "prompt": prompt,
            "model": "ray-2",  # ✅ use a supported model, e.g. ray-2, ray-flash-2
            "resolution": "720p",
            "duration": "5s"
        }
    )
    data = response.json()
    print("DEBUG LUMA STATUS:", response.status_code)
    print("DEBUG LUMA RESPONSE:", data)

    generation_id = data.get("id")
    if not generation_id:
        return None, f"Error: No generation ID returned. Details: {data}"

    # 2. Poll until video is ready
    for _ in range(30):
        status_resp = requests.get(
            f"https://api.lumalabs.ai/dream-machine/v1/generations/{generation_id}",
            headers=headers
        )
        status_data = status_resp.json()
        print("DEBUG POLL:", status_data)

        state = status_data.get("state") or status_data.get("status")
        if state == "completed":
            video_url = status_data.get("assets", {}).get("video")
            if video_url:
                return video_url, None
            else:
                return None, "Error: Completed but no video URL found."
        elif state == "failed":
            return None, f"Generation failed: {status_data.get('failure_reason', 'unknown')}"

        time.sleep(5)  # wait before polling again

    return None, "Timeout waiting for video."

# ----------------------
# Slash command
# ----------------------
@bot.tree.command(name="luma", description="Generate a video with Luma AI")
async def luma(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message(
        f"🎥 Generating video for: `{prompt}` ... please wait!"
    )

    loop = asyncio.get_event_loop()
    video_url, error = await loop.run_in_executor(None, generate_video, prompt)

    if error:
        await interaction.followup.send(f"❌ {error}")
    else:
        await interaction.followup.send(f"✅ Done! Here’s your video:\n{video_url}")

# ----------------------
# Run bot
# ----------------------
bot.run(DISCORD_TOKEN)
