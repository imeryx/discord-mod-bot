import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import database

# Tải các biến môi trường từ file .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ĐIỀN ID SERVER TEST CỦA BẠN VÀO ĐÂY ĐỂ DỌN LỆNH LẶP
TEST_GUILD_ID = 1056226442146492506 
# Hàm tự động tìm prefix tương ứng với server
def get_server_prefix(bot, message):
    # Nếu nhắn tin riêng DM cho bot thì dùng dấu !
    if not message.guild:
        return "!"
    # Lấy prefix từ database ra
    return database.get_prefix(message.guild.id)
class BotEnigma(commands.Bot):
    def __init__(self):
        # Thiết lập prefix và intents
        super().__init__(
            command_prefix=get_server_prefix, 
            intents=discord.Intents.all(),
            help_command=None
        )

    # Hàm setup_hook chạy một lần duy nhất trước khi bot kết nối
    async def setup_hook(self):
        # 1. Khởi tạo database
        database.setup_db()
        print("-> Đã kiểm tra và khởi tạo Database thành công!")
        
        # 2. Load tất cả các module trong thư mục 'cogs'
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                except Exception as e:
                    print(f'Lỗi khi load module {filename}: {e}')
                    
        # ================= DỌN DẸP LỆNH & ĐỒNG BỘ =================
        try:
            if TEST_GUILD_ID:
                test_guild = discord.Object(id=TEST_GUILD_ID)
                
                # Xóa sạch bộ lệnh Cục bộ của riêng server test
                self.tree.clear_commands(guild=test_guild)
                await self.tree.sync(guild=test_guild)
                print(f"-> Đã xóa sạch Slash Commands cục bộ tại server test!")
            
            # Đồng bộ bộ lệnh mới nhất ra Toàn cầu
            await self.tree.sync()
            print("-> Đã đồng bộ Slash Commands toàn cầu (Có thể mất thời gian cập nhật)!")
        except Exception as e:
            print(f"Lỗi khi đồng bộ lệnh: {e}")

    # Sự kiện khi bot online thành công
    async def on_ready(self):
        print("-" * 50)
        print(f"Thành công! Bot {self.user} đã online.")
        activity = discord.Activity(type=discord.ActivityType.watching, name="/help | ElfariaBot")
        await self.change_presence(activity=activity)
        print("-> Đã thiết lập trạng thái cho bot!")
        print("-" * 50)

# Chạy bot
if __name__ == '__main__':
    bot = BotEnigma()
    bot.run(TOKEN)