import discord
from discord.ext import commands
from discord import app_commands
import datetime
import sqlite3
import database

# ========================================================
# MODAL: KICK REASON INPUT
# ========================================================
class KickReasonModal(discord.ui.Modal, title='Confirm Member Kick'):
    reason = discord.ui.TextInput(
        label='Kick Reason (Will be sent via DM)',
        style=discord.TextStyle.paragraph,
        placeholder='E.g.: You have been inactive in the server for 14 days...',
        required=True,
        max_length=500
    )

    def __init__(self, selected_members: list[str]):
        super().__init__()
        self.selected_members = selected_members

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("⏳ Sending DMs and kicking selected members...", ephemeral=True)
        
        kicked_count = 0
        failed_count = 0
        
        for member_id in self.selected_members:
            member = interaction.guild.get_member(int(member_id))
            if member:
                # 1. Attempt to send DM
                try:
                    embed = discord.Embed(
                        title=f"Kicked from {interaction.guild.name}",
                        description=f"**Reason:**\n{self.reason.value}",
                        color=discord.Color.red()
                    )
                    await member.send(embed=embed)
                except discord.HTTPException:
                    pass 
                
                # 2. Execute Kick
                try:
                    await member.kick(reason=self.reason.value)
                    kicked_count += 1
                except discord.Forbidden:
                    failed_count += 1 
                    
        await interaction.followup.send(f"✅ **Done!** Successfully kicked **{kicked_count}** members. (Failed: {failed_count})", ephemeral=True)


# ========================================================
# VIEW: INACTIVE FILTER SELECTION
# ========================================================
class InactiveFilterView(discord.ui.View):
    def __init__(self, options):
        super().__init__(timeout=600) 
        self.selected_members = []
        
        self.select_menu = discord.ui.Select(
            placeholder="Open to select members to kick...",
            min_values=1,
            max_values=len(options),
            options=options
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

        self.kick_btn = discord.ui.Button(label="Proceed to Kick Selected", style=discord.ButtonStyle.danger, disabled=True, emoji="🔨")
        self.kick_btn.callback = self.kick_callback
        self.add_item(self.kick_btn)

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_members = self.select_menu.values
        self.kick_btn.disabled = False 
        await interaction.response.edit_message(view=self)

    async def kick_callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ You do not have permission to kick members!", ephemeral=True)
        
        await interaction.response.send_modal(KickReasonModal(self.selected_members))


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
        print("-> Cog [Moderation] loaded successfully! (Inactive Scanner Integrated)")

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

    # ================= 1. SCAN INACTIVE =================
    @app_commands.command(name="scan_inactive", description="Filter members who have been inactive in the last 14 days")
    @app_commands.describe(max_messages="Max messages allowed to be considered inactive (e.g., 0 or 5)")
    @app_commands.default_permissions(kick_members=True)
    async def scan_inactive(self, interaction: discord.Interaction, max_messages: int = 0):
        await interaction.response.defer(ephemeral=True)
        
        now = discord.utils.utcnow()
        fourteen_days_ago = now - datetime.timedelta(days=14)
        date_threshold = fourteen_days_ago.strftime('%Y-%m-%d')
        
        # Retrieve data from Database
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, SUM(msg_count) 
            FROM DailyMessageCount 
            WHERE date_str >= ? 
            GROUP BY user_id
        """, (date_threshold,))
        
        active_data = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        old_inactive = []
        new_inactive = []

        for member in interaction.guild.members:
            if member.bot: continue
            
            count = active_data.get(member.id, 0)
            
            if count <= max_messages:
                if member.joined_at and member.joined_at > fourteen_days_ago:
                    new_inactive.append((member, count))
                else:
                    old_inactive.append((member, count))

        all_inactives = old_inactive + new_inactive
        
        if not all_inactives:
            return await interaction.followup.send("✅ Excellent! No inactive members meet this criteria.")

        display_list = all_inactives[:25]
        dropdown_options = []
        
        for member, count in display_list:
            is_new = member.joined_at > fourteen_days_ago
            status_text = "New Member (<14 days)" if is_new else "Old Member"
            desc = f"{status_text} | Sent {count} messages"
            
            dropdown_options.append(
                discord.SelectOption(
                    label=member.display_name[:100],
                    description=desc,
                    value=str(member.id),
                    emoji="🌱" if is_new else "👻"
                )
            )

        embed = discord.Embed(
            title="🔍 Inactive Members Scan Report",
            description=f"Fetched data from the last 14 days. Limit criteria: **≤ {max_messages} messages**.",
            color=discord.Color.orange()
        )
        embed.add_field(name="👻 Inactive Old Members", value=str(len(old_inactive)), inline=True)
        embed.add_field(name="🌱 Inactive New Members", value=str(len(new_inactive)), inline=True)
        
        warning = ""
        if len(all_inactives) > 25:
            warning = f"\n⚠️ *Note: Found {len(all_inactives)} members, but the dropdown below only shows the first 25 due to UI limits.*"
        
        await interaction.followup.send(content=warning, embed=embed, view=InactiveFilterView(dropdown_options))

    # ================= 2. KICK COMMAND =================
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

    # ================= 3. BAN COMMAND =================
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

    # ================= 4. TIMEOUT COMMAND =================
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

    # ================= 5. WARN COMMAND =================
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

    # ================= 6. CHECKWARN COMMAND =================
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

    # ================= 7. CLEARWARN COMMAND =================
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

    # ================= 8. REMOVEWARN COMMAND =================
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

    # ================= 9. UNTIMEOUT COMMAND =================
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

    # ================= 10. UNBAN COMMAND =================
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