import discord
from discord.ext import commands
from google import genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Hàm kiểm tra trạng thái bật/tắt theo ID Server (guild_id)
def is_module_enabled(guild_id, module_name):
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get(str(guild_id), {}).get("modules", {}).get(module_name, True)
    except Exception as e:
        print(f"Lỗi đọc config.json: {e}")
    return True

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bỏ qua nếu là tin nhắn của bot khác hoặc không bị tag
        if message.author.bot or self.bot.user not in message.mentions:
            return

        # Kiểm tra xem tính năng AI có bị tắt trên Server này không
        if message.guild and not is_module_enabled(message.guild.id, "ai_chat"):
            return # Im lặng, không trả lời

        query = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        if not query: 
            return

        try:
            await message.add_reaction("🧠")
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=query
            )
            
            await message.remove_reaction("🧠", self.bot.user)
            await message.reply(response.text[:2000])
            
        except Exception as e:
            error_msg = str(e)
            print(f"Lỗi AI: {error_msg}")
            await message.remove_reaction("🧠", self.bot.user)
            
            # Nếu bắt được lỗi 429 quá tải từ Google
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                await message.reply("⏳ Tốc độ chat đang quá nhanh! Google yêu cầu tôi nghỉ ngơi một chút. Bạn đợi khoảng 1 phút rồi nhắn lại nhé!")
            else:
                # Các lỗi mạng khác
                await message.reply("⚠️ Elfaria đang bị lỗi kết nối tạm thời, bạn thử lại sau nhé!")

async def setup(bot):
    await bot.add_cog(AIChat(bot))