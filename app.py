from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
import pg8000
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_casa_antigua_2026'

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# ==========================================
# CONEXIÓN A POSTGRESQL
# ==========================================
def obtener_conexion():
    return pg8000.connect(
        user=os.environ.get("PGUSER"),
        password=os.environ.get("PGPASSWORD"),
        host=os.environ.get("PGHOST"),
        database=os.environ.get("PGDATABASE"),
        port=int(os.environ.get("PGPORT", 5432)),
        timeout=10
    )

# Inicializar tablas y asegurar columnas en la base de datos
def inicializar_bd():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                categoria TEXT NOT NULL,
                precio NUMERIC(12, 2) NOT NULL,
                stock INTEGER NOT NULL,
                imagen TEXT
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas_diarias (
                id SERIAL PRIMARY KEY,
                producto TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                total NUMERIC(12, 2) NOT NULL,
                usuario TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial (
                id SERIAL PRIMARY KEY,
                accion TEXT NOT NULL,
                producto TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                usuario TEXT NOT NULL,
                total NUMERIC(12, 2) DEFAULT 0,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Por si la tabla ya existía sin la columna total, la agregamos de forma segura:
        cursor.execute("""
            ALTER TABLE historial ADD COLUMN IF NOT EXISTS total NUMERIC(12, 2) DEFAULT 0;
        """)
        
        conexion.commit()
        cursor.close()
        conexion.close()
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")

# Ejecutar inicialización al arrancar
inicializar_bd()

fecha_actual_sistema = datetime.now().strftime("%Y-%m-%d")

def verificar_cambio_dia():
    global fecha_actual_sistema
    hoy = datetime.now().strftime("%Y-%m-%d")
    if hoy != fecha_actual_sistema:
        fecha_actual_sistema = hoy
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute("DELETE FROM ventas_diarias;")
            conexion.commit()
            cursor.close()
            conexion.close()
        except Exception:
            pass

@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip().lower()
        contrasena = request.form.get('contrasena', '').strip()
        
        if not usuario or not contrasena:
            flash("Por favor rellene todos los campos", "danger")
            return redirect(url_for('login'))
        
        session['usuario'] = usuario
        if usuario == 'admin':
            session['rol'] = 'admin'
        else:
            session['rol'] = 'empleado'
            
        return redirect(url_for('panel'))
            
    return render_template('login.html')

@app.route('/panel')
def panel():
    if 'usuario' not in session:
        flash("Por favor inicia sesión primero", "danger")
        return redirect(url_for('login'))
        
    verificar_cambio_dia()
    query = request.args.get('q', '').strip().lower()
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    productos = []
    if query:
        cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos WHERE LOWER(nombre) LIKE %s OR LOWER(categoria) LIKE %s;", (f"%{query}%", f"%{query}%"))
    else:
        cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos;")
        
    for fila in cursor.fetchall():
        productos.append({
            "id": fila[0], "nombre": fila[1], "categoria": fila[2],
            "precio": float(fila[3]), "stock": fila[4], "imagen": fila[5]
        })
        
    ventas_del_dia = []
    cursor.execute("SELECT producto, cantidad, usuario, total FROM ventas_diarias ORDER BY id DESC;")
    for v in cursor.fetchall():
        ventas_del_dia.append({
            "producto": v[0], "cantidad": v[1], "usuario": v[2], "total": float(v[3])
        })
        
    historial_permanente = []
    cursor.execute("SELECT fecha, accion, producto, cantidad, usuario, total FROM historial ORDER BY id DESC;")
    for h in cursor.fetchall():
        historial_permanente.append({
            "fecha": str(h[0]), "accion": h[1], "producto": h[2],
            "cantidad": h[3], "usuario": h[4], "total": float(h[5]) if h[5] is not None else 0
        })
        
    cursor.close()
    conexion.close()
    
    total_dinero_hoy = sum(v['total'] for v in ventas_del_dia)
    
    return render_template(
        'index.html', 
        productos=productos, 
        ventas_del_dia=ventas_del_dia,
        historial_permanente=historial_permanente,
        total_dinero_hoy=total_dinero_hoy,
        busqueda=query
    )

@app.route('/catalogo')
def catalogo():
    query = request.args.get('q', '').strip().lower()
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    productos = []
    if query:
        cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos WHERE LOWER(nombre) LIKE %s OR LOWER(categoria) LIKE %s;", (f"%{query}%", f"%{query}%"))
    else:
        cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos;")
        
    for fila in cursor.fetchall():
        productos.append({
            "id": fila[0], "nombre": fila[1], "categoria": fila[2],
            "precio": float(fila[3]), "stock": fila[4], "imagen": fila[5]
        })
        
    cursor.close()
    conexion.close()
    
    return render_template('catalogo.html', productos=productos, busqueda=query)

@app.route('/agregar', methods=['POST'])
def agregar():
    if 'usuario' not in session or session.get('rol') != 'admin':
        return redirect(url_for('panel'))
        
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria', 'GENERAL').upper()
    imagen = request.form.get('imagen', '').strip()
    
    try:
        precio = float(request.form.get('precio', 0))
        stock = int(request.form.get('stock', 0))
    except ValueError:
        precio, stock = 0.0, 0
    
    if not imagen:
        imagen = "https://via.placeholder.com/400x200?text=" + nombre.replace(" ", "+")
    
    if nombre:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("INSERT INTO productos (nombre, categoria, precio, stock, imagen) VALUES (%s, %s, %s, %s, %s);",
                       (nombre, categoria, precio, stock, imagen))
        
        fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("INSERT INTO historial (accion, producto, cantidad, usuario, total, fecha) VALUES (%s, %s, %s, %s, %s, %s);",
                       ('Creación Inventario', nombre, stock, session.get('usuario'), 0, fecha_str))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        
    return redirect(url_for('panel'))

@app.route('/vender/<int:prod_id>', methods=['POST'])
def vender(prod_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    verificar_cambio_dia()
    
    try:
        cantidad = int(request.form.get('cantidad', 1))
    except ValueError:
        cantidad = 1
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id = %s;", (prod_id,))
    prod = cursor.fetchone()
    
    if prod:
        nombre, precio, stock = prod[0], float(prod[1]), prod[2]
        if stock >= cantidad:
            nuevo_stock = stock - cantidad
            total_venta = precio * cantidad
            fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            cursor.execute("UPDATE productos SET stock = %s WHERE id = %s;", (nuevo_stock, prod_id))
            cursor.execute("INSERT INTO ventas_diarias (producto, cantidad, total, usuario, fecha) VALUES (%s, %s, %s, %s, %s);",
                           (nombre, cantidad, total_venta, session.get('usuario'), fecha_str))
            cursor.execute("INSERT INTO historial (accion, producto, cantidad, usuario, total, fecha) VALUES (%s, %s, %s, %s, %s, %s);",
                           ('Venta', nombre, cantidad, session.get('usuario'), total_venta, fecha_str))
            
            conexion.commit()
            
    cursor.close()
    conexion.close()
    return redirect(url_for('panel'))

@app.route('/incrementar/<int:prod_id>', methods=['POST'])
def incrementar(prod_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    try:
        cantidad = int(request.form.get('cantidad', 1))
    except ValueError:
        cantidad = 1
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT nombre, stock FROM productos WHERE id = %s;", (prod_id,))
    prod = cursor.fetchone()
    
    if prod:
        nombre, stock = prod[0], prod[1]
        nuevo_stock = stock + cantidad
        fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute("UPDATE productos SET stock = %s WHERE id = %s;", (nuevo_stock, prod_id))
        cursor.execute("INSERT INTO historial (accion, producto, cantidad, usuario, total, fecha) VALUES (%s, %s, %s, %s, %s, %s);",
                       ('Incremento Stock', nombre, cantidad, session.get('usuario'), 0, fecha_str))
        
        conexion.commit()
        
    cursor.close()
    conexion.close()
    return redirect(url_for('panel'))

@app.route('/eliminar/<int:prod_id>')
def eliminar(prod_id):
    if 'usuario' not in session or session.get('rol') != 'admin':
        return redirect(url_for('panel'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("DELETE FROM productos WHERE id = %s;", (prod_id,))
    conexion.commit()
    
    cursor.close()
    conexion.close()
    return redirect(url_for('panel'))

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('rol', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)