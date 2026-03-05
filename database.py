from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """Inicializar la base de datos con la aplicación Flask."""
    db.init_app(app)
    with app.app_context():
        import models  # noqa: F401
        db.create_all()
        print("[OK] Base de datos inicializada correctamente.")
