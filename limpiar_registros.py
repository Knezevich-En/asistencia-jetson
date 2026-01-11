import sqlite3

DB_FILE = "asistencia.db"

try:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Ejecuta el comando SQL para borrar todo de la tabla Registros
    cursor.execute("DELETE FROM Registros")

    # Resetea el contador de autoincremento (opcional pero limpio)
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='Registros'")

    conn.commit()
    conn.close()

    print(f"¡Éxito! Todos los registros de asistencia han sido borrados de '{DB_FILE}'.")
    print("Los perfiles de estudiantes siguen intactos.")

except Exception as e:
    print(f"Error al limpiar la base de datos: {e}")
