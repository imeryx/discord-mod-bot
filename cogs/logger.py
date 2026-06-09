import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime

class LoggerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        conn = sqlite3.connect('bot_database.db')
        conn.execute("CREATE TABLE IF NOT EXISTS ServerLogConfig (guild_id INTEGER PRIMARY KEY, log_channel_id INTEGER)")
        conn.commit()
        conn.close()
        print("-> Cog [Ultimate Server Logger] loaded!")

    def get_log_channel(self, guild):
        conn = sqlite3.connect('bot_database.db')
        row = conn.execute("SELECT log_channel_id FROM ServerLogConfig WHERE guild_id = ?", (guild.id,)).fetchone()
        conn.close()
        if row and row[0]:
            return guild.get_channel(row[0])
        return None

    # ========================================================
    # 1. MESSAGE LOGS (DELETED / EDITED)
    # ========================================================
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        channel = self.get_log_channel(message.guild)
        if not channel: return

        embed = discord.Embed(
            title="🗑️ Message Deleted",
            description=f"**Author:** {message.author.mention} ({message.author.id})\n**Channel:** {message.channel.mention}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        content = message.content[:1024] if message.content else "*No text content (Might be an Embed/Image)*"
        embed.add_field(name="Content", value=content, inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content: return
        channel = self.get_log_channel(before.guild)
        if not channel: return

        embed = discord.Embed(
            title="✏️ Message Edited",
            description=f"**Author:** {before.author.mention} ({before.author.id})\n**Channel:** {before.channel.mention}\n[👉 Jump to Message]({after.jump_url})",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Before", value=before.content[:1024] or "*Empty*", inline=False)
        embed.add_field(name="After", value=after.content[:1024] or "*Empty*", inline=False)
        await channel.send(embed=embed)

    # ========================================================
    # 2. MEMBER LOGS (JOIN / LEAVE)
    # ========================================================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = self.get_log_channel(member.guild)
        if not channel: return
        
        embed = discord.Embed(
            title="📥 Member Joined",
            description=f"{member.mention} **{member.name}** joined the server.",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        # Kiểm tra xem tài khoản lập bao lâu rồi (cảnh báo nick ảo)
        account_age = (discord.utils.utcnow() - member.created_at).days
        embed.add_field(name="Account Age", value=f"{account_age} days old", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = self.get_log_channel(member.guild)
        if not channel: return

        embed = discord.Embed(
            title="👋 Member Left",
            description=f"{member.mention} **{member.name}** left the server.",
            color=discord.Color.dark_gray(),
            timestamp=discord.utils.utcnow()
        )
        # Thời gian đã gắn bó với server
        stay_duration = (discord.utils.utcnow() - member.joined_at).days if member.joined_at else "?"
        embed.add_field(name="Stay Duration", value=f"{stay_duration} days", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

    # ========================================================
    # 3. MEMBER UPDATES (NICKNAME, ROLES, TIMEOUT)
    # ========================================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        channel = self.get_log_channel(before.guild)
        if not channel: return

        # A. Đổi Nickname
        if before.nick != after.nick:
            embed = discord.Embed(
                title="📝 Nickname Changed",
                description=f"**User:** {after.mention}",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Before", value=before.nick or before.name, inline=True)
            embed.add_field(name="After", value=after.nick or after.name, inline=True)
            await channel.send(embed=embed)

        # B. Thêm/Xóa Role
        if before.roles != after.roles:
            added_roles = [role.mention for role in after.roles if role not in before.roles]
            removed_roles = [role.mention for role in before.roles if role not in after.roles]

            if added_roles:
                embed = discord.Embed(title="🛡️ Roles Added", description=f"**User:** {after.mention}\n**Roles:** {', '.join(added_roles)}", color=discord.Color.green(), timestamp=discord.utils.utcnow())
                await channel.send(embed=embed)
            if removed_roles:
                embed = discord.Embed(title="🛡️ Roles Removed", description=f"**User:** {after.mention}\n**Roles:** {', '.join(removed_roles)}", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                await channel.send(embed=embed)

        # C. Bị Timeout
        if before.communication_disabled_until != after.communication_disabled_until:
            if after.communication_disabled_until:
                embed = discord.Embed(
                    title="🔇 User Timed Out",
                    description=f"**User:** {after.mention}\n**Until:** {discord.utils.format_dt(after.communication_disabled_until, 'F')}",
                    color=discord.Color.dark_red(),
                    timestamp=discord.utils.utcnow()
                )
                await channel.send(embed=embed)

    # ========================================================
    # 4. VOICE CHANNEL UPDATES (JOIN / LEAVE / MOVE)
    # ========================================================
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        channel = self.get_log_channel(member.guild)
        if not channel: return

        # Tham gia Voice
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(description=f"🔊 {member.mention} **joined voice channel** {after.channel.mention}", color=discord.Color.brand_green(), timestamp=discord.utils.utcnow())
            await channel.send(embed=embed)
            
        # Rời Voice
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(description=f"🔇 {member.mention} **left voice channel** {before.channel.mention}", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
            await channel.send(embed=embed)
            
        # Chuyển kênh Voice
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            embed = discord.Embed(description=f"🔀 {member.mention} **moved** from {before.channel.mention} to {after.channel.mention}", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            await channel.send(embed=embed)

    # ========================================================
    # 5. SERVER UPDATES
    # ========================================================
    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        channel = self.get_log_channel(before)
        if not channel: return

        if before.name != after.name:
            embed = discord.Embed(
                title="🏢 Server Name Changed",
                color=discord.Color.purple(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Before", value=before.name, inline=True)
            embed.add_field(name="After", value=after.name, inline=True)
            await channel.send(embed=embed)

    # ========================================================
    # SETUP COMMAND
    # ========================================================
    @app_commands.command(name="setup_logger", description="Set up the channel to track all server and member activities")
    @app_commands.default_permissions(administrator=True)
    async def setup_logger(self, i: discord.Interaction, log_channel: discord.TextChannel):
        conn = sqlite3.connect('bot_database.db')
        conn.execute(
            "INSERT INTO ServerLogConfig (guild_id, log_channel_id) VALUES (?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET log_channel_id = excluded.log_channel_id", 
            (i.guild.id, log_channel.id)
        )
        conn.commit()
        conn.close()

        await i.response.send_message(f"✅ **Server Logger Active!** Monitoring all messages, voice channels, roles, and nicknames in {log_channel.mention}.", ephemeral=True)

async def setup(bot): await bot.add_cog(LoggerCog(bot))