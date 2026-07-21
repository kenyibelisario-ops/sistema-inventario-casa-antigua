import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pg8000.native

app = Flask(__name__)
app.secret_key = 'clave_secreta_casa_antigua'

# Datos de conexión
DB_USER = "avnadmin"
DB_PASS = "3HUKlHpqIidKR5nM0nPDN69W1Dq7kJ1G"
DB_HOST = "dpg-d9f7blnavr4c73c9u29g-a"
DB_NAME = "casaantigua_db"

def obtener_conexion():
    return pg8000.native.Connection(
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        database=DB_NAME,
        port=5432
    )

# Ruta auxiliar para crear tablas/usuarios manualmente solo cuando sea necesario
@app.route('/init-db')
def init_db():
    try:
        conexion = obtener_conexion()
        conexion.run("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR(100) UNIQUE NOT NULL,
                clave VARCHAR(255) NOT NULL,
                rol VARCHAR(50) NOT NULL DEFAULT 'empleado'
            )
        """)
        conexion.run("""
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                categoria VARCHAR(100) NOT NULL,
                precio DECIMAL(10, 2) NOT NULL,
                cantidad INT NOT NULL
            )
        """)
        
        # Insertar usuarios si no existen
        res = conexion.run("SELECT COUNT(*) FROM usuarios")
        if res and res[0][0] == 0:
            conexion.run("INSERT INTO usuarios (usuario, clave, rol) VALUES ('admin', '1234', 'administrador')")
            conexion.run("INSERT INTO usuarios (usuario, clave, rol) VALUES ('empleado', '1234', 'empleado')")
        
        conexion.close()
        return "Base de datos inicializada correctamente. <a href='/login'>Ir al Login</a>"
    except Exception as e:
        return f"Error al inicializar la base de datos: {e}"


# --- RUTAS PRINCIPALES ---

@app.route('/')
def inicio():
    if 'usuario' in session:
        return redirect(url_for('panel_principal'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('username')
        clave = request.form.get('password')
        
        if not usuario or not clave:
            flash('Por favor complete todos los campos.', 'warning')
            return render_template('login.html')
            
        try:
            conexion = obtener_conexion()
            res = conexion.run("SELECT id, usuario, clave, rol FROM usuarios WHERE usuario = :u AND clave = :c", u=usuario, c=clave)
            conexion.close()
            
            if res:
                session['usuario_id'] = res[0][0]
                session['usuario'] = res[0][1]
                session['rol'] = res[0][3]
                flash('¡Inicio de sesión exitoso!', 'success')
                return redirect(url_for('panel_principal'))
            else:
                flash('Usuario o contraseña incorrectos.', 'danger')
        except Exception as e:
            flash(f'Error de conexión a la base de datos: {e}', 'danger')

    return render_template('login.html')

@app.route('/panel')
def panel_principal():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    try:
        conexion = obtener_conexion()
        productos = conexion.run("SELECT id, nombre, categoria, precio, cantidad FROM productos ORDER BY id DESC")
        
        # Variables requeridas por index.html para evitar errores de renderizado
        total_dia = 0.0
        labels = []
        data = []
        
        conexion.close()
    except Exception as e:
        productos = []
        total_dia = 0.0
        labels = []
        data = []
        flash(f'Error al obtener productos: {e}', 'danger')
        
    return render_template('index.html', 
                           productos=productos, 
                           usuario=session.get('usuario'), 
                           rol=session.get('rol'),
                           total_dia=total_dia,
                           labels=labels,
                           data=data)

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)