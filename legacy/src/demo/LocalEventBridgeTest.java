package demo;

import com.gzby.manuchain.communication.CommunicationEvent;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/** End-to-end local HTTP contract check. Runs entirely with synthetic values. */
public final class LocalEventBridgeTest {
    public static void main(String[] args) throws Exception {
        AtomicInteger requests = new AtomicInteger();
        AtomicReference<String> observed = new AtomicReference<>();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/api/online/event", exchange -> {
            requests.incrementAndGet();
            if (!"POST".equals(exchange.getRequestMethod()) ||
                    !"unit-test-token".equals(exchange.getRequestHeaders().getFirst("X-Bridge-Token"))) {
                exchange.sendResponseHeaders(403, -1);
            } else {
                ByteArrayOutputStream output = new ByteArrayOutputStream();
                try (InputStream in = exchange.getRequestBody()) {
                    byte[] buffer = new byte[1024]; int count;
                    while ((count = in.read(buffer)) != -1) output.write(buffer, 0, count);
                }
                observed.set(new String(output.toByteArray(), StandardCharsets.UTF_8));
                exchange.sendResponseHeaders(204, -1);
            }
            exchange.close();
        });
        server.start();
        try {
            LocalEventBridge bridge = new LocalEventBridge("machine_1", "unit-test-token", server.getAddress().getPort());
            CommunicationEvent event = new CommunicationEvent(new Object(), 0, 1.5, "sensor_01", "test");
            bridge.onVariableValueUpdate(event);
            bridge.onVariableValueChange(event);
            if (requests.get() != 1) throw new AssertionError("A change must not cause duplicate transmissions");
            String body = observed.get();
            if (body == null || !body.contains("\"device_id\":\"machine_1\"") ||
                !body.contains("\"signal\":\"sensor_01\"") || !body.contains("\"value\":1.5") ||
                !body.contains("\"timestamp\":")) throw new AssertionError("Unexpected event payload");
            try {
                bridge.send(new CommunicationEvent(null, null, Double.NaN, "sensor_01", ""));
                throw new AssertionError("Expected invalid-value rejection");
            } catch (IllegalArgumentException expected) { }
            if (requests.get() != 1) throw new AssertionError("Invalid value was transmitted");
            try {
                bridge.send(new CommunicationEvent(null, null, 1, "bad\"signal", ""));
                throw new AssertionError("Expected invalid-signal rejection");
            } catch (IllegalArgumentException expected) { }
            bridge.send(event, 1700000000.125);
            if (requests.get() != 2 || !observed.get().contains("\"timestamp\":1.700000000125E9"))
                throw new AssertionError("Source timestamp was not preserved");
            try {
                bridge.send(event, Double.NaN);
                throw new AssertionError("Expected invalid-timestamp rejection");
            } catch (IllegalArgumentException expected) { }
            if (requests.get() != 2) throw new AssertionError("Invalid timestamp was transmitted");
            System.out.println("LocalEventBridge contract tests passed");
        } finally { server.stop(0); }
    }
}
