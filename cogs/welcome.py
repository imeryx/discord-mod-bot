import discord
from discord.ext import commands
from discord import app_commands
import database

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Welcome/Goodbye] đã sẵn sàng hoạt động!")

    # ================= LỆNH CẤU HÌNH (SLASH COMMAND) =================
    @app_commands.command(name="set_welcome", description="Cấu hình hệ thống chào đón và tạm biệt cho Server")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="Kênh sẽ gửi lời nhắn",
        welcome_msg="Lời chào (Dùng {user} để tag tên, {server} để gọi tên server)",
        welcome_image="Link ảnh hoặc GIF hiển thị khi chào đón (Bắt đầu bằng http...)",
        goodbye_msg="Lời tạm biệt (Dùng {user} hoặc {username} để gọi tên)",
        goodbye_image="Link ảnh hoặc GIF hiển thị khi tạm biệt (Bắt đầu bằng http...)"
    )
    async def set_welcome(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel, 
        welcome_msg: str, 
        welcome_image: str = None, 
        goodbye_msg: str = None, 
        goodbye_image: str = None
    ):
        # Lưu vào database
        database.save_welcome_config(
            guild_id=interaction.guild.id,
            channel_id=channel.id,
            welcome_msg=welcome_msg,
            welcome_image=welcome_image,
            goodbye_msg=goodbye_msg,
            goodbye_image=goodbye_image
        )
        await interaction.response.send_message(f"✅ Đã thiết lập hệ thống Chào đón/Tạm biệt thành công tại kênh {channel.mention}!", ephemeral=True)


    # ================= SỰ KIỆN KHI CÓ NGƯỜI VÀO SERVER =================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = database.get_welcome_config(member.guild.id)
        if not config or not config["channel_id"]:
            return
            
        channel = member.guild.get_channel(config["channel_id"])
        if not channel:
            return

        # Định dạng lại văn bản biến động {user} và {server}
        msg_text = config["welcome_msg"].replace("{user}", member.mention).replace("{server}", member.guild.name)

        # Tạo Embed đẹp mắt để chứa ảnh/gif bên dưới
        embed = discord.Embed(
            description=msg_text,
            color=discord.Color.green()
        )
        embed.set_author(name=f"Thành viên mới!", icon_url=member.display_avatar.url)
        
        # Nếu có link ảnh/gif thì đính kèm vào
        if config["welcome_image"]:
            embed.set_image(url=config["welcome_image"])
            
        embed.set_footer(text=f"Server hiện có {member.guild.member_count} thành viên.")
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Lỗi gửi tin nhắn Welcome: {e}")


    # ================= SỰ KIỆN KHI CÓ NGƯỜI RỜI SERVER =================
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = database.get_welcome_config(member.guild.id)
        if not config or not config["channel_id"] or not config["goodbye_msg"]:
            return
            
        channel = member.guild.get_channel(config["channel_id"])
        if not channel:
            return

        # Định dạng lại văn bản tạm biệt
        msg_text = config["goodbye_msg"].replace("{user}", member.mention).replace("{username}", member.name).replace("{server}", member.guild.name)

        embed = discord.Embed(
            description=msg_text,
            color=discord.Color.red()
        )
        embed.set_author(name=f"Thành viên rời đi!", icon_url=member.display_avatar.url)
        
        if config["goodbye_image"]:
            embed.set_image(url=config["goodbye_image"])
            
        embed.set_footer(text=f"Server còn lại {member.guild.member_count} thành viên.")
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Lỗi gửi tin nhắn Goodbye: {e}")

async def setup(bot):
    await bot.add_cog(Welcome(bot))