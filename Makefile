# Makefile para Sistema de Asistencia Jetson Nano
# Autor: Arturo Knezevich & Christian Menéndez

PYTHON = python3
PIP = pip3

.PHONY: help install system-deps python-deps run-gui run-web clean

# Muestra la ayuda por defecto
help:
	@echo "----------------------------------------------------------------"
	@echo "🤖 SISTEMA DE ASISTENCIA - COMANDOS DISPONIBLES"
	@echo "----------------------------------------------------------------"
	@echo "make install    -> Instala TODAS las dependencias (Sistema + Python)"
	@echo "make run-gui    -> Inicia la interfaz gráfica (Pantalla Jetson)"
	@echo "make run-web    -> Inicia solo el servidor web (Panel Admin)"
	@echo "make clean      -> Limpia archivos temporales y caché"
	@echo "----------------------------------------------------------------"

# Instalación completa
install: system-deps python-deps
	@echo "✅ Instalación completada exitosamente."

# Instalación de dependencias del sistema (Linux/Ubuntu/Jetson)
system-deps:
	@echo "🔧 Instalando librerías del sistema y drivers NFC..."
	sudo apt-get update
	sudo apt-get install -y cmake libopenblas-dev liblapack-dev libjpeg-dev
	sudo apt-get install -y pcscd libpcsclite1 libpcsclite-dev swig
	sudo systemctl enable pcscd
	sudo systemctl start pcscd

# Instalación de librerías de Python
python-deps:
	@echo "🐍 Instalando librerías de Python..."
	$(PIP) install -r requirements.txt

# Ejecutar la Interfaz Gráfica
run-gui:
	@echo "🚀 Iniciando Interfaz Gráfica..."
	$(PYTHON) qt_app.py

# Ejecutar el Servidor Web
run-web:
	@echo "🌐 Iniciando Servidor Web..."
	$(PYTHON) app.py

# Limpieza
clean:
	@echo "🧹 Limpiando archivos temporales..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f nohup.out