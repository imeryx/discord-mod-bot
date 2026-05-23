import discord
from discord.ext import commands
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env
load_dotenv()

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Lấy chìa khóa từ file .env
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            # Khởi tạo não bộ Gemini (dùng bản 1.5 Flash cho tốc độ phản hồi cực nhanh)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self.model:
            print("-> Cog [AI Chat] Đã kết nối thành công với não bộ Gemini!")
        else:
            print("-> Cog [AI Chat] LỖI: Không tìm thấy chìa khóa GEMINI_API_KEY!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Không tự nói chuyện với chính mình hoặc bot khác
        if message.author.bot:
            return

        # Nếu có ai đó tag @Elfaria (hoặc tên bot của bạn)
        if self.bot.user in message.mentions:
            if not self.model:
                await message.reply("Khụ khụ... Não bộ của tôi chưa được gắn chìa khóa API. Hãy kiểm tra lại file .env nhé!")
                return

            # Lấy nội dung câu hỏi (lọc bỏ phần tag tên bot đi)
            user_query = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            
            if not user_query:
                await message.reply("Bạn gọi tôi có việc gì không? Thử hỏi tôi một câu xem!")
                return

            try:
                # Thả icon bộ não để báo cho người dùng biết bot đang suy nghĩ
                await message.add_reaction("🧠")
                
                # Gửi câu hỏi lên máy chủ của Google
                response = self.model.generate_content(user_query)
                
                # Gỡ icon bộ não xuống
                try: await message.remove_reaction("🧠", self.bot.user)
                except: pass
                
                # Lấy câu trả lời
                reply_text = response.text
                
                # Discord giới hạn 2000 ký tự mỗi tin nhắn, nên nếu AI trả lời dài quá thì cắt bớt
                if len(reply_text) > 2000:
                    reply_text = reply_text[:1995] + "..."
                    
                await message.reply(reply_text)
                
            except Exception as e:
                print(f"Lỗi hệ thống AI: {e}")
                try: await message.remove_reaction("🧠", self.bot.user)
                except: pass
                await message.reply("Oáp... Não bộ tôi đang bị quá tải hoặc đường truyền có vấn đề. Bạn đợi chút rồi hỏi lại nhé!")

async def setup(bot):
    await bot.add_cog(AIChat(bot))