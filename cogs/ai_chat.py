import discord
from discord.ext import commands
from google import genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Hàm kiểm tra trạng thái bật/tắt từ Dashboard
def is_module_enabled(module_name):
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("modules", {}).get(module_name, True)
    except:
        pass
    return True

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or self.bot.user not in message.mentions:
            return

        # 1. Kiểm tra xem module này có bị tắt trên web không
        if not is_module_enabled("ai_chat"):
            return # Im lặng, không trả lời

        query = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        if not query: return

        try:
            await message.add_reaction("🧠")
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=query
            )
            
            await message.remove_reaction("🧠", self.bot.user)
            await message.reply(response.text[:2000])
            
        except Exception as e:
            print(f"Lỗi AI: {e}")
            await message.remove_reaction("🧠", self.bot.user)
            await message.reply("Tôi đang bận xử lý dữ liệu, bạn đợi chút nhé!")

async def setup(bot):
    await bot.add_cog(AIChat(bot))