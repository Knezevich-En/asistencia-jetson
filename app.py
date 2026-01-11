import sqlite3
from flask import Flask, render_template, redirect, url_for, request, session, Response, jsonify
from datetime import datetime
from functools import wraps
import os
import csv
from io import StringIO
# LIBRERÍAS DE CORREO
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash 
from smartcard.System import readers
import main_cuadro 

app = Flask(__name__) 
app.secret_key = 'CLAVE_SECRETA_PROYECTO_FINAL_12345' 


# CONFIGURACIÓN DEL CORREO 
EMAIL_SENDER = "fkaknezevi@gmail.com"        
EMAIL_PASSWORD = "htes dfzw oene ablw"     
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587

DB_FILE = "asistencia.db"
FOTOS_PATH = "rostros_conocidos"
app.config['FOTOS_PATH'] = FOTOS_PATH

# -----------------------------------------------------------------
# INICIALIZACIÓN DE LA BASE DE DATOS
# -----------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Tablas Base
    c.execute('''CREATE TABLE IF NOT EXISTS Admin (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Estudiantes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, uid_nfc TEXT, archivo_foto TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Registros (id INTEGER PRIMARY KEY AUTOINCREMENT, estudiante_id INTEGER, metodo TEXT, fecha_hora TEXT, FOREIGN KEY(estudiante_id) REFERENCES Estudiantes(id))''')
    
    # 2. Nuevas Tablas para Materias y Horarios
    c.execute('''CREATE TABLE IF NOT EXISTS Materias (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nombre TEXT NOT NULL,
        hora_inicio TEXT,
        hora_fin TEXT,
        dias TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS Inscripciones (
        materia_id INTEGER, 
        estudiante_id INTEGER, 
        PRIMARY KEY (materia_id, estudiante_id),
        FOREIGN KEY(materia_id) REFERENCES Materias(id),
        FOREIGN KEY(estudiante_id) REFERENCES Estudiantes(id)
    )''')

    # 3. Usuario Admin por defecto
    c.execute("SELECT count(*) FROM Admin")
    if c.fetchone()[0] == 0:
        pass_hash = generate_password_hash("12345")
        c.execute("INSERT INTO Admin (username, password) VALUES (?, ?)", ("profesor", pass_hash))
        print("INFO: Base de datos inicializada correctamente.")
        
    conn.commit()
    conn.close()

# Ejecutar al iniciar
init_db()

# -----------------------------------------------------------------
# FUNCIONES AUXILIARES
# -----------------------------------------------------------------

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# -----------------------------------------------------------------
# RUTAS PRINCIPALES (DASHBOARD)
# -----------------------------------------------------------------

@app.route('/')
@login_required 
def index():
    conn = get_db_connection()
    # Filtramos por HOY para el dashboard
    asistencia = conn.execute("""
        SELECT E.nombre, R.fecha_hora, R.metodo 
        FROM Registros R JOIN Estudiantes E ON R.estudiante_id = E.id
        WHERE date(R.fecha_hora) = date('now', 'localtime')
        ORDER BY R.fecha_hora DESC
    """).fetchall()
    
    total_estudiantes = conn.execute("SELECT count(*) FROM Estudiantes").fetchone()[0]
    nombres = {reg['nombre'] for reg in asistencia}
    conn.close()

    fecha_hoy = datetime.now().strftime('%Y-%m-%d')

    return render_template('index.html', asistencia=asistencia, 
                           total_estudiantes=total_estudiantes, asistencia_hoy=len(nombres),
                           fecha_filtro=fecha_hoy)

# -----------------------------------------------------------------
# HISTORIAL CON FILTROS (MATERIA + FECHA)
# -----------------------------------------------------------------
@app.route('/historial', methods=['GET', 'POST'])
@login_required
def historial():
    conn = get_db_connection()
    # 1. Obtener lista de materias para el dropdown del filtro
    materias = conn.execute("SELECT * FROM Materias ORDER BY nombre ASC").fetchall()
    
    registros = []
    fecha_busqueda = ""
    materia_filtro = ""

    # 2. Si es POST, obtenemos filtros del formulario
    if request.method == 'POST':
        fecha_busqueda = request.form.get('fecha', '')
        materia_filtro = request.form.get('materia', '')

    # 3. Construimos la consulta SQL Dinámica
    sql = """
        SELECT E.nombre, R.fecha_hora, R.metodo 
        FROM Registros R 
        JOIN Estudiantes E ON R.estudiante_id = E.id
    """
    conditions = []
    params = []

    # Filtro por Materia (JOIN con Inscripciones si es necesario saber a qué materia pertenece el alumno,
    # OJO: Aquí asumimos que queremos ver registros de alumnos INSCRITOS en esa materia)
    if materia_filtro and materia_filtro.strip():
        sql += " JOIN Inscripciones I ON E.id = I.estudiante_id "
        conditions.append("I.materia_id = ?")
        params.append(materia_filtro)

    # Filtro por Fecha
    if fecha_busqueda and fecha_busqueda.strip():
        conditions.append("date(R.fecha_hora) = ?")
        params.append(fecha_busqueda)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    
    sql += " ORDER BY R.fecha_hora DESC"
    
    # Límite por defecto si no hay filtros para no saturar la vista
    if not conditions:
        sql += " LIMIT 200"

    registros = conn.execute(sql, params).fetchall()
    conn.close()
    
    # Convertir materia_filtro a int para mantener la selección en el HTML
    m_id_sel = int(materia_filtro) if materia_filtro and materia_filtro.isdigit() else None

    return render_template('historial.html', registros=registros, 
                           materias=materias,
                           fecha_actual=fecha_busqueda,
                           materia_actual=m_id_sel)

# -----------------------------------------------------------------
# RUTAS GESTION Y LOGIN
# -----------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM Admin WHERE username = ?", (request.form['username'],)).fetchone()
        conn.close()
        if admin and check_password_hash(admin['password'], request.form['password']):
            session['logged_in'] = True; session['username'] = request.form['username']
            return redirect(url_for('index'))
        else: error = 'Credenciales inválidas.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/configuracion', methods=['GET', 'POST'])
@login_required
def configuracion():
    mensaje = None
    if request.method == 'POST':
        conn = get_db_connection()
        admin = conn.execute("SELECT * FROM Admin WHERE username = ?", (session['username'],)).fetchone()
        if admin and check_password_hash(admin['password'], request.form['pass_actual']):
            try:
                conn.execute("UPDATE Admin SET username = ?, password = ? WHERE id = ?", 
                             (request.form['nuevo_user'], generate_password_hash(request.form['nueva_pass']), admin['id']))
                conn.commit(); session['username'] = request.form['nuevo_user']; mensaje = "Actualizado con éxito"
            except: mensaje = "Error: Usuario ya existe"
        else: mensaje = "Contraseña actual incorrecta"
        conn.close()
    return render_template('configuracion.html', mensaje=mensaje)

# -----------------------------------------------------------------
# GESTIÓN DE ESTUDIANTES (ACTUALIZADA CON MATERIAS)
# -----------------------------------------------------------------

@app.route('/estudiantes')
@login_required 
def listar_estudiantes():
    conn = get_db_connection()
    est = conn.execute("SELECT * FROM Estudiantes ORDER BY nombre ASC").fetchall()
    conn.close()
    return render_template('estudiantes.html', estudiantes=est)

@app.route('/estudiantes/agregar', methods=['GET', 'POST'])
@login_required
def agregar_estudiante():
    conn = get_db_connection()
    if request.method == 'POST':
        # 1. Guardar Estudiante
        f = request.files['foto']; fn = secure_filename(f.filename) if f else None
        if fn: f.save(os.path.join(app.config['FOTOS_PATH'], fn))
        
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Estudiantes (nombre, uid_nfc, archivo_foto) VALUES (?, ?, ?)", 
                       (request.form['nombre'], request.form['uid_nfc'].replace(" ",""), fn))
        estudiante_id = cursor.lastrowid # ID del nuevo estudiante
        
        # 2. Guardar Inscripciones (Materias seleccionadas en checkboxes)
        materias_seleccionadas = request.form.getlist('materias')
        for materia_id in materias_seleccionadas:
            cursor.execute("INSERT INTO Inscripciones (materia_id, estudiante_id) VALUES (?, ?)", (materia_id, estudiante_id))
            
        conn.commit()
        conn.close()
        return redirect(url_for('listar_estudiantes'))
    
    # GET: Enviamos materias para llenar los checkboxes
    materias = conn.execute("SELECT * FROM Materias ORDER BY nombre ASC").fetchall()
    conn.close()
    return render_template('agregar_estudiante.html', materias=materias)

@app.route('/estudiantes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_estudiante(id):
    conn = get_db_connection()
    est = conn.execute("SELECT * FROM Estudiantes WHERE id = ?", (id,)).fetchone()
    if not est: return "No encontrado", 404
    
    if request.method == 'POST':
        # 1. Actualizar Datos Básicos
        f = request.files['foto']; fn = est['archivo_foto']
        if f and f.filename != '':
            if fn: 
                try: os.remove(os.path.join(app.config['FOTOS_PATH'], fn))
                except: pass
            fn = secure_filename(f.filename); f.save(os.path.join(app.config['FOTOS_PATH'], fn))
            
        conn.execute("UPDATE Estudiantes SET nombre=?, uid_nfc=?, archivo_foto=? WHERE id=?", 
                     (request.form['nombre'], request.form['uid_nfc'].replace(" ",""), fn, id))
        
        # 2. Actualizar Inscripciones (Borrar anteriores -> Insertar nuevas)
        conn.execute("DELETE FROM Inscripciones WHERE estudiante_id = ?", (id,))
        
        materias_seleccionadas = request.form.getlist('materias')
        for materia_id in materias_seleccionadas:
            conn.execute("INSERT INTO Inscripciones (materia_id, estudiante_id) VALUES (?, ?)", (materia_id, id))
            
        conn.commit()
        conn.close()
        return redirect(url_for('listar_estudiantes'))
    
    # GET: Obtenemos materias e inscripciones actuales
    materias = conn.execute("SELECT * FROM Materias ORDER BY nombre ASC").fetchall()
    inscripciones = conn.execute("SELECT materia_id FROM Inscripciones WHERE estudiante_id = ?", (id,)).fetchall()
    ids_inscritos = [row['materia_id'] for row in inscripciones]
    
    conn.close()
    return render_template('editar_estudiante.html', estudiante=est, materias=materias, inscritos=ids_inscritos)

@app.route('/estudiantes/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_estudiante(id):
    conn = get_db_connection()
    est = conn.execute("SELECT archivo_foto FROM Estudiantes WHERE id=?", (id,)).fetchone()
    if est and est['archivo_foto']:
        try: os.remove(os.path.join(app.config['FOTOS_PATH'], est['archivo_foto']))
        except: pass
    
    # Eliminar registros relacionados para mantener integridad
    conn.execute("DELETE FROM Inscripciones WHERE estudiante_id=?", (id,))
    conn.execute("DELETE FROM Registros WHERE estudiante_id=?", (id,))
    conn.execute("DELETE FROM Estudiantes WHERE id=?", (id,))
    
    conn.commit()
    conn.close()
    return redirect(url_for('listar_estudiantes'))

@app.route('/api/scan_nfc')
@login_required 
def api_scan_nfc():
    try:
        r = readers()
        if not r: return jsonify({"error": "No lector"}), 500
        uid = main_cuadro.leer_nfc(r[0]) 
        if uid: return jsonify({"uid": uid})
        return jsonify({"error": "Tiempo agotado"}), 404
    except Exception as e: return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------
# GESTIÓN DE MATERIAS (NUEVO)
# -----------------------------------------------------------------

@app.route('/materias')
@login_required
def listar_materias():
    conn = get_db_connection()
    materias = conn.execute("""
        SELECT M.*, COUNT(I.estudiante_id) as total_alumnos
        FROM Materias M
        LEFT JOIN Inscripciones I ON M.id = I.materia_id
        GROUP BY M.id
        ORDER BY M.nombre ASC
    """).fetchall()
    conn.close()
    return render_template('materias.html', materias=materias)

@app.route('/materias/agregar', methods=['POST'])
@login_required
def agregar_materia():
    nombre = request.form['nombre']
    h_ini = request.form['hora_inicio']
    h_fin = request.form['hora_fin']
    # 'dias' viene como lista ["0", "2", "4"] -> convertimos a string "0,2,4"
    lista_dias = request.form.getlist('dias')
    dias_str = ",".join(lista_dias)

    if nombre and h_ini and h_fin:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO Materias (nombre, hora_inicio, hora_fin, dias) VALUES (?, ?, ?, ?)", 
            (nombre, h_ini, h_fin, dias_str)
        )
        conn.commit()
        conn.close()
    return redirect(url_for('listar_materias'))

@app.route('/materias/eliminar/<int:id>')
@login_required
def eliminar_materia(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM Inscripciones WHERE materia_id = ?", (id,))
    conn.execute("DELETE FROM Materias WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('listar_materias'))

@app.route('/materias/gestionar/<int:id>', methods=['GET', 'POST'])
@login_required
def gestionar_materia(id):
    conn = get_db_connection()
    materia = conn.execute("SELECT * FROM Materias WHERE id = ?", (id,)).fetchone()
    
    if request.method == 'POST':
        # Borrar inscripciones viejas de esta materia
        conn.execute("DELETE FROM Inscripciones WHERE materia_id = ?", (id,))
        # Insertar nuevas
        ids_seleccionados = request.form.getlist('estudiantes')
        for est_id in ids_seleccionados:
            conn.execute("INSERT INTO Inscripciones (materia_id, estudiante_id) VALUES (?, ?)", (id, est_id))
        conn.commit()
        conn.close()
        return redirect(url_for('listar_materias'))

    # GET
    todos_estudiantes = conn.execute("SELECT id, nombre FROM Estudiantes ORDER BY nombre ASC").fetchall()
    inscritos = conn.execute("SELECT estudiante_id FROM Inscripciones WHERE materia_id = ?", (id,)).fetchall()
    inscritos_ids = [row['estudiante_id'] for row in inscritos]
    
    conn.close()
    return render_template('gestionar_materia.html', materia=materia, estudiantes=todos_estudiantes, inscritos=inscritos_ids)


# -----------------------------------------------------------------
# LÓGICA DE EXPORTACIÓN Y ENVÍO DE CORREO (ACTUALIZADA)
# -----------------------------------------------------------------

def generar_csv_string(fecha=None, materia_id=None):
    """Genera el contenido del CSV en memoria, filtrando por fecha y/o materia."""
    conn = get_db_connection()
    
    # Query Base
    sql = """
        SELECT E.nombre, R.fecha_hora, R.metodo 
        FROM Registros R 
        JOIN Estudiantes E ON R.estudiante_id = E.id
    """
    conditions = []
    params = []

    # Filtro Materia
    if materia_id and str(materia_id).strip() != "":
        sql += " JOIN Inscripciones I ON E.id = I.estudiante_id "
        conditions.append("I.materia_id = ?")
        params.append(materia_id)

    # Filtro Fecha
    if fecha and fecha.strip() != "":
        conditions.append("date(R.fecha_hora) = ?")
        params.append(fecha)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    
    sql += " ORDER BY R.fecha_hora DESC"

    registros = conn.execute(sql, params).fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nombre del Estudiante', 'Fecha y Hora', 'Metodo de Entrada'])
    for r in registros:
        writer.writerow([r['nombre'], r['fecha_hora'], r['metodo']])
    return output.getvalue()

@app.route('/exportar')
@login_required 
def exportar():
    fecha_filtro = request.args.get('fecha', '')
    materia_filtro = request.args.get('materia', '')
    
    csv_content = generar_csv_string(fecha_filtro, materia_filtro)
    
    # Nombre de archivo dinámico
    nombre_archivo = "asistencia"
    if materia_filtro: nombre_archivo += f"_materia{materia_filtro}"
    if fecha_filtro: nombre_archivo += f"_{fecha_filtro}"
    nombre_archivo += ".csv"
    
    return Response(csv_content, mimetype="text/csv", headers={"Content-disposition":f"attachment; filename={nombre_archivo}"})

@app.route('/enviar_email', methods=['POST'])
@login_required
def enviar_email():
    email_destino = request.form['email_destino']
    fecha_filtro = request.form['fecha_filtro']
    # Recibimos el filtro de materia del formulario oculto
    materia_filtro = request.form.get('materia_filtro', '') 
    
    csv_content = generar_csv_string(fecha_filtro, materia_filtro)
    
    nombre_archivo = "reporte_asistencia.csv"

    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = email_destino
    msg['Subject'] = f"Reporte de Asistencia"

    body_msg = "Hola,\n\nAdjunto encontrarás el reporte solicitado.\n"
    if fecha_filtro: body_msg += f"Fecha: {fecha_filtro}\n"
    if materia_filtro: body_msg += f"Filtrado por Materia ID: {materia_filtro}\n"
    msg.attach(MIMEText(body_msg, 'plain'))

    part = MIMEBase('application', "octet-stream")
    part.set_payload(csv_content.encode('utf-8'))
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename="{nombre_archivo}"')
    msg.attach(part)

    try:
        server = smtplib.SMTP(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_SENDER, email_destino, text)
        server.quit()
        if 'Referer' in request.headers:
            return redirect(request.headers['Referer'])
        return redirect(url_for('index'))
    except Exception as e:
        return f"Error al enviar correo: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
