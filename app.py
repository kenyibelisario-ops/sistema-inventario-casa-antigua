from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_mensajes'  # Necesario para las alertas flash

# Configura tu conexión a PostgreSQL (ajusta tus credenciales si es necesario)
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
        # Captura los datos enviados desde el formulario HTML
        usuario = request.form.get('usuario')
        contrasena = request.form.get('contrasena')
        
        # Validación básica (aquí puedes conectar tu validación con PostgreSQL)
        if not usuario or not contrasena:
            flash("Por favor rellene todos los campos", "danger")
            return redirect(url_for('login'))
        
        # Ejemplo de validación de credenciales de administrador/empleado
        # if usuario == "admin" and contrasena == "1234":
        #     return redirect(url_for('panel_control'))
        # else:
        #     flash("Usuario o contraseña incorrectos", "danger")
            
    return render_template('login.html')

@app.route('/catalogo')
def catalogo():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Consulta a PostgreSQL para el catálogo público
    # Orden de columnas: id (0), nombre (1), categoria (2), precio (3), stock (4), imagen (5)
    cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos;")
    productos = cursor.fetchall()
    
    cursor.close()
    conexion.close()
    
    return render_template('catalogo.html', productos=productos)

if __name__ == '__main__':
    app.run(debug=True)