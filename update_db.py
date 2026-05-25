import sqlite3

def update_database():
    # Kết nối vào database hiện tại của bạn
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    print("Đang tiến hành nâng cấp Database...")

    # 1. Thêm cột 'equipped_weapon' vào bảng người chơi
    try:
        # Tạm thời gán mặc định là w_broken_branch, lát nữa vào game sẽ xử lý chuẩn theo hệ phái sau
        cursor.execute("ALTER TABLE WistoriaPlayers ADD COLUMN equipped_weapon TEXT DEFAULT 'w_broken_branch'")
        print("✅ Đã thêm cột 'equipped_weapon' thành công.")
    except sqlite3.OperationalError:
        print("⚠️ Cột 'equipped_weapon' đã tồn tại, bỏ qua bước này.")

    # 2. Tạo bảng Kho đồ (PlayerInventory)
    # Khóa chính (PRIMARY KEY) là sự kết hợp của user_id và weapon_key 
    # để đảm bảo mỗi người chỉ có 1 dòng cho mỗi loại vũ khí (số lượng sẽ cộng dồn vào cột quantity)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PlayerInventory (
        user_id INTEGER,
        weapon_key TEXT,
        quantity INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, weapon_key)
    )
    ''')
    print("✅ Đã tạo/kiểm tra bảng 'PlayerInventory' thành công.")

    # Lưu thay đổi và đóng kết nối
    conn.commit()
    conn.close()
    print("🎉 Nâng cấp Database hoàn tất! Dữ liệu cũ an toàn 100%.")

if __name__ == "__main__":
    update_database()