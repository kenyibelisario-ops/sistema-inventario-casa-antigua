from flask import Flask, render_template, redirect, url_for
import psycopg2 # o el conector que estés utilizando

app = Flask(__name__)

# Configura tu conexión a PostgreSQL
def obtener_conexion():
    return psycopg2.connect(
        host="localhost",
        database="tu_base_de_datos",
        user="tu_usuario",
        password="tu_contraseña"
    )

@app.route('/catalogo')
def catalogo():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # IMPORTANTE: El orden de las columnas debe coincidir exactamente con los índices de la plantilla (p[0], p[1], etc.)
    # p[0] = id, p[1] = nombre, p[2] = categoria, p[3] = precio, p[4] = stock, p[5] = imagen
    cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos;")
    productos = cursor.fetchall()
    
    cursor.close()
    conexion.close()
    
    return render_template('catalogo.html', productos=productos)

@app.route('/login')
def login():
    return "Vista de Login / Acceso de Empleados"

if __name__ == '__main__':
    app.run(debug=True)