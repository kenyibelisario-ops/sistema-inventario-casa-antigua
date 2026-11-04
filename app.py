from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime
import pg8000
import os
import urllib.parse
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

app = Flask(__name__)
app.secret_key = 'clave_secreta_casa_antigua_2026'

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

def obtener_conexion():
    database_url = os.environ.get("DATABASE_URL")
    
    if database_url:
        parsed_url = urllib.parse.urlparse(database_url)
        return pg8000.connect(
            user=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            database=parsed_url.path[1:],
            port=parsed_url.port or 5432,
            timeout=30,
            ssl_context=True
        )
    else:
        return pg8000.connect(
            user=os.environ.get("PGUSER", "postgres"),
            password=os.environ.get("PGPASSWORD", ""),
            host=os.environ.get("PGHOST", "localhost"),
            database=os.environ.get("PGDATABASE", "casaantigua_db"),
            port=int(os.environ.get("PGPORT", 5432)),
            timeout=30,
            ssl_context=True
        )

def inicializar_bd():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                categoria TEXT NOT NULL,
                precio NUMERIC(12, 2) NOT NULL,
                stock INTEGER NOT NULL,
                imagen TEXT
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas_diarias (
                id SERIAL PRIMARY KEY,
                producto TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                total NUMERIC(12, 2) NOT NULL,
                usuario TEXT NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial (
                id SERIAL PRIMARY KEY,
                accion TEXT NOT NULL,
                producto TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                usuario TEXT NOT NULL,
                total NUMERIC(12, 2) DEFAULT 0,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            ALTER TABLE historial ADD COLUMN IF NOT EXISTS total NUMERIC(12, 2) DEFAULT 0;
        """)
        
        conexion.commit()
        cursor.close()
        conexion.close()
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")

inicializar_bd()

def verificar_cambio_dia():
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT fecha FROM ventas_diarias ORDER BY id DESC LIMIT 1;")
        ultima_venta = cursor.fetchone()
        
        if ultima_venta:
            fecha_ultima_venta = str(ultima_venta[0])[:10]
            if fecha_ultima_venta != hoy_str:
                cursor.execute("DELETE FROM ventas_diarias;")
                conexion.commit()
                
        cursor.close()
        conexion.close()
    except Exception:
        pass

@app.route('/')
def inicio():
    return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip().lower()
        contrasena = request.form.get('contrasena', '').strip()
        
        if not usuario or not contrasena:
            flash("Por favor rellene todos los campos", "danger")
            return redirect(url_for('login'))
        
        if usuario == 'admin':
            if contrasena != 'admin123':
                flash("Contraseña incorrecta", "danger")
                return redirect(url_for('login'))
            session['rol'] = 'admin'
        else:
            if contrasena != 'empleado123':
                flash("Contraseña incorrecta", "danger")
                return redirect(url_for('login'))
            session['rol'] = 'empleado'
            
        session['usuario'] = usuario
        return redirect(url_for('panel'))
            
    return render_template('login.html')

@app.route('/panel')
def panel():
    if 'usuario' not in session:
        flash("Por favor inicia sesión primero", "danger")
        return redirect(url_for('login'))
        
    verificar_cambio_dia()
    query = request.args.get('q', '').strip().lower()
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    productos = []
    if query:
        cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos WHERE LOWER(nombre) LIKE %s OR LOWER(categoria) LIKE %s;", (f"%{query}%", f"%{query}%"))
    else:
        cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos;")
        
    for fila in cursor.fetchall():
        productos.append({
            "id": fila[0], "nombre": fila[1], "categoria": fila[2],
            "precio": float(fila[3]), "stock": fila[4], "imagen": fila[5]
        })
        
    ventas_del_dia = []
    cursor.execute("SELECT producto, cantidad, usuario, total, fecha FROM ventas_diarias ORDER BY id DESC;")
    for v in cursor.fetchall():
        ventas_del_dia.append({
            "producto": v[0], "cantidad": v[1], "usuario": v[2], "total": float(v[3]), "fecha": str(v[4])
        })
        
    historial_permanente = []
    cursor.execute("SELECT fecha, accion, producto, cantidad, usuario, total FROM historial ORDER BY id DESC;")
    for h in cursor.fetchall():
        historial_permanente.append({
            "fecha": str(h[0]), "accion": h[1], "producto": h[2],
            "cantidad": h[3], "usuario": h[4], "total": float(h[5]) if h[5] is not None else 0
        })
        
    cursor.close()
    conexion.close()
    
    total_dinero_hoy = sum(v['total'] for v in ventas_del_dia)
    
    return render_template(
        'index.html', 
        productos=productos, 
        ventas_del_dia=ventas_del_dia,
        historial_permanente=historial_permanente,
        total_dinero_hoy=total_dinero_hoy,
        busqueda=query
    )

@app.route('/catalogo')
def catalogo():
    query = request.args.get('q', '').strip().lower()
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    productos = []
    if query:
        cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos WHERE LOWER(nombre) LIKE %s OR LOWER(categoria) LIKE %s;", (f"%{query}%", f"%{query}%"))
    else:
        cursor.execute("SELECT id, nombre, categoria, precio, stock, imagen FROM productos;")
        
    for fila in cursor.fetchall():
        productos.append({
            "id": fila[0], "nombre": fila[1], "categoria": fila[2],
            "precio": float(fila[3]), "stock": fila[4], "imagen": fila[5]
        })
        
    cursor.close()
    conexion.close()
    
    return render_template('catalogo.html', productos=productos, busqueda=query)

@app.route('/agregar', methods=['POST'])
def agregar():
    if 'usuario' not in session or session.get('rol') != 'admin':
        return redirect(url_for('panel'))
        
    nombre = request.form.get('nombre', '').strip()
    categoria = request.form.get('categoria', 'GENERAL').upper()
    imagen = request.form.get('imagen', '').strip()
    
    if not nombre or nombre.isdigit():
        flash("El nombre del producto no puede estar vacío ni contener únicamente números", "danger")
        return redirect(url_for('panel'))
    
    try:
        precio = float(request.form.get('precio', 0))
    except ValueError:
        flash("coloque un precio valido", "danger")
        return redirect(url_for('panel'))
        
    if precio <= 0:
        flash("coloque un precio valido", "danger")
        return redirect(url_for('panel'))
        
    try:
        stock = int(request.form.get('stock', 0))
    except ValueError:
        flash("coloque una cantidad de stock valida", "danger")
        return redirect(url_for('panel'))
        
    if stock <= 0:
        flash("coloque una cantidad de stock valida", "danger")
        return redirect(url_for('panel'))
        
    if imagen and not (imagen.startswith("http://") or imagen.startswith("https://")):
        flash("coloque una URL de imagen valida", "danger")
        return redirect(url_for('panel'))
    
    if not imagen:
        imagen = "https://via.placeholder.com/400x200?text=" + nombre.replace(" ", "+")
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("INSERT INTO productos (nombre, categoria, precio, stock, imagen) VALUES (%s, %s, %s, %s, %s);",
                   (nombre, categoria, precio, stock, imagen))
    
    fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("INSERT INTO historial (accion, producto, cantidad, usuario, total, fecha) VALUES (%s, %s, %s, %s, %s, %s);",
                   ('Creación Inventario', nombre, stock, session.get('usuario'), 0, fecha_str))
    
    conexion.commit()
    cursor.close()
    conexion.close()
        
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
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id = %s;", (prod_id,))
    prod = cursor.fetchone()
    
    if prod:
        nombre, precio, stock = prod[0], float(prod[1]), prod[2]
        if stock >= cantidad:
            nuevo_stock = stock - cantidad
            total_venta = precio * cantidad
            fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            cursor.execute("UPDATE productos SET stock = %s WHERE id = %s;", (nuevo_stock, prod_id))
            cursor.execute("INSERT INTO ventas_diarias (producto, cantidad, total, usuario, fecha) VALUES (%s, %s, %s, %s, %s);",
                           (nombre, cantidad, total_venta, session.get('usuario'), fecha_str))
            cursor.execute("INSERT INTO historial (accion, producto, cantidad, usuario, total, fecha) VALUES (%s, %s, %s, %s, %s, %s);",
                           ('Venta', nombre, cantidad, session.get('usuario'), total_venta, fecha_str))
            
            conexion.commit()
            
    cursor.close()
    conexion.close()
    return redirect(url_for('panel'))

@app.route('/incrementar/<int:prod_id>', methods=['POST'])
def incrementar(prod_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    try:
        cantidad = int(request.form.get('cantidad', 1))
    except ValueError:
        cantidad = 1
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT nombre, stock FROM productos WHERE id = %s;", (prod_id,))
    prod = cursor.fetchone()
    
    if prod:
        nombre, stock = prod[0], prod[1]
        nuevo_stock = stock + cantidad
        fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        cursor.execute("UPDATE productos SET stock = %s WHERE id = %s;", (nuevo_stock, prod_id))
        cursor.execute("INSERT INTO historial (accion, producto, cantidad, usuario, total, fecha) VALUES (%s, %s, %s, %s, %s, %s);",
                       ('Incremento Stock', nombre, cantidad, session.get('usuario'), 0, fecha_str))
        
        conexion.commit()
        
    cursor.close()
    conexion.close()
    return redirect(url_for('panel'))

@app.route('/eliminar/<int:prod_id>')
def eliminar(prod_id):
    if 'usuario' not in session or session.get('rol') != 'admin':
        return redirect(url_for('panel'))
        
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("DELETE FROM productos WHERE id = %s;", (prod_id,))
    conexion.commit()
    
    cursor.close()
    conexion.close()
    return redirect(url_for('panel'))

@app.route('/reporte-pdf')
def reporte_pdf():
    if 'usuario' not in session:
        return redirect(url_for('login'))
        
    verificar_cambio_dia()
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT producto, cantidad, total, usuario, fecha FROM ventas_diarias ORDER BY id DESC;")
    ventas = cursor.fetchall()
    
    cursor.close()
    conexion.close()
    
    total_dinero = sum(float(v[2]) for v in ventas)
    total_unidades = sum(int(v[1]) for v in ventas)
    
    conteo_productos = {}
    ingreso_por_producto = {}
    for v in ventas:
        prod = v[0]
        cant = int(v[1])
        tot = float(v[2])
        conteo_productos[prod] = conteo_productos.get(prod, 0) + cant
        ingreso_por_producto[prod] = ingreso_por_producto.get(prod, 0.0) + tot
        
    prod_mas_vendido = "N/A"
    cant_mas_vendido = 0
    if conteo_productos:
        prod_mas_vendido = max(conteo_productos, key=conteo_productos.get)
        cant_mas_vendido = conteo_productos[prod_mas_vendido]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    c_marron_oscuro = colors.HexColor('#2e1b14')
    c_marron_tarjeta = colors.HexColor('#3b2219')
    c_dorado = colors.HexColor('#d4af37')
    c_verde = colors.HexColor('#198754')
    
    titulo_style = ParagraphStyle(
        'TituloReporte',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=c_dorado,
        alignment=1,
        spaceAfter=4
    )
    
    subtitulo_style = ParagraphStyle(
        'SubtituloReporte',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.white,
        alignment=1,
        spaceAfter=10
    )
    
    seccion_style = ParagraphStyle(
        'SeccionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=c_marron_oscuro,
        spaceBefore=12,
        spaceAfter=6
    )
    
    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#1a0f0a')
    )
    
    cell_normal = ParagraphStyle(
        'CellNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        textColor=colors.HexColor('#222222')
    )

    cell_header = ParagraphStyle(
        'CellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white
    )

    fecha_hoy = datetime.now().strftime("%d/%m/%Y %I:%M %p")
    header_data = [
        [Paragraph("CAFÉ-CASA ANTIGUA", titulo_style)],
        [Paragraph(f"REPORTE DETALLADO DE VENTAS DIARIAS - GENERADO EL {fecha_hoy}", subtitulo_style)]
    ]
    t_header = Table(header_data, colWidths=[7.2*inch])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_marron_tarjeta),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('BOX', (0, 0), (-1, -1), 1.5, c_dorado),
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 15))

    elements.append(Paragraph("Resumen General de la Jornada", seccion_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=c_dorado, spaceAfter=8))
    
    resumen_data = [
        [
            Paragraph("Total Dinero Ingresado", cell_bold),
            Paragraph(f"${total_dinero:.2f}", ParagraphStyle('GreenText', parent=cell_bold, textColor=c_verde, fontSize=11))
        ],
        [
            Paragraph("Producto Más Vendido", cell_bold),
            Paragraph(f"{prod_mas_vendido} ({cant_mas_vendido} unidades)", cell_normal)
        ],
        [
            Paragraph("Total Unidades Vendidas", cell_bold),
            Paragraph(f"{total_unidades} artículos", cell_normal)
        ],
        [
            Paragraph("Total Transacciones Registradas", cell_bold),
            Paragraph(f"{len(ventas)} ventas", cell_normal)
        ],
        [
            Paragraph("Generado por", cell_bold),
            Paragraph(f"{session.get('usuario')} (Rol: {session.get('rol').upper()})", cell_normal)
        ]
    ]
    t_resumen = Table(resumen_data, colWidths=[2.5*inch, 4.7*inch])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fcf8f2