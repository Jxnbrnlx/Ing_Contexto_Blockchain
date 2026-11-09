"""Generador de códigos QR (versión 3-L, modo byte, máscara 0) sin dependencias. Máx. 53 bytes."""
EXP, LOG = [0] * 512, [0] * 256
_x = 1
for _i in range(255):
    EXP[_i], LOG[_x] = _x, _i
    _x <<= 1
    if _x & 256:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def _mul(a, b):
    return 0 if not a or not b else EXP[LOG[a] + LOG[b]]


def _rs(datos, n=15):
    g = [1]
    for i in range(n):
        g = [(g[j] if j < len(g) else 0) ^ (_mul(g[j - 1], EXP[i]) if j else 0) for j in range(len(g) + 1)]
    r = [0] * n
    for d in datos:
        f = d ^ r[0]
        r = r[1:] + [0]
        r = [r[i] ^ _mul(g[i + 1], f) for i in range(n)]
    return r


def matriz(texto):
    data = texto.encode()
    if len(data) > 53:
        raise ValueError("Texto demasiado largo para el QR (máx. 53 bytes)")
    bits = "0100" + format(len(data), "08b") + "".join(format(b, "08b") for b in data) + "0000"
    bits += "0" * (-len(bits) % 8)
    cw = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
    while len(cw) < 55:
        cw.append(0xEC if len(cw) % 2 == len(cw) % 2 and (len(cw) - len(bits) // 8) % 2 == 0 else 0x11)
    cw = cw[:55]
    cw += _rs(cw)
    bits = "".join(format(c, "08b") for c in cw) + "0" * 7
    N = 29
    m = [[False] * N for _ in range(N)]
    fn = [[False] * N for _ in range(N)]

    def poner(x, y, v):
        m[y][x] = v
        fn[y][x] = True

    for cx, cy in ((3, 3), (N - 4, 3), (3, N - 4)):
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                x, y = cx + dx, cy + dy
                if 0 <= x < N and 0 <= y < N:
                    poner(x, y, max(abs(dx), abs(dy)) not in (2, 4))
    for i in range(N):
        poner(6, i, i % 2 == 0)
        poner(i, 6, i % 2 == 0)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            poner(22 + dx, 22 + dy, max(abs(dx), abs(dy)) != 1)
    d = 8
    r = d << 10
    for i in range(14, 9, -1):
        if r >> i & 1:
            r ^= 0x537 << (i - 10)
    f = ((d << 10) | r) ^ 0x5412
    b = lambda i: bool(f >> i & 1)
    for i in range(6):
        poner(8, i, b(i))
    poner(8, 7, b(6)); poner(8, 8, b(7)); poner(7, 8, b(8))
    for i in range(9, 15):
        poner(14 - i, 8, b(i))
    for i in range(8):
        poner(N - 1 - i, 8, b(i))
    for i in range(8, 15):
        poner(8, N - 15 + i, b(i))
    poner(8, N - 8, True)
    k, right = 0, N - 1
    while right >= 1:
        if right == 6:
            right = 5
        for v in range(N):
            for j in (0, 1):
                x = right - j
                y = N - 1 - v if ((right + 1) & 2) == 0 else v
                if not fn[y][x] and k < len(bits):
                    m[y][x] = bits[k] == "1"
                    k += 1
        right -= 2
    for y in range(N):
        for x in range(N):
            if not fn[y][x] and (x + y) % 2 == 0:
                m[y][x] = not m[y][x]
    return m


def svg(texto, escala=8, borde=4):
    m = matriz(texto)
    n = len(m) + 2 * borde
    rects = "".join(f'<rect x="{x + borde}" y="{y + borde}" width="1" height="1"/>'
                    for y, fila in enumerate(m) for x, v in enumerate(fila) if v)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" width="{n * escala}" height="{n * escala}">'
            f'<rect width="{n}" height="{n}" fill="#fff"/><g fill="#1f2a1d">{rects}</g></svg>')
