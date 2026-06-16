import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_secreta_casa_antigua")

def obtener_conexion():
    en_produccion = os.environ.get("DB_HOST")
    if en_produccion:
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME"),
            port=int(os.environ.get("DB_PORT", 3306)),
            auth_plugin='mysql_native_password'
        )
    else:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="casa_antigua_db"
        )

@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    usuario_actual = session['usuario']
    rol = session['rol']
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Asegurar tablas base comerciales
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            categoria VARCHAR(255) NOT NULL,
            precio DECIMAL(10,2) NOT NULL,
            stock INT NOT NULL,
            ruta_img TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            cantidad INT NOT NULL,
            total DECIMAL(10,2) NOT NULL,
            usuario VARCHAR(255) NOT NULL,
            fecha DATETIME NOT NULL
        )
    """)
    conexion.commit()
    
    # 1. Catálogo de productos completo
    cursor.execute("SELECT id, nombre, categoria, precio, stock, ruta_img FROM productos")
    productos = cursor.fetchall()
    
    # 2. Flujo de Caja Real (Hoy) - Solo contabiliza salidas/ventas reales de hoy
    cursor.execute("SELECT SUM(total) FROM ventas WHERE DATE(fecha) = CURDATE() AND cantidad > 0")
    resultado_caja = cursor.fetchone()[0]
    total_dia = float(resultado_caja) if resultado_caja is not None else 0.0
    
    # 3. Auditoría Unificada del Día (Hoy)
    cursor.execute("""
        SELECT nombre, cantidad, total, usuario, 
               CASE WHEN cantidad > 0 THEN 'VENTA' ELSE 'STOCK_ADD' END as tipo_operacion,
               DATE_FORMAT(fecha, '%H:%i') as hora
        FROM ventas 
        WHERE DATE(fecha) = CURDATE()
        ORDER BY id DESC
    """)
    ventas_hoy = cursor.fetchall()

    # 4. Historial Permanente Completo (Todas las fechas)
    cursor.execute("""
        SELECT nombre, cantidad, total, usuario, 
               CASE WHEN cantidad > 0 THEN 'VENTA' ELSE 'STOCK_ADD' END as tipo_operacion,
               DATE_FORMAT(fecha, '%d/%m/%Y %H:%i') as fecha_formateada
        FROM ventas 
        ORDER BY id DESC
    """)
    historial_permanente = cursor.fetchall()
    
    # 5. Datos para el Gráfico Circular (Volumen de Ventas Reales del Día)
    cursor.execute("""
        SELECT nombre, SUM(cantidad) 
        FROM ventas 
        WHERE DATE(fecha) = CURDATE() AND cantidad > 0
        GROUP BY nombre
    """)
    datos_grafico = cursor.fetchall()
    labels = [row[0] for row in datos_grafico] if datos_grafico else []
    valores = [row[1] for row in datos_grafico] if datos_grafico else []
    
    cursor.close()
    conexion.close()
    
    return render_template(
        'index.html', 
        rol=rol, 
        productos=productos, 
        total_dia=total_dia, 
        ventas_hoy=ventas_hoy,
        historial_permanente=historial_permanente,
        labels=labels,
        valores=valores
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        txt_usuario = request.form['username'].strip()
        txt_clave = request.form['password'].strip()
        if txt_usuario == "admin" and txt_clave == "1234":
            session['usuario'] = 'admin'
            session['rol'] = 'admin'
            return redirect(url_for('index'))
        elif txt_usuario == "operario" and txt_clave == "5678":
            session['usuario'] = 'Susej Boscariol'
            session['rol'] = 'operario'
            return redirect(url_for('index'))
        else:
            flash("Usuario o contraseña incorrectos.")
    return render_template('login.html')

@app.route('/guardar', methods=['POST'])
def guardar():
    if session.get('rol') != 'admin':
        return "Acceso denegado", 403
    nombre = request.form['nombre']
    categoria = request.form['categoria']
    precio = float(request.form['precio'])
    stock = int(request.form['stock'])
    ruta_img = request.form.get('ruta_img', '').strip()
    
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
        
    cantidad = int(request.form['cantidad'])
    usuario_actual = session.get('usuario', 'admin')
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id = %s", (id,))
    producto = cursor.fetchone()
    
    if producto:
        nombre_prod, precio_prod, stock_actual = producto
        if operacion == 'resta':
            if stock_actual >= cantidad:
                nuevo_stock = stock_actual - cantidad
                total_venta = precio_prod * cantidad
                cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, id))
                cursor.execute("""
                    INSERT INTO ventas (nombre, cantidad, total, usuario, fecha) 
                    VALUES (%s, %s, %s, %s, NOW())
                """, (nombre_prod, cantidad, total_venta, usuario_actual))
        elif operacion == 'suma':
            nuevo_stock = stock_actual + cantidad
            cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, id))
            # Guardamos la cantidad como negativa internamente para el historial de stock sin afectar sumatorias de caja
            cursor.execute("""
                INSERT INTO ventas (nombre, cantidad, total, usuario, fecha) 
                VALUES (%s, %s, %s, %s, NOW())
            """, (nombre_prod, -cantidad, 0.00, usuario_actual))
            
        conexion.commit()
        
    cursor.close()
    conexion.close()
    return redirect(url_for('index'))

@app.route('/eliminar/<int:id>')
def eliminar(id):
    if session.get('rol') != 'admin':
        return "Acceso denegado", 403
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))