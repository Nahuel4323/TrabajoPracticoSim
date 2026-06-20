"""
Núcleo de simulación por eventos discretos del sistema PLAZA.
"""

from typing import Optional

from .modelos import Servidor, Transeunte
from .variables_aleatorias import gen_exponencial, gen_uniforme, gen_decision
from .runge_kutta import runge_kutta_tiempo_info


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
        self.contador_rechazo_entrevista = 0          # informados que dijeron "NO"
        self.contador_se_fue_puestos_llenos = 0        # aceptó pero no había entrevistador libre
        self.acum_tiempo_contactos_ocupados = 0.0
        self.acum_tiempo_entrevistadores_ocupados = 0.0
        self.acum_edades_completaron_entrevista = 0.0
        self.edades_entrevista_completada: list[float] = []  # para histograma

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
                    self.contador_se_fue_puestos_llenos += 1
                    del self.transeuntes_activos[tid]
            else:
                transeunte.estado = "Rechazó entrevista"
                self.contador_informados_no_fueron_entrevista += 1
                self.contador_rechazo_entrevista += 1
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
            self.edades_entrevista_completada.append(transeunte.edad)
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
        # Próxima llegada: se muestra siempre el valor calculado, incluso si la
        # jornada ya terminó (es el mismo valor que se calculó para el próximo
        # transeúnte en el momento en que finalizó la jornada).
        prox_ll_hora = round(self.prox_llegada, 4)

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

        # 8. % de personas efectivamente entrevistadas sobre el total que pasó por la plaza
        m["8. % de Personas Entrevistadas sobre el Total que Pasó por la Plaza"] = (
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
        m["Total Rechazaron la Entrevista"] = self.contador_rechazo_entrevista
        m["Total Se Fueron (Entrevistadores Llenos)"] = self.contador_se_fue_puestos_llenos
        m["Reloj Final (min)"] = round(reloj_final, 4)
        m["Iteraciones"] = self.iter

        return m
