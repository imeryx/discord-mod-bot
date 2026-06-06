import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io

# --- NÚT ĐÓNG TICKET & LƯU TRANSCRIPT ---
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, i: discord.Interaction, b: discord.ui.Button):
        if not i.user.guild_permissions.manage_messages:
            return await i.response.send_message("❌ Chỉ quản trị viên mới có quyền đóng ticket!", ephemeral=True)
            
        await i.response.send_message("🔒 Đang lưu transcript và đóng ticket trong 5 giây...", ephemeral=True)
        
        # 1. Thu thập tin nhắn
        transcript = io.StringIO()
        transcript.write(f"Transcript of ticket {i.channel.name}\n")
        async for message in i.channel.history(limit=None, oldest_first=True):
            transcript.write(f"{message.created_at} - {message.author}: {message.content}\n")
        
        transcript.seek(0)
        file = discord.File(fp=transcript, filename=f"{i.channel.name}_transcript.txt")
        
        # 2. Gửi vào kênh log (Giả sử bạn có kênh tên 'ticket-logs')
        log_channel = discord.utils.get(i.guild.text_channels, name="ticket-logs")
        if log_channel:
            await log_channel.send(f"Transcript cho {i.channel.name}:", file=file)
        
        # 3. Đóng kênh
        await asyncio.sleep(5)
        await i.channel.delete()

# --- TICKET LAUNCHER ---
class TicketLauncher(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, i: discord.Interaction, category: str):
        guild = i.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(f"ticket-{i.user.name}", overwrites=overwrites)
        
        embed = discord.Embed(title=f"Support: {category}", description="Vui lòng mô tả vấn đề của bạn.", color=discord.Color.green())
        await channel.send(embed=embed, view=TicketControls())
        await i.response.send_message(f"Ticket đã tạo: {channel.mention}", ephemeral=True)

    @discord.ui.button(label="Giải đáp thắc mắc cho thành viên server", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="btn_general")
    async def btn_general(self, i, b): await self.create_ticket(i, "Hỗ Trợ Chung")
    @discord.ui.button(label="Tố cáo hành vi thành viên server", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="btn_report")
    async def btn_report(self, i, b): await self.create_ticket(i, "Tố Cáo")
    @discord.ui.button(label="Góp ý cho server và bot", style=discord.ButtonStyle.secondary, emoji="💡", custom_id="btn_feedback")
    async def btn_feedback(self, i, b): await self.create_ticket(i, "Góp Ý")

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketLauncher())
        self.bot.add_view(TicketControls())

    @app_commands.command(name="setup_ticket", description="Thiết lập bảng Ticket")
    @app_commands.default_permissions(administrator=True)
    async def setup_ticket(self, i: discord.Interaction):
        embed = discord.Embed(title="✨ Support Center", description="Chọn mục để mở ticket.", color=discord.Color.blue())
        await i.channel.send(embed=embed, view=TicketLauncher())
        await i.response.send_message("Xong!", ephemeral=True)

async def setup(bot): await bot.add_cog(TicketCog(bot))