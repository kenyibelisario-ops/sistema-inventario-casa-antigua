import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import DictCursor

app = Flask(__name__)
app.secret_key = 'clave_secreta_casa_antigua'

# Tu URL de conexión interna de Render integrada directamente
URL_BASE_DATOS = "postgresql://avnadmin:3HUKlHpqIidKR5nM0nPDN69W1Dq7kJ1G@dpg-d9f7blnavr4c73c9u29g-a/casaantigua_db"

def obtener_conexion():
    return psycopg2.connect(URL_BASE_DATOS)

# CREACIÓN AUTOMÁTICA DE TABLAS AL ARRANCAR
def inicializar_base_datos():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Tabla de productos (Serial reemplaza a AUTO_INCREMENT)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                categoria VARCHAR(100) NOT NULL,
                precio DECIMAL(10, 2) NOT NULL,
                stock INT NOT NULL,
                ruta_img TEXT
            );
        """)
        
        # Tabla de ventas e historial
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id SERIAL PRIMARY KEY,
                producto_nombre VARCHAR(255) NOT NULL,
                cantidad INT NOT NULL,
                total_venta DECIMAL(10, 2) NOT NULL,
                usuario_accion VARCHAR(100) NOT NULL,
                tipo_movimiento VARCHAR(50) NOT NULL,
                fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conexion.commit()
        cursor.close()
        conexion.close()
        print("Base de datos inicializada correctamente.")
    except Exception as e:
        print(f"Error al conectar o inicializar la base de datos: {e}")

# Inicializar tablas de forma automática
inicializar_base_datos()

@app.route('/')
def login():
    if 'usuario' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def procesar_login():
    usuario = request.form.get('usuario')
    contrasena = request.form.get('contrasena')
    
    if usuario == 'admin' and contrasena == 'Antigua2026':
        session['usuario'] = usuario
        session['rol'] = 'admin'
        return redirect(url_for('index'))
    elif usuario == 'empleado' and contrasena == 'Cafecito2026':
        session['usuario'] = usuario
        session['rol'] = 'empleado'
        return redirect(url_for('index'))
    else:
        flash('Credenciales incorrectas', 'danger')
        return redirect(url_for('login'))

@app.route('/index')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=DictCursor)
    
    # Obtener productos
    cursor.execute("SELECT id, nombre, categoria, precio, stock, ruta_img FROM productos ORDER BY id DESC")
    productos = cursor.fetchall()
    
    # Ventas de hoy
    cursor.execute("""
        SELECT producto_nombre, cantidad, total_venta, usuario_accion, tipo_movimiento, 
               TO_CHAR(fecha_hora, 'HH24:MI') as hora 
        FROM ventas 
        WHERE fecha_hora::date = CURRENT_DATE 
        ORDER BY id DESC
    """)
    ventas_hoy = cursor.fetchall()
    
    # Historial Permanente
    cursor.execute("""
        SELECT producto_nombre, cantidad, total_venta, usuario_accion, tipo_movimiento, 
               TO_CHAR(fecha_hora, 'DD/MM/YYYY HH24:MI') as fecha 
        FROM ventas 
        ORDER BY id DESC
    """)
    historial_permanente = cursor.fetchall()
    
    # Total Caja Hoy
    cursor.execute("SELECT COALESCE(SUM(total_venta), 0) FROM ventas WHERE fecha_hora::date = CURRENT_DATE AND tipo_movimiento = 'VENTA'")
    total_dia = cursor.fetchone()[0]
    
    # Datos para el gráfico circular
    cursor.execute("""
        SELECT producto_nombre, SUM(cantidad) 
        FROM ventas 
        WHERE tipo_movimiento = 'VENTA' 
        GROUP BY producto_nombre
    """)
    grafico_data = cursor.fetchall()
    labels = [row[0] for row in grafico_data]
    valores = [row[1] for row in grafico_data]
    
    cursor.close()
    conexion.close()
    
    return render_template('index.html', 
                           rol=session.get('rol'), 
                           productos=productos, 
                           ventas_hoy=ventas_hoy, 
                           historial_permanente=historial_permanente,
                           total_dia=total_dia, 
                           labels=labels, 
                           valores=valores)

@app.route('/guardar', methods=['POST'])
def guardar():
    if 'usuario' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria')
    precio = request.form.get('precio')
    stock = request.form.get('stock')
    ruta_img = request.form.get('ruta_img') or "https://images.unsplash.com/photo-1509042239860-f550ce710b93?q=80&w=500"
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        INSERT INTO productos (nombre, categoria, precio, stock, ruta_img) 
        VALUES (%s, %s, %s, %s, %s)
    """, (nombre, categoria, precio, stock, ruta_img))
    conexion.commit()
    cursor.close()
    conexion.close()
    return redirect(url_for('index'))

@app.route('/ajustar_stock/<int:id>/<string:operacion>', methods=['POST'])
def ajustar_stock(id, operacion):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    cantidad = int(request.form.get('cantidad', 1))
    conexion = obtener_conexion()
    cursor = conexion.cursor(cursor_factory=DictCursor)
    
    cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id = %s", (id,))
    producto = cursor.fetchone()
    
    if producto:
        nuevo_stock = producto['stock']
        tipo_movimiento = 'VENTA'
        total_movimiento = producto['precio'] * cantidad
        cantidad_registro = cantidad
        
        if operacion == 'resta':
            if producto['stock'] >= cantidad:
                nuevo_stock = producto['stock'] - cantidad
            else:
                cursor.close()
                conexion.close()
                return redirect(url_for('index'))
        elif operacion == 'suma' and session.get('rol') == 'admin':
            nuevo_stock = producto['stock'] + cantidad
            tipo_movimiento = 'STOCK_ADD'
            total_movimiento = 0
            cantidad_registro = -cantidad
            
        # Actualizar Stock
        cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, id))
        
        # Registrar Operación
        cursor.execute("""
            INSERT INTO ventas (producto_nombre, cantidad, total_venta, usuario_accion, tipo_movimiento) 
            VALUES (%s, %s, %s, %s, %s)
        """, (producto['nombre'], cantidad_registro, total_movimiento, session['usuario'], tipo_movimiento))
        
        conexion.commit()
        
    cursor.close()
    conexion.close()
    return redirect(url_for('index'))

@app.route('/eliminar/<int:id>')
def eliminar(id):
    if 'usuario' not in session or session.get('rol') != 'admin':
        return redirect(url_for('login'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM productos WHERE id = %s", (id,))
    conexion.commit()
    cursor.close()
    conexion.close()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)