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
                cantidad INT NOT NULL,
                imagen TEXT
            )
        """)
        
        # ASEGURAR TIPO TEXT PARA LA IMAGEN SI LA TABLA YA EXISTÍA
        try:
            conexion.run("ALTER TABLE productos ALTER COLUMN imagen TYPE TEXT;")
        except Exception:
            pass

        res = conexion.run("SELECT COUNT(*) FROM usuarios")
        if res and res[0][0] == 0:
            conexion.run("INSERT INTO usuarios (usuario, clave, rol) VALUES ('admin', '1234', 'administrador')")
            conexion.run("INSERT INTO usuarios (usuario, clave, rol) VALUES ('empleado', '1234', 'empleado')")
        
        conexion.close()
        return "Base de datos inicializada y actualizada correctamente. <a href='/login'>Ir al Login</a>"
    except Exception as e:
        return f"Error al inicializar la base de datos: {e}"

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
        
        # AUTO-MIGRACIÓN: Asegura que la columna 'imagen' soporte textos largos
        try:
            conexion.run("ALTER TABLE productos ALTER COLUMN imagen TYPE TEXT;")
        except Exception:
            pass
            
        productos = conexion.run("SELECT id, nombre, categoria, precio, cantidad, imagen FROM productos ORDER BY id DESC")
        
        # Estructuras recuperadas para el flujo de caja, gráficas e historiales
        total_dia = 0.0
        labels = []
        valores = []
        ventas_hoy = []
        historial_permanente = []
        
        # Intentar obtener datos de ventas o transacciones si las tablas existen
        try:
            res_ventas = conexion.run("SELECT SUM(total) FROM ventas_dia")
            if res_ventas and res_ventas[0][0]:
                total_dia = float(res_ventas[0][0])
        except Exception:
            pass

        try:
            res_grafica = conexion.run("SELECT producto, SUM(cantidad) FROM detalle_ventas GROUP BY producto")
            for row in res_grafica:
                labels.append(row[0])
                valores.append(row[1])
        except Exception:
            # Datos de respaldo para la gráfica basados en productos actuales si no hay ventas
            for p in productos:
                labels.append(p[1])  # nombre
                valores.append(p[4])  # cantidad / stock
        
        try:
            ventas_hoy = conexion.run("SELECT * FROM ventas_dia ORDER BY id DESC")
        except Exception:
            pass

        try:
            historial_permanente = conexion.run("SELECT * FROM historial ORDER BY id DESC")
        except Exception:
            pass
        
        conexion.close()
    except Exception as e:
        productos = []
        total_dia = 0.0
        labels = []
        valores = []
        ventas_hoy = []
        historial_permanente = []
        flash(f'Error al obtener productos: {e}', 'danger')
        
    return render_template('index.html', 
                           productos=productos, 
                           usuario=session.get('usuario'), 
                           rol=session.get('rol'),
                           total_dia=total_dia,
                           labels=labels,
                           valores=valores,
                           ventas_hoy=ventas_hoy,
                           historial_permanente=historial_permanente)

@app.route('/agregar', methods=['POST'])
def agregar_producto():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria')
    precio = request.form.get('precio')
    stock = request.form.get('stock')
    ruta_img = request.form.get('ruta_img')
    
    try:
        conexion = obtener_conexion()
        conexion.run(
            "INSERT INTO productos (nombre, categoria, precio, cantidad, imagen) VALUES (:n, :c, :p, :q, :i)",
            n=nombre, c=categoria, p=float(precio), q=int(stock), i=ruta_img
        )
        
        # Registrar en el historial si la tabla existe
        try:
            conexion.run(
                "INSERT INTO historial (accion, detalle, usuario) VALUES ('AGREGAR', :d, :u)",
                d=f"Se agregó el producto {nombre} con stock {stock}", u=session.get('usuario')
            )
        except Exception:
            pass

        conexion.close()
        flash('¡Producto agregado exitosamente!', 'success')
    except Exception as e:
        flash(f'Error al agregar el producto: {e}', 'danger')
        
    return redirect(url_for('panel_principal'))

@app.route('/ajustar_stock/<int:id_prod>/<accion>', methods=['POST'])
def ajustar_stock(id_prod, accion):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    cantidad_str = request.form.get('cantidad', '1')
    try:
        cantidad = int(cantidad_str)
        conexion = obtener_conexion()
        
        if accion == 'resta':
            conexion.run("UPDATE productos SET cantidad = cantidad - :q WHERE id = :id", q=cantidad, id=id_prod)
            
            # Intentar registrar venta / flujo de caja si las tablas secundarias existen
            try:
                res_prod = conexion.run("SELECT nombre, precio FROM productos WHERE id = :id", id=id_prod)
                if res_prod:
                    nombre_prod = res_prod[0][0]
                    precio_prod = float(res_prod[0][1])
                    total_venta = precio_prod * cantidad
                    conexion.run(
                        "INSERT INTO ventas_dia (producto, cantidad, total, usuario) VALUES (:p, :q, :t, :u)",
                        p=nombre_prod, q=cantidad, t=total_venta, u=session.get('usuario')
                    )
            except Exception:
                pass

            flash('Venta registrada correctamente.', 'success')
        elif accion == 'suma':
            rol_actual = session.get('rol')
            if rol_actual == 'administrador' or rol_actual == 'admin':
                conexion.run("UPDATE productos SET cantidad = cantidad + :q WHERE id = :id", q=cantidad, id=id_prod)
                flash('Stock incrementado correctamente.', 'success')
            else:
                flash('No tienes permisos de administrador para realizar esta acción.', 'danger')
                
        conexion.close()
    except Exception as e:
        flash(f'Error al ajustar el stock: {e}', 'danger')
        
    return redirect(url_for('panel_principal'))

@app.route('/eliminar/<int:id_prod>')
def eliminar_producto(id_prod):
    rol_actual = session.get('rol')
    if 'usuario' not in session or (rol_actual != 'admin' and rol_actual != 'administrador'):
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('panel_principal'))
        
    try:
        conexion = obtener_conexion()
        conexion.run("DELETE FROM productos WHERE id = :id", id=id_prod)
        conexion.close()
        flash('Producto eliminado del catálogo.', 'info')
    except Exception as e:
        flash(f'Error al eliminar el producto: {e}', 'danger')
        
    return redirect(url_for('panel_principal'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)