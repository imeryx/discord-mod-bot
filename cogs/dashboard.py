import discord
from discord.ext import commands
import requests
import os
import io
import json
from dotenv import load_dotenv

load_dotenv()

# Hàm kiểm tra trạng thái bật/tắt theo ID Server (guild_id)
def is_module_enabled(guild_id, module_name):
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                # Đọc cấu hình theo ID Server, nếu không có dữ liệu thì mặc định là True (Bật)
                return config.get(str(guild_id), {}).get("modules", {}).get(module_name, True)
    except Exception as e:
        print(f"Lỗi đọc config.json: {e}")
    return True

class ImageTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("REMOVEBG_API_KEY")

    @commands.command(name="tachnen", aliases=["removebg", "bgremove"])
    async def remove_background(self, ctx):
        # Kiểm tra trạng thái Module dựa trên ID của Server hiện tại
        if ctx.guild and not is_module_enabled(ctx.guild.id, "image_tools"):
            await ctx.send("❌ Tính năng Tách Nền Ảnh hiện đang bị Admin tắt trên server này.")
            return

        if not ctx.message.attachments:
            await ctx.send("⚠️ Bạn cần gửi kèm một bức ảnh cùng với lệnh `!tachnen` nhé!")
            return

        attachment = ctx.message.attachments[0]
        
        if not attachment.content_type.startswith("image/"):
            await ctx.send("⚠️ File bạn gửi không phải là định dạng ảnh hợp lệ.")
            return

        if not self.api_key:
            await ctx.send("⚠️ Lỗi: Chưa cấu hình API Key cho remove.bg.")
            return

        processing_msg = await ctx.send("⏳ Đang gửi ảnh sang máy chủ remove.bg để xử lý...")
        await ctx.message.add_reaction("✂️")

        try:
            image_bytes = await attachment.read()
            response = requests.post(
                'https://api.remove.bg/v1.0/removebg',
                files={'image_file': image_bytes},
                data={'size': 'auto'},
                headers={'X-Api-Key': self.api_key},
            )

            if response.status_code == requests.codes.ok:
                result_image = discord.File(io.BytesIO(response.content), filename=f"tachnen_{attachment.filename}.png")
                await ctx.message.remove_reaction("✂️", self.bot.user)
                await processing_msg.delete()
                await ctx.send(content=f"✅ Xong ngay! Trả ảnh đã tách nền cho {ctx.author.mention}:", file=result_image)
            else:
                await ctx.message.remove_reaction("✂️", self.bot.user)
                await processing_msg.edit(content=f"⚠️ Máy chủ API báo lỗi (Code {response.status_code}).")
                
        except Exception as e:
            await ctx.message.remove_reaction("✂️", self.bot.user)
            await processing_msg.edit(content="⚠️ Không thể kết nối với API tách nền, thử lại sau nhé!")

async def setup(bot):
    await bot.add_cog(ImageTools(bot))