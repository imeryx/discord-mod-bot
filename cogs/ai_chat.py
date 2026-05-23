import discord
from discord.ext import commands
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Khởi tạo client mới nhất của Google
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or self.bot.user not in message.mentions:
            return

        query = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        if not query: return

        try:
            await message.add_reaction("🧠")
            # Dùng model flash mới nhất, cực thông minh và cập nhật tốt
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=query
            )
            await message.remove_reaction("🧠", self.bot.user)
            await message.reply(response.text[:2000])
        except Exception as e:
            print(f"Lỗi: {e}")
            await message.remove_reaction("🧠", self.bot.user)
            await message.reply("Tôi vẫn đang cập nhật kiến thức, bạn đợi chút nhé!")

async def setup(bot):
    await bot.add_cog(AIChat(bot))