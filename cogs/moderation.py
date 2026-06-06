import discord
from discord.ext import commands
from discord import app_commands
import datetime
import sqlite3
import database

# ========================================================
# AUTO-PUNISHMENT SYSTEM
# ========================================================
async def apply_auto_punishment(interaction_or_message, member: discord.Member, warn_count: int):
    guild = member.guild
    bot_user = guild.me
    channel = interaction_or_message.channel

    if warn_count == 3:
        try:
            duration = datetime.timedelta(hours=1)
            await member.timeout(duration, reason=f"System: Accumulated {warn_count} warnings.")
            await channel.send(f"🤖 **Auto-Punish:** {member.mention} has accumulated **3 warnings**. Automatically timed out for 1 hour!")
        except Exception as e:
            print(f"Auto-Punish Timeout Error: {e}")

    elif warn_count == 5:
        try:
            if member.top_role < bot_user.top_role:
                await member.kick(reason=f"System: Accumulated {warn_count} warnings.")
                await channel.send(f"🤖 **Auto-Punish:** {member.mention} has accumulated **5 warnings**. Automatically kicked from the server!")
        except Exception as e:
            print(f"Auto-Punish Kick Error: {e}")

    elif warn_count >= 7:
        try:
            if member.top_role < bot_user.top_role:
                await member.ban(reason=f"System: Accumulated {warn_count} warnings.", delete_message_days=0)
                await channel.send(f"🔨 **Auto-Punish:** {member.mention} has accumulated **7 warnings**. Automatically permanently banned!")
        except Exception as e:
            print(f"Auto-Punish Ban Error: {e}")


# ========================================================
# MAIN COG: MODERATION
# ========================================================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # INITIALIZE DAILY MESSAGE COUNT DATABASE
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS DailyMessageCount (
                user_id INTEGER,
                date_str TEXT,
                msg_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, date_str)
            )
        """)
        
        # Cleanup: Automatically delete records older than 30 days
        thirty_days_ago = (discord.utils.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        cursor.execute("DELETE FROM DailyMessageCount WHERE date_str < ?", (thirty_days_ago,))
        
        conn.commit()
        conn.close()
        print("-> Cog [Moderation] loaded successfully! (Detailed version with Bulk Kick)")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Silently log and count messages
        if message.author.bot or not message.guild:
            return
            
        today = discord.utils.utcnow().strftime('%Y-%m-%d')
        user_id = message.author.id
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO DailyMessageCount (user_id, date_str, msg_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, date_str) 
            DO UPDATE SET msg_count = msg_count + 1
        """, (user_id, today))
        conn.commit()
        conn.close()

    # Role Hierarchy Check (Shared Utility)
    def check_hierarchy(self, interaction: discord.Interaction, member: discord.Member):
        if member.top_role >= interaction.guild.me.top_role:
            return "❌ I cannot punish a user whose role is higher than or equal to mine!"
        if member.id == interaction.user.id:
            return "❌ You cannot punish yourself!"
        return None

    # ================= 1. SCAN ACTIVITY =================
    @app_commands.command(name="scan_activity", description="List members activity in the last 30 days")
    @app_commands.default_permissions(kick_members=True)
    async def scan_activity(self, interaction: discord.Interaction):
        # Defer the response as compiling a large list might take a few seconds
        await interaction.response.defer()
        
        thirty_days_ago = (discord.utils.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Retrieve data from Database
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, SUM(msg_count) 
            FROM DailyMessageCount 
            WHERE date_str >= ? 
            GROUP BY user_id
            ORDER BY SUM(msg_count) ASC
        """, (thirty_days_ago,))
        
        active_data = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        lines = ["**Rank | Name | Messages (30d) | ID**"]
        
        # Filter out bots and assign indices
        valid_members = [m for m in interaction.guild.members if not m.bot]
        
        for idx, member in enumerate(valid_members, 1):
            count = active_data.get(member.id, 0)
            # Formatting to align columns nicely
            line = f"`{idx:03}` | {member.display_name[:15]:<15} | {count:<10} | `{member.id}`"
            lines.append(line)

        # Discord has a 2000 character limit per message, so we send in chunks of 20
        if len(lines) == 1:
            return await interaction.followup.send("✅ No members found to scan.")

        for i in range(0, len(lines), 20):
            chunk = "\n".join(lines[i:i+20])
            await interaction.followup.send(chunk)

    # ================= 2. BULK KICK =================
    @app_commands.command(name="bulk_kick", description="Kick multiple members using their ID or Rank index")
    @app_commands.describe(targets="Enter IDs or Rank indices separated by comma (e.g., 001, 005, 123456789)")
    @app_commands.default_permissions(kick_members=True)
    async def bulk_kick(self, interaction: discord.Interaction, targets: str, reason: str = "Inactive for 30 days"):
        # Defer and make it ephemeral so the target list is hidden
        await interaction.response.defer(ephemeral=True)
        
        valid_members = [m for m in interaction.guild.members if not m.bot]
        target_inputs = [t.strip() for t in targets.split(",") if t.strip()]
        
        kicked_names = []
        failed_names = []

        for target in target_inputs:
            member = None
            # Check if input is a 1-3 digit index (e.g., 1, 05, 012)
            if target.isdigit() and len(target) <= 3:
                idx = int(target) - 1
                if 0 <= idx < len(valid_members):
                    member = valid_members[idx]
            # Otherwise treat as Discord ID
            elif target.isdigit():
                member = interaction.guild.get_member(int(target))

            if member:
                # Check hierarchy before kicking
                if self.check_hierarchy(interaction, member):
                    failed_names.append(member.name)
                    continue
                    
                try:
                    # Attempt DM
                    try:
                        await member.send(f"You have been kicked from {interaction.guild.name}. Reason: {reason}")
                    except discord.HTTPException:
                        pass
                        
                    await member.kick(reason=reason)
                    kicked_names.append(member.name)
                except discord.Forbidden:
                    failed_names.append(member.name)
            else:
                failed_names.append(target) # Invalid target

        # Compile Result Message
        result_msg = ""
        if kicked_names:
            result_msg += f"✅ Successfully kicked: **{', '.join(kicked_names)}**\n"
        if failed_names:
            result_msg += f"❌ Failed to kick: **{', '.join(failed_names)}**"
            
        if not result_msg:
            result_msg = "⚠️ No valid targets found."
            
        await interaction.followup.send(result_msg)

    # ================= 3. KICK COMMAND =================
    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        error_msg = self.check_hierarchy(interaction, member)
        if error_msg:
            return await interaction.response.send_message(error_msg, ephemeral=True)

        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(f"✅ **{member.name}** was kicked from the server by {interaction.user.mention}. \nReason: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    # ================= 4. BAN COMMAND =================
    @app_commands.command(name="ban", description="Permanently ban a member from the server")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        error_msg = self.check_hierarchy(interaction, member)
        if error_msg:
            return await interaction.response.send_message(error_msg, ephemeral=True)

        try:
            await member.ban(reason=reason, delete_message_days=0)
            await interaction.response.send_message(f"🔨 **{member.name}** was permanently banned by {interaction.user.mention}. \nReason: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    # ================= 5. TIMEOUT COMMAND =================
    @app_commands.command(name="timeout", description="Mute a member for a specified amount of time")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(minutes="Duration of the timeout in minutes")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        error_msg = self.check_hierarchy(interaction, member)
        if error_msg:
            return await interaction.response.send_message(error_msg, ephemeral=True)

        try:
            duration = datetime.timedelta(minutes=minutes)
            await member.timeout(duration, reason=reason)
            await interaction.response.send_message(f"🤫 **{member.name}** has been timed out for {minutes} minutes by {interaction.user.mention}. \nReason: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    # ================= 6. WARN COMMAND =================
    @app_commands.command(name="warn", description="Issue a warning to a member and log it")
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
            await interaction.response.send_message(f"⚠️ **{member.name}** has received their **{warn_count}** warning from {interaction.user.mention}. \nReason: {reason}")
            
            await apply_auto_punishment(interaction, member, warn_count)
        except Exception as e:
            await interaction.response.send_message(f"❌ Database error occurred: {e}", ephemeral=True)

    # ================= 7. CHECKWARN COMMAND =================
    @app_commands.command(name="checkwarn", description="Check the warning history of a member")
    @app_commands.default_permissions(moderate_members=True)
    async def checkwarn(self, interaction: discord.Interaction, member: discord.Member):
        records = database.get_warnings(interaction.guild.id, member.id)
        
        if not records:
            return await interaction.response.send_message(f"✅ **{member.name}** has a clean record, no warnings!", ephemeral=True)
        
        embed = discord.Embed(
            title=f"Warning History of {member.name}", 
            description=f"Total warnings: **{len(records)}**",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        for idx, record in enumerate(records, 1):
            warning_id, mod_id, reason, timestamp = record 
            date_only = timestamp[:10] 
            
            embed.add_field(
                name=f"Warning #{idx} - Date {date_only}", 
                value=f"**ID:** `{warning_id}`\n**Reason:** {reason}\n**Moderator:** <@{mod_id}>", 
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

    # ================= 8. CLEARWARN COMMAND =================
    @app_commands.command(name="clearwarn", description="Clear all warnings from a member's record")
    @app_commands.default_permissions(moderate_members=True)
    async def clearwarn(self, interaction: discord.Interaction, member: discord.Member):
        if member.id == interaction.user.id:
            return await interaction.response.send_message("❌ You cannot clear your own warning history!", ephemeral=True)

        try:
            records = database.get_warnings(interaction.guild.id, member.id)
            if not records:
                return await interaction.response.send_message(f"❌ **{member.name}** currently has no warnings to clear!", ephemeral=True)
            
            database.clear_warnings(interaction.guild.id, member.id)
            await interaction.response.send_message(f"🧹 Successfully cleared all warning records for **{member.name}** by {interaction.user.mention}.")
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    # ================= 9. REMOVEWARN COMMAND =================
    @app_commands.command(name="removewarn", description="Remove a specific warning using its ID")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(warning_id="Enter the Warning ID (found via /checkwarn)")
    async def removewarn(self, interaction: discord.Interaction, warning_id: int):
        try:
            success = database.remove_specific_warning(interaction.guild.id, warning_id)
            
            if success:
                await interaction.response.send_message(f"✅ Successfully removed warning ID **`{warning_id}`**.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Warning ID **`{warning_id}`** not found in this server. Please verify using `/checkwarn`.", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    # ================= 10. UNTIMEOUT COMMAND =================
    @app_commands.command(name="untimeout", description="Remove a timeout (unmute) from a member")
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        error_msg = self.check_hierarchy(interaction, member)
        if error_msg:
            return await interaction.response.send_message(error_msg, ephemeral=True)

        if not member.is_timed_out():
            return await interaction.response.send_message(f"❌ **{member.name}** is not currently timed out!", ephemeral=True)

        try:
            await member.timeout(None, reason=reason)
            await interaction.response.send_message(f"🔊 **{member.name}**'s timeout was successfully removed by {interaction.user.mention}. \nReason: {reason}")
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

    # ================= 11. UNBAN COMMAND =================
    @app_commands.command(name="unban", description="Revoke a ban for a user")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="The ID of the user to unban")
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided"):
        try:
            await interaction.guild.unban(user, reason=reason)
            await interaction.response.send_message(f"🕊️ **{user.name}** was successfully unbanned by {interaction.user.mention}. \nReason: {reason}")
        
        except discord.NotFound:
            await interaction.response.send_message(f"❌ Account **{user.name}** is not currently banned in this server!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))