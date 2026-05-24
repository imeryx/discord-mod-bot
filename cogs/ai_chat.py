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
        
        # Chỉ xử lý khi bot nằm trong danh sách được mention (bị tag trực tiếp hoặc qua tính năng Reply)
        if self.bot.user not in message.mentions: return

        # --- LOGIC LỌC REPLY THÔNG MINH ---
        # 1. Kiểm tra xem người dùng có gõ trực tiếp "@Bot" vào đoạn chat hay không
        is_explicit_mention = f"<@{self.bot.user.id}>" in message.content or f"<@!{self.bot.user.id}>" in message.content

        # 2. Nếu người dùng dùng tính năng Reply mà KHÔNG gõ "@Bot" trực tiếp vào chữ
        if message.reference is not None and not is_explicit_mention:
            try:
                # Lấy nội dung của tin nhắn gốc mà người dùng đang reply
                original_msg = message.reference.cached_message
                if original_msg is None:
                    original_msg = await message.channel.fetch_message(message.reference.message_id)
                
                # Nếu tin nhắn gốc là do bot gửi ra, VÀ nó chứa file đính kèm (TikTok) hoặc khung Embed (Ship)
                if original_msg.author == self.bot.user:
                    if original_msg.attachments or original_msg.embeds:
                        return # Lặng lẽ BỎ QUA, không gọi AI
            except Exception:
                pass 
        # ---------------------------------

        # Dọn dẹp nội dung tin nhắn (xóa chữ tag @Bot đi để gửi cho Llama 3.3 một câu hỏi sạch sẽ nhất)
        clean_content = message.content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
        
        # Nếu người dùng chỉ tag bot rồi để trống (không nói gì) thì cũng bỏ qua
        if not clean_content: return

        async with message.channel.typing():
            try:
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": clean_content}]
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