import sqlite3

DB_FILE = "asistencia.db"

# -----------------------------------------------------------------
# ¡TUS DATOS CORREGIDOS!
# -----------------------------------------------------------------
NOMBRE_ESTUDIANTE = "Arturo Knezevich"
UID_NFC = "94A1E42E"          # UID SIN ESPACIOS
ARCHIVO_FOTO = "arturo.jpg"   # Nombre de archivo simple
# -----------------------------------------------------------------


def registrar_estudiante():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        print("Conectado a la base de datos...")

        # ... (código que revisa si existe y lo inserta)
        cursor.execute(
            "SELECT * FROM Estudiantes WHERE nombre = ? OR uid_nfc = ?", 
            (NOMBRE_ESTUDIANTE, UID_NFC)
        )

        if cursor.fetchone():
            print(f"Advertencia: '{NOMBRE_ESTUDIANTE}' o su UID '{UID_NFC}' ya existe. Omitiendo.")
        else:
            cursor.execute(
                "INSERT INTO Estudiantes (nombre, uid_nfc, archivo_foto) VALUES (?, ?, ?)",
                (NOMBRE_ESTUDIANTE, UID_NFC, ARCHIVO_FOTO)
            )
            print(f"¡Éxito! Estudiante '{NOMBRE_ESTUDIANTE}' registrado.")

        conn.commit()
        conn.close()
        print("Registro completado. Conexión cerrada.")

    except Exception as e:
        print(f"Error al registrar: {e}")

if __name__ == "__main__":
    registrar_estudiante()
