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
        
    # HÀM VẼ PROFILE (DÙNG PILLOW)
    # ==========================================
    async def create_profile_card(self, user, balance, partner_name, bg_key):
        # 1. Lấy hình nền
        bg_url = self.BG_SHOP.get(bg_key, self.BG_SHOP["minimal"])["url"]
        response = requests.get(bg_url)
        base = Image.open(io.BytesIO(response.content)).convert("RGBA")
        base = base.resize((900, 500)) # Kích thước chuẩn cho thẻ profile

        # 2. Tạo lớp phủ mờ (Dark Overlay) để chữ dễ đọc hơn
        overlay = Image.new("RGBA", (900, 500), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # Vẽ một hình chữ nhật đen mờ ở giữa
        draw.rounded_rectangle((50, 50, 850, 450), radius=30, fill=(0, 0, 0, 160))
        base = Image.alpha_composite(base, overlay)

        # 3. Vẽ Avatar
        avatar_url = user.display_avatar.url
        response_avatar = requests.get(avatar_url)
        avatar = Image.open(io.BytesIO(response_avatar.content)).convert("RGBA")
        avatar = avatar.resize((150, 150))
        
        # Làm avatar hình tròn
        mask = Image.new("L", (150, 150), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 150, 150), fill=255)
        avatar = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
        avatar.putalpha(mask)
        
        base.paste(avatar, (100, 100), avatar)

        # 4. Viết chữ (Sử dụng font mặc định nếu không có file font)
        draw_text = ImageDraw.Draw(base)
        
        # Chỉnh font (Bạn có thể tải file .ttf lên VPS để có font đẹp hơn)
        try:
            font_name = ImageFont.truetype("arial.ttf", 50)
            font_info = ImageFont.truetype("arial.ttf", 35)
        except:
            font_name = ImageFont.load_default()
            font_info = ImageFont.load_default()

        # Vẽ tên User
        draw_text.text((280, 120), f"{user.display_name}", font=font_name, fill="white")
        
        # Vẽ ví tiền
        draw_text.text((280, 220), f"💰 Wallet: {balance:,} Coins", font=font_info, fill="#FFD700")
        
        # Vẽ trạng thái kết hôn
        status_color = "#FF69B4" if partner_name != "Single" else "#AAAAAA"
        draw_text.text((280, 300), f"❤️ Status: {partner_name}", font=font_info, fill=status_color)

        # 5. Xuất ảnh
        buffer = io.BytesIO()
        base.save(buffer, format="PNG")
        buffer.seek(0)
        return discord.File(buffer, filename="profile.png")
        # 1. Vẫn giữ lệnh tạo bảng gốc để đề phòng trường hợp file chưa từng tồn tại
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
    # LỆNH PROFILE NÂNG CẤP
    # ==========================================
    @app_commands.command(name="profile", description="View your professional profile card")
    async def profile(self, i: discord.Interaction, member: discord.Member = None):
        await i.response.defer() # Cần defer vì xử lý ảnh mất thời gian
        
        target = member or i.user
        user_id = target.id
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.execute("SELECT balance, active_bg, partner_id FROM Economy WHERE user_id = ?", (user_id,))
        data = cursor.fetchone()
        
        if not data:
            conn.close()
            return await i.followup.send("❌ This user doesn't have a profile yet!")

        balance, active_bg, partner_id = data
        
        # Lấy tên người bạn đời
        partner_name = "Single"
        if partner_id:
            partner_user = self.bot.get_user(partner_id) or await self.bot.fetch_user(partner_id)
            partner_name = f"Married to {partner_user.name}"
            
        conn.close()

        # Tạo file ảnh
        profile_file = await self.create_profile_card(target, balance, partner_name, active_bg or "minimal")
        
        await i.followup.send(file=profile_file)

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
        conn.execute("INSERT OR IGNORE INTO OwnedBackgrounds (user_id, bg_key) VALUES (?, ?)", (i.user.id, bg_type))
        conn.commit()
        conn.close()
        
        await i.response.send_message(f"🖼️ You bought and equipped the **{BG_SHOP[bg_type]['name']}** background! Check `/profile`.")

    # 2. TẠO LỆNH MỚI: /equip_bg (Để thay đổi background cũ)
    @app_commands.command(name="equip_bg", description="Equip a background you already own")
    async def equip_bg(self, i: discord.Interaction):
        # Lấy danh sách những cái đã mua
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.execute("SELECT bg_key FROM OwnedBackgrounds WHERE user_id = ?", (i.user.id,))
        owned = cursor.fetchall()
        
        if not owned:
            conn.close()
            return await i.response.send_message("❌ You don't own any background yet. Go to `/shop` to buy one!", ephemeral=True)

        # Tạo View để chọn background đã sở hữu
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
    @app_commands.command(name="dev_give", description="[ADMIN ONLY] Give Money or Rings for testing")
    @app_commands.describe(
        give_type="Choose what to give",
        amount="Amount (For coins or quantity of rings)"
    )
    @app_commands.choices(give_type=[
        app_commands.Choice(name="Credits (Coins)", value="credits"),
        app_commands.Choice(name="Plastic Ring", value="ring_plastic"),
        app_commands.Choice(name="Silver Ring", value="ring_silver"),
        app_commands.Choice(name="Gold Ring", value="ring_gold"),
        app_commands.Choice(name="Diamond Ring", value="ring_diamond"),
        app_commands.Choice(name="Astrite Ring", value="ring_astrite")
    ])
    async def dev_give(self, i: discord.Interaction, give_type: str, amount: int):
        # THAY ID CỦA BẠN VÀO ĐÂY
        MY_DISCORD_ID = 834054385746575380 
        
        if i.user.id != MY_DISCORD_ID:
            return await i.response.send_message("⛔ Access Denied: Admin only!", ephemeral=True)

        self.check_user(i.user.id)
        conn = sqlite3.connect('bot_database.db')
        
        if give_type == "credits":
            conn.execute("UPDATE Economy SET balance = balance + ? WHERE user_id = ?", (amount, i.user.id))
            msg = f"✅ Added {amount} {SYS_EMOJIS.COIN} to your wallet."
        else:
            conn.execute(f"UPDATE Economy SET {give_type} = {give_type} + ? WHERE user_id = ?", (amount, i.user.id))
            msg = f"✅ Added {amount} items of type `{give_type}` to your inventory."
            
        conn.commit()
        conn.close()
        await i.response.send_message(msg, ephemeral=True)
async def setup(bot):
    await bot.add_cog(EconomyCog(bot))

    