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
        self.chat_histories = {}

    async def search_web(self, query):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                return "\n".join([r['body'] for r in results])
        except:
            return ""

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or self.bot.user not in message.mentions:
            return

        user_id = message.author.id
        user_query = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        
        if not user_query: return

        try:
            await message.add_reaction("🔍")
            
            # Tự động tìm kiếm web trước khi trả lời
            web_info = await self.search_web(user_query)
            
            prompt = f"Thông tin mới nhất từ web: {web_info}\n\nCâu hỏi: {user_query}"
            
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            
            reply_text = chat_completion.choices[0].message.content
            await message.remove_reaction("🔍", self.bot.user)
            await message.reply(reply_text[:2000])
                
        except Exception as e:
            await message.remove_reaction("🔍", self.bot.user)
            await message.reply("Tôi đang bận tìm kiếm thông tin, thử lại nhé!")

async def setup(bot):
    await bot.add_cog(AIChat(bot))