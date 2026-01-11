# 🏫 Sistema de Asistencia Inteligente (NFC + IA)

Este proyecto es una solución integral para el control de asistencia estudiantil automatizado. Utiliza una **NVIDIA Jetson Nano** para procesar reconocimiento facial en tiempo real y lectura de tarjetas NFC, validando la asistencia únicamente si el estudiante está inscrito en la materia que se imparte en el horario actual.

## 🚀 Características Principales

### 🖥️ Interfaz de Terminal (Punto de Acceso)
- **Doble Validación:** Permite ingreso mediante **Reconocimiento Facial** (IA) o Tarjeta **NFC**.
- **Validación de Horarios:** El sistema verifica automáticamente si hay una clase activa (Día/Hora) y si el alumno pertenece a ella antes de registrar la asistencia.
- **Feedback Visual:** Interfaz gráfica táctil (desarrollada en PyQt5) que muestra mensajes de éxito, errores o "Fuera de Horario".
- **Gestión de Hardware:** Control de cámara y reinicio del servicio NFC desde la pantalla.

### 🌐 Panel de Administración Web (Dashboard)
- **Gestión de Estudiantes:** Altas, bajas, fotos para la IA y asignación de tarjetas NFC.
- **Gestión de Materias:** Creación de clases con horarios de inicio/fin y días de la semana.
- **Reportes:** Visualización de historial con filtros por fecha y materia.
- **Exportación:** Descarga de reportes en CSV y envío automático por **Correo Electrónico**.
- **Seguridad:** Login para administradores y configuración de credenciales.

---

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3.8+
* **Visión Artificial:** OpenCV, Face Recognition (Dlib).
* **Interfaz Gráfica:** PyQt5.
* **Backend Web:** Flask (Jinja2, SQLite).
* **Hardware:** Pyscard (para lectores NFC PC/SC).
* **Base de Datos:** SQLite3.

---

## 🔌 Hardware Requerido

1.  **NVIDIA Jetson Nano** (Recomendado para usar aceleración GPU con CNN).
2.  **Cámara:** USB (Logitech C270 o similar) o Cámara IP (configurable por IP).
3.  **Lector NFC:** Modelo compatible con PC/SC (Ej: ACR122U).
4.  **Pantalla:** Monitor HDMI o Pantalla Táctil para la interfaz de usuario.
5.  **Conexión a Internet:** Para el envío de correos y servidor local.

---

## 📂 Estructura del Proyecto

```text
Proyecto_Asistencia/
│
├── app.py                  # Servidor Web (Flask) - Gestión y Dashboard
├── qt_app.py               # Interfaz Gráfica (PyQt5) - Pantalla principal en la Jetson
├── main_cuadro.py          # Lógica Central (IA, NFC, Validación de Horarios)
├── asistencia.db           # Base de datos SQLite (Se crea automáticamente)
├── config_sistema.json     # Configuración local (IP cámara, pass)
│
├── rostros_conocidos/      # Carpeta donde se guardan las fotos de los estudiantes
├── templates/              # Plantillas HTML para el panel web
└── static/                 # Estilos CSS y scripts JS (si aplica)
```

## ⚙️ Instalación y Configuración
1. Clonar el repositorio
```bash
git clone [https://github.com/TU_USUARIO/TU_REPO.git](https://github.com/Knezevich-En/https://github.com/Knezevich-En/asistencia-jetson.git)
cd Proyecto_Asistencia
```
2. Instalar dependencias del sistema (Ubuntu/Debian)
Para que funcione el lector NFC y la compilación de Dlib:
```bash
sudo apt-get update
sudo apt-get install python3-pip cmake libopenblas-dev liblapack-dev 
sudo apt-get install pcscd libpcsclite1 libpcsclite-dev swig
sudo systemctl enable pcscd
sudo systemctl start pcscd
```
3. Instalar librerías de Python
```bash
pip3 install flask opencv-python face_recognition pyscard PyQt5
```
(Nota: La instalación de `face_recognition` en Jetson Nano puede tardar unos minutos mientras compila dlib).
4. Configuración de Correo (Opcional)
Para usar la función de enviar reportes por correo, edita las variables en app.py:
```bash
EMAIL_SENDER = "tu_correo@gmail.com"
EMAIL_PASSWORD = "tu_contraseña_de_aplicacion"
```
## ▶️ Ejecución
El sistema consta de dos partes que pueden correr simultáneamente:
1. Iniciar la Interfaz de Asistencia (En la Jetson)
Esta es la pantalla que verán los alumnos.
```bash
python3 qt_app.py
```
Desde esta interfaz puedes iniciar el servidor web tocando el botón "Iniciar Servidor Web".
2. Iniciar solo el Servidor Web (Admin)
Si solo quieres gestionar datos desde otra PC:
```bash
python3 app.py
```
Luego, abre tu navegador e ingresa a: http://IP_DE_LA_JETSON:5000

## 📋 Uso del Sistema
1. **Registro de Materias:** Entra al panel web, ve a "Materias" y crea una clase (ej: "Robótica") definiendo sus días y hora (ej: Lunes de 14:00 a 16:00).
2. **Registro de Alumnos:** En el panel web, agrega un estudiante, sube su foto y selecciona las materias que cursa.
3. Tomar Asistencia:
* Ejecuta qt_app.py.
* El sistema detectará automáticamente si hay una clase activa según la hora actual.
* El alumno pasa su rostro o tarjeta.
* Si está inscrito y es la hora correcta -> **"Bienvenido"**.
* Si no es la hora o no está inscrito -> **"Acceso Denegado"**.

