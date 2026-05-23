import discord
from discord.ext import commands
import requests
import os
import io
from dotenv import load_dotenv

load_dotenv()

class ImageTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("REMOVEBG_API_KEY")

    @commands.command(name="tachnen", aliases=["removebg", "bgremove"])
    async def remove_background(self, ctx):
        """Lệnh tách nền ảnh qua remove.bg API."""
        if not ctx.message.attachments:
            await ctx.send("⚠️ Bạn cần gửi kèm một bức ảnh cùng với lệnh `!tachnen` nhé!")
            return

        attachment = ctx.message.attachments[0]
        
        if not attachment.content_type.startswith("image/"):
            await ctx.send("⚠️ File bạn gửi không phải là định dạng ảnh hợp lệ.")
            return

        if not self.api_key:
            await ctx.send("⚠️ Lỗi: Chưa cấu hình API Key cho remove.bg trong file .env của máy chủ.")
            return

        processing_msg = await ctx.send("⏳ Đang gửi ảnh sang máy chủ remove.bg để xử lý, đợi vài giây nhé...")
        await ctx.message.add_reaction("✂️")

        try:
            image_bytes = await attachment.read()
            
            # Gửi dữ liệu sang API của remove.bg
            response = requests.post(
                'https://api.remove.bg/v1.0/removebg',
                files={'image_file': image_bytes},
                data={'size': 'auto'},
                headers={'X-Api-Key': self.api_key},
            )

            # Xử lý kết quả trả về
            if response.status_code == requests.codes.ok:
                result_image = discord.File(io.BytesIO(response.content), filename=f"tachnen_{attachment.filename}.png")
                await ctx.message.remove_reaction("✂️", self.bot.user)
                await processing_msg.delete()
                await ctx.send(content=f"✅ Xong ngay! Trả ảnh đã tách nền cực mượt cho {ctx.author.mention} nè:", file=result_image)
            else:
                await ctx.message.remove_reaction("✂️", self.bot.user)
                await processing_msg.edit(content=f"⚠️ Máy chủ API báo lỗi (Code {response.status_code}). Có thể bạn đã dùng hết 50 lượt miễn phí tháng này!")
                
        except Exception as e:
            await ctx.message.remove_reaction("✂️", self.bot.user)
            print(f"Lỗi kết nối: {e}")
            await processing_msg.edit(content="⚠️ Không thể kết nối với API tách nền, thử lại sau nhé!")

async def setup(bot):
    await bot.add_cog(ImageTools(bot))