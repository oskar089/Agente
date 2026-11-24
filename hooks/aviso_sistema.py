#!/usr/bin/env python3
"""Hook PreToolUse de Claude Code: si una acción toca carpetas del sistema,
obliga a Claude Code a mostrarte su diálogo de permiso antes de ejecutarla."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from seguridad import es_ruta_sistema, motivo_para_confirmar_comando  # noqa: E402


def motivo(herramienta: str, entrada: dict) -> str | None:
    nombre = herramienta.rsplit("__", 1)[-1]  # mcp__asistente-pc__energia -> energia
    if "command" in entrada:                   # Bash / PowerShell de Claude Code
        return motivo_para_confirmar_comando(entrada["command"])
    if nombre == "ejecutar_comando":
        return motivo_para_confirmar_comando(entrada.get("comando", ""))
    if nombre == "energia" and entrada.get("accion") != "cancelar":
        return f"vas a {entrada.get('accion')} el ordenador: se cerrarán los programas abiertos"
    for clave in ("file_path", "notebook_path", "ruta"):
        if clave in entrada and es_ruta_sistema(entrada[clave]):
            return f"{entrada[clave]} está en una carpeta del sistema"
    return None


def main() -> None:
    try:
        datos = json.load(sys.stdin)
    except Exception:
        return
    razon = motivo(datos.get("tool_name", ""), datos.get("tool_input") or {})
    if razon:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": f"⚠️ Cambio en el sistema: {razon}",
            }
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
