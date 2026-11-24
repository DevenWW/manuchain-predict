package demo;

import com.gzby.manuchain.communication.CommunicationEvent;
import java.net.URI;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.eclipse.milo.opcua.sdk.client.OpcUaClient;
import org.eclipse.milo.opcua.stack.core.security.SecurityPolicy;
import org.eclipse.milo.opcua.stack.core.types.builtin.NodeId;
import org.eclipse.milo.opcua.stack.core.types.enumerated.UserTokenType;

/** Explicit opt-in for a local, anonymous OPC UA simulator only. */
public final class MiloCollector {
    private static boolean isLoopbackEndpoint(String endpoint) {
        try {
            URI uri = URI.create(endpoint);
            return "opc.tcp".equalsIgnoreCase(uri.getScheme()) && "127.0.0.1".equals(uri.getHost());
        } catch (IllegalArgumentException e) { return false; }
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 5 || !isLoopbackEndpoint(args[0]))
            throw new IllegalArgumentException("Usage: endpoint(127.0.0.1 only) bridgePort deviceId intervalMs signal=NodeId [...]");
        int port = Integer.parseInt(args[1]);
        String deviceId = args[2];
        long interval = Long.parseLong(args[3]);
        if (interval < 1000) throw new IllegalArgumentException("intervalMs must be at least 1000");
        Map<String, NodeId> nodes = new LinkedHashMap<>();
        for (int i = 4; i < args.length; i++) {
            int separator = args[i].indexOf('=');
            if (separator <= 0 || separator == args[i].length() - 1)
                throw new IllegalArgumentException("Expected signal=NodeId");
            String signal = args[i].substring(0, separator);
            if (!signal.matches("[A-Za-z0-9_-]{1,64}"))
                throw new IllegalArgumentException("Invalid signal");
            if (nodes.put(signal, NodeId.parse(args[i].substring(separator + 1))) != null)
                throw new IllegalArgumentException("Duplicate signal");
        }
        LocalEventBridge bridge = new LocalEventBridge(deviceId, System.getenv("MANUCHAIN_BRIDGE_TOKEN"), port);
        OpcUaClient client = OpcUaClient.create(args[0], endpoints -> endpoints.stream().filter(endpoint ->
            isLoopbackEndpoint(endpoint.getEndpointUrl())
                && SecurityPolicy.None.getUri().equals(endpoint.getSecurityPolicyUri())
                && Arrays.stream(endpoint.getUserIdentityTokens()).anyMatch(t -> t.getTokenType() == UserTokenType.Anonymous)
        ).findFirst(), builder -> builder.build());
        try {
            client.connect().get(10, TimeUnit.SECONDS);
            MiloReadAdapter adapter = new MiloReadAdapter(client, nodes, (signal, value, timestamp) ->
                bridge.send(new CommunicationEvent(deviceId, null, value, signal, "OPC UA read"), timestamp));
            while (!Thread.currentThread().isInterrupted()) {
                adapter.readOnce();
                Thread.sleep(interval);
            }
        } finally {
            client.disconnect().get(10, TimeUnit.SECONDS);
        }
    }
}
