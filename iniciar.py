import subprocess
import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import sys

# Configuración de Nombres de Archivo 
SCRIPT_IA = "main_cuadro.py" # El script que activa la IA y el NFC
SCRIPT_WEB = "app.py"        # El script que activa el servidor web

# Inicializar la consola de Rich 
console = Console()

def mostrar_menu():
    """ Muestra el menú principal con un diseño atractivo. """
    console.clear() # Limpia la pantalla
    
    # Define el texto del menú con colores y estilos
    menu_text = Text(justify="left")
    menu_text.append("Selecciona un modo de operación:\n\n", style="bold white")
    menu_text.append("[1] MODO REGISTRO\n", style="green bold")
    menu_text.append("    (Activar Cámara y/o NFC para registrar asistencia)\n\n", style="green")
    menu_text.append("[2] MODO VER\n", style="blue bold")
    menu_text.append("    (Activar Panel Web del Docente)\n\n", style="blue")
    menu_text.append("[Q] Salir\n", style="red bold")
    
    # Dibuja el panel
    console.print(
        Panel(
            menu_text,
            title="🚀 Sistema de Asistencia 🚀",
            subtitle="Por Arturo Knezevich & Christian Menéndez",
            border_style="cyan",
            padding=(1, 2)
        )
    )

def ejecutar_modo_registro():
    """ Ejecuta el script de IA/NFC y espera a que termine. """
    console.print(f"\n[green]Iniciando [bold]{SCRIPT_IA}[/bold]...[/green]")
    console.print("La ventana de video se abrirá (si la cámara está conectada).")
    
    # Instrucciones de uso
    console.print("\n[yellow bold]PARA VOLVER AL MENÚ:[/yellow bold]")
    console.print("[yellow] 1. Si la cámara está activa: Presiona 'q' en la ventana de video.[/yellow]")
    console.print("[yellow] 2. Si solo usas NFC (sin cámara): Presiona 'Ctrl + C' en esta terminal.[/yellow]")
    
    try:
        # Usamos sys.executable para asegurarnos de que usa el python3 actual
        subprocess.run([sys.executable, SCRIPT_IA], check=True)
        console.print(f"\n[yellow]Modo Registro terminado. Volviendo al menú...[/yellow]")
    except subprocess.CalledProcessError:
        console.print(f"\n[red]Error al ejecutar {SCRIPT_IA}.[/red]")
    except KeyboardInterrupt:
        # Esto captura el 'Ctrl + C' del modo "Solo NFC"
        console.print(f"\n[yellow]Modo Registro (NFC) interrumpido. Volviendo al menú...[/yellow]")
    
    time.sleep(2) # Pausa para que el usuario lea el mensaje

def ejecutar_modo_ver():
    """ Ejecuta el servidor web y espera a que el usuario lo detenga. """
    console.print(f"\n[blue]Iniciando [bold]{SCRIPT_WEB}[/bold]...[/blue]")
    console.print(f"Accede al Dashboard en: http://[TU_IP]:5000")
    console.print("[yellow]Presiona [bold]Ctrl + C[/bold] en esta terminal para detener el servidor y volver al menú.[/yellow]")
    
    try:
        # Ejecuta el servidor y espera a que termine (con Ctrl+C)
        subprocess.run([sys.executable, SCRIPT_WEB], check=True)
    except subprocess.CalledProcessError:
        console.print(f"\n[red]Error al ejecutar {SCRIPT_WEB}.[/red]")
    except KeyboardInterrupt:
        pass # Captura el Ctrl+C silenciosamente
    
    console.print(f"\n[yellow]Servidor Web detenido. Volviendo al menú...[/yellow]")
    time.sleep(2) # Pausa para que el usuario lea el mensaje

# Bucle Principal del Lanzador
if __name__ == "__main__":
    while True:
        mostrar_menu()
        opcion = input("Tu opción: ").strip().upper()
        
        if opcion == '1':
            ejecutar_modo_registro()
        
        elif opcion == '2':
            ejecutar_modo_ver()
            
        elif opcion == 'Q':
            console.print("\n[white]Saliendo del sistema...[/white]")
            break
            
        else:
            console.print(f"\n[red]Opción '{opcion}' no válida. Intenta de nuevo.[/red]")
            time.sleep(1)