import discord
from discord.ext import commands
from discord import app_commands
import datetime
import random
import sqlite3
from collections import defaultdict

# ========================================================
# POP-UP MODAL CAPTCHA (PROFESSIONAL ANTI-RAID)
# ========================================================
class CaptchaModal(discord.ui.Modal):
    def __init__(self, role_id, log_channel_id):
        self.role_id = role_id
        self.log_channel_id = log_channel_id
        
        # Generate a random math problem
        self.num1 = random.randint(1, 10)
        self.num2 = random.randint(1, 10)
        self.correct_answer = str(self.num1 + self.num2)
        
        # Modal Title acts as the Captcha question
        super().__init__(title=f"Security Captcha: {self.num1} + {self.num2} = ?")
        
        self.answer_input = discord.ui.TextInput(
            label="Please solve the math problem above:",
            style=discord.TextStyle.short,
            placeholder="Type your answer here...",
            required=True,
            max_length=3
        )
        self.add_item(self.answer_input)

    async def on_submit(self, i: discord.Interaction):
        log_channel = i.guild.get_channel(self.log_channel_id) if self.log_channel_id else None

        # Check if the answer is correct
        if self.answer_input.value.strip() == self.correct_answer:
            role = i.guild.get_role(self.role_id)
            if role:
                await i.user.add_roles(role)
                await i.response.send_message("✅ **Verification successful!** You now have access to the server.", ephemeral=True)
                
                # Log the success
                if log_channel:
                    await log_channel.send(f"✅ **Verified:** {i.user.mention} (`{i.user.id}`) passed the captcha.")
            else:
                await i.response.send_message("⚠️ Error: Verification role not found. Contact an Admin.", ephemeral=True)
        else:
            # If the answer is wrong
            await i.response.send_message("❌ **Verification failed!** Incorrect answer. You are muted for 5 minutes.", ephemeral=True)
            
            # Log the failure
            if log_channel:
                await log_channel.send(f"⚠️ **Failed Captcha:** {i.user.mention} answered `{self.answer_input.value}` instead of `{self.correct_answer}`.")
            
            try:
                await i.user.timeout(datetime.timedelta(minutes=5), reason="Failed Captcha (Anti-Raid)")
            except: pass

class VerifyPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Click to Verify", style=discord.ButtonStyle.success, emoji="🛡️", custom_id="btn_verify_modal")
    async def verify_btn(self, i: discord.Interaction, b: discord.ui.Button):
        conn = sqlite3.connect('bot_database.db')
        row = conn.execute("SELECT verified_role_id, security_log_id FROM SecurityConfig WHERE guild_id = ?", (i.guild.id,)).fetchone()
        conn.close()

        if not row:
            return await i.response.send_message("⚠️ Admin has not configured the security system yet!", ephemeral=True)

        role_id, log_channel_id = row[0], row[1]
        
        if i.user.get_role(role_id):
            return await i.response.send_message("✅ You are already verified!", ephemeral=True)

        # Trigger the Pop-up Modal instead of sending a new message
        await i.response.send_modal(CaptchaModal(role_id, log_channel_id))

# ========================================================
# MAIN COG: ANTI-RAID & ANTI-NUKE
# ========================================================
class SecurityCog(commands.Cog):
    def __init__(self, bot): 
        self.bot = bot
        self.spam_tracker = defaultdict(list)
        self.nuke_tracker = defaultdict(list)

    @commands.Cog.listener()
    async def on_ready(self):
        conn = sqlite3.connect('bot_database.db')
        conn.execute("CREATE TABLE IF NOT EXISTS SecurityConfig (guild_id INTEGER PRIMARY KEY, verified_role_id INTEGER, security_log_id INTEGER)")
        conn.commit(); conn.close()
        self.bot.add_view(VerifyPanel())

    # --- ANTI-NUKE ---
    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        if entry.user.id == self.bot.user.id: return

        dangerous_actions = [discord.AuditLogAction.ban, discord.AuditLogAction.kick, discord.AuditLogAction.channel_delete, discord.AuditLogAction.role_delete]

        if entry.action in dangerous_actions:
            now = discord.utils.utcnow()
            user_id = entry.user.id
            
            self.nuke_tracker[user_id].append(now)
            self.nuke_tracker[user_id] = [t for t in self.nuke_tracker[user_id] if (now - t).total_seconds() <= 10]

            if len(self.nuke_tracker[user_id]) >= 3:
                guild = entry.guild
                rogue_admin = guild.get_member(user_id)
                if rogue_admin:
                    try:
                        await rogue_admin.ban(reason="ANTI-NUKE TRIGGERED: Server sabotage detected")
                        self.nuke_tracker[user_id].clear()
                        
                        conn = sqlite3.connect('bot_database.db')
                        row = conn.execute("SELECT security_log_id FROM SecurityConfig WHERE guild_id = ?", (guild.id,)).fetchone()
                        conn.close()
                        if row and row[0]:
                            log_channel = guild.get_channel(row[0])
                            if log_channel:
                                await log_channel.send(f"🚨 **RED ALERT (ANTI-NUKE)** 🚨\nDetected {rogue_admin.mention} attempting to nuke the server. **The system has automatically BANNED this user!**")
                    except discord.Forbidden: pass

    # --- ANTI-RAID GATE (ACCOUNT AGE) ---
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        account_age = discord.utils.utcnow() - member.created_at
        if account_age.days < 3:
            try:
                await member.send("🛑 **Access Denied:** Your account is too new (under 3 days old). This is an anti-raid measure.")
            except: pass
            await member.kick(reason="Anti-Raid: Account under 3 days old")

    # --- ANTI-SPAM ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return

        user_id = message.author.id
        now = discord.utils.utcnow()
        
        self.spam_tracker[user_id].append(now)
        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] if (now - t).total_seconds() <= 4]

        if len(self.spam_tracker[user_id]) >= 5:
            try:
                await message.author.timeout(datetime.timedelta(minutes=10), reason="Anti-Raid: Chat spamming")
                await message.channel.send(f"⚠️ {message.author.mention} has been automatically muted for 10 minutes for spamming.")
                self.spam_tracker[user_id].clear()
            except discord.Forbidden: pass

    # --------------------------------------------------------
    # SECURITY SETUP COMMAND
    # --------------------------------------------------------
    @app_commands.command(name="setup_security", description="Set up the verification gate and Anti-Nuke alert channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_security(
        self, 
        i: discord.Interaction, 
        verify_role: discord.Role, 
        target_channel: discord.TextChannel = None, # Đã thêm tùy chọn kênh gửi Panel
        log_channel: discord.TextChannel = None
    ):
        await i.response.defer(ephemeral=True) # Tránh lỗi "Interaction failed" nếu bot xử lý chậm

        log_id = log_channel.id if log_channel else None
        
        # Nếu bạn không chọn target_channel, bot sẽ gửi ở kênh bạn đang gõ lệnh
        send_channel = target_channel or i.channel
        
        conn = sqlite3.connect('bot_database.db')
        conn.execute(
            "INSERT INTO SecurityConfig (guild_id, verified_role_id, security_log_id) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET verified_role_id = excluded.verified_role_id, security_log_id = excluded.security_log_id", 
            (i.guild.id, verify_role.id, log_id)
        )
        conn.commit(); conn.close()

        embed = discord.Embed(
            title="🛡️ SERVER SECURITY GATE",
            description=(
                "**Multi-layer server protection system is active.**\n\n"
                "Please click the button below to verify and gain access.\n"
            ),
            color=0x2b2d31
        )
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1161/1161388.png")
        embed.set_footer(text="Automated Anti-Raid System | Protected by Elfaria Bot")

        # Gửi Panel vào đúng kênh bạn đã chọn
        await send_channel.send(embed=embed, view=VerifyPanel())
        
        msg = f"✅ Verification gate set up successfully in {send_channel.mention}! Users will receive the role {verify_role.mention}."
        if log_channel: 
            msg += f"\n🚨 Anti-Nuke Alert Channel: {log_channel.mention}"
        else:
            msg += f"\n⚠️ Warning: No log_channel selected. Anti-Nuke alerts will not be sent anywhere."
            
        await i.followup.send(msg)

async def setup(bot): await bot.add_cog(SecurityCog(bot))