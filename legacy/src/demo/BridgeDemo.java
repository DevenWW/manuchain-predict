package demo;

import com.gzby.manuchain.communication.CommunicationEvent;
import com.gzby.manuchain.constant.PlcVariableConstant;

/** Sends synthetic events only. No PLC, production address or credentials. */
public final class BridgeDemo {
    public static void main(String[] args) throws Exception {
        if (args.length != 2 || !(args[0].equals("status") || args[0].equals("features"))) {
            throw new IllegalArgumentException("Usage: demo.BridgeDemo status|features PORT");
        }
        LocalEventBridge bridge = new LocalEventBridge("DEMO_01", System.getenv("MANUCHAIN_BRIDGE_TOKEN"),
                                                        Integer.parseInt(args[1]));
        if (args[0].equals("status")) {
            bridge.send(new CommunicationEvent(null, null, 1, PlcVariableConstant.DEVICE_STATUS, "demo"));
            System.out.println("Sent synthetic device_status; not a complete model input.");
        } else {
            for (int i = 1; i <= 15; i++) {
                String signal = String.format(java.util.Locale.ROOT, "sensor_%02d", i);
                bridge.send(new CommunicationEvent(null, null, (i - 8) * 0.1, signal, "synthetic demo"));
            }
            System.out.println("Sent 15 synthetic feature signals for interface testing.");
        }
    }
}
