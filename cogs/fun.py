import discord
from discord.ext import commands
import random
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import json

# Hàm kiểm tra trạng thái bật/tắt từ Web Dashboard
def is_module_enabled(guild_id, module_name):
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get(str(guild_id), {}).get("modules", {}).get(module_name, True)
    except Exception:
        pass
    return True

class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Tự động tải Font chữ Arial nếu VPS chưa có để vẽ % lên ảnh
        self.font_path = "arial.ttf"
        if not os.path.exists(self.font_path):
            try:
                urllib.request.urlretrieve("https://github.com/matomo-org/travis-scripts/raw/master/fonts/Arial.ttf", self.font_path)
            except Exception as e:
                print(f"Không thể tải font: {e}")

    def create_ship_image(self, avatar1_bytes, avatar2_bytes, percentage):
        """Hàm xử lý đồ họa: Cắt ảnh tròn và ghép nền"""
        img1 = Image.open(io.BytesIO(avatar1_bytes)).convert("RGBA").resize((200, 200))
        img2 = Image.open(io.BytesIO(avatar2_bytes)).convert("RGBA").resize((200, 200))

        # Tạo mặt nạ hình tròn để cắt
        mask = Image.new('L', (200, 200), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 200, 200), fill=255)

        # Nền đen xám chuẩn Discord
        bg = Image.new('RGBA', (700, 300), (43, 45, 49, 255))

        bg.paste(img1, (50, 50), mask)
        bg.paste(img2, (450, 50), mask)

        # Vòng tròn đỏ ở giữa
        draw_bg = ImageDraw.Draw(bg)
        draw_bg.ellipse((270, 70, 430, 230), fill=(237, 66, 69, 255))

        # Font chữ
        try:
            font = ImageFont.truetype(self.font_path, 60)
        except:
            font = ImageFont.load_default()
        
        # Căn giữa text %
        text = f"{percentage}%"
        bbox = draw_bg.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = 350 - (text_width / 2)
        text_y = 150 - (text_height / 2) - 10 

        draw_bg.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))

        # Xuất ảnh
        buffer = io.BytesIO()
        bg.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    # Giới hạn mỗi người dùng 1 lần / 10 giây
    @commands.command(name="ship")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ship(self, ctx, user: discord.Member = None):
        # Kiểm tra tính năng có bị tắt trên web không
        if ctx.guild and not is_module_enabled(ctx.guild.id, "fun_commands"):
            return

        user1 = ctx.author
        user2 = user if user else random.choice([m for m in ctx.guild.members if not m.bot and m != user1])

        if user1 == user2:
            # Reset cooldown nếu gọi lỗi (để user không bị phạt oan)
            ctx.command.reset_cooldown(ctx)
            await ctx.send("Tự yêu bản thân là tốt, nhưng lệnh này để ghép đôi với người khác cơ! 😅")
            return

        processing_msg = await ctx.send("💖 Đang tính toán mức độ hòa hợp của các vì sao...")

        # 1. Quay xổ số nhân phẩm ngẫu nhiên 100%
        percentage = random.randint(0, 100)

        # 2. Tạo tên ghép
        name1 = user1.display_name
        name2 = user2.display_name
        ship_name = name1[:len(name1)//2] + name2[len(name2)//2:]

        # 3. Câu chúc
        if percentage >= 90:
            quote = "Một cặp trời sinh! Cưới ngay kẻo lỡ. 🥰"
        elif percentage >= 70:
            quote = "Đẹp đôi lắm đó! Hai bạn rất hiểu nhau. 💕"
        elif percentage >= 40:
            quote = "Có chút tia hy vọng đấy. Hãy thử tìm hiểu nhau xem! 🤔"
        elif percentage >= 20:
            quote = "Trái dấu thì hút nhau? Nhưng case này có vẻ căng... 😅"
        else:
            quote = "Nước biển và dầu hỏa... Làm lốp là ngon luôn 💔"

        # 4. Lấy avatar và xử lý
        try:
            av1_bytes = await user1.display_avatar.replace(size=256, format="png").read()
            av2_bytes = await user2.display_avatar.replace(size=256, format="png").read()
            
            image_buffer = self.create_ship_image(av1_bytes, av2_bytes, percentage)
            file = discord.File(image_buffer, filename="ship.png")

            # 5. Đóng gói Embed
            embed = discord.Embed(title=f"Khớp lệnh: {ship_name.capitalize()}! 💞", description=quote, color=0xED4245)
            embed.add_field(name="Độ tương thích", value=f"**{percentage}%**", inline=False)
            embed.set_image(url="attachment://ship.png")
            
            await processing_msg.delete()
            await ctx.send(content=f"{user1.mention} x {user2.mention}", file=file, embed=embed)
        except Exception as e:
            await processing_msg.edit(content="⚠️ Đã có lỗi xảy ra khi tải ảnh đại diện, vui lòng thử lại sau.")
            print(f"Lỗi lệnh ship: {e}")

    # Bắt lỗi khi chưa hết thời gian hồi chiêu
    @ship.error
    async def ship_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Từ từ thôi bạn ơi! Tính năng ghép đôi đang quá tải, vui lòng thử lại sau **{error.retry_after:.1f} giây** nữa nhé.")
        else:
            # In ra console nếu có lỗi khác
            print(f"Ship Error: {error}")

async def setup(bot):
    await bot.add_cog(FunCommands(bot))