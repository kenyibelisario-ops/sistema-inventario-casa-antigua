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
    
    # Creamos la tabla clásica si no existe
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
    conexion.commit()
    
    # Traemos solo tus productos nativos
    cursor.execute("SELECT id, nombre, categoria, precio, stock, ruta_img FROM productos")
    productos = cursor.fetchall()
    
    cursor.close()
    conexion.close()
    
    return render_template('index.html', usuario_actual=usuario_actual, rol=rol, productos=productos)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        txt_usuario = request.form['username'].strip() # Vinculado a tu login.html
        txt_clave = request.form['password'].strip()
        
        if txt_usuario == "admin" and txt_clave == "1234":
            session['usuario'] = 'Administrador'
            session['rol'] = 'admin'
            return redirect(url_for('index'))
        elif txt_usuario == "operario" and txt_clave == "5678":
            session['usuario'] = 'Operario Ventas'
            session['rol'] = 'operario'
            return redirect(url_for('index'))
        else:
            flash("Usuario o contraseña incorrectos.")
            return redirect(url_for('login'))
            
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

@app.route('/ajustar_stock/<int:id>/<string:operacion>', methods=['POST'])
def ajustar_stock(id, operacion):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cantidad = int(request.form['cantidad'])
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT stock FROM productos WHERE id = %s", (id,))
    producto = cursor.fetchone()
    
    if producto:
        stock_actual = producto[0]
        if operacion == 'resta':
            nuevo_stock = max(0, stock_actual - cantidad)
        elif operacion == 'suma':
            nuevo_stock = stock_actual + cantidad
            
        cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, id))
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
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)