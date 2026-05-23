import sqlite3

def setup_db():
    # Kết nối tới file database (hệ thống sẽ tự tạo file bot_database.db nếu chưa có)
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Bảng 1: Lưu Cấu hình riêng của từng Server (Guild)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS GuildSettings (
            guild_id INTEGER PRIMARY KEY,
            mod_log_channel_id INTEGER,
            welcome_channel_id INTEGER,
            mute_role_id INTEGER
        )
    ''')

    # Bảng 2: Lưu Lịch sử Cảnh báo (Warnings) của thành viên
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
    
    # Bảng 3: Lưu danh sách từ cấm của từng Server
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS WordFilters (
            guild_id INTEGER,
            word TEXT,
            UNIQUE(guild_id, word) 
        )
    ''')
    
    # Bảng 4: Lưu Prefix tùy chỉnh của từng server
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS GuildPrefixes (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT
        )
    ''')

    # Bảng 5 (MỚI THÊM): Lưu cấu hình hệ thống Chào đón / Tạm biệt (Welcome & Goodbye)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS welcome_settings (
            guild_id INTEGER PRIMARY KEY,
            channel_id INTEGER,
            welcome_msg TEXT,
            welcome_image TEXT,
            goodbye_msg TEXT,
            goodbye_image TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("-> Đã kiểm tra và khởi tạo Database thành công!")

# ================= CÁC HÀM XỬ LÝ CẢNH BÁO (WARNINGS) =================
def add_warning(guild_id, user_id, moderator_id, reason):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # 1. Ghi nhận cảnh báo mới
    cursor.execute('''
        INSERT INTO Warnings (guild_id, user_id, moderator_id, reason)
        VALUES (?, ?, ?, ?)
    ''', (guild_id, user_id, moderator_id, reason))
    
    # 2. Đếm tổng số cảnh báo hiện tại của người dùng này trong server
    cursor.execute('''
        SELECT COUNT(*) FROM Warnings 
        WHERE guild_id = ? AND user_id = ?
    ''', (guild_id, user_id))
    
    warn_count = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    return warn_count

def get_warnings(guild_id, user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT warning_id, moderator_id, reason, timestamp 
        FROM Warnings 
        WHERE guild_id = ? AND user_id = ?
        ORDER BY timestamp DESC
    ''', (guild_id, user_id))
    records = cursor.fetchall() 
    conn.close()
    return records

def clear_warnings(guild_id, user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM Warnings 
        WHERE guild_id = ? AND user_id = ?
    ''', (guild_id, user_id))
    conn.commit()
    conn.close()

def remove_specific_warning(guild_id, warning_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM Warnings 
        WHERE guild_id = ? AND warning_id = ?
    ''', (guild_id, warning_id))
    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0

# ================= CÁC HÀM XỬ LÝ TỪ CẤM (AUTOMOD) =================
def get_badwords(guild_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT word FROM WordFilters WHERE guild_id = ?', (guild_id,))
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    return words

def add_badword(guild_id, word):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO WordFilters (guild_id, word) VALUES (?, ?)', (guild_id, word.lower()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_badword(guild_id, word):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM WordFilters WHERE guild_id = ? AND word = ?', (guild_id, word.lower()))
    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_deleted > 0

# ================= CÁC HÀM CẤU HÌNH (CONFIG) =================
def set_log_channel(guild_id, channel_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO GuildSettings (guild_id, mod_log_channel_id)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET mod_log_channel_id = ?
    ''', (guild_id, channel_id, channel_id))
    conn.commit()
    conn.close()

def get_log_channel(guild_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT mod_log_channel_id FROM GuildSettings WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# ================= CÁC HÀM XỬ LÝ PREFIX =================
def set_prefix(guild_id, prefix):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO GuildPrefixes (guild_id, prefix)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET prefix = ?
    ''', (guild_id, prefix, prefix))
    conn.commit()
    conn.close()

def get_prefix(guild_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT prefix FROM GuildPrefixes WHERE guild_id = ?', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "!"


# ================= CÁC HÀM CẤU HÌNH WELCOME / GOODBYE =================
def save_welcome_config(guild_id, channel_id, welcome_msg, welcome_image, goodbye_msg, goodbye_image):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO welcome_settings (guild_id, channel_id, welcome_msg, welcome_image, goodbye_msg, goodbye_image)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (guild_id, channel_id, welcome_msg, welcome_image, goodbye_msg, goodbye_image))
    conn.commit()
    conn.close()

def get_welcome_config(guild_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT channel_id, welcome_msg, welcome_image, goodbye_msg, goodbye_image 
        FROM welcome_settings WHERE guild_id = ?
    ''', (guild_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "channel_id": result[0],
            "welcome_msg": result[1],
            "welcome_image": result[2],
            "goodbye_msg": result[3],
            "goodbye_image": result[4]
        }
    return None