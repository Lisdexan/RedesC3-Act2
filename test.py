import random

from router import (LARGO_HEADER, check_routes, create_packet, fragment_IP_packet, parse_packet,
                    reassemble_IP_packet)

R = "rutas/"


def header(ip, puerto, ttl, id_, offset, size, flag):
    return (bytes(int(x) for x in ip.split(".")) + puerto.to_bytes(2, "big") + bytes([ttl])
            + id_.to_bytes(2, "big") + offset.to_bytes(2, "big") + size.to_bytes(4, "big") + bytes([flag]))


def paquete(id_, largo_total, ttl=10):
    msg = (b"abcdefghij" * 100)[:largo_total - LARGO_HEADER]
    return header("127.0.0.1", 8885, ttl, id_, 0, len(msg), 0) + msg


# parse / create con el header nuevo, armado a mano en bytes (test del enunciado)
IP_packet_v1 = header("127.0.0.1", 8885, 10, 347, 0, 5, 0) + b"hola!"
parsed_IP_packet = parse_packet(IP_packet_v1)
IP_packet_v2 = create_packet(parsed_IP_packet)
print("IP_packet_v1 == IP_packet_v2 ? {}".format(IP_packet_v1 == IP_packet_v2))
assert IP_packet_v1 == IP_packet_v2 and len(IP_packet_v1) == 16 + 5
assert create_packet(parsed_IP_packet).encode() == IP_packet_v1  # versión con .encode()
assert parsed_IP_packet == {"ip": "127.0.0.1", "port": 8885, "ttl": 10, "id": 347, "offset": 0,
                            "size": 5, "flag": 0, "msg": b"hola!"}

# check_routes devuelve (hop, MTU) y sigue con round-robin
r2 = R + "rutas_R2_v3_mtu.txt"
res = [check_routes(r2, ("127.0.0.1", 8885)) for _ in range(2)]
assert res == [(("127.0.0.1", 8883), 50), (("127.0.0.1", 8884), 80)], res
assert check_routes(r2, ("127.0.0.1", 9999)) is None
print("check_routes MTU + round-robin OK")

# fragmentar
p150 = paquete(347, 150)
assert len(p150) == 150
assert fragment_IP_packet(p150, 150) == [p150]
frags = fragment_IP_packet(p150, 50)
assert len(frags) > 1 and all(len(f) <= 50 for f in frags)
print(f"fragmentar OK ({len(frags)} fragmentos con MTU 50)")

# test del enunciado: fragmentar y reensamblar
fragment_list = fragment_IP_packet(p150, 50)
IP_packet_v2 = reassemble_IP_packet(fragment_list)
print("IP_packet_v1 = IP_packet_v2 ? {}".format(p150 == IP_packet_v2))

# reensamblar en orden, desordenado, e incompleto
assert reassemble_IP_packet(frags) == p150
random.shuffle(frags)
assert reassemble_IP_packet(frags) == p150
assert reassemble_IP_packet(frags[:-1]) is None
assert reassemble_IP_packet(frags[:1]) is None
assert reassemble_IP_packet([p150]) == p150
print("reensamblar OK (orden, desorden, incompleto, sin fragmentar)")

# re-fragmentar fragmentos (MTU 100 -> 50, como R1 -> R2 -> R3)
nivel1 = fragment_IP_packet(p150, 100)
nivel2 = [x for f in nivel1 for x in fragment_IP_packet(f, 50)]
assert all(len(f) <= 50 for f in nivel2)
random.shuffle(nivel2)
assert reassemble_IP_packet(nivel2) == p150
print("re-fragmentación OK")

# dos IDs intercalados, como el diccionario del router
a, b = paquete(1, 150), paquete(2, 120)
llegada = fragment_IP_packet(a, 60) + fragment_IP_packet(b, 55)
random.shuffle(llegada)
d, listos = {}, []
for fr in llegada:
    i = parse_packet(fr)["id"]
    d.setdefault(i, []).append(fr)
    x = reassemble_IP_packet(d[i])
    if x is not None:
        listos.append(x)
assert sorted(listos) == sorted([a, b])
print("IDs intercalados OK")
