import sqlite3

conn = sqlite3.connect('farmacia.db')
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(ventas)")
cols = [row[1] for row in cursor.fetchall()]
print('Columnas actuales:', cols)

if 'metodo_pago' not in cols:
    cursor.execute("ALTER TABLE ventas ADD COLUMN metodo_pago TEXT DEFAULT 'Efectivo'")
    conn.commit()
    print('OK: Columna metodo_pago agregada correctamente.')
else:
    print('ℹ️  La columna metodo_pago ya existe.')

conn.close()
