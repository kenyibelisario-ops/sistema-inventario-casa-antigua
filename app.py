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