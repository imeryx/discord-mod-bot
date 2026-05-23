import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import database

# Tải các biến môi trường từ file .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Hàm tự động tìm prefix tương ứng với server
def get_server_prefix(bot, message):
    if not message.guild:
        return "!"
    return database.get_prefix(message.guild.id)

class BotEnigma(commands.Bot):
    def __init__(self):
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
                    print(f'-> Đã tải module: {filename}')
                except Exception as e:
                    print(f'Lỗi khi load module {filename}: {e}')
                    
        print("-> Cấu hình bot sẵn sàng! (Đã tắt đồng bộ tự động để tránh Rate Limit)")

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
    
    # Tạo một lệnh ẩn bằng prefix để bạn đồng bộ thủ công khi cần
    @bot.command(name="sync")
    @commands.is_owner() # Chỉ có bạn (chủ bot) mới dùng được lệnh này
    async def sync_commands(ctx):
        await bot.tree.sync()
        await ctx.send("-> Đã đồng bộ Slash Commands toàn cầu thành công!")

    bot.run(TOKEN)