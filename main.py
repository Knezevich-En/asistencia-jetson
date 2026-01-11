import cv2
import sqlite3
import numpy as np
import os
import time
import face_recognition
import sys 

# --- NFC Imports ---
from smartcard.System import readers
from smartcard.util import toHexString

# --- Configuración General ---
DB_FILE = "asistencia.db"
FOTOS_PATH = "rostros_conocidos" 
CAP_ID = 0  # 0 para cámara USB o CSI

# --- Variables Globales ---
ESTUDIANTES_DB = {}   
CONOCIDOS_ENCODINGS = [] 
CONOCIDOS_IDS = []       
ULTIMO_REGISTRO = {}     


def cargar_datos_ia():
    """ Carga los perfiles de la BD y calcula los encodings faciales. """
    print("--- 1. Cargando datos de IA ---")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, archivo_foto, uid_nfc FROM Estudiantes")
    estudiantes = cursor.fetchall()
    conn.close()

    if not estudiantes:
        print("ADVERTENCIA: No hay estudiantes registrados.")
        return False

    for id_db, nombre, foto_archivo, uid_nfc in estudiantes:
        ruta_foto = os.path.join(FOTOS_PATH, foto_archivo)
        
        if not os.path.exists(ruta_foto):
            print(f"ERROR: Foto no encontrada para {nombre} en {ruta_foto}")
            continue

        try:
            imagen = face_recognition.load_image_file(ruta_foto)
            encodings = face_recognition.face_encodings(imagen)
            
            if len(encodings) > 0:
                CONOCIDOS_ENCODINGS.append(encodings[0])
                CONOCIDOS_IDS.append(id_db)
                uid_sin_espacios = uid_nfc.replace(" ", "") 
                ESTUDIANTES_DB[id_db] = {'nombre': nombre, 'uid': uid_sin_espacios}
                print(f" -> OK: {nombre} cargado.")
            else:
                print(f"ADVERTENCIA: No se encontró cara en la foto de {nombre}.")
        
        except Exception:
            pass 
                
    return True


def registrar_asistencia(estudiante_id, metodo):
    """ Registra la asistencia en la base de datos y aplica restricción de tiempo (30s). """
    global ULTIMO_REGISTRO
    
    ahora = time.time()
    if estudiante_id in ULTIMO_REGISTRO and (ahora - ULTIMO_REGISTRO[estudiante_id] < 30): 
        return
            
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Registros (estudiante_id, metodo) VALUES (?, ?)", 
            (estudiante_id, metodo)
        )
        conn.commit()
        conn.close()
        
        ULTIMO_REGISTRO[estudiante_id] = ahora
        
        print(f"\n>>>> ASISTENCIA REGISTRADA: {ESTUDIANTES_DB[estudiante_id]['nombre']} ({metodo}) <<<<")

    except Exception as e:
        print(f"ERROR al registrar en DB: {e}") # Añadimos esto para ver errores de DB


def reconocer_cara(frame):
    """ 
    Detecta y reconoce caras en un frame de video. 
    ¡NO DIBUJA CUADROS para ahorrar recursos y evitar el congelamiento!
    """
    # Convierte la imagen a color RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Usamos el modelo HOG (rápido)
    caras_loc = face_recognition.face_locations(rgb_frame, model="hog") 
    caras_encodings = face_recognition.face_encodings(rgb_frame, caras_loc)
    
    for cara_encoding in caras_encodings:
        coincidencias = face_recognition.compare_faces(CONOCIDOS_ENCODINGS, cara_encoding, tolerance=0.5)
        
        if True in coincidencias:
            distancias = face_recognition.face_distance(CONOCIDOS_ENCODINGS, cara_encoding)
            mejor_match_index = np.argmin(distancias)
            
            if distancias[mejor_match_index] < 0.5: # Umbral de confianza
                id_db = CONOCIDOS_IDS[mejor_match_index]
                # ¡Registro Inmediato!
                registrar_asistencia(id_db, "Facial")


def escanear_nfc(lector):
    """ Intenta leer el UID de una tarjeta si está presente y lo FORMATEA. """
    try:
        connection = lector.createConnection()
        connection.connect()
        
        GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        data, sw1, sw2 = connection.transmit(GET_UID)
        connection.disconnect() 

        if (sw1, sw2) == (0x90, 0x00):
            uid_leido = toHexString(data)
            uid_sin_espacios = uid_leido.replace(" ", "") 
            return uid_sin_espacios
        
    except Exception:
        return None 


def buscar_estudiante_por_nfc(uid_sin_espacios):
    """ Busca en la BD el estudiante asociado al UID sin espacios. """
    for id_db, data in ESTUDIANTES_DB.items():
        if data['uid'] == uid_sin_espacios: 
            return id_db, data['nombre']
    return None, "Desconocido"


def main():
    # --- Pausa de Arranque (¡Extendida a 20 segundos para estabilidad!) ---
    print("PAUSA: Esperando 20 segundos para que otros servicios inicien y el sistema se estabilice.")
    time.sleep(20) 
    # ----------------------------------------
    
    if not cargar_datos_ia():
        return

    print("--- 2. Inicializando Hardware ---")
    
    # --- Inicialización de la CÁMARA (Acepta fallo) ---
    cap = cv2.VideoCapture(CAP_ID)
    usar_camara = cap.isOpened()
    if not usar_camara:
        print("ADVERTENCIA: Cámara no detectada. El reconocimiento facial estará DESACTIVADO.")
    else:
        print("Cámara lista para reconocimiento facial.")

    # --- Inicialización del NFC ---
    lector_nfc = None
    usar_nfc = False
    try:
        lector_list = readers()
        lector_nfc = lector_list[0] if lector_list else None
        if lector_nfc:
            usar_nfc = True
            print("Lector NFC (ACR122U) listo.")
        else:
             print("ADVERTENCIA: Lector NFC no encontrado. Función de tarjeta DESACTIVADA.")
    except Exception:
        print("ERROR: Servicio pcscd fallido. Función de tarjeta DESACTIVADA.")
    
    if not usar_camara and not usar_nfc:
        print("\nERROR CRÍTICO: Ningún método de identificación está activo. Deteniendo sistema.")
        return

    print("\n>>>> INICIO DEL SISTEMA DE ASISTENCIA <<<<")
    
    # --- Variables para Frame Skipping (simplificado) ---
    frame_counter = 0

    try:
        while True:
            # --- Módulo de Visión (IA) ---
            if usar_camara:
                ret, frame = cap.read()
                if not ret:
                    print("Error: No se pudo leer el frame de la cámara.")
                    break 

                frame_counter += 1
                
                # Procesa solo 1 de cada 4 frames para IA 
                if frame_counter % 4 == 0:
                    reconocer_cara(frame) # Llama a la IA, que ahora solo registra
                    frame_counter = 0
                
                # Muestra el video (sin cuadros, rápido)
                cv2.imshow("Asistencia Activa", frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            # --- Módulo NFC ---
            if usar_nfc:
                uid_sin_espacios = escanear_nfc(lector_nfc) 
                if uid_sin_espacios:
                    estudiante_id, nombre = buscar_estudiante_por_nfc(uid_sin_espacios)
                    if estudiante_id:
                        registrar_asistencia(estudiante_id, "NFC")
                
                if not usar_camara:
                    time.sleep(0.1) 

    except KeyboardInterrupt:
        print("\nSistema detenido por el usuario.")
    
    finally:
        if usar_camara:
            cap.release()
            cv2.destroyAllWindows()
        print("Sistemas cerrados. ¡Sistema apagado!")


if __name__ == "__main__":
    main()
