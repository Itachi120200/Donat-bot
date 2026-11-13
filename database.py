import sqlite3

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            price REAL,
            image_url TEXT,
            is_popular INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            product_name TEXT,
            amount REAL,
            game_id TEXT,
            status TEXT,
            receipt_file_id TEXT
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ("Free Fire", "100 Almaz", 12000, "🔥", 1),
            ("Free Fire", "310 Almaz", 35000, "🔥", 0),
            ("PUBG Mobile", "60 UC", 14000, "⚡", 1),
            ("PUBG Mobile", "325 UC", 68000, "⚡", 0),
            ("Roblox", "400 Robux", 55000, "💎", 1),
            ("Telegram", "Telegram Stars (100)", 25000, "⭐", 1),
            ("Telegram", "Telegram Premium (1 oy)", 32000, "🚀", 1),
            ("Steam", "Steam Wallet $5", 65000, "🎮", 1),
            ("NFT", "MRKT Exclusive #1", 150, "🎨", 1)
        ]
        cursor.executemany("INSERT INTO products (category, name, price, image_url, is_popular) VALUES (?, ?, ?, ?, ?)", sample_products)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
  
