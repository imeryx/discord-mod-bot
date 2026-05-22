import discord
from discord.ext import commands
from discord import app_commands
import datetime
import database

# Hàm xử lý hình phạt tự động dựa trên số lượng cảnh báo (Viết ngoài Class)
async def apply_auto_punishment(interaction_or_message, member: discord.Member, warn_count: int):
    guild = member.guild
    bot_user = guild.me
    channel = interaction_or_message.channel

    if warn_count == 3:
        try:
            duration = datetime.timedelta(hours=1)
            await member.timeout(duration, reason=f"Hệ thống: Tích lũy đủ {warn_count} cảnh báo.")
            await channel.send(f"🤖 **Auto-Punish:** {member.mention} đã tích lũy đủ **3 cảnh báo**. Tự động cấm túc (Timeout) 1 tiếng!")
        except Exception as e:
            print(f"Lỗi Auto-Punish Timeout: {e}")

    elif warn_count == 5:
        try:
            if member.top_role < bot_user.top_role:
                await member.kick(reason=f"Hệ thống: Tích lũy đủ {warn_count} cảnh báo.")
                await channel.send(f"🤖 **Auto-Punish:** {member.mention} đã tích lũy đủ **5 cảnh báo**. Tự động Đuổi (Kick) khỏi server!")
        except Exception as e:
            print(f"Lỗi Auto-Punish Kick: {e}")

    elif warn_count >= 7:
        try:
            if member.top_role < bot_user.top_role:
                await member.ban(reason=f"Hệ thống: Tích lũy đủ {warn_count} cảnh báo.", delete_message_days=0)
                await channel.send(f"🔨 **Auto-Punish:** {member.mention} đã tích lũy đủ **7 cảnh báo**. Tự động Cấm vĩnh viễn (Ban)!")
        except Exception as e:
            print(f"Lỗi Auto-Punish Ban: {e}")


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Moderation] đã được tải thành công!")

    # Hàm kiểm tra phân quyền (Dùng chung)
    def check_hierarchy(self, interaction: discord.Interaction, member: discord.Member):
        if member.top_role >= interaction.guild.me.top_role:
            return "❌ Tôi không thể xử lý người có chức vụ cao hơn hoặc bằng tôi!"
        if member.id == interaction.user.id:
            return "❌ Bạn không thể tự trừng phạt chính mình!"
        return None

    # ================= 1. LỆNH KICK =================
    @app_commands.command(name="kick", description="Đuổi một thành viên khỏi server")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
        error_msg = self.check_hierarchy(interaction, member)
        if error_msg:
            return await interaction.response.send_message(error_msg, ephemeral=True)

        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(f"✅ **{member.name}** đã bị đuổi khỏi server bởi {interaction.user.mention}. \nLý do: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Có lỗi xảy ra: {e}", ephemeral=True)

    # ================= 2. LỆNH BAN =================
    @app_commands.command(name="ban", description="Cấm vĩnh viễn một thành viên khỏi server")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
        error_msg = self.check_hierarchy(interaction, member)
        if error_msg:
            return await interaction.response.send_message(error_msg, ephemeral=True)

        try:
            await member.ban(reason=reason, delete_message_days=0)
            await interaction.response.send_message(f"🔨 **{member.name}** đã bị cấm vĩnh viễn bởi {interaction.user.mention}. \nLý do: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Có lỗi xảy ra: {e}", ephemeral=True)

    # ================= 3. LỆNH TIMEOUT =================
    @app_commands.command(name="timeout", description="Cấm túc (mute) thành viên trong một khoảng thời gian")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(minutes="Số phút muốn cấm túc")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "Không có lý do"):
        error_msg = self.check_hierarchy(interaction, member)
        if error_msg:
            return await interaction.response.send_message(error_msg, ephemeral=True)

        try:
            duration = datetime.timedelta(minutes=minutes)
            await member.timeout(duration, reason=reason)
            await interaction.response.send_message(f"🤫 **{member.name}** đã bị cấm túc {minutes} phút bởi {interaction.user.mention}. \nLý do: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Có lỗi xảy ra: {e}", ephemeral=True)

    # ================= 4. LỆNH WARN =================
    @app_commands.command(name="warn", description="Cảnh báo một thành viên và lưu lịch sử vào hệ thống")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        error_msg = self.check_hierarchy(interaction, member)
        if error_msg:
            return await interaction.response.send_message(error_msg, ephemeral=True)

        try:
            warn_count = database.add_warning(
                guild_id=interaction.guild.id, 
                user_id=member.id, 
                moderator_id=interaction.user.id, 
                reason=reason
            )
            await interaction.response.send_message(f"⚠️ **{member.name}** đã bị ghi danh cảnh báo lần thứ **{warn_count}** bởi {interaction.user.mention}. \nLý do: {reason}")
            
            # Kích hoạt hệ thống phạt tự động
            await apply_auto_punishment(interaction, member, warn_count)
        except Exception as e:
            await interaction.response.send_message(f"❌ Có lỗi xảy ra khi ghi vào database: {e}", ephemeral=True)

    # ================= 5. LỆNH CHECKWARN =================
    @app_commands.command(name="checkwarn", description="Xem lịch sử cảnh báo của một thành viên")
    @app_commands.default_permissions(moderate_members=True)
    async def checkwarn(self, interaction: discord.Interaction, member: discord.Member):
        records = database.get_warnings(interaction.guild.id, member.id)
        
        if not records:
            return await interaction.response.send_message(f"✅ **{member.name}** có hồ sơ trong sạch, chưa từng bị cảnh báo!", ephemeral=True)
        
        embed = discord.Embed(
            title=f"Lịch sử vi phạm của {member.name}", 
            description=f"Tổng số cảnh báo: **{len(records)}**",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        for idx, record in enumerate(records, 1):
            warning_id, mod_id, reason, timestamp = record 
            date_only = timestamp[:10] 
            
            embed.add_field(
                name=f"Cảnh báo #{idx} - Ngày {date_only}", 
                value=f"**Mã ID:** `{warning_id}`\n**Lý do:** {reason}\n**Xử lý bởi:** <@{mod_id}>", 
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    # ================= 6. LỆNH CLEARWARN =================
    @app_commands.command(name="clearwarn", description="Xóa toàn bộ lịch sử cảnh báo của một thành viên")
    @app_commands.default_permissions(moderate_members=True)
    async def clearwarn(self, interaction: discord.Interaction, member: discord.Member):
        if member.id == interaction.user.id:
            return await interaction.response.send_message("❌ Bạn không thể tự xóa lịch sử cảnh báo của bản thân!", ephemeral=True)

        try:
            records = database.get_warnings(interaction.guild.id, member.id)
            if not records:
                return await interaction.response.send_message(f"❌ **{member.name}** hiện tại không có cảnh báo nào để xóa!", ephemeral=True)
            
            database.clear_warnings(interaction.guild.id, member.id)
            await interaction.response.send_message(f"🧹 Đã xóa sạch toàn bộ lịch sử vi phạm của **{member.name}** theo lệnh của {interaction.user.mention}.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Có lỗi xảy ra: {e}", ephemeral=True)

    # ================= 7. LỆNH REMOVEWARN =================
    @app_commands.command(name="removewarn", description="Xóa một cảnh báo cụ thể dựa trên Mã ID")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(warning_id="Nhập Mã ID của cảnh báo (xem trong lệnh /checkwarn)")
    async def removewarn(self, interaction: discord.Interaction, warning_id: int):
        try:
            success = database.remove_specific_warning(interaction.guild.id, warning_id)
            
            if success:
                await interaction.response.send_message(f"✅ Đã xóa thành công cảnh báo có mã **`{warning_id}`**.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Không tìm thấy cảnh báo có mã **`{warning_id}`** trong server này. Hãy kiểm tra lại bằng lệnh `/checkwarn`.", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Có lỗi xảy ra: {e}", ephemeral=True)

    # ================= 8. LỆNH UNTIMEOUT =================
    @app_commands.command(name="untimeout", description="Gỡ cấm túc (unmute) cho một thành viên")
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Không có lý do"):
        error_msg = self.check_hierarchy(interaction, member)
        if error_msg:
            return await interaction.response.send_message(error_msg, ephemeral=True)

        if not member.is_timed_out():
            return await interaction.response.send_message(f"❌ **{member.name}** hiện tại không bị cấm túc để gỡ phạt!", ephemeral=True)

        try:
            await member.timeout(None, reason=reason)
            await interaction.response.send_message(f"🔊 **{member.name}** đã được gỡ cấm túc thành công bởi {interaction.user.mention}. \nLý do: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Có lỗi xảy ra: {e}", ephemeral=True)

    # ================= 9. LỆNH UNBAN =================
    @app_commands.command(name="unban", description="Gỡ lệnh cấm (unban) cho một người dùng")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Nhập ID tài khoản của người dùng cần gỡ ban")
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: str = "Không có lý do"):
        try:
            await interaction.guild.unban(user, reason=reason)
            await interaction.response.send_message(f"🕊️ **{user.name}** đã được gỡ cấm thành công bởi {interaction.user.mention}. \nLý do: {reason}")
        
        except discord.NotFound:
            await interaction.response.send_message(f"❌ Tài khoản **{user.name}** hiện không nằm trong danh sách bị cấm của server!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Có lỗi xảy ra: {e}", ephemeral=True)

# Khởi tạo Cog
async def setup(bot):
    await bot.add_cog(Moderation(bot))