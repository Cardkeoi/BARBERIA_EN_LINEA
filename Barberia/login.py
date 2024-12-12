from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from datetime import datetime, timedelta
import pyodbc
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'JDCRDSFLN'

# Configuración de conexión a la base de datos
connection_string = (
    "DRIVER={SQL Server};"
    "SERVER=localhost;"
    "DATABASE=Barberia;"
    "Trusted_Connection=yes;"
)

UPLOAD_FOLDER = 'static/uploads/'  # Ruta para cargar imágenes
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Función para validar usuario
def validar_usuario(username, password):
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_usuario, rol FROM usuarios WHERE username = ? AND password = ?", (username, password))
            row = cursor.fetchone()
            if row:
                return {"id_usuario": row[0], "rol": row[1]}
            return None
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

def obtener_id_usuario_autenticado():
    return session.get('id_usuario')

# Rutas de la aplicación
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    usuario = validar_usuario(username, password)
    
    if usuario:
        session['id_usuario'] = usuario['id_usuario']
        session['rol'] = usuario['rol']
        if usuario['rol'] == 'Administrador':
            return jsonify({"message": "Inicio de sesión exitoso", "rol": usuario['rol'], "redirect": "/admin"})
        else:
            return jsonify({"message": "Inicio de sesión exitoso", "rol": usuario['rol'], "redirect": "/cliente"})
    else:
        return jsonify({"message": "Usuario o contraseña incorrectos"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Cierre de sesión exitoso"})

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'GET':
        return render_template('registro.html')  # Sirve el HTML para el registro

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO usuarios (username, password, rol, email) VALUES (?, ?, 'Cliente', ?)", (username, password, email))
            conn.commit()
        return jsonify({"message": "Cliente registrado con éxito"}), 200
    except Exception as e:
        print(f"Error al registrar cliente: {e}")
        return jsonify({"message": "Error al registrar cliente"}), 500

@app.route('/admin')
def admin():
    if session.get('rol') != 'Administrador':
        return redirect(url_for('index'))
    return render_template('admin.html')

@app.route('/cliente')
def cliente():
    if not obtener_id_usuario_autenticado():
        return redirect(url_for('index'))
    return render_template('cliente.html')

@app.route('/visita')
def visita():
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_servicio, nombre_servicio, descripcion, precio FROM servicios")
            servicios = cursor.fetchall()
            return render_template('visita.html', servicios=servicios)
    except Exception as e:
        print(f"Error al obtener los servicios: {e}")
        return jsonify({"message": "Error al cargar los servicios"}), 500

# Ruta para cargar y ver trabajos
@app.route('/subir_trabajo', methods=['POST'])
def subir_trabajo():
    if 'imagen' not in request.files:
        return jsonify({"message": "No se ha seleccionado ningún archivo"}), 400

    imagen = request.files['imagen']
    descripcion = request.form.get('descripcion')
    if imagen.filename == '':
        return jsonify({"message": "Nombre de archivo inválido"}), 400

    filename = secure_filename(imagen.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    imagen.save(filepath)

    # Guardar el trabajo en la base de datos
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO trabajos (imagen_url, descripcion) VALUES (?, ?)", (filepath, descripcion))
            conn.commit()
        return jsonify({"message": "Trabajo subido exitosamente"}), 200
    except Exception as e:
        print(f"Error al subir el trabajo: {e}")
        return jsonify({"message": "Error al subir el trabajo"}), 500


@app.route('/obtener_trabajos', methods=['GET'])
def obtener_trabajos():
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_trabajo, imagen_url, descripcion FROM trabajos")
            trabajos = cursor.fetchall()
            return jsonify([
                {"id_trabajo": row[0], "imagen_url": row[1], "descripcion": row[2]}
                for row in trabajos
            ])
    except Exception as e:
        print(f"Error al obtener trabajos: {e}")
        return jsonify({"message": "Error al obtener trabajos"}), 500




@app.route('/hacer_cita', methods=['POST'])
def hacer_cita():
    data = request.get_json()

    fecha = data.get('fecha')
    hora = data.get('hora')
    servicio = data.get('servicio')
    id_usuario = obtener_id_usuario_autenticado()

    # Concatenar fecha y hora en un solo campo para almacenar en la base de datos
    fecha_hora = f"{fecha} {hora}"

    # Conectar a la base de datos SQL Server usando la autenticación de Windows
    connection_string = (
        "DRIVER={SQL Server};"
        "SERVER=localhost;"
        "DATABASE=Barberia;"
        "Trusted_Connection=yes;"
    )
    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()

    # Verificar si la fecha y hora ya están ocupadas
    query_verificar = "SELECT COUNT(*) FROM citas WHERE fecha_cita = ?"
    cursor.execute(query_verificar, (fecha_hora,))
    resultado_verificar = cursor.fetchone()

    if resultado_verificar[0] > 0:
        cursor.close()
        connection.close()
        return jsonify({"message": "Este horario ya está ocupado."}), 400

    # Instrucción SQL para insertar la cita con fecha y hora concatenadas
    query_insertar = """
    INSERT INTO citas (id_usuario, fecha_cita, servicio, estado)
    VALUES (?, ?, ?, 'Pendiente')
    """

    try:
        cursor.execute(query_insertar, (id_usuario, fecha_hora, servicio))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({"message": "Cita realizada con éxito"}), 200
    except Exception as e:
        cursor.close()
        connection.close()
        print(f"Error al insertar la cita: {e}")
        return jsonify({"message": "Error al insertar la cita"}), 500

@app.route('/obtener_servicios', methods=['GET'])
def obtener_servicios():
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_servicio, nombre_servicio, descripcion, precio FROM servicios")
            servicios = cursor.fetchall()
            return jsonify([{
                "id_servicio": row[0],
                "nombre_servicio": row[1],
                "descripcion": row[2],
                "precio": row[3]
            } for row in servicios])
    except Exception as e:
        print(f"Error al obtener servicios: {e}")
        return jsonify({"message": "Error al obtener servicios"}), 500

@app.route('/actualizar_cliente', methods=['POST'])
def actualizar_cliente():
    id_usuario = obtener_id_usuario_autenticado()
    if not id_usuario:
        return jsonify({"message": "No estás autenticado"}), 401

    data = request.get_json()
    email = data.get('email')
    new_password = data.get('newPassword')

    if not email:
        return jsonify({"message": "El campo de email es obligatorio."}), 400

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            if new_password:  # Si hay una nueva contraseña, actualízala
                cursor.execute(
                    "UPDATE usuarios SET email = ?, password = ? WHERE id_usuario = ?",
                    (email, new_password, id_usuario)
                )
            else:  # Si no hay nueva contraseña, solo actualiza el email
                cursor.execute(
                    "UPDATE usuarios SET email = ? WHERE id_usuario = ?",
                    (email, id_usuario)
                )
            conn.commit()
            return jsonify({"message": "Datos actualizados exitosamente"}), 200
    except Exception as e:
        print(f"Error al actualizar los datos del cliente: {e}")
        return jsonify({"message": "Error al actualizar los datos"}), 500


    
@app.route('/obtener_citas_admin', methods=['GET'])
def obtener_citas_admin():
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT citas.id_cita, usuarios.username, 
                       FORMAT(citas.fecha_cita, 'yyyy-MM-dd HH:mm') as fecha_hora, 
                       servicios.nombre_servicio, citas.estado
                FROM citas
                JOIN usuarios ON citas.id_usuario = usuarios.id_usuario
                JOIN servicios ON citas.servicio = servicios.id_servicio
            """)
            citas = cursor.fetchall()
            
            # Devuelve las citas en un formato JSON con el nombre del servicio
            return jsonify([
                {
                    "id_cita": row[0],
                    "username": row[1],
                    "fecha_cita": row[2],
                    "servicio": row[3],  # Nombre del servicio en lugar del ID
                    "estado": row[4]
                } 
                for row in citas
            ])
    except Exception as e:
        print(f"Error al obtener las citas: {e}")
        return jsonify({"message": "Error al obtener las citas"}), 500




@app.route('/agregar_servicio', methods=['POST'])
def agregar_servicio():
    data = request.get_json()
    nombre_servicio = data.get('nombre_servicio')
    descripcion = data.get('descripcion')
    precio = data.get('precio')
    
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO servicios (nombre_servicio, descripcion, precio) VALUES (?, ?, ?)", 
                           (nombre_servicio, descripcion, precio))
            conn.commit()
        return jsonify({"message": "Servicio agregado exitosamente"}), 200
    except Exception as e:
        print(f"Error al agregar servicio: {e}")
        return jsonify({"message": "Error al agregar servicio"}), 500

@app.route('/actualizar_servicio', methods=['PUT'])
def actualizar_servicio():
    data = request.get_json()
    id_servicio = data.get('id_servicio')
    nombre_servicio = data.get('nombre_servicio')
    descripcion = data.get('descripcion')
    precio = data.get('precio')

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE servicios SET nombre_servicio = ?, descripcion = ?, precio = ?
                WHERE id_servicio = ?
            """, (nombre_servicio, descripcion, precio, id_servicio))
            conn.commit()
        return jsonify({"message": "Servicio actualizado exitosamente"}), 200
    except Exception as e:
        print(f"Error al actualizar servicio: {e}")
        return jsonify({"message": "Error al actualizar servicio"}), 500
    
@app.route('/actualizar_precio_servicio', methods=['PUT'])
def actualizar_precio_servicio():
    data = request.get_json()
    id_servicio = data.get('id_servicio')
    nuevo_precio = data.get('precio')

    if not id_servicio or nuevo_precio is None:
        return jsonify({"message": "Datos incompletos"}), 400

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE servicios SET precio = ? WHERE id_servicio = ?
            """, (nuevo_precio, id_servicio))
            conn.commit()
        return jsonify({"message": "Precio actualizado exitosamente"}), 200
    except Exception as e:
        print(f"Error al actualizar precio del servicio: {e}")
        return jsonify({"message": "Error al actualizar el precio"}), 500


@app.route('/eliminar_servicio', methods=['DELETE'])
def eliminar_servicio():
    data = request.get_json()
    id_servicio = data.get('id_servicio')
    
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM servicios WHERE id_servicio = ?", (id_servicio,))
            conn.commit()
        return jsonify({"message": "Servicio eliminado exitosamente"}), 200
    except Exception as e:
        print(f"Error al eliminar servicio: {e}")
        return jsonify({"message": "Error al eliminar servicio"}), 500
    
@app.route('/clientes', methods=['GET'])
def obtener_clientes():
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_usuario, username, rol, email FROM usuarios")
            clientes = cursor.fetchall()
            return jsonify([
                {
                    "id_usuario": row[0],
                    "username": row[1],
                    "rol": row[2],
                    "email": row[3]
                }
                for row in clientes
            ])
    except Exception as e:
        print(f"Error al obtener clientes: {e}")
        return jsonify({"message": "Error al obtener clientes"}), 500
    
    # Ruta para obtener citas del cliente
@app.route('/tus_citas', methods=['GET'])
def tus_citas():
    cliente_id = obtener_id_usuario_autenticado()
    if cliente_id is None:
        return jsonify({"message": "No estás autenticado."}), 401

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id_cita, fecha_cita, servicio, estado FROM citas WHERE id_usuario = ?", (cliente_id,))
            citas = cursor.fetchall()

            # Agrega este print para depuración
            print("Citas encontradas:", [{
                "id_cita": row[0],
                "fecha_cita": row[1].strftime("%Y-%m-%d %H:%M"),
                "servicio": row[2],
                "estado": row[3]
            } for row in citas])

            return jsonify([{
                "id_cita": row[0],
                "fecha_cita": row[1].strftime("%Y-%m-%d %H:%M"),
                "servicio": row[2],
                "estado": row[3]
            } for row in citas])
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# Ruta para eliminar una cita por cliente
from datetime import datetime, timedelta

@app.route('/eliminar_cita', methods=['POST'])
def eliminar_cita():
    data = request.get_json()
    id_cita = data.get('id_cita')

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()

            # Obtener la fecha y hora de la cita
            cursor.execute("SELECT fecha_cita FROM citas WHERE id_cita = ?", (id_cita,))
            cita = cursor.fetchone()
            if not cita:
                return jsonify({"message": "Cita no encontrada"}), 404

            fecha_cita = cita[0]
            ahora = datetime.now()
            diferencia = fecha_cita - ahora

            # Verificar si quedan al menos 5 horas
            if diferencia < timedelta(hours=5):
                return jsonify({"message": "No puedes cancelar la cita con menos de 5 horas de anticipación.", "contact_admin": True}), 400

            # Eliminar la cita si es válida
            cursor.execute("DELETE FROM citas WHERE id_cita = ?", (id_cita,))
            conn.commit()
            return jsonify({"message": "Cita eliminada exitosamente."}), 200
    except Exception as e:
        print(f"Error al eliminar la cita: {e}")
        return jsonify({"message": "Error al eliminar la cita"}), 500


# Ruta para actualizar el estado de una cita (usada por el admin)
@app.route('/actualizar_estado_cita', methods=['POST'])
def actualizar_estado_cita():
    data = request.get_json()
    id_cita = data.get('id_cita')
    nuevo_estado = data.get('nuevo_estado')

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            
            if nuevo_estado == "Realizado":
                cursor.execute("DELETE FROM citas WHERE id_cita = ?", (id_cita,))
            else:
                cursor.execute("UPDATE citas SET estado = ? WHERE id_cita = ?", (nuevo_estado, id_cita))
            
            conn.commit()
            return jsonify({"message": "Estado actualizado exitosamente."}), 200
    except Exception as e:
        print(f"Error al actualizar el estado de la cita: {e}")
        return jsonify({"message": "Error al actualizar el estado de la cita"}), 500
    
@app.route('/eliminar_trabajo', methods=['DELETE'])
def eliminar_trabajo():
    data = request.get_json()
    id_trabajo = data.get('id_trabajo')
    
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM trabajos WHERE id_trabajo = ?", (id_trabajo,))
            conn.commit()
        return jsonify({"message": "Trabajo eliminado exitosamente."}), 200
    except Exception as e:
        print(f"Error al eliminar trabajo: {e}")
        return jsonify({"message": "Error al eliminar trabajo"}), 500



if __name__ == '__main__':
    app.run(debug=True)
