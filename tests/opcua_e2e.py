import asyncio, os, sys, threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from asyncua import Server, ua
from server import Application, make_server

async def main():
    token = 'synthetic-test-token-12345'
    app = Application(token=token)
    app.mode = 'online'
    app.online_enabled = True
    http = make_server(0, app=app)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    server = Server()
    print("initializing OPC UA server", flush=True)
    await server.init()
    print("OPC UA server initialized", flush=True)
    server.set_endpoint('opc.tcp://127.0.0.1:48591/example/')
    index = await server.register_namespace('urn:synthetic:manuchain')
    variables = [await server.nodes.objects.add_variable(ua.NodeId(f'example{i}', index), f'Example{i}', float(i)) for i in range(1, 16)]
    source = (await variables[0].read_data_value()).SourceTimestamp.timestamp()
    classpath = os.environ['MANUCHAIN_MILO_CLASSPATH']
    async with server:
        process = await asyncio.create_subprocess_exec('java', '-cp', classpath, 'demo.MiloCollector', 'opc.tcp://127.0.0.1:48591/example/', str(http.server_port), 'SYNTHETIC', '1000', *[f'sensor_{i:02}=ns={index};s=example{i}' for i in range(1, 16)], env={**os.environ, 'MANUCHAIN_BRIDGE_TOKEN':token}, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            for _ in range(80):
                await asyncio.sleep(.25)
                if process.returncode is not None: break
                if app.predictions: break
            row = app.assembler.devices.get('SYNTHETIC', {}).get('sensor_01')
            if row is None or not app.predictions:
                if process.returncode is None: process.terminate()
                _, err = await process.communicate()
                raise RuntimeError('no event received: '+err.decode())
            assert row[0] == 1.0, row
            assert app.predictions[0]['record_id'] == 'SYNTHETIC', app.predictions
            print('prediction:', app.predictions[0], flush=True)
            assert abs(row[1] - source) < 0.002, (row, source)
            print('PASS local OPC UA simulator -> real Milo collector -> Python event assembler; 15 signals predicted; source timestamp preserved')
        finally:
            if process.returncode is None: process.terminate()
            await process.communicate()
    http.shutdown()
    http.server_close()

asyncio.run(main())
