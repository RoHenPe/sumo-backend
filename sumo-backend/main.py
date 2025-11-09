import os
import subprocess
import random
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET_NAME = "osm-grids" 

class BoundingBox(BaseModel):
    west: float
    south: float
    east: float
    north: float

GRID_X = 3
GRID_Y = 3
VEHICLE_COUNT = 300
SIMULATION_DURATION = 3600
OUTPUT_DIR = "sim_scenarios"

def log_event_db(level: str, module: str, message: str, user_email: str = "API/SUMO_BACKEND"):
    try:
        supabase.table('application_logs').insert([
            {'nivel': level, 'modulo': module, 'mensagem': message, 'user_email': user_email}
        ]).execute()
    except Exception:
        pass
        
def create_unified_scenario_files(output_folder):
    scenario_path = os.path.join(output_folder, "unified_grid")
    os.makedirs(scenario_path, exist_ok=True)
    
    net_file = os.path.join(scenario_path, "grid.net.xml")
    rou_file = os.path.join(scenario_path, "grid.rou.xml")
    add_file = os.path.join(scenario_path, "grid.add.xml")
    
    subprocess.run(
        ["netgenerate", 
         "--grid", f"{GRID_X},{GRID_Y}", 
         "--tls.guess", 
         "-o", net_file],
        check=True
    )
    
    with open(rou_file, "w") as f:
        f.write('<routes>\n')
        f.write('<vType id="car" accel="2.0" decel="4.5" sigma="0.5" length="5" maxSpeed="70" color="1,1,0"/>\n')
        f.write('<vType id="priority_car" accel="3.5" decel="6.0" sigma="0.8" length="5" maxSpeed="100" color="1,0,0"/>\n')
        
        for i in range(VEHICLE_COUNT):
            f.write(f'<trip id="veh{i}" type="car" depart="{random.randint(0, SIMULATION_DURATION)}" from="E0" to="E{GRID_X * GRID_Y}" />\n')

        f.write('</routes>')
    
    with open(add_file, "w") as f:
        f.write('<additional>\n')
        
        tls_id = "J2" 
        
        f.write(f'<e1Detector id="det_{tls_id}_entrada_0" lane="E1_0" pos="-5" freq="1" file="detectors.xml"/>\n')
        f.write(f'<e1Detector id="det_{tls_id}_entrada_1" lane="E1_1" pos="-5" freq="1" file="detectors.xml"/>\n')
        
        f.write('</additional>')

    return scenario_path, "grid.net.xml", "grid.rou.xml", "grid.add.xml"

@app.post("/api/generate-grid")
async def generate_grid(bbox: BoundingBox):
    user_email = "API/SUMO_BACKEND"
    
    try:
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            
        log_event_db("INFO", "SUMO_API_GRID", "Iniciando geração de grid 3x3 e arquivos de rota.", user_email)
            
        scenario_path, net_name, rou_name, add_name = create_unified_scenario_files(OUTPUT_DIR)
        
        cfg_file = os.path.join(scenario_path, "unified.sumocfg")
        with open(cfg_file, "w") as f:
            f.write('<configuration>\n')
            f.write('  <input>\n')
            f.write(f'    <net-file value="{net_name}"/>\n')
            f.write(f'    <route-files value="{rou_name}"/>\n')
            f.write(f'    <additional-files value="{add_name}"/>\n')
            f.write('  </input>\n')
            f.write('  <time>\n')
            f.write(f'    <begin value="0"/>\n')
            f.write(f'    <end value="{SIMULATION_DURATION}"/>\n')
            f.write('  </time>\n')
            f.write('</configuration>')
            
        log_event_db("INFO", "SUMO_API_GRID", f"Grid gerado. Iniciando upload do {os.path.basename(cfg_file)}.", user_email)

        file_path_in_bucket = f"sim_scenarios/unified_grid.sumocfg"
        
        with open(cfg_file, 'rb') as f:
            supabase.storage.from_(BUCKET_NAME).upload(
                path=file_path_in_bucket,
                file=f,
                file_options={"content-type": "application/xml", "upsert": "true"}
            )
            
        log_event_db("SUCCESS", "SUMO_API_GRID", f"Cenário salvo com sucesso no Storage.", user_email)

        return {
            "status": "sucesso", 
            "message": f"Grid unificado salvo em {BUCKET_NAME}/{file_path_in_bucket}. Pronto para simulação."
        }

    except subprocess.CalledProcessError as e:
        error_msg = f"Falha no comando Netgenerate/SUMO: {e.stderr}"
        log_event_db("ERROR", "SUMO_API_GRID", error_msg, user_email)
        return {"status": "erro", "message": f"Falha no comando SUMO/Netgenerate. Detalhes: {e.stderr}"}
    except Exception as e:
        error_msg = f"Erro interno ao salvar cenário: {str(e)}"
        log_event_db("CRITICAL", "SUMO_API_GRID", error_msg, user_email)
        return {"status": "erro", "message": f"Erro interno ao salvar cenário: {str(e)}"}

@app.get("/")
def read_root():
    return {"status": "API de processamento SUMO está online"}