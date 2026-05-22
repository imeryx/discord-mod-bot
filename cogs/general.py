import discord
from discord.ext import commands
import random

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [General] (Lệnh cổ điển) đã được tải!")

    # ================= 1. LỆNH PING =================
    @commands.command(name="ping", help="Kiểm tra độ trễ của bot")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"🏓 Pong! Độ trễ của bot hiện tại là: **{latency}ms**")

    # ================= 2. LỆNH HELLO =================
    @commands.command(name="hello", help="Bot gửi lời chào")
    async def hello(self, ctx):
        await ctx.send(f"👋 Chào bạn {ctx.author.mention}!")

    # ================= 3. LỆNH AVATAR =================
    @commands.command(name="avt", help="Lấy ảnh đại diện của một người")
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author 
        embed = discord.Embed(title=f"Ảnh đại diện của {member.display_name}", color=discord.Color.blue())
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)

    # ================= 4. LỆNH CHOOSE (CÁCH NHAU BẰNG DẤU CÁCH) =================
    @commands.command(name="choose", help="Chọn ngẫu nhiên từ danh sách (ngăn cách bằng dấu cách)")
    async def choose(self, ctx, *choices: str):
        # Kiểm tra xem người dùng có nhập đủ lựa chọn không
        if len(choices) < 2:
            return await ctx.send("❌ Hãy nhập ít nhất 2 lựa chọn, ngăn cách nhau bằng dấu cách. Ví dụ: `-choose Phở Cơm`")
        
        chosen = random.choice(choices)
        await ctx.send(f"🤔 Sau một hồi suy nghĩ, tôi chọn: **{chosen}**")

async def setup(bot):
    await bot.add_cog(General(bot))