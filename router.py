# python3 router.py router_IP router_puerto archivo_rutas_mtu.txt
import ipaddress
import socket
import sys

# Header (16 bytes, big-endian), en este orden:
#   IP      4 bytes  (a.b.c.d, un byte por número)
#   puerto  2 bytes
#   TTL     1 byte   (1 a 255)
#   ID      2 bytes  (hasta 65535, como el Identification de IPv4)
#   offset  2 bytes  (en bytes, no en octetos)
#   tamaño  4 bytes  (largo del mensaje sin header)
#   FLAG    1 byte   (1 = quedan fragmentos, 0 = último)
# Lo que sigue después de los 16 bytes es el mensaje.
LARGO_HEADER = 16

# Estado de round-robin: (archivo de rutas, zona) -> índice de la última ruta usada
_rr = {}


class Paquete(bytes):
    """Paquete en bytes con un .encode() que devuelve los mismos bytes, para que el
    test del enunciado create_packet(...).encode() funcione aunque el paquete sea bytes."""

    def encode(self, *args, **kwargs):
        return bytes(self)


def parse_packet(IP_packet: bytes):
    h = IP_packet
    return {
        "ip": ".".join(str(b) for b in h[0:4]),
        "port": int.from_bytes(h[4:6], "big"),
        "ttl": h[6],
        "id": int.from_bytes(h[7:9], "big"),
        "offset": int.from_bytes(h[9:11], "big"),
        "size": int.from_bytes(h[11:15], "big"),
        "flag": h[15],
        "msg": bytes(h[LARGO_HEADER:]),
    }


def create_packet(parsed_IP_packet) -> Paquete:
    p = parsed_IP_packet
    msg = p["msg"].encode() if isinstance(p["msg"], str) else p["msg"]
    header = (bytes(int(x) for x in p["ip"].split("."))
              + p["port"].to_bytes(2, "big")
              + p["ttl"].to_bytes(1, "big")
              + p["id"].to_bytes(2, "big")
              + p["offset"].to_bytes(2, "big")
              + p["size"].to_bytes(4, "big")
              + p["flag"].to_bytes(1, "big"))
    return Paquete(header + msg)


def legible(p) -> str:
    """Paquete parseado en texto, solo para imprimirlo en los logs:
    ip;puerto;ttl;id;offset;tamaño;flag;mensaje"""
    return (f"{p['ip']};{p['port']};{p['ttl']};{p['id']};{p['offset']};{p['size']};{p['flag']};"
            f"{p['msg'].decode(errors='replace')}")


def check_routes(routes_file_name: str, destination_address: tuple):
    ip, puerto = destination_address
    zona_actual = None
    candidatas = []
    with open(routes_file_name) as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            red, p_ini, p_fin, hop_ip, hop_puerto, mtu = linea.split()[:6]
            en_red = ipaddress.ip_address(ip) in ipaddress.ip_network(red, strict=False)
            if en_red and int(p_ini) <= puerto <= int(p_fin):
                zona = (red, int(p_ini), int(p_fin))
                if zona_actual is None:
                    zona_actual = zona  # la primera ruta que calza define la zona
                if zona == zona_actual:
                    candidatas.append(((hop_ip, int(hop_puerto)), int(mtu)))
    if not candidatas:
        return None
    llave = (routes_file_name, zona_actual)
    i = (_rr.get(llave, -1) + 1) % len(candidatas)
    _rr[llave] = i
    return candidatas[i]  # (next_hop_address, MTU)


def fragment_IP_packet(IP_packet: bytes, MTU: int):
    if len(IP_packet) <= MTU:
        return [IP_packet]
    p = parse_packet(IP_packet)
    msg = p["msg"]
    trozo = MTU - LARGO_HEADER  # len(trozo_mensaje_en_bytes) = MTU - tamaño_header_en_bytes
    if trozo <= 0:
        raise ValueError("MTU demasiado chico para el header")
    fragmentos = []
    for i in range(0, len(msg), trozo):
        parte = msg[i:i + trozo]
        es_ultimo = i + trozo >= len(msg)
        # El último trozo conserva el FLAG del paquete que se corta: si ese paquete ya
        # era un fragmento con FLAG 1, sus pedazos siguen diciendo que faltan más.
        frag = {**p, "msg": parte, "size": len(parte), "offset": p["offset"] + i,
                "flag": p["flag"] if es_ultimo else 1}
        fragmentos.append(create_packet(frag))
    return fragmentos


def reassemble_IP_packet(fragment_list):
    partes = {}
    for fr in fragment_list:
        p = parse_packet(fr)
        partes[p["offset"]] = p  # si llega repetido, queda uno solo
    if not partes:
        return None
    orden = [partes[o] for o in sorted(partes)]  # ordenar por offset
    esperado = 0
    for p in orden:
        if p["offset"] != esperado:
            return None  # falta un fragmento al medio (o el primero)
        esperado += p["size"]
    if orden[-1]["flag"] != 0:
        return None  # falta el último
    # Un paquete sin fragmentar es simplemente offset 0 y FLAG 0, así que pasa por aquí igual.
    msg = b"".join(p["msg"] for p in orden)
    return create_packet({**orden[0], "msg": msg, "size": len(msg), "flag": 0})


def main():
    router_ip, router_puerto, rutas = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    yo = (router_ip, router_puerto)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(yo)
    recibidos = {}  # ID -> lista de fragmentos/paquetes que llegaron para este router
    while True:
        data, _ = sock.recvfrom(4096)
        paquete = parse_packet(data)
        destino = (paquete["ip"], paquete["port"])
        if paquete["ttl"] <= 0:
            print(f"Se recibió paquete {legible(paquete)} con TTL 0", flush=True)
            continue
        if destino == yo:
            recibidos.setdefault(paquete["id"], []).append(data)
            completo = reassemble_IP_packet(recibidos[paquete["id"]])
            if completo is not None:
                print(parse_packet(completo)["msg"].decode(errors="replace"), flush=True)
                del recibidos[paquete["id"]]
            continue
        ruta = check_routes(rutas, destino)
        if ruta is None:
            print(f"No hay rutas hacia {destino} para paquete {legible(paquete)}", flush=True)
            continue
        hop, mtu = ruta
        paquete["ttl"] -= 1  # se decrementa antes de fragmentar: todos los fragmentos salen con el mismo TTL
        try:
            lista = fragment_IP_packet(create_packet(paquete), mtu)
        except ValueError as e:
            print(f"Se descarta paquete {legible(paquete)}: {e}", flush=True)
            continue
        for frag in lista:
            sock.sendto(frag, hop)
            print(f"redirigiendo paquete {legible(parse_packet(frag))} con destino final {destino} "
                  f"desde {yo} hacia {hop}", flush=True)


if __name__ == "__main__":
    main()
