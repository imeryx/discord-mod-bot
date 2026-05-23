import discord
from discord.ext import commands
import re

class MediaFixer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Regex thông minh để "bắt" link X, Twitter, Instagram, Reddit
        self.pattern = re.compile(r'https?://(?:www\.)?(x\.com|twitter\.com|instagram\.com|reddit\.com)/[^\s]+')

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Media Fixer] Đã sẵn sàng (Hỗ trợ X, Instagram, Reddit)!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        match = self.pattern.search(message.content)
        if match:
            url = match.group(0)
            domain = match.group(1)
            fixed_url = url

            # ================= BỘ CHUYỂN ĐỔI LINK =================
            if domain in ["x.com", "twitter.com"]:
                # Đổi X/Twitter sang fxtwitter để hiện video/ảnh
                fixed_url = url.replace("x.com", "fxtwitter.com").replace("twitter.com", "fxtwitter.com")
            
            elif domain == "instagram.com":
                # Đổi Instagram sang ddinstagram để hiện Reels/Post
                fixed_url = url.replace("instagram.com", "ddinstagram.com")
            
            elif domain == "reddit.com":
                # Đổi Reddit sang rxddit để phát thẳng video không bị lỗi audio
                fixed_url = url.replace("reddit.com", "rxddit.com")

            # Nếu link có sự thay đổi, tiến hành gửi lại lên Discord
            if fixed_url != url:
                try: 
                    await message.edit(suppress=True) # Ẩn cái link lỗi mặc định của Discord
                except: 
                    pass
                
                await message.reply(content=f"🎬 **Media từ {message.author.mention}:**\n{fixed_url}")

async def setup(bot):
    await bot.add_cog(MediaFixer(bot))