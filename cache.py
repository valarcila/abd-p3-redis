"""EnVivo · fase 3 · caché de documentos.

Hay que implementar la clase `CacheDocumentos`. Las firmas y los valores de
retorno **no deben cambiarse**: son el contrato con el que se corrige.
"""

import redis
from bson import json_util

# 24 horas
TTL_POR_DEFECTO = 24 * 60 * 60
MEMORIA_MAXIMA = "150mb"
# politica enunciado
POLITICA_DESALOJO = "volatile-ttl"


class CacheDocumentos:
    """Caché de documentos con caducidad renovada en cada acceso."""

    def __init__(self, cliente: redis.Redis, ttl: int = TTL_POR_DEFECTO):
        self._r = cliente
        self.ttl = ttl

    def configurar_limite(self, memoria: str = MEMORIA_MAXIMA, politica: str = POLITICA_DESALOJO) -> None:
        """Fija el límite de memoria y la política de desalojo de la caché."""
        self._r.config_set("maxmemory", memoria)
        self._r.config_set("maxmemory-policy", politica)

    @staticmethod
    def clave(coleccion: str, id_documento) -> str:
        """Clave de Redis para un documento. Formato: envivo:cache:<col>:<id>"""
        return f"envivo:cache:{coleccion}:{id_documento}"

    def get(self, coleccion: str, id_documento) -> dict | None:
        """Devuelve el documento cacheado, o None si no está.

        Cada acceso debe **renovar la caducidad** a `self.ttl`.
        """
        clave_identificadora = self.clave(coleccion, id_documento)
        valor = self._r.getex(clave_identificadora, ex = self.ttl)

        if valor is None: return None

        # reconstruir diccionario python a partir del valor almacenado, 
        # recuperando los tipos bson
        return json_util.loads(valor)

    def set(self, coleccion: str, id_documento, documento: dict) -> None:
        """Guarda el documento en la caché con su caducidad.

        `get` tiene que devolverlo igual, con los mismos tipos: las fechas como
        fechas y los ObjectId como ObjectId.
        """
        clave_identificadora = self.clave(coleccion, id_documento) 

        # transformar documento en una cadena que redis puede almacenar, 
        # conservando la informacion necesaria para reconstruir los tipos bson
        valor_serializado = json_util.dumps(documento)
        
        self._r.set(clave_identificadora, valor_serializado, ex = self.ttl)

    def invalidar(self, coleccion: str, id_documento) -> bool:
        """Saca el documento de la caché. Devuelve si estaba."""
        clave_identificadora = self.clave(coleccion, id_documento)
        eliminadas = self._r.unlink(clave_identificadora)
        return eliminadas > 0

    def caducidad(self, coleccion: str, id_documento) -> int:
        """Segundos restantes. -1 si no caduca, -2 si no existe."""
        clave_identificadora = self.clave(coleccion, id_documento)
        return self._r.ttl(clave_identificadora)
