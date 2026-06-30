import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random

# ==========================================
# 1. HỆ THỐNG EMOJI VÀ DỮ LIỆU VẬT PHẨM
# ==========================================
class SYS_EMOJIS:
    COIN = "🪙" 
    WORK = "💻"
    WALLET = "💳"
    INVENTORY = "🎒"
    SHOP = "🛒"
    SINGLE = "🕸️"
    MARRIED = "💒"
    
    # 5 Cấp độ nhẫn (Bạn có thể thay ID custom emoji của server vào)
    RING_PLASTIC = "<:plastic_ring:1521432439476715540>" 
    RING_SILVER = "<:silver_ring:1521432589422956766>"
    RING_GOLD = "<:gold_ring:1521432692774932543>"
    RING_DIAMOND = "<:diamond_ring:1521432786701914142>"
    RING_ASTRITE = "<:astrite_ring:1521432868729917510>" # Hoặc dùng <a:astrite:123456789>

RING_SHOP = {
    "plastic": {"price": 1000, "name": "Plastic Ring", "emoji": SYS_EMOJIS.RING_PLASTIC, "tier": 1},
    "silver": {"price": 5000, "name": "Silver Ring", "emoji": SYS_EMOJIS.RING_SILVER, "tier": 2},
    "gold": {"price": 20000, "name": "Gold Ring", "emoji": SYS_EMOJIS.RING_GOLD, "tier": 3},
    "diamond": {"price": 100000, "name": "Diamond Ring", "emoji": SYS_EMOJIS.RING_DIAMOND, "tier": 4},
    "astrite": {"price": 500000, "name": "Astrite Ring", "emoji": SYS_EMOJIS.RING_ASTRITE, "tier": 5}
}

BG_SHOP = {
    "hanoi": {"price": 15000, "name": "Background 1", "url": "https://i.imgur.com/example1.jpg"},
    "mixue": {"price": 30000, "name": "Background 2", "url": "https://i.imgur.com/example2.jpg"},
    "cyber": {"price": 50000, "name": "Background 3", "url": "https://i.imgur.com/example3.jpg"}
}

# ==========================================
# 2. GIAO DIỆN CẦU HÔN (UI View)
# ==========================================
class ProposalView(discord.ui.View):
    def __init__(self, proposer: discord.Member, target: discord.Member, ring_type: str):
        super().__init__(timeout=60)
        self.proposer = proposer
        self.target = target
        self.ring_type = ring_type
        self.ring_info = RING_SHOP[ring_type]

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="❤️")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ This proposal is not for you!", ephemeral=True)
        
        self.stop()
        conn = sqlite3.connect('bot_database.db')
        
        # Cập nhật trạng thái kết hôn cho cả 2
        conn.execute("UPDATE Economy SET partner_id = ?, marriage_ring = ? WHERE user_id = ?", (self.target.id, self.ring_type, self.proposer.id))
        conn.execute("UPDATE Economy SET partner_id = ?, marriage_ring = ? WHERE user_id = ?", (self.proposer.id, self.ring_type, self.target.id))
        
        # Trừ nhẫn của người cầu hôn
        col_name = f"ring_{self.ring_type}"
        conn.execute(f"UPDATE Economy SET {col_name} = {col_name} - 1 WHERE user_id = ?", (self.proposer.id,))
        conn.commit()
        conn.close()

        await interaction.response.edit_message(content=f"🎉 **{self.target.mention} accepted!**\n{self.proposer.mention} and {self.target.mention} are now happily married with a {self.ring_info['emoji']} **{self.ring_info['name']}**! 💖", view=None)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="💔")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            return await interaction.response.send_message("❌ This proposal is not for you!", ephemeral=True)
        
        self.stop()
        await interaction.response.edit_message(content=f"💔 **{self.target.mention} declined the proposal.** You tried with a {self.ring_info['emoji']} {self.ring_info['name']}, but it wasn't enough, {self.proposer.mention}...", view=None)


# ==========================================
# 3. MODULE KINH TẾ CHÍNH
# ==========================================
class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.setup_database()

    def setup_database(self):
        conn = sqlite3.connect('bot_database.db')
        
        # 1. Vẫn giữ lệnh tạo bảng gốc để đề phòng trường hợp file chưa từng tồn tại
        conn.execute('''CREATE TABLE IF NOT EXISTS Economy (
                        user_id INTEGER PRIMARY KEY,
                        balance INTEGER DEFAULT 0,
                        partner_id INTEGER DEFAULT NULL
                    )''')
                    
        # 2. Nâng cấp cấu trúc (Migration) - Thêm các cột mới một cách an toàn
        new_columns = [
            ("ring_plastic", "INTEGER DEFAULT 0"),
            ("ring_silver", "INTEGER DEFAULT 0"),
            ("ring_gold", "INTEGER DEFAULT 0"),
            ("ring_diamond", "INTEGER DEFAULT 0"),
            ("ring_astrite", "INTEGER DEFAULT 0"),
            ("active_bg", "TEXT DEFAULT NULL"),
            ("marriage_ring", "TEXT DEFAULT NULL")
        ]
        
        for col_name, col_type in new_columns:
            try:
                # Lệnh ALTER TABLE dùng để nhét thêm cột mới vào bảng đang có sẵn dữ liệu
                conn.execute(f"ALTER TABLE Economy ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                # Nếu SQLite báo lỗi "Cột này đã tồn tại", bot sẽ lơ đi và chạy tiếp
                pass
                
        conn.commit()
        conn.close()
    def check_user(self, user_id):
        conn = sqlite3.connect('bot_database.db')
        conn.execute("INSERT OR IGNORE INTO Economy (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Economy V2] loaded successfully with 5-Tier Rings & Divorce!")

    # ------------------------------------------
    # LỆNH CÀY TIỀN (WORK) VỚI CÁC NHIỆM VỤ ĐA DẠNG
    # ------------------------------------------
    @app_commands.command(name="work", description="Do some tasks to earn coins!")
    @app_commands.checks.cooldown(1, 1800, key=lambda i: i.user.id) # Cooldown 30 phút
    async def work(self, i: discord.Interaction):
        self.check_user(i.user.id)
        
        # Hệ thống nhiệm vụ thường ngày quen thuộc
        tasks = [
            "Bạn đi làm thêm ca tối tại cửa hàng tiện lợi",
            "Bạn phụ giúp gia đình dọn dẹp nhà cửa gọn gàng",
            "Bạn nhận công việc phát tờ rơi ở ngã tư đường",
            "Bạn dắt chó của hàng xóm đi dạo quanh công viên",
            "Bạn đi rửa bát thuê cho quán phở đầu ngõ",
            "Bạn bắt xe buýt đi giao hàng siêu tốc cho khách",
            "Bạn đứng quầy thu ngân cho một quán kem và trà sữa",
            "Bạn nhặt được chiếc ví rơi rớt ngoài đường và được trả ơn",
            "Bạn bán mớ giấy vụn và ve chai trong kho",
            "Bạn trông trẻ thuê cho nhà hàng xóm đi vắng"
        ]
        
        task_done = random.choice(tasks)
        earned = random.randint(1000, 5000) # Lương dao động từ 1k đến 5k
        
        conn = sqlite3.connect('bot_database.db')
        conn.execute("UPDATE Economy SET balance = balance + ? WHERE user_id = ?", (earned, i.user.id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title=f"{SYS_EMOJIS.WORK} Work Completed!", color=0x42f5a4)
        embed.description = f"{task_done} và nhận được **{earned:,}** {SYS_EMOJIS.COIN}!"
        await i.response.send_message(embed=embed)

    @work.error
    async def work_error(self, i: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            minutes, seconds = divmod(int(error.retry_after), 60)
            await i.response.send_message(f"⏳ You need to rest! Try again in **{minutes}m {seconds}s**.", ephemeral=True)

    # ------------------------------------------
    # LỆNH XEM PROFILE (HIỂN THỊ BACKGROUND)
    # ------------------------------------------
    @app_commands.command(name="profile", description="Check your balance, rings, and relationship")
    async def profile(self, i: discord.Interaction, member: discord.Member = None):
        target = member or i.user
        self.check_user(target.id)

        conn = sqlite3.connect('bot_database.db')
        cursor = conn.execute("SELECT balance, ring_plastic, ring_silver, ring_gold, ring_diamond, ring_astrite, active_bg, partner_id, marriage_ring FROM Economy WHERE user_id = ?", (target.id,))
        data = cursor.fetchone()
        conn.close()

        balance, r_pla, r_sil, r_gol, r_dia, r_ast, active_bg, partner_id, m_ring = data
        
        partner_text = f"<@{partner_id}>" if partner_id else f"Single {SYS_EMOJIS.SINGLE}"
        if partner_id and m_ring:
            partner_text += f" (Married with {RING_SHOP[m_ring]['emoji']})"

        embed = discord.Embed(title=f"👤 {target.display_name}'s Profile", color=0x2b2d31)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Nếu có mua background, set hình ảnh vào embed
        if active_bg and active_bg in BG_SHOP:
            embed.set_image(url=BG_SHOP[active_bg]["url"])
            embed.set_footer(text=f"Equipped Background: {BG_SHOP[active_bg]['name']}")

        embed.add_field(name=f"{SYS_EMOJIS.WALLET} Wallet", value=f"**{balance:,}** {SYS_EMOJIS.COIN}", inline=False)
        
        inventory = f"{SYS_EMOJIS.RING_PLASTIC} Plastic: **{r_pla}** | {SYS_EMOJIS.RING_SILVER} Silver: **{r_sil}**\n" \
                    f"{SYS_EMOJIS.RING_GOLD} Gold: **{r_gol}** | {SYS_EMOJIS.RING_DIAMOND} Diamond: **{r_dia}**\n" \
                    f"{SYS_EMOJIS.RING_ASTRITE} Astrite: **{r_ast}**"
        
        embed.add_field(name=f"{SYS_EMOJIS.INVENTORY} Ring Inventory", value=inventory, inline=False)
        embed.add_field(name=f"{SYS_EMOJIS.MARRIED} Relationship", value=partner_text, inline=False)

        await i.response.send_message(embed=embed)

    # ------------------------------------------
    # HỆ THỐNG CỬA HÀNG VÀ MUA SẮM
    # ------------------------------------------
    @app_commands.command(name="shop", description="View the item and background shop")
    async def shop(self, i: discord.Interaction):
        embed = discord.Embed(title=f"{SYS_EMOJIS.SHOP} Server Shop", description="Use `/buy_ring` or `/buy_bg` to purchase.", color=0xffd700)
        
        # In danh sách nhẫn
        rings_text = ""
        for key, info in RING_SHOP.items():
            rings_text += f"{info['emoji']} **{info['name']}** (`{key}`): {info['price']:,} {SYS_EMOJIS.COIN}\n"
        embed.add_field(name="💍 Marriage Rings", value=rings_text, inline=False)

        # In danh sách Background
        bg_text = ""
        for key, info in BG_SHOP.items():
            bg_text += f"🖼️ **{info['name']}** (`{key}`): {info['price']:,} {SYS_EMOJIS.COIN}\n"
        embed.add_field(name="🌆 Profile Backgrounds", value=bg_text, inline=False)

        await i.response.send_message(embed=embed)

    @app_commands.command(name="buy_ring", description="Buy a ring from the shop")
    @app_commands.describe(ring_type="Select the ring tier")
    @app_commands.choices(ring_type=[app_commands.Choice(name=v["name"], value=k) for k, v in RING_SHOP.items()])
    async def buy_ring(self, i: discord.Interaction, ring_type: str):
        self.check_user(i.user.id)
        price = RING_SHOP[ring_type]["price"]

        conn = sqlite3.connect('bot_database.db')
        cursor = conn.execute("SELECT balance FROM Economy WHERE user_id = ?", (i.user.id,))
        balance = cursor.fetchone()[0]

        if balance < price:
            conn.close()
            return await i.response.send_message(f"❌ You need **{(price - balance):,} more** {SYS_EMOJIS.COIN}.", ephemeral=True)
        
        col = f"ring_{ring_type}"
        conn.execute(f"UPDATE Economy SET balance = balance - ?, {col} = {col} + 1 WHERE user_id = ?", (price, i.user.id))
        conn.commit()
        conn.close()
        
        await i.response.send_message(f"🛍️ You bought a {RING_SHOP[ring_type]['emoji']} **{RING_SHOP[ring_type]['name']}**!")

    @app_commands.command(name="buy_bg", description="Buy and equip a profile background")
    @app_commands.describe(bg_type="Select the background")
    @app_commands.choices(bg_type=[app_commands.Choice(name=v["name"], value=k) for k, v in BG_SHOP.items()])
    async def buy_bg(self, i: discord.Interaction, bg_type: str):
        self.check_user(i.user.id)
        price = BG_SHOP[bg_type]["price"]

        conn = sqlite3.connect('bot_database.db')
        cursor = conn.execute("SELECT balance FROM Economy WHERE user_id = ?", (i.user.id,))
        balance = cursor.fetchone()[0]

        if balance < price:
            conn.close()
            return await i.response.send_message(f"❌ You need **{(price - balance):,} more** {SYS_EMOJIS.COIN}.", ephemeral=True)
        
        conn.execute("UPDATE Economy SET balance = balance - ?, active_bg = ? WHERE user_id = ?", (price, bg_type, i.user.id))
        conn.commit()
        conn.close()
        
        await i.response.send_message(f"🖼️ You bought and equipped the **{BG_SHOP[bg_type]['name']}** background! Check `/profile`.")

    # ------------------------------------------
    # TÍNH NĂNG KẾT HÔN & LY HÔN
    # ------------------------------------------
    @app_commands.command(name="marry", description="Propose to another user!")
    @app_commands.choices(ring_type=[app_commands.Choice(name=v["name"], value=k) for k, v in RING_SHOP.items()])
    async def marry(self, i: discord.Interaction, member: discord.Member, ring_type: str):
        if member.id == i.user.id or member.bot:
            return await i.response.send_message("❌ Invalid target!", ephemeral=True)

        self.check_user(i.user.id)
        self.check_user(member.id)

        conn = sqlite3.connect('bot_database.db')
        col = f"ring_{ring_type}"
        
        cursor = conn.execute(f"SELECT {col}, partner_id FROM Economy WHERE user_id = ?", (i.user.id,))
        p_rings, p_partner = cursor.fetchone()
        
        cursor = conn.execute("SELECT partner_id FROM Economy WHERE user_id = ?", (member.id,))
        t_partner = cursor.fetchone()[0]
        conn.close()

        if p_partner or t_partner:
            return await i.response.send_message("❌ One of you is already married!", ephemeral=True)
        if p_rings <= 0:
            return await i.response.send_message(f"❌ You don't have a {RING_SHOP[ring_type]['emoji']} **{RING_SHOP[ring_type]['name']}**!", ephemeral=True)

        view = ProposalView(proposer=i.user, target=member, ring_type=ring_type)
        await i.response.send_message(f"💒 {member.mention}! {i.user.mention} is proposing to you with a {RING_SHOP[ring_type]['emoji']}! Do you accept?", view=view)

    @app_commands.command(name="divorce", description="Break up with your current partner")
    async def divorce(self, i: discord.Interaction):
        self.check_user(i.user.id)
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.execute("SELECT partner_id FROM Economy WHERE user_id = ?", (i.user.id,))
        partner_id = cursor.fetchone()[0]

        if not partner_id:
            conn.close()
            return await i.response.send_message("❌ You are not married to anyone!", ephemeral=True)

        # Hủy quan hệ của cả 2 người trong Database
        conn.execute("UPDATE Economy SET partner_id = NULL, marriage_ring = NULL WHERE user_id = ?", (i.user.id,))
        conn.execute("UPDATE Economy SET partner_id = NULL, marriage_ring = NULL WHERE user_id = ?", (partner_id,))
        conn.commit()
        conn.close()

        await i.response.send_message(f"💔 You have officially divorced <@{partner_id}>. You are now single.")

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))