from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from config import Config
from database import db, init_db
from models import Producto, Venta, DetalleVenta, Compra, DetalleCompra, Usuario
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import json
import pandas as pd
from io import BytesIO
import io
from flask import send_file, make_response
import qrcode
import base64
from helpers import numero_a_letras


app = Flask(__name__)
app.config.from_object(Config)
init_db(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, inicie sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

app.jinja_env.globals.update(numero_a_letras=numero_a_letras)

with app.app_context():
    # Crear usuarios por defecto si no existen
    if not Usuario.query.filter_by(email='admin@farmacia.com').first():
        admin = Usuario(email='admin@farmacia.com', rol='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        
    if not Usuario.query.filter_by(email='usuario@farmacia.com').first():
        normal = Usuario(email='usuario@farmacia.com', rol='normal')
        normal.set_password('usuario123')
        db.session.add(normal)
        
    db.session.commit()
# ========================================================
#  AUTENTICACIÓN
# ========================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = Usuario.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ========================================================
#  DASHBOARD
# ========================================================
@app.route('/')
@login_required
def dashboard():
    total_productos = Producto.query.count()
    productos_stock_bajo = Producto.query.filter(Producto.stock <= Producto.stock_minimo, Producto.stock > 0).all()
    productos_sin_stock = Producto.query.filter(Producto.stock == 0).all()

    hoy = datetime.now().date()
    inicio_dia = datetime.combine(hoy, datetime.min.time())
    fin_dia = datetime.combine(hoy, datetime.max.time())

    ventas_hoy = Venta.query.filter(Venta.fecha.between(inicio_dia, fin_dia)).all()
    total_ventas_hoy = sum(v.total for v in ventas_hoy)
    num_ventas_hoy = len(ventas_hoy)

    costo_ventas_hoy = sum(d.cantidad * d.producto.precio_compra for v in ventas_hoy for d in v.detalles)
    ganancia_hoy = total_ventas_hoy - costo_ventas_hoy

    # Ventas últimos 7 días para gráfico
    ventas_semana = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        inicio = datetime.combine(dia, datetime.min.time())
        fin = datetime.combine(dia, datetime.max.time())
        total_dia = db.session.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.fecha.between(inicio, fin)
        ).scalar()
        ventas_semana.append({
            'dia': dia.strftime('%d/%m'),
            'total': float(total_dia)
        })

    # Productos más vendidos y menos vendidos (Top 5 / Bottom 5)
    # Total de cantidad vendida por producto
    ventas_por_producto = db.session.query(
        Producto.nombre,
        func.sum(DetalleVenta.cantidad).label('total_vendido')
    ).join(DetalleVenta, Producto.id == DetalleVenta.producto_id).group_by(Producto.nombre).subquery()

    top_productos = db.session.query(
        ventas_por_producto.c.nombre,
        ventas_por_producto.c.total_vendido
    ).order_by(ventas_por_producto.c.total_vendido.desc()).limit(5).all()

    bottom_productos = db.session.query(
        ventas_por_producto.c.nombre,
        ventas_por_producto.c.total_vendido
    ).order_by(ventas_por_producto.c.total_vendido.asc()).limit(5).all()

    umbral_vencimiento = hoy + timedelta(days=180)
    productos_proximos_vencer = Producto.query.filter(
        Producto.fecha_vencimiento != None,
        Producto.fecha_vencimiento <= umbral_vencimiento
    ).order_by(Producto.fecha_vencimiento.asc()).all()

    return render_template('dashboard.html',
                           total_productos=total_productos,
                           productos_stock_bajo=productos_stock_bajo,
                           productos_sin_stock=productos_sin_stock,
                           total_ventas_hoy=total_ventas_hoy,
                           num_ventas_hoy=num_ventas_hoy,
                           ganancia_hoy=ganancia_hoy,
                           ventas_semana=json.dumps(ventas_semana),
                           top_productos=top_productos,
                           bottom_productos=bottom_productos,
                           productos_proximos_vencer=productos_proximos_vencer,
                           hoy=hoy)


from sqlalchemy import func, extract, or_

# ========================================================
#  PRODUCTOS
# ========================================================
@app.route('/productos')
@login_required
def productos_lista():
    buscar = request.args.get('buscar', '')
    if buscar:
        productos = Producto.query.filter(or_(
            Producto.nombre.ilike(f'%{buscar}%'),
            Producto.categoria.ilike(f'%{buscar}%'),
            Producto.descripcion.ilike(f'%{buscar}%'),
            Producto.codigo_barras.ilike(f'%{buscar}%')
        )).all()
    else:
        productos = Producto.query.order_by(Producto.nombre).all()
    return render_template('productos/lista.html', productos=productos, buscar=buscar)


@app.route('/productos/nuevo', methods=['GET', 'POST'])
@login_required
def producto_nuevo():
    if not current_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'danger')
        return redirect(url_for('productos_lista'))
        
    if request.method == 'POST':
        fecha_venc = request.form.get('fecha_vencimiento')
        if fecha_venc:
            fecha_venc = datetime.strptime(fecha_venc, '%Y-%m-%d').date()
        else:
            fecha_venc = None
            
        precio_blister = request.form.get('precio_blister')
        precio_blister = float(precio_blister) if precio_blister else 0.0
        precio_caja = request.form.get('precio_caja')
        precio_caja = float(precio_caja) if precio_caja else 0.0

        producto = Producto(
            nombre=request.form['nombre'],
            descripcion=request.form.get('descripcion', ''),
            categoria=request.form.get('categoria', 'General'),
            lote=request.form.get('lote', ''),
            codigo_barras=request.form.get('codigo_barras', ''),
            precio_compra=float(request.form['precio_compra']),
            precio_venta=float(request.form['precio_venta']),
            stock=int(request.form.get('stock', 0)),
            stock_minimo=int(request.form.get('stock_minimo', 5)),
            fecha_vencimiento=fecha_venc,
            precio_blister=precio_blister,
            precio_caja=precio_caja
        )
        db.session.add(producto)
        db.session.commit()
        flash('✅ Producto creado exitosamente.', 'success')
        return redirect(url_for('productos_lista'))
    return render_template('productos/formulario.html', producto=None)


@app.route('/productos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def producto_editar(id):
    if not current_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'danger')
        return redirect(url_for('productos_lista'))
        
    producto = Producto.query.get_or_404(id)
    if request.method == 'POST':
        fecha_venc = request.form.get('fecha_vencimiento')
        if fecha_venc:
            fecha_venc = datetime.strptime(fecha_venc, '%Y-%m-%d').date()
        else:
            fecha_venc = None
            
        precio_blister = request.form.get('precio_blister')
        precio_blister = float(precio_blister) if precio_blister else 0.0
        precio_caja = request.form.get('precio_caja')
        precio_caja = float(precio_caja) if precio_caja else 0.0

        producto.nombre = request.form['nombre']
        producto.descripcion = request.form.get('descripcion', '')
        producto.categoria = request.form.get('categoria', 'General')
        producto.lote = request.form.get('lote', '')
        producto.codigo_barras = request.form.get('codigo_barras', '')
        producto.precio_compra = float(request.form['precio_compra'])
        producto.precio_venta = float(request.form['precio_venta'])
        producto.stock = int(request.form.get('stock', 0))
        producto.stock_minimo = int(request.form.get('stock_minimo', 5))
        producto.fecha_vencimiento = fecha_venc
        producto.precio_blister = precio_blister
        producto.precio_caja = precio_caja
        db.session.commit()
        flash('✅ Producto actualizado exitosamente.', 'success')
        return redirect(url_for('productos_lista'))
    return render_template('productos/formulario.html', producto=producto)


@app.route('/productos/<int:id>/eliminar', methods=['POST'])
@login_required
def producto_eliminar(id):
    if not current_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'danger')
        return redirect(url_for('productos_lista'))
        
    producto = Producto.query.get_or_404(id)
    try:
        # Eliminar detalles de venta y compra asociados
        DetalleVenta.query.filter_by(producto_id=id).delete()
        DetalleCompra.query.filter_by(producto_id=id).delete()
        db.session.delete(producto)
        db.session.commit()
        flash('Producto eliminado correctamente.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar el producto: ' + str(e), 'danger')
    return redirect(url_for('productos_lista'))


# ========================================================
#  VENTAS
# ========================================================
@app.route('/ventas')
@login_required
def ventas_lista():
    fecha_filtro = request.args.get('fecha')
    if fecha_filtro:
        try:
            fecha_obj = datetime.strptime(fecha_filtro, '%Y-%m-%d').date()
            inicio_dia = datetime.combine(fecha_obj, datetime.min.time())
            fin_dia = datetime.combine(fecha_obj, datetime.max.time())
            ventas = Venta.query.filter(Venta.fecha.between(inicio_dia, fin_dia)).order_by(Venta.fecha.desc()).all()
        except ValueError:
            ventas = Venta.query.order_by(Venta.fecha.desc()).all()
    else:
        ventas = Venta.query.order_by(Venta.fecha.desc()).all()
        
    total_efectivo = 0.0
    total_yape = 0.0
    total_tarjeta = 0.0

    for v in ventas:
        metodo = v.metodo_pago or 'Efectivo'
        if metodo == 'Yape':
            total_yape += v.total
        elif metodo == 'Tarjeta':
            total_tarjeta += v.total
        else:
            total_efectivo += v.total
            
    return render_template('ventas/lista.html', 
                           ventas=ventas, 
                           fecha_filtro=fecha_filtro,
                           total_efectivo=total_efectivo,
                           total_yape=total_yape,
                           total_tarjeta=total_tarjeta)


@app.route('/ventas/nueva', methods=['GET', 'POST'])
@login_required
def venta_nueva():
    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('items'):
            return jsonify({'error': 'No se recibieron productos'}), 400

        venta = Venta(
            cliente=data.get('cliente', 'Cliente General'),
            total=0,
            descuento=float(data.get('descuento', 0)),
            metodo_pago=data.get('metodo_pago', 'Efectivo')
        )
        db.session.add(venta)
        db.session.flush()

        total_venta = 0
        for item in data['items']:
            producto = Producto.query.get(item['producto_id'])
            if not producto:
                db.session.rollback()
                return jsonify({'error': f'Producto ID {item["producto_id"]} no encontrado'}), 400
            if producto.stock < item['cantidad']:
                db.session.rollback()
                return jsonify({'error': f'Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}'}), 400

            precio_usado = float(item.get('precio_unitario', producto.precio_venta))
            subtotal = item['cantidad'] * precio_usado
            detalle = DetalleVenta(
                venta_id=venta.id,
                producto_id=producto.id,
                cantidad=item['cantidad'],
                precio_unitario=precio_usado,
                subtotal=subtotal
            )
            db.session.add(detalle)
            producto.stock -= item['cantidad']
            total_venta += subtotal

        total_final = total_venta * (1 - venta.descuento / 100)
        venta.total = total_final
        db.session.commit()
        return jsonify({'success': True, 'venta_id': venta.id, 'total': total_final})

    productos = Producto.query.filter(Producto.stock > 0).order_by(Producto.nombre).all()
    return render_template('ventas/nueva.html', productos=productos)


@app.route('/ventas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def venta_editar(id):
    venta = Venta.query.get_or_404(id)

    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('items'):
            return jsonify({'error': 'No se recibieron productos'}), 400

        # Revertir stock de la venta anterior
        for detalle in venta.detalles:
            producto = Producto.query.get(detalle.producto_id)
            if producto:
                producto.stock += detalle.cantidad
        
        # Eliminar detalles anteriores
        DetalleVenta.query.filter_by(venta_id=venta.id).delete()
        
        # Actualizar datos de venta y crear nuevos detalles
        venta.cliente = data.get('cliente', 'Cliente General')
        venta.descuento = float(data.get('descuento', 0))
        venta.metodo_pago = data.get('metodo_pago', 'Efectivo')
        total_venta = 0
        
        for item in data['items']:
            producto = Producto.query.get(item['producto_id'])
            if not producto:
                db.session.rollback()
                return jsonify({'error': f'Producto ID {item["producto_id"]} no encontrado'}), 400
            
            if producto.stock < item['cantidad']:
                db.session.rollback()
                return jsonify({'error': f'Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}'}), 400

            precio_usado = float(item.get('precio_unitario', producto.precio_venta))
            subtotal = item['cantidad'] * precio_usado
            detalle = DetalleVenta(
                venta_id=venta.id,
                producto_id=producto.id,
                cantidad=item['cantidad'],
                precio_unitario=precio_usado,
                subtotal=subtotal
            )
            db.session.add(detalle)
            producto.stock -= item['cantidad']
            total_venta += subtotal

        total_final = total_venta * (1 - venta.descuento / 100)
        venta.total = total_final
        db.session.commit()
        return jsonify({'success': True, 'venta_id': venta.id, 'total': total_final})

    productos = Producto.query.filter(Producto.stock > 0).order_by(Producto.nombre).all()
    # Para la vista GET, necesitamos el estado actual del carrito
    carrito_actual = []
    for d in venta.detalles:
        # Añadir al stock actual la cantidad de la venta para saber el "stockMáximo" en edición
        stock_maximo = d.producto.stock + d.cantidad
        carrito_actual.append({
            'id': d.producto.id,
            'nombre': d.producto.nombre,
            'precio': d.precio_unitario,
            'cantidad': d.cantidad,
            'stockMax': stock_maximo
        })
    
    return render_template('ventas/editar.html', venta=venta, productos=productos, carrito_actual=json.dumps(carrito_actual))

@app.route('/ventas/<int:id>/eliminar', methods=['POST'])
@login_required
def venta_eliminar(id):
    if not current_user.is_admin:
        flash('No tienes permisos para realizar esta acción.', 'danger')
        return redirect(url_for('ventas_lista'))
        
    venta = Venta.query.get_or_404(id)
    try:
        # Revertir stock
        for detalle in venta.detalles:
            producto = Producto.query.get(detalle.producto_id)
            if producto:
                producto.stock += detalle.cantidad
        
        # Eliminar detalles de venta
        DetalleVenta.query.filter_by(venta_id=venta.id).delete()
        
        # Eliminar venta
        db.session.delete(venta)
        db.session.commit()
        flash('Venta eliminada correctamente y stock restaurado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar la venta: ' + str(e), 'danger')
    return redirect(url_for('ventas_lista'))

@app.route('/ventas/<int:id>')
@login_required
def venta_detalle(id):
    venta = Venta.query.get_or_404(id)
    return render_template('ventas/detalle.html', venta=venta)

@app.route('/ventas/<int:id>/imprimir_boleta')
@login_required
def venta_imprimir_boleta(id):
    venta = Venta.query.get_or_404(id)
    return render_template('ventas/boleta.html', venta=venta)

@app.route('/ventas/<int:id>/imprimir_factura')
@login_required
def venta_imprimir_factura(id):
    venta = Venta.query.get_or_404(id)
    return render_template('ventas/factura.html', venta=venta)

@app.route('/ventas/exportar')
@login_required
def ventas_exportar():
    ventas = Venta.query.order_by(Venta.fecha.desc()).all()
    
    data = []
    for v in ventas:
        for d in v.detalles:
            data.append({
                'ID Venta': v.id,
                'Fecha': v.fecha.strftime('%Y-%m-%d %H:%M:%S'),
                'Cliente': v.cliente,
                'Producto ID': d.producto_id,
                'Producto': d.producto.nombre,
                'Cantidad': d.cantidad,
                'Precio Unitario': d.precio_unitario,
                'Subtotal': d.subtotal,
                'Total Venta': v.total
            })

    if not data:
        flash('No hay ventas para exportar.', 'warning')
        return redirect(url_for('ventas_lista'))

    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Ventas')
        
        # Ajustar el ancho de las columnas
        worksheet = writer.sheets['Ventas']
        for idx, col in enumerate(df.columns):
            max_len = max(
                df[col].astype(str).map(len).max(),
                len(str(col))
            ) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = max_len

    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'ventas_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ========================================================
#  COMPRAS
# ========================================================
@app.route('/compras')
@login_required
def compras_lista():
    compras = Compra.query.order_by(Compra.fecha.desc()).all()
    return render_template('compras/lista.html', compras=compras)


@app.route('/compras/nueva', methods=['GET', 'POST'])
@login_required
def compra_nueva():
    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('items'):
            return jsonify({'error': 'No se recibieron productos'}), 400

        compra = Compra(
            proveedor=data.get('proveedor', 'Proveedor General'),
            total=0
        )
        db.session.add(compra)
        db.session.flush()

        total_compra = 0
        for item in data['items']:
            producto = Producto.query.get(item['producto_id'])
            if not producto:
                db.session.rollback()
                return jsonify({'error': f'Producto ID {item["producto_id"]} no encontrado'}), 400

            precio = float(item.get('precio_unitario', producto.precio_compra))
            subtotal = item['cantidad'] * precio
            detalle = DetalleCompra(
                compra_id=compra.id,
                producto_id=producto.id,
                cantidad=item['cantidad'],
                precio_unitario=precio,
                subtotal=subtotal
            )
            db.session.add(detalle)
            producto.stock += item['cantidad']
            total_compra += subtotal

        compra.total = total_compra
        db.session.commit()
        return jsonify({'success': True, 'compra_id': compra.id, 'total': total_compra})

    productos = Producto.query.order_by(Producto.nombre).all()
    return render_template('compras/nueva.html', productos=productos)


# ========================================================
#  REPORTES
# ========================================================
@app.route('/reportes')
@login_required
def reportes():
    return render_template('reportes/reportes.html')


@app.route('/api/reportes/<tipo>')
@login_required
def api_reportes(tipo):
    hoy = datetime.now().date()

    if tipo == 'diario':
        # Ventas por hora del día actual
        inicio = datetime.combine(hoy, datetime.min.time())
        fin = datetime.combine(hoy, datetime.max.time())
        ventas = Venta.query.filter(Venta.fecha.between(inicio, fin)).all()

        datos_por_hora = {}
        for v in ventas:
            hora = v.fecha.strftime('%H:00')
            datos_por_hora[hora] = datos_por_hora.get(hora, 0) + v.total

        labels = [f'{h:02d}:00' for h in range(24)]
        valores = [datos_por_hora.get(l, 0) for l in labels]

        total = sum(valores)
        num_ventas = len(ventas)

    elif tipo == 'semanal':
        # Ventas por día de la semana actual
        inicio_semana = hoy - timedelta(days=hoy.weekday())
        labels = []
        valores = []
        dias_nombre = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

        for i in range(7):
            dia = inicio_semana + timedelta(days=i)
            inicio = datetime.combine(dia, datetime.min.time())
            fin = datetime.combine(dia, datetime.max.time())
            total_dia = db.session.query(func.coalesce(func.sum(Venta.total), 0)).filter(
                Venta.fecha.between(inicio, fin)
            ).scalar()
            labels.append(f'{dias_nombre[i]} {dia.strftime("%d/%m")}')
            valores.append(float(total_dia))

        total = sum(valores)
        num_ventas = Venta.query.filter(
            Venta.fecha >= datetime.combine(inicio_semana, datetime.min.time())
        ).count()

    elif tipo == 'mensual':
        # Acepta mes y anio como parámetros opcionales (?mes=5&anio=2026)
        mes_param = request.args.get('mes', type=int, default=hoy.month)
        anio_param = request.args.get('anio', type=int, default=hoy.year)
        try:
            inicio_mes = hoy.replace(year=anio_param, month=mes_param, day=1)
        except ValueError:
            inicio_mes = hoy.replace(day=1)
        if inicio_mes.month == 12:
            fin_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            fin_mes = inicio_mes.replace(month=inicio_mes.month + 1, day=1) - timedelta(days=1)

        labels = []
        valores = []
        dia_actual = inicio_mes
        while dia_actual <= fin_mes:
            inicio = datetime.combine(dia_actual, datetime.min.time())
            fin = datetime.combine(dia_actual, datetime.max.time())
            total_dia = db.session.query(func.coalesce(func.sum(Venta.total), 0)).filter(
                Venta.fecha.between(inicio, fin)
            ).scalar()
            labels.append(dia_actual.strftime('%d'))
            valores.append(float(total_dia))
            dia_actual += timedelta(days=1)

        total = sum(valores)
        num_ventas = Venta.query.filter(
            Venta.fecha >= datetime.combine(inicio_mes, datetime.min.time()),
            Venta.fecha <= datetime.combine(fin_mes, datetime.max.time())
        ).count()

    elif tipo == 'anual':
        # Ventas por mes del año actual
        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
        labels = meses
        valores = []

        for m in range(1, 13):
            total_mes = db.session.query(func.coalesce(func.sum(Venta.total), 0)).filter(
                extract('year', Venta.fecha) == hoy.year,
                extract('month', Venta.fecha) == m
            ).scalar()
            valores.append(float(total_mes))

        total = sum(valores)
        num_ventas = Venta.query.filter(
            extract('year', Venta.fecha) == hoy.year
        ).count()

    else:
        return jsonify({'error': 'Tipo de reporte no válido'}), 400

    # Top 5 productos más vendidos en el período
    top_productos = []
    if tipo == 'diario':
        inicio_periodo = datetime.combine(hoy, datetime.min.time())
        fin_periodo = datetime.combine(hoy, datetime.max.time())
    elif tipo == 'semanal':
        inicio_periodo = datetime.combine(inicio_semana, datetime.min.time())
        fin_periodo = datetime.combine(inicio_semana + timedelta(days=6), datetime.max.time())
    elif tipo == 'mensual':
        inicio_periodo = datetime.combine(inicio_mes, datetime.min.time())
        fin_periodo = datetime.combine(fin_mes, datetime.max.time())
    else:
        inicio_periodo = datetime.combine(hoy.replace(month=1, day=1), datetime.min.time())
        fin_periodo = datetime.combine(hoy.replace(month=12, day=31), datetime.max.time())

    top_query = db.session.query(
        Producto.nombre,
        func.sum(DetalleVenta.cantidad).label('total_cantidad'),
        func.sum(DetalleVenta.subtotal).label('total_ingreso')
    ).join(DetalleVenta, Producto.id == DetalleVenta.producto_id
    ).join(Venta, DetalleVenta.venta_id == Venta.id
    ).filter(Venta.fecha.between(inicio_periodo, fin_periodo)
    ).group_by(Producto.id
    ).order_by(func.sum(DetalleVenta.cantidad).desc()
    ).limit(5).all()

    costo_periodo = db.session.query(
        func.coalesce(func.sum(DetalleVenta.cantidad * Producto.precio_compra), 0)
    ).join(Venta, DetalleVenta.venta_id == Venta.id
    ).join(Producto, DetalleVenta.producto_id == Producto.id
    ).filter(Venta.fecha.between(inicio_periodo, fin_periodo)
    ).scalar()

    ganancia = float(total) - float(costo_periodo)

    for p in top_query:
        top_productos.append({
            'nombre': p.nombre,
            'cantidad': int(p.total_cantidad),
            'ingreso': float(p.total_ingreso)
        })

    # Ventas por método de pago
    ventas_por_metodo = db.session.query(
        func.coalesce(Venta.metodo_pago, 'Efectivo').label('metodo'),
        func.sum(Venta.total).label('total')
    ).filter(Venta.fecha.between(inicio_periodo, fin_periodo)
    ).group_by(func.coalesce(Venta.metodo_pago, 'Efectivo')).all()

    pagos = {
        'Efectivo': 0.0,
        'Yape': 0.0,
        'Tarjeta': 0.0
    }
    for m in ventas_por_metodo:
        if m.metodo in pagos:
            pagos[m.metodo] = float(m.total)

    return jsonify({
        'labels': labels,
        'valores': valores,
        'total': float(total),
        'num_ventas': int(num_ventas),
        'ganancia': float(ganancia),
        'top_productos': top_productos,
        'pagos': pagos
    })


# ========================================================
#  API - Obtener productos (para autocompletar)
# ========================================================
@app.route('/api/productos')
@login_required
def api_productos():
    productos = Producto.query.order_by(Producto.nombre).all()
    return jsonify([{
        'id': p.id,
        'nombre': p.nombre,
        'codigo_barras': p.codigo_barras,
        'precio_venta': p.precio_venta,
        'precio_compra': p.precio_compra,
        'precio_blister': p.precio_blister or 0,
        'precio_caja': p.precio_caja or 0,
        'categoria': p.categoria or 'General',
        'stock': p.stock
    } for p in productos])

# ========================================================
#  API - Generar QR
# ========================================================
@app.route('/api/qr/<path:data>')
def generar_qr(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=0,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    response = make_response(send_file(img_io, mimetype='image/png'))
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
