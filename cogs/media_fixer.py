import discord
from discord.ext import commands
import re

class MediaFixer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pattern = re.compile(r'https?://(?:www\.)?(x\.com|twitter\.com|instagram\.com|reddit\.com)/[^\s]+')

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Media Fixer] Đã sẵn sàng (Bản tự động cắt đuôi link rác)!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        match = self.pattern.search(message.content)
        if match:
            url = match.group(0)
            
            # Vũ khí 1: Cắt bỏ toàn bộ phần mã theo dõi (tracking) từ dấu '?' trở đi
            clean_url = url.split("?")[0]
            domain = match.group(1)
            fixed_url = clean_url

            # ================= BỘ CHUYỂN ĐỔI LINK =================
            if domain in ["x.com", "twitter.com"]:
                fixed_url = clean_url.replace("x.com", "fxtwitter.com").replace("twitter.com", "fxtwitter.com")
            
            elif domain == "instagram.com":
                # Vũ khí 2: Sử dụng zzinstagram (tự động định tuyến máy chủ mượt nhất)
                fixed_url = clean_url.replace("instagram.com", "zzinstagram.com")
            
            elif domain == "reddit.com":
                fixed_url = clean_url.replace("reddit.com", "rxddit.com")

            if fixed_url != url:
                try: 
                    await message.edit(suppress=True)
                except: 
                    pass
                
                await message.reply(content=f"🎬 **Media từ {message.author.mention}:**\n{fixed_url}")

async def setup(bot):
    await bot.add_cog(MediaFixer(bot))