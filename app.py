import firebase_admin
from firebase_admin import credentials, firestore, auth
from flask import Flask, render_template, request, redirect, session
from functools import wraps
import pyrebase
import secrets

# Inicializar Firebase con el archivo de configuración descargado
cred = credentials.Certificate("key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Configuracion de pyrebase
pyrebase_config = {
    'apiKey': "AIzaSyDXumdWpQwWRCY21C-eC1yLV0I_QKkKPTU",
    'authDomain': "el-abasto-2028f.firebaseapp.com",
    'databaseURL': "https://el-abasto-2028f-default-rtdb.firebaseio.com",
    'projectId': "el-abasto-2028f",
    'storageBucket': "el-abasto-2028f.appspot.com",
    'messagingSenderId': "697474647552",
    'appId': "1:697474647552:web:6cce9e7a65646216397ae5",
    'measurementId': "G-B731TJT5XM"
}

pyrebase_app = pyrebase.initialize_app(pyrebase_config)
pyrebase_auth = pyrebase_app.auth()

# Flask
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Genera una cadena hexadecimal segura de 16 bytes

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect('/')  # Redirige a la página de inicio de sesión si el usuario no está autenticado
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect('/inicio')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = pyrebase_auth.sign_in_with_email_and_password(email, password)
            session['user'] = email
            return redirect('/inicio')  # Redirige a la página de inicio después del inicio de sesión exitoso
        except Exception as e:
            print(f"Error de autenticación: {e}")
            return render_template("login.html", error="Email o contraseña incorrectos")

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')

@app.route('/inicio')
@login_required
def inicio():
    #cajas
    cajas_ref = firestore.client().collection('cajas')
    cajas = cajas_ref.get()
    cajas_ordenadas = sorted(cajas, key=lambda x: x.to_dict().get('fecha'), reverse=True)

    #gastos
    gastos_ref = firestore.client().collection('gastos')
    gastos = gastos_ref.get()
    gastos_ordenados = sorted(gastos, key=lambda x: x.to_dict().get('fecha'), reverse=True)

    return render_template("inicio.html", cajas = cajas_ordenadas, gastos = gastos_ordenados)

@app.route('/caja')
@login_required
def caja():
    return render_template("caja.html")

@app.route('/gastos')
@login_required
def gastos():
    return render_template("gastos.html")

@app.route('/ventas')
@login_required
def ventas():
    return render_template("ventas.html")

@app.route('/recuperarPassword', methods=['GET', 'POST'])
def recuperarPassword():
    mensaje_error = None
    if request.method == 'POST':
        email = request.form.get('email')
        try:
            user = auth.get_user_by_email(email)
            print(user.uid)
            pyrebase_auth.send_password_reset_email(email)
            return redirect("/")
        except Exception as e:
            mensaje_error = "Usuario no registrado"

    return render_template("recuperarPassword.html", error=mensaje_error)


@app.route('/agregar_gastos', methods=['POST'])
@login_required
def agregar_gastos():
    # Recibe los datos del formulario
    datos = request.form

    # Obtiene la lista de categorías, nombres, cantidades, montos y fechas
    categorias = datos.getlist('categoria')
    nombres = datos.getlist('nombre')
    cantidades = [int(cantidad) for cantidad in datos.getlist('cantidad')]
    montos = [float(monto) for monto in datos.getlist('monto')]
    fechas = datos.getlist('fecha')

    # Agrega cada gasto como un documento individual en la colección gastos
    for categoria, nombre, cantidad, monto, fecha in zip(categorias, nombres, cantidades, montos, fechas):
        data = {
            'categoria': categoria,
            'nombre': nombre,
            'cantidad': cantidad,
            'monto': monto,
            'fecha': fecha
        }
        db.collection('gastos').add(data)

    return redirect('/gastos')


@app.route('/cerrar_caja', methods=['POST'])
@login_required
def cerrar_caja():
    # Recibe los datos del formulario
    fecha = request.form.get('fecha')
    monto_efectivo = float(request.form.get('montoEfectivo'))
    monto_tarjeta_mp = float(request.form.get('montoTarjetaMP'))

    # Obtener los gastos de Firestore
    gasto_ref = firestore.client().collection('gastos')
    gastos = gasto_ref.get()
    
    total_gastos = 0

    for gasto in gastos:
        gasto_data = gasto.to_dict()
        if fecha == gasto_data.get('fecha'):
            total_gastos += gasto_data.get('monto')

    #saco el total
    total = monto_efectivo + monto_tarjeta_mp + total_gastos

    try:
        # Agrega los datos del cierre de caja como un documento individual en la colección cajas
        data = {
            'fecha': fecha,
            'monto_efectivo': monto_efectivo,
            'monto_tarjeta_mp': monto_tarjeta_mp,
            'gastos': total_gastos,
            'total': total
        }
        db.collection('cajas').add(data)

        return redirect('/inicio')
    except Exception as e:
        print(f"Error al cerrar la caja: {e}")
        return redirect('/caja')


if __name__ == '__main__':
    app.run(debug=True)
