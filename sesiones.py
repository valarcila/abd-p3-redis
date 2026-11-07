"""EnVivo · fase 3 · usuarios y sesiones.

De cada usuario se guarda: nombre completo, nombre de usuario, contraseña
(puede estar en plano), privilegios (entero positivo) y el token de sesión si
tiene una activa. Las sesiones duran **un mes** y al caducar desaparecen solas.

Las firmas y los valores de retorno **no deben cambiarse**.
"""

import redis

# generar valores aleatorios
import secrets

# un mes
DURACION_SESION = 30 * 24 * 60 * 60
SIN_ACCESO = -1

PREFIJO_USUARIO = 'envivo:usuario'
PREFIJO_SESION = 'envivo:sesion'


def clave_usuario(usuario: str) -> str:
    """Formato: envivo:usuario:<usuario>"""
    return f"{PREFIJO_USUARIO}:{usuario}"


def clave_sesion(token: str) -> str:
    """Formato: envivo:sesion:<token>"""
    return f"{PREFIJO_SESION}:{token}"


# ── Gestión de usuarios (CRUD) ──────────────────────────────────────────────

def crear_usuario(r: redis.Redis, usuario: str, nombre: str,
                  password: str, privilegios: int) -> bool:
    """Crea el usuario si no existe. Devuelve si se ha creado."""
    if r.exists(clave_usuario(usuario)): return False

    data = {
        'usuario': usuario,
        'nombre': nombre,
        'password': password,
        'privilegios': privilegios
    }

    # mapping, guardar diccionario fields
    r.hset(clave_usuario(usuario), mapping = data)

    return True


def obtener_usuario(r: redis.Redis, usuario: str) -> dict | None:
    """Todos los campos del usuario, o None si no existe.

    `privilegios` debe venir como **entero**, no como cadena.
    """
    data = r.hgetall(clave_usuario(usuario))

    # hgetall() puede devolver {}
    if not data: return None

    data['privilegios'] = int(data['privilegios'])

    return data


def actualizar_usuario(r: redis.Redis, usuario: str, **campos) -> bool:
    """Modifica los campos indicados y **solo** esos.

    Devuelve False si el usuario no existe.
    """
    clave = clave_usuario(usuario)

    if not r.exists(clave): return False

    if campos: r.hset(clave, mapping = campos)

    return True


def borrar_usuario(r: redis.Redis, usuario: str) -> bool:
    """Borra el usuario. Si tenía sesión abierta, debe quedar cerrada."""
    data = obtener_usuario(r, usuario)

    if data is None: return False

    token = data.get('token')

    if token: logout(r, token)

    return bool(r.delete(clave_usuario(usuario)))


# ── Sesiones ────────────────────────────────────────────────────────────────

def login(r: redis.Redis, usuario: str, password: str) -> tuple[int, str | None]:
    """Comprueba las credenciales y abre una sesión.

    Devuelve `(privilegios, token)` si son correctas y `(-1, None)` si no.
    Un login nuevo debe invalidar la sesión anterior del mismo usuario.
    """
    data = obtener_usuario(r, usuario)

    if data is None or data['password'] != password: return (SIN_ACCESO, None)

    token_anterior = data.get('token')

    if token_anterior: r.delete(clave_sesion(token_anterior))

    # generar token 16 bytes aleatorios
    # token_hex(), str
    token = secrets.token_hex(16)

    # guardar sesion
    # ex tiempo de expiracion
    r.set(clave_sesion(token), usuario, ex = DURACION_SESION)

    # guardar token en usuario
    r.hset(clave_usuario(usuario), 'token', token)

    return (data['privilegios'], token)


def login_por_token(r: redis.Redis, token: str) -> int:
    """Privilegios asociados al token, o -1 si no vale.

    Un token cuya sesión ha caducado devuelve -1, igual que uno inventado.
    """
    if not token: return SIN_ACCESO

    usuario = r.get(clave_sesion(token))

    if usuario is None: return SIN_ACCESO

    data = obtener_usuario(r, usuario)

    if data is None: return SIN_ACCESO

    return data['privilegios']


def logout(r: redis.Redis, token: str) -> bool:
    """Cierra la sesión. Devuelve si había una sesión que cerrar."""
    if not token: return False

    clave_s = clave_sesion(token)

    usuario = r.get(clave_s)

    if usuario is None: return False

    r.delete(clave_s)

    clave_u = clave_usuario(usuario)

    # limpiar token
    if r.hget(clave_u, 'token') == token: r.hdel(clave_u, 'token')

    return True


def segundos_de_sesion(r: redis.Redis, token: str) -> int:
    """Segundos que le quedan a la sesión. -2 si no existe."""
    return r.ttl(clave_sesion(token))
