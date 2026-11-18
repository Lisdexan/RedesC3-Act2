# python3 enviar.py IP_final puerto_final "mensaje" IP_envio puerto_envio [ttl] [id]
# Arma un paquete sin fragmentar (offset 0, FLAG 0) en bytes y lo manda a (IP_envio, puerto_envio).
import socket
import sys

from router import create_packet

ip_final, puerto_final, mensaje, ip_envio, puerto_envio = sys.argv[1:6]
ttl = int(sys.argv[6]) if len(sys.argv) > 6 else 64
id_ = int(sys.argv[7]) if len(sys.argv) > 7 else 1
msg = mensaje.encode()
paquete = create_packet({"ip": ip_final, "port": int(puerto_final), "ttl": ttl, "id": id_,
                         "offset": 0, "size": len(msg), "flag": 0, "msg": msg})
socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(paquete, (ip_envio, int(puerto_envio)))
