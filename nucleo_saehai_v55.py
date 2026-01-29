

















import hashlib
import json
import math
import time
import threading
import mmap
from datetime import datetime
from typing import Dict, Final, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import IntEnum

# =============================================================================
# NÚCLEO SAEHAI RTOS v5.5 - PROTOCOLO DE HERENCIA DE PRIORIDAD
# =============================================================================

class NucleoAVLI:
    VERSION: Final = "5.5.0_ANNIVERSARY_55"
    PHI_SYNC: Final = 0.13
    LIMITE_TORSION: Final = (0.30, 0.85)
    UMBRAL_VIBRACION_MAX: Final = 0.25

class TaskControlBlock:
    def __init__(self, pid, priority, entry_point, args=()):
        self.pid = pid
        self.priority = priority
        self.base_priority = priority # Para restaurar tras herencia
        self.state = "READY"
        self.entry_point = entry_point
        self.args = args
        self.holding_semaphores = []

class InterProcessCommunication:
    """IPC con Protocolo de Herencia de Prioridad"""
    def __init__(self, scheduler):
        self.semaphores: Dict[str, Dict] = {}
        self.scheduler = scheduler

    def create_semaphore(self, name: str, initial: int = 1):
        self.semaphores[name] = {
            "value": initial,
            "owner_pid": None,
            "waiting_pids": []
        }

    def semaphore_wait(self, name: str, pid: int):
        sem = self.semaphores[name]
        current_task = self.scheduler.tasks[pid]
        
        if sem["value"] > 0:
            sem["value"] -= 1
            sem["owner_pid"] = pid
            current_task.holding_semaphores.append(name)
        else:
            # --- HERENCIA DE PRIORIDAD ---
            owner_pid = sem["owner_pid"]
            if owner_pid:
                owner_task = self.scheduler.tasks[owner_pid]
                if owner_task.priority < current_task.priority:
                    # El dueño humilde hereda la nobleza del que espera
                    owner_task.priority = current_task.priority
                    print(f"[KERNEL] Herencia: PID {owner_pid} sube a Prioridad {owner_task.priority}")
            
            sem["waiting_pids"].append(pid)
            current_task.state = "WAITING"

    def semaphore_signal(self, name: str, pid: int):
        sem = self.semaphores[name]
        current_task = self.scheduler.tasks[pid]
        
        sem["value"] += 1
        current_task.holding_semaphores.remove(name)
        # Restaurar prioridad base tras soltar el recurso
        current_task.priority = current_task.base_priority
        
        if sem["waiting_pids"]:
            next_pid = sem["waiting_pids"].pop(0)
            self.scheduler.tasks[next_pid].state = "READY"
            sem["value"] -= 1
            sem["owner_pid"] = next_pid

class TaskScheduler:
    def __init__(self):
        self.tasks: Dict[int, TaskControlBlock] = {}
        self.ready_queue: List[int] = []
        self.next_pid = 1

    def create_task(self, entry, priority, args=()):
        pid = self.next_pid
        self.next_pid += 1
        task = TaskControlBlock(pid, priority, entry, args)
        self.tasks[pid] = task
        self.ready_queue.append(pid)
        return pid

    def schedule(self):
        # Filtra solo las READY y ordena por prioridad actual (incluyendo herencia)
        ready_tasks = [pid for pid in self.ready_queue if self.tasks[pid].state == "READY"]
        if not ready_tasks: return None
        
        best_pid = max(ready_tasks, key=lambda p: self.tasks[p].priority)
        return best_pid

class SaehaiRTOS:
    def __init__(self):
        print(f"--- INICIANDO SAEHAI RTOS v{NucleoAVLI.VERSION} ---")
        self.scheduler = TaskScheduler()
        self.ipc = InterProcessCommunication(self.scheduler)
        self.caja_negra = []

    def registrar(self, msg):
        ts = datetime.now().isoformat()
        self.caja_negra.append(f"{ts}|{msg}")

    def loop_sistema(self):
        # Simulación de ciclos de ejecución
        for _ in range(5):
            pid = self.scheduler.schedule()
            if pid:
                task = self.scheduler.tasks[pid]
                print(f"[RUNNING] PID {pid} (Prio: {task.priority})")
                task.entry_point(*task.args)
            time.sleep(0.1)

# =============================================================================
# APLICACIÓN DE ENERGÍA (CASO DE USO)
# =============================================================================

if __name__ == "__main__":
    os = SaehaiRTOS()
    os.ipc.create_semaphore("EJE_TORSION")

    # 1. Proceso humilde toma el recurso
    def tarea_baja(): print("Baja: Usando el Eje...")
    pid_low = os.scheduler.create_task(tarea_baja, priority=10)
    os.ipc.semaphore_wait("EJE_TORSION", pid_low)

    # 2. Proceso crítico intenta entrar
    def tarea_alta(): print("Alta: ¡NECESITO EL EJE!")
    pid_high = os.scheduler.create_task(tarea_alta, priority=99)
    os.ipc.semaphore_wait("EJE_TORSION", pid_high) # Aquí ocurre la magia de la v5.5

    os.loop_sistema()
    print(f"\n✅ RTOS v5.5 estable. Caja negra sellada. ¡Felices 55, Profe!")

