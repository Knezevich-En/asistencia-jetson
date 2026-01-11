import sys
import time
from smartcard.System import readers
from smartcard.util import toHexString

print("--- Lector de UIDs ---")
print("Presiona Ctrl+C para salir.")

# Asegúrate de que el servicio pcscd esté corriendo
# (Puedes ejecutar 'sudo systemctl start pcscd' en otra terminal si esto falla)
try:
    lector_list = readers()
except Exception as e:
    print(f"\nError: No se pudo conectar al servicio 'pcscd'. ({e})")
    print("Asegúrate de que el servicio esté corriendo (sudo systemctl start pcscd)")
    sys.exit()

if not lector_list:
    print("\nError: No se encontró ningún lector NFC conectado.")
    sys.exit()

lector = lector_list[0]
print("Usando lector:", lector)
print("\n--- Esperando una tarjeta... ---")

last_uid = None

try:
    while True:
        try:
            connection = lector.createConnection()
            connection.connect()
            
            # Comando estándar para obtener el UID
            GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            data, sw1, sw2 = connection.transmit(GET_UID)
            connection.disconnect() 

            if (sw1, sw2) == (0x90, 0x00):
                uid = toHexString(data)
                # Solo imprime si es una tarjeta nueva
                if uid != last_uid:
                    print(f"\n¡Tarjeta detectada! UID: {uid}")
                    print("--- Esperando otra tarjeta... ---")
                    last_uid = uid
            
        except Exception:
            # Si no hay tarjeta, resetea el last_uid y espera
            last_uid = None
            time.sleep(0.2) # Pausa para no saturar el CPU

except KeyboardInterrupt:
    print("\nCerrando lector.")
