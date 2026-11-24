# Asistente PC

Un agente que hace las tareas que le pidas en tu ordenador, lo apaga cuando se lo dices
y **siempre te avisa antes de cambiar algo en carpetas del sistema**.
Funciona en Windows, macOS y Linux.

## Qué IA usa (sin pagar API)

| Opción | Coste | Cómo |
|---|---|---|
| **Claude Code con tu plan de Claude** (recomendado) | Incluido en Pro/Max | `claude` dentro de esta carpeta |
| Cualquier app compatible con MCP: Claude Desktop, Gemini CLI, Cursor, LM Studio… | Lo que cueste esa app | Pegar el bloque que muestra el instalador |
| Modelo local (LM Studio, Ollama + cliente MCP) | Gratis | Igual que la anterior; necesita un PC potente |

## Instalación

1. Instala **Python 3.10+** (python.org).
2. Instala **Claude Code**: https://code.claude.com (en Windows necesita también Git for Windows).
3. En esta carpeta:
   ```bash
   python instalar.py
   ```
4. Arranca el agente:
   ```bash
   claude
   ```
   La primera vez inicia sesión con tu cuenta de Claude.

Ejemplos: «organiza mi carpeta de Descargas por tipo», «instala VLC», «apaga el ordenador en 30 minutos», «cancela el apagado».

## Cómo funcionan los avisos

- **Uso normal** (tus carpetas, abrir programas, buscar, descargar): sin preguntas.
- **Carpetas del sistema** (`C:\Windows`, `Program Files`, registro HKLM / `/etc`, `/usr`, `/System`…),
  **`sudo`/administrador**, **instalar o desinstalar programas** y **apagar/reiniciar**: te sale un aviso y decides tú.
  - En Claude Code, el aviso es el diálogo de permisos de Claude Code (lo provoca `hooks/aviso_sistema.py`).
  - Con otras IAs, aparece una ventana emergente Sí/No. Si no se puede mostrar, la acción se deniega.
- Leer archivos del sistema no pregunta; cambiarlos, sí.

> La detección es por reglas (rutas y comandos conocidos), no infalible. Las demás apps traen
> sus propias herramientas de terminal, que no pasan por estos avisos: desactívalas
> y deja solo las de `asistente-pc` para que todo cambio pase por el aviso.

Las carpetas y comandos vigilados están en `seguridad.py` (`_carpetas_sistema` y `_PATRONES_ELEVADOS`).

## Encender el ordenador

Un ordenador apagado no puede encenderse solo: otro dispositivo de la misma red tiene que enviarle
una señal **Wake-on-LAN**.

**1. Activa Wake-on-LAN en el PC que quieres encender**
- BIOS/UEFI: activa «Wake on LAN» / «Power On by PCI-E».
- Windows: Administrador de dispositivos → tarjeta de red → Administración de energía → «Permitir que este dispositivo reactive el equipo»
  y en Opciones avanzadas «Wake on Magic Packet». Desactiva «Inicio rápido» en Opciones de energía.
- macOS: Ajustes → Batería/Energía → «Activar para acceso a la red».
- Linux: `sudo ethtool -s eth0 wol g` (hazlo persistente con NetworkManager).
- Mejor por **cable de red**; por Wi-Fi casi nunca funciona.

**2. Apunta su dirección MAC** (`ipconfig /all` en Windows, `ip link` en Linux, `ifconfig` en macOS)
y ponla en `config.json`:
```json
"equipos": { "sobremesa": { "mac": "AA:BB:CC:DD:EE:FF", "broadcast": "192.168.1.255" } }
```

**3. Elige quién envía la señal**
- **Desde el móvil**: cualquier app de Wake-on-LAN (gratis) con esa MAC. Lo más sencillo para empezar.
- **Desde otro equipo siempre encendido** (otro PC, Raspberry Pi, servidor):
  `python despertar.py sobremesa`. Si instalas el asistente ahí, puedes decirle «enciende el sobremesa».
- **Desde fuera de casa**: muchos routers tienen Wake-on-LAN en su panel o app; o usa una VPN (p. ej. Tailscale) hacia el equipo que envía la señal.
- **Alternativa sin WoL**: en la BIOS activa «Restore on AC power loss = Power On» y usa un enchufe inteligente.

## Archivos

| Archivo | Para qué |
|---|---|
| `servidor_mcp.py` | Herramientas del agente para cualquier IA: comandos, archivos, energía, Wake-on-LAN |
| `seguridad.py` | Detecta cambios en el sistema y muestra el aviso |
| `hooks/aviso_sistema.py` | Hace que Claude Code pida permiso en esos casos |
| `despertar.py` | Enciende un equipo de la red (no necesita nada instalado) |
| `instalar.py` | Configura todo en tu ordenador |
| `CLAUDE.md` | Instrucciones de comportamiento del agente |
