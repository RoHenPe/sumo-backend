import sys
import traci
from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare/export 'SUMO_HOME'")

sumo_binary = "sumo"
sumo_config_file = "sumo-data/3x3.sumocfg" 
sumo_cmd = [sumo_binary, "-c", sumo_config_file, "--remote-port", "8813"]

@app.route('/')
def status():
    return jsonify({"status": "API de processamento SUMO está online"})

def run_simulation():
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
            
        update_data = {
            "vehicles": vehicles_data,
        }
        
        socketio.emit('simulation_update', update_data)
        socketio.sleep(0.05) 

    traci.close()
    print("Simulação finalizada.")
    socketio.emit('simulation_end')

@socketio.on('connect')
def handle_connect():
    print("Cliente conectado. Iniciando simulação...")
    try:
        traci.start(sumo_cmd)
        run_simulation()
    except Exception as e:
        print(f"Erro ao iniciar o SUMO: {e}", file=sys.stderr)
    finally:
        if 'traci' in locals() and traci.isLoaded():
            traci.close()

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)