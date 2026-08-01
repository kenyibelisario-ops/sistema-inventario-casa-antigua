from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'  # Necesario para manejar sesiones de usuario

# Configura tu conexión a PostgreSQL
def obtener_conexion():
    return psycopg2.connect(
        host="localhost",
        database="tu_base_de_datos",
        user="tu_usuario",
        password="tu_contraseña"
    )

@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        
        if not usuario or not contrasena:
            flash("Por favor rellene todos los campos", "danger")
            return redirect(url_for('login'))
        
        # Conexión a PostgreSQL para verificar el usuario en la base de datos
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            
            # Ajusta la consulta según el nombre de tu tabla de usuarios/empleados
            cursor.execute("SELECT id, usuario, rol FROM empleados WHERE usuario = %s AND contrasena = %s;", (usuario, contrasena))
            empleado = cursor.fetchone()
            
            cursor.close()
            conexion.close()
            
            if empleado:
                # Guardamos los datos en la sesión de Flask
                session['usuario_id'] = empleado[0]
                session['usuario_nombre'] = empleado[1]
                session['rol'] = empleado[2] # Ej: 'admin' o 'empleado'
                
                # Redirige al panel de control exitosamente
                return redirect(url_for('panel_control'))
            else:
                flash("Usuario o contraseña incorrectos", "danger")
                return redirect(url_for('login'))
                
        except Exception as e:
            flash(f"Error de conexión con la base de datos", "danger")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/panel')
def panel_control():
    # Validación simple para asegurar que inició sesión
    if 'usuario_nombre' not in session:
        flash("Por favor inicie sesión primero", "danger")
        return redirect(url_for('login'))
        
    return render_template('panel.html') # O la ruta de tu panel actual

@app.route('/catalogo')
def catalogo():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos;")
    productos = cursor.fetchall()
    cursor.close()
    conexion.close()
    
    return render_template('catalogo.html', productos=productos)

if __name__ == '__main__':
    app.run(debug=True)