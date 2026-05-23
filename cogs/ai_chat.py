import discord
from discord.ext import commands
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Khởi tạo client Groq với API Key từ file .env
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        # Lưu trữ lịch sử chat: {user_id: [danh_sách_tin_nhắn]}
        self.chat_histories = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bỏ qua tin nhắn của chính bot hoặc tin nhắn không tag bot
        if message.author.bot or self.bot.user not in message.mentions:
            return

        user_id = message.author.id
        user_query = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
        
        if not user_query:
            await message.reply("Chào bạn! Bạn cần tôi giúp gì không?")
            return

        # Khởi tạo lịch sử nếu người dùng mới chat lần đầu
        if user_id not in self.chat_histories:
            self.chat_histories[user_id] = [
                {"role": "system", "content": "Bạn là Elfaria, một trợ lý thông minh và thân thiện."}
            ]

        # Thêm câu hỏi của người dùng vào lịch sử
        self.chat_histories[user_id].append({"role": "user", "content": user_query})

        # Giới hạn lịch sử: Chỉ giữ 10 tin nhắn gần nhất (5 user + 5 bot) để tránh quá tải
        if len(self.chat_histories[user_id]) > 11:
            self.chat_histories[user_id] = [self.chat_histories[user_id][0]] + self.chat_histories[user_id][-10:]

        try:
            await message.add_reaction("🧠")
            
            # Gửi yêu cầu đến Groq (dùng model Llama 3 8B cực nhanh)
            chat_completion = self.client.chat.completions.create(
                messages=self.chat_histories[user_id],
                model="llama-3.3-70b-versatile",
            )
            
            reply_text = chat_completion.choices[0].message.content
            
            # Lưu câu trả lời của bot vào lịch sử
            self.chat_histories[user_id].append({"role": "assistant", "content": reply_text})
            
            await message.remove_reaction("🧠", self.bot.user)
            
            # Phản hồi lại Discord (cắt ngắn nếu quá 2000 ký tự)
            await message.reply(reply_text[:2000])
                
        except Exception as e:
            await message.remove_reaction("🧠", self.bot.user)
            print(f"Lỗi AI: {e}")
            await message.reply("Bộ não AI của tôi đang tạm nghỉ, bạn thử lại sau nhé!")

async def setup(bot):
    await bot.add_cog(AIChat(bot))