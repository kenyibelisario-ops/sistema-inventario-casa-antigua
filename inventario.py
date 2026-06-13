import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
import mysql.connector
from datetime import datetime

app = Flask(__name__)
# Clave secreta segura desde variables de entorno o una por defecto en local
app.secret_key = os.environ.get("SECRET_KEY", "clave_secreta_casa_antigua")

# --- CONFIGURACIÓN DINÁMICA DE CONEXIÓN (Localhost vs Nube) ---
def obtener_conexion():
    en_produccion = os.environ.get("DB_HOST")
    
    if en_produccion:
        # Conexión Segura en la Nube (Producción - Con soporte de encriptación moderna)
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST"),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            database=os.environ.get("DB_NAME"),
            port=int(os.environ.get("DB_PORT", 3306)),
            auth_plugin='mysql_native_password'  # Corrección de plugin de autenticación
        )
    else:
        # Tu configuración local de XAMPP original (Desarrollo)
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="casa_antigua_db"
        )

# --- RUTA PRINCIPAL (CATÁLOGO, DASHBOARD Y AUTO-CREACIÓN) ---
@app.route('/')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    usuario_actual = session['usuario']
    rol = session['rol']
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # === SCRIPT DE AUTOMATIZACIÓN DE TABLAS ===
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
    conexion.commit()  # Asegura los cambios en la base de datos remota
    # ==========================================
    
    # 1. Obtener todos los productos para la malla del catálogo
    cursor.execute("SELECT id, nombre, categoria, precio, stock, ruta_img FROM productos")
    productos = cursor.fetchall()
    
    # 2. Flujo de Caja Real (Filtrado por el día de hoy)
    cursor.execute("""
        SELECT SUM(total) FROM ventas 
        WHERE DATE(fecha) = CURDATE()
    """)
    resultado_caja = cursor.fetchone()[0]
    total_dia = float(resultado_caja) if resultado_caja is not None else 0.0
    
    # 3. Auditoría de Ventas del Día
    cursor.execute("""
        SELECT nombre, cantidad, total, usuario 
        FROM ventas 
        WHERE DATE(fecha) = CURDATE() 
        ORDER BY id DESC
    """)
    ventas_hoy = cursor.fetchall()
    
    # 4. Datos del Gráfico Estadístico
    cursor.execute("""
        SELECT nombre, SUM(cantidad) 
        FROM ventas 
        WHERE DATE(fecha) = CURDATE() 
        GROUP BY nombre
    """)
    datos_grafico = cursor.fetchall()
    labels = [row[0] for row in datos_grafico] if datos_grafico else []
    valores = [row[1] for row in datos_grafico] if datos_grafico else []
    
    # 5. HISTORIAL DE VENTAS PERPETUO (Modal del Administrador)
    cursor.execute("""
        SELECT nombre, cantidad, total, usuario, DATE_FORMAT(fecha, '%d/%m/%Y %H:%i') 
        FROM ventas 
        ORDER BY id DESC
    """)
    historial_completo = cursor.fetchall()
    
    cursor.close()
    conexion.close()
    
    return render_template(
        'index.html',
        usuario_actual=usuario_actual,
        rol=rol,
        productos=productos,
        total_dia=total_dia,
        ventas_hoy=ventas_hoy,
        labels=labels,
        valores=valores,
        historial_completo=historial_completo
    )

# --- CONTROLADOR DE LOGIN (GENÉRICO) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        txt_usuario = request.form['usuario'].strip()
        txt_clave = request.form['password'].strip()
        
        if txt_usuario == "admin" and txt_clave == "1234":
            session['usuario'] = 'Administrador'  # Nombre genérico público
            session['rol'] = 'admin'
            flash("Sesión iniciada como Administrador.")
            return redirect(url_for('index'))
            
        elif txt_usuario == "operario" and txt_clave == "5678":
            session['usuario'] = 'Operario Ventas'  # Nombre genérico para el trabajador
            session['rol'] = 'operario'
            flash("Sesión iniciada como Operario.")
            return redirect(url_for('index'))
            
        else:
            flash("Usuario o contraseña incorrectos.")
            return redirect(url_for('login'))
            
    return render_template('login.html')

# --- REGISTRAR NUEVO PRODUCTO EN INVENTARIO (ADMIN) ---
@app.route('/guardar', methods=['POST'])
def guardar():
    if session.get('rol') != 'admin':
        return "Acceso denegado", 403
        
    nombre = request.form['nombre']
    categoria = request.form['categoria']
    precio = float(request.form['precio'])
    stock = int(request.form['stock'])
    ruta_img = request.form['ruta_img']
    
    if not ruta_img:
        ruta_img = "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=500"
        
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

# --- AJUSTAR STOCK (REGISTRAR VENTA / INCREMENTAR STOCK) ---
@app.route('/ajustar_stock/<int:id>/<string:operacion>', methods=['POST'])
def ajustar_stock(id, operacion):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cantidad = int(request.form['cantidad'])
    usuario_actual = session.get('usuario', 'Sistema')
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id = %s", (id,))
    producto = cursor.fetchone()
    
    if not producto:
        cursor.close()
        conexion.close()
        return "Producto no encontrado", 404
        
    nombre_prod, precio_prod, stock_actual = producto
    
    if operacion == 'resta':
        if stock_actual >= cantidad:  # Verificación correcta en español
            nuevo_stock = stock_actual - cantidad
            total_venta = precio_prod * cantidad
            
            cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, id))
            
            cursor.execute("""
                INSERT INTO ventas (nombre, cantidad, total, usuario, fecha) 
                VALUES (%s, %s, %s, %s, NOW())
            """, (nombre_prod, cantidad, total_venta, usuario_actual))
        else:
            flash("No hay suficiente stock para realizar la venta.")
            
    elif operacion == 'suma':
        if session.get('rol') != 'admin':
            cursor.close()
            conexion.close()
            return "Acceso denegado", 403
            
        nuevo_stock = stock_actual + cantidad
        cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, id))
            
    conexion.commit()
    cursor.close()
    conexion.close()
    
    return redirect(url_for('index'))

# --- ELIMINAR ARTÍCULO DEL CATÁLOGO (ADMIN) ---
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

# --- CERRAR SESIÓN ---
@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada con éxito. Por favor, inicie sesión otra vez.")
    return redirect(url_for('login'))

# --- REPORTE (SOLO ADMIN) ---
@app.route('/informe_word')
def informe_word():
    if session.get('rol') != 'admin':
        return "Acceso denegado", 403
    return "Generando informe de Word en base a los registros de MySQL... (Módulo de descarga listo)."

if __name__ == '__main__':
    # Puerto asignado dinámicamente para el entorno de Render
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)