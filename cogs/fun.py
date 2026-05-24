import discord
from discord.ext import commands
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter # Thêm ImageFilter
import io
import os
import urllib.request
import json
import requests
import math

# File cấu hình riêng cho lệnh Ship
SETTINGS_FILE = "ship_settings.json"
DEFAULT_BG = "https://images.unsplash.com/photo-1581833971358-2c8b550f87b3?q=80&w=700&h=300&auto=format&fit=crop"

# Hàm load/save cấu hình nền
def load_ship_config():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"background_url": DEFAULT_BG}, f)
        return DEFAULT_BG
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("background_url", DEFAULT_BG)

def save_ship_config(url):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump({"background_url": url}, f)

# Hàm kiểm tra trạng thái tắt bật module từ Dashboard (nếu có)
def is_module_enabled(guild_id, module_name):
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get(str(guild_id), {}).get("modules", {}).get(module_name, True)
    except Exception:
        pass
    return True

# Hàm vẽ đa giác trái tim perfect
def get_heart_polygon(x_center, y_center, scale):
    points = []
    for t in range(0, 360, 2): 
        rad = math.radians(t)
        x = 16 * math.sin(rad)**3
        y = 13 * math.cos(rad) - 5 * math.cos(2*rad) - 2 * math.cos(3*rad) - math.cos(4*rad)
        points.append((x * scale, -y * scale))
    
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

    # --- HÀM XỬ LÝ ĐỒ HỌA MỚI: Glassmorphism Heart ---
    def create_ship_image(self, avatar1_bytes, avatar2_bytes, percentage, bg_url):
        """Vẽ trái tim trong suốt dạng kính (Glassmorphism)"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        }
        
        # 1. Xử lý Ảnh Nền Tùy Chỉnh (Sáng)
        try:
            bg_response = requests.get(bg_url, headers=headers, timeout=5)
            bg_response.raise_for_status() 
            base_bg = Image.open(io.BytesIO(bg_response.content)).convert("RGBA")
            base_bg = ImageOps.fit(base_bg, (700, 300), Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"Lỗi tải nền tuỳ chỉnh, dùng nền dự phòng: {e}")
            base_bg = Image.new('RGBA', (700, 300), (43, 45, 49, 255)) # Nền Discord

        # 2. Tạo một phiên bản Nền Mờ (Lớp kính mờ)
        blurry_bg = base_bg.copy().filter(ImageFilter.GaussianBlur(radius=15))

        # 3. Tạo nền tối (Outside Heart)
        dark_overlay = Image.new('RGBA', (700, 300), (0, 0, 0, 180)) # Nền tối xung quanh: 180/255
        dark_bg = base_bg.copy()
        dark_bg.alpha_composite(dark_overlay)

        # 4. Cắt mặt nạ Trái tim
        mask = Image.new('L', (700, 300), 0)
        draw_mask = ImageDraw.Draw(mask)
        heart_poly = get_heart_polygon(350, 150, 6) # Size 6
        draw_mask.polygon(heart_poly, fill=255)

        # 5. Gộp ảnh Glassmorphism: Bên trong tim là ảnh mờ (light), bên ngoài là ảnh tối
        final_bg = Image.composite(blurry_bg, dark_bg, mask)

        # 6. Vẽ VIỀN TRẮNG bọc quanh trái tim Glassmorphism
        draw_final = ImageDraw.Draw(final_bg)
        draw_final.polygon(heart_poly, outline=(255, 255, 255, 200), width=4) # Viền trắng hơi trong suốt

        # 7. Xử lý Avatar
        img1 = Image.open(io.BytesIO(avatar1_bytes)).convert("RGBA").resize((200, 200))
        img2 = Image.open(io.BytesIO(avatar2_bytes)).convert("RGBA").resize((200, 200))

        mask_circle = Image.new('L', (200, 200), 0)
        draw_circle = ImageDraw.Draw(mask_circle)
        draw_circle.ellipse((0, 0, 200, 200), fill=255)

        border = 4
        draw_final.ellipse((50-border, 50-border, 250+border, 250+border), fill="white")
        draw_final.ellipse((450-border, 50-border, 650+border, 250+border), fill="white")

        final_bg.paste(img1, (50, 50), mask_circle)
        final_bg.paste(img2, (450, 50), mask_circle)

        # 8. Chèn chữ % 
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

        # Chữ trắng viền đen
        draw_final.text((text_x, text_y), text, font=font, fill="white", stroke_width=2, stroke_fill="black")

        buffer = io.BytesIO()
        final_bg.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer


    @commands.command(name="ship")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def ship(self, ctx, member1: discord.Member = None, member2: discord.Member = None):
        if ctx.guild and not is_module_enabled(ctx.guild.id, "fun_commands"):
            return

        if member1 and member2:
            user1 = member1
            user2 = member2
        elif member1:
            user1 = ctx.author
            user2 = member1
        else:
            user1 = ctx.author
            valid_members = [m for m in ctx.guild.members if not m.bot and m != user1]
            user2 = random.choice(valid_members) if valid_members else user1

        if user1 == user2:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("Self-love is great, but try tagging someone else! 😅")
            return

        processing_msg = await ctx.send("💖 Calculating the alignment of the stars...")

        percentage = random.randint(0, 100)

        name1 = user1.display_name
        name2 = user2.display_name
        ship_name = name1[:len(name1)//2] + name2[len(name2)//2:]

        # Load Nền tùy chỉnh
        bg_url = load_ship_config()

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
            
            # Truyền bg_url vào hàm vẽ
            image_buffer = self.create_ship_image(av1_bytes, av2_bytes, percentage, bg_url)
            file = discord.File(image_buffer, filename="ship.png")

            embed = discord.Embed(title=f"The name of the ship is {ship_name.capitalize()}! 💞", description=quote, color=0xED4245)
            embed.add_field(name="Compatibility", value=f"**{percentage}%**", inline=False)
            embed.set_image(url="attachment://ship.png")
            
            await processing_msg.delete()
            await ctx.send(content=f"{user1.mention} x {user2.mention}", file=file, embed=embed)
        except Exception as e:
            await processing_msg.edit(content="⚠️ An error occurred while fetching avatars or processing the image. Please try again later.")
            print(f"Lỗi lệnh ship: {e}")

    # --- LỆNH MỚI: TÙY CHỈNH ẢNH NỀN (CHỈ CHỦ SỞ HỮU GÕ ĐƯỢC) ---
    @commands.command(name="shipbg")
    @commands.is_owner() # Thẻ chặn người dùng chỉ chủ bot gõ được
    async def set_ship_background(self, ctx, url: str):
        """[Owner Only] Thay đổi ảnh nền tùy chỉnh cho lệnh !ship"""
        save_ship_config(url)
        await ctx.send(f"✅ Ship background updated successfully by the owner!\nNew URL: `<{url}>`")

    @set_ship_background.error
    async def set_ship_background_error(self, ctx, error):
        if isinstance(error, commands.NotOwner):
            await ctx.send("❌ An error occurred: You are not authorized to run this command. Only the bot owner can change the background.")
        else:
            await ctx.send(f"An error occurred: `{error}`")

    @ship.error
    async def ship_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Whoa there! The matchmaking service is on cooldown. Try again in **{error.retry_after:.1f}s**.")
        else:
            print(f"Ship Error: {error}")

async def setup(bot):
    await bot.add_cog(FunCommands(bot))