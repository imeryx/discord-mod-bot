import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io

# --- 1. NÚT ĐÓNG TICKET VÀ LƯU LỊCH SỬ (TRANSCRIPT) ---
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, i: discord.Interaction, b: discord.ui.Button):
        # Bảo mật: Chỉ người có quyền quản lý mới được đóng
        if not i.user.guild_permissions.manage_messages:
            return await i.response.send_message("❌ Chỉ staff mới có quyền đóng ticket!", ephemeral=True)
            
        await i.response.send_message("🔒 Đang lưu lịch sử chat và đóng ticket...", ephemeral=True)
        
        # Tạo file transcript
        transcript = io.StringIO()
        transcript.write(f"--- LỊCH SỬ TICKET: {i.channel.name} ---\n\n")
        async for message in i.channel.history(limit=None, oldest_first=True):
            transcript.write(f"[{message.created_at.strftime('%H:%M:%S')}] {message.author.name}: {message.content}\n")
        
        transcript.seek(0)
        file = discord.File(fp=transcript, filename=f"ticket_{i.channel.name}.txt")
        
        # Gửi vào kênh log 'ticket-logs'
        log_channel = discord.utils.get(i.guild.text_channels, name="ticket-logs")
        if log_channel:
            await log_channel.send(f"📋 **Transcript ticket:** {i.channel.name}", file=file)
            
        await asyncio.sleep(2)
        await i.channel.delete()

# --- 2. GIAO DIỆN PANEL TICKET (ĐÃ CĂN CHỈNH ĐÚNG CỠ CHỮ) ---
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
            description=f"Chào {i.user.mention}, vui lòng trình bày vấn đề của bạn. Staff sẽ phản hồi sớm nhất!",
            color=0x2b2d31
        )
        await channel.send(embed=embed, view=TicketControls())
        await i.response.send_message(f"✅ Ticket đã tạo: {channel.mention}", ephemeral=True)

    @discord.ui.button(label="Mua Hàng", style=discord.ButtonStyle.primary, emoji="🛒", custom_id="btn_buy")
    async def btn_buy(self, i, b): await self.create_ticket(i, "Mua Hàng")
    
    @discord.ui.button(label="Hỗ Trợ/Bảo Hành", style=discord.ButtonStyle.secondary, emoji="🔧", custom_id="btn_support")
    async def btn_support(self, i, b): await self.create_ticket(i, "Hỗ Trợ/Bảo Hành")

# --- 3. COG VÀ LỆNH SLASH ---
class TicketCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketLauncher())
        self.bot.add_view(TicketControls())

    @app_commands.command(name="setup_ticket", description="Gửi Panel Ticket chuẩn mẫu")
    @app_commands.default_permissions(administrator=True)
    async def setup_ticket(self, i: discord.Interaction):
        # Embed chuẩn thiết kế phân cấp chữ:
        # Tiêu đề: To nhất
        # Mô tả: Chữ đậm và chữ thường đan xen
        # Footer: Chữ nhỏ nhất
        embed = discord.Embed(
            title="🎫 TRUNG TÂM HỖ TRỢ",
            description=(
                "**Chào mừng bạn đến với hệ thống hỗ trợ**\n\n"
                "Vui lòng bấm vào nút bên dưới để mở ticket. Đội ngũ nhân viên sẽ liên hệ với bạn trong thời gian sớm nhất.\n"
            ),
            color=0x007BFF
        )
        # Logo góc phải
        embed.set_thumbnail(url="https://i.pinimg.com/736x/b7/17/f8/b717f8505781eecc83f414cf1bb51470.jpg")
        # Footer (cỡ chữ nhỏ nhất)
        embed.set_footer(text="⚠️ Lưu ý: Vui lòng không spam ticket để tránh bị khóa quyền.")
        
        await i.channel.send(embed=embed, view=TicketLauncher())
        await i.response.send_message("Đã đăng Panel thành công!", ephemeral=True)

async def setup(bot): await bot.add_cog(TicketCog(bot))