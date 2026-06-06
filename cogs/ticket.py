import discord
from discord.ext import commands
from discord import app_commands
import asyncio

# --- GIAO DIỆN NÚT BẤM KHI ĐÃ VÀO TICKET ---
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, i: discord.Interaction, b: discord.ui.Button):
        await i.response.send_message("Ticket will be closed and channel deleted in 5 seconds...", ephemeral=True)
        await asyncio.sleep(5)
        await i.channel.delete()

# --- GIAO DIỆN PANEL CHÍNH (GIỐNG MẪU) ---
class TicketLauncher(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Select a support category...", 
        custom_id="ticket_menu",
        options=[
            discord.SelectOption(label="General Support", value="general", description="Need help with general questions?", emoji="🎫"),
            discord.SelectOption(label="Report Player", value="report", description="Report rule breakers", emoji="⚠️"),
            discord.SelectOption(label="Feedback", value="feedback", description="Have a suggestion for us?", emoji="💡")
        ]
    )
    async def select_callback(self, i: discord.Interaction, select: discord.ui.Select):
        guild = i.guild
        # Thiết lập quyền hạn: Chỉ người mở ticket và Admin mới thấy
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            i.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await guild.create_text_channel(f"ticket-{i.user.name}", overwrites=overwrites)
        
        # Embed chào mừng bên trong ticket
        embed = discord.Embed(
            title=f"Support Ticket: {select.values[0].capitalize()}",
            description=f"Welcome {i.user.mention}! Our staff will be with you shortly. Please describe your issue.",
            color=discord.Color.green()
        )
        await channel.send(embed=embed, view=TicketControls())
        await i.response.send_message(f"Your ticket has been created: {channel.mention}", ephemeral=True)

class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Đăng ký View để các nút bấm hoạt động vĩnh viễn
        self.bot.add_view(TicketLauncher())
        self.bot.add_view(TicketControls())
        print("-> Cog [Ticket] loaded!")

    @app_commands.command(name="setup_ticket", description="Display the Ticket Panel")
    @app_commands.default_permissions(administrator=True)
    async def setup_ticket(self, interaction: discord.Interaction):
        # Embed Panel giống ảnh mẫu
        embed = discord.Embed(
            title="✨ Support Center", 
            description="**Welcome to our Support Center.**\n\nIf you have any questions or need assistance, please open a ticket by selecting a category below.",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url="https://i.pinimg.com/736x/b7/17/f8/b717f8505781eecc83f414cf1bb51470.jpg") 
        embed.set_footer(text="Please do not abuse the ticket system.")
        
        await interaction.channel.send(embed=embed, view=TicketLauncher())
        await interaction.response.send_message("Ticket Panel posted!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketCog(bot))