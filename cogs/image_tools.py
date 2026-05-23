import discord
from discord.ext import commands
from rembg import remove
import io
import asyncio

class ImageTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="tachnen", aliases=["removebg", "bgremove"])
    async def remove_background(self, ctx):
        """Lệnh tách nền ảnh không giới hạn (Dùng AI nội bộ)."""
        
        if not ctx.message.attachments:
            await ctx.send("⚠️ Bạn cần gửi kèm một bức ảnh cùng với lệnh `!tachnen` nhé!")
            return

        attachment = ctx.message.attachments[0]
        
        if not attachment.content_type.startswith("image/"):
            await ctx.send("⚠️ File bạn gửi không phải là định dạng ảnh hợp lệ.")
            return

        processing_msg = await ctx.send("⏳ Đang dồn sức mạnh CPU để tách nền, bạn đợi vài giây nhé...")
        await ctx.message.add_reaction("✂️")

        try:
            # 1. Tải ảnh về dưới dạng bytes
            image_bytes = await attachment.read()
            
            # 2. Chạy thuật toán tách nền. 
            # Vì đây là tác vụ nặng, ta dùng asyncio.to_thread để không làm treo bot
            output_bytes = await asyncio.to_thread(remove, image_bytes)

            # 3. Đóng gói kết quả thành file để gửi lên Discord
            result_image = discord.File(io.BytesIO(output_bytes), filename=f"tachnen_{attachment.filename}.png")
            
            # 4. Gửi kết quả
            await ctx.message.remove_reaction("✂️", self.bot.user)
            await processing_msg.delete()
            await ctx.send(content=f"✅ Đã tách nền thành công (Miễn phí & Không giới hạn) cho {ctx.author.mention}!", file=result_image)
                
        except Exception as e:
            await ctx.message.remove_reaction("✂️", self.bot.user)
            print(f"Lỗi hệ thống: {e}")
            await processing_msg.edit(content="⚠️ Ôi hỏng! Có lỗi xảy ra trong quá trình xử lý ảnh rồi.")

async def setup(bot):
    await bot.add_cog(ImageTools(bot))