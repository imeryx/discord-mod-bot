import discord
from discord.ext import commands
from discord import app_commands
import database

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Welcome/Goodbye] Đã sẵn sàng với cấu trúc tách rời độc lập!")

    # ================= LỆNH BẬT / CẤU HÌNH =================
    @app_commands.command(name="set_welcome", description="Cài đặt lời CHÀO ĐÓN thành viên mới (Tách biệt)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="Kênh sẽ gửi lời chào",
        message="Lời chào (Dùng {user} để tag, {server} để gọi tên server)",
        image_url="Link ảnh/GIF chào mừng (http...)"
    )
    async def set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str, image_url: str = None):
        database.set_welcome(interaction.guild.id, channel.id, message, image_url)
        await interaction.response.send_message(f"✅ Đã bật hệ thống **Chào đón** tại kênh {channel.mention}!", ephemeral=True)

    @app_commands.command(name="set_goodbye", description="Cài đặt lời TẠM BIỆT thành viên rời đi (Tách biệt)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="Kênh sẽ gửi lời tạm biệt",
        message="Lời tạm biệt (Dùng {user} hoặc {username})",
        image_url="Link ảnh/GIF tạm biệt (http...)"
    )
    async def set_goodbye(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str, image_url: str = None):
        database.set_goodbye(interaction.guild.id, channel.id, message, image_url)
        await interaction.response.send_message(f"✅ Đã bật hệ thống **Tạm biệt** tại kênh {channel.mention}!", ephemeral=True)


    # ================= LỆNH TẮT =================
    @app_commands.command(name="disable_welcome", description="Tắt riêng hệ thống Chào đón")
    @app_commands.default_permissions(administrator=True)
    async def disable_welcome(self, interaction: discord.Interaction):
        database.disable_welcome(interaction.guild.id)
        await interaction.response.send_message("❌ Đã tắt lời Chào đón!", ephemeral=True)

    @app_commands.command(name="disable_goodbye", description="Tắt riêng hệ thống Tạm biệt")
    @app_commands.default_permissions(administrator=True)
    async def disable_goodbye(self, interaction: discord.Interaction):
        database.disable_goodbye(interaction.guild.id)
        await interaction.response.send_message("❌ Đã tắt lời Tạm biệt!", ephemeral=True)


    # ================= XỬ LÝ SỰ KIỆN =================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = database.get_welcome_config(member.guild.id)
        # Chỉ chạy nếu có thiết lập lời chào và chưa bị tắt
        if not config or not config["welcome_msg"] or not config["welcome_channel_id"]:
            return
            
        channel = member.guild.get_channel(config["welcome_channel_id"])
        if not channel: return

        msg_text = config["welcome_msg"].replace("{user}", member.mention).replace("{server}", member.guild.name)
        embed = discord.Embed(description=msg_text, color=discord.Color.green())
        embed.set_author(name="Thành viên mới!", icon_url=member.display_avatar.url)
        if config["welcome_image"]: embed.set_image(url=config["welcome_image"])
        embed.set_footer(text=f"Server hiện có {member.guild.member_count} thành viên.")
        
        try: await channel.send(embed=embed)
        except Exception as e: print(f"Lỗi gửi Welcome: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = database.get_welcome_config(member.guild.id)
        # Chỉ chạy nếu có thiết lập lời tạm biệt và chưa bị tắt
        if not config or not config["goodbye_msg"] or not config["goodbye_channel_id"]:
            return
            
        channel = member.guild.get_channel(config["goodbye_channel_id"])
        if not channel: return

        msg_text = config["goodbye_msg"].replace("{user}", member.mention).replace("{username}", member.name).replace("{server}", member.guild.name)
        embed = discord.Embed(description=msg_text, color=discord.Color.red())
        embed.set_author(name="Thành viên rời đi!", icon_url=member.display_avatar.url)
        if config["goodbye_image"]: embed.set_image(url=config["goodbye_image"])
        embed.set_footer(text=f"Server còn lại {member.guild.member_count} thành viên.")
        
        try: await channel.send(embed=embed)
        except Exception as e: print(f"Lỗi gửi Goodbye: {e}")

async def setup(bot):
    await bot.add_cog(Welcome(bot))