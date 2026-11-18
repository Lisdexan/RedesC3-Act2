# Redes C3
## Actividad 2 (Fragmentación)
Para ejecutar el proyecto se debe runear desde una virtual box, linux. Primero se levantan los 5 routers con `for i in 1 2 3 4 5; do python3 router.py 127.0.0.1 888$i rutas/rutas_R${i}_v3_mtu.txt > R$i.log 2>&1 & done` (cada uno escribe en su R$i.log) y se apagan con `pkill -f router.py`.
Luego, en otra terminal en la misma carpeta, se envía un paquete con `python3 enviar.py 127.0.0.1 8885 "hola!" 127.0.0.1 8881 10 347` (IP_final, puerto_final, mensaje, IP_envío, puerto_envío, TTL e ID), que va de R1 a R5 sin fragmentarse.
Para un paquete de 150 bytes (header de 16 + mensaje de 134) se usa `MSG=$(python3 -c "print(('abcdefghij'*20)[:134])")` y `python3 enviar.py 127.0.0.1 8885 "$MSG" 127.0.0.1 8881 64 401`. Conviene TTL 64, porque con TTL 10 los fragmentos pueden morir antes de llegar y no se reensambla. Con `grep -c "^abcdefghij" R5.log` se cuentan los datagramas reensamblados, y con `grep redirigiendo R2.log | grep ";401;" | cut -d';' -f3-7` se ven los fragmentos que reenvía R2 (ttl;id;offset;tamaño;flag).
Los tests rápidos de las funciones se corren con `python3 test.py`.
