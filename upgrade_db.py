import sqlite3

def upgrade():
    try:
        conn = sqlite3.connect('farmacia.db')
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE productos ADD COLUMN codigo_barras VARCHAR(100);")
        cursor.execute("CREATE INDEX idx_productos_codigo_barras ON productos (codigo_barras);")
        conn.commit()
        print("Successfully added codigo_barras to productos table.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    upgrade()
