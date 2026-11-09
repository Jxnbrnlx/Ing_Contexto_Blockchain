"""Cadena de bloques SHA-256 y reglas de negocio de OrigenChain."""
import hashlib, json, os, threading, time

FLUJO = ["CREACION", "RECEPCION", "DESPACHO", "ENTREGA", "VERIFICACION"]
ROLES = {"CREACION": "Agricultor", "RECEPCION": "Cooperativa", "DESPACHO": "Transportador",
         "ENTREGA": "Transportador", "VERIFICACION": "Exportador/Tostador"}


class ErrorNegocio(ValueError):
    pass


def calcular_hash(b):
    campos = {k: b[k] for k in ("indice", "marca_tiempo", "lote", "evento", "actor", "rol", "datos", "hash_previo")}
    return hashlib.sha256(json.dumps(campos, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Cadena:
    def __init__(self, ruta="cadena.json"):
        self.ruta, self.lock, self.bloques = ruta, threading.RLock(), []
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                self.bloques = json.load(f)
        if not self.bloques:
            self._anexar("-", "GENESIS", "OrigenChain", "Sistema", {}, "0" * 64)

    def _anexar(self, lote, evento, actor, rol, datos, previo):
        b = {"indice": len(self.bloques), "marca_tiempo": time.strftime("%Y-%m-%d %H:%M:%S"), "lote": lote,
             "evento": evento, "actor": actor, "rol": rol, "datos": datos, "hash_previo": previo}
        b["hash"] = calcular_hash(b)
        self.bloques.append(b)
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(self.bloques, f, ensure_ascii=False, indent=1)
        return b

    def eventos(self, lote):
        return [b for b in self.bloques if b["lote"] == lote]

    def registrar_lote(self, actor, datos):
        for c in ("producto", "origen", "kg"):
            if not str(datos.get(c, "")).strip():
                raise ErrorNegocio(f"Falta el campo obligatorio: {c}")
        try:
            kg = float(datos["kg"])
        except ValueError:
            raise ErrorNegocio("El peso debe ser numérico")
        if kg <= 0:
            raise ErrorNegocio("El peso debe ser mayor que cero")
        datos["kg"] = kg
        with self.lock:
            pref = "CAF" if "caf" in datos["producto"].lower() else "CAC"
            n = 1042 + len({b["lote"] for b in self.bloques if b["evento"] == "CREACION"})
            lote = f"OC-{pref}-{n}"
            return self._anexar(lote, "CREACION", actor or "Agricultor", ROLES["CREACION"], datos, self.bloques[-1]["hash"])

    def registrar_evento(self, lote, evento, actor, datos=None):
        with self.lock:
            ev = self.eventos(lote)
            if not ev:
                raise ErrorNegocio("El lote no existe")
            if len(ev) >= len(FLUJO):
                raise ErrorNegocio("El lote ya completó su trazabilidad")
            esperado = FLUJO[len(ev)]
            if evento != esperado:
                raise ErrorNegocio(f"Evento fuera de secuencia: se esperaba {esperado}")
            return self._anexar(lote, evento, actor or ROLES[evento], ROLES[evento], datos or {}, self.bloques[-1]["hash"])

    def lotes(self, q=""):
        res = []
        for b in self.bloques:
            if b["evento"] != "CREACION":
                continue
            ev = self.eventos(b["lote"])
            d = b["datos"]
            item = {"lote": b["lote"], **d, "estado": ev[-1]["evento"], "eventos": len(ev),
                    "siguiente": FLUJO[len(ev)] if len(ev) < len(FLUJO) else None}
            if q.lower() in json.dumps(item, ensure_ascii=False).lower():
                res.append(item)
        return res

    def verificar(self):
        for i, b in enumerate(self.bloques):
            if b["hash"] != calcular_hash(b) or (i and b["hash_previo"] != self.bloques[i - 1]["hash"]):
                return {"valida": False, "bloque_invalido": i}
        return {"valida": True, "bloque_invalido": None}

    def resumen(self):
        ls = self.lotes()
        por = {}
        for l in ls:
            por[l["estado"]] = por.get(l["estado"], 0) + 1
        return {"lotes": len(ls), "movimientos": len(self.bloques) - 1, "kg": sum(l["kg"] for l in ls),
                "bloques": len(self.bloques), "por_estado": por, "integridad": self.verificar()}

    def sembrar(self):
        if len(self.bloques) > 1:
            return
        b = self.registrar_lote("Asociación Cafetera El Roble", {"producto": "Café especial", "variedad": "Caturra",
            "origen": "Pitalito, Huila", "kg": 180, "productor": "Asociación Cafetera El Roble"})
        self.registrar_evento(b["lote"], "RECEPCION", "Cooperativa del Sur del Huila", {"nota": "Recepción confirmada"})
        self.registrar_evento(b["lote"], "DESPACHO", "Transportes Andina", {"nota": "Traslado a Bogotá"})
