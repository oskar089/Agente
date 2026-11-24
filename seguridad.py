"""Detecta si una acción toca carpetas del sistema y pide confirmación al usuario."""

import os
import platform
import re
import shlex
import shutil
import subprocess

SO = platform.system()  # "Windows", "Darwin" (macOS) o "Linux"


def _carpetas_sistema() -> list[str]:
    if SO == "Windows":
        raiz = os.environ.get("SystemRoot", r"C:\Windows")
        disco = os.environ.get("SystemDrive", "C:")
        carpetas = [
            raiz,
            os.environ.get("ProgramFiles", rf"{disco}\Program Files"),
            os.environ.get("ProgramFiles(x86)", rf"{disco}\Program Files (x86)"),
            os.environ.get("ProgramData", rf"{disco}\ProgramData"),
            rf"{disco}\Boot",
            rf"{disco}\Recovery",
            rf"{disco}\System Volume Information",
        ]
        return [os.path.normcase(os.path.normpath(c)) for c in carpetas]
    if SO == "Darwin":
        return ["/System", "/Library", "/usr", "/bin", "/sbin", "/etc",
                "/private", "/var", "/Applications", "/opt", "/cores", "/Volumes"]
    return ["/etc", "/usr", "/bin", "/sbin", "/lib", "/lib32", "/lib64", "/boot",
            "/var", "/opt", "/root", "/sys", "/proc", "/dev", "/srv", "/snap"]


CARPETAS_SISTEMA = _carpetas_sistema()

# Comandos que piden privilegios o cambian la configuración del sistema
# aunque no escriban una ruta del sistema de forma explícita.
_PATRONES_ELEVADOS = [
    r"(^|[\s;&|(])sudo\b", r"(^|[\s;&|(])doas\b", r"(^|[\s;&|(])su\s",
    r"\brunas\b", r"-Verb\s+RunAs", r"\bStart-Process\b.*RunAs",
    r"\breg(\.exe)?\s+(add|delete|import|copy|load|restore)\b",
    r"\bHKLM:?\\?", r"HKEY_LOCAL_MACHINE",
    r"\bbcdedit\b", r"\bdiskpart\b", r"\bformat\s+[a-zA-Z]:", r"\bsfc\b", r"\bdism\b",
    r"\bsc(\.exe)?\s+(config|delete|create)\b", r"\bnetsh\b", r"\bSet-ExecutionPolicy\b",
    r"\b(apt|apt-get|dnf|yum|pacman|zypper|snap)\s+(install|remove|purge|upgrade|dist-upgrade)\b",
    r"\bsystemctl\s+(enable|disable|mask|unmask|edit)\b",
    r"\b(mkfs|fdisk|parted|dd)\b", r"\bchown\b.*\s/", r"\bcsrutil\b", r"\bnvram\b",
    r"\bwinget\s+(install|uninstall|upgrade)\b", r"\bchoco\s+(install|uninstall|upgrade)\b",
]

# Primeras palabras de comandos que solo leen: no hace falta preguntar
# aunque mencionen una carpeta del sistema.
_SOLO_LECTURA = {
    "ls", "dir", "cat", "type", "head", "tail", "less", "more", "find", "grep",
    "rg", "stat", "file", "du", "df", "wc", "tree", "which", "where", "whereis",
    "echo", "pwd", "uname", "ps", "top", "get-childitem", "gci", "get-content",
    "gc", "get-item", "gi", "test-path", "select-string", "get-process",
    "get-service", "systeminfo", "ipconfig", "ifconfig", "ip", "sw_vers",
}


def es_ruta_sistema(ruta: str) -> bool:
    if not ruta:
        return False
    ruta = os.path.expanduser(os.path.expandvars(ruta.strip().strip("\"'")))
    absoluta = os.path.normcase(os.path.normpath(os.path.abspath(ruta)))
    for carpeta in CARPETAS_SISTEMA:
        if absoluta == carpeta or absoluta.startswith(carpeta.rstrip("\\/") + os.sep):
            return True
    return False


def _rutas_en_comando(comando: str) -> list[str]:
    try:
        partes = shlex.split(comando, posix=(SO != "Windows"))
    except ValueError:
        partes = comando.split()
    rutas = []
    for p in partes:
        p = p.strip("\"'")
        if SO == "Windows":
            if re.match(r"^[a-zA-Z]:[\\/]", p) or p.startswith("%") or p.startswith("$env:"):
                rutas.append(p)
        elif p.startswith("/") or p.startswith("~"):
            rutas.append(p)
        # rutas tras redirecciones del tipo >/etc/archivo
        m = re.search(r">{1,2}\s*(\S+)", p)
        if m:
            rutas.append(m.group(1))
    return rutas


def motivo_para_confirmar_comando(comando: str) -> str | None:
    """Devuelve una explicación si el comando necesita confirmación, o None si no."""
    for patron in _PATRONES_ELEVADOS:
        if re.search(patron, comando, re.IGNORECASE):
            return "el comando pide privilegios de administrador o cambia la configuración del sistema"
    rutas = [r for r in _rutas_en_comando(comando) if es_ruta_sistema(r)]
    if rutas:
        primera = comando.strip().split()[0].lower() if comando.strip() else ""
        primera = os.path.basename(primera).removesuffix(".exe")
        hay_redireccion = re.search(r"(^|[^2])>", comando) is not None
        encadenado = re.search(r"[;&|]", comando) is not None
        if primera in _SOLO_LECTURA and not hay_redireccion and not encadenado:
            return None
        return f"el comando toca carpetas del sistema: {', '.join(rutas)}"
    return None


def pedir_confirmacion(accion: str, motivo: str) -> bool:
    """Muestra una ventana emergente de Sí/No. Funciona sea cual sea la IA que llame.

    Si no se puede mostrar ninguna ventana (equipo sin pantalla), se deniega por seguridad.
    """
    titulo = "Asistente: necesita tu permiso"
    texto = f"El agente quiere hacer un cambio en el sistema.\n\nMotivo: {motivo}\n\nAcción:\n{accion[:1500]}\n\n¿Lo permites?"
    try:
        if SO == "Darwin":
            esc = texto.replace("\\", "\\\\").replace('"', '\\"')
            r = subprocess.run(
                ["osascript", "-e", f'display dialog "{esc}" with title "{titulo}" '
                 'buttons {"No", "Sí"} default button "No" with icon caution'],
                capture_output=True, text=True, timeout=600)
            return r.returncode == 0 and "Sí" in r.stdout
        if SO == "Linux":
            if shutil.which("zenity"):
                r = subprocess.run(["zenity", "--question", "--title", titulo, "--text", texto,
                                    "--ok-label=Sí", "--cancel-label=No", "--width=500"], timeout=600)
                return r.returncode == 0
            if shutil.which("kdialog"):
                r = subprocess.run(["kdialog", "--title", titulo, "--yesno", texto], timeout=600)
                return r.returncode == 0
        import tkinter
        from tkinter import messagebox
        raiz = tkinter.Tk()
        raiz.withdraw()
        raiz.attributes("-topmost", True)
        ok = messagebox.askyesno(titulo, texto, icon="warning", default="no", parent=raiz)
        raiz.destroy()
        return bool(ok)
    except Exception:
        return False
