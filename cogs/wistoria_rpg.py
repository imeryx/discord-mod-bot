import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
from datetime import datetime, timedelta

from .game_data import FACTIONS, MONSTERS, PLAYER_SKILLS, WEAPONS, MATERIALS

# --- CẤU HÌNH HỆ THỐNG LÒ RÈN ---
SELL_PRICES = {"D": 25, "C": 100, "B": 300, "A": 800, "S": 2000, "SS": 5000}

# Sát thương cộng thêm trên mỗi cấp độ vũ khí dựa theo Tier
LVL_BONUS = {"D": 2, "C": 5, "B": 10, "A": 22, "S": 50, "SS": 110}

# Chi phí Credits gốc để nâng cấp (Giá tăng dần: Chi phí = Giá gốc * Cấp hiện tại)
UPGRADE_BASE_COSTS = {"D": 200, "C": 500, "B": 1200, "A": 3000, "S": 7000, "SS": 15000}


# --- HELPER FUNCTION: DRAW BARS ---
def generate_bar(current, maximum, color_emoji, empty_emoji="⬛", length=10):
    if maximum <= 0: return empty_emoji * length
    progress = int((current / maximum) * length)
    progress = max(0, min(length, progress)) 
    return (color_emoji * progress) + (empty_emoji * (length - progress))


# --- FACTION SELECTION VIEW ---
class FactionSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180) 

    async def register_player(self, interaction: discord.Interaction, faction_key: str):
        user_id = interaction.user.id
        faction_info = FACTIONS[faction_key]
        starter_weapon = "w_dull_blade" if faction_key == "Physical" else "w_broken_branch"
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO WistoriaPlayers (user_id, faction, equipped_weapon) VALUES (?, ?, ?)', (user_id, faction_key, starter_weapon))
            cursor.execute('INSERT INTO PlayerInventory (user_id, weapon_key, quantity, weapon_level) VALUES (?, ?, 1, 1)', (user_id, starter_weapon))
            conn.commit()
            
            embed = discord.Embed(
                title="🎓 Welcome to Rigarden Academy!",
                description=f"Congratulations **{interaction.user.name}**, you are officially enrolled.\n\n"
                            f"You have awakened the power of: **{faction_info['emoji']} {faction_info['name']}**\n"
                            f"*{faction_info.get('description', 'A powerful magic faction.')}*\n\n"
                            f"Newcomer Reward: **✨ 500 Credits** and a Starter Weapon.",
                color=discord.Color.gold()
            )
            await interaction.response.edit_message(embed=embed, view=None)
        except sqlite3.IntegrityError:
            await interaction.response.send_message("❌ You are already enrolled!", ephemeral=True)
        finally:
            conn.close()

    @discord.ui.button(label="Ice (El)", emoji="🧊", style=discord.ButtonStyle.primary, row=0)
    async def btn_ice(self, interaction: discord.Interaction, button: discord.ui.Button): await self.register_player(interaction, "Ice")
    @discord.ui.button(label="Fire (Ignis)", emoji="🔥", style=discord.ButtonStyle.danger, row=0)
    async def btn_fire(self, interaction: discord.Interaction, button: discord.ui.Button): await self.register_player(interaction, "Fire")
    @discord.ui.button(label="Physical (Sword)", emoji="⚔️", style=discord.ButtonStyle.secondary, row=0)
    async def btn_phys(self, interaction: discord.Interaction, button: discord.ui.Button): await self.register_player(interaction, "Physical")
    @discord.ui.button(label="Wind (Ventus)", emoji="🌪️", style=discord.ButtonStyle.primary, row=1)
    async def btn_wind(self, interaction: discord.Interaction, button: discord.ui.Button): await self.register_player(interaction, "Wind")
    @discord.ui.button(label="Earth (Terra)", emoji="🪨", style=discord.ButtonStyle.success, row=1)
    async def btn_earth(self, interaction: discord.Interaction, button: discord.ui.Button): await self.register_player(interaction, "Earth")
    @discord.ui.button(label="Lightning (Fulgur)", emoji="⚡", style=discord.ButtonStyle.danger, row=1)
    async def btn_lightning(self, interaction: discord.Interaction, button: discord.ui.Button): await self.register_player(interaction, "Lightning")


# --- THE COMBAT ARENA ---
class CombatView(discord.ui.View):
    def __init__(self, user, player_data, monster):
        super().__init__(timeout=300)
        self.user = user
        self.monster = monster
        
        # Nhận thêm dữ liệu weapon_level từ lệnh gọi dungeon
        self.level, self.exp, self.credits, self.faction_key, self.max_floor, self.weapon_key, self.fighting_floor, self.weapon_level = player_data
        
        faction_data = FACTIONS[self.faction_key]
        self.max_hp = faction_data["base_hp"] + (self.level * faction_data["hp_growth"])
        self.current_hp = self.max_hp
        self.max_mana = faction_data["base_mana"] + (self.level * faction_data["mana_growth"])
        self.current_mana = self.max_mana
        
        # Tính toán sát thương dựa trên chỉ số Cường hóa vũ khí
        self.equipped_weapon = WEAPONS.get(self.weapon_key, WEAPONS["w_broken_branch"])
        w_tier = self.equipped_weapon["tier"]
        lvl_bonus_dmg = (self.weapon_level - 1) * LVL_BONUS.get(w_tier, 0)
        
        self.base_dmg = self.equipped_weapon["dmg"] + lvl_bonus_dmg + (self.level * 3)
        
        floor_factor = max(0, self.fighting_floor - 1)
        self.monster_max_hp = int(monster["hp"] * (1 + floor_factor * 0.08))
        self.monster_hp = self.monster_max_hp
        self.monster_dmg = int(monster["dmg"] * (1 + floor_factor * 0.04))
        
        weapon_display = f"{self.equipped_weapon['name']} (+{self.weapon_level})" if self.weapon_level > 1 else self.equipped_weapon['name']
        self.combat_log = f"Trang bị: **{weapon_display}**! The battle begins.\n"
        self.skill_cooldowns = {}
        self.update_buttons()

    def build_embed(self):
        embed = discord.Embed(title=f"⚔️ Dungeon - Floor {self.fighting_floor}", description=f"📜 **Combat Log:**\n> {self.combat_log}", color=discord.Color.dark_red())
        hp_bar_m = generate_bar(self.monster_hp, self.monster_max_hp, "🟥")
        embed.add_field(name=f"{self.monster['emoji']} {self.monster['name']}", value=f"HP: `{hp_bar_m}` {self.monster_hp}/{self.monster_max_hp}", inline=False)
        hp_bar_p = generate_bar(self.current_hp, self.max_hp, "🟩")
        mana_bar_p = generate_bar(self.current_mana, self.max_mana, "🟦")
        faction_name = FACTIONS[self.faction_key]['name']
        embed.add_field(name=f"🎓 {self.user.display_name} (Lv.{self.level} {faction_name})", value=f"HP: `{hp_bar_p}` {self.current_hp}/{self.max_hp}\nMP: `{mana_bar_p}` {self.current_mana}/{self.max_mana}", inline=False)
        embed.set_thumbnail(url=self.monster["gif"])
        return embed

    def update_buttons(self):
        self.clear_items()
        btn_attack = discord.ui.Button(label="Basic Attack", emoji="🗡️", style=discord.ButtonStyle.secondary, row=0)
        btn_attack.callback = self.attack_callback
        self.add_item(btn_attack)
        
        available_skills = [sk for sk in PLAYER_SKILLS.get(self.faction_key, []) if self.level >= sk["unlock_level"]]
        for index, skill in enumerate(available_skills):
            cd_remaining = self.skill_cooldowns.get(skill["id"], 0)
            label = skill["name"]
            disabled = False
            style = discord.ButtonStyle.primary
            
            if skill["mana_cost"] > 0:
                label += f" ({skill['mana_cost']}MP)"
                if self.current_mana < skill["mana_cost"]: disabled, style = True, discord.ButtonStyle.secondary
            if cd_remaining > 0:
                label += f" (CD: {cd_remaining}T)"
                disabled, style = True, discord.ButtonStyle.secondary
                
            btn_skill = discord.ui.Button(label=label, emoji=skill['emoji'], style=style, disabled=disabled, row=0 if index < 3 else 1)
            btn_skill.callback = self.create_skill_callback(skill)
            self.add_item(btn_skill)
            
        btn_flee = discord.ui.Button(label="Flee", emoji="🏃", style=discord.ButtonStyle.danger, row=2)
        btn_flee.callback = self.flee_callback
        self.add_item(btn_flee)

    async def attack_callback(self, interaction: discord.Interaction): await self.process_turn(interaction, action="attack")
    def create_skill_callback(self, skill):
        async def callback(interaction: discord.Interaction): await self.process_turn(interaction, action="skill", skill=skill)
        return callback
        
    async def flee_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id: return
        self.combat_log = "💨 You fled the battle like a coward..."
        embed = self.build_embed()
        embed.color = discord.Color.light_grey()
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    async def process_turn(self, interaction: discord.Interaction, action: str, skill=None):
        if interaction.user.id != self.user.id: return await interaction.response.send_message("⚠️ This is not your battle!", ephemeral=True)
        self.combat_log = "" 
        player_dmg = 0
        
        if action == "attack":
            player_dmg = self.base_dmg
            mana_regen = 15 if self.max_mana > 0 else 0
            self.current_mana = min(self.max_mana, self.current_mana + mana_regen)
            self.combat_log += f"🗡️ You used Basic Attack dealing **{player_dmg} DMG**! Recovered {mana_regen} MP.\n"
        elif action == "skill":
            if skill["mana_cost"] > 0 and self.current_mana < skill["mana_cost"]: return await interaction.response.send_message("❌ Not enough Mana!", ephemeral=True)
            if self.skill_cooldowns.get(skill["id"], 0) > 0: return await interaction.response.send_message("❌ Skill is on cooldown!", ephemeral=True)
            if skill["mana_cost"] > 0: self.current_mana -= skill["mana_cost"]
            if "cooldown" in skill: self.skill_cooldowns[skill["id"]] = skill["cooldown"] + 1
            player_dmg = int(self.base_dmg * skill["dmg_multiplier"])
            self.combat_log += f"{skill['emoji']} You cast **{skill['name']}** dealing **{player_dmg} DMG**!\n"

        self.monster_hp = max(0, self.monster_hp - player_dmg)
        if self.monster_hp <= 0: return await self.victory(interaction)

        m_base_dmg = self.monster_dmg 
        if random.randint(1, 100) <= self.monster.get("skill_chance", 0):
            actual_m_dmg = int(m_base_dmg * self.monster.get("skill_dmg_mult", 1.5))
            self.combat_log += f"⚠️ **{self.monster['name']}** used **{self.monster.get('skill_name')}** dealing **{actual_m_dmg} DMG**!"
        else:
            actual_m_dmg = m_base_dmg
            self.combat_log += f"👺 **{self.monster['name']}** attacked dealing **{actual_m_dmg} DMG**!"

        self.current_hp = max(0, self.current_hp - actual_m_dmg)
        if self.current_hp <= 0: return await self.defeat(interaction)

        for sk_id in list(self.skill_cooldowns.keys()):
            if self.skill_cooldowns[sk_id] > 0: self.skill_cooldowns[sk_id] -= 1

        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def victory(self, interaction):
        earned_exp = random.randint(30, 60)
        earned_credits = self.monster['credits'] + random.randint(10, 30)
        new_exp, new_level, new_max_floor = self.exp + earned_exp, self.level, self.max_floor
        exp_needed = self.level * 100
        level_up_msg = ""
        
        if new_exp >= exp_needed:
            new_level += 1
            new_exp -= exp_needed
            new_max_floor += 1
            level_up_msg = f"\n\n🎉 **LEVEL UP!** Reached Level {new_level}! Advanced Max Floor to {new_max_floor}!"

        # Xử lý Logic rớt đồ (Drop System)
        drops_received = {}
        for drop in self.monster.get("drops", []):
            if random.randint(1, 100) <= drop["chance"]:
                mat_key = drop["item"]
                drops_received[mat_key] = drops_received.get(mat_key, 0) + 1

        c = sqlite3.connect('bot_database.db')
        
        # 1. Cập nhật EXP và Tiền
        c.execute('UPDATE WistoriaPlayers SET level=?, exp=?, credits=?, current_floor=? WHERE user_id=?', (new_level, new_exp, self.credits + earned_credits, new_max_floor, self.user.id))
        
        # 2. Cập nhật Vật liệu vào Database
        drop_text = ""
        if drops_received:
            drop_text = "\n\n**💎 Materials Found:**"
            for mat_key, qty in drops_received.items():
                mat_info = MATERIALS.get(mat_key)
                if mat_info:
                    drop_text += f"\n{mat_info['emoji']} **{mat_info['name']}** x{qty}"
                    
                c.execute("""
                    INSERT INTO PlayerMaterials (user_id, material_key, quantity) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(user_id, material_key) 
                    DO UPDATE SET quantity = quantity + ?
                """, (self.user.id, mat_key, qty, qty))
                
        c.commit()
        c.close()

        win_embed = discord.Embed(
            title="🏆 VICTORY!", 
            description=f"You successfully defeated the **{self.monster['name']}**!\n\n**📦 Loot:**\n✨ **+{earned_credits}** Credits\n📈 **+{earned_exp}** EXP" + drop_text + level_up_msg, 
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
    async def on_ready(self): print("-> Cog [Wistoria RPG] Loaded (Forge & Weapon Inspection Enabled)!")

    @app_commands.command(name="start_journey", description="Begin your journey at Rigarden Academy")
    async def start_journey(self, interaction: discord.Interaction):
        conn = sqlite3.connect('bot_database.db')
        player = conn.cursor().execute("SELECT * FROM WistoriaPlayers WHERE user_id = ?", (interaction.user.id,)).fetchone()
        conn.close()
        if player: return await interaction.response.send_message("⚠️ You are already enrolled! Use `/profile`.", ephemeral=True)
        
        embed = discord.Embed(title="🔮 The Magic Awakening Sphere", description="Touch the sphere to determine your path of power.", color=discord.Color.dark_purple())
        embed.set_image(url="https://images4.alphacoders.com/136/thumbbig-1368886.webp") 
        await interaction.response.send_message(embed=embed, view=FactionSelectView())

    @app_commands.command(name="profile", description="View your detailed Rigarden Student Profile & Stats")
    async def profile(self, interaction: discord.Interaction):
        conn = sqlite3.connect('bot_database.db')
        # Join bảng để lấy cấp độ của vũ khí đang trang bị
        player = conn.cursor().execute("""
            SELECT p.level, p.exp, p.credits, p.faction, p.current_floor, p.equipped_weapon, i.weapon_level 
            FROM WistoriaPlayers p
            LEFT JOIN PlayerInventory i ON p.user_id = i.user_id AND p.equipped_weapon = i.weapon_key
            WHERE p.user_id = ?
        """, (interaction.user.id,)).fetchone()
        conn.close()
        
        if not player: return await interaction.response.send_message("⚠️ You haven't enrolled yet!", ephemeral=True)
        level, exp, credits, faction_key, current_floor, weapon_key, weapon_level = player
        
        if not weapon_key: weapon_key = "w_dull_blade" if faction_key == "Physical" else "w_broken_branch"
        weapon_level = weapon_level if weapon_level is not None else 1
        
        faction_info = FACTIONS.get(faction_key, {"name": "Unknown", "emoji": "❓"})
        max_hp = faction_info["base_hp"] + (level * faction_info["hp_growth"])
        max_mana = faction_info["base_mana"] + (level * faction_info["mana_growth"])
        
        equipped_weapon = WEAPONS.get(weapon_key, WEAPONS["w_broken_branch"])
        lvl_bonus_dmg = (weapon_level - 1) * LVL_BONUS.get(equipped_weapon["tier"], 0)
        total_dmg = equipped_weapon["dmg"] + lvl_bonus_dmg + (level * 3)
        
        skills_text = "".join([f"{sk['emoji']} **{sk['name']}** ({sk.get('mana_cost', 0)}MP{' | '+str(sk['cooldown'])+'T CD' if 'cooldown' in sk else ''})\n*↳ {sk['desc']}*\n\n" for sk in PLAYER_SKILLS.get(faction_key, []) if level >= sk["unlock_level"]])
        exp_needed = level * 100 
        
        embed = discord.Embed(title=f"🎓 Student Profile | {interaction.user.display_name}", color=discord.Color.blue())
        if interaction.user.avatar: embed.set_thumbnail(url=interaction.user.avatar.url)
        embed.add_field(name="Magic Faction", value=f"{faction_info['emoji']} **{faction_info['name']}**", inline=True)
        embed.add_field(name="Level", value=f"**Lv. {level}**", inline=True)
        embed.add_field(name="Credits", value=f"✨ **{credits:,}**", inline=True)
        embed.add_field(name="Combat Stats", value=f"💖 **HP:** {max_hp}\n💧 **MP:** {max_mana}\n⚔️ **Total DMG:** {total_dmg}", inline=True)
        
        weapon_name_display = f"{equipped_weapon['name']} (+{weapon_level})" if weapon_level > 1 else equipped_weapon['name']
        embed.add_field(name="Equipped Weapon", value=f"{equipped_weapon['emoji']} **{weapon_name_display}**\n*Tier {equipped_weapon['tier']} | Base DMG: {equipped_weapon['dmg']}*", inline=True)
        embed.add_field(name="Max Tower Progress", value=f"🏰 **Floor {current_floor}**", inline=True)
        embed.add_field(name=f"Experience ({exp}/{exp_needed})", value=generate_bar(exp, exp_needed, "🟩"), inline=False)
        embed.add_field(name="Unlocked Skills", value=skills_text or "*No skills yet.*", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="materials", description="Open your bag of crafting materials")
    async def materials(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT material_key, quantity FROM PlayerMaterials WHERE user_id = ? AND quantity > 0", (user_id,))
        items = cursor.fetchall()
        conn.close()
        
        if not items:
            return await interaction.response.send_message("🕸️ Your material bag is completely empty. Go to the `/dungeon` to hunt monsters!", ephemeral=True)
            
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Material Bag", color=discord.Color.teal())
        
        desc = ""
        for mat_key, qty in items:
            m_data = MATERIALS.get(mat_key)
            if not m_data: continue
            
            desc += f"{m_data['emoji']} **{m_data['name']}** (x{qty})\n*Tier: {m_data['tier']} | ID: `{mat_key}`*\n\n"
            
        embed.description = desc
        embed.set_footer(text="Materials are used to /enhance your weapons!")
        await interaction.response.send_message(embed=embed)
    @app_commands.command(name="dungeon", description="Enter the dungeon to hunt monsters. Optionally select a floor to farm.")
    @app_commands.describe(target_floor="The floor you want to farm (must be <= your Max Floor)")
    async def dungeon(self, interaction: discord.Interaction, target_floor: int = None):
        user_id = interaction.user.id
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        # Nhập thêm cấp độ vũ khí phục vụ tính sát thương thật trong trận đấu
        player = cursor.execute("""
            SELECT p.level, p.exp, p.credits, p.faction, p.current_floor, p.last_dungeon_time, p.equipped_weapon, i.weapon_level 
            FROM WistoriaPlayers p
            LEFT JOIN PlayerInventory i ON p.user_id = i.user_id AND p.equipped_weapon = i.weapon_key
            WHERE p.user_id = ?
        """, (user_id,)).fetchone()
        
        if not player:
            conn.close()
            return await interaction.response.send_message("⚠️ Use `/start_journey` first.", ephemeral=True)
            
        level, exp, credits, faction, max_floor, str_last_time, weapon_key, weapon_level = player
        if not weapon_key: weapon_key = "w_dull_blade" if faction == "Physical" else "w_broken_branch"
        weapon_level = weapon_level if weapon_level is not None else 1
        
        fighting_floor = max_floor
        if target_floor is not None:
            if target_floor < 1 or target_floor > max_floor:
                conn.close()
                return await interaction.response.send_message(f"❌ Invalid floor! You can only choose a floor between 1 and **{max_floor}**.", ephemeral=True)
            fighting_floor = target_floor
            
        last_time = datetime.strptime(str_last_time, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        if now - last_time < timedelta(minutes=1):
            remaining = int((timedelta(minutes=1) - (now - last_time)).total_seconds())
            conn.close()
            return await interaction.response.send_message(f"⏳ Exhausted! Come back in **{remaining} seconds**.", ephemeral=True)
            
        cursor.execute("UPDATE WistoriaPlayers SET last_dungeon_time = ? WHERE user_id = ?", (now.strftime('%Y-%m-%d %H:%M:%S'), user_id))
        conn.commit()
        conn.close()
        
        tier = "1-20" if fighting_floor <= 20 else "21-50" if fighting_floor <= 50 else "51-100"
        monster = random.choice(MONSTERS[tier])
        
        player_data = (level, exp, credits, faction, max_floor, weapon_key, fighting_floor, weapon_level)
        combat_view = CombatView(interaction.user, player_data, monster)
        await interaction.response.send_message(embed=combat_view.build_embed(), view=combat_view)

    @app_commands.command(name="daily", description="Claim your daily allowance of 1000 Credits")
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT credits, last_daily_time FROM WistoriaPlayers WHERE user_id = ?", (user_id,))
            player = cursor.fetchone()
        except sqlite3.OperationalError:
            conn.close()
            return await interaction.response.send_message("🛠️ Database is updating. Please ask the admin to run `update_daily_db.py`.", ephemeral=True)
            
        if not player:
            conn.close()
            return await interaction.response.send_message("⚠️ You haven't enrolled yet!", ephemeral=True)
            
        current_credits, str_last_time = player
        last_time = datetime.strptime(str_last_time, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        
        if now - last_time < timedelta(hours=24):
            remaining_time = timedelta(hours=24) - (now - last_time)
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            conn.close()
            return await interaction.response.send_message(f"⏳ You have already claimed your daily reward! Come back in **{hours}h {minutes}m**.", ephemeral=True)
            
        cursor.execute("UPDATE WistoriaPlayers SET credits = ?, last_daily_time = ? WHERE user_id = ?", (current_credits + 1000, now.strftime('%Y-%m-%d %H:%M:%S'), user_id))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"🎁 **Daily Reward Claimed!** You received **1000 ✨ Credits**.\nYour balance is now: **{current_credits + 1000} ✨**")

    @app_commands.command(name="sell", description="Sell unused weapons for Credits")
    @app_commands.describe(weapon_id="The ID of the weapon to sell", quantity="Amount to sell (Default: 1)")
    async def sell(self, interaction: discord.Interaction, weapon_id: str, quantity: int = 1):
        if quantity < 1: return await interaction.response.send_message("❌ Quantity must be at least 1.", ephemeral=True)
        if weapon_id not in WEAPONS: return await interaction.response.send_message("❌ Invalid weapon ID! Check your `/inventory`.", ephemeral=True)
            
        target_weapon = WEAPONS[weapon_id]
        sell_price_per_item = SELL_PRICES.get(target_weapon["tier"], 25)
        total_revenue = sell_price_per_item * quantity
        
        user_id = interaction.user.id
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT equipped_weapon, credits FROM WistoriaPlayers WHERE user_id = ?", (user_id,))
        player_info = cursor.fetchone()
        if not player_info:
            conn.close()
            return await interaction.response.send_message("⚠️ You haven't enrolled yet!", ephemeral=True)
            
        equipped, current_credits = player_info
        cursor.execute("SELECT quantity FROM PlayerInventory WHERE user_id = ? AND weapon_key = ?", (user_id, weapon_id))
        item = cursor.fetchone()
        
        if not item or item[0] < quantity:
            conn.close()
            return await interaction.response.send_message(f"❌ You don't have {quantity}x of this weapon to sell!", ephemeral=True)
            
        current_qty = item[0]
        if equipped == weapon_id and (current_qty - quantity) < 1:
            conn.close()
            return await interaction.response.send_message(f"🛡️ **Warning!** You are currently equipping this weapon! Unequip it first or sell fewer.", ephemeral=True)
            
        if current_qty - quantity == 0:
            cursor.execute("DELETE FROM PlayerInventory WHERE user_id = ? AND weapon_key = ?", (user_id, weapon_id))
        else:
            cursor.execute("UPDATE PlayerInventory SET quantity = ? WHERE user_id = ? AND weapon_key = ?", (current_qty - quantity, user_id, weapon_id))
            
        cursor.execute("UPDATE WistoriaPlayers SET credits = ? WHERE user_id = ?", (current_credits + total_revenue, user_id))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"💰 You sold {quantity}x {target_weapon['emoji']} **{target_weapon['name']}** for **{total_revenue} ✨ Credits**!")

    @app_commands.command(name="inventory", description="Open your equipment bag")
    async def inventory(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT equipped_weapon FROM WistoriaPlayers WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        if not player:
            conn.close()
            return await interaction.response.send_message("⚠️ You haven't enrolled yet!", ephemeral=True)
            
        equipped = player[0]
        # Lấy thêm weapon_level để hiển thị
        cursor.execute("SELECT weapon_key, quantity, weapon_level FROM PlayerInventory WHERE user_id = ?", (user_id,))
        items = cursor.fetchall()
        conn.close()
        
        if not items: return await interaction.response.send_message("🎒 Your inventory is completely empty.", ephemeral=True)
            
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Inventory", color=discord.Color.gold())
        desc = ""
        for weapon_key, qty, w_lvl in items:
            w_data = WEAPONS.get(weapon_key)
            if not w_data: continue
            
            w_lvl = w_lvl if w_lvl is not None else 1
            status = "🔴 **[EQUIPPED]**" if weapon_key == equipped else f"ID: `{weapon_key}`"
            
            # Tính toán sát thương thực tế bao gồm cả cấp độ để hiển thị trong kho đồ
            dmg_bonus = (w_lvl - 1) * LVL_BONUS.get(w_data["tier"], 0)
            actual_dmg = w_data["dmg"] + dmg_bonus
            
            lvl_str = f" (+{w_lvl})" if w_lvl > 1 else ""
            desc += f"{w_data['emoji']} **{w_data['name']}{lvl_str}** (x{qty})\n*Tier {w_data['tier']} | DMG: {actual_dmg} | {status}*\n\n"
            
        embed.description = desc
        embed.set_footer(text="Use /equip <weapon_id> to change or /upgrade <weapon_id> to forge!")
        await interaction.response.set_message(embed=embed)

    @app_commands.command(name="equip", description="Equip a weapon from your inventory")
    @app_commands.describe(weapon_id="The ID of the weapon (e.g., w_iron_sword)")
    async def equip(self, interaction: discord.Interaction, weapon_id: str):
        user_id = interaction.user.id
        if weapon_id not in WEAPONS: return await interaction.response.send_message("❌ Invalid weapon ID! Check your `/inventory`.", ephemeral=True)
            
        target_weapon = WEAPONS[weapon_id]
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT faction FROM WistoriaPlayers WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        
        if not player:
            conn.close()
            return await interaction.response.send_message("⚠️ You haven't enrolled yet!", ephemeral=True)
            
        faction = player[0]
        if target_weapon["faction"] != "None" and target_weapon["faction"] != faction:
            conn.close()
            return await interaction.response.send_message(f"⚠️ **Incompatible Magic!** The {target_weapon['name']} requires **{target_weapon['faction']}** affinity.", ephemeral=True)
        
        cursor.execute("SELECT quantity FROM PlayerInventory WHERE user_id = ? AND weapon_key = ?", (user_id, weapon_id))
        item = cursor.fetchone()
        if not item or item[0] <= 0:
            conn.close()
            return await interaction.response.send_message("❌ You don't own this weapon in your inventory!", ephemeral=True)
            
        cursor.execute("UPDATE WistoriaPlayers SET equipped_weapon = ? WHERE user_id = ?", (weapon_id, user_id))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Successfully equipped {target_weapon['emoji']} **{target_weapon['name']}**!")

    @app_commands.command(name="summon", description="Spend 1000 Credits to summon a random magic weapon")
    async def summon(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        cost = 1000
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT credits FROM WistoriaPlayers WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        
        if not player:
            conn.close()
            return await interaction.response.send_message("⚠️ You haven't enrolled yet!", ephemeral=True)
            
        current_credits = player[0]
        if current_credits < cost:
            conn.close()
            return await interaction.response.send_message(f"💸 Not enough Credits! You need **{cost}** ✨. (Current: {current_credits})", ephemeral=True)
            
        roll = random.uniform(0, 100)
        if roll <= 1.0: pulled_tier, color = "SS", discord.Color.gold()
        elif roll <= 5.0: pulled_tier, color = "S", discord.Color.purple()
        elif roll <= 15.0: pulled_tier, color = "A", discord.Color.blue()
        elif roll <= 45.0: pulled_tier, color = "B", discord.Color.green()
        else: pulled_tier, color = "C", discord.Color.light_grey()
            
        possible_weapons = {k: v for k, v in WEAPONS.items() if v["tier"] == pulled_tier}
        pulled_weapon_key = random.choice(list(possible_weapons.keys()))
        pulled_weapon = possible_weapons[pulled_weapon_key]
        
        new_credits = current_credits - cost
        cursor.execute("UPDATE WistoriaPlayers SET credits = ? WHERE user_id = ?", (new_credits, user_id))
        
        # Sửa đổi lệnh INSERT gacha để mặc định weapon_level = 1 nếu là vũ khí mới quay được lần đầu
        cursor.execute("""
            INSERT INTO PlayerInventory (user_id, weapon_key, quantity, weapon_level) 
            VALUES (?, ?, 1, 1) 
            ON CONFLICT(user_id, weapon_key) 
            DO UPDATE SET quantity = quantity + 1
        """, (user_id, pulled_weapon_key))
        
        conn.commit()
        conn.close()
        
        embed = discord.Embed(title="✨ Magic Summoning Circle Activating... ✨", description=f"You spent **1000 Credits** and pulled a weapon from the void!", color=color)
        if pulled_tier in ["S", "SS"]: embed.title = "🌟 LEGENDARY PULL! THE HEAVENS SHAKE! 🌟"
            
        embed.add_field(name="🎁 You Obtained:", value=f"{pulled_weapon['emoji']} **{pulled_weapon['name']}**\n**Tier:** {pulled_weapon['tier']} | **DMG:** {pulled_weapon['dmg']}\n**Faction Check:** {pulled_weapon['faction']}", inline=False)
        embed.set_footer(text=f"Remaining Credits: {new_credits} ✨ | Use /inventory to check.")
        await interaction.response.send_message(embed=embed)


    # ========================================================
    # MỚI 1: TÍNH NĂNG LÒ RÈN NÂNG CẤP VŨ KHÍ (UPGRADE)
    # ========================================================
    @app_commands.command(name="upgrade", description="Consume 1 duplicate copy + Credits to level up a weapon")
    @app_commands.describe(weapon_id="The ID of the weapon to upgrade (e.g., w_iron_sword)")
    async def upgrade(self, interaction: discord.Interaction, weapon_id: str):
        user_id = interaction.user.id
        if weapon_id not in WEAPONS:
            return await interaction.response.send_message("❌ Invalid weapon ID! Check your `/inventory`.", ephemeral=True)
            
        target_weapon = WEAPONS[weapon_id]
        tier = target_weapon["tier"]
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        # 1. Kiểm tra túi đồ của người chơi
        cursor.execute("SELECT quantity, weapon_level FROM PlayerInventory WHERE user_id = ? AND weapon_key = ?", (user_id, weapon_id))
        inv_data = cursor.fetchone()
        
        if not inv_data or inv_data[0] < 2:
            conn.close()
            return await interaction.response.send_message(f"❌ **Upgrade Failed!** You need at least **2 copies** of this weapon (1 to equip, 1 to consume as material).", ephemeral=True)
            
        current_qty, current_lvl = inv_data
        current_lvl = current_lvl if current_lvl is not None else 1
        
        # 2. Tính toán chi phí nâng cấp
        upgrade_cost = UPGRADE_BASE_COSTS[tier] * current_lvl
        
        # 3. Kiểm tra ví tiền người chơi
        cursor.execute("SELECT credits FROM WistoriaPlayers WHERE user_id = ?", (user_id,))
        player_credits = cursor.fetchone()[0]
        
        if player_credits < upgrade_cost:
            conn.close()
            return await interaction.response.send_message(f"💸 **Insolvent!** Upgrading this weapon to +{current_lvl + 1} requires **{upgrade_cost} ✨ Credits**. (You have: {player_credits})", ephemeral=True)
            
        # 4. Thực thi nâng cấp (Trừ 1 bản sao, Trừ tiền, Tăng 1 Level vũ khí)
        new_credits = player_credits - upgrade_cost
        new_qty = current_qty - 1
        new_lvl = current_lvl + 1
        
        cursor.execute("UPDATE WistoriaPlayers SET credits = ? WHERE user_id = ?", (new_credits, user_id))
        cursor.execute("UPDATE PlayerInventory SET quantity = ?, weapon_level = ? WHERE user_id = ? AND weapon_key = ?", (new_qty, new_lvl, user_id, weapon_id))
        
        conn.commit()
        conn.close()
        
        # Tính toán sát thương mới để khoe
        old_dmg = target_weapon["dmg"] + (current_lvl - 1) * LVL_BONUS[tier]
        new_dmg = target_weapon["dmg"] + (new_lvl - 1) * LVL_BONUS[tier]
        
        embed = discord.Embed(
            title="🔨 Rigarden Blacksmith - Success! 🔨",
            description=f"The blacksmith successfully forged and refined your weapon!",
            color=discord.Color.dark_gold()
        )
        embed.add_field(name="Weapon", value=f"{target_weapon['emoji']} **{target_weapon['name']}**", inline=True)
        embed.add_field(name="Refinement level", value=f"**+{current_lvl}** ➔ 🌟 **+{new_lvl}**", inline=True)
        embed.add_field(name="Attack Growth", value=f"⚔️ Sát thương: `{old_dmg}` ➔ **`{new_dmg} DMG`** (+{LVL_BONUS[tier]})", inline=False)
        embed.set_footer(text=f"Spent {upgrade_cost} Credits | Remaining balance: {new_credits} ✨")
        
        await interaction.response.send_message(embed=embed)


    # ========================================================
    # MỚI 2: LỆNH TRA CỨU THÔNG SỐ VŨ KHÍ (WEAPON)
    # ========================================================
    @app_commands.command(name="weapon", description="Inspect the detailed statistics of a specific weapon")
    @app_commands.describe(weapon_id="The ID of the weapon (e.g., w_iron_sword, w_broken_branch)")
    async def weapon(self, interaction: discord.Interaction, weapon_id: str):
        if weapon_id not in WEAPONS:
            return await interaction.response.send_message("❌ Invalid weapon ID! Ensure it starts with `w_`.", ephemeral=True)
            
        target_weapon = WEAPONS[weapon_id]
        tier = target_weapon["tier"]
        
        # Kiểm tra xem người dùng hiện tại có sở hữu và nâng cấp nó không
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT quantity, weapon_level FROM PlayerInventory WHERE user_id = ? AND weapon_key = ?", (interaction.user.id, weapon_id))
        owned_data = cursor.fetchone()
        conn.close()
        
        # Thiết lập thông tin hiển thị
        if owned_data:
            qty, lvl = owned_data
            lvl = lvl if lvl is not None else 1
            ownership_status = f"✅ **Owned:** x{qty} (Level +{lvl})"
            bonus_dmg = (lvl - 1) * LVL_BONUS[tier]
            display_dmg = f"**{target_weapon['dmg'] + bonus_dmg}** ({target_weapon['dmg']} Base + {bonus_dmg} Forge)"
            next_upgrade_cost = f"{UPGRADE_BASE_COSTS[tier] * lvl} ✨ Credits"
        else:
            lvl = 1
            ownership_status = "❌ **Not Owned**"
            display_dmg = f"{target_weapon['dmg']} (Base)"
            next_upgrade_cost = f"{UPGRADE_BASE_COSTS[tier]} ✨ Credits"
            
        # Xác định màu sắc Embed theo độ hiếm
        tier_colors = {"D": 0x95a5a6, "C": 0x7f8c8d, "B": 0x2ecc71, "A": 0x3498db, "S": 0x9b59b6, "SS": 0xf1c40f}
        
        embed = discord.Embed(
            title=f"{target_weapon['emoji']} Weapon Codex: {target_weapon['name']}",
            description=f"**Weapon ID:** `{weapon_id}`\n**Status:** {ownership_status}",
            color=tier_colors.get(tier, 0xffffff)
        )
        
        embed.add_field(name="Classification", value=f"⭐ **Tier:** {tier}\n🔮 **Faction:** {target_weapon['faction']}", inline=True)
        embed.add_field(name="Combat Power", value=f"⚔️ **Total DMG:** {display_dmg}\n📈 **Growth per lvl:** +{LVL_BONUS[tier]} DMG", inline=True)
        embed.add_field(name="Forge & Economy", value=f"🛠️ **Next Upgrade Cost:** {next_upgrade_cost}\n💰 **Recycle Value:** {SELL_PRICES.get(tier, 25)} Credits", inline=False)
        
        embed.set_footer(text="To upgrade this weapon, obtain duplicates and use /upgrade!")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(WistoriaRPG(bot))