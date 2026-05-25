# cogs/game_data.py

# --- HỆ PHÁI & CHỈ SỐ CƠ BẢN (Base Stats) ---
FACTIONS = {
    "Ice": {
        "name": "Ice (El)", "emoji": "🧊", "strong_against": "Fire",
        "base_hp": 100, "base_mana": 60, "hp_growth": 15, "mana_growth": 8
    },
    "Fire": {
        "name": "Fire (Ignis)", "emoji": "🔥", "strong_against": "Wind",
        "base_hp": 85, "base_mana": 50, "hp_growth": 12, "mana_growth": 6
    },
    "Wind": {
        "name": "Wind (Ventus)", "emoji": "🌪️", "strong_against": "Earth",
        "base_hp": 90, "base_mana": 55, "hp_growth": 14, "mana_growth": 7
    },
    "Earth": {
        "name": "Earth (Terra)", "emoji": "🪨", "strong_against": "Lightning",
        "base_hp": 150, "base_mana": 40, "hp_growth": 25, "mana_growth": 4
    },
    "Lightning": {
        "name": "Lightning (Fulgur)", "emoji": "⚡", "strong_against": "Ice",
        "base_hp": 80, "base_mana": 70, "hp_growth": 10, "mana_growth": 10
    },
    "Physical": {
        "name": "Physical (Sword)", "emoji": "⚔️", "strong_against": "None", 
        "base_hp": 120, "base_mana": 0, "hp_growth": 20, "mana_growth": 0 # Vô năng không có Mana
    }
}

# --- KỸ NĂNG NGƯỜI CHƠI (PLAYER SKILLS) ---
PLAYER_SKILLS = {
    "Ice": [
        {"id": "sk_ice_pierce", "name": "Ice Pierce", "emoji": "🗡️", "unlock_level": 1, "mana_cost": 15, "dmg_multiplier": 1.5, "desc": "Fire a sharp ice spear."},
        {"id": "sk_frost_shield", "name": "Frost Shield", "emoji": "🛡️", "unlock_level": 5, "mana_cost": 25, "dmg_multiplier": 0, "desc": "Create an ice shield, reducing incoming damage."},
        {"id": "sk_absolute_zero", "name": "Absolute Zero", "emoji": "❄️", "unlock_level": 15, "mana_cost": 60, "dmg_multiplier": 3.0, "desc": "Freeze everything. Massive AoE damage."}
    ],
    "Fire": [
        {"id": "sk_fireball", "name": "Fireball", "emoji": "☄️", "unlock_level": 1, "mana_cost": 15, "dmg_multiplier": 1.6, "desc": "Throw a burning fireball."},
        {"id": "sk_flame_burst", "name": "Flame Burst", "emoji": "💥", "unlock_level": 5, "mana_cost": 30, "dmg_multiplier": 2.2, "desc": "Trigger a high-intensity flame explosion."},
        {"id": "sk_hellfire", "name": "Hellfire", "emoji": "🌋", "unlock_level": 15, "mana_cost": 65, "dmg_multiplier": 3.5, "desc": "Summon hellfire to incinerate the enemy."}
    ],
    "Wind": [
        {"id": "sk_wind_blade", "name": "Wind Blade", "emoji": "🌪️", "unlock_level": 1, "mana_cost": 12, "dmg_multiplier": 1.4, "desc": "Slash the enemy with sharp winds."},
        {"id": "sk_gale_step", "name": "Tornado Strike", "emoji": "💨", "unlock_level": 5, "mana_cost": 25, "dmg_multiplier": 2.0, "desc": "A rapid strike empowered by a tornado."},
        {"id": "sk_storm_tempest", "name": "Storm Tempest", "emoji": "🌩️", "unlock_level": 15, "mana_cost": 55, "dmg_multiplier": 3.2, "desc": "Summon a massive tempest to tear enemies apart."}
    ],
    "Earth": [
        {"id": "sk_rock_throw", "name": "Rock Throw", "emoji": "🪨", "unlock_level": 1, "mana_cost": 15, "dmg_multiplier": 1.5, "desc": "Hurl a heavy boulder at the target."},
        {"id": "sk_terra_armor", "name": "Terra Armor", "emoji": "🧱", "unlock_level": 5, "mana_cost": 20, "dmg_multiplier": 0, "desc": "Cover yourself in stone, bracing for impact."},
        {"id": "sk_meteor_strike", "name": "Meteor Strike", "emoji": "🌠", "unlock_level": 15, "mana_cost": 70, "dmg_multiplier": 3.8, "desc": "Pull a meteor from the sky. Devastating damage."}
    ],
    "Lightning": [
        {"id": "sk_spark_volt", "name": "Spark Volt", "emoji": "⚡", "unlock_level": 1, "mana_cost": 18, "dmg_multiplier": 1.7, "desc": "Shoot a quick jolt of electricity."},
        {"id": "sk_chain_lightning", "name": "Chain Lightning", "emoji": "🌩️", "unlock_level": 5, "mana_cost": 35, "dmg_multiplier": 2.4, "desc": "Unleash lightning that strikes vital points."},
        {"id": "sk_thunder_wrath", "name": "Thunder God's Wrath", "emoji": "⛈️", "unlock_level": 15, "mana_cost": 65, "dmg_multiplier": 3.6, "desc": "Call down divine lightning to obliterate foes."}
    ],
    "Physical": [
        {"id": "sk_heavy_strike", "name": "Heavy Strike", "emoji": "⚔️", "unlock_level": 1, "mana_cost": 0, "dmg_multiplier": 1.4, "desc": "A powerful sword slash. (Costs no Mana)"},
        {"id": "sk_parry", "name": "Parry & Counter", "emoji": "🛡️", "unlock_level": 5, "mana_cost": 0, "dmg_multiplier": 1.0, "desc": "Deflect the attack and counter immediately."},
        {"id": "sk_wis_strike", "name": "Wistoria Strike", "emoji": "✨", "unlock_level": 15, "mana_cost": 0, "dmg_multiplier": 2.8, "desc": "The ultimate sword skill of the magicless."}
    ]
}

# --- KHO VŨ KHÍ (WEAPONS) ---
WEAPONS = {
    # --- TIER B: COMMON (Phổ thông) ---
    "w_wood_staff": {"name": "Novice Wooden Staff", "emoji": "🪵", "tier": "B", "dmg": 15, "faction": "None"},
    "w_rusty_sword": {"name": "Rusty Sword", "emoji": "🗡️", "tier": "B", "dmg": 18, "faction": "Physical"},
    "w_old_grimoire": {"name": "Old Torn Grimoire", "emoji": "📖", "tier": "B", "dmg": 14, "faction": "None"},
    
    # --- TIER A: RARE (Hiếm) ---
    "w_ice_crystal": {"name": "Frost Crystal Wand", "emoji": "💎", "tier": "A", "dmg": 45, "faction": "Ice"},
    "w_fire_blade": {"name": "Flame Dagger", "emoji": "🔥", "tier": "A", "dmg": 48, "faction": "Fire"},
    "w_gale_bow": {"name": "Gale Bow", "emoji": "🏹", "tier": "A", "dmg": 42, "faction": "Wind"},
    "w_stone_hammer": {"name": "Heavy Stone Hammer", "emoji": "🔨", "tier": "A", "dmg": 50, "faction": "Earth"},
    "w_shock_wand": {"name": "Static Shock Wand", "emoji": "🪄", "tier": "A", "dmg": 46, "faction": "Lightning"},
    "w_steel_sword": {"name": "Steel Longsword", "emoji": "🤺", "tier": "A", "dmg": 55, "faction": "Physical"},
    
    # --- TIER S: EPIC (Sử thi) ---
    "w_glacial_scepter": {"name": "Glacial Scepter", "emoji": "💠", "tier": "S", "dmg": 110, "faction": "Ice"},
    "w_inferno_halberd": {"name": "Inferno Halberd", "emoji": "🔱", "tier": "S", "dmg": 125, "faction": "Fire"},
    "w_tempest_blade": {"name": "Tempest Twin Blades", "emoji": "⚔️", "tier": "S", "dmg": 105, "faction": "Wind"},
    "w_earth_axe": {"name": "Seismic Great Axe", "emoji": "🪓", "tier": "S", "dmg": 130, "faction": "Earth"},
    "w_lightning_reaper": {"name": "Thunder Reaper", "emoji": "⚡", "tier": "S", "dmg": 120, "faction": "Lightning"},
    "w_knight_greatsword": {"name": "Knight's Greatsword", "emoji": "🗡️", "tier": "S", "dmg": 140, "faction": "Physical"},
    
    # --- TIER SS: VANDER / MYTHIC (Thần thoại) ---
    "w_albis_staff": {"name": "👑 Albis Ice Staff", "emoji": "❄️", "tier": "SS", "dmg": 280, "faction": "Ice"},
    "w_ignis_staff": {"name": "👑 Ignis Supreme Staff", "emoji": "🌋", "tier": "SS", "dmg": 300, "faction": "Fire"},
    "w_zephyr_breath": {"name": "👑 Zephyr's Breath", "emoji": "🌪️", "tier": "SS", "dmg": 270, "faction": "Wind"},
    "w_terra_aegis": {"name": "👑 Aegis of Terra", "emoji": "🛡️", "tier": "SS", "dmg": 320, "faction": "Earth"},
    "w_fulgur_judgement": {"name": "👑 Fulgur's Judgement", "emoji": "⛈️", "tier": "SS", "dmg": 290, "faction": "Lightning"},
    "w_sword_of_will": {"name": "👑 Sword of the Lone Wanderer", "emoji": "✨", "tier": "SS", "dmg": 350, "faction": "Physical"}
}
# --- QUÁI VẬT & AI KỸ NĂNG (MỞ RỘNG ĐA DẠNG) ---
MONSTERS = {
    "1-20": [
        {
            "name": "Mutant Slime", "emoji": "🟢", "hp": 150, "dmg": 10, "credits": 20,
            "skill_name": "Acid Splash", "skill_dmg_mult": 1.5, "skill_chance": 20,
            "gif": "https://i.pinimg.com/1200x/fc/05/f7/fc05f7ee42456f2b0f15c1ecab66c3a4.jpg" 
        },
        {
            "name": "Scout Goblin", "emoji": "👺", "hp": 200, "dmg": 15, "credits": 35,
            "skill_name": "Sneak Attack", "skill_dmg_mult": 2.0, "skill_chance": 25,
            "gif": "https://i.pinimg.com/736x/2e/20/58/2e2058b0474057ebd9b390d4868276a0.jpg"
        },
        {
            "name": "Demonic Wolf", "emoji": "🐺", "hp": 220, "dmg": 18, "credits": 50,
            "skill_name": "Feral Bite", "skill_dmg_mult": 1.8, "skill_chance": 30,
            "gif": "https://i.pinimg.com/736x/1c/1f/d9/1c1fd95239cf77df9b6c53d100dadeb1.jpg"
        },
        {
            "name": "Giant Spider", "emoji": "🕷️", "hp": 180, "dmg": 20, "credits": 45,
            "skill_name": "Venom Web", "skill_dmg_mult": 2.2, "skill_chance": 20,
            "gif": "https://i.pinimg.com/736x/05/cb/61/05cb61ba7220f99c29c82ff976f88906.jpg"
        },
        {
            "name": "Living Armor", "emoji": "🤖", "hp": 300, "dmg": 12, "credits": 60,
            "skill_name": "Shield Bash", "skill_dmg_mult": 1.5, "skill_chance": 15,
            "gif": "https://i.pinimg.com/736x/23/29/a7/2329a703aad2a24273ec866d56ae8d60.jpg"
        },
        {
            "name": "Rogue Mage", "emoji": "🧙", "hp": 120, "dmg": 25, "credits": 55,
            "skill_name": "Magic Missile", "skill_dmg_mult": 2.5, "skill_chance": 40,
            "gif": "https://i.pinimg.com/736x/d1/0e/64/d10e646926bc2c7c27d013cc86592f50.jpg"
        }
    ],
    "21-50": [
        {
            "name": "Crystal Golem", "emoji": "🗿", "hp": 800, "dmg": 40, "credits": 120,
            "skill_name": "Earthquake", "skill_dmg_mult": 1.8, "skill_chance": 30,
            "gif": "https://i.pinimg.com/736x/a5/39/29/a539298baec30c54350b1646c5a8b8cd.jpg"
        },
        {
            "name": "Mana-sucking Bat", "emoji": "🦇", "hp": 600, "dmg": 50, "credits": 150,
            "skill_name": "Vampiric Drain", "skill_dmg_mult": 2.0, "skill_chance": 35,
            "gif": "https://i.pinimg.com/736x/d6/1b/26/d61b261d214ce33559a73ff7d3f7436f.jpg"
        },
        {
            "name": "Headless Knight", "emoji": "🛡️", "hp": 1000, "dmg": 60, "credits": 250,
            "skill_name": "Decapitate", "skill_dmg_mult": 2.5, "skill_chance": 25,
            "gif": "https://i.pinimg.com/736x/72/54/3a/72543a52bba0ef42a3d53753a1e935dc.jpg"
        },
        {
            "name": "Fire Salamander", "emoji": "🦎", "hp": 750, "dmg": 70, "credits": 200,
            "skill_name": "Flame Breath", "skill_dmg_mult": 2.2, "skill_chance": 30,
            "gif": "https://i.pinimg.com/736x/b8/fb/41/b8fb415501e7ca551ec46d29473c3982.jpg"
        },
        {
            "name": "Shadow Assassin", "emoji": "🥷", "hp": 650, "dmg": 80, "credits": 280,
            "skill_name": "Fatal Backstab", "skill_dmg_mult": 3.0, "skill_chance": 20,
            "gif": "https://i.pinimg.com/1200x/02/74/f7/0274f7942246e7d73ce4549b01d9bf78.jpg"
        }
    ],
    "51-100": [
        {
            "name": "Supreme Dark Mage", "emoji": "🧙‍♂️", "hp": 2500, "dmg": 180, "credits": 1000,
            "skill_name": "Death Ray", "skill_dmg_mult": 2.5, "skill_chance": 40,
            "gif": "https://i.pinimg.com/736x/3b/c9/7c/3bc97cd91d03d3ce5b65fd5127c40d0a.jpg"
        },
        {
            "name": "Eternal Ice Dragon", "emoji": "🐉", "hp": 5000, "dmg": 250, "credits": 2500,
            "skill_name": "Absolute Frost Breath", "skill_dmg_mult": 2.0, "skill_chance": 35,
            "gif": "https://i.pinimg.com/736x/eb/c4/c9/ebc4c95467b106876092a62837df0707.jpg"
        },
        {
            "name": "Abyssal Behemoth", "emoji": "👹", "hp": 6000, "dmg": 300, "credits": 3500,
            "skill_name": "World Shatter", "skill_dmg_mult": 2.2, "skill_chance": 30,
            "gif": "https://i.pinimg.com/1200x/6d/ed/ba/6dedbaa8274d716e1d184c7b06793e45.jpg"
        },
        {
            "name": "Fallen Vander", "emoji": "👑", "hp": 4500, "dmg": 350, "credits": 4000,
            "skill_name": "Forbidden Magic", "skill_dmg_mult": 3.0, "skill_chance": 45,
            "gif": "https://i.pinimg.com/1200x/d6/7f/1d/d67f1d0f15ed438e283482a4945c88b1.jpg"
        },
        {
            "name": "Void Devourer", "emoji": "👁️", "hp": 8000, "dmg": 400, "credits": 5000,
            "skill_name": "Space Collapse", "skill_dmg_mult": 2.8, "skill_chance": 25,
            "gif": "https://i.pinimg.com/736x/96/6e/df/966edf1e7132e1ad38cdf4c66661bfbb.jpg"
        }
    ]
}

# --- CRAFTING & UPGRADE MATERIALS (LINH KIỆN NÂNG CẤP) ---
MATERIALS = {
    # --- COMMON MATERIALS (Nguyên liệu cơ bản - Rớt ở mọi tầng) ---
    "mat_iron_ore": {
        "name": "Iron Ore", 
        "emoji": "🪨", 
        "tier": "Common", 
        "desc": "A basic mineral used for reinforcing weapon frames and structures."
    },
    "mat_magic_dust": {
        "name": "Magic Dust", 
        "emoji": "✨", 
        "tier": "Common", 
        "desc": "Glowing residual dust used for basic mana conduction and stabilization."
    },

    # --- RARE ELEMENTAL SHARDS (Mảnh vỡ nguyên tố - Rớt theo quái hệ phái) ---
    "mat_frost_shard": {
        "name": "Frost Shard", 
        "emoji": "❄️", 
        "tier": "Rare", 
        "desc": "A frozen crystal holding stable ice energy. Required for Ice weapons."
    },
    "mat_flame_ember": {
        "name": "Flame Ember", 
        "emoji": "🔥", 
        "tier": "Rare", 
        "desc": "A flickering ember that never extinguishes. Required for Fire weapons."
    },
    "mat_gale_feather": {
        "name": "Gale Feather", 
        "emoji": "🪶", 
        "tier": "Rare", 
        "desc": "A feather blessed by high-altitude spirits. Required for Wind weapons."
    },
    "mat_terra_pebble": {
        "name": "Tectonic Pebble", 
        "emoji": "🧱", 
        "tier": "Rare", 
        "desc": "A heavy stone dense with earth essence. Required for Earth weapons."
    },
    "mat_spark_crystal": {
        "name": "Spark Crystal", 
        "emoji": "⚡", 
        "tier": "Rare", 
        "desc": "A crackling crystal storing raw static electricity. Required for Lightning weapons."
    },
    "mat_honing_stone": {
        "name": "Honing Stone", 
        "emoji": "🧫", 
        "tier": "Rare", 
        "desc": "A fine-grit whetstone used to sharpen physical blades. Required for Sword weapons."
    },

    # --- EPIC CORES (Lõi sử thi - Rớt ở Tầng 21-50 hoặc Boss) ---
    "mat_ancient_essence": {
        "name": "Ancient Essence", 
        "emoji": "🧪", 
        "tier": "Epic", 
        "desc": "A pure distillation of ancient magical energy used for high-tier upgrades."
    },
    "mat_dragon_blood": {
        "name": "Dragon Blood", 
        "emoji": "🩸", 
        "tier": "Epic", 
        "desc": "Boiling biological fluid capable of unlocking hidden weapon potentials."
    },

    # --- MYTHIC / VANDER CORES (Lõi Thần thoại - Cực hiếm ở Tầng 51-100) ---
    "mat_mercedes_gem": {
        "name": "Mercedes Crystal", 
        "emoji": "👑", 
        "tier": "Mythic", 
        "desc": "A legendary gemstone found near the top of the tower. Required for Tier SS upgrades."
    }
}