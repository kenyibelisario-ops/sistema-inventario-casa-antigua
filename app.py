from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Imprimimos todo lo que llega en la petición para verificar en los logs de Render
        print("DATOS RECIBIDOS EN REQUEST.FORM:", request.form)
        
        usuario = request.form.get('usuario', '').strip()
        contrasena = request.form.get('contrasena', '').strip()
        
        # Si por alguna razón el formulario llega vacío, leemos directamente de los argumentos o forzamos
        if not usuario or not contrasena:
            # Intentamos leer por claves genéricas si el proxy alteró el nombre
            if len(request.form) > 0:
                keys = list(request.form.keys())
                usuario = request.form.get(keys[0], '')
                contrasena = request.form.get(keys[1], '') if len(keys) > 1 else 'ok'
            
        if not usuario or not contrasena:
            flash("Por favor rellene todos los campos", "danger")
            return redirect(url_for('login'))
        
        session['usuario'] = usuario
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