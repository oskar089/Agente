#!/usr/bin/env python3
"""Configura el asistente en este ordenador (Windows, macOS o Linux).

Ejecútalo una vez:  python instalar.py
Crea config.json, la configuración de Claude Code (.claude/settings.json y .mcp.json)
y muestra cómo conectar el servidor MCP con otras IAs.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PY = sys.executable
SERVIDOR = str(RAIZ / "servidor_mcp.py")
HOOK = str(RAIZ / "hooks" / "aviso_sistema.py")


def escribir(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  ✔ {ruta.relative_to(RAIZ)}")


def main() -> None:
    print("Instalando dependencias…")
    subprocess.run([PY, "-m", "pip", "install", "-q", "-r", str(RAIZ / "requirements.txt")], check=True)

    print("Creando configuración…")
    if not (RAIZ / "config.json").exists():
        shutil.copy(RAIZ / "config.ejemplo.json", RAIZ / "config.json")
        print("  ✔ config.json (edítalo para añadir las MAC de tus equipos)")

    # Claude Code: servidor MCP del proyecto. Claude Code ya pide permiso con su
    # propio diálogo (hook), así que el servidor no abre ventanas.
    escribir(RAIZ / ".mcp.json", {"mcpServers": {"asistente-pc": {
        "command": PY, "args": [SERVIDOR], "env": {"ASISTENTE_CONFIRMA_CLIENTE": "1"}}}})

    escribir(RAIZ / ".claude" / "settings.json", {
        "permissions": {
            # Sin restricciones en el uso normal del ordenador…
            "allow": ["Bash", "PowerShell", "Read", "Write", "Edit", "Glob", "Grep",
                      "WebFetch", "WebSearch", "mcp__asistente-pc"],
            "defaultMode": "acceptEdits",
        },
        # …pero el hook fuerza el diálogo de permiso si se toca el sistema.
        "hooks": {"PreToolUse": [{
            "matcher": "Bash|PowerShell|Write|Edit|MultiEdit|NotebookEdit|mcp__asistente-pc__.*",
            "hooks": [{"type": "command", "command": PY, "args": [HOOK], "timeout": 10}],
        }]},
        "enableAllProjectMcpServers": True,
        "language": "spanish",
    })

    bloque = json.dumps({"mcpServers": {"asistente-pc": {"command": PY, "args": [SERVIDOR]}}},
                        indent=2, ensure_ascii=False)
    print(f"""
Listo.

▶ Con tu plan de Claude (sin pagar API):
    cd "{RAIZ}"
    claude
  La primera vez inicia sesión con tu cuenta de Claude (Pro/Max).

▶ Con otra IA (Claude Desktop, Gemini CLI, Cursor, LM Studio…):
  añade esto a la configuración MCP de esa aplicación:

{bloque}
""")


if __name__ == "__main__":
    main()
