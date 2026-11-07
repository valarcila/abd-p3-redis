"""EnVivo · fase 3 · sala de espera virtual.

Cola de prioridad: los valores grandes son peticiones de alta prioridad y los
pequeños de baja. El operador atiende siempre la de mayor prioridad y, si no
hay ninguna, **espera** hasta que llegue.

Las firmas y los valores de retorno **no deben cambiarse**.
"""

import redis

PRIORIDAD_ABSOLUTA = float('inf')
PREFIJO_SALA = 'envivo:sala'

def clave(evento_id) -> str:
    """Clave de Redis. Formato: envivo:sala:<evento>"""
    return f"{PREFIJO_SALA}:{evento_id}"

def entrar(r: redis.Redis, evento_id, usuario_id, prioridad: float) -> bool:
    """Registra al usuario en la sala con esa prioridad.

    Devuelve True si es nuevo en la cola y False si ya estaba (en ese caso se
    le actualiza la prioridad). Un usuario **no puede ocupar dos puestos**.
    """
    # zadd(), devolver miembros agregados
    # 0 = False, 1 = True
    return bool(r.zadd(clave(evento_id), {usuario_id:prioridad}))

def atender_siguiente(r: redis.Redis, evento_id, timeout: int = 0):
    """Toma y elimina la petición de mayor prioridad.

    Devuelve `(usuario_id, prioridad)`, o None si se agota el `timeout`.
    Con `timeout=0` espera indefinidamente. Obtener y eliminar deben ser una
    sola operación, o dos operadores podrían atender al mismo usuario.
    """
    # bzpopmax(), devolver tupla con clave, usuario y prioridad
    peticion = r.bzpopmax(clave(evento_id), timeout = timeout)

    if peticion is None: return None

    clave_cola, usuario_id, prioridad = peticion

    return (usuario_id, prioridad)

def en_espera(r: redis.Redis, evento_id) -> int:
    """Cuántos usuarios hay en la sala."""
    return r.zcard(clave(evento_id))

def posicion(r: redis.Redis, evento_id, usuario_id) -> int | None:
    """Puesto en la cola **empezando en 1**, o None si el usuario no está.

    El puesto 1 es el que se va a atender antes.
    """
    # zrevrank(), consultar puesto de mayor a menor prioridad
    puesto = r.zrevrank(clave(evento_id), usuario_id)

    if puesto is None: return None

    return 1 + puesto
