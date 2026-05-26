import sqlite3

def update_database():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    print("Đang tạo Túi Vật Liệu...")

    # Tạo bảng PlayerMaterials
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PlayerMaterials (
        user_id INTEGER,
        material_key TEXT,
        quantity INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, material_key)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Đã tạo bảng 'PlayerMaterials' thành công!")

if __name__ == "__main__":
    update_database()