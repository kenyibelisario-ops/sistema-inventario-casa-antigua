from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave_secreta_casa_antigua_2026'

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Datos iniciales en memoria
inventario_productos = [
    {"id": 1, "nombre": "arroz Mary", "categoria": "GRANOS", "precio": 2000.00, "stock": 10, "imagen": "https://via.placeholder.com/400x200?text=Arroz+Mary"},
    {"id": 2, "nombre": "lentejas", "categoria": "GRANOS", "precio": 3000.00, "stock": 17, "imagen": "https://via.placeholder.com/400x200?text=Lentejas"},
    {"id": 3, "nombre": "Speed Max", "categoria": "BEBIDAS", "precio": 75000.00, "stock": 25, "imagen": "https://via.placeholder.com/400x200?text=Speed+Max"},
    {"id": 4, "nombre": "crema de dientes colgate", "categoria": "ASEO", "precio": 21000.00, "stock": 7, "imagen": "https://via.placeholder.com/400x200?text=Colgate"}
]

historial_permanente = [
    {"fecha": "2026-08-09 10:30", "accion": "Venta", "producto": "Speed Max", "cantidad": 25, "usuario": "Sulej Boscarini", "total": 75000.00},
    {"fecha": "2026-08-09 11:15", "accion": "Venta", "producto": "crema de dientes colgate", "cantidad": 7, "usuario": "admin", "total": 21000.00},
    {"fecha": "2026-08-09 09:00", "accion": "Creación Inventario", "producto": "arroz Mary", "cantidad": 10, "usuario": "admin", "total": 0}
]

ventas_del_dia = [
    {"producto": "Speed Max", "cantidad": 25, "usuario": "Sulej Boscarini", "total": 75000.00},
    {"producto": "crema de dientes colgate", "cantidad": 7, "usuario": "admin", "total": 21000.00}
]

fecha_actual_sistema = datetime.now().strftime("%Y-%m-%d")

def verificar_cambio_dia():
    global fecha_actual_sistema, ventas_del_dia
    hoy = datetime.now().strftime("%Y-%m-%d")
    if hoy != fecha_actual_sistema:
        fecha_actual_sistema = hoy
        ventas_del_dia.clear()

@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip().lower()
        contrasena = request.form.get('contrasena', '').strip()
        
        if not usuario or not contrasena:
            flash("Por favor rellene todos los campos", "danger")
            return redirect(url_for('login'))
        
        session['usuario'] = usuario
        if usuario == 'admin':
            session['rol'] = 'admin'
        else:
            session['rol'] = 'empleado'
            
        return redirect(url_for('panel'))
            
    return render_template('login.html')

@app.route('/panel')
def panel():
    if 'usuario' not in session:
        flash("Por favor inicia sesión primero", "danger")
        return redirect(url_for('login'))
        
    verificar_cambio_dia()
    
    query = request.args.get('q', '').strip().lower()
    if query:
        productos_filtrados = [p for p in inventario_productos if query in p['nombre'].lower() or query in p['categoria'].lower()]
    else:
        productos_filtrados = inventario_productos
        
    total_dinero_hoy = sum(v['total'] for v in ventas_del_dia)
    
    return render_template(
        'index.html', 
        productos=productos_filtrados, 
        ventas_del_dia=ventas_del_dia,
        historial_permanente=historial_permanente,
        total_dinero_hoy=total_dinero_hoy,
        busqueda=query
    )

@app.route('/catalogo')
def catalogo():
    query = request.args.get('q', '').strip().lower()
    if query:
        productos_filtrados = [p for p in inventario_productos if query in p['nombre'].lower() or query in p['categoria'].lower()]
    else:
        productos_filtrados = inventario_productos
        
    return render_template('catalogo.html', productos=productos_filtrados, busqueda=query)

@app.route('/agregar', methods=['POST'])
def agregar():
    if 'usuario' not in session or session.get('rol') != 'admin':
        return redirect(url_for('panel'))
        
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria', 'GENERAL').upper()
    imagen = request.form.get('imagen', '').strip()
    
    try:
        precio = float(request.form.get('precio', 0))
        stock = int(request.form.get('stock', 0))
    except ValueError:
        precio, stock = 0.0, 0
    
    if not imagen:
        imagen = "https://via.placeholder.com/400x200?text=" + nombre.replace(" ", "+")
    
    if nombre:
        nuevo_id = max([p['id'] for p in inventario_productos], default=0) + 1
        inventario_productos.append({
            "id": nuevo_id,
            "nombre": nombre,
            "categoria": categoria,
            "precio": precio,
            "stock": stock,
            "imagen": imagen
        })
        
        historial_permanente.insert(0, {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "accion": "Creación Inventario",
            "producto": nombre,
            "cantidad": stock,
            "usuario": session.get('usuario'),
            "total": 0
        })
        
    return redirect(url_for('panel'))

@app.route('/vender/<int:prod_id>', methods=['POST'])
def vender(prod_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    verificar_cambio_dia()
    
    try:
        cantidad = int(request.form.get('cantidad', 1))
    except ValueError:
        cantidad = 1
        
    for prod in inventario_productos:
        if prod['id'] == prod_id:
            if prod['stock'] >= cantidad:
                prod['stock'] -= cantidad
                total_venta = prod['precio'] * cantidad
                
                ventas_del_dia.insert(0, {
                    "producto": prod['nombre'],
                    "cantidad": cantidad,
                    "usuario": session.get('usuario'),
                    "total": total_venta
                })
                
                historial_permanente.insert(0, {
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "accion": "Venta",
                    "producto": prod['nombre'],
                    "cantidad": cantidad,
                    "usuario": session.get('usuario'),
                    "total": total_venta
                })
            break
    return redirect(url_for('panel'))

@app.route('/incrementar/<int:prod_id>', methods=['POST'])
def incrementar(prod_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    try:
        cantidad = int(request.form.get('cantidad', 1))
    except ValueError:
        cantidad = 1
        
    for prod in inventario_productos:
        if prod['id'] == prod_id:
            prod['stock'] += cantidad
            historial_permanente.insert(0, {
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "accion": "Incremento Stock",
                "producto": prod['nombre'],
                "cantidad": cantidad,
                "usuario": session.get('usuario'),
                "total": 0
            })
            break
    return redirect(url_for('panel'))

@app.route('/eliminar/<int:prod_id>')
def eliminar(prod_id):
    if 'usuario' not in session or session.get('rol') != 'admin':
        return redirect(url_for('panel'))
        
    global inventario_productos
    inventario_productos = [p for p in inventario_productos if p['id'] != prod_id]
    return redirect(url_for('panel'))

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('rol', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
    import pg8000
from flask import Flask, session

app = Flask(__name__)
# Recuerda que debes tener configurada tu app.secret_key para que 'session' funcione
app.secret_key = 'tu_clave_secreta_aqui'

# Función de conexión a tu base de datos casaantigua_db
def obtener_conexion():
    return pg8000.connect(
        user="tu_usuario_postgres",      # Cambia por tu usuario
        password="tu_password",          # Cambia por tu contraseña
        host="localhost",                # O la URL de Render si está en la nube
        database="casaantigua_db",
        port=5432
    )

# --- TUS OTRAS RUTAS AQUÍ (/catalogo, /login, etc.) ---

@app.route('/limpiar-base-datos-antigua')
def limpiar_bd():
    # Medida de seguridad: Validar que solo el administrador pueda borrar datos
    if session.get('rol') == 'admin':
        conexion = None
        try:
            # 1. Establecer conexión
            conexion = obtener_conexion()
            cursor = conexion.cursor()
            
            # 2. Ejecutar las sentencias de limpieza
            cursor.execute("DELETE FROM ventas_diarias;")
            cursor.execute("DELETE FROM historial;")
            cursor.execute("DELETE FROM productos;")
            
            # 3. Confirmar (commit) los cambios en la base de datos
            conexion.commit()
            cursor.close()
            
            return """
            <div style="font-family: Arial; text-align: center; margin-top: 50px;">
                <h2 style="color: #25d366;">✅ Base de datos limpiada con éxito</h2>
                <p>El historial y los productos antiguos han sido eliminados del sistema.</p>
                <a href="/catalogo" style="padding: 10px 20px; background: #d4af37; color: #000; text-decoration: none; border-radius: 5px;">Volver al Catálogo</a>
            </div>
            """
            
        except Exception as e:
            # Si ocurre algún error en la base de datos, lo mostramos
            return f"<h3 style='color: red;'>❌ Ocurrió un error al limpiar la BD: {e}</h3>"
            
        finally:
            # 4. Asegurarnos de cerrar la conexión siempre
            if conexion:
                conexion.close()
    else:
        return "<h3 style='color: red;'>⛔ Acceso denegado. Debes iniciar sesión como Administrador.</h3>", 403

if __name__ == '__main__':
    app.run(debug=True)