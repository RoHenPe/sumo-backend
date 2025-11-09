import os
import subprocess
import random
import sys
import traci
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
from supabase import create_client, Client

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare/export 'SUMO_HOME'")

app = FastAPI()
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

GRID_X = 3
GRID_Y = 3
VEHICLE_COUNT = 300
SIMULATION_DURATION = 3600
OUTPUT_DIR = "sim_scenarios"
SCENARIO_PATH = os.path.join(OUTPUT_DIR, "unified_grid")
NET_FILE = os.path.join(SCENARIO_PATH, "grid.net.xml")
ROU_FILE = os.path.join(SCENARIO_PATH, "grid.rou.xml")
CFG_FILE = os.path.join(SCENARIO_PATH, "unified.sumocfg")
PORT = 8813

def create_scenario_files():
    os.makedirs(SCENARIO_PATH, exist_ok=True)
    
    subprocess.run(
        ["netgenerate", 
         "--grid", f"{GRID_X},{GRID_Y}", 
         "--grid.length=200",
         "--tls.guess", 
         "-o", NET_FILE],
        check=True
    )
    
    with open(ROU_FILE, "w") as f:
        f.write('<routes>\n')
        f.write('<vType id="car" accel="2.0" decel="4.5" sigma="0.5" length="5" maxSpeed="30" color="1,1,0"/>\n')
        f.write('<vType id="policia" vClass="police" accel="3.5" decel="6.0" sigma="0.8" length="5" maxSpeed="50" color="0,0,1"/>\n')
        f.write('<vType id="ambulancia" vClass="ambulance" accel="3.0" decel="5.0" sigma="0.8" length="6" maxSpeed="40" color="1,1,1"/>\n')
        
        for i in range(VEHICLE_COUNT):
            v_type = random.choice(["car", "car", "car", "car", "policia", "ambulancia"])
            f.write(f'<trip id="veh{i}" type="{v_type}" depart="{random.randint(0, 500)}" from="E0" to="E{GRID_X * GRID_Y}" />\n')

        f.write('</routes>')

    with open(CFG_FILE, "w") as f:
        f.write('<configuration>\n')
        f.write('  <input>\n')
        f.write(f'    <net-file value="{os.path.basename(NET_FILE)}"/>\n')
        f.write(f'    <route-files value="{os.path.basename(ROU_FILE)}"/>\n')
        f.write('  </input>\n')
        f.write('  <time>\n')
        f.write(f'    <begin value="0"/>\n')
        f.write(f'    <end value="{SIMULATION_DURATION}"/>\n')
        f.write('  </time>\n')
        f.write(f'  <remote-port value="{PORT}"/>\n')
        f.write('</configuration>')
    
    return True

async def run_simulation():
    sumo_binary = "sumo"
    sumo_cmd = [sumo_binary, "-c", CFG_FILE]
    
    try:
        create_scenario_files()
    except Exception as e:
        print(f"Erro ao criar arquivos: {e}")
        return

    traci_started = False
    try:
        sumo_proc = subprocess.Popen(sumo_cmd)
        
        traci.init(PORT)
        traci_started = True
        print("TraCI Conectado. Rodando simulação...")

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            vehicle_ids = traci.vehicle.getIDList()
            vehicles_data = []

            for vid in vehicle_ids:
                try:
                    pos = traci.vehicle.getPosition(vid)
                    angle = traci.vehicle.getAngle(vid)
                    v_type = traci.vehicle.getTypeID(vid)
                    
                    vehicles_data.append({
                        "id": vid,
                        "x": pos[0],
                        "y": pos[1], 
                        "angle": angle,
                        "type": v_type 
                    })
                except traci.TraCIException:
                    pass 
            
            await sio.emit('simulation_update', {"vehicles": vehicles_data})
            await sio.sleep(0.05)

    except Exception as e:
        print(f"Erro na simulação: {e}")
    finally:
        if traci_started:
            traci.close()
        sumo_proc.terminate()
        print("Simulação finalizada.")
        await sio.emit('simulation_end')

@sio.on('connect')
async def handle_connect(sid, environ):
    print(f"Cliente conectado: {sid}")
    await sio.start_background_task(run_simulation)

@sio.on('disconnect')
def handle_disconnect(sid):
    print(f"Cliente desconectado: {sid}")

@app.get("/")
def read_root():
    return {"status": "API de processamento SUMO está online"}