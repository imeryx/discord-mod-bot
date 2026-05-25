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
    progress = max(0, min(length, progress)) 
    return (color_emoji * progress) + (empty_emoji * (length - progress))


# --- FACTION SELECTION VIEW ---
class FactionSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180) 

    async def register_player(self, interaction: discord.Interaction, faction_key: str):
        user_id = interaction.user.id
        faction_info = FACTIONS[faction_key]
        
        # Chọn vũ khí khởi đầu tùy theo hệ (Tier D)
        starter_weapon = "w_dull_blade" if faction_key == "Physical" else "w_broken_branch"
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        try:
            # 1. Đăng ký người chơi và gán vũ khí mặc định vào DB
            cursor.execute('INSERT INTO WistoriaPlayers (user_id, faction, equipped_weapon) VALUES (?, ?, ?)', (user_id, faction_key, starter_weapon))
            
            # 2. Thêm vũ khí khởi đầu vào túi đồ của họ
            cursor.execute('INSERT INTO PlayerInventory (user_id, weapon_key, quantity) VALUES (?, ?, 1)', (user_id, starter_weapon))
            
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
    async def btn_ice(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Ice")

    @discord.ui.button(label="Fire (Ignis)", emoji="🔥", style=discord.ButtonStyle.danger, row=0)
    async def btn_fire(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Fire")

    @discord.ui.button(label="Physical (Sword)", emoji="⚔️", style=discord.ButtonStyle.secondary, row=0)
    async def btn_phys(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Physical")

    @discord.ui.button(label="Wind (Ventus)", emoji="🌪️", style=discord.ButtonStyle.primary, row=1)
    async def btn_wind(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Wind")

    @discord.ui.button(label="Earth (Terra)", emoji="🪨", style=discord.ButtonStyle.success, row=1)
    async def btn_earth(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Earth")

    @discord.ui.button(label="Lightning (Fulgur)", emoji="⚡", style=discord.ButtonStyle.danger, row=1)
    async def btn_lightning(self, interaction: discord.Interaction, button: discord.ui.Button): 
        await self.register_player(interaction, "Lightning")


# --- THE COMBAT ARENA ---
class CombatView(discord.ui.View):
    def __init__(self, user, player_data, monster):
        super().__init__(timeout=300)
        self.user = user
        self.monster = monster
        
        # Unpack dữ liệu (Bao gồm cả weapon_key từ Database)
        self.level, self.exp, self.credits, self.faction_key, self.floor, self.weapon_key = player_data
        
        faction_data = FACTIONS[self.faction_key]
        self.max_hp = faction_data["base_hp"] + (self.level * faction_data["hp_growth"])
        self.current_hp = self.max_hp
        self.max_mana = faction_data["base_mana"] + (self.level * faction_data["mana_growth"])
        self.current_mana = self.max_mana
        
        # Đọc thông số vũ khí thực tế người chơi đang trang bị
        self.equipped_weapon = WEAPONS.get(self.weapon_key, WEAPONS["w_broken_branch"])
        self.base_dmg = self.equipped_weapon["dmg"] + (self.level * 3)
        
        floor_factor = max(0, self.floor - 1)
        self.monster_max_hp = int(monster["hp"] * (1 + floor_factor * 0.08))
        self.monster_hp = self.monster_max_hp
        self.monster_dmg = int(monster["dmg"] * (1 + floor_factor * 0.04))
        
        self.combat_log = f"Trang bị: **{self.equipped_weapon['name']}**! The battle begins.\n"
        self.skill_cooldowns = {}
        
        self.update_buttons()

    def build_embed(self):
        embed = discord.Embed(
            title=f"⚔️ Dungeon - Floor {self.floor}", 
            description=f"📜 **Combat Log:**\n> {self.combat_log}", 
            color=discord.Color.dark_red()
        )
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
                if self.current_mana < skill["mana_cost"]:
                    disabled, style = True, discord.ButtonStyle.secondary
            if cd_remaining > 0:
                label += f" (CD: {cd_remaining}T)"
                disabled, style = True, discord.ButtonStyle.secondary
                
            btn_skill = discord.ui.Button(label=label, emoji=skill['emoji'], style=style, disabled=disabled, row=0 if index < 3 else 1)
            btn_skill.callback = self.create_skill_callback(skill)
            self.add_item(btn_skill)
            
        btn_flee = discord.ui.Button(label="Flee", emoji="🏃", style=discord.ButtonStyle.danger, row=2)
        btn_flee.callback = self.flee_callback
        self.add_item(btn_flee)

    async def attack_callback(self, interaction: discord.Interaction):
        await self.process_turn(interaction, action="attack")

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
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("⚠️ This is not your battle!", ephemeral=True)

        self.combat_log = "" 
        player_dmg = 0
        if action == "attack":
            player_dmg = self.base_dmg
            mana_regen = 15 if self.max_mana > 0 else 0
            self.current_mana = min(self.max_mana, self.current_mana + mana_regen)
            self.combat_log += f"🗡️ You used Basic Attack dealing **{player_dmg} DMG**! Recovered {mana_regen} MP.\n"
        elif action == "skill":
            if skill["mana_cost"] > 0 and self.current_mana < skill["mana_cost"]:
                return await interaction.response.send_message("❌ Not enough Mana!", ephemeral=True)
            if self.skill_cooldowns.get(skill["id"], 0) > 0:
                return await interaction.response.send_message("❌ Skill is on cooldown!", ephemeral=True)
            
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
        new_exp, new_level, new_floor = self.exp + earned_exp, self.level, self.floor
        exp_needed = self.level * 100
        level_up_msg = ""
        
        if new_exp >= exp_needed:
            new_level += 1
            new_exp -= exp_needed
            new_floor += 1
            level_up_msg = f"\n\n🎉 **LEVEL UP!** Reached Level {new_level}! Advanced to Floor {new_floor}!"

        c = sqlite3.connect('bot_database.db')
        c.execute('UPDATE WistoriaPlayers SET level=?, exp=?, credits=?, current_floor=? WHERE user_id=?', (new_level, new_exp, self.credits + earned_credits, new_floor, self.user.id))
        c.commit()
        c.close()

        win_embed = discord.Embed(title="🏆 VICTORY!", description=f"You successfully defeated the **{self.monster['name']}**!\n\n**📦 Loot:**\n✨ **+{earned_credits}** Credits\n📈 **+{earned_exp}** EXP" + level_up_msg, color=discord.Color.green())
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
        player = conn.cursor().execute("SELECT * FROM WistoriaPlayers WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        
        if player: return await interaction.response.send_message("⚠️ You are already enrolled! Use `/profile`.", ephemeral=True)
        
        embed = discord.Embed(title="🔮 The Magic Awakening Sphere", description="Touch the sphere to determine your path of power.", color=discord.Color.dark_purple())
        embed.set_image(url="https://images4.alphacoders.com/136/thumbbig-1368886.webp") 
        await interaction.response.send_message(embed=embed, view=FactionSelectView())

    @app_commands.command(name="profile", description="View your detailed Rigarden Student Profile & Stats")
    async def profile(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = sqlite3.connect('bot_database.db')
        # Lấy thêm equipped_weapon từ DB
        player = conn.cursor().execute("SELECT level, exp, credits, faction, current_floor, equipped_weapon FROM WistoriaPlayers WHERE user_id = ?", (user_id,)).fetchone()
        conn.close()
        
        if not player: return await interaction.response.send_message("⚠️ You haven't enrolled yet! Use `/start_journey`.", ephemeral=True)
            
        level, exp, credits, faction_key, current_floor, weapon_key = player
        
        # Fallback an toàn nếu người chơi cũ chưa có dữ liệu vũ khí
        if not weapon_key: weapon_key = "w_dull_blade" if faction_key == "Physical" else "w_broken_branch"
        
        faction_info = FACTIONS.get(faction_key, {"name": "Unknown", "emoji": "❓"})
        max_hp = faction_info["base_hp"] + (level * faction_info["hp_growth"])
        max_mana = faction_info["base_mana"] + (level * faction_info["mana_growth"])
        
        equipped_weapon = WEAPONS.get(weapon_key, WEAPONS["w_broken_branch"])
        total_dmg = equipped_weapon["dmg"] + (level * 3)
        
        available_skills = [sk for sk in PLAYER_SKILLS.get(faction_key, []) if level >= sk["unlock_level"]]
        skills_text = ""
        for sk in available_skills:
            cost_str = f"{sk['mana_cost']}MP" if sk.get("mana_cost", 0) > 0 else "0MP"
            cd_str = f" | {sk['cooldown']}T CD" if "cooldown" in sk else ""
            skills_text += f"{sk['emoji']} **{sk['name']}** ({cost_str}{cd_str})\n*↳ {sk['desc']}*\n\n"
            
        exp_needed = level * 100 
        embed = discord.Embed(title=f"🎓 Student Profile | {interaction.user.display_name}", color=discord.Color.blue())
        if interaction.user.avatar: embed.set_thumbnail(url=interaction.user.avatar.url)
        embed.add_field(name="Magic Faction", value=f"{faction_info['emoji']} **{faction_info['name']}**", inline=True)
        embed.add_field(name="Level", value=f"**Lv. {level}**", inline=True)
        embed.add_field(name="Credits", value=f"✨ **{credits:,}**", inline=True)
        embed.add_field(name="Combat Stats", value=f"💖 **HP:** {max_hp}\n💧 **MP:** {max_mana}\n⚔️ **Total DMG:** {total_dmg}", inline=True)
        embed.add_field(name="Equipped Weapon", value=f"{equipped_weapon['emoji']} **{equipped_weapon['name']}**\n*Tier {equipped_weapon['tier']} | DMG: {equipped_weapon['dmg']}*", inline=True)
        embed.add_field(name="Tower Progress", value=f"🏰 **Floor {current_floor}**", inline=True)
        embed.add_field(name=f"Experience ({exp}/{exp_needed})", value=generate_bar(exp, exp_needed, "🟩"), inline=False)
        embed.add_field(name="Unlocked Skills", value=skills_text or "*No skills yet.*", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dungeon", description="Enter the dungeon to hunt monsters")
    async def dungeon(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        # Lấy thêm equipped_weapon
        player = cursor.execute("SELECT level, exp, credits, faction, current_floor, last_dungeon_time, equipped_weapon FROM WistoriaPlayers WHERE user_id = ?", (user_id,)).fetchone()
        
        if not player:
            conn.close()
            return await interaction.response.send_message("⚠️ Use `/start_journey` first.", ephemeral=True)
            
        level, exp, credits, faction, current_floor, str_last_time, weapon_key = player
        if not weapon_key: weapon_key = "w_dull_blade" if faction == "Physical" else "w_broken_branch"
        
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
        
        tier = "1-20" if current_floor <= 20 else "21-50" if current_floor <= 50 else "51-100"
        monster = random.choice(MONSTERS[tier])
        
        # Truyền thêm weapon_key vào dữ liệu trận đấu
        player_data = (level, exp, credits, faction, current_floor, weapon_key)
        combat_view = CombatView(interaction.user, player_data, monster)
        
        await interaction.response.send_message(embed=combat_view.build_embed(), view=combat_view)

    # ========================================================
    # LỆNH QUẢN LÝ TÚI ĐỒ (INVENTORY) & TRANG BỊ (EQUIP)
    # ========================================================
    
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
        
        cursor.execute("SELECT weapon_key, quantity FROM PlayerInventory WHERE user_id = ?", (user_id,))
        items = cursor.fetchall()
        conn.close()
        
        if not items:
            return await interaction.response.send_message("🎒 Your inventory is completely empty.", ephemeral=True)
            
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Inventory", color=discord.Color.gold())
        
        desc = ""
        for weapon_key, qty in items:
            w_data = WEAPONS.get(weapon_key)
            if not w_data: continue
            
            status = "🔴 **[EQUIPPED]**" if weapon_key == equipped else f"ID: `{weapon_key}`"
            desc += f"{w_data['emoji']} **{w_data['name']}** (x{qty})\n*Tier {w_data['tier']} | DMG: {w_data['dmg']} | {status}*\n\n"
            
        embed.description = desc
        embed.set_footer(text="Use /equip <weapon_id> to change your weapon!")
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="equip", description="Equip a weapon from your inventory")
    @app_commands.describe(weapon_id="The ID of the weapon (e.g., w_iron_sword)")
    async def equip(self, interaction: discord.Interaction, weapon_id: str):
        user_id = interaction.user.id
        
        if weapon_id not in WEAPONS:
            return await interaction.response.send_message("❌ Invalid weapon ID! Check your `/inventory`.", ephemeral=True)
            
        target_weapon = WEAPONS[weapon_id]
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT faction FROM WistoriaPlayers WHERE user_id = ?", (user_id,))
        player = cursor.fetchone()
        if not player:
            conn.close()
            return await interaction.response.send_message("⚠️ You haven't enrolled yet!", ephemeral=True)
            
        faction = player[0]
        
        # Cơ chế khóa Hệ phái
        if target_weapon["faction"] != "None" and target_weapon["faction"] != faction:
            conn.close()
            return await interaction.response.send_message(f"⚠️ **Incompatible Magic!** The {target_weapon['name']} requires **{target_weapon['faction']}** affinity.", ephemeral=True)
        
        # Kiểm tra xem người chơi có thực sự sở hữu món đồ này không
        cursor.execute("SELECT quantity FROM PlayerInventory WHERE user_id = ? AND weapon_key = ?", (user_id, weapon_id))
        item = cursor.fetchone()
        
        if not item or item[0] <= 0:
            conn.close()
            return await interaction.response.send_message("❌ You don't own this weapon in your inventory!", ephemeral=True)
            
        # Cập nhật vũ khí vào bảng chính
        cursor.execute("UPDATE WistoriaPlayers SET equipped_weapon = ? WHERE user_id = ?", (weapon_id, user_id))
        conn.commit()
        conn.close()
        
        await interaction.response.send_message(f"✅ Successfully equipped {target_weapon['emoji']} **{target_weapon['name']}**!")


async def setup(bot):
    await bot.add_cog(WistoriaRPG(bot))