import sqlite3

# Đặt tên file DB thành biến để dễ quản lý sau này
DB_NAME = 'bot_database.db'

def setup_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Bảng Cài đặt Server chung
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS GuildSettings (
            guild_id INTEGER PRIMARY KEY, 
            mod_log_channel_id INTEGER,
            welcome_channel_id INTEGER, 
            mute_role_id INTEGER
        )
    ''')

    # 2. Bảng Cảnh báo (Warnings)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Warnings (
            warning_id INTEGER PRIMARY KEY AUTOINCREMENT, 
            guild_id INTEGER,
            user_id INTEGER, 
            moderator_id INTEGER, 
            reason TEXT, 
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Bảng Từ cấm (Word Filters)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS WordFilters (
            guild_id INTEGER, 
            word TEXT, 
            UNIQUE(guild_id, word) 
        )
    ''')

    # 4. Bảng Prefix Tùy chỉnh
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS GuildPrefixes (
            guild_id INTEGER PRIMARY KEY, 
            prefix TEXT
        )
    ''')

    # 5. Bảng Chào đón & Tạm biệt
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS welcome_settings (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            welcome_msg TEXT, 
            welcome_image TEXT,
            goodbye_msg TEXT, 
            goodbye_image TEXT,
            goodbye_channel_id INTEGER
        )
    ''')

    # 6. Bảng Tự động Trả lời (AutoRespond)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS autoresponses (
            guild_id INTEGER,
            trigger_word TEXT,
            response_text TEXT,
            image_url TEXT,
            UNIQUE(guild_id, trigger_word)
        )
    ''')

    # 7. Bảng Dữ liệu Người chơi Game RPG (Wistoria)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS WistoriaPlayers (
            user_id INTEGER PRIMARY KEY,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            credits INTEGER DEFAULT 500,
            faction TEXT,
            inventory TEXT DEFAULT '[]',
            current_floor INTEGER DEFAULT 1,
            last_dungeon_time TEXT DEFAULT '2000-01-01 00:00:00'
        )
    ''')

    # --- CẬP NHẬT CẤU TRÚC BẢNG CŨ (MIGRATIONS) ---
    try:
        cursor.execute('ALTER TABLE autoresponses ADD COLUMN image_url TEXT')
    except sqlite3.OperationalError:
        pass # Bỏ qua nếu cột đã tồn tại

    try:
        cursor.execute('ALTER TABLE welcome_settings ADD COLUMN goodbye_channel_id INTEGER')
    except sqlite3.OperationalError:
        pass # Bỏ qua nếu cột đã tồn tại

    conn.commit()
    conn.close()
    print("-> Đã kiểm tra và khởi tạo Database thành công!")


# ================= CÁC HÀM CẢNH BÁO (WARNINGS) =================

def add_warning(guild_id, user_id, moderator_id, reason):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO Warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)', 
        (guild_id, user_id, moderator_id, reason)
    )
    cursor.execute(
        'SELECT COUNT(*) FROM Warnings WHERE guild_id = ? AND user_id = ?', 
        (guild_id, user_id)
    )
    warn_count = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return warn_count

def get_warnings(guild_id, user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT warning_id, moderator_id, reason, timestamp FROM Warnings WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC', 
        (guild_id, user_id)
    )
    records = cursor.fetchall() 
    conn.close()
    return records

def clear_warnings(guild_id, user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM Warnings WHERE guild_id = ? AND user_id = ?', 
        (guild_id, user_id)
    )
    conn.commit()
    conn.close()

def remove_specific_warning(guild_id, warning_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM Warnings WHERE guild_id = ? AND warning_id = ?', 
        (guild_id, warning_id)
    )
    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0


# ================= CÁC HÀM TỪ CẤM (BADWORDS) =================

def get_badwords(guild_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT word FROM WordFilters WHERE guild_id = ?', (guild_id,))
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    return words

def add_badword(guild_id, word):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO WordFilters (guild_id, word) VALUES (?, ?)', 
            (guild_id, word.lower())
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_badword(guild_id, word):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM WordFilters WHERE guild_id = ? AND word = ?', 
        (guild_id, word.lower())
    )
    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0


# ================= CÁC HÀM CÀI ĐẶT (SETTINGS & PREFIX) =================

def set_log_channel(guild_id, channel_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO GuildSettings (guild_id, mod_log_channel_id) 
        VALUES (?, ?) 
        ON CONFLICT(guild_id) DO UPDATE SET mod_log_channel_id = ?
    ''', (guild_id, channel_id, channel_id))
    conn.commit()
    conn.close()

def get_log_channel(guild_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT mod_log_channel_id FROM GuildSettings WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_prefix(guild_id, prefix):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO GuildPrefixes (guild_id, prefix) 
        VALUES (?, ?) 
        ON CONFLICT(guild_id) DO UPDATE SET prefix = ?
    ''', (guild_id, prefix, prefix))
    conn.commit()
    conn.close()

def get_prefix(guild_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT prefix FROM GuildPrefixes WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "!"


# ================= CÁC HÀM CHÀO ĐÓN / TẠM BIỆT (WELCOME) =================

def set_welcome(guild_id, channel_id, msg, image):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO welcome_settings (guild_id, channel_id, welcome_msg, welcome_image)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET 
        channel_id = ?, welcome_msg = ?, welcome_image = ?
    ''', (guild_id, channel_id, msg, image, channel_id, msg, image))
    conn.commit()
    conn.close()

def set_goodbye(guild_id, channel_id, msg, image):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO welcome_settings (guild_id, goodbye_channel_id, goodbye_msg, goodbye_image)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET 
        goodbye_channel_id = ?, goodbye_msg = ?, goodbye_image = ?
    ''', (guild_id, channel_id, msg, image, channel_id, msg, image))
    conn.commit()
    conn.close()

def disable_welcome(guild_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE welcome_settings SET welcome_msg = NULL, welcome_image = NULL WHERE guild_id = ?', (guild_id,))
    conn.commit()
    conn.close()

def disable_goodbye(guild_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE welcome_settings SET goodbye_msg = NULL, goodbye_image = NULL WHERE guild_id = ?', (guild_id,))
    conn.commit()
    conn.close()

def get_welcome_config(guild_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT channel_id, welcome_msg, welcome_image, goodbye_channel_id, goodbye_msg, goodbye_image 
        FROM welcome_settings WHERE guild_id = ?
    ''', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "welcome_channel_id": result[0],
            "welcome_msg": result[1],
            "welcome_image": result[2],
            "goodbye_channel_id": result[3] if result[3] else result[0],
            "goodbye_msg": result[4],
            "goodbye_image": result[5]
        }
    return None


# ================= CÁC HÀM TRẢ LỜI TỰ ĐỘNG (AUTORESPOND) =================

def add_autoresponse(guild_id, trigger, response, image_url=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO autoresponses (guild_id, trigger_word, response_text, image_url)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(guild_id, trigger_word) DO UPDATE SET response_text = ?, image_url = ?
    ''', (guild_id, trigger.lower(), response, image_url, response, image_url))
    conn.commit()
    conn.close()

def remove_autoresponse(guild_id, trigger):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM autoresponses WHERE guild_id = ? AND trigger_word = ?', 
        (guild_id, trigger.lower())
    )
    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0

def get_autoresponses(guild_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT trigger_word, response_text, image_url FROM autoresponses WHERE guild_id = ?', 
        (guild_id,)
    )
    results = cursor.fetchall()
    conn.close()
    return results