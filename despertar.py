#!/usr/bin/env python3
"""Enciende un ordenador de la red local con Wake-on-LAN (paquete mágico).

Úsalo desde OTRO dispositivo que esté encendido en la misma red
(otro PC, una Raspberry Pi, un servidor...). No necesita librerías externas.

    python despertar.py AA:BB:CC:DD:EE:FF
    python despertar.py sobremesa            # nombre definido en config.json
"""

import json
import re
import socket
import sys
from pathlib import Path


def enviar_paquete_magico(mac: str, broadcast: str = "255.255.255.255", puerto: int = 9) -> None:
    limpia = re.sub(r"[^0-9A-Fa-f]", "", mac)
    if len(limpia) != 12:
        raise ValueError(f"Dirección MAC no válida: {mac}")
    paquete = bytes.fromhex("FF" * 6 + limpia * 16)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(paquete, (broadcast, puerto))
        s.sendto(paquete, (broadcast, 7))  # algunos equipos escuchan en el 7


def resolver_equipo(nombre_o_mac: str) -> tuple[str, str]:
    config = Path(__file__).with_name("config.json")
    if config.exists():
        equipos = json.loads(config.read_text(encoding="utf-8")).get("equipos", {})
        if nombre_o_mac in equipos:
            e = equipos[nombre_o_mac]
            return e["mac"], e.get("broadcast", "255.255.255.255")
    return nombre_o_mac, "255.255.255.255"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    mac, broadcast = resolver_equipo(sys.argv[1])
    enviar_paquete_magico(mac, broadcast)
    print(f"Paquete de encendido enviado a {mac} (broadcast {broadcast}).")
