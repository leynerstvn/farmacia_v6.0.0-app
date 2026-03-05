from datetime import datetime
from database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Producto(db.Model):
    __tablename__ = 'productos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.String(100), nullable=True, default='General')
    lote = db.Column(db.String(100), nullable=True)
    precio_compra = db.Column(db.Float, nullable=False, default=0.0)
    precio_venta = db.Column(db.Float, nullable=False, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    stock_minimo = db.Column(db.Integer, nullable=False, default=5)
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    detalles_venta = db.relationship('DetalleVenta', backref='producto', lazy=True)
    detalles_compra = db.relationship('DetalleCompra', backref='producto', lazy=True)

    def __repr__(self):
        return f'<Producto {self.nombre}>'

    @property
    def stock_bajo(self):
        return self.stock <= self.stock_minimo


class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='normal') # admin o normal
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.rol == 'admin'

    def __repr__(self):
        return f'<Usuario {self.email}>'


class Venta(db.Model):
    __tablename__ = 'ventas'

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    cliente = db.Column(db.String(200), nullable=True, default='Cliente General')
    total = db.Column(db.Float, nullable=False, default=0.0)

    detalles = db.relationship('DetalleVenta', backref='venta', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Venta #{self.id} - {self.total}>'


class DetalleVenta(db.Model):
    __tablename__ = 'detalle_ventas'

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey('ventas.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<DetalleVenta {self.producto_id} x{self.cantidad}>'


class Compra(db.Model):
    __tablename__ = 'compras'

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    proveedor = db.Column(db.String(200), nullable=True, default='Proveedor General')
    total = db.Column(db.Float, nullable=False, default=0.0)

    detalles = db.relationship('DetalleCompra', backref='compra', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Compra #{self.id} - {self.total}>'


class DetalleCompra(db.Model):
    __tablename__ = 'detalle_compras'

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('compras.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<DetalleCompra {self.producto_id} x{self.cantidad}>'
