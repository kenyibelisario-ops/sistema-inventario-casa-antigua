from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

# Esto es CRUCIAL para que las sesiones y cookies funcionen correctamente detrás del proxy HTTPS de Render
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        contrasena = request.form.get('contrasena', '').strip()
        
        print(f"DEBUG LOGIN -> Intentando ingresar con usuario: '{usuario}'")
        
        if not usuario or not contrasena:
            flash("Por favor rellene todos los campos", "danger")
            return redirect(url_for('login'))
        
        # Guardamos la sesión de manera segura
        session.permanent = True
        session['usuario'] = usuario
        print(f"DEBUG LOGIN -> Sesión guardada exitosamente para: {usuario}. Redirigiendo...")
        return redirect(url_for('catalogo'))
            
    return render_template('login.html')

@app.route('/catalogo')
def catalogo():
    # Validamos si la sesión existe
    if 'usuario' not in session:
        print("DEBUG CATALOGO -> Acceso denegado: No hay sesión activa. Redirigiendo al login.")
        flash("Por favor inicia sesión primero", "danger")
        return redirect(url_for('login'))
        
    productos = [
        (1, "Café Americano Tradicional", "Bebidas", 2.50, 15, "https://via.placeholder.com/400x200?text=Cafe+Americano"),
        (2, "Café Subscription Latte", "Bebidas", 3.75, 10, "https://via.placeholder.com/400x200?text=Latte"),
        (3, "Tres Leches Casero", "Postres", 4.00, 5, "https://via.placeholder.com/400x200?text=Tres+Leches")
    ]
    return render_template('catalogo.html', productos=productos)

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)