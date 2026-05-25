import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
from datetime import datetime, timedelta

from .game_data import FACTIONS, MONSTERS, PLAYER_SKILLS, WEAPONS

# --- HELPER FUNCTION: DRAW BARS ---
def generate_bar(current, maximum, color_emoji, empty_emoji="⬛", length=10):
    """Tạo thanh HP/Mana trực quan bằng Emoji"""
    if maximum <= 0: return empty_emoji * length
    progress = int((current / maximum) * length)
    progress = max(0, min(length, progress)) # Đảm bảo không bị vọt giới hạn
    return (color_emoji * progress) + (empty_emoji * (length - progress))


# --- FACTION SELECTION VIEW ---
class FactionSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180) 

    async def register_player(self, interaction: discord.Interaction, faction_key: str):
        user_id = interaction.user.id
        faction_info = FACTIONS[faction_key]
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO WistoriaPlayers (user_id, faction) VALUES (?, ?)', (user_id, faction_key))
            conn.commit()
            
            embed = discord.Embed(
                title="🎓 Welcome to Rigarden Academy!",
                description=f"Congratulations **{interaction.user.name}**, you are officially enrolled.\n\n"
                            f"You have awakened the power of: **{faction_info['emoji']} {faction_info['name']}**\n"
                            f"*{faction_info.get('description', 'A powerful magic faction.')}*\n\n"
                            f"Newcomer Reward: **✨ 500 Credits**.",
                color=discord.Color.gold()
            )
            await interaction.response.edit_message(embed=embed, view=None)
        except sqlite3.IntegrityError:
            await interaction.response.send_message("❌ You are already enrolled!", ephemeral=True)
        finally:
            conn.close()

    # --- Hàng 0: 3 hệ cơ bản ---
    @discord.ui.button(label="Ice (El)", emoji="🧊", style=discord.ButtonStyle.primary, row=0)
    async def btn_ice(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Ice")

    @discord.ui.button(label="Fire (Ignis)", emoji="🔥", style=discord.ButtonStyle.danger, row=0)
    async def btn_fire(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Fire")

    @discord.ui.button(label="Physical (Sword)", emoji="⚔️", style=discord.ButtonStyle.secondary, row=0)
    async def btn_phys(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Physical")

    # --- Hàng 1: 3 hệ mở rộng ---
    @discord.ui.button(label="Wind (Ventus)", emoji="🌪️", style=discord.ButtonStyle.primary, row=1)
    async def btn_wind(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Wind")

    @discord.ui.button(label="Earth (Terra)", emoji="🪨", style=discord.ButtonStyle.success, row=1)
    async def btn_earth(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Earth")

    @discord.ui.button(label="Lightning (Fulgur)", emoji="⚡", style=discord.ButtonStyle.danger, row=1)
    async def btn_lightning(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Lightning")

# --- THE COMBAT ARENA (TURN-BASED SYSTEM) ---
class CombatView(discord.ui.View):
    def __init__(self, user, player_data, monster):
        super().__init__(timeout=300) # Trận chiến kết thúc nếu AFK 5 phút
        self.user = user
        self.monster = monster
        
        # Unpack Player Data from Database
        self.level, self.exp, self.credits, self.faction_key, self.floor = player_data
        
        # 1. Player Stats Calculation
        faction_data = FACTIONS[self.faction_key]
        self.max_hp = faction_data["base_hp"] + (self.level * faction_data["hp_growth"])
        self.current_hp = self.max_hp
        self.max_mana = faction_data["base_mana"] + (self.level * faction_data["mana_growth"])
        self.current_mana = self.max_mana
        
        # Tăng sát thương cơ bản của người chơi theo Level (Cộng dồn với vũ khí)
        equipped_weapon_dmg = WEAPONS["w_dull_blade"]["dmg"] if self.faction_key == "Physical" else WEAPONS["w_broken_branch"]["dmg"]
        self.base_dmg = equipped_weapon_dmg + (self.level * 3)
        
        # 2. Monster Dynamic Scaling theo số Tầng (Floor)
        floor_factor = max(0, self.floor - 1)
        
        # Tăng 8% HP và 4% Sát thương mỗi tầng so với gốc
        self.monster_max_hp = int(monster["hp"] * (1 + floor_factor * 0.08))
        self.monster_hp = self.monster_max_hp
        self.monster_dmg = int(monster["dmg"] * (1 + floor_factor * 0.04))
        
        self.combat_log = "The battle begins! Prepare yourself.\n"
        
        # Khởi tạo các nút bấm động
        self.setup_buttons()

    def build_embed(self):
        """Xây dựng giao diện trận đấu mới nhất"""
        embed = discord.Embed(
            title=f"⚔️ Dungeon - Floor {self.floor}",
            description=f"📜 **Combat Log:**\n> {self.combat_log}",
            color=discord.Color.dark_red()
        )
        
        # Thanh HP Quái vật
        hp_bar_m = generate_bar(self.monster_hp, self.monster_max_hp, "🟥")
        embed.add_field(
            name=f"{self.monster['emoji']} {self.monster['name']}", 
            value=f"HP: `{hp_bar_m}` {self.monster_hp}/{self.monster_max_hp}", 
            inline=False
        )
        
        # Thanh HP & Mana Người chơi
        hp_bar_p = generate_bar(self.current_hp, self.max_hp, "🟩")
        mana_bar_p = generate_bar(self.current_mana, self.max_mana, "🟦")
        
        faction_name = FACTIONS[self.faction_key]['name']
        embed.add_field(
            name=f"🎓 {self.user.display_name} (Lv.{self.level} {faction_name})",
            value=f"HP: `{hp_bar_p}` {self.current_hp}/{self.max_hp}\nMP: `{mana_bar_p}` {self.current_mana}/{self.max_mana}",
            inline=False
        )
        
        embed.set_thumbnail(url=self.monster["gif"])
        return embed

    def setup_buttons(self):
        """Tự động tạo các nút Kỹ năng dựa trên Cấp độ"""
        # Nút đánh thường (Hồi Mana)
        btn_attack = discord.ui.Button(label="Basic Attack", emoji="🗡️", style=discord.ButtonStyle.secondary, row=0)
        btn_attack.callback = self.attack_callback
        self.add_item(btn_attack)
        
        # Nút Kỹ năng (Lọc theo Faction và Level)
        available_skills = [sk for sk in PLAYER_SKILLS.get(self.faction_key, []) if self.level >= sk["unlock_level"]]
        
        for index, skill in enumerate(available_skills):
            btn_skill = discord.ui.Button(
                label=f"{skill['name']} ({skill['mana_cost']}MP)", 
                emoji=skill['emoji'], 
                style=discord.ButtonStyle.primary, 
                row=0 if index < 4 else 1 # Xuống hàng nếu quá nhiều nút
            )
            btn_skill.callback = self.create_skill_callback(skill)
            self.add_item(btn_skill)
            
        # Nút bỏ chạy
        btn_flee = discord.ui.Button(label="Flee", emoji="🏃", style=discord.ButtonStyle.danger, row=2)
        btn_flee.callback = self.flee_callback
        self.add_item(btn_flee)

    # --- CALLBACKS XỬ LÝ NÚT BẤM ---
    async def attack_callback(self, interaction: discord.Interaction):
        await self.process_turn(interaction, action="attack")

    def create_skill_callback(self, skill):
        """Hàm bọc (Closure) để truyền dữ liệu skill vào nút bấm"""
        async def callback(interaction: discord.Interaction):
            await self.process_turn(interaction, action="skill", skill=skill)
        return callback
        
    async def flee_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id: return
        self.combat_log = "💨 You fled the battle like a coward..."
        embed = self.build_embed()
        embed.color = discord.Color.light_grey()
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    # --- LOGIC VÒNG LẶP CHIẾN ĐẤU CHÍNH ---
    async def process_turn(self, interaction: discord.Interaction, action: str, skill=None):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("⚠️ This is not your battle!", ephemeral=True)

        self.combat_log = "" # Reset log cho lượt mới

        # 1. PLAYER TURN (Lượt người chơi)
        player_dmg = 0
        if action == "attack":
            player_dmg = self.base_dmg
            mana_regen = 15 if self.max_mana > 0 else 0
            self.current_mana = min(self.max_mana, self.current_mana + mana_regen)
            self.combat_log += f"🗡️ You used Basic Attack dealing **{player_dmg} DMG**! Recovered {mana_regen} MP.\n"
            
        elif action == "skill":
            if self.current_mana < skill["mana_cost"]:
                return await interaction.response.send_message("❌ Not enough Mana!", ephemeral=True)
            
            self.current_mana -= skill["mana_cost"]
            player_dmg = int(self.base_dmg * skill["dmg_multiplier"])
            self.combat_log += f"{skill['emoji']} You cast **{skill['name']}** dealing **{player_dmg} DMG**!\n"

        # Trừ máu quái
        self.monster_hp = max(0, self.monster_hp - player_dmg)

        # Kiểm tra Quái vật chết chưa
        if self.monster_hp <= 0:
            return await self.victory(interaction)

        # 2. MONSTER TURN (Lượt quái vật)
        m_base_dmg = self.monster_dmg # Đã sử dụng chỉ số scale
        skill_chance = self.monster.get("skill_chance", 0)
        
        if random.randint(1, 100) <= skill_chance:
            # Quái dùng Kỹ năng
            m_skill = self.monster.get("skill_name", "Special Attack")
            actual_m_dmg = int(m_base_dmg * self.monster.get("skill_dmg_mult", 1.5))
            self.combat_log += f"⚠️ **{self.monster['name']}** used **{m_skill}** dealing **{actual_m_dmg} DMG**!"
        else:
            # Quái đánh thường
            actual_m_dmg = m_base_dmg
            self.combat_log += f"👺 **{self.monster['name']}** attacked dealing **{actual_m_dmg} DMG**!"

        # Trừ máu người chơi
        self.current_hp = max(0, self.current_hp - actual_m_dmg)

        # Kiểm tra Người chơi chết chưa
        if self.current_hp <= 0:
            return await self.defeat(interaction)

        # 3. CẬP NHẬT MÀN HÌNH (Tiếp tục trận đấu)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    # --- ENDGAME MENTHODS ---
    async def victory(self, interaction):
        earned_exp = random.randint(30, 60)
        earned_credits = self.monster['credits'] + random.randint(10, 30)
        
        new_exp = self.exp + earned_exp
        new_level = self.level
        new_floor = self.floor
        exp_needed = self.level * 100
        
        level_up_msg = ""
        if new_exp >= exp_needed:
            new_level += 1
            new_exp -= exp_needed
            new_floor += 1
            level_up_msg = f"\n\n🎉 **LEVEL UP!** Reached Level {new_level}! Advanced to Floor {new_floor}!"

        # Save to DB
        c = sqlite3.connect('bot_database.db')
        cur = c.cursor()
        cur.execute('UPDATE WistoriaPlayers SET level=?, exp=?, credits=?, current_floor=? WHERE user_id=?', 
                    (new_level, new_exp, self.credits + earned_credits, new_floor, self.user.id))
        c.commit()
        c.close()

        win_embed = discord.Embed(
            title="🏆 VICTORY!",
            description=f"You successfully defeated the **{self.monster['name']}**!\n\n"
                        f"**📦 Loot:**\n✨ **+{earned_credits}** Credits\n📈 **+{earned_exp}** EXP" + level_up_msg,
            color=discord.Color.green()
        )
        win_embed.set_thumbnail(url=self.monster["gif"])
        await interaction.response.edit_message(embed=win_embed, view=None)
        self.stop()

    async def defeat(self, interaction):
        self.combat_log += "\n💀 **You were defeated and passed out...**"
        defeat_embed = self.build_embed()
        defeat_embed.color = discord.Color.dark_grey()
        await interaction.response.edit_message(embed=defeat_embed, view=None)
        self.stop()


# --- MAIN COG CLASS ---
class WistoriaRPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("-> Cog [Wistoria RPG] Loaded (Turn-based Combat Active)!")

    @app_commands.command(name="start_journey", description="Begin your journey at Rigarden Academy")
    async def start_journey(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM WistoriaPlayers WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        conn.close()
        
        if player:
            return await interaction.response.send_message("⚠️ You are already enrolled! Use `/profile`.", ephemeral=True)
        
        embed = discord.Embed(
            title="🔮 The Magic Awakening Sphere",
            description="Touch the sphere to determine your path of power.",
            color=discord.Color.dark_purple()
        )
        embed.set_image(url="https://images4.alphacoders.com/136/thumbbig-1368886.webp") 
        await interaction.response.send_message(embed=embed, view=FactionSelectView())

    @app_commands.command(name="profile", description="View your detailed Rigarden Student Profile & Stats")
    async def profile(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT level, exp, credits, faction, current_floor FROM WistoriaPlayers WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        conn.close()
        
        if not player:
            return await interaction.response.send_message("⚠️ You haven't enrolled yet! Use `/start_journey`.", ephemeral=True)
            
        level, exp, credits, faction_key, current_floor = player
        faction_info = FACTIONS.get(faction_key, {"name": "Unknown", "emoji": "❓"})
        
        # --- 1. TÍNH TOÁN THÔNG SỐ CHIẾN ĐẤU ---
        max_hp = faction_info["base_hp"] + (level * faction_info["hp_growth"])
        max_mana = faction_info["base_mana"] + (level * faction_info["mana_growth"])
        
        # Lấy vũ khí mặc định hiện tại (Sau này sẽ query từ Database Inventory)
        weapon_key = "w_dull_blade" if faction_key == "Physical" else "w_broken_branch"
        equipped_weapon = WEAPONS[weapon_key]
        total_dmg = equipped_weapon["dmg"] + (level * 3)
        
        # --- 2. LẤY DANH SÁCH KỸ NĂNG ---
        available_skills = [sk for sk in PLAYER_SKILLS.get(faction_key, []) if level >= sk["unlock_level"]]
        skills_text = ""
        if available_skills:
            for sk in available_skills:
                # Xử lý hiển thị Mana hoặc Cooldown
                cost_str = f"{sk['mana_cost']}MP" if sk.get("mana_cost", 0) > 0 else "0MP"
                cd_str = f" | {sk['cooldown']}T CD" if "cooldown" in sk else ""
                
                skills_text += f"{sk['emoji']} **{sk['name']}** ({cost_str}{cd_str})\n*↳ {sk['desc']}*\n\n"
        else:
            skills_text = "*No skills unlocked yet.*"
            
        # --- 3. XÂY DỰNG GIAO DIỆN EMBED ---
        exp_needed = level * 100 
        exp_bar = generate_bar(exp, exp_needed, "🟩")
        
        embed = discord.Embed(title=f"🎓 Student Profile | {interaction.user.display_name}", color=discord.Color.blue())
        if interaction.user.avatar: 
            embed.set_thumbnail(url=interaction.user.avatar.url)
            
        # Dòng 1: Thông tin cơ bản
        embed.add_field(name="Magic Faction", value=f"{faction_info['emoji']} **{faction_info['name']}**", inline=True)
        embed.add_field(name="Level", value=f"**Lv. {level}**", inline=True)
        embed.add_field(name="Credits", value=f"✨ **{credits:,}**", inline=True)
        
        # Dòng 2: Chỉ số sinh tồn & Sát thương
        embed.add_field(name="Combat Stats", value=f"💖 **HP:** {max_hp}\n💧 **Mana:** {max_mana}\n⚔️ **Total DMG:** {total_dmg}", inline=True)
        
        # Dòng 3: Vũ khí đang dùng
        embed.add_field(name="Equipped Weapon", value=f"{equipped_weapon['emoji']} **{equipped_weapon['name']}**\n*Tier {equipped_weapon['tier']} | DMG: {equipped_weapon['dmg']}*", inline=True)
        
        # Dòng 4: Tiến trình
        embed.add_field(name="Tower Progress", value=f"🏰 **Floor {current_floor}**", inline=True)
        
        # Thanh kinh nghiệm
        embed.add_field(name=f"Experience ({exp}/{exp_needed})", value=exp_bar, inline=False)
        
        # Danh sách kỹ năng
        embed.add_field(name="Unlocked Skills", value=skills_text, inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dungeon", description="Enter the dungeon to hunt monsters")
    async def dungeon(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT level, exp, credits, faction, current_floor, last_dungeon_time FROM WistoriaPlayers WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        
        if not player:
            conn.close()
            return await interaction.response.send_message("⚠️ Use `/start_journey` first.", ephemeral=True)
            
        level, exp, credits, faction, current_floor, str_last_time = player
        
        # Cooldown Check (1 minute)
        last_time = datetime.strptime(str_last_time, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        cooldown_time = timedelta(minutes=1) 
        
        if now - last_time < cooldown_time:
            remaining = int((cooldown_time - (now - last_time)).total_seconds())
            conn.close()
            return await interaction.response.send_message(f"⏳ Exhausted! Come back in **{remaining} seconds**.", ephemeral=True)
            
        cursor.execute("UPDATE WistoriaPlayers SET last_dungeon_time = ? WHERE user_id = ?", (now.strftime('%Y-%m-%d %H:%M:%S'), user_id))
        conn.commit()
        conn.close()
        
        # Determine Monster
        tier = "1-20" if current_floor <= 20 else "21-50" if current_floor <= 50 else "51-100"
        monster = random.choice(MONSTERS[tier])
        
        # Khởi tạo Giao diện Chiến đấu & Load Dữ liệu
        player_data = (level, exp, credits, faction, current_floor)
        combat_view = CombatView(interaction.user, player_data, monster)
        
        await interaction.response.send_message(embed=combat_view.build_embed(), view=combat_view)

async def setup(bot):
    await bot.add_cog(WistoriaRPG(bot))