from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

@app.route('/')
def inicio():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Permitimos capturar tanto por GET (enlace directo) como por POST
    usuario = request.args.get('usuario') or request.form.get('usuario')
    
    if usuario:
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