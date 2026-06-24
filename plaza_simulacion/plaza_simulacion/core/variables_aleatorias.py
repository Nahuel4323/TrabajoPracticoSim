"""
Generadores de variables aleatorias usados por la simulación.
"""

import math
import random


def gen_exponencial(media: float) -> tuple[float, float]:
    """Devuelve (rnd, valor) con TS = -media * ln(1-rnd)."""
    rnd = random.random()
    ts = -media * math.log(1 - rnd)
    return round(rnd, 4), round(ts, 4)


def gen_uniforme(a: float, b: float) -> tuple[float, float]:
    """Devuelve (rnd, valor) con valor = a + (b-a)*rnd."""
    rnd = random.random()
    val = a + (b - a) * rnd
    return round(rnd, 4), round(val, 2)


def gen_decision(prob_si: float) -> tuple[float, bool]:
    """Devuelve (rnd, True si acepta)."""
    rnd = random.random()
    return round(rnd, 4), rnd < prob_si
