import os
import discord
from discord.ext import commands
import requests
import time

# Tokens from Railway environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LUMA_API_KEY = os.getenv("LUMA_API_KEY")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

def generate_video(prompt: str):
    headers = {
        "Authorization": f"Bearer {LUMA_API_KEY}",
        "Content-Type": "application/json"
    }

    # 1. Submit the prompt
    response = requests.post(
        "https://api.lumalabs.ai/v1/ray/generate",
        headers=headers,
        json={"prompt": prompt, "model": "ray-3-reasoning"}
    )
    data = response.json()
    generation_id = data.get("id")

    if not generation_id:
        return None, "Error: No generation ID returned."

    # 2. Poll until video is ready
    for _ in range(30):  
        status_resp = requests.get(
            f"https://api.lumalabs.ai/v1/ray/generations/{generation_id}",
            headers=headers
        )
        status_data = status_resp.json()
        state = status_data.get("status")

        if state == "completed":
            return status_data["output"]["video_url"], None
        elif state == "failed":
            return None, "Generation failed."

        time.sleep(5)

    return None, "Timeout waiting for video."

@bot.command(name="luma")
async def luma(ctx, *, prompt: str):
    await ctx.send(f"🎥 Generating video for: `{prompt}` ... please wait!")

    video_url, error = generate_video(prompt)

    if error:
        await ctx.send(f"❌ {error}")
    else:
        await ctx.send(f"✅ Done! Here’s your video:\n{video_url}")

bot.run(DISCORD_TOKEN)
