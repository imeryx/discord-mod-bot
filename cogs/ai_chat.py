import discord
from discord.ext import commands
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        # Sử dụng model Flash mới nhất, nếu không được sẽ fallback về Pro
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        # Lưu trữ lịch sử chat của người dùng (mỗi người 1 key)
        self.chat_sessions = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or self.bot.user not in message.mentions:
            return

        user_id = message.author.id
        user_query = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        
        if not user_query:
            await message.reply("Chào bạn! Bạn cần tôi giúp gì về lập trình hay giải đáp thắc mắc nào không?")
            return

        # Khởi tạo hoặc lấy phiên chat cũ để bot nhớ ngữ cảnh
        if user_id not in self.chat_sessions:
            self.chat_sessions[user_id] = self.model.start_chat(history=[])

        try:
            await message.add_reaction("🧠")
            
            # Gửi câu hỏi vào phiên chat
            response = self.chat_sessions[user_id].send_message(user_query)
            
            await message.remove_reaction("🧠", self.bot.user)
            
            reply_text = response.text
            # Chia nhỏ nếu quá dài (Discord limit)
            if len(reply_text) > 2000:
                parts = [reply_text[i:i+1900] for i in range(0, len(reply_text), 1900)]
                for part in parts:
                    await message.reply(part)
            else:
                await message.reply(reply_text)
                
        except Exception as e:
            await message.remove_reaction("🧠", self.bot.user)
            await message.reply("Hệ thống AI đang bảo trì, bạn thử lại sau một chút nhé!")

async def setup(bot):
    await bot.add_cog(AIChat(bot))