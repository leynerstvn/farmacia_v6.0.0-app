# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine, MetaData, text

def migrate():
    print("Iniciando migración de SQLite a MySQL...")
    
    # Origen (SQLite) y Destino (MySQL)
    sqlite_uri = 'sqlite:///farmacia.db'
    mysql_uri = 'mysql+pymysql://root:@localhost/farmacia_db'
    
    sqlite_engine = create_engine(sqlite_uri)
    mysql_engine = create_engine(mysql_uri)
    
    # Leer la estructura de la base de datos desde SQLite
    metadata = MetaData()
    metadata.reflect(bind=sqlite_engine)
    
    # Crear las mismas tablas en MySQL si no existen
    metadata.create_all(bind=mysql_engine)
    
    # Mover los datos tabla por tabla
    with sqlite_engine.connect() as sqlite_conn:
        with mysql_engine.begin() as mysql_conn:
            
            # Desactivar comprobación de llaves foráneas para evitar errores de orden
            mysql_conn.execute(text("SET FOREIGN_KEY_CHECKS=0;"))
            
            for table in metadata.sorted_tables:
                print(f"Migrando tabla: {table.name}...")
                
                # Limpiar la tabla en MySQL por si ya tenía datos de prueba
                mysql_conn.execute(table.delete())
                
                # Traer todos los datos de esta tabla desde SQLite
                rows = sqlite_conn.execute(table.select()).mappings().all()
                
                # Insertarlos en MySQL
                if rows:
                    # Convertimos los mappings a diccionarios estándar para mayor compatibilidad
                    datos = [dict(row) for row in rows]
                    mysql_conn.execute(table.insert(), datos)
                    print(f" -> {len(rows)} filas insertadas.")
                else:
                    print(" -> 0 filas insertadas.")
                    
            # Reactivar comprobación de llaves foráneas
            mysql_conn.execute(text("SET FOREIGN_KEY_CHECKS=1;"))
            
    print("\n¡Migración completada exitosamente!")
    print("Todos tus datos (usuarios, productos, ventas) ya están en MySQL.")

if __name__ == '__main__':
    try:
        migrate()
    except Exception as e:
        print(f"Error durante la migración: {e}")
