import os
import discord
from discord.ext import commands
import requests
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
LUMA_API_KEY = os.getenv("LUMA_API_KEY")

intents = discord.Intents.default()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()  # register slash commands with Discord

bot = MyBot()

def generate_video(prompt: str):
    headers = {
        "Authorization": f"Bearer {LUMA_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        "https://api.lumalabs.ai/v1/ray/generate",
        headers=headers,
        json={"prompt": prompt, "model": "ray-3-reasoning"}
    )
    data = response.json()
    print("DEBUG LUMA RESPONSE:", data) 
    generation_id = data.get("id")
    if not generation_id:
        return None, "Error: No generation ID returned."
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
        asyncio.sleep(5)
    return None, "Timeout waiting for video."

@bot.tree.command(name="luma", description="Generate video with Luma AI")
async def luma(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message(f"🎥 Generating video for: `{prompt}` ... please wait!")
    loop = asyncio.get_event_loop()
    video_url, error = await loop.run_in_executor(None, generate_video, prompt)
    if error:
        await interaction.followup.send(f"❌ {error}")
    else:
        await interaction.followup.send(f"✅ Done! Here’s your video:\n{video_url}")

bot.run(TOKEN)
