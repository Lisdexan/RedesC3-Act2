# python3 prueba_router.py "127.0.0.1;8885;10;100" IP_router_inicial puerto_router_inicial [archivo]
# headers = ip;puerto;ttl;id_inicial  (el ID sube en 1 por cada línea para no mezclar datagramas)
import socket
import sys

from router import create_packet

ip, puerto, ttl, id_ini = sys.argv[1].split(";")
ip_inicial, puerto_inicial = sys.argv[2], int(sys.argv[3])
archivo = sys.argv[4] if len(sys.argv) > 4 else "mensajes.txt"
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
with open(archivo) as f:
    for n, linea in enumerate(f):
        msg = linea.rstrip("\n").encode()
        paquete = create_packet({"ip": ip, "port": int(puerto), "ttl": int(ttl), "id": int(id_ini) + n,
                                 "offset": 0, "size": len(msg), "flag": 0, "msg": msg})
        sock.sendto(paquete, (ip_inicial, puerto_inicial))
