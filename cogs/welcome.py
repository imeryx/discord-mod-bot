import discord
from discord.ext import commands
from discord import app_commands
import database

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Welcome/Goodbye] đã sẵn sàng với cấu trúc tùy biến nâng cao!")

    # ================= LỆNH BẬT / CẤU HÌNH (SLASH COMMANDS) =================
    @app_commands.command(name="set_welcome", description="Cài đặt lời CHÀO ĐÓN thành viên mới (Hỗ trợ \\n để xuống dòng)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="Kênh sẽ gửi lời chào",
        message="Lời chào (Dùng {user} để tag, {server} để gọi tên server, \\n để xuống dòng)",
        image_url="Link ảnh/GIF chào mừng dưới khung chat (Tùy chọn)"
    )
    async def set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str, image_url: str = None):
        database.set_welcome(interaction.guild.id, channel.id, message, image_url)
        await interaction.response.send_message(f"✅ Đã bật và cấu hình hệ thống **Chào đón** tại kênh {channel.mention}!", ephemeral=True)

    @app_commands.command(name="set_goodbye", description="Cài đặt lời TẠM BIỆT thành viên rời đi (Hỗ trợ \\n để xuống dòng)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="Kênh sẽ gửi lời tạm biệt",
        message="Lời tạm biệt (Dùng {user}, {username}, {server}, \\n để xuống dòng)",
        image_url="Link ảnh/GIF tạm biệt dưới khung chat (Tùy chọn)"
    )
    async def set_goodbye(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str, image_url: str = None):
        database.set_goodbye(interaction.guild.id, channel.id, message, image_url)
        await interaction.response.send_message(f"✅ Đã bật và cấu hình hệ thống **Tạm biệt** tại kênh {channel.mention}!", ephemeral=True)


    # ================= LỆNH TẮT (SLASH COMMANDS) =================
    @app_commands.command(name="disable_welcome", description="Tắt riêng hệ thống Chào đón")
    @app_commands.default_permissions(administrator=True)
    async def disable_welcome(self, interaction: discord.Interaction):
        database.disable_welcome(interaction.guild.id)
        await interaction.response.send_message("❌ Đã tắt lời Chào đón của server!", ephemeral=True)

    @app_commands.command(name="disable_goodbye", description="Tắt riêng hệ thống Tạm biệt")
    @app_commands.default_permissions(administrator=True)
    async def disable_goodbye(self, interaction: discord.Interaction):
        database.disable_goodbye(interaction.guild.id)
        await interaction.response.send_message("❌ Đã tắt lời Tạm biệt của server!", ephemeral=True)


    # ================= XỬ LÝ SỰ KIỆN (LISTENERS) =================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = database.get_welcome_config(member.guild.id)
        # Chỉ chạy nếu có cấu hình, có lời chào và có kênh welcome
        if not config or not config["welcome_msg"] or not config["welcome_channel_id"]:
            return
            
        channel = member.guild.get_channel(config["welcome_channel_id"])
        if not channel: 
            return

        # Thay thế các biến động
        msg_text = config["welcome_msg"].replace("{user}", member.mention).replace("{server}", member.guild.name)
        # Bẻ dòng ký tự \n người dùng nhập từ Discord thành phím Enter thực sự
        msg_text = msg_text.replace("\\n", "\n")

        # Tạo khung Embed hoàn toàn trống tiêu đề để người dùng tự thiết kế qua văn bản gửi vào
        embed = discord.Embed(description=msg_text, color=discord.Color.green())
        
        # Đưa avatar thành viên vào góc phải làm ảnh thu nhỏ (Thumbnail) cho chuẩn quốc tế
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Nếu có cài ảnh hoặc gif lớn ở dưới cùng thì hiển thị
        if config["welcome_image"]: 
            embed.set_image(url=config["welcome_image"])
            
        # Thêm thông tin số lượng thành viên ở chân trang
        embed.set_footer(text=f"Thành viên thứ {member.guild.member_count}")
        
        try: 
            # Gửi tin nhắn kèm tag mờ ở ngoài Embed để thành viên mới nhận được thông báo điện thoại
            await channel.send(content=member.mention, embed=embed)
        except Exception as e: 
            print(f"Lỗi gửi tin nhắn Welcome tại guild {member.guild.id}: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = database.get_welcome_config(member.guild.id)
        # Chỉ chạy nếu có cấu hình, có lời tạm biệt và có kênh goodbye
        if not config or not config["goodbye_msg"] or not config["goodbye_channel_id"]:
            return
            
        channel = member.guild.get_channel(config["goodbye_channel_id"])
        if not channel: 
            return

        # Thay thế các biến động
        msg_text = config["goodbye_msg"].replace("{user}", member.mention).replace("{username}", member.name).replace("{server}", member.guild.name)
        # Bẻ dòng ký tự \n
        msg_text = msg_text.replace("\\n", "\n")

        embed = discord.Embed(description=msg_text, color=discord.Color.red())
        embed.set_thumbnail(url=member.display_avatar.url)
        
        if config["goodbye_image"]: 
            embed.set_image(url=config["goodbye_image"])
            
        embed.set_footer(text=f"Server còn lại {member.guild.member_count} thành viên.")
        
        try: 
            await channel.send(embed=embed)
        except Exception as e: 
            print(f"Lỗi gửi tin nhắn Goodbye tại guild {member.guild.id}: {e}")

async def setup(bot):
    await bot.add_cog(Welcome(bot))