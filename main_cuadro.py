import cv2
import sqlite3
import numpy as np
import os
import time
import json
import face_recognition
from datetime import datetime
from smartcard.System import readers
from smartcard.util import toHexString

# ===========================
# CONFIGURACION Y PERSISTENCIA
# ===========================

DB_FILE = "asistencia.db"
FOTOS_PATH = "rostros_conocidos"
CONFIG_FILE = "config_sistema.json"

# --- SELECCIÓN DE MODELO DE IA ---
MODELO_DETECCION = "cnn"  # "hog" (CPU) o "cnn" (GPU/Jetson)

DEFAULT_CONFIG = {
    "ip_camara": "http://192.168.1.10:4747/video",
    "password_gui": "1234" 
}

CONFIG_ACTUAL = DEFAULT_CONFIG.copy()
CAP_ID = CONFIG_ACTUAL["ip_camara"]

def cargar_configuracion():
    global CONFIG_ACTUAL, CAP_ID
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                CONFIG_ACTUAL = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in CONFIG_ACTUAL: CONFIG_ACTUAL[k] = v
        except: 
            CONFIG_ACTUAL = DEFAULT_CONFIG.copy()
    else:
        guardar_configuracion()

    CAP_ID = CONFIG_ACTUAL["ip_camara"]
    if str(CAP_ID).isdigit(): CAP_ID = int(CAP_ID)

def guardar_configuracion():
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(CONFIG_ACTUAL, f, indent=4)
    except: pass

def actualizar_parametros(nueva_ip, nueva_pass=None):
    global CONFIG_ACTUAL, CAP_ID
    CONFIG_ACTUAL["ip_camara"] = nueva_ip
    if str(nueva_ip).isdigit(): CAP_ID = int(nueva_ip)
    else: CAP_ID = nueva_ip
    if nueva_pass and nueva_pass.strip() != "":
        CONFIG_ACTUAL["password_gui"] = nueva_pass.strip()
    guardar_configuracion()

def verificar_password(password_ingresada):
    return password_ingresada == CONFIG_ACTUAL["password_gui"]

cargar_configuracion()

# ===========================
# VARIABLES GLOBALES IA Y HORARIOS
# ===========================
ESTUDIANTES_DB = {}
ENCODINGS = []
IDS = []
ULTIMO_INTENTO = {} 

# --- NUEVAS VARIABLES PARA MATERIAS ---
MATERIAS_DB = {}      # { id: {nombre, inicio, fin, dias} }
INSCRIPCIONES_DB = {} # { materia_id: [lista_estudiantes_ids] }
MATERIA_ACTUAL_INFO = None # Guardará la info de la clase activa o None

def cargar_datos_ia():
    global ESTUDIANTES_DB, ENCODINGS, IDS, MATERIAS_DB, INSCRIPCIONES_DB
    ESTUDIANTES_DB.clear()
    ENCODINGS.clear()
    IDS.clear()
    MATERIAS_DB.clear()
    INSCRIPCIONES_DB.clear()

    if not os.path.exists(DB_FILE):
        print("Base de datos no encontrada.")
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 1. Cargar Estudiantes
        cursor.execute("SELECT id, nombre, archivo_foto, uid_nfc FROM Estudiantes")
        filas = cursor.fetchall()

        # 2. Cargar Materias con Horarios
        # dias se guarda como texto "0,2,4"
        try:
            cursor.execute("SELECT id, nombre, hora_inicio, hora_fin, dias FROM Materias")
            for mid, mnombre, hini, hfin, dias_str in cursor.fetchall():
                lista_dias = []
                if dias_str:
                    lista_dias = [int(d) for d in dias_str.split(",")]
                
                MATERIAS_DB[mid] = {
                    "nombre": mnombre,
                    "inicio": hini,
                    "fin": hfin,
                    "dias": lista_dias
                }
                INSCRIPCIONES_DB[mid] = []
            
            # 3. Cargar Inscripciones
            cursor.execute("SELECT materia_id, estudiante_id FROM Inscripciones")
            for mid, eid in cursor.fetchall():
                if mid in INSCRIPCIONES_DB:
                    INSCRIPCIONES_DB[mid].append(eid)
        except Exception as e:
            print(f"Tablas de materias aun no creadas o vacias: {e}")

        conn.close()
    except Exception as e:
        print(f"Error leyendo BD: {e}")
        return

    print("--- Cargando Base de Datos e IA ---")
    for sid, nombre, foto, uid in filas:
        tipo_usuario = "solo nfc"
        tiene_foto_valida = False
        if foto:
            ruta = os.path.join(FOTOS_PATH, foto)
            if os.path.exists(ruta):
                try:
                    img = face_recognition.load_image_file(ruta)
                    encs = face_recognition.face_encodings(img)
                    if encs:
                        ENCODINGS.append(encs[0])
                        IDS.append(sid)
                        tiene_foto_valida = True
                except: pass

        if tiene_foto_valida: tipo_usuario = "nfc + IA"

        ESTUDIANTES_DB[sid] = {
            "nombre": nombre,
            "uid": uid.replace(" ", "") if uid else "",
            "tipo": tipo_usuario
        }
    
    # Al terminar de cargar, calculamos si hay clase AHORA
    actualizar_bloque_horario()
    print(f"IA cargada. Perfiles: {len(ESTUDIANTES_DB)}. Materias: {len(MATERIAS_DB)}")

# --- LOGICA DE HORARIO AUTOMATICO ---
def actualizar_bloque_horario():
    global MATERIA_ACTUAL_INFO
    
    now = datetime.now()
    dia_semana = now.weekday() # 0=Lunes, 6=Domingo
    hora_actual = now.strftime("%H:%M") # Formato "14:30"
    
    MATERIA_ACTUAL_INFO = None # Resetear
    
    # Buscamos si alguna materia coincide con AHORA
    for mid, datos in MATERIAS_DB.items():
        if dia_semana in datos["dias"]:
            # Comparamos cadenas de hora (funciona bien en formato HH:MM de 24h)
            if datos["inicio"] <= hora_actual <= datos["fin"]:
                MATERIA_ACTUAL_INFO = {
                    "id": mid,
                    "nombre": datos["nombre"]
                }
                print(f"CLASE DETECTADA: {datos['nombre']}")
                return

    print("INFO: No hay clase programada en este momento.")

# ===========================
# REGISTRO INTELIGENTE (CON VALIDACION)
# ===========================
def registrar_asistencia(sid, metodo_origen):
    global ULTIMO_INTENTO, MATERIA_ACTUAL_INFO
    
    # 1. VERIFICAR SI HAY CLASE ACTIVA
    if MATERIA_ACTUAL_INFO is None:
        # Si no hay clase, decidimos si bloqueamos o no. 
        # Según tu pedido: "verificar si esta en esa materia". 
        # Si no hay materia, no se puede registrar asistencia a clases.
        return "FUERA_HORARIO"

    # 2. VERIFICAR INSCRIPCION
    materia_id = MATERIA_ACTUAL_INFO["id"]
    inscritos = INSCRIPCIONES_DB.get(materia_id, [])
    
    if sid not in inscritos:
        return "NO_INSCRITO"

    # 3. Lógica normal de duplicados y tiempo
    now = time.time()
    if sid in ULTIMO_INTENTO and now - ULTIMO_INTENTO[sid] < 3:
        return "ESPERA"

    estudiante = ESTUDIANTES_DB.get(sid)
    if not estudiante: return "ERROR"

    nombre = estudiante["nombre"]
    ULTIMO_INTENTO[sid] = now 
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Opcional: Podríamos guardar el ID de materia en Registros, 
        # pero para no romper compatibilidad dejamos la tabla Registros igual por ahora.
        cursor.execute("""
            SELECT id FROM Registros 
            WHERE estudiante_id = ? AND date(fecha_hora) = date('now', 'localtime')
        """, (sid,))
        existe = cursor.fetchone()
        
        if existe:
            conn.close()
            return "DUPLICADO"

        fecha_log = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO Registros (estudiante_id, metodo, fecha_hora) VALUES (?, ?, ?)",
            (sid, metodo_origen, fecha_log))
        conn.commit()
        conn.close()
        
        print(f"Registro Exitoso en {MATERIA_ACTUAL_INFO['nombre']}: {nombre}")
        return "EXITO"

    except Exception as e: 
        print(f"Error BD: {e}")
        return "ERROR"

# ===========================
# PROCESAMIENTO DE VIDEO
# ===========================
def procesar_cara(frame, msg_callback):
    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    if MODELO_DETECCION == "cnn":
        locs = face_recognition.face_locations(rgb_small, model="cnn", number_of_times_to_upsample=1)
    else:
        locs = face_recognition.face_locations(rgb_small, model="hog")

    encs = face_recognition.face_encodings(rgb_small, locs)
    resultados_dibujo = []

    for enc, loc in zip(encs, locs):
        nombre_mostrar = "Desconocido"
        match = face_recognition.compare_faces(ENCODINGS, enc, tolerance=0.5)
        if True in match:
            idx = np.argmin(face_recognition.face_distance(ENCODINGS, enc))
            sid = IDS[idx]
            nombre_mostrar = ESTUDIANTES_DB[sid]["nombre"]
            
            resultado = registrar_asistencia(sid, "VISION")
            
            # --- MANEJO DE RESPUESTAS ---
            if resultado == "EXITO":
                msg_callback(f"VISION_OK:{nombre_mostrar}")
            elif resultado == "DUPLICADO":
                msg_callback(f"VISION_DUP:{nombre_mostrar}")
            elif resultado == "NO_INSCRITO":
                msg_callback(f"VISION_NO_INSCRITO:{nombre_mostrar}")
            elif resultado == "FUERA_HORARIO":
                msg_callback("VISION_FUERA:Sin Clase")
        
        top, right, bottom, left = loc
        resultados_dibujo.append((nombre_mostrar, top*4, right*4, bottom*4, left*4))

    for nombre, top, right, bottom, left in resultados_dibujo:
        color = (0, 255, 0) if nombre != "Desconocido" else (0, 0, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(frame, nombre, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
    return frame

# ===========================
# NFC
# ===========================
def iniciar_nfc():
    try:
        r = readers()
        return r[0] if r else None
    except: return None

def leer_nfc(lector):
    try:
        c = lector.createConnection()
        c.connect()
        data, sw1, sw2 = c.transmit([0xFF,0xCA,0x00,0x00,0x00])
        c.disconnect()
        if (sw1,sw2)==(0x90,0x00): return toHexString(data).replace(" ","")
    except: return None

def buscar_por_uid(uid):
    for sid, data in ESTUDIANTES_DB.items():
        if data["uid"] == uid: return sid, data["nombre"]
    return None, None
