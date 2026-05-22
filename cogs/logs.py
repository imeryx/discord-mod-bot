import discord
from discord.ext import commands
import database

class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Logs] đã bật chế độ giám sát sự kiện!")

    # ================= 1. GHI LOG TIN NHẮN BỊ XÓA =================
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        # Bỏ qua tin nhắn của bot hoặc tin nhắn nhắn riêng (DM)
        if message.author.bot or not message.guild:
            return

        # Lấy ID kênh log từ Database
        log_channel_id = database.get_log_channel(message.guild.id)
        if not log_channel_id:
            return # Nếu server chưa cài đặt kênh log thì bỏ qua

        # Tìm kênh log trong server
        log_channel = message.guild.get_channel(log_channel_id)
        if not log_channel:
            return

        embed = discord.Embed(
            title="🗑️ Tin nhắn bị xóa",
            description=f"Tin nhắn của {message.author.mention} vừa bị xóa tại kênh {message.channel.mention}",
            color=discord.Color.red()
        )
        
        # Xử lý trường hợp người dùng chỉ gửi ảnh/sticker (không có chữ)
        content = message.content if message.content else "*Tin nhắn không có văn bản (có thể là hình ảnh/sticker)*"
        
        # Cắt chuỗi ở mức 1000 ký tự để tránh lỗi vượt quá giới hạn của Discord Embed
        embed.add_field(name="Nội dung:", value=content[:1000], inline=False)
        
        await log_channel.send(embed=embed)

    # ================= 2. GHI LOG TIN NHẮN BỊ CHỈNH SỬA =================
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild:
            return
        
        # Quan trọng: Discord đôi khi tự kích hoạt event Edit khi nó load xong link preview hoặc ảnh.
        # Ta cần kiểm tra xem nội dung chữ có thực sự thay đổi không.
        if before.content == after.content:
            return

        log_channel_id = database.get_log_channel(before.guild.id)
        if not log_channel_id:
            return

        log_channel = before.guild.get_channel(log_channel_id)
        if not log_channel:
            return

        embed = discord.Embed(
            title="✏️ Tin nhắn bị chỉnh sửa",
            description=f"Tin nhắn của {before.author.mention} được sửa tại {before.channel.mention}\n[🔗 Bấm vào đây để nhảy đến tin nhắn]({after.jump_url})",
            color=discord.Color.gold()
        )
        
        before_content = before.content if before.content else "*Trống*"
        after_content = after.content if after.content else "*Trống*"
        
        embed.add_field(name="Nội dung CŨ:", value=before_content[:1000], inline=False)
        embed.add_field(name="Nội dung MỚI:", value=after_content[:1000], inline=False)
        
        await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Logs(bot))