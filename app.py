@app.route('/login', methods=['GET', 'POST'])
def login():
    # Capturamos el usuario ya sea por parámetros GET (en la URL) o POST (formulario)
    usuario = request.args.get('usuario') or request.form.get('usuario')
    
    if usuario:
        session['usuario'] = usuario
        print(f"¡Inicio de sesión exitoso para: {usuario}! Redirigiendo al catálogo...")
        return redirect(url_for('catalogo')) # <--- Esto es vital para que brinque al catálogo
            
    return render_template('login.html')