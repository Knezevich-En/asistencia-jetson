import sys
import subprocess
import socket
import time
import os
import signal

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect, QFrame, 
    QSpacerItem, QSizePolicy, QLineEdit, QDialog, QMessageBox, QScrollArea,
    QStyle
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QTimer, QSize
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor, QIcon

import cv2
import main_cuadro as mc

proceso_servidor = None

# ==========================================
# FUNCIONES DE UTILIDAD
# ==========================================
def obtener_ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

def cerrar_servidor_global():
    global proceso_servidor
    if proceso_servidor is not None:
        try: os.killpg(os.getpgid(proceso_servidor.pid), signal.SIGTERM)
        except: proceso_servidor.terminate()
        proceso_servidor = None

# ==========================================
# ESTILOS VISUALES
# ==========================================
ESTILO_BOTON_BASE = """
    QPushButton {
        color: white; border-radius: 15px; font-size: 22px; font-weight: bold;
        min-height: 60px; min-width: 150px; border: none;
        padding-left: 15px; padding-right: 15px; text-align: left;
    }
"""
ESTILO_INPUT = """
    QLineEdit {
        background-color: #f2f2f7; border: 2px solid #c7c7cc; border-radius: 12px;
        padding: 10px; font-size: 18px; color: #333; min-height: 40px;
    }
    QLineEdit:focus { border: 2px solid #007aff; background-color: #ffffff; }
"""
ESTILO_FRAME = """
    QFrame { background-color: white; border-radius: 25px; border: 2px solid #d1d1d6; }
"""

# ==========================================
# DIÁLOGOS DE CONFIGURACIÓN
# ==========================================
class DialogoLogin(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Autenticación")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 400)
        layout = QVBoxLayout(); layout.setContentsMargins(0, 0, 0, 0); self.setLayout(layout)
        self.frame = QFrame(); self.frame.setStyleSheet(ESTILO_FRAME)
        sombra = QGraphicsDropShadowEffect(); sombra.setBlurRadius(50); sombra.setColor(QColor(0, 0, 0, 100)); self.frame.setGraphicsEffect(sombra)
        inner = QVBoxLayout(); inner.setContentsMargins(40, 40, 40, 40); inner.setSpacing(20)
        lbl = QLabel("Acceso Restringido"); lbl.setFont(QFont("Arial", 22, QFont.Bold)); lbl.setAlignment(Qt.AlignCenter); lbl.setStyleSheet("border: none; color: #333;")
        lbl_info = QLabel("Ingrese la contraseña de administrador:"); lbl_info.setFont(QFont("Arial", 14)); lbl_info.setAlignment(Qt.AlignCenter); lbl_info.setStyleSheet("border: none; color: #666;")
        self.input_pass = QLineEdit(); self.input_pass.setEchoMode(QLineEdit.Password); self.input_pass.setAlignment(Qt.AlignCenter); self.input_pass.setStyleSheet(ESTILO_INPUT)
        inner.addWidget(lbl); inner.addWidget(lbl_info); inner.addWidget(self.input_pass); inner.addStretch()
        botones_layout = QHBoxLayout(); botones_layout.setSpacing(20)
        btn_cancel = QPushButton("Cancelar"); btn_cancel.setCursor(Qt.PointingHandCursor); btn_cancel.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #ff3b30; } QPushButton:hover { background-color: #d63024; }"); btn_cancel.clicked.connect(self.reject)
        btn_entrar = QPushButton("Entrar"); btn_entrar.setCursor(Qt.PointingHandCursor); btn_entrar.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #007aff; } QPushButton:hover { background-color: #005bb5; }"); btn_entrar.clicked.connect(self.verificar)
        botones_layout.addWidget(btn_cancel); botones_layout.addWidget(btn_entrar); inner.addLayout(botones_layout); self.frame.setLayout(inner); layout.addWidget(self.frame)
    def verificar(self):
        if mc.verificar_password(self.input_pass.text()): self.accept()
        else: self.input_pass.setStyleSheet(ESTILO_INPUT.replace("#c7c7cc", "#ff3b30")); self.input_pass.clear(); self.input_pass.setPlaceholderText("Contraseña Incorrecta")

class DialogoConfig(QDialog):
    def __init__(self, ip_actual, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog); self.setAttribute(Qt.WA_TranslucentBackground); self.setFixedSize(700, 550)
        layout_principal = QVBoxLayout(); layout_principal.setContentsMargins(0, 0, 0, 0); self.setLayout(layout_principal)
        self.frame = QFrame(); self.frame.setStyleSheet(ESTILO_FRAME)
        sombra = QGraphicsDropShadowEffect(); sombra.setBlurRadius(50); sombra.setColor(QColor(0, 0, 0, 100)); self.frame.setGraphicsEffect(sombra)
        layout_interno = QVBoxLayout(); layout_interno.setContentsMargins(40, 40, 40, 40); layout_interno.setSpacing(15)
        lbl_titulo = QLabel("Configuración Avanzada"); lbl_titulo.setFont(QFont("Arial", 24, QFont.Bold)); lbl_titulo.setAlignment(Qt.AlignCenter); lbl_titulo.setStyleSheet("border:none; color: #333;"); layout_interno.addWidget(lbl_titulo); layout_interno.addSpacing(10)
        lbl_cam = QLabel("Fuente de Cámara (URL o 0 para USB):"); lbl_cam.setFont(QFont("Arial", 14, QFont.Bold)); lbl_cam.setStyleSheet("border:none; color: #555;"); layout_interno.addWidget(lbl_cam)
        self.input_ip = QLineEdit(); self.input_ip.setText(str(ip_actual)); self.input_ip.setStyleSheet(ESTILO_INPUT); layout_interno.addWidget(self.input_ip); layout_interno.addSpacing(15)
        lbl_sec = QLabel("Cambiar Contraseña (Opcional):"); lbl_sec.setFont(QFont("Arial", 14, QFont.Bold)); lbl_sec.setStyleSheet("border:none; color: #555;"); layout_interno.addWidget(lbl_sec)
        self.input_pass_new = QLineEdit(); self.input_pass_new.setPlaceholderText("Nueva contraseña..."); self.input_pass_new.setStyleSheet(ESTILO_INPUT); layout_interno.addWidget(self.input_pass_new); layout_interno.addStretch()
        layout_botones = QHBoxLayout(); layout_botones.setSpacing(20)
        btn_cancelar = QPushButton("Cancelar"); btn_cancelar.setCursor(Qt.PointingHandCursor); btn_cancelar.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #ff3b30; } QPushButton:hover { background-color: #d63024; }"); btn_cancelar.clicked.connect(self.reject)
        btn_guardar = QPushButton("Guardar Cambios"); btn_guardar.setCursor(Qt.PointingHandCursor); btn_guardar.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #34c759; } QPushButton:hover { background-color: #248a3d; }"); btn_guardar.clicked.connect(self.accept)
        layout_botones.addWidget(btn_cancelar); layout_botones.addWidget(btn_guardar); layout_interno.addLayout(layout_botones); self.frame.setLayout(layout_interno); layout_principal.addWidget(self.frame)
    def obtener_datos(self): return self.input_ip.text(), self.input_pass_new.text()

# ====================================
# HILOS DE HARDWARE
# ====================================

class HiloCamara(QThread):
    frame_signal = pyqtSignal(object)
    nombre_signal = pyqtSignal(str) 
    status_signal = pyqtSignal(bool)
    detener = False

    def run(self):
        cap = cv2.VideoCapture(mc.CAP_ID)
        if cap.isOpened(): self.status_signal.emit(True)
        else: self.status_signal.emit(False); return

        frame_counter = 0
        while not self.detener:
            ret, frame = cap.read()
            if not ret: continue
            frame_counter += 1
            if frame_counter % 3 == 0:
                # El main_cuadro procesa y devuelve el código de estado
                mc.procesar_cara(frame, lambda msg: self.nombre_signal.emit(msg))
            self.frame_signal.emit(frame)
        cap.release()

class HiloNFC(QThread):
    nombre_signal = pyqtSignal(str)
    status_signal = pyqtSignal(bool)
    detener = False

    def run(self):
        lector = mc.iniciar_nfc()
        if lector: self.status_signal.emit(True)
        else: self.status_signal.emit(False); return

        while not self.detener:
            try:
                if lector:
                    uid = mc.leer_nfc(lector)
                    if uid:
                        sid, nombre = mc.buscar_por_uid(uid)
                        if sid:
                            res = mc.registrar_asistencia(sid, "NFC")
                            # Emitimos la respuesta tal cual nos la da mc
                            if res == "EXITO":
                                self.nombre_signal.emit(f"NFC_OK:{nombre}")
                            elif res == "DUPLICADO":
                                self.nombre_signal.emit(f"NFC_DUP:{nombre}")
                            elif res == "NO_INSCRITO":
                                self.nombre_signal.emit(f"NFC_NO_INSCRITO:{nombre}")
                            elif res == "FUERA_HORARIO":
                                self.nombre_signal.emit("NFC_FUERA:Sin Clase")
                time.sleep(0.15)
            except: pass

# ====================================
# VENTANA REGISTRO
# ====================================
class VentanaRegistro(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Registro de Asistencia")
        self.showFullScreen()
        self.setStyleSheet("QWidget { background-color: #f2f2f7; }")
        
        self.camara_activa = False
        self.nfc_activo = False
        
        self.timer_ocultar = QTimer(self)
        self.timer_ocultar.setSingleShot(True)
        self.timer_ocultar.timeout.connect(self.iniciar_salida_notificacion)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0) 

        # Título principal
        self.lbl_msg = QLabel("Iniciando Hardware...")
        self.lbl_msg.setFont(QFont("Arial", 28, QFont.Bold))
        self.lbl_msg.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_msg)

        # Subtítulo para mostrar qué materia se detectó
        self.lbl_materia = QLabel("Calculando horario...")
        self.lbl_materia.setFont(QFont("Arial", 16, QFont.Bold))
        self.lbl_materia.setAlignment(Qt.AlignCenter)
        self.lbl_materia.setStyleSheet("color: #666; padding-bottom: 5px;")
        layout.addWidget(self.lbl_materia)

        # Video
        self.lbl_video = QLabel()
        self.lbl_video.setAlignment(Qt.AlignCenter)
        self.lbl_video.setStyleSheet("background-color: #e5e5ea; border-radius: 20px;")
        self.lbl_video.setFixedSize(640, 480) 
        layout.addWidget(self.lbl_video, alignment=Qt.AlignCenter)

        # Botón Volver
        btn = QPushButton(" Volver al Menú Principal")
        btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowLeft))
        btn.setIconSize(QSize(32, 32))
        btn.setFixedWidth(450)
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,0.65); border-radius: 25px; padding: 12px;
                font-size: 24px; color: #007aff; border: 2px solid rgba(255,255,255,0.4); 
            }
        """)
        btn.clicked.connect(self.volver)
        layout.addSpacing(20); layout.addWidget(btn, alignment=Qt.AlignCenter); layout.addSpacing(20)

        self.setLayout(layout)
        self.configurar_notificacion()

        # Iniciar hilos
        self.hilo_camara = HiloCamara()
        self.hilo_camara.frame_signal.connect(self.mostrar_frame)
        self.hilo_camara.nombre_signal.connect(self.procesar_mensaje) # Conectamos los mensajes
        self.hilo_camara.status_signal.connect(self.set_estado_camara)
        self.hilo_camara.start()

        self.hilo_nfc = HiloNFC()
        self.hilo_nfc.nombre_signal.connect(self.procesar_mensaje) # Conectamos los mensajes
        self.hilo_nfc.status_signal.connect(self.set_estado_nfc)
        self.hilo_nfc.start()

        # Verificamos la materia al abrir
        self.actualizar_info_materia()

    def actualizar_info_materia(self):
        # Muestra en pantalla qué clase está activa según main_cuadro
        info = mc.MATERIA_ACTUAL_INFO
        if info:
            nombre = info["nombre"]
            self.lbl_materia.setText(f"CLASE ACTIVA: {nombre}")
            self.lbl_materia.setStyleSheet("color: #007aff; font-weight: bold; font-size: 20px;")
        else:
            self.lbl_materia.setText("Modo Espera: No hay clase programada ahora")
            self.lbl_materia.setStyleSheet("color: #ef4444; font-weight: normal; font-size: 18px;")

    def configurar_notificacion(self):
        self.notif = QLabel("", self)
        self.notif.setAlignment(Qt.AlignCenter)
        self.estilo_base_notif = """
            QLabel {
                background-color: rgba(255,255,255,0.95);
                padding: 15px 30px; border-radius: 20px;
                font-size: 26px; font-weight: bold; border: 1px solid rgba(0,0,0,0.1);
            }
        """
        self.notif.setStyleSheet(self.estilo_base_notif)
        self.notif.resize(800, 80) 
        self.notif.move((1024 - 800) // 2, 50) 
        self.notif.setVisible(False)
        self.anim_salida = QPropertyAnimation(self.notif, b"windowOpacity")
        self.anim_salida.setDuration(400)
        self.anim_salida.setStartValue(1); self.anim_salida.setEndValue(0)
        self.anim_salida.finished.connect(lambda: self.notif.setVisible(False))

    def set_estado_camara(self, activo):
        self.camara_activa = activo; self.actualizar_titulo()
        if not activo: self.lbl_video.setText("Cámara no detectada")

    def set_estado_nfc(self, activo):
        self.nfc_activo = activo; self.actualizar_titulo()

    def actualizar_titulo(self):
        if self.camara_activa and self.nfc_activo: texto = "Sistema de Visión y NFC"
        elif self.camara_activa: texto = "Sistema de Visión"
        elif self.nfc_activo: texto = "Sistema NFC"
        else: texto = "Esperando Hardware..."
        self.lbl_msg.setText(texto)

    def mostrar_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, w * ch, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        pixmap = pixmap.scaled(self.lbl_video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_video.setPixmap(pixmap)

    # -----------------------------------------------------------------
    # AQUÍ ESTÁ LA LÓGICA QUE PIDES PARA LOS MENSAJES
    # -----------------------------------------------------------------
    def procesar_mensaje(self, codigo_msg):
        # El formato que recibimos es "TIPO:NOMBRE" o "TIPO:MENSAJE"
        if ":" not in codigo_msg: return
        tipo, nombre = codigo_msg.split(":", 1)

        mensaje = ""
        color = "#333"

        if "OK" in tipo:
            # Caso: Registrado en la materia y en hora correcta
            mensaje = f"✅ ¡Bienvenido {nombre}!"
            color = "#059669" # Verde

        elif "DUP" in tipo:
            # Caso: Ya registró asistencia hoy
            mensaje = f"⚠️ {nombre}, ya te registraste."
            color = "#d97706" # Naranja

        elif "NO_INSCRITO" in tipo:
            # Caso: Alumno reconocido, pero NO está en esta materia
            mensaje = f"⛔ {nombre} NO REGISTRADO en esta materia."
            color = "#dc2626" # Rojo

        elif "FUERA" in tipo:
            # Caso: Alumno intenta registrarse pero no es hora de clase
            mensaje = "🕒 No hay clase en este horario."
            color = "#dc2626"
        else:
            return

        self.mostrar_burbuja(mensaje, color)

    def mostrar_burbuja(self, texto, color_hex):
        self.timer_ocultar.stop()
        self.anim_salida.stop()
        self.notif.setText(texto)
        self.notif.setStyleSheet(self.estilo_base_notif + f"color: {color_hex}; border-left: 10px solid {color_hex};")
        self.notif.setVisible(True)
        self.notif.setWindowOpacity(1)
        self.timer_ocultar.start(4000)

    def iniciar_salida_notificacion(self):
        self.anim_salida.start()

    def volver(self):
        self.hilo_camara.detener = True
        self.hilo_nfc.detener = True
        time.sleep(0.3)
        self.close()
        main_window.showFullScreen()

# ====================================
# MENÚ PRINCIPAL
# ====================================
class MenuPrincipal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Asistencia")
        self.showFullScreen()
        self.setStyleSheet("""
            QWidget { background-color: #ffffff; }
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { width: 30px; }
        """)
        main_layout = QVBoxLayout(); main_layout.setAlignment(Qt.AlignCenter); main_layout.setContentsMargins(40, 40, 40, 20)
        titulo = QLabel("Sistema de Asistencia Escolar"); titulo.setFont(QFont("Arial", 36, QFont.Bold)); titulo.setAlignment(Qt.AlignCenter); titulo.setStyleSheet("color: #333; margin-bottom: 20px; background-color: transparent;"); main_layout.addWidget(titulo)
        
        scroll_area = QScrollArea(); scroll_area.setWidgetResizable(True); scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_content = QWidget(); scroll_content.setStyleSheet("background-color: transparent;"); scroll_layout = QVBoxLayout(scroll_content); scroll_layout.setAlignment(Qt.AlignCenter); scroll_layout.setSpacing(15)

        btn1 = QPushButton("  Iniciar Registro"); btn1.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay)); btn1.setIconSize(QSize(40, 40)); btn1.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #007aff; } QPushButton:hover { background-color: #0060d1; }"); btn1.clicked.connect(self.iniciar_registro); scroll_layout.addWidget(btn1)
        self.btn_sync = QPushButton("  Sincronizar Datos"); self.btn_sync.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload)); self.btn_sync.setIconSize(QSize(40, 40)); self.btn_sync.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #06b6d4; }"); self.btn_sync.clicked.connect(self.sincronizar_datos); scroll_layout.addWidget(self.btn_sync)
        self.btn_cam_config = QPushButton("  Configurar Sistema"); self.btn_cam_config.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView)); self.btn_cam_config.setIconSize(QSize(40, 40)); self.btn_cam_config.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #8b5cf6; } QPushButton:hover { background-color: #7c3aed; }"); self.btn_cam_config.clicked.connect(self.configurar_sistema); scroll_layout.addWidget(self.btn_cam_config)
        self.btn_servidor = QPushButton("  Iniciar Servidor Web"); self.btn_servidor.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon)); self.btn_servidor.setIconSize(QSize(40, 40)); self.btn_servidor.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #007aff; } QPushButton:hover { background-color: #0060d1; }"); self.btn_servidor.clicked.connect(self.toggle_servidor); scroll_layout.addWidget(self.btn_servidor)
        self.btn_nfc = QPushButton("  Reiniciar Lector NFC"); self.btn_nfc.setIcon(self.style().standardIcon(QStyle.SP_MediaSeekForward)); self.btn_nfc.setIconSize(QSize(40, 40)); self.btn_nfc.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #f59e0b; }"); self.btn_nfc.clicked.connect(self.reiniciar_nfc); scroll_layout.addWidget(self.btn_nfc)

        self.panel_server = QFrame(); self.panel_server.setVisible(False); self.panel_server.setStyleSheet("QFrame { background-color: #f0f9ff; border: 3px solid #bae6fd; border-radius: 20px; margin: 10px; min-width: 450px; }")
        layout_panel = QVBoxLayout()
        self.lbl_status = QLabel("SERVIDOR EN LÍNEA"); self.lbl_status.setAlignment(Qt.AlignCenter); self.lbl_status.setFont(QFont("Arial", 16, QFont.Bold)); self.lbl_status.setStyleSheet("color: #0369a1; border: none; background: transparent;"); layout_panel.addWidget(self.lbl_status)
        self.lbl_ip = QLabel(""); self.lbl_ip.setAlignment(Qt.AlignCenter); self.lbl_ip.setFont(QFont("Courier New", 32, QFont.Bold)); self.lbl_ip.setStyleSheet("color: #0284c7; border: none; background: transparent;"); layout_panel.addWidget(self.lbl_ip)
        self.lbl_info = QLabel("Conecta tus dispositivos a la red"); self.lbl_info.setAlignment(Qt.AlignCenter); self.lbl_info.setFont(QFont("Arial", 14)); self.lbl_info.setStyleSheet("color: #64748b; border: none; background: transparent;"); layout_panel.addWidget(self.lbl_info)
        self.panel_server.setLayout(layout_panel); scroll_layout.addWidget(self.panel_server)

        scroll_area.setWidget(scroll_content); main_layout.addWidget(scroll_area)
        btn_salir = QPushButton("  Salir del Sistema"); btn_salir.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton)); btn_salir.setIconSize(QSize(40, 40)); btn_salir.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #ff3b30; } QPushButton:hover { background-color: #d63024; }"); btn_salir.clicked.connect(self.close); main_layout.addWidget(btn_salir)
        self.setLayout(main_layout)

    def iniciar_registro(self): self.reg = VentanaRegistro(); self.reg.show(); self.hide()
    
    def sincronizar_datos(self): 
        # Actualizamos la IA y forzamos el recálculo del horario
        self.btn_sync.setEnabled(False)
        self.btn_sync.setText("  Calculando Horario...")
        QApplication.processEvents()
        
        # 1. Recargar BD e IA
        mc.cargar_datos_ia()
        # 2. Forzar calculo de hora actual
        mc.actualizar_bloque_horario()

        self.btn_sync.setText("  ¡Horario Actualizado!")
        QTimer.singleShot(2000, lambda: self.btn_sync.setText("  Sincronizar Datos"))
        self.btn_sync.setEnabled(True)

    def configurar_sistema(self):
        login = DialogoLogin(self)
        if login.exec_() == QDialog.Accepted:
            config = DialogoConfig(mc.CAP_ID, self)
            if config.exec_() == QDialog.Accepted:
                nueva_ip, nueva_pass = config.obtener_datos()
                if nueva_ip: mc.actualizar_parametros(nueva_ip, nueva_pass); self.btn_cam_config.setText("  Cambios Guardados"); QTimer.singleShot(2000, lambda: self.btn_cam_config.setText("  Configurar Sistema"))
    def toggle_servidor(self):
        global proceso_servidor
        if proceso_servidor is None: proceso_servidor = subprocess.Popen(["python3", "app.py"], preexec_fn=os.setsid); ip = obtener_ip_local(); self.btn_servidor.setIcon(self.style().standardIcon(QStyle.SP_DriveNetIcon)); self.lbl_status.setText("SERVIDOR ACTIVO"); self.lbl_ip.setText(f"http://{ip}:5000"); self.panel_server.setVisible(True); self.btn_servidor.setText("  Detener Servidor"); self.btn_servidor.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #ef4444; }")
        else: cerrar_servidor_global(); self.panel_server.setVisible(False); self.btn_servidor.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon)); self.btn_servidor.setText("  Iniciar Servidor Web"); self.btn_servidor.setStyleSheet(ESTILO_BOTON_BASE + "QPushButton { background-color: #007aff; }")
    def reiniciar_nfc(self):
        self.btn_nfc.setText("  Verificando..."); self.btn_nfc.setEnabled(False); QApplication.processEvents(); exito = False
        try: subprocess.run(["sudo", "systemctl", "restart", "pcscd"], check=True, timeout=2); exito = True
        except: pass
        if not exito: 
            try: 
                if mc.iniciar_nfc(): exito = True
            except: pass
        if exito: self.lbl_info.setText("Lector NFC Activo")
        else: self.lbl_info.setText("Intente registrar asistencia")
        QTimer.singleShot(3000, self.restaurar_estado_tras_nfc)
    def restaurar_estado_tras_nfc(self): self.btn_nfc.setText("  Reiniciar Lector NFC"); self.btn_nfc.setEnabled(True)
    def closeEvent(self, event): cerrar_servidor_global(); event.accept()

print("Cargando IA, espere…")
mc.cargar_datos_ia()
print("IA cargada correctamente.")
app = QApplication(sys.argv)
main_window = MenuPrincipal()
main_window.show()
sys.exit(app.exec_())
