"""
Simulación "PLAZA" - TP5 Simulación UTN FRC 4K1 2026
Sistema: Investigación de mercado en Plaza San Martín de Córdoba.
"""

import streamlit as st
import pandas as pd
import math
import random
from dataclasses import dataclass, field
from typing import Optional
import copy

# ─────────────────────────────────────────────────────────────────────────────
# 1.  PARÁMETROS (modificables por el usuario)
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_PARAMS = {
    "media_llegada_min": 60 / 90,       # 0.6667 min entre llegadas
    "media_entrevista_min": 3.0,        # 3 min por entrevista
    "prob_acepta_entrevista": 0.85,
    "prob_vuelve_tarde": 0.25,
    "edad_min": 20,
    "edad_max": 85,
    "n_contactos": 2,
    "n_entrevistadores": 4,
    "tiempo_inicio_min": 0.0,           # reloj arranca en 0 (= 10 AM)
    "duracion_jornada_min": 360.0,      # 6 horas
    "rk_h": 0.1,                        # paso Runge-Kutta
    "segundos_por_unidad_t": 8,         # 1 unidad t = 8 segundos
    "max_iter": 100_000,
    "iter_desde_j": 1,
    "iter_mostrar_i": 50,
}

# ─────────────────────────────────────────────────────────────────────────────
# 2.  RUNGE-KUTTA para calcular tiempo de información
# ─────────────────────────────────────────────────────────────────────────────

def f_ode(t: float, E: float, h: float) -> float:
    """dE/dt = (t^2 - E) * h^2"""
    return (t ** 2 - E) * h ** 2


def runge_kutta_tiempo_info(edad: float, h: float, seg_por_unidad: int) -> tuple[float, float, list[dict]]:
    """
    Integra dE/dt = (t^2 - E)*h^2 con E(0)=edad hasta que dE/dt > 0.
    Devuelve (t_final_unidades, t_final_minutos, tabla_rk_pasos).
    """
    t = 0.0
    E = edad
    tabla = []

    max_steps = 100_000
    steps = 0
    t_final = None

    while steps < max_steps:
        k1 = f_ode(t, E, h)
        k2 = f_ode(t + h / 2, E + h / 2 * k1, h)
        k3 = f_ode(t + h / 2, E + h / 2 * k2, h)
        k4 = f_ode(t + h, E + h * k3, h)

        t_new = round(t + h, 10)
        E_new = E + (h / 6) * (k1 + 2 * k2 + 2 * k3 + k4)

        tabla.append({
            "t": round(t, 4),
            "E": round(E, 6),
            "K1": round(k1, 6),
            "K2": round(k2, 6),
            "K3": round(k3, 6),
            "K4": round(k4, 6),
            "t(i+1)": round(t_new, 4),
            "E(i+1)": round(E_new, 6),
        })

        t = t_new
        E = E_new

        # Velocidad de crecimiento ACTUAL (ya en el nuevo punto)
        dE_new = f_ode(t, E, h)
        if dE_new > 0:
            t_final = t
            break
        steps += 1

    if t_final is None:
        t_final = t  # fallback

    t_segundos = t_final * seg_por_unidad
    t_minutos = t_segundos / 60.0
    return t_final, t_minutos, tabla


# ─────────────────────────────────────────────────────────────────────────────
# 3.  VARIABLES ALEATORIAS
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# 4.  ESTADO DEL SISTEMA
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# 5.  NÚCLEO DE SIMULACIÓN
# ─────────────────────────────────────────────────────────────────────────────

class SimulacionPlaza:
    def __init__(self, params: dict):
        self.p = params
        self.reset()

    def reset(self):
        p = self.p
        self.reloj = p["tiempo_inicio_min"]
        self.iter = 0
        self.fin_jornada = p["tiempo_inicio_min"] + p["duracion_jornada_min"]
        self.jornada_terminada = False

        # Servidores
        self.contactos = [Servidor(i + 1, "contacto") for i in range(p["n_contactos"])]
        self.entrevistadores = [Servidor(i + 1, "entrevistador") for i in range(p["n_entrevistadores"])]

        # Transeunte counter
        self.id_transeunte = 0
        self.transeuntes_activos: dict[int, Transeunte] = {}

        # Métricas / contadores
        self.contador_entrevistas_finalizadas = 0
        self.contador_entrevistas_aceptadas = 0
        self.contador_abandonos_contactos_ocupados = 0
        self.contador_transeuntes_totales = 0
        self.contador_volvieron_preguntar = 0
        self.contador_informados = 0
        self.contador_informados_no_fueron_entrevista = 0
        self.acum_tiempo_contactos_ocupados = 0.0
        self.acum_tiempo_entrevistadores_ocupados = 0.0
        self.acum_edades_completaron_entrevista = 0.0

        # Siguiente llegada
        rnd, ts = gen_exponencial(p["media_llegada_min"])
        self.prox_llegada = self.reloj + ts
        self.rnd_prox_llegada = rnd
        self.ts_prox_llegada = ts

        # Tabla de estado (vector)
        self.vector_estado: list[dict] = []
        self.tablas_rk_acumuladas: list[dict] = []  # {id_transeunte, edad, tabla}

        # Guardar fila inicial
        self._guardar_fila_inicio()

    # ── Fila inicial ──────────────────────────────────────────────────────────
    def _guardar_fila_inicio(self):
        fila = self._construir_fila("Inicio")
        self.vector_estado.append(fila)

    # ── Seleccionar contacto / entrevistador libre ────────────────────────────
    def _contacto_libre(self) -> Optional[Servidor]:
        for c in self.contactos:
            if c.libre:
                return c
        return None

    def _entrevistador_libre(self) -> Optional[Servidor]:
        for e in self.entrevistadores:
            if e.libre:
                return e
        return None

    # ── Evento: Llegada ───────────────────────────────────────────────────────
    def _evento_llegada(self):
        self.contador_transeuntes_totales += 1
        self.id_transeunte += 1
        tid = self.id_transeunte
        evento_nombre = f"Llegada_Transeunte_T{tid}"

        # Generar próxima llegada
        rnd_next, ts_next = gen_exponencial(self.p["media_llegada_min"])

        contacto = self._contacto_libre()

        rnd_edad = None
        edad = None
        t_info_u = None
        t_info_m = None
        hora_fin_info = None
        rnd_vuelve = None
        decide_vuelve = None
        tabla_rk = []

        if contacto is None:
            # Ambos contactos ocupados
            self.contador_abandonos_contactos_ocupados += 1
            rnd_vuelve, decide_vuelve = gen_decision(self.p["prob_vuelve_tarde"])
            if decide_vuelve:
                self.contador_volvieron_preguntar += 1
            # La persona se va; no genera transeunte activo
            evento_nombre = f"Llegada_Transeunte_T{tid}"
        else:
            # Hay contacto libre → se genera transeunte
            rnd_edad, edad = gen_uniforme(self.p["edad_min"], self.p["edad_max"])
            # RK
            t_info_u, t_info_m, tabla_rk = runge_kutta_tiempo_info(
                edad, self.p["rk_h"], self.p["segundos_por_unidad_t"]
            )
            hora_fin_info = self.reloj + t_info_m

            transeunte = Transeunte(
                id=tid,
                rnd_edad=rnd_edad,
                edad=edad,
                tiempo_inicio_info=self.reloj,
                tiempo_fin_info=hora_fin_info,
                t_info_unidades=t_info_u,
                t_info_minutos=t_info_m,
                tabla_rk=tabla_rk,
            )
            self.transeuntes_activos[tid] = transeunte

            # Ocupar contacto
            contacto.libre = False
            contacto.fin_atencion = hora_fin_info
            contacto.id_transeunte = tid
            contacto.tiempo_inicio = self.reloj

            # Guardar tabla RK
            self.tablas_rk_acumuladas.append({
                "id_transeunte": tid,
                "edad": edad,
                "rnd_edad": rnd_edad,
                "tabla": tabla_rk,
                "t_unidades": t_info_u,
                "t_segundos": round(t_info_u * self.p["segundos_por_unidad_t"], 4),
                "t_minutos": round(t_info_m, 4),
            })

        # Actualizar próxima llegada
        self.prox_llegada = self.reloj + ts_next
        self.rnd_prox_llegada = rnd_next
        self.ts_prox_llegada = ts_next

        fila = self._construir_fila(
            evento_nombre,
            rnd_edad, edad, t_info_u, hora_fin_info,
            rnd_vuelve=rnd_vuelve, decide_vuelve=decide_vuelve,
        )
        self.vector_estado.append(fila)

    # ── Evento: Fin de Información ────────────────────────────────────────────
    def _evento_fin_informacion(self, contacto: Servidor):
        tid = contacto.id_transeunte
        transeunte = self.transeuntes_activos.get(tid)

        # Acumular tiempo contacto ocupado
        self.acum_tiempo_contactos_ocupados += (self.reloj - contacto.tiempo_inicio)
        contacto.libre = True
        contacto.fin_atencion = None
        id_contacto = contacto.id

        rnd_acepta = None
        acepta = None
        rnd_ent = None
        ts_ent = None
        hora_fin_ent = None
        entrevistador_asignado = None

        if transeunte:
            self.contador_informados += 1
            rnd_acepta, acepta = gen_decision(self.p["prob_acepta_entrevista"])
            transeunte.rnd_acepta = rnd_acepta
            transeunte.acepta = acepta

            if acepta:
                self.contador_entrevistas_aceptadas += 1
                entrevistador = self._entrevistador_libre()
                if entrevistador:
                    rnd_ent, ts_ent = gen_exponencial(self.p["media_entrevista_min"])
                    hora_fin_ent = self.reloj + ts_ent

                    entrevistador.libre = False
                    entrevistador.fin_atencion = hora_fin_ent
                    entrevistador.id_transeunte = tid
                    entrevistador.tiempo_inicio = self.reloj
                    entrevistador_asignado = entrevistador.id

                    transeunte.estado = "Siendo Entrevistado"
                    transeunte.tiempo_inicio_entrevista = self.reloj
                    transeunte.tiempo_fin_entrevista = hora_fin_ent
                else:
                    # Todos los entrevistadores ocupados → persona se va
                    transeunte.estado = "Se Fue (puestos llenos)"
                    self.contador_informados_no_fueron_entrevista += 1
                    del self.transeuntes_activos[tid]
            else:
                transeunte.estado = "Rechazó entrevista"
                self.contador_informados_no_fueron_entrevista += 1
                del self.transeuntes_activos[tid]

        evento_nombre = f"Fin_informando_C{id_contacto}_T{tid}"
        fila = self._construir_fila(
            evento_nombre,
            rnd_ent=rnd_ent, ts_ent=ts_ent, hora_fin_ent=hora_fin_ent,
            rnd_acepta=rnd_acepta, acepta=acepta,
            entrevistador_asignado=entrevistador_asignado,
        )
        self.vector_estado.append(fila)

    # ── Evento: Fin de Entrevista ─────────────────────────────────────────────
    def _evento_fin_entrevista(self, entrevistador: Servidor):
        tid = entrevistador.id_transeunte
        transeunte = self.transeuntes_activos.get(tid)
        id_ent = entrevistador.id

        self.acum_tiempo_entrevistadores_ocupados += (self.reloj - entrevistador.tiempo_inicio)
        entrevistador.libre = True
        entrevistador.fin_atencion = None

        if transeunte:
            self.contador_entrevistas_finalizadas += 1
            self.acum_edades_completaron_entrevista += transeunte.edad
            transeunte.estado = "Entrevista Finalizada"
            del self.transeuntes_activos[tid]

        evento_nombre = f"Fin_entrevista_E{id_ent}_T{tid}"
        fila = self._construir_fila(evento_nombre)
        self.vector_estado.append(fila)

    # ── Evento: Fin de Jornada ────────────────────────────────────────────────
    def _evento_fin_jornada(self):
        self.jornada_terminada = True
        # Acumular contactos que siguen ocupados
        for c in self.contactos:
            if not c.libre:
                self.acum_tiempo_contactos_ocupados += (self.reloj - c.tiempo_inicio)
                c.libre = True
                c.fin_atencion = None
        # No se generan más llegadas; entrevistadores terminan los actuales

        fila = self._construir_fila("Fin_Jornada")
        self.vector_estado.append(fila)

    # ── Construir fila del vector de estado ───────────────────────────────────
    def _construir_fila(
        self, evento,
        rnd_edad=None, edad=None, t_info_u=None, hora_fin_info=None,
        rnd_vuelve=None, decide_vuelve=None,
        rnd_ent=None, ts_ent=None, hora_fin_ent=None,
        rnd_acepta=None, acepta=None,
        entrevistador_asignado=None,
    ) -> dict:
        # Próxima llegada
        prox_ll_hora = self.prox_llegada if not self.jornada_terminada else "∞"

        fila = {
            "N°": self.iter,
            "Evento": evento,
            "Reloj": round(self.reloj, 4),
            # Llegada
            "RND Llegada": self.rnd_prox_llegada,
            "TS Llegada": self.ts_prox_llegada,
            "Prox Llegada": prox_ll_hora,
            # Contactos - fin información
        }

        # Fin información contactos
        for c in self.contactos:
            if c.libre:
                fila[f"Fin Info C{c.id}"] = ""
            else:
                fila[f"Fin Info C{c.id}"] = round(c.fin_atencion, 4) if c.fin_atencion else ""

        # RK para esta fila
        fila["RND Edad"] = rnd_edad if rnd_edad is not None else ""
        fila["Edad"] = edad if edad is not None else ""
        fila["T Info (u)"] = round(t_info_u, 4) if t_info_u is not None else ""
        fila["T Info (s)"] = round(t_info_u * self.p["segundos_por_unidad_t"], 2) if t_info_u is not None else ""
        fila["T Info (min)"] = round(t_info_u * self.p["segundos_por_unidad_t"] / 60, 4) if t_info_u is not None else ""
        fila["Hora Fin Info"] = round(hora_fin_info, 4) if hora_fin_info is not None else ""

        # Decisión de volver (cuando contactos ocupados)
        fila["RND Vuelve"] = rnd_vuelve if rnd_vuelve is not None else ""
        fila["Vuelve Tarde"] = ("Sí" if decide_vuelve else "No") if decide_vuelve is not None else ""

        # Decisión entrevista
        fila["RND Acepta"] = rnd_acepta if rnd_acepta is not None else ""
        fila["Acepta Entrevista"] = ("SI" if acepta else "NO") if acepta is not None else ""

        # Fin entrevista generado
        fila["RND Entrevista"] = rnd_ent if rnd_ent is not None else ""
        fila["TS Entrevista"] = round(ts_ent, 4) if ts_ent is not None else ""
        fila["Hora Fin Entrevista"] = round(hora_fin_ent, 4) if hora_fin_ent is not None else ""
        fila["Entrevistador Asignado"] = entrevistador_asignado if entrevistador_asignado else ""

        # Estado contactos
        for c in self.contactos:
            fila[f"Estado C{c.id}"] = c.estado_str()

        # Estado entrevistadores + fin entrevistas
        for e in self.entrevistadores:
            fila[f"Estado E{e.id}"] = e.estado_str()
            fila[f"Fin Ent E{e.id}"] = round(e.fin_atencion, 4) if (not e.libre and e.fin_atencion) else ""

        # Contadores / acumuladores (métricas)
        fila["Cnt Entrevistas Finalizadas"] = self.contador_entrevistas_finalizadas
        fila["Cnt Entrevistas Aceptadas"] = self.contador_entrevistas_aceptadas
        fila["Cnt Abandonos Contactos Ocup"] = self.contador_abandonos_contactos_ocupados
        fila["Cnt Transeuntes Totales"] = self.contador_transeuntes_totales
        fila["Cnt Volvieron Preguntar"] = self.contador_volvieron_preguntar
        fila["Cnt Informados"] = self.contador_informados
        fila["Cnt Info No Fueron Entrevista"] = self.contador_informados_no_fueron_entrevista
        fila["Acum T Contactos Ocup"] = round(self.acum_tiempo_contactos_ocupados, 4)
        fila["Acum T Entrevistadores Ocup"] = round(self.acum_tiempo_entrevistadores_ocupados, 4)
        fila["Acum Edades Completaron Entrevista"] = round(self.acum_edades_completaron_entrevista, 2)

        # Objetos temporales (transeunte activos)
        for i in range(1, 4):  # mostramos hasta 3 transeuentes como columnas fijas
            key_id = f"Transeunte {i} ID"
            key_estado = f"Transeunte {i} Estado"
            key_edad = f"Transeunte {i} Edad"
            key_t_info = f"Transeunte {i} Inicio Info"
            key_t_ent = f"Transeunte {i} Inicio Ent"

            activos = list(self.transeuntes_activos.values())
            if i - 1 < len(activos):
                t = activos[i - 1]
                fila[key_id] = t.id
                fila[key_estado] = t.estado
                fila[key_edad] = t.edad
                fila[key_t_info] = round(t.tiempo_inicio_info, 4) if t.tiempo_inicio_info is not None else ""
                fila[key_t_ent] = round(t.tiempo_inicio_entrevista, 4) if t.tiempo_inicio_entrevista is not None else ""
            else:
                fila[key_id] = ""
                fila[key_estado] = ""
                fila[key_edad] = ""
                fila[key_t_info] = ""
                fila[key_t_ent] = ""

        return fila

    # ── Bucle principal ───────────────────────────────────────────────────────
    def run(self):
        p = self.p
        self.reset()

        while self.iter < p["max_iter"]:
            # Determinar próximo evento
            eventos_posibles = []

            if not self.jornada_terminada:
                eventos_posibles.append(("llegada", self.prox_llegada))
                eventos_posibles.append(("fin_jornada", self.fin_jornada))

            for c in self.contactos:
                if not c.libre and c.fin_atencion is not None:
                    eventos_posibles.append((f"fin_info_{c.id}", c.fin_atencion, c))

            for e in self.entrevistadores:
                if not e.libre and e.fin_atencion is not None:
                    eventos_posibles.append((f"fin_ent_{e.id}", e.fin_atencion, e))

            if not eventos_posibles:
                break

            # Ordenar por tiempo
            eventos_posibles.sort(key=lambda x: x[1])
            prox = eventos_posibles[0]
            nuevo_reloj = prox[1]

            # Si llegamos al fin de jornada
            if prox[0] == "fin_jornada":
                self.reloj = nuevo_reloj
                self.iter += 1
                self._evento_fin_jornada()
                # Seguir hasta que todos los entrevistadores terminen
                continue

            # Si la jornada terminó, sólo procesamos entrevistas pendientes
            if self.jornada_terminada:
                if prox[0].startswith("fin_ent"):
                    self.reloj = nuevo_reloj
                    self.iter += 1
                    self._evento_fin_entrevista(prox[2])
                    continue
                else:
                    break

            self.reloj = nuevo_reloj
            self.iter += 1

            if prox[0] == "llegada":
                self._evento_llegada()
            elif prox[0].startswith("fin_info"):
                self._evento_fin_informacion(prox[2])
            elif prox[0].startswith("fin_ent"):
                self._evento_fin_entrevista(prox[2])

            if self.reloj >= self.fin_jornada and not self.jornada_terminada:
                self.reloj = self.fin_jornada
                self._evento_fin_jornada()

        return self.vector_estado

    # ── Métricas finales ──────────────────────────────────────────────────────
    def calcular_metricas(self) -> dict:
        p = self.p
        reloj_final = self.reloj
        T = reloj_final * p["n_contactos"] if reloj_final > 0 else 1
        T_ent = reloj_final * p["n_entrevistadores"] if reloj_final > 0 else 1

        # Acumular tiempo de entrevistadores que aún están ocupados al finalizar
        for e in self.entrevistadores:
            if not e.libre and e.tiempo_inicio is not None:
                self.acum_tiempo_entrevistadores_ocupados += (reloj_final - e.tiempo_inicio)

        m = {}

        # 1. % ocupación contactos
        m["1. % Ocupación Promedio Contactos"] = (
            round(self.acum_tiempo_contactos_ocupados / T * 100, 2) if T > 0 else 0
        )

        # 2. % ocupación entrevistadores
        m["2. % Ocupación Promedio Entrevistadores"] = (
            round(self.acum_tiempo_entrevistadores_ocupados / T_ent * 100, 2) if T_ent > 0 else 0
        )

        # 3. % personas que aceptaron entrevista (de las informadas)
        m["3. % Personas que Aceptaron Entrevista"] = (
            round(self.contador_entrevistas_aceptadas / self.contador_informados * 100, 2)
            if self.contador_informados > 0 else 0
        )

        # 4. % rechazo por contactos ocupados (sobre el total de transeúntes)
        m["4. % Rechazo por Contactos Ocupados"] = (
            round(self.contador_abandonos_contactos_ocupados / self.contador_transeuntes_totales * 100, 2)
            if self.contador_transeuntes_totales > 0 else 0
        )

        # 5. Cantidad de personas que volvieron a preguntar
        m["5. Cant. Personas que Volvieron a Preguntar"] = self.contador_volvieron_preguntar

        # 6. % personas informadas que no fueron a entrevista
        m["6. % Informados que No Fueron a Entrevista"] = (
            round(self.contador_informados_no_fueron_entrevista / self.contador_informados * 100, 2)
            if self.contador_informados > 0 else 0
        )

        # 7. Edad promedio de personas que completaron entrevista
        m["7. Edad Promedio de Entrevistados Completos"] = (
            round(self.acum_edades_completaron_entrevista / self.contador_entrevistas_finalizadas, 2)
            if self.contador_entrevistas_finalizadas > 0 else 0
        )

        # 8. Tasa de conversión global (entrevistas finalizadas / transeúntes totales)
        m["8. Tasa de Conversión Global (%)"] = (
            round(self.contador_entrevistas_finalizadas / self.contador_transeuntes_totales * 100, 2)
            if self.contador_transeuntes_totales > 0 else 0
        )

        # Info adicional
        m["── Totales ──"] = ""
        m["Total Transeúntes"] = self.contador_transeuntes_totales
        m["Total Informados"] = self.contador_informados
        m["Total Entrevistas Aceptadas"] = self.contador_entrevistas_aceptadas
        m["Total Entrevistas Finalizadas"] = self.contador_entrevistas_finalizadas
        m["Total Abandonos Contactos Ocupados"] = self.contador_abandonos_contactos_ocupados
        m["Total Volvieron Preguntar"] = self.contador_volvieron_preguntar
        m["Total Informados No Entrevistados"] = self.contador_informados_no_fueron_entrevista
        m["Reloj Final (min)"] = round(reloj_final, 4)
        m["Iteraciones"] = self.iter

        return m


# ─────────────────────────────────────────────────────────────────────────────
# 6.  INTERFAZ STREAMLIT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Simulación PLAZA - UTN FRC",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("🏛️ Simulación: PLAZA San Martín — UTN FRC 4K1 2026")
    st.markdown("**TP5 · Simulación por Eventos Discretos + Runge-Kutta**")

    # ── Sidebar: Parámetros ──────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Parámetros")

        st.subheader("Sistema")
        media_llegada_personas_hora = st.number_input("Media llegada (personas/hora)", value=90.0, min_value=1.0)
        media_llegada_min = 60.0 / media_llegada_personas_hora

        media_entrevista = st.number_input("Media duración entrevista (min)", value=3.0, min_value=0.1)
        prob_acepta = st.slider("P(acepta entrevista)", 0.0, 1.0, 0.85, 0.01)
        prob_vuelve = st.slider("P(vuelve tarde si contactos ocupados)", 0.0, 1.0, 0.25, 0.01)

        st.subheader("Edades")
        edad_min = st.number_input("Edad mínima", value=20, min_value=0)
        edad_max = st.number_input("Edad máxima", value=85, min_value=1)

        st.subheader("Servidores")
        n_contactos = st.number_input("N° de contactos", value=2, min_value=1, max_value=10)
        n_entrevistadores = st.number_input("N° de entrevistadores", value=4, min_value=1, max_value=20)

        st.subheader("Horario")
        hora_inicio = st.number_input("Hora de inicio (0=10AM)", value=0.0, min_value=0.0)
        duracion_horas = st.number_input("Duración jornada (horas)", value=6.0, min_value=0.1)

        st.subheader("Runge-Kutta")
        rk_h = st.number_input("Paso h (RK)", value=0.1, min_value=0.001, format="%.3f")
        seg_por_unidad = st.number_input("Segundos por unidad t", value=8, min_value=1)

        st.subheader("Simulación")
        max_iter = st.number_input("Máx. iteraciones", value=100_000, min_value=1, max_value=100_000)
        semilla = st.number_input("Semilla aleatoria (0=aleatoria)", value=0, min_value=0)

        st.subheader("Visualización del Vector")
        iter_j = st.number_input("Mostrar desde iteración j", value=1, min_value=0)
        iter_i = st.number_input("Mostrar i iteraciones", value=50, min_value=1, max_value=100000)

        ejecutar = st.button("▶️ Ejecutar Simulación", type="primary", use_container_width=True)

    # ── Ejecución ────────────────────────────────────────────────────────────
    if ejecutar:
        if semilla > 0:
            random.seed(semilla)

        params = {
            "media_llegada_min": media_llegada_min,
            "media_entrevista_min": media_entrevista,
            "prob_acepta_entrevista": prob_acepta,
            "prob_vuelve_tarde": prob_vuelve,
            "edad_min": edad_min,
            "edad_max": edad_max,
            "n_contactos": int(n_contactos),
            "n_entrevistadores": int(n_entrevistadores),
            "tiempo_inicio_min": hora_inicio,
            "duracion_jornada_min": duracion_horas * 60,
            "rk_h": rk_h,
            "segundos_por_unidad_t": int(seg_por_unidad),
            "max_iter": int(max_iter),
            "iter_desde_j": int(iter_j),
            "iter_mostrar_i": int(iter_i),
        }

        sim = SimulacionPlaza(params)

        with st.spinner("Simulando..."):
            vector = sim.run()
            metricas = sim.calcular_metricas()

        st.success(f"✅ Simulación completada — {sim.iter} iteraciones / Reloj final: {round(sim.reloj, 2)} min")

        # ── Tabs ─────────────────────────────────────────────────────────────
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Vector de Estado",
            "📈 Métricas",
            "🔢 Tablas Runge-Kutta",
            "📋 Última Fila",
        ])

        # ── Tab 1: Vector de Estado ──────────────────────────────────────────
        with tab1:
            st.subheader("Vector de Estado")

            j = int(iter_j)
            i = int(iter_i)

            # Rango [j, j+i)
            filas_rango = [f for f in vector if isinstance(f.get("N°"), int) and j <= f["N°"] < j + i]

            if filas_rango:
                df = pd.DataFrame(filas_rango)
                st.markdown(f"**Mostrando iteraciones {j} a {j + i - 1}** ({len(filas_rango)} filas)")
                st.dataframe(df, use_container_width=True, height=500)
            else:
                st.info(f"No hay iteraciones en el rango [{j}, {j+i}). "
                        f"La simulación generó {sim.iter} iteraciones.")

            # Fila de inicio separada
            fila_inicio = [f for f in vector if f.get("Evento") == "Inicio"]
            if fila_inicio and j <= 0:
                st.markdown("**Fila de Inicio (iteración 0):**")
                st.dataframe(pd.DataFrame(fila_inicio), use_container_width=True)

        # ── Tab 2: Métricas ──────────────────────────────────────────────────
        with tab2:
            st.subheader("📈 Métricas de la Simulación")

            metricas_principales = {k: v for k, v in metricas.items() if not k.startswith("──")}

            col1, col2 = st.columns(2)
            items = [(k, v) for k, v in metricas_principales.items()]
            mid = len(items) // 2

            for k, v in items[:mid]:
                if isinstance(v, float):
                    col1.metric(k, f"{v}%")
                else:
                    col1.metric(k, v)

            for k, v in items[mid:]:
                if isinstance(v, float) and "%" in k:
                    col2.metric(k, f"{v}%")
                else:
                    col2.metric(k, v)

            st.divider()
            st.subheader("Tabla de métricas completa")
            df_met = pd.DataFrame(list(metricas.items()), columns=["Métrica", "Valor"])
            st.dataframe(df_met, use_container_width=True)

        # ── Tab 3: Tablas Runge-Kutta ────────────────────────────────────────
        with tab3:
            st.subheader("Tablas de Runge-Kutta calculadas")
            tablas = sim.tablas_rk_acumuladas

            if not tablas:
                st.info("No se calcularon tablas RK en esta simulación.")
            else:
                st.markdown(f"**Total de tablas calculadas:** {len(tablas)}")

                opciones = [
                    f"T{t['id_transeunte']} — Edad: {t['edad']} — RND: {t['rnd_edad']} — "
                    f"t={t['t_unidades']} u / {t['t_segundos']} seg / {t['t_minutos']} min"
                    for t in tablas
                ]

                seleccion = st.selectbox("Seleccionar tabla:", opciones)
                idx = opciones.index(seleccion)
                tabla_sel = tablas[idx]

                st.markdown(
                    f"**Transeunte T{tabla_sel['id_transeunte']}** · "
                    f"Edad = `{tabla_sel['edad']}` años · "
                    f"RND Edad = `{tabla_sel['rnd_edad']}` · "
                    f"Tiempo informando = `{tabla_sel['t_unidades']}` unidades = "
                    f"`{tabla_sel['t_segundos']}` seg = `{tabla_sel['t_minutos']}` min"
                )

                df_rk = pd.DataFrame(tabla_sel["tabla"])
                st.dataframe(df_rk, use_container_width=True, height=400)

                st.caption(
                    "**dE/dt = (t² − E) · h²** · "
                    f"E(0) = {tabla_sel['edad']} (edad del transeunte) · "
                    f"h = {rk_h} · "
                    "Se integra hasta que dE/dt > 0 (velocidad de crecimiento positiva)"
                )

                # Mostrar resumen de todas las tablas
                st.divider()
                st.subheader("Resumen de todas las tablas RK")
                resumen = [
                    {
                        "Transeunte": f"T{t['id_transeunte']}",
                        "RND Edad": t["rnd_edad"],
                        "Edad (años)": t["edad"],
                        "t final (unidades)": t["t_unidades"],
                        "t final (segundos)": t["t_segundos"],
                        "t final (minutos)": t["t_minutos"],
                        "Pasos RK": len(t["tabla"]),
                    }
                    for t in tablas
                ]
                st.dataframe(pd.DataFrame(resumen), use_container_width=True)

        # ── Tab 4: Última Fila ───────────────────────────────────────────────
        with tab4:
            st.subheader("Última fila del vector de estado (instante final X)")
            st.caption("Sin objetos temporales, sólo estado del sistema y métricas.")

            ultima_fila = vector[-1] if vector else {}

            # Filtrar campos de objetos temporales
            campos_excluir = [k for k in ultima_fila if k.startswith("Transeunte")]
            fila_filtrada = {k: v for k, v in ultima_fila.items() if k not in campos_excluir}

            df_ultima = pd.DataFrame([fila_filtrada]).T.reset_index()
            df_ultima.columns = ["Campo", "Valor"]
            st.dataframe(df_ultima, use_container_width=True, height=600)

    else:
        st.info("👈 Configurá los parámetros en el panel lateral y presioná **Ejecutar Simulación**.")

        with st.expander("ℹ️ Descripción del sistema"):
            st.markdown("""
### Sistema "PLAZA"
- **4 entrevistadores** en la Plaza San Martín de Córdoba.
- **2 contactos** que informan a los transeúntes.
- Llegada de transeúntes: **Exponencial(90 personas/hora)**.
- Si los 2 contactos están ocupados: el **25%** vuelve más tarde, el **75%** se va definitivamente.
- Tiempo de información: calculado con **Runge-Kutta (dE/dt = (t²−E)·h²)**, E(0)=Edad~Uniforme[20,85].
  - Se integra hasta que dE/dt > 0. Ese `t` (en unidades, 1 unidad = 8 seg) es el tiempo de información.
- El **85%** acepta la entrevista. Si todos los puestos están ocupados → la persona se va.
- Duración entrevista: **Exponencial(media=3 min)**.
- Horario: **10:00 AM a 16:00 PM** (360 minutos por jornada).

### 8 Métricas calculadas
1. **% Ocupación promedio Contactos**
2. **% Ocupación promedio Entrevistadores**
3. **% Personas que aceptaron entrevista** (de las informadas)
4. **% Rechazo por contactos ocupados** (sobre total de transeúntes)
5. **Cantidad de personas que volvieron a preguntar**
6. **% Informados que no fueron a entrevista**
7. **Edad promedio de entrevistados que completaron** la entrevista
8. **Tasa de conversión global** (entrevistas finalizadas / transeúntes totales)
            """)


if __name__ == "__main__":
    main()
