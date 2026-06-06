import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io

# --- NÚT ĐÓNG TICKET VỚI TÍNH NĂNG TRANSCRIPT ---
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, i: discord.Interaction, b: discord.ui.Button):
        # Bảo mật: Chỉ quản trị viên mới đóng được
        if not i.user.guild_permissions.manage_messages:
            return await i.response.send_message("❌ Chỉ staff mới có quyền đóng ticket!", ephemeral=True)
            
        await i.response.send_message("🔒 Đang lưu trữ dữ liệu và đóng ticket...", ephemeral=True)
        
        # 1. Tạo file Transcript
        transcript = io.StringIO()
        transcript.write(f"Transcript của ticket: {i.channel.name}\n\n")
        async for message in i.channel.history(limit=None, oldest_first=True):
            transcript.write(f"[{message.created_at.strftime('%H:%M:%S')}] {message.author}: {message.content}\n")
        
        transcript.seek(0)
        file = discord.File(fp=transcript, filename=f"transcript_{i.channel.name}.txt")
        
        # 2. Gửi vào kênh log 'ticket-logs'
        log_channel = discord.utils.get(i.guild.text_channels, name="ticket-logs")
        if log_channel:
            await log_channel.send(f"📋 **Transcript ticket:** {i.channel.name}", file=file)
            
        await asyncio.sleep(2)
        await i.channel.delete()

# --- PANEL TICKET: THIẾT KẾ TINH TẾ (THUMBNAIL Ở GÓC) ---
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
        
        embed = discord.Embed(
            title=f"📩 Support: {category}",
            description=f"Chào {i.user.mention}, vui lòng trình bày vấn đề của bạn ở đây. Staff sẽ hỗ trợ bạn sớm nhất!",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed, view=TicketControls())
        await i.response.send_message(f"✅ Ticket đã tạo: {channel.mention}", ephemeral=True)

    @discord.ui.button(label="General Support", style=discord.ButtonStyle.primary, custom_id="btn_gen")
    async def btn_gen(self, i, b): await self.create_ticket(i, "Hỗ trợ chung")
    @discord.ui.button(label="Report", style=discord.ButtonStyle.danger, custom_id="btn_rep")
    async def btn_rep(self, i, b): await self.create_ticket(i, "Báo cáo")

class TicketCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketLauncher())
        self.bot.add_view(TicketControls())

    @app_commands.command(name="setup_ticket", description="Tạo Ticket")
    async def setup_ticket(self, i: discord.Interaction):
        # Embed tối giản, sang trọng với logo góc phải
        embed = discord.Embed(
            title="✨ Support Center",
            description="Chào mừng bạn đến với hệ thống hỗ trợ. Vui lòng bấm vào nút tương ứng bên dưới để mở ticket.",
            color=discord.Color.from_rgb(47, 49, 54)
        )
        # Chỉ để Thumbnail (Logo góc phải), không để Banner ảnh lớn
        embed.set_thumbnail(url="https://i.pinimg.com/736x/b7/17/f8/b717f8505781eecc83f414cf1bb51470.jpg")
        embed.add_field(name="Lưu ý:", value="Spam ticket sẽ dẫn đến việc bị mute hoặc ban.", inline=False)
        
        await i.channel.send(embed=embed, view=TicketLauncher())
        await i.response.send_message("Đã đăng Panel thành công!", ephemeral=True)

async def setup(bot): await bot.add_cog(TicketCog(bot))