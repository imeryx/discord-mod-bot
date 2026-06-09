import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io
import datetime
import sqlite3  # Thêm thư viện để lưu cấu hình kênh

# --- 1. NÚT ĐÓNG TICKET VÀ LƯU LỊCH SỬ (TRANSCRIPT) ---
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, i: discord.Interaction, b: discord.ui.Button):
        # Bảo mật: Chỉ người có quyền quản lý tin nhắn mới được đóng
        if not i.user.guild_permissions.manage_messages:
            return await i.response.send_message("❌ Chỉ admin mới có quyền đóng ticket!", ephemeral=True)
            
        await i.response.send_message("🔒 Đang lưu lịch sử chat và đóng ticket...", ephemeral=True)
        
        # Tạo file transcript
        transcript = io.StringIO()
        transcript.write(f" LỊCH SỬ TICKET: {i.channel.name} \n\n")
        async for message in i.channel.history(limit=None, oldest_first=True):
            utc_time = message.created_at
            vn_time = utc_time + datetime.timedelta(hours=7) 
            transcript.write(f"[{vn_time.strftime('%Y-%m-%d %H:%M:%S')}] {message.author.name}: {message.content}\n")
        
        transcript.seek(0)
        file = discord.File(fp=transcript, filename=f"ticket_{i.channel.name}.txt")
        
        # TỐI ƯU: Lấy ID kênh log từ Database ra để dùng
        conn = sqlite3.connect('bot_database.db')
        row = conn.execute("SELECT log_channel_id FROM TicketConfig WHERE guild_id = ?", (i.guild.id,)).fetchone()
        conn.close()
        
        if row:
            log_channel = i.guild.get_channel(row[0])
            if log_channel:
                await log_channel.send(f"📋 **Transcript ticket:** {i.channel.name}", file=file)
            
        await asyncio.sleep(2)
        await i.channel.delete()

# --- 2. GIAO DIỆN PANEL TICKET (CÁC NÚT BẤM) ---
class TicketLauncher(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, i: discord.Interaction, category_name: str):
        guild = i.guild
        
        # Tự động gom vào danh mục TICKETS cho gọn server
        ticket_category = discord.utils.get(guild.categories, name="TICKETS")
        if not ticket_category:
            ticket_category = await guild.create_category("TICKETS")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await guild.create_text_channel(
            name=f"ticket-{i.user.name}", 
            category=ticket_category, 
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title=f"📩 Hỗ trợ: {category_name}",
            description=f"Chào {i.user.mention}, vui lòng trình bày vấn đề của bạn. Admin sẽ phản hồi trong thời gian sớm nhất!",
            color=0x007BFF
        )
        await channel.send(embed=embed, view=TicketControls())
        await i.response.send_message(f"✅ Ticket đã tạo: {channel.mention}", ephemeral=True)

    @discord.ui.button(label="Hỗ Trợ", style=discord.ButtonStyle.primary, emoji="<:pnv_support:1512882340995534989>", custom_id="btn_idea")
    async def btn_idea(self, i, b): await self.create_ticket(i, "Hỗ Trợ")
    
    @discord.ui.button(label="Tố Cáo", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="btn_report")
    async def btn_report(self, i, b): await self.create_ticket(i, "Tố Cáo")

# --- 3. COG VÀ LỆNH SLASH ---
class TicketCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Khởi tạo bảng lưu cấu hình nếu chưa có
        conn = sqlite3.connect('bot_database.db')
        conn.execute("CREATE TABLE IF NOT EXISTS TicketConfig (guild_id INTEGER PRIMARY KEY, log_channel_id INTEGER)")
        conn.commit()
        conn.close()
        
        self.bot.add_view(TicketLauncher())
        self.bot.add_view(TicketControls())
        print("-> Cog [Ticket] loaded and optimized with DB successfully!")

    # LỆNH SETUP MỚI: Cho phép chọn cả kênh đăng Panel và kênh lưu Log trực tiếp
    @app_commands.command(name="setup_ticket", description="Cấu hình hệ thống Ticket cho server")
    @app_commands.default_permissions(administrator=True)
    async def setup_ticket(
        self, 
        i: discord.Interaction, 
        target_channel: discord.TextChannel = None, 
        log_channel: discord.TextChannel = None
    ):
        await i.response.defer(ephemeral=True)
        
        send_channel = target_channel or i.channel
        
        # Nếu người dùng có chọn kênh log, tiến hành lưu vào Database
        if log_channel:
            conn = sqlite3.connect('bot_database.db')
            conn.execute(
                "INSERT INTO TicketConfig (guild_id, log_channel_id) VALUES (?, ?) "
                "ON CONFLICT(guild_id) DO UPDATE SET log_channel_id = excluded.log_channel_id", 
                (i.guild.id, log_channel.id)
            )
            conn.commit()
            conn.close()
        
        # Giao diện chuẩn phân cấp chữ và màu xanh nước biển (0x007BFF) của bạn
        embed = discord.Embed(
            title="<:elfie_hug:1512859756862378046> Support Center",
            description=(
                "**Chào mừng bạn đến với Trung Tâm Hỗ Trợ của Elfaria**\n\n"
                "Vui lòng bấm vào nút bên dưới để mở ticket. Admin sẽ liên hệ với bạn trong thời gian sớm nhất.\n"
            ),
            color=0x007BFF
        )
        embed.set_thumbnail(url="https://i.pinimg.com/736x/b7/17/f8/b717f8505781eecc83f414cf1bb51470.jpg")
        embed.set_footer(text="⚠️ Lưu ý: Spam ticket sẽ dẫn đến việc bị kick hoặc ban!")
        
        await send_channel.send(embed=embed, view=TicketLauncher())
        
        msg = f" Đã đăng Panel tại {send_channel.mention}!"
        if log_channel:
            msg += f"\n Kênh lưu trữ dữ liệu chat được đặt thành: {log_channel.mention}"
        else:
            msg += f"\n⚠️ Bạn chưa cấu hình kênh log. Vui lòng chạy lại lệnh và chọn `log_channel` để tính năng lưu transcript hoạt động."
            
        await i.followup.send(msg)

async def setup(bot): await bot.add_cog(TicketCog(bot))