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

    conn.commit()
    conn.close()
    print("-> Đã kiểm tra và khởi tạo Database thành công!")
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
    
    # Trả về con số đếm được để Bot xử lý logic phạt
    return warn_count

def get_warnings(guild_id, user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Truy vấn lấy ID người phạt, lý do và thời gian
    cursor.execute('''
        SELECT warning_id, moderator_id, reason, timestamp 
        FROM Warnings 
        WHERE guild_id = ? AND user_id = ?
        ORDER BY timestamp DESC
    ''', (guild_id, user_id))
    
    # fetchall() sẽ trả về một danh sách (list) chứa các kết quả
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
# Lấy danh sách từ cấm của một server
def get_badwords(guild_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT word FROM WordFilters WHERE guild_id = ?', (guild_id,))
    # Trả về một danh sách (list) các từ, thay vì list các tuple
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    return words

# Thêm từ cấm mới
def add_badword(guild_id, word):
    try:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO WordFilters (guild_id, word) VALUES (?, ?)', (guild_id, word.lower()))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False # Trả về False nếu từ này đã tồn tại trong database của server đó

# Xóa từ cấm
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
    
    # Insert dữ liệu mới, nếu guild_id đã tồn tại thì Update cột mod_log_channel_id
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
    
    # Nếu có kết quả thì trả về ID (nằm ở vị trí đầu tiên của tuple), nếu không thì trả về None
    return result[0] if result else None
# Thêm vào cuối file database.py
def remove_specific_warning(guild_id, warning_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Xóa dựa trên đúng ID của cảnh báo và ID của server
    cursor.execute('''
        DELETE FROM Warnings 
        WHERE guild_id = ? AND warning_id = ?
    ''', (guild_id, warning_id))
    
    rows_deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    # Trả về True nếu xóa thành công (có ít nhất 1 dòng bị ảnh hưởng), ngược lại là False
    return rows_deleted > 0
# ================= CÁC HÀM XỬ LÝ PREFIX =================
def set_prefix(guild_id, prefix):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    # Dùng ON CONFLICT để tự động Update nếu server đã từng set prefix
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
    # Nếu server chưa cài, mặc định trả về dấu chấm than "!"
    return result[0] if result else "!"