import sqlite3

conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE WistoriaPlayers ADD COLUMN last_daily_time TEXT DEFAULT '2000-01-01 00:00:00'")
    print("✅ Đã thêm cột 'last_daily_time' thành công!")
except sqlite3.OperationalError:
    print("⚠️ Cột đã tồn tại, bỏ qua.")

conn.commit()
conn.close()