import discord
from discord.ext import commands
from groq import Groq
from duckduckgo_search import DDGS
import os
from dotenv import load_dotenv

load_dotenv()

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or self.bot.user not in message.mentions:
            return

        user_query = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        if not user_query: return

        try:
            await message.add_reaction("🔍")
            
            # 1. Tìm kiếm thông tin mới nhất trên web
            search_results = ""
            with DDGS() as ddgs:
                results = list(ddgs.text(user_query, max_results=3))
                for r in results:
                    search_results += f"\n- {r['body']}"

            # 2. Đưa thông tin tìm được vào prompt cho AI
            prompt = f"""Dựa trên thông tin thời gian thực sau đây, hãy trả lời câu hỏi của người dùng. 
            Nếu thông tin không đủ, hãy dùng kiến thức của bạn.
            Thông tin tìm được: {search_results}
            
            Câu hỏi của người dùng: {user_query}"""
            
            # 3. Gửi sang Groq với model mới nhất
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            
            reply_text = chat_completion.choices[0].message.content
            await message.remove_reaction("🔍", self.bot.user)
            await message.reply(reply_text[:2000])
                
        except Exception as e:
            await message.remove_reaction("🔍", self.bot.user)
            print(f"Lỗi tìm kiếm: {e}")
            await message.reply("Tôi đang gặp chút sự cố khi tra cứu web, bạn thử lại nhé!")

async def setup(bot):
    await bot.add_cog(AIChat(bot))