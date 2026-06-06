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
        placeholder='E.g.: You have been inactive...',
        required=True,
        max_length=500
    )

    def __init__(self, selected_members: list[str]):
        super().__init__()
        self.selected_members = selected_members

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("⏳ Processing bulk kick...", ephemeral=True)
        success, failed = 0, 0
        for m_id in self.selected_members:
            member = interaction.guild.get_member(int(m_id))
            if member:
                try:
                    await member.send(f"You have been kicked from {interaction.guild.name}. Reason: {self.reason.value}")
                    await member.kick(reason=self.reason.value)
                    success += 1
                except: failed += 1
        await interaction.followup.send(f"✅ Finished: {success} kicked, {failed} failed.", ephemeral=True)

# ========================================================
# MAIN COG: MODERATION
# ========================================================
class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        conn = sqlite3.connect('bot_database.db')
        conn.execute("CREATE TABLE IF NOT EXISTS DailyMessageCount (user_id INTEGER, date_str TEXT, msg_count INTEGER DEFAULT 0, PRIMARY KEY (user_id, date_str))")
        thirty_days_ago = (discord.utils.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        conn.execute("DELETE FROM DailyMessageCount WHERE date_str < ?", (thirty_days_ago,))
        conn.commit(); conn.close()
        print("-> Cog [Moderation] loaded successfully!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild: return
        today = discord.utils.utcnow().strftime('%Y-%m-%d')
        conn = sqlite3.connect('bot_database.db')
        conn.execute("INSERT INTO DailyMessageCount VALUES (?, ?, 1) ON CONFLICT(user_id, date_str) DO UPDATE SET msg_count = msg_count + 1", (message.author.id, today))
        conn.commit(); conn.close()

    def check_hierarchy(self, i, m):
        if m.top_role >= i.guild.me.top_role: return "❌ Cannot punish higher role!"
        if m.id == i.user.id: return "❌ Cannot punish yourself!"
        return None

    # --- NEW: SCAN ACTIVITY & BULK KICK ---
    @app_commands.command(name="scan_activity", description="List members activity in the last 30 days")
    @app_commands.default_permissions(kick_members=True)
    async def scan_activity(self, i: discord.Interaction):
        await i.response.defer()
        m_date = (discord.utils.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        conn = sqlite3.connect('bot_database.db')
        data = {row[0]: row[1] for row in conn.execute("SELECT user_id, SUM(msg_count) FROM DailyMessageCount WHERE date_str >= ? GROUP BY user_id", (m_date,)).fetchall()}
        conn.close()
        lines = ["**Rank | Name | Msgs | ID**"]
        for idx, m in enumerate([m for m in i.guild.members if not m.bot], 1):
            lines.append(f"`{idx:03}` | {m.display_name[:12]:<12} | {data.get(m.id, 0):<5} | `{m.id}`")
        for chunk in [lines[j:j+20] for j in range(0, len(lines), 20)]: await i.followup.send("\n".join(chunk))

    @app_commands.command(name="bulk_kick", description="Kick members by index/ID list (separated by comma)")
    @app_commands.default_permissions(kick_members=True)
    async def bulk_kick(self, i: discord.Interaction, targets: str, reason: str = "Inactive"):
        m_list = [m for m in i.guild.members if not m.bot]
        t_list = [t.strip() for t in targets.split(",")]
        kicked = []
        for t in t_list:
            m = m_list[int(t)-1] if (t.isdigit() and len(t) <= 3) else i.guild.get_member(int(t))
            if m: await m.kick(reason=reason); kicked.append(m.name)
        await i.response.send_message(f"✅ Kicked: {', '.join(kicked)}")

    # --- OLD COMMANDS (KEPT) ---
    @app_commands.command(name="kick", description="Kick a member")
    async def kick(self, i: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if err := self.check_hierarchy(i, member): await i.response.send_message(err, ephemeral=True); return
        await member.kick(reason=reason); await i.response.send_message(f"✅ Kicked {member.name}")

    @app_commands.command(name="ban", description="Ban a member")
    async def ban(self, i: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if err := self.check_hierarchy(i, member): await i.response.send_message(err, ephemeral=True); return
        await member.ban(reason=reason); await i.response.send_message(f"🔨 Banned {member.name}")

    @app_commands.command(name="timeout", description="Timeout a member")
    async def timeout(self, i: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason"):
        await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        await i.response.send_message(f"🤫 Timed out {member.name} for {minutes}m")

    @app_commands.command(name="warn", description="Warn a member")
    async def warn(self, i: discord.Interaction, member: discord.Member, reason: str):
        count = database.add_warning(i.guild.id, member.id, i.user.id, reason)
        await i.response.send_message(f"⚠️ {member.name} warned (Total: {count})")

    @app_commands.command(name="checkwarn", description="Check warnings")
    async def checkwarn(self, i: discord.Interaction, member: discord.Member):
        records = database.get_warnings(i.guild.id, member.id)
        if not records: await i.response.send_message("✅ Clean record!")
        else: await i.response.send_message(f"Warnings found: {len(records)}")

    @app_commands.command(name="clearwarn", description="Clear all warnings")
    async def clearwarn(self, i: discord.Interaction, member: discord.Member):
        database.clear_warnings(i.guild.id, member.id)
        await i.response.send_message(f"🧹 Warnings cleared for {member.name}")

    @app_commands.command(name="removewarn", description="Remove specific warning")
    async def removewarn(self, i: discord.Interaction, warning_id: int):
        database.remove_specific_warning(i.guild.id, warning_id)
        await i.response.send_message("✅ Warning removed.")

    @app_commands.command(name="untimeout", description="Untimeout member")
    async def untimeout(self, i: discord.Interaction, member: discord.Member):
        await member.timeout(None); await i.response.send_message(f"🔊 Untimed out {member.name}")

    @app_commands.command(name="unban", description="Unban member")
    async def unban(self, i: discord.Interaction, user: discord.User):
        await i.guild.unban(user); await i.response.send_message(f"🕊️ Unbanned {user.name}")

async def setup(bot): await bot.add_cog(Moderation(bot))