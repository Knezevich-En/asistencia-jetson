import PySimpleGUI as sg
import cv2
import threading
import sys
import webbrowser
import time

# --- Importamos la lógica de TUS archivos ---
try:
    from app import app as flask_app
    import main_cuadro
except ImportError as e:
    print(f"Error: No se pudieron importar tus scripts. Asegúrate que gui_app.py esté en la misma carpeta.")
    print(e)
    sys.exit(1)

# --- Hilo para correr el servidor Flask ---
servidor_iniciado = False
def iniciar_servidor_flask():
    global servidor_iniciado
    try:
        servidor_iniciado = True
        print("Iniciando servidor Flask en un hilo...")
        flask_app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"Error al iniciar el servidor Flask: {e}")

# ===================================================================
# PANTALLA 2: LÓGICA DE ASISTENCIA (se ejecuta en un hilo)
# ===================================================================
def bucle_logica_asistencia(window):
    """
    Esta es la función que corre en un hilo separado.
    Maneja OpenCV y NFC, y envía actualizaciones a la ventana.
    """
    global datos_rostros_conocidos
    
    # --- Iniciar Cámara ---
    captura = cv2.VideoCapture(0)
    if not captura.isOpened():
        print("¡Error! No se pudo abrir la cámara.")
        # Envía un evento a la ventana principal para mostrar el error
        window.write_event_value('-ACTUALIZAR_ESTADO-', ("Error: Cámara no encontrada. NFC sigue activo.", 'red'))
    
    # --- Iniciar Lector NFC ---
    ser = None
    try:
        ser = main_cuadro.conectar_puerto_serial()
        if ser:
            print(f"Conectado a {ser.portstr} para NFC.")
        else:
            print("No se pudo conectar al puerto serial para NFC.")
            window.write_event_value('-ACTUALIZAR_ESTADO-', ("Error: No se detectó lector NFC", 'red'))
    except Exception as e:
        print(f"Error al iniciar serial: {e}")
        window.write_event_value('-ACTUALIZAR_ESTADO-', (f"Error Serial: {e}", 'red'))

    nombres_conocidos = datos_rostros_conocidos[0]
    codificaciones_conocidas = datos_rostros_conocidos[1]

    # Bucle principal de lógica
    while True:
        # --- 1. Lógica NFC (Siempre se ejecuta) ---
        if ser:
            try:
                uid_nfc = main_cuadro.leer_puerto_serial(ser)
                if uid_nfc:
                    print(f"NFC Detectado: {uid_nfc}")
                    main_cuadro.registrar_asistencia_nfc(uid_nfc)
                    
                    # Enviar evento de actualización a la GUI
                    mensaje = f"Asistencia NFC Registrada\nUID: {uid_nfc}"
                    window.write_event_value('-ACTUALIZAR_ESTADO-', (mensaje, 'green'))
                    time.sleep(3) # Pausa para mostrar el mensaje
                    if captura.isOpened():
                        window.write_event_value('-ACTUALIZAR_ESTADO-', ("Mire a la cámara o pase su tarjeta", 'white'))
                    else:
                        window.write_event_value('-ACTUALIZAR_ESTADO-', ("Error: Cámara no encontrada. NFC sigue activo.", 'red'))
            except Exception as e:
                print(f"Error en bucle serial: {e}")

        # --- 2. Lógica de Cámara (SOLO si la cámara está abierta) ---
        if captura and captura.isOpened():
            ret, frame = captura.read()
            if not ret:
                print("Error al leer frame de la cámara")
                time.sleep(0.1)
                continue

            frame_pequeno = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_frame_pequeno = frame_pequeno[:, :, ::-1] # BGR a RGB

            loc_rostros = main_cuadro.face_recognition.face_locations(rgb_frame_pequeno)
            cod_rostros = main_cuadro.face_recognition.face_encodings(rgb_frame_pequeno, loc_rostros)

            for (top, right, bottom, left), cod_rostro in zip(loc_rostros, cod_rostros):
                coincidencias = main_cuadro.face_recognition.compare_faces(codificaciones_conocidas, cod_rostro)
                nombre = "Desconocido"
                color_cuadro = (0, 0, 255) # Rojo

                if True in coincidencias:
                    indice_coincidencia = coincidencias.index(True)
                    nombre = nombres_conocidos[indice_coincidencia]
                    color_cuadro = (0, 255, 0) # Verde
                    main_cuadro.registrar_asistencia_facial(nombre)
                    # Enviar evento de actualización a la GUI
                    window.write_event_value('-ACTUALIZAR_ESTADO-', (f"¡Bienvenido, {nombre}!", 'green'))

                top, right, bottom, left = top * 4, right * 4, bottom * 4, left * 4
                cv2.rectangle(frame, (left, top), (right, bottom), color_cuadro, 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color_cuadro, cv2.FILLED)
                cv2.putText(frame, nombre, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 1)

            # --- 3. Enviar el Frame a la UI ---
            # Convertir frame de OpenCV (BGR) a formato de PySimpleGUIQt (RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            window.write_event_value('-ACTUALIZAR_FRAME-', frame_rgb)
        
        else:
            # Si la cámara falla, envía un frame negro para que el NFC siga activo
            window.write_event_value('-ACTUALIZAR_FRAME-', None)


        time.sleep(0.05) # Pequeña pausa del bucle

# ===================================================================
# PANTALLA 2: Ventana de Asistencia
# ===================================================================
def iniciar_pantalla_asistencia():
    global datos_rostros_conocidos
    
    # Cargar rostros ANTES de abrir la ventana
    try:
        print("Cargando rostros conocidos...")
        datos_rostros_conocidos = main_cuadro.cargar_rostros_conocidos('rostros_conocidos')
        print(f"Se cargaron {len(datos_rostros_conocidos[0])} rostros.")
    except Exception as e:
        print(f"Error al cargar rostros: {e}")
        datos_rostros_conocidos = ([], [])

    # --- Definir el layout de la ventana ---
    layout = [
        [sg.Image(filename='', key='-VISOR_CAMARA-', size=(800, 600))],
        [sg.Text('Iniciando...', key='-ETIQUETA_ESTADO-', font=('Helvetica', 20), justification='center')],
        [sg.Button('Volver al Menú', key='-VOLVER-', size=(20, 2))]
    ]

    # Crear la ventana en pantalla completa
    window = sg.Window('Registro de Asistencia', layout,
                       location=(0, 0),
                       finalize=True,
                       no_titlebar=True,
                       keep_on_top=True)
    window.Maximize()

    # --- Iniciar el hilo de lógica (Cámara y NFC) ---
    threading.Thread(target=bucle_logica_asistencia, args=(window,), daemon=True).start()

    # --- Bucle de la Ventana (GUI) ---
    # Este es el hilo principal, solo actualiza la pantalla
    while True:
        event, values = window.read(timeout=20)

        if event == sg.WIN_CLOSED or event == '-VOLVER-':
            # Detener el hilo de la cámara (aunque al ser 'daemon' se cerrará solo)
            break
        
        if event == '-ACTUALIZAR_FRAME-':
            frame = values[event]
            if frame is not None:
                # Actualizar la imagen
                imgbytes = cv2.imencode('.png', frame)[1].tobytes()
                window['-VISOR_CAMARA-'].update(data=imgbytes)
            else:
                # Mostrar un cuadro negro si la cámara falla
                window['-VISOR_CAMARA-'].update(data=None, size=(800, 600), background_color='black')
                
        if event == '-ACTUALIZAR_ESTADO-':
            mensaje, color = values[event]
            window['-ETIQUETA_ESTADO-'].update(value=mensaje, text_color=color)

    window.close()


# ===================================================================
# PANTALLA 1: Ventana de Menú Principal
# ===================================================================
def iniciar_menu_principal():
    global servidor_iniciado
    
    # sg.theme('DarkBlue') # Puedes cambiar el tema de color

    layout = [
        [sg.Text('Proyecto de Asistencia', font=('Helvetica', 30), justification='center')],
        [sg.Button('1. Iniciar Registro de Asistencia', key='-ASISTENCIA-', font=('Helvetica', 20), size=(30, 3))],
        [sg.Button('2. Iniciar Servidor Web', key='-SERVIDOR-', font=('Helvetica', 20), size=(30, 3))],
        [sg.Button('3. Salir', key='-SALIR-', font=('Helvetica', 20), size=(30, 3))]
    ]

    window = sg.Window('Menú Principal', layout,
                       location=(0, 0),
                       finalize=True,
                       no_titlebar=True,
                       keep_on_top=True)
    window.Maximize() # Poner en pantalla completa

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == '-SALIR-':
            break
        
        if event == '-ASISTENCIA-':
            window.hide() # Oculta el menú
            iniciar_pantalla_asistencia() # Lanza la pantalla de asistencia
            window.un_hide() # Muestra el menú de nuevo al volver

        if event == '-SERVIDOR-':
            if not servidor_iniciado:
                threading.Thread(target=iniciar_servidor_flask, daemon=True).start()
                window['-SERVIDOR-'].update(text="Servidor Corriendo (Abrir de nuevo)")
                sg.popup("Iniciando servidor... Se abrirá el navegador.", auto_close=True, auto_close_duration=2, non_blocking=True)
                time.sleep(1) # Darle tiempo al servidor
                webbrowser.open('http://127.0.0.1:5000')
            else:
                webbrowser.open('http://127.0.0.1:5000')

    window.close()

# ===================================================================
# Punto de entrada
# ===================================================================
if __name__ == '__main__':
    datos_rostros_conocidos = ([], []) # Variable global para los rostros
    iniciar_menu_principal()
