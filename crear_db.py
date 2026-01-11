import sqlite3
import os

DB_FILE = "asistencia.db"

if os.path.exists(DB_FILE):
    print(f"La base de datos '{DB_FILE}' ya existe.")
else:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE Estudiantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            uid_nfc TEXT,
            archivo_foto TEXT
        )
        ''')
        print("Tabla 'Estudiantes' creada con éxito.")

        cursor.execute('''
        CREATE TABLE Registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metodo TEXT NOT NULL,
            FOREIGN KEY (estudiante_id) REFERENCES Estudiantes (id)
        )
        ''')
        print("Tabla 'Registros' creada con éxito.")

        conn.commit()
        conn.close()

        print(f"\n¡Base de datos '{DB_FILE}' creada exitosamente!")

    except Exception as e:
        print(f"Error al crear la base de datos: {e}")
