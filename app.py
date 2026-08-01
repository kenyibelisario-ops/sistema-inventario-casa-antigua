from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

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
        
        try:
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            
            # Consulta a tu base de datos para verificar el usuario y contraseña
            cursor.execute("SELECT id, usuario, rol FROM empleados WHERE usuario = %s AND contrasena = %s;", (usuario, contrasena))
            empleado = cursor.fetchone()
            
            cursor.close()
            conexion.close()
            
            if empleado:
                # Si las credenciales son correctas, redirige al catálogo o panel
                return redirect(url_for('catalogo'))
            else:
                flash("Usuario o contraseña incorrectos", "danger")
                return redirect(url_for('login'))
                
        except Exception as e:
            flash("Error conectando con la base de datos", "danger")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/catalogo')
def catalogo():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        # Orden esperado por la plantilla: id(0), nombre(1), categoria(2), precio(3), stock(4), imagen(5)
        cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos;")
        productos = cursor.fetchall()
        cursor.close()
        conexion.close()
    except:
        productos = []
        
    return render_template('catalogo.html', productos=productos)

if __name__ == '__main__':
    app.run(debug=True)