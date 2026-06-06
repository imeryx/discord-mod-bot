import discord
from discord.ext import commands
from discord import app_commands
import datetime
import sqlite3
import database

# ========================================================
# VIEW: EMBED PAGINATION (NÚT LẬT TRANG)
# ========================================================
class ActivityPaginationView(discord.ui.View):
    def __init__(self, data_chunks, title):
        super().__init__(timeout=600) # Tồn tại 10 phút
        self.data_chunks = data_chunks
        self.title = title
        self.current_page = 0
        self.max_page = len(data_chunks) - 1
        self.update_buttons()

    def update_buttons(self):
        self.first_page_btn.disabled = self.current_page == 0
        self.prev_page_btn.disabled = self.current_page == 0
        self.next_page_btn.disabled = self.current_page == self.max_page
        self.last_page_btn.disabled = self.current_page == self.max_page

    def get_embed(self):
        # Tạo Embed giống mẫu hình ảnh
        embed = discord.Embed(
            title=self.title, 
            description=self.data_chunks[self.current_page], 
            color=0x2b2d31 # Màu nền tối sang trọng
        )
        # Footer hiển thị trang và thời gian
        time_now = discord.utils.utcnow().strftime('%d/%m/%Y, %H:%M')
        embed.set_footer(text=f"Page {self.current_page + 1} • {time_now}")
        return embed

    @discord.ui.button(emoji="⏪", style=discord.ButtonStyle.secondary)
    async def first_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.primary)
    async def prev_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.primary)
    async def next_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(emoji="⏩", style=discord.ButtonStyle.secondary)
    async def last_page_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.max_page
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


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
        
        thirty_days_ago = (discord.utils.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        cursor.execute("DELETE FROM DailyMessageCount WHERE date_str < ?", (thirty_days_ago,))
        conn.commit()
        conn.close()
        print("-> Cog [Moderation] loaded successfully! (Pagination UI version)")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
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

    def check_hierarchy(self, interaction: discord.Interaction, member: discord.Member):
        if member.top_role >= interaction.guild.me.top_role:
            return "❌ I cannot punish a user whose role is higher than or equal to mine!"
        if member.id == interaction.user.id:
            return "❌ You cannot punish yourself!"
        return None

    # ================= 1. SCAN ACTIVITY (LẬT TRANG) =================
    @app_commands.command(name="scan_activity", description="List members activity in the last 30 days (Leaderboard style)")
    @app_commands.default_permissions(kick_members=True)
    async def scan_activity(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        thirty_days_ago = (discord.utils.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, SUM(msg_count) 
            FROM DailyMessageCount 
            WHERE date_str >= ? 
            GROUP BY user_id
        """, (thirty_days_ago,))
        
        active_data = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        valid_members = [m for m in interaction.guild.members if not m.bot]
        # QUAN TRỌNG: Sắp xếp người nhắn ít nhất (0 tin) lên đầu!
        valid_members.sort(key=lambda m: active_data.get(m.id, 0))

        pages_data = []
        current_page_lines = []
        
        for idx, member in enumerate(valid_members, 1):
            count = active_data.get(member.id, 0)
            # Format: **1.** tên_người_dùng ( @Tên ): **X messages**
            line = f"**{idx}.** {member.name} ( {member.mention} ): **{count} messages** `({member.id})`"
            current_page_lines.append(line)
            
            # Cứ đủ 10 người thì ngắt thành 1 trang
            if len(current_page_lines) == 10:
                pages_data.append("\n".join(current_page_lines))
                current_page_lines = []
                
        # Thêm những người còn lẻ tẻ vào trang cuối
        if current_page_lines:
            pages_data.append("\n".join(current_page_lines))

        if not pages_data:
            return await interaction.followup.send("✅ No members found to scan.")

        # Khởi tạo giao diện lật trang và gửi
        view = ActivityPaginationView(pages_data, "Inactive Members Scan (30 Days)")
        await interaction.followup.send(embed=view.get_embed(), view=view)


    # ================= 2. BULK KICK =================
    @app_commands.command(name="bulk_kick", description="Kick multiple members using their ID or Rank index")
    @app_commands.describe(targets="Enter IDs or Rank indices separated by comma (e.g., 1, 5, 123456789)")
    @app_commands.default_permissions(kick_members=True)
    async def bulk_kick(self, interaction: discord.Interaction, targets: str, reason: str = "Inactive for 30 days"):
        await interaction.response.defer(ephemeral=True)
        
        # ĐỒNG BỘ LOGIC SẮP XẾP VỚI LỆNH SCAN
        thirty_days_ago = (discord.utils.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, SUM(msg_count) FROM DailyMessageCount WHERE date_str >= ? GROUP BY user_id", (thirty_days_ago,))
        active_data = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        valid_members = [m for m in interaction.guild.members if not m.bot]
        valid_members.sort(key=lambda m: active_data.get(m.id, 0)) # Sort y hệt như lúc nãy
        
        target_inputs = [t.strip() for t in targets.split(",") if t.strip()]
        kicked_names = []
        failed_names = []

        for target in target_inputs:
            member = None
            if target.isdigit() and len(target) <= 3:
                idx = int(target) - 1
                if 0 <= idx < len(valid_members):
                    member = valid_members[idx]
            elif target.isdigit():
                member = interaction.guild.get_member(int(target))

            if member:
                if self.check_hierarchy(interaction, member):
                    failed_names.append(member.name)
                    continue
                    
                try:
                    try:
                        await member.send(f"You have been kicked from {interaction.guild.name}. Reason: {reason}")
                    except discord.HTTPException:
                        pass
                        
                    await member.kick(reason=reason)
                    kicked_names.append(member.name)
                except discord.Forbidden:
                    failed_names.append(member.name)
            else:
                failed_names.append(target) 

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