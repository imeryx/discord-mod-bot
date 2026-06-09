import discord
from discord.ext import commands
from discord import app_commands
import database

class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Config] đã được tải thành công!")


    # ================= 2. LỆNH THIẾT LẬP PREFIX =================
    @app_commands.command(name="setprefix", description="Thay đổi prefix cho các lệnh cổ điển của server")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(prefix="Ký tự prefix mới (VD: ?, ., -, ~)")
    async def setprefix(self, interaction: discord.Interaction, prefix: str):
        # Chặn trường hợp đặt prefix quá dài làm rác cú pháp
        if len(prefix) > 3:
            return await interaction.response.send_message("❌ Prefix quá dài! Vui lòng chọn ký tự dưới 3 chữ cái.", ephemeral=True)
        
        try:
            # Lưu prefix tùy chỉnh vào Database
            database.set_prefix(interaction.guild.id, prefix)
            await interaction.response.send_message(
                f"✅ Đã đổi prefix của server thành: `{prefix}`\n"
                f"*(Lưu ý: Prefix này chỉ áp dụng cho lệnh văn bản cổ điển, các Slash Command vẫn bắt buộc dùng dấu `/`)*"
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Có lỗi xảy ra khi lưu cấu hình prefix: {e}", ephemeral=True)
    # ================= 3. LỆNH XEM PREFIX HIỆN TẠI =================
    @app_commands.command(name="prefix", description="Xem ký tự prefix đang được sử dụng ở server này")
    async def prefix(self, interaction: discord.Interaction):
        # Gọi hàm lấy prefix từ database
        current_prefix = database.get_prefix(interaction.guild.id)
        
        embed = discord.Embed(
            title="⚙️ Cấu hình Prefix",
            description=f"Dấu lệnh (prefix) hiện tại của server là: **`{current_prefix}`**",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Sử dụng các lệnh cổ điển với prefix này (VD: " + current_prefix + "ping)")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    # ================= 4. LỆNH SERVER INFO =================
    @app_commands.command(name="serverinfo", description="Xem thông tin chi tiết về server này")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"Thông tin Server: {guild.name}", color=discord.Color.purple())
        
        embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
        embed.add_field(name="Chủ sở hữu", value=guild.owner.mention, inline=True)
        embed.add_field(name="Số thành viên", value=guild.member_count, inline=True)
        embed.add_field(name="Ngày tạo", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="Số lượng kênh", value=len(guild.channels), inline=True)
        embed.add_field(name="Số vai trò", value=len(guild.roles), inline=True)
        embed.add_field(name="Server ID", value=guild.id, inline=False)
        
        await interaction.response.send_message(embed=embed)

    # ================= 5. LỆNH USER INFO =================
    @app_commands.command(name="userinfo", description="Xem thông tin chi tiết của một thành viên")
    @app_commands.describe(member="Người bạn muốn xem thông tin")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user # Nếu không tag ai thì lấy info của chính mình
        
        roles = [role.mention for role in member.roles[1:]] # Bỏ qua role @everyone
        roles_display = ", ".join(roles) if roles else "Không có vai trò"
        
        embed = discord.Embed(title=f"Thông tin thành viên: {member.name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(name="Tên hiển thị", value=member.display_name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Ngày tham gia server", value=member.joined_at.strftime("%d/%m/%Y"), inline=False)
        embed.add_field(name="Ngày tạo tài khoản", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="Vai trò", value=roles_display, inline=False)
        
        await interaction.response.send_message(embed=embed)
# Đảm bảo hàm setup nằm sát lề trái, thụt lề chuẩn Python
async def setup(bot):
    await bot.add_cog(Config(bot))