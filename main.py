import discord
from discord.ext import commands
import os
import traceback  # Thư viện cực kỳ quan trọng để truy vết lỗi
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
        # Lấy ID chủ sở hữu từ file .env và ép kiểu sang số nguyên (int)
        owner_id_env = os.getenv("OWNER_ID")
        owner_ids = set()
        if owner_id_env:
            owner_ids.add(int(owner_id_env.strip()))

        super().__init__(
            command_prefix=get_server_prefix, 
            intents=discord.Intents.all(),
            help_command=None,
            owner_ids=owner_ids  
        )

    # Hàm setup_hook chạy một lần duy nhất trước khi bot kết nối
    async def setup_hook(self):
        # 1. Khởi tạo database
        database.setup_db()
        
        # 2. Load tất cả các module trong thư mục 'cogs'
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Đã tải module: {filename}')
                except Exception as e:
                    print(f'❌ Lỗi khi load module {filename}:')
                    # In ra toàn bộ chi tiết lỗi để lập trình viên dễ sửa
                    traceback.print_exc() 
                    
        print("🚀 Cấu hình bot sẵn sàng! (Đã tắt đồng bộ tự động)")

    # Sự kiện khi bot online thành công
    async def on_ready(self):
        print("-" * 50)
        print(f"🎉 Thành công! Bot {self.user} đã online.")
        activity = discord.Activity(type=discord.ActivityType.watching, name="/help | ElfariaBot")
        await self.change_presence(activity=activity)
        print("-" * 50)

# ================= TẠO THỂ THỨC BOT VÀ CÁC LỆNH GỐC =================
bot = BotEnigma()
    
# Lệnh ẩn đồng bộ Slash Commands
@bot.command(name="sync")
@commands.is_owner() # Lệnh này đã được bảo vệ tuyệt đối
async def sync_commands(ctx):
    # Trả lời trước để người dùng biết bot đang xử lý
    msg = await ctx.send("🔄 Đang tiến hành đồng bộ cây lệnh Slash...")
    try:
        synced = await bot.tree.sync()
        await msg.edit(content=f"✅ Đã đồng bộ thành công **{len(synced)}** lệnh Slash toàn cầu!")
    except Exception as e:
        await msg.edit(content=f"❌ Có lỗi xảy ra trong quá trình đồng bộ:\n```py\n{e}\n```")


# ================= KHỞI CHẠY BOT =================
if __name__ == '__main__':
    # Chạy bot bằng Token
    bot.run(TOKEN)