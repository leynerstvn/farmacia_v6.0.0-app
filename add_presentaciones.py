"""
Script para agregar columnas de presentación (precio_blister, precio_caja) a la tabla productos.
Ejecutar una sola vez para migrar la base de datos existente.
"""
import sqlite3

DB_PATH = 'farmacia.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Verificar si las columnas ya existen
cursor.execute("PRAGMA table_info(productos)")
columnas = [col[1] for col in cursor.fetchall()]

if 'precio_blister' not in columnas:
    cursor.execute("ALTER TABLE productos ADD COLUMN precio_blister FLOAT DEFAULT 0.0")
    print("[OK] Columna 'precio_blister' agregada correctamente.")
else:
    print("[INFO] Columna 'precio_blister' ya existe.")

if 'precio_caja' not in columnas:
    cursor.execute("ALTER TABLE productos ADD COLUMN precio_caja FLOAT DEFAULT 0.0")
    print("[OK] Columna 'precio_caja' agregada correctamente.")
else:
    print("[INFO] Columna 'precio_caja' ya existe.")

conn.commit()
conn.close()
print("\n[DONE] Migracion completada exitosamente.")
