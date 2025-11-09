import traci
import sys
import time
import os
from supabase import create_client 

TLS_ID = "J2"
DETECTOR_IDS = ["det_J2_entrada_0", "det_J2_entrada_1"]
TRACI_PORT = 8813

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") 
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def log_event_db(level: str, module: str, message: str, user_email: str = "SYSTEM/TRAFFIC_CONTROL"):
    try:
        supabase.table('application_logs').insert([
            {'nivel': level, 'modulo': module, 'mensagem': message, 'user_email': user_email}
        ]).execute()
    except Exception:
        pass

def setup_simulation():
    try:
        traci.init(TRACI_PORT)
        log_event_db("INFO", "SIM_TRAFFIC_CONTROL", f"Controlador TraCI conectado na porta {TRACI_PORT}.")
    except Exception:
        pass

def run_dynamic_control():
    try:
        current_phase = traci.trafficlight.getPhase(TLS_ID)
        traci.trafficlight.setPhaseDuration(TLS_ID, 40)
        log_event_db("INFO", "SIM_TRAFFIC_CONTROL", f"Lógica IOT aplicada. Fase {current_phase} forçada para 40s.")
    except Exception as e:
        log_event_db("ERROR", "SIM_TRAFFIC_CONTROL", f"Falha ao aplicar lógica IOT no semáforo: {e}")


if __name__ == "__main__":
    setup_simulation()
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "STATIC"

    if mode == "DYNAMIC":
        log_event_db("WARNING", "SIM_TRAFFIC_CONTROL", "Modo Dinâmico IOT ATIVADO. TraCI está controlando o semáforo J2.")
        run_dynamic_control()
    else:
        log_event_db("WARNING", "SIM_TRAFFIC_CONTROL", "Modo Estático ATIVADO. Semáforo J2 em tempo fixo.")

    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        traci.close()