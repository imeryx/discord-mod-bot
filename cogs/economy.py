import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import io
import requests
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pilmoji import Pilmoji

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
    
    # 5 Cấp độ nhẫn
    RING_PLASTIC = "<:plastic_ring:1521432439476715540>" 
    RING_SILVER = "<:silver_ring:1521432589422956766>"
    RING_GOLD = "<:gold_ring:1521432692774932543>"
    RING_DIAMOND = "<:diamond_ring:1521432786701914142>"
    RING_ASTRITE = "<:astrite_ring:1521432868729917510>"

RING_SHOP = {
    "plastic": {"price": 1000, "name": "Plastic Ring", "emoji": SYS_EMOJIS.RING_PLASTIC, "tier": 1},
    "silver": {"price": 5000, "name": "Silver Ring", "emoji": SYS_EMOJIS.RING_SILVER, "tier": 2},
    "gold": {"price": 20000, "name": "Gold Ring", "emoji": SYS_EMOJIS.RING_GOLD, "tier": 3},
    "diamond": {"price": 100000, "name": "Diamond Ring", "emoji": SYS_EMOJIS.RING_DIAMOND, "tier": 4},
    "astrite": {"price": 500000, "name": "Astrite Ring", "emoji": SYS_EMOJIS.RING_ASTRITE, "tier": 5}
}

BG_SHOP = {
    "Background 1": {"price": 15000, "name": "Background 1", "url": "https://i.pinimg.com/736x/d6/13/8a/d6138a6450396f542d668dc028c40ac9.jpg"},
    "Background 2": {"price": 15000, "name": "Background 2", "url": "https://i.pinimg.com/736x/2f/68/0f/2f680f41b4840b65f6d9f12dcf386f48.jpg"},
    "Background 3": {"price": 15000, "name": "Background 3", "url": "https://i.pinimg.com/736x/01/e1/e1/01e1e1bb80c522470f77cd863c302e4c.jpg"}
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
        now_str = datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect('bot_database.db')
        
        # Cập nhật kết hôn kèm Ngày tháng và Reset mốc kỷ niệm
        conn.execute("UPDATE Economy SET partner_id = ?, marriage_ring = ?, marriage_date = ?, anniversary_milestone = 0 WHERE user_id = ?", (self.target.id, self.ring_type, now_str, self.proposer.id))
        conn.execute("UPDATE Economy SET partner_id = ?, marriage_ring = ?, marriage_date = ?, anniversary_milestone = 0 WHERE user_id = ?", (self.proposer.id, self.ring_type, now_str, self.target.id))
        
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
        conn.execute('''CREATE TABLE IF NOT EXISTS Economy (
                        user_id INTEGER PRIMARY KEY,
                        balance INTEGER DEFAULT 0,
                        partner_id INTEGER DEFAULT NULL
                    )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS OwnedBackgrounds (
                        user_id INTEGER,
                        bg_key TEXT,
                        PRIMARY KEY(user_id, bg_key)
                    )''')
                    
        new_columns = [
            ("ring_plastic", "INTEGER DEFAULT 0"),
            ("ring_silver", "INTEGER DEFAULT 0"),
            ("ring_gold", "INTEGER DEFAULT 0"),
            ("ring_diamond", "INTEGER DEFAULT 0"),
            ("ring_astrite", "INTEGER DEFAULT 0"),
            ("active_bg", "TEXT DEFAULT NULL"),
            ("marriage_ring", "TEXT DEFAULT NULL"),
            ("marriage_date", "TEXT DEFAULT NULL"),      # Ngày cưới (YYYY-MM-DD)
            ("anniversary_milestone", "INTEGER DEFAULT 0") # Mốc thưởng cao nhất đã nhận (30, 100, 365...)
        ]
        
        for col_name, col_type in new_columns:
            try:
                conn.execute(f"ALTER TABLE Economy ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass
                
        conn.commit()
        conn.close()

    def check_user(self, user_id):
        conn = sqlite3.connect('bot_database.db')
        conn.execute("INSERT OR IGNORE INTO Economy (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()

    # ------------------------------------------
    # HÀM XỬ LÝ NHẬN THƯỞNG KỶ NIỆM TỰ ĐỘNG
    # ------------------------------------------
    def process_anniversaries(self, user_id):
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.execute("SELECT partner_id, marriage_date, anniversary_milestone FROM Economy WHERE user_id = ?", (user_id,))
        data = cursor.fetchone()
        
        if not data or not data[0] or not data[1]:
            conn.close()
            return []
            
        partner_id, m_date_str, milestone = data
        try:
            m_date = datetime.strptime(m_date_str, '%Y-%m-%d')
        except:
            conn.close()
            return []
            
        days_married = (datetime.now() - m_date).days
        rewards_msgs = []
        
        # Thiết lập các mốc quà tặng
        MILESTONES = {
            30: {"name": "1 Month", "reward": 50000},
            100: {"name": "100 Days", "reward": 150000},
            365: {"name": "1 Year", "reward": 500000}
        }
        
        new_milestone = milestone
        total_reward = 0
        
        for m_days, m_info in sorted(MILESTONES.items()):
            if days_married >= m_days and milestone < m_days:
                total_reward += m_info["reward"]
                new_milestone = m_days
                rewards_msgs.append(f"🎉 Happy **{m_info['name']}** Anniversary! You and <@{partner_id}> have been together for {days_married} days. You received a gift of **{m_info['reward']:,}** {SYS_EMOJIS.COIN}!")
        
        if total_reward > 0:
            conn.execute("UPDATE Economy SET balance = balance + ?, anniversary_milestone = ? WHERE user_id = ?", (total_reward, new_milestone, user_id))
            conn.commit()
            
        conn.close()
        return rewards_msgs

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Economy V4] loaded successfully with Anniversaries & Datetimes!")

    # ==========================================
    # HÀM VẼ PROFILE 
    # ==========================================
    async def create_profile_card(self, user, balance, partner_name, ring_emoji, marriage_date, bg_key):
        bg_url = BG_SHOP.get(bg_key, list(BG_SHOP.values())[0])["url"]
        try:
            response = requests.get(bg_url, timeout=5)
            base = Image.open(io.BytesIO(response.content)).convert("RGBA")
        except:
            base = Image.new("RGBA", (1000, 400), (43, 45, 49, 255)) 
            
        base = base.resize((1000, 400))

        overlay = Image.new("RGBA", (1000, 400), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rounded_rectangle((20, 20, 980, 380), radius=20, fill=(0, 0, 0, 160))
        base = Image.alpha_composite(base, overlay)

        avatar_size = 220
        try:
            avatar_url = user.display_avatar.url
            response_avatar = requests.get(avatar_url, timeout=5)
            avatar = Image.open(io.BytesIO(response_avatar.content)).convert("RGBA")
        except:
            avatar = Image.new("RGBA", (avatar_size, avatar_size), (100, 100, 100, 255))
            
        avatar = avatar.resize((avatar_size, avatar_size))
        
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
        avatar.putalpha(mask)
        
        ring_color = (255, 215, 0, 255) 
        ring_size = avatar_size + 10
        avatar_ring = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
        ring_draw = ImageDraw.Draw(avatar_ring)
        ring_draw.ellipse((0, 0, ring_size, ring_size), outline=ring_color, width=5)
        
        avatar_ring.paste(avatar, (5, 5), avatar)
        base.paste(avatar_ring, (45, 80), avatar_ring)

        try:
            font_title = ImageFont.truetype("Roboto-Bold.ttf", 60)
            font_stats = ImageFont.truetype("Roboto-Bold.ttf", 45)
            font_small = ImageFont.truetype("Roboto-Bold.ttf", 30)
            font_tiny = ImageFont.truetype("Roboto-Bold.ttf", 20) # Font cho ngày tháng
        except:
            font_title = font_stats = font_small = font_tiny = ImageFont.load_default()

        text_x = 320 
        
        with Pilmoji(base) as pilmoji:
            pilmoji.text((text_x, 70), f"{user.display_name}", font=font_title, fill=(255, 255, 255, 255))
            
            draw_line = ImageDraw.Draw(base)
            draw_line.line([(text_x, 160), (940, 160)], fill=(255, 255, 255, 100), width=3)

            # Cột 1: VÍ TIỀN
            pilmoji.text((text_x, 190), f"💳 WALLET", font=font_small, fill=(200, 200, 200, 255))
            pilmoji.text((text_x, 240), f"{balance:,} {SYS_EMOJIS.COIN}", font=font_stats, fill=(255, 215, 0, 255)) 
            
            # Cột 2: TÌNH TRẠNG KẾT HÔN
            status_color = (255, 105, 180, 255) if partner_name != "Single" else (170, 170, 170, 255)
            pilmoji.text((650, 190), f"❤️ RELATIONSHIP", font=font_small, fill=(200, 200, 200, 255))
            
            if partner_name != "Single":
                if ring_emoji:
                    pilmoji.text((650, 240), f"{partner_name} {ring_emoji}", font=font_stats, fill=status_color)
                else:
                    pilmoji.text((650, 240), f"{partner_name}", font=font_stats, fill=status_color)
                
                # Render ngày cưới
                if marriage_date:
                    try:
                        m_date_obj = datetime.strptime(marriage_date, '%Y-%m-%d')
                        days_passed = (datetime.now() - m_date_obj).days
                        date_display = f"Since {marriage_date} ({days_passed} days)"
                    except:
                        date_display = "Since: Unknown"
                else:
                    date_display = "Since: Unknown (Legacy)"
                    
                pilmoji.text((650, 295), date_display, font=font_tiny, fill=(200, 200, 200, 255))
            else:
                pilmoji.text((650, 240), f"{partner_name}", font=font_stats, fill=status_color)

        buffer = io.BytesIO()
        base.save(buffer, format="PNG")
        buffer.seek(0)
        return discord.File(buffer, filename=f"profile_{user.name}.png")


    # ==========================================
    # CÁC LỆNH CHÍNH (SLASH COMMANDS)
    
    @app_commands.command(name="transfer", description="Send coins to another user")
    @app_commands.describe(member="The user you want to send coins to", amount="The amount of coins to send")
    async def transfer(self, i: discord.Interaction, member: discord.Member, amount: int):
        # 1. Các lớp kiểm tra an toàn cơ bản
        if amount <= 0:
            return await i.response.send_message("❌ Amount must be greater than 0!", ephemeral=True)
            
        if member.id == i.user.id or member.bot:
            return await i.response.send_message("❌ You can't send coins to yourself or to a bot!", ephemeral=True)
            
        # 2. Đảm bảo cả 2 người đều có dữ liệu trong Database
        self.check_user(i.user.id)
        self.check_user(member.id)
        
        conn = sqlite3.connect('bot_database.db')
        
        # 3. Kiểm tra số dư của người gửi
        cursor = conn.execute("SELECT balance FROM Economy WHERE user_id = ?", (i.user.id,))
        sender_balance = cursor.fetchone()[0]
        
        if sender_balance < amount:
            conn.close()
            return await i.response.send_message(f"❌ You don't have enough coins! Your balance: **{sender_balance:,}** {SYS_EMOJIS.COIN}", ephemeral=True)
            
        # 4. Tiến hành trừ tiền người gửi và cộng tiền người nhận
        conn.execute("UPDATE Economy SET balance = balance - ? WHERE user_id = ?", (amount, i.user.id))
        conn.execute("UPDATE Economy SET balance = balance + ? WHERE user_id = ?", (amount, member.id))
        conn.commit()
        conn.close()
        
        # 5. Xuất thông báo thành công
        embed = discord.Embed(title="💸 Transfer Successful!", color=0x3498db)
        embed.description = f"{i.user.mention} has sent **{amount:,}** {SYS_EMOJIS.COIN} to {member.mention}!"
        await i.response.send_message(embed=embed)
    
    @app_commands.command(name="work", description="Do some tasks to earn coins!")
    @app_commands.checks.cooldown(1, 1800, key=lambda i: i.user.id)
    async def work(self, i: discord.Interaction):
        self.check_user(i.user.id)
        
        # Quét và tặng quà kỷ niệm nếu có
        anniversary_msgs = self.process_anniversaries(i.user.id)
        
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
        earned = random.randint(1000, 5000)
        
        conn = sqlite3.connect('bot_database.db')
        conn.execute("UPDATE Economy SET balance = balance + ? WHERE user_id = ?", (earned, i.user.id))
        conn.commit()
        conn.close()

        embed = discord.Embed(title=f"{SYS_EMOJIS.WORK} Work Completed!", color=0x42f5a4)
        embed.description = f"{task_done} và nhận được **{earned:,}** {SYS_EMOJIS.COIN}!"
        
        # Chèn thông báo kỷ niệm vào embed (nếu có)
        if anniversary_msgs:
            embed.add_field(name="🎁 Anniversary Rewards", value="\n".join(anniversary_msgs), inline=False)
            embed.color = discord.Color.gold()
            
        await i.response.send_message(embed=embed)

    @work.error
    async def work_error(self, i: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            minutes, seconds = divmod(int(error.retry_after), 60)
            await i.response.send_message(f"⏳ You need to rest! Try again in **{minutes}m {seconds}s**.", ephemeral=True)


    @app_commands.command(name="profile", description="View your professional profile card")
    async def profile(self, i: discord.Interaction, member: discord.Member = None):
        await i.response.defer() 
        
        target = member or i.user
        user_id = target.id
        self.check_user(user_id)
        
        # Quét và tặng quà kỷ niệm trước khi render ảnh
        anniversary_msgs = self.process_anniversaries(user_id)
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.execute("SELECT balance, active_bg, partner_id, marriage_ring, marriage_date FROM Economy WHERE user_id = ?", (user_id,))
        data = cursor.fetchone()
        
        if not data:
            conn.close()
            return await i.followup.send("❌ This user doesn't have a profile yet!")

        balance, active_bg, partner_id, m_ring, m_date = data
        
        partner_name = "Single"
        ring_emoji = ""
        
        if partner_id:
            try:
                partner_user = self.bot.get_user(partner_id) or await self.bot.fetch_user(partner_id)
                partner_name = partner_user.name
                if len(partner_name) > 10:
                    partner_name = partner_name[:8] + "..."
                    
                if m_ring and m_ring in RING_SHOP:
                    ring_emoji = RING_SHOP[m_ring]["emoji"]
            except:
                partner_name = "Unknown"
            
        conn.close()

        try:
            profile_file = await self.create_profile_card(target, balance, partner_name, ring_emoji, m_date, active_bg or "Background 1")
            
            # Gửi ảnh kèm theo thông báo nhận thưởng nếu có
            content = "\n".join(anniversary_msgs) if anniversary_msgs else None
            await i.followup.send(content=content, file=profile_file)
        except Exception as e:
            await i.followup.send(f"❌ Failed to generate profile card. Error: `{e}`")


    @app_commands.command(name="shop", description="View the item and background shop")
    async def shop(self, i: discord.Interaction):
        embed = discord.Embed(title=f"{SYS_EMOJIS.SHOP} Server Shop", description="Use `/buy_ring` or `/buy_bg` to purchase.", color=0xffd700)
        
        rings_text = ""
        for key, info in RING_SHOP.items():
            rings_text += f"{info['emoji']} **{info['name']}** (`{key}`): {info['price']:,} {SYS_EMOJIS.COIN}\n"
        embed.add_field(name="💍 Marriage Rings", value=rings_text, inline=False)

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
        conn.execute("INSERT OR IGNORE INTO OwnedBackgrounds (user_id, bg_key) VALUES (?, ?)", (i.user.id, bg_type))
        conn.commit()
        conn.close()
        
        await i.response.send_message(f"🖼️ You bought and equipped the **{BG_SHOP[bg_type]['name']}** background! Check `/profile`.")


    @app_commands.command(name="equip_bg", description="Equip a background you already own")
    async def equip_bg(self, i: discord.Interaction):
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.execute("SELECT bg_key FROM OwnedBackgrounds WHERE user_id = ?", (i.user.id,))
        owned = cursor.fetchall()
        
        if not owned:
            conn.close()
            return await i.response.send_message("❌ You don't own any background yet. Go to `/shop` to buy one!", ephemeral=True)

        options = [discord.SelectOption(label=BG_SHOP[row[0]]["name"], value=row[0]) for row in owned]
        
        class SelectBgView(discord.ui.View):
            @discord.ui.select(placeholder="Choose your background...", options=options)
            async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
                new_bg = select.values[0]
                conn = sqlite3.connect('bot_database.db')
                conn.execute("UPDATE Economy SET active_bg = ? WHERE user_id = ?", (new_bg, interaction.user.id))
                conn.commit()
                conn.close()
                await interaction.response.edit_message(content=f"✅ You have equipped **{BG_SHOP[new_bg]['name']}**!", view=None)

        await i.response.send_message("Pick your background:", view=SelectBgView(), ephemeral=True)
        conn.close()


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

        # Xóa toàn bộ dữ liệu kết hôn
        conn.execute("UPDATE Economy SET partner_id = NULL, marriage_ring = NULL, marriage_date = NULL, anniversary_milestone = 0 WHERE user_id = ?", (i.user.id,))
        conn.execute("UPDATE Economy SET partner_id = NULL, marriage_ring = NULL, marriage_date = NULL, anniversary_milestone = 0 WHERE user_id = ?", (partner_id,))
        conn.commit()
        conn.close()

        await i.response.send_message(f"💔 You have officially divorced <@{partner_id}>. You are now single.")


    @app_commands.command(name="dev_give", description="[ADMIN ONLY] Give Money or Rings for testing")
    @app_commands.describe(
        give_type="Choose what to give",
        amount="Amount (For coins or quantity of rings)"
    )
    @app_commands.choices(give_type=[
        app_commands.Choice(name="Credits (Coins)", value="balance"),
        app_commands.Choice(name="Plastic Ring", value="ring_plastic"),
        app_commands.Choice(name="Silver Ring", value="ring_silver"),
        app_commands.Choice(name="Gold Ring", value="ring_gold"),
        app_commands.Choice(name="Diamond Ring", value="ring_diamond"),
        app_commands.Choice(name="Astrite Ring", value="ring_astrite")
    ])
    async def dev_give(self, i: discord.Interaction, give_type: str, amount: int):
        MY_DISCORD_ID = 834054385746575380 
        
        if i.user.id != MY_DISCORD_ID:
            return await i.response.send_message("⛔ Access Denied: Admin only!", ephemeral=True)

        self.check_user(i.user.id)
        conn = sqlite3.connect('bot_database.db')
        
        conn.execute(f"UPDATE Economy SET {give_type} = {give_type} + ? WHERE user_id = ?", (amount, i.user.id))
        if give_type == "balance":
            msg = f"✅ Added {amount} {SYS_EMOJIS.COIN} to your wallet."
        else:
            msg = f"✅ Added {amount} items of type `{give_type}` to your inventory."
            
        conn.commit()
        conn.close()
        await i.response.send_message(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))