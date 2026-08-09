from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Capturamos usando notación de diccionario para asegurar lectura estricta
        try:
            usuario = request.form['usuario']
            contrasena = request.form['contrasena']
        except KeyError:
            flash("Error en los campos del formulario. Intenta de nuevo.", "danger")
            return redirect(url_for('login'))
        
        print(f"DEBUG LOGIN -> Usuario: '{usuario}' | Contraseña: '{contrasena}'")
        
        # Validación de campos vacíos o espacios en blanco
        if not usuario.strip() or not contrasena.strip():
            flash("Por favor rellene todos los campos", "danger")
            return redirect(url_for('login'))
        
        # Si todo está correcto, guardamos sesión y avanzamos
        session['usuario'] = usuario.strip()
        return redirect(url_for('catalogo'))
            
    return render_template('login.html')

@app.route('/catalogo')
def catalogo():
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