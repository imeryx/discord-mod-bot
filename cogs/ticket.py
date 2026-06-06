import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io

# --- 1. XỬ LÝ NÚT ĐÓNG TICKET VÀ TRANSCRIPT ---
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, i: discord.Interaction, b: discord.ui.Button):
        # Kiểm tra quyền: Chỉ Staff/Admin mới được đóng
        if not i.user.guild_permissions.manage_messages:
            return await i.response.send_message("❌ Chỉ quản trị viên mới có quyền đóng ticket!", ephemeral=True)
            
        await i.response.send_message("🔒 Đang lưu lịch sử chat và đóng ticket...", ephemeral=True)
        
        # Tạo file transcript
        transcript = io.StringIO()
        transcript.write(f"--- Lịch sử Ticket: {i.channel.name} ---\n\n")
        async for message in i.channel.history(limit=None, oldest_first=True):
            transcript.write(f"[{message.created_at.strftime('%H:%M:%S')}] {message.author.name}: {message.content}\n")
        
        transcript.seek(0)
        file = discord.File(fp=transcript, filename=f"ticket_{i.channel.name}.txt")
        
        # Gửi vào log (yêu cầu tạo kênh tên 'ticket-logs')
        log_channel = discord.utils.get(i.guild.text_channels, name="ticket-logs")
        if log_channel:
            await log_channel.send(f"📋 **Đã đóng ticket:** {i.channel.name}", file=file)
            
        await asyncio.sleep(2)
        await i.channel.delete()

# --- 2. GIAO DIỆN PANEL (Sát với ảnh mẫu) ---
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
            title=f"📩 Hỗ trợ: {category}",
            description=f"Chào {i.user.mention}, vui lòng trình bày vấn đề của bạn. Đội ngũ Staff sẽ phản hồi sớm nhất!",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed, view=TicketControls())
        await i.response.send_message(f"✅ Ticket đã tạo: {channel.mention}", ephemeral=True)

    @discord.ui.button(label="General Support", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="btn_gen")
    async def btn_gen(self, i, b): await self.create_ticket(i, "General Support")
    
    @discord.ui.button(label="Report Player", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="btn_rep")
    async def btn_rep(self, i, b): await self.create_ticket(i, "Report Player")

# --- 3. ĐĂNG KÝ VÀ LỆNH SLASH ---
class TicketCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketLauncher())
        self.bot.add_view(TicketControls())

    @app_commands.command(name="setup_ticket", description="Gửi Panel Ticket chuyên nghiệp")
    @app_commands.default_permissions(administrator=True)
    async def setup_ticket(self, i: discord.Interaction):
        # Bố cục Embed giống ảnh mẫu: Tiêu đề lớn, nội dung ngắn gọn, logo góc phải
        embed = discord.Embed(
            title="🎫 TRUNG TÂM HỖ TRỢ",
            description="Chào mừng bạn đến với hệ thống hỗ trợ. Vui lòng bấm vào nút tương ứng bên dưới để bắt đầu.",
            color=0x2f3136 # Màu tối sang trọng của Discord
        )
        # Logo góc phải (Thay URL này bằng logo server của bạn)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2936/2936769.png")
        
        await i.channel.send(embed=embed, view=TicketLauncher())
        await i.response.send_message("Đã gửi Panel Ticket thành công!", ephemeral=True)

async def setup(bot): await bot.add_cog(TicketCog(bot))