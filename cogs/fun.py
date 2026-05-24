import discord
from discord.ext import commands
import random
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import json
import requests 

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

        # Danh sách URL ảnh anime nền đẹp (Unsplash, size 700x300)
        self.anime_backgrounds = [
            "https://images.unsplash.com/photo-1581833971358-2c8b550f87b3?q=80&w=700&h=300&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1543160897-40b48f6f5773?q=80&w=700&h=300&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1605370824036-7c0b05b45c22?q=80&w=700&h=300&auto=format&fit=crop"
        ]

    def create_ship_image(self, avatar1_bytes, avatar2_bytes, percentage):
        """Hàm xử lý đồ họa: Cắt ảnh tròn, trái tim trong suốt, nền anime ngẫu nhiên"""
        # 1. Tải ảnh nền anime ngẫu nhiên
        bg_url = random.choice(self.anime_backgrounds)
        bg_response = requests.get(bg_url)
        bg_img = Image.open(io.BytesIO(bg_response.content)).convert("RGBA")

        # 2. Xử lý avatar (cắt tròn)
        img1 = Image.open(io.BytesIO(avatar1_bytes)).convert("RGBA").resize((200, 200))
        img2 = Image.open(io.BytesIO(avatar2_bytes)).convert("RGBA").resize((200, 200))

        # Tạo mặt nạ hình tròn để cắt
        mask_circle = Image.new('L', (200, 200), 0)
        draw_circle = ImageDraw.Draw(mask_circle)
        draw_circle.ellipse((0, 0, 200, 200), fill=255)

        # 3. Tạo lớp phủ đen trong suốt
        overlay = Image.new('RGBA', (700, 300), (43, 45, 49, 255))

        # 4. Cắt hình trái tim trong suốt ở giữa lớp phủ
        heart_mask_size = (160, 160)
        mask_heart = Image.new('L', heart_mask_size, 0)
        draw_heart = ImageDraw.Draw(mask_heart)
        # Vẽ trái tim tương đối khớp với vùng 160x160
        draw_heart.rectangle(((40, 40), (120, 120)), fill=255)
        draw_heart.ellipse(((0, 40), (80, 120)), fill=255)
        draw_heart.ellipse(((40, 0), (120, 80)), fill=255)

        # Căn chỉnh vị trí mặt nạ trái tim (350 - 80, 150 - 80) = (270, 70)
        overlay.paste((0, 0, 0, 0), (270, 70), mask_heart) # Dán trong suốt với mặt nạ

        # 5. Dán lớp phủ lên ảnh nền anime
        bg_img.paste(overlay, (0, 0), overlay)

        # 6. Dán 2 avatar cắt tròn lên lớp phủ ở 2 bên
        bg_img.paste(img1, (50, 50), mask_circle)
        bg_img.paste(img2, (450, 50), mask_circle)

        # 7. Viết số % vào giữa
        draw_text = ImageDraw.Draw(bg_img)

        try:
            font = ImageFont.truetype(self.font_path, 60)
        except:
            font = ImageFont.load_default()
        
        # Căn giữa text %
        text = f"{percentage}%"
        bbox = draw_text.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = 350 - (text_width / 2)
        text_y = 150 - (text_height / 2) - 10 

        draw_text.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))

        # Xuất ảnh PNG
        buffer = io.BytesIO()
        bg_img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    # Giới hạn mỗi người dùng 1 lần / 10 giây
    @commands.command(name="ship")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ship(self, ctx, user: discord.Member = None):
        if ctx.guild and not is_module_enabled(ctx.guild.id, "fun_commands"):
            return

        user1 = ctx.author
        user2 = user if user else random.choice([m for m in ctx.guild.members if not m.bot and m != user1])

        if user1 == user2:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("Self-love is great, but this command is for shipping with someone else! 😅")
            return

        processing_msg = await ctx.send("💖 Calculating the alignment of the stars...")

        # 1. Quay xổ số ngẫu nhiên
        percentage = random.randint(0, 100)

        # 2. Tạo tên ghép
        name1 = user1.display_name
        name2 = user2.display_name
        ship_name = name1[:len(name1)//2] + name2[len(name2)//2:]

        # 3. Câu chúc Tiếng Anh
        if percentage >= 90:
            quote = "A match made in heaven! You two are meant to be. 🥰"
        elif percentage >= 70:
            quote = "Looking great! There's a really strong connection here. 💕"
        elif percentage >= 40:
            quote = "There's a spark! It might take some work, but who knows? 🤔"
        elif percentage >= 20:
            quote = "Opposites attract? Maybe, but this looks like a bumpy ride... 😅"
        else:
            quote = "Water and oil... It's probably best to just stay friends. 💔"

        # 4. Lấy avatar và xử lý
        try:
            av1_bytes = await user1.display_avatar.replace(size=256, format="png").read()
            av2_bytes = await user2.display_avatar.replace(size=256, format="png").read()
            
            image_buffer = self.create_ship_image(av1_bytes, av2_bytes, percentage)
            file = discord.File(image_buffer, filename="ship.png")

            # 5. Đóng gói Embed (Đã đổi toàn bộ sang Tiếng Anh)
            embed = discord.Embed(title=f"The name of the ship is {ship_name.capitalize()}! 💞", description=quote, color=0xED4245)
            embed.add_field(name="Compatibility", value=f"**{percentage}%**", inline=False)
            embed.set_image(url="attachment://ship.png")
            
            await processing_msg.delete()
            await ctx.send(content=f"{user1.mention} x {user2.mention}", file=file, embed=embed)
        except Exception as e:
            await processing_msg.edit(content="⚠️ An error occurred while fetching avatars. Please try again later.")
            print(f"Lỗi lệnh ship: {e}")

    # Bắt lỗi khi chưa hết thời gian hồi chiêu
    @ship.error
    async def ship_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Whoa there! The matchmaking service is on cooldown. Try again in **{error.retry_after:.1f}s**.")
        else:
            print(f"Ship Error: {error}")

async def setup(bot):
    await bot.add_cog(FunCommands(bot))