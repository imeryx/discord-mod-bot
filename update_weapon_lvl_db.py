import sqlite3

conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE PlayerInventory ADD COLUMN weapon_level INTEGER DEFAULT 1")
    print("✅ Đã thêm cột 'weapon_level' vào bảng PlayerInventory thành công!")
except sqlite3.OperationalError:
    print("⚠️ Cột 'weapon_level' đã tồn tại, bỏ qua.")

conn.commit()
conn.close()