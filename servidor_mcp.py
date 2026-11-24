#!/usr/bin/env python3
"""Servidor MCP del asistente: da a CUALQUIER IA compatible con MCP control sobre este ordenador.

Herramientas: ejecutar comandos, leer/escribir archivos, apagar/reiniciar/suspender
y encender otros equipos con Wake-on-LAN.

Antes de cualquier cambio en carpetas del sistema (o con permisos de administrador)
aparece una ventana pidiéndote permiso. Con Claude Code, esa confirmación la hace
el propio Claude Code (ver hooks/aviso_sistema.py) y la ventana se omite.
"""

import json
import os
import subprocess
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from despertar import enviar_paquete_magico, resolver_equipo
from seguridad import SO, es_ruta_sistema, motivo_para_confirmar_comando, pedir_confirmacion

RAIZ = Path(__file__).parent
CONFIG = {"confirmar_apagado": True, "equipos": {}}
if (RAIZ / "config.json").exists():
    CONFIG.update(json.loads((RAIZ / "config.json").read_text(encoding="utf-8")))

# Claude Code ya pregunta con su propio diálogo (hook), así que no mostramos ventana doble.
CONFIRMA_EL_CLIENTE = os.environ.get("ASISTENTE_CONFIRMA_CLIENTE") == "1"
MAX_SALIDA = 20_000
SHELL = "PowerShell" if SO == "Windows" else "bash"

servidor = MCPServer(
    "asistente-pc",
    instructions=(
        f"Controlas el ordenador del usuario ({SO}, shell {SHELL}). Puedes hacer cualquier tarea. "
        "Los cambios en carpetas del sistema requieren el permiso del usuario, que se pide "
        "automáticamente; si lo rechaza, no lo intentes por otro camino. "
        "Solo apaga, reinicia o suspende el equipo cuando el usuario lo pida."
    ),
)


def _permitido(accion: str, motivo: str | None) -> bool:
    if not motivo or CONFIRMA_EL_CLIENTE:
        return True
    return pedir_confirmacion(accion, motivo)


def _recortar(texto: str) -> str:
    if len(texto) > MAX_SALIDA:
        return texto[:MAX_SALIDA] + f"\n[... recortado: {len(texto) - MAX_SALIDA} caracteres más]"
    return texto


@servidor.tool()
def ejecutar_comando(comando: str, carpeta: str | None = None, segundos_max: int = 120) -> str:
    """Ejecuta un comando de terminal (PowerShell en Windows, bash en macOS/Linux) y devuelve la salida.

    Args:
        comando: El comando a ejecutar.
        carpeta: Carpeta de trabajo (opcional).
        segundos_max: Tiempo máximo antes de detenerlo.
    """
    if not _permitido(comando, motivo_para_confirmar_comando(comando)):
        return "El usuario NO ha permitido este comando. No lo intentes de otra forma; pregúntale."
    orden = (["powershell", "-NoProfile", "-NonInteractive", "-Command", comando]
             if SO == "Windows" else ["/bin/bash", "-lc", comando])
    try:
        r = subprocess.run(orden, cwd=carpeta or None, capture_output=True, text=True,
                           timeout=segundos_max, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return f"El comando superó {segundos_max} s y se detuvo."
    salida = f"[código de salida {r.returncode}]\n{r.stdout}"
    if r.stderr:
        salida += f"\n[stderr]\n{r.stderr}"
    return _recortar(salida)


@servidor.tool()
def leer_archivo(ruta: str) -> str:
    """Lee un archivo de texto.

    Args:
        ruta: Ruta del archivo.
    """
    try:
        return _recortar(Path(os.path.expanduser(ruta)).read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        return f"Error al leer: {e}"


@servidor.tool()
def escribir_archivo(ruta: str, contenido: str, anadir: bool = False) -> str:
    """Crea o sobrescribe un archivo de texto, o añade al final si anadir es true.

    Args:
        ruta: Ruta del archivo.
        contenido: Texto a escribir.
        anadir: Si es true, añade al final en vez de sobrescribir.
    """
    motivo = "es una carpeta del sistema" if es_ruta_sistema(ruta) else None
    if not _permitido(f"{'añadir a' if anadir else 'escribir'} {ruta}", motivo):
        return "El usuario NO ha permitido escribir en esa ruta del sistema."
    try:
        p = Path(os.path.expanduser(ruta))
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a" if anadir else "w", encoding="utf-8") as f:
            f.write(contenido)
        return f"Guardado en {p}"
    except Exception as e:
        return f"Error al escribir: {e}"


def _orden_energia(accion: str, minutos: int) -> list[str] | str:
    segundos = max(0, minutos) * 60
    if SO == "Windows":
        return {
            "apagar": ["shutdown", "/s", "/t", str(segundos)],
            "reiniciar": ["shutdown", "/r", "/t", str(segundos)],
            "suspender": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            "cancelar": ["shutdown", "/a"],
        }[accion]
    if SO == "Darwin":
        if accion == "cancelar":
            return "pkill -f asistente-energia; echo cancelado"
        apple = {"apagar": "shut down", "reiniciar": "restart", "suspender": "sleep"}[accion]
        orden = f"osascript -e 'tell application \"System Events\" to {apple}'"
        if segundos:
            return f"nohup sh -c 'sleep {segundos}; {orden}' asistente-energia >/dev/null 2>&1 &"
        return orden
    return {  # Linux con systemd
        "apagar": ["shutdown", "-h", f"+{minutos}"] if minutos else ["systemctl", "poweroff"],
        "reiniciar": ["shutdown", "-r", f"+{minutos}"] if minutos else ["systemctl", "reboot"],
        "suspender": ["systemctl", "suspend"],
        "cancelar": ["shutdown", "-c"],
    }[accion]


@servidor.tool()
def energia(accion: str, minutos: int = 0) -> str:
    """Apaga, reinicia o suspende ESTE ordenador, o cancela un apagado programado.
    Úsala solo cuando el usuario lo pida expresamente.

    Args:
        accion: "apagar", "reiniciar", "suspender" o "cancelar".
        minutos: Retraso en minutos (0 = ahora).
    """
    if accion not in ("apagar", "reiniciar", "suspender", "cancelar"):
        return "Acción no válida. Usa apagar, reiniciar, suspender o cancelar."
    if accion != "cancelar" and CONFIG.get("confirmar_apagado", True) and not CONFIRMA_EL_CLIENTE:
        cuando = f"dentro de {minutos} min" if minutos else "ahora"
        if not pedir_confirmacion(f"{accion} el ordenador {cuando}", "se cerrarán los programas abiertos"):
            return "El usuario ha cancelado la acción."
    orden = _orden_energia(accion, minutos)
    try:
        r = subprocess.run(orden, shell=isinstance(orden, str), capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return f"No se pudo ({r.returncode}): {r.stderr or r.stdout}"
        return f"Hecho: {accion}" + (f" en {minutos} min" if minutos and accion != "cancelar" else "")
    except Exception as e:
        return f"Error: {e}"


@servidor.tool()
def encender_equipo(equipo: str) -> str:
    """Enciende otro ordenador de la red local con Wake-on-LAN.

    Args:
        equipo: Nombre definido en config.json (sección "equipos") o una dirección MAC.
    """
    try:
        mac, broadcast = resolver_equipo(equipo)
        enviar_paquete_magico(mac, broadcast)
        return f"Señal de encendido enviada a {equipo} ({mac})."
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    servidor.run()
