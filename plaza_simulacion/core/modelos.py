"""
Modelos de datos del sistema: Servidor (contacto/entrevistador) y Transeunte.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Servidor:
    id: int
    tipo: str          # "contacto" o "entrevistador"
    libre: bool = True
    fin_atencion: float = None
    id_transeunte: int = None
    tiempo_inicio: float = None

    def estado_str(self) -> str:
        return "Libre" if self.libre else "Ocupado"


@dataclass
class Transeunte:
    id: int
    rnd_edad: float
    edad: float
    estado: str = "Siendo Informado"
    tiempo_inicio_info: float = None
    tiempo_fin_info: float = None
    tiempo_inicio_entrevista: float = None
    tiempo_fin_entrevista: float = None
    rnd_acepta: float = None
    acepta: Optional[bool] = None
    tabla_rk: list = field(default_factory=list)
    t_info_unidades: float = None
    t_info_minutos: float = None
