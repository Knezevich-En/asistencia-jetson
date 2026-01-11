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

## 🧠 Arquitectura del Código

El sistema está modularizado en tres componentes principales para desacoplar la lógica de detección de la interfaz de usuario:

### 1. `main_cuadro.py` (El Núcleo Lógico)
Es el backend local que corre en la Jetson.
* **Gestión de Modelos:** Carga los *embeddings* faciales en memoria al iniciar para una comparación rápida (O(1)).
* **Lógica de Horarios (`actualizar_bloque_horario`):** Se ejecuta periódicamente para verificar si la hora actual `datetime.now()` coincide con el rango `inicio-fin` de alguna materia registrada en la base de datos.
* **Prevención de Duplicados:** Implementa un `debounce` de 3 segundos y verifica en SQL si el alumno ya tiene asistencia ese día para evitar registros múltiples.

### 2. `qt_app.py` (Interfaz Gráfica - Frontend)
Desarrollada en **PyQt5**, diseñada para pantallas táctiles.
* **Multithreading (`QThread`):**
    * *Hilo 1 (Cámara):* Captura frames, los envía a procesar y actualiza el widget de video.
    * *Hilo 2 (NFC):* Escucha eventos del lector de tarjetas en segundo plano sin congelar la interfaz.
* **Sistema de Señales:** Usa `pyqtSignal` para comunicar los eventos de detección (éxito, error, no inscrito) desde los hilos hacia la interfaz visual principal.

### 3. `app.py` (Servidor Web & API)
Servidor **Flask** que actúa como panel administrativo.
* **Rutas Dinámicas:** Gestiona el CRUD de estudiantes y materias.
* **Reportes:** Genera archivos CSV en memoria (sin escribir en disco) usando `io.StringIO` para exportaciones rápidas y envío de correos vía SMTP.
* **Seguridad:** Protege rutas sensibles con decoradores `@login_required` y hash de contraseñas.

## 🔄 Lógica de Toma de Asistencia

El sistema no acepta cualquier rostro conocido. Para validar una asistencia, el algoritmo sigue un flujo estricto de 4 niveles:

1.  **Nivel 1: Identificación Biométrica/Física**
    * ¿El rostro coincide con los *encodings* pre-entrenados? O ¿El UID de la tarjeta NFC existe en la base de datos?
    * *Si NO:* Se marca como "Desconocido".
    * *Si SÍ:* Pasamos al Nivel 2.

2.  **Nivel 2: Validación Temporal (Cronograma)**
    * El sistema consulta: *¿Existe alguna materia activa en este preciso minuto y día de la semana?*
    * *Si NO:* Retorna error **"FUERA DE HORARIO"** (No se puede registrar asistencia en recreos o horas libres).

3.  **Nivel 3: Validación Académica (Inscripción)**
    * El sistema cruza datos: *¿El estudiante identificado (ID X) está inscrito en la materia activa (Materia Y)?*
    * *Si NO:* Retorna alerta **"NO INSCRITO"** (Un alumno de otra clase no puede registrar asistencia aquí).

4.  **Nivel 4: Persistencia**
    * Si pasa los 3 filtros, se guarda el registro en SQLite con `timestamp`, `metodo (NFC/Vision)` y se muestra el mensaje de **"Bienvenido"** en pantalla.

## 📚 Stack Tecnológico Detallado
| Tecnología | Uso en el proyecto | Por qué se eligió |
| :--- | :--- | :--- |
| **Python 3.8** | Lenguaje Principal | Versatilidad para integrar Hardware y Web. |
| **OpenCV** | Visión Artificial | Manipulación de frames y pre-procesamiento de imágenes. |
| **Face Recognition** | IA (Dlib based) | Modelo HOG/CNN robusto capaz de generar *embeddings* de 128 dimensiones. |
| **PyQt5** | GUI (Escritorio) | Permite crear interfaces táctiles fluidas con manejo avanzado de hilos. |
| **Flask** | Backend Web | Ligero y modular para servir el dashboard en la red local. |
| **SQLite** | Base de Datos | SQL *serverless*, ideal para sistemas embebidos donde no queremos correr un servidor MySQL pesado. |
| **Pyscard** | NFC | Implementación estándar PC/SC para comunicación directa con lectores inteligentes. |

# Instalación usando Archivo Makefile
* Asegúrate de tener los archivos en la Jetson
```bash
cd Proyecto_Asistencia
git pull
```

2. Verifica si tienes "Make" instalado
En la terminal de la Jetson, escribe:
```bash
make --version
```
* Si sale un texto con la versión (ej. `GNU Make 4.2`), ya lo tienes.
* Si dice `command not found`, instálalo escribiendo:
```bash
sudo apt-get install make
```
## Finalemente ejecuta los siguiente comandos
1. Para instalar TODO desde cero:
```bash
make install
```
(Esto pedirá la contraseña de sudo una vez y se encargará de instalar `cmake`, los drivers de la tarjeta NFC, activar el servicio y descargar las librerías de Python).

### ¿Qué pasará automáticamente?
* La terminal leerá tu archivo Makefile.
* Verá que install depende de system-deps.
* Te pedirá tu contraseña de usuario (porque usa sudo).
* Empezará a descargar e instalar los drivers del lector NFC (pcscd, etc).
* Cuando termine eso, saltará a la parte de python-deps y leerá tu requirements.txt para instalar Flask, OpenCV, etc.

2. Para abrir la aplicación:
```bash
make run-gui
```
Esto buscará la instrucción run-gui en el archivo y ejecutará `python3 qt_app.py`.



