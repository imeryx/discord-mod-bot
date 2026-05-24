import discord
from discord.ext import commands
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import os
import urllib.request
import json
import requests
import math

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

# Hàm Toán học: Sinh ra các tọa độ đỉnh để vẽ hình trái tim hoàn hảo
def get_heart_polygon(x_center, y_center, scale):
    points = []
    for t in range(0, 360, 1): # Lấy 360 điểm để đường viền mượt nhất
        rad = math.radians(t)
        x = 16 * math.sin(rad)**3
        y = 13 * math.cos(rad) - 5 * math.cos(2*rad) - 2 * math.cos(3*rad) - math.cos(4*rad)
        points.append((x * scale, -y * scale)) # Trục Y của ảnh đi xuống nên phải đảo ngược
    
    # Căn giữa hoàn hảo đa giác trái tim vào đúng (x_center, y_center)
    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)
    
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    
    return [(p[0] - cx + x_center, p[1] - cy + y_center) for p in points]


class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.font_path = "arial.ttf"
        if not os.path.exists(self.font_path):
            try:
                urllib.request.urlretrieve("https://github.com/matomo-org/travis-scripts/raw/master/fonts/Arial.ttf", self.font_path)
            except Exception as e:
                print(f"Không thể tải font: {e}")

        # Danh sách URL ảnh anime nền chất lượng cao
        self.anime_backgrounds = [
            "https://images.unsplash.com/photo-1581833971358-2c8b550f87b3?q=80&w=700&h=300&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1543160897-40b48f6f5773?q=80&w=700&h=300&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1605370824036-7c0b05b45c22?q=80&w=700&h=300&auto=format&fit=crop",
            "https://images.unsplash.com/photo-1578632767115-351597cf2477?q=80&w=700&h=300&auto=format&fit=crop"
        ]

    def create_ship_image(self, avatar1_bytes, avatar2_bytes, percentage):
        """Hàm xử lý đồ họa nâng cao: Nền Anime Xuyên thấu"""
        
        # 1. Tải và xử lý Ảnh Nền Anime gốc (Sáng)
        bg_url = random.choice(self.anime_backgrounds)
        bg_response = requests.get(bg_url)
        base_bg = Image.open(io.BytesIO(bg_response.content)).convert("RGBA")
        
        # Crop cho chuẩn kích thước 700x300 để không bị méo ảnh
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.LANCZOS # Hỗ trợ Pillow bản cũ
        base_bg = ImageOps.fit(base_bg, (700, 300), resample_filter)

        # 2. Tạo một phiên bản Nền Tối (Lớp làm mờ đi background)
        dark_bg = base_bg.copy()
        black_overlay = Image.new('RGBA', (700, 300), (0, 0, 0, 160)) # Mức độ tối: 160/255
        dark_bg.alpha_composite(black_overlay)

        # 3. Cắt mặt nạ Trái tim (Vùng trắng sẽ hiện ảnh sáng, vùng đen hiện ảnh tối)
        mask = Image.new('L', (700, 300), 0)
        draw_mask = ImageDraw.Draw(mask)
        # Sử dụng hàm toán học để vẽ trái tim size 6 (khoảng 190x130px) ngay giữa ảnh
        heart_poly = get_heart_polygon(350, 150, 6)
        draw_mask.polygon(heart_poly, fill=255)

        # 4. Gộp ảnh lại: Bên trong tim là sáng, bên ngoài là tối
        final_bg = Image.composite(base_bg, dark_bg, mask)

        # 5. Xử lý Avatar Cắt tròn
        img1 = Image.open(io.BytesIO(avatar1_bytes)).convert("RGBA").resize((200, 200))
        img2 = Image.open(io.BytesIO(avatar2_bytes)).convert("RGBA").resize((200, 200))

        mask_circle = Image.new('L', (200, 200), 0)
        draw_circle = ImageDraw.Draw(mask_circle)
        draw_circle.ellipse((0, 0, 200, 200), fill=255)

        # Vẽ viền trắng bọc quanh Avatar cho đẹp
        draw_final = ImageDraw.Draw(final_bg)
        border = 4
        draw_final.ellipse((50-border, 50-border, 250+border, 250+border), fill="white")
        draw_final.ellipse((450-border, 50-border, 650+border, 250+border), fill="white")

        # Dán Avatar lên nền
        final_bg.paste(img1, (50, 50), mask_circle)
        final_bg.paste(img2, (450, 50), mask_circle)

        # 6. Chèn chữ % vào giữa trái tim
        try:
            font = ImageFont.truetype(self.font_path, 65)
        except:
            font = ImageFont.load_default()
        
        text = f"{percentage}%"
        bbox = draw_final.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = 350 - (text_width / 2)
        text_y = 150 - (text_height / 2) - 10 

        # Viết chữ trắng có viền đen xung quanh để dễ đọc trên nền sáng
        draw_final.text((text_x, text_y), text, font=font, fill="white", stroke_width=2, stroke_fill="black")

        buffer = io.BytesIO()
        final_bg.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    # Cập nhật thuật toán nhận diện 2 User để không bị lỗi "Tự yêu bản thân"
    @commands.command(name="ship")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ship(self, ctx, member1: discord.Member = None, member2: discord.Member = None):
        if ctx.guild and not is_module_enabled(ctx.guild.id, "fun_commands"):
            return

        # Thuật toán phân luồng ai bị ship với ai
        if member1 and member2:
            # Gõ: !ship @A @B -> Ship A với B
            user1 = member1
            user2 = member2
        elif member1:
            # Gõ: !ship @A -> Ship bản thân với A
            user1 = ctx.author
            user2 = member1
        else:
            # Gõ: !ship -> Lấy random 1 người trong server ship với bản thân
            user1 = ctx.author
            valid_members = [m for m in ctx.guild.members if not m.bot and m != user1]
            user2 = random.choice(valid_members) if valid_members else user1

        # Chặn nếu tự ship mình với mình (Gõ: !ship @Eryx @Eryx)
        if user1 == user2:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("Self-love is great, but try tagging someone else! 😅")
            return

        processing_msg = await ctx.send("💖 Calculating the alignment of the stars...")

        percentage = random.randint(0, 100)

        name1 = user1.display_name
        name2 = user2.display_name
        ship_name = name1[:len(name1)//2] + name2[len(name2)//2:]

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

        try:
            av1_bytes = await user1.display_avatar.replace(size=256, format="png").read()
            av2_bytes = await user2.display_avatar.replace(size=256, format="png").read()
            
            image_buffer = self.create_ship_image(av1_bytes, av2_bytes, percentage)
            file = discord.File(image_buffer, filename="ship.png")

            embed = discord.Embed(title=f"The name of the ship is {ship_name.capitalize()}! 💞", description=quote, color=0xED4245)
            embed.add_field(name="Compatibility", value=f"**{percentage}%**", inline=False)
            embed.set_image(url="attachment://ship.png")
            
            await processing_msg.delete()
            await ctx.send(content=f"{user1.mention} x {user2.mention}", file=file, embed=embed)
        except Exception as e:
            await processing_msg.edit(content="⚠️ An error occurred while fetching avatars. Please try again later.")
            print(f"Lỗi lệnh ship: {e}")

    @ship.error
    async def ship_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Whoa there! The matchmaking service is on cooldown. Try again in **{error.retry_after:.1f}s**.")
        else:
            print(f"Ship Error: {error}")

async def setup(bot):
    await bot.add_cog(FunCommands(bot))