import discord
from discord.ext import commands
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        
        # Chỉ trả lời khi bot được nhắc đến (tag)
        if self.bot.user not in message.mentions: return

        async with message.channel.typing():
            try:
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": message.content}]
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.url, headers=self.headers, json=payload) as resp:
                        data = await resp.json()
                        reply = data["choices"][0]["message"]["content"]
                        
                await message.reply(reply)
                
            except Exception as e:
                print(f"Lỗi AI: {e}")
                await message.reply("⚠️ Não bộ của tôi đang gặp trục trặc, vui lòng thử lại sau nhé!")

async def setup(bot):
    await bot.add_cog(AIChat(bot))