"""
Script para agregar la columna unidades_descontadas a la tabla detalle_ventas.
Ejecutar una sola vez para migrar la base de datos existente.
"""
import sqlite3

DB_PATH = 'farmacia.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Verificar si las columnas ya existen
cursor.execute("PRAGMA table_info(detalle_ventas)")
columnas = [col[1] for col in cursor.fetchall()]

if 'unidades_descontadas' not in columnas:
    cursor.execute("ALTER TABLE detalle_ventas ADD COLUMN unidades_descontadas INTEGER DEFAULT 0")
    # Para los registros antiguos, asumimos que unidades_descontadas = cantidad
    cursor.execute("UPDATE detalle_ventas SET unidades_descontadas = cantidad")
    print("[OK] Columna 'unidades_descontadas' agregada correctamente.")
else:
    print("[INFO] Columna 'unidades_descontadas' ya existe.")

conn.commit()
conn.close()
print("\n[DONE] Migracion completada exitosamente.")
