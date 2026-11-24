# Legacy device-event bridge

The four files in `src/com/gzby/manuchain/` are unchanged source files from
`phone（manuchain）.rar` → `manuchain.rar` →
`manuchain/src/main/java/com/gzby/manuchain/`: communication event, listener,
adapter and PLC signal names. The source archive has no known individual-file
attribution; original author contributions remain to be confirmed. Other legacy
configuration, real data, third-party binaries and credentials are excluded.

`src/demo/SignalRecord.java` is newly written with OpenAI Codex assistance. It
validates a device status event and converts it to a simple CSV row. It neither
connects to a PLC nor claims to implement the thesis model. It is a minimal
bridge example and is not wired to `train.py`: the model requires 15 numerical
features and a seven-day target, while this event contains one status only.
The mapping from real equipment signals to model features remains unverified.

Using JDK 8 or later, from this directory:

```sh
mkdir -p /tmp/manuchain-legacy-classes
javac -d /tmp/manuchain-legacy-classes $(find src -name '*.java')
java -cp /tmp/manuchain-legacy-classes demo.SignalRecordTest
java -cp /tmp/manuchain-legacy-classes demo.SignalRecord
```

The demonstration uses synthetic values. Do not use it to operate real devices.

## Local online event bridge

`LocalEventBridge` is a newly written listener for the original
`PlcCommunication.addVariableListener` contract. The original code sets the
event target to the PLC communication object, so the adapter takes an explicit
stable device ID; it does not infer one. It receives the variable name from
`event.getType()` and the numeric reading from `event.getNewValue()`. It adds a
Unix-seconds timestamp at the bridge, not a measurement time from the device.
Only numeric, finite values and short alphanumeric/underscore/hyphen IDs and
signal names are accepted. Each update is sent once to the local Python server
as JSON; the separate change callback is intentionally ignored because the old
PLC implementation fires both callbacks on a change.

Start the Python server in online mode as described in the top-level README,
using the same `MANUCHAIN_BRIDGE_TOKEN` in both processes. With a JDK 8 or later,
compile and run the synthetic tests:

```sh
mkdir -p /tmp/manuchain-legacy-classes
javac -d /tmp/manuchain-legacy-classes $(find src -name '*.java')
java -cp /tmp/manuchain-legacy-classes demo.LocalEventBridgeTest
java -cp /tmp/manuchain-legacy-classes demo.BridgeDemo status 8000
java -cp /tmp/manuchain-legacy-classes demo.BridgeDemo features 8000
```

The `status` example sends one `device_status` event; the Python server's
default demo mapping does not accept it and the bridge reports the HTTP error.
It cannot form a model input. The `features` example sends fifteen `sensor_01` to `sensor_15` values
invented solely to test the end-to-end interface. They are not real PLC fields
or thesis data. There is no automatic connection to the legacy PLC service.

The real system could register `new LocalEventBridge(deviceId, token, port)`
with `plcCommunication.addVariableListener(variableName, listener)` for each
confirmed numeric signal. Before that, determine permitted data, actual signal
names, units and meaning, and their mapping to the model's features. The
existing PLC reader synchronously invokes listeners; this adapter performs a
bounded HTTP call and may block that thread for up to the configured timeouts.
It has no queue, durable delivery or retries, and must not be used for
production acquisition without addressing those limitations. This project
does not write commands to a device.

## OPC UA / Milo read adapter

`opcua/` adds a newly written read-only adapter using Eclipse Milo
`sdk-client` 0.6.5. The source archives contain a 0.2.4 OPC UA client project
and a 0.6.5-SNAPSHOT Milo source tree. Its batch `readValues` pattern follows
that archived code and the 0.6.x API; the incompatible 1.x API is not used.
Archived addresses and credentials are excluded.

The command-line collector is an explicit opt-in for a **local simulator only**.
It accepts only `opc.tcp://127.0.0.1:...`, and requires the discovered endpoint
to use the same loopback host, anonymous authentication and `SecurityPolicy.None`.
The latter has no encryption and is unsuitable for a real network or device.
It reads supplied nodes at a fixed interval and posts valid values to
`LocalEventBridge`. The Python online mode must be running and its mapping must
recognize the chosen signal names. Starting the application does not start this
collector or connect to OPC UA.

With a JDK, Maven and access to Maven Central, build in `legacy/opcua`:

```sh
mvn package dependency:build-classpath -Dmdep.outputFile=/tmp/manuchain-milo-classpath
export MANUCHAIN_BRIDGE_TOKEN='the-same-token-as-the-local-server'
java -cp "target/classes:$(cat /tmp/manuchain-milo-classpath)" demo.MiloCollector \
  'opc.tcp://127.0.0.1:4840/example' 8000 DEMO_01 1000 \
  'sensor_01=ns=2;s=example1' 'sensor_02=ns=2;s=example2'
```

The endpoint and NodeIds are illustrative; use values from your local simulator.
Arguments are endpoint, local Python server port, device ID, polling interval
in milliseconds (at least 1000), and one or more `signal=NodeId` mappings. This
example supplies two readings, not the 15 features needed for prediction. The
node names are not claimed as real thesis features. The Python server can
reject unknown signals or wait for the remaining mapped features.

`MiloReadAdapter` also accepts an **already configured and connected** Milo
client, a map from signal names to `NodeId` objects, and a callback. It validates
quality, numeric finiteness and source timestamps of the entire read response
before calling the callback. A missing source timestamp, one older than 60
seconds or more than five seconds in the future rejects the batch. These
limits match the Python event assembler and require synchronized clocks. An integration can forward each callback to
`bridge.send(new CommunicationEvent(deviceId, null, value, signal, "OPC UA read"), sourceTimestamp)`.
Callers are responsible for secure endpoint selection, authentication,
certificate validation, scheduling and shutdown. Failed reads or delivery stop
the command-line collector; there is no retry, buffering or atomic delivery of
separate HTTP events. OPC UA source timestamps are forwarded to Python; the
legacy event listener without a source timestamp still uses receipt time. The web settings page and Python server do not start this Java
module or change its mapping.

The module was compiled against the actual Milo 0.6.5 dependencies and `mvn test`
passed. The checked-in JUnit test covers quality, numeric values, batch size,
source timestamp preservation, missing and stale timestamps, and future clock
skew. The local HTTP bridge contract test also passed, including explicit source
timestamp forwarding. A local OPC UA simulator attempt was stopped while it was
initializing its address space; end-to-end OPC UA server integration has not
yet been verified. No real device was contacted.
