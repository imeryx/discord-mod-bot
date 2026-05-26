import sqlite3

conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE PlayerInventory ADD COLUMN enhance_level INTEGER DEFAULT 1")
    print("✅ Đã thêm cột 'enhance_level' (Cấp Cường hóa) thành công!")
except sqlite3.OperationalError:
    print("⚠️ Cột 'enhance_level' đã tồn tại.")

try:
    cursor.execute("ALTER TABLE PlayerInventory ADD COLUMN weapon_exp INTEGER DEFAULT 0")
    print("✅ Đã thêm cột 'weapon_exp' (EXP Cường hóa) thành công!")
except sqlite3.OperationalError:
    print("⚠️ Cột 'weapon_exp' đã tồn tại.")

conn.commit()
conn.close()