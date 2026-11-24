package demo;

import com.gzby.manuchain.communication.CommunicationEvent;
import com.gzby.manuchain.communication.PlcCommunicationListener;
import java.io.IOException;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.time.Instant;

/**
 * Explicit adapter for the original PlcCommunication.addVariableListener API.
 * The legacy event target is a PlcCommunication object, not a device ID;
 * supply a verified stable ID when constructing this adapter.
 * Never sends device writes or initializes a connection to real equipment.
 */
public final class LocalEventBridge implements PlcCommunicationListener {
    private final String deviceId;
    private final String token;
    private final URL endpoint;

    public LocalEventBridge(String deviceId, String token, int port) throws IOException {
        checkName(deviceId, "deviceId");
        if (token == null || token.isEmpty() || token.indexOf('\n') >= 0 || token.indexOf('\r') >= 0)
            throw new IllegalArgumentException("Set a non-empty MANUCHAIN_BRIDGE_TOKEN");
        if (port < 1 || port > 65535) throw new IllegalArgumentException("Invalid port");
        this.deviceId = deviceId;
        this.token = token;
        this.endpoint = new URL("http://127.0.0.1:" + port + "/api/online/event");
    }

    private static void checkName(String value, String field) {
        if (value == null || !value.matches("[A-Za-z0-9_-]{1,64}"))
            throw new IllegalArgumentException("Invalid " + field);
    }

    /** Exposed for contract tests and callers that need explicit failure handling. */
    public void send(CommunicationEvent event) throws IOException {
        Instant now = Instant.now();
        send(event, now.getEpochSecond() + now.getNano() / 1_000_000_000.0);
    }

    /** Forward the actual source timestamp in Unix seconds when one is available. */
    public void send(CommunicationEvent event, double timestamp) throws IOException {
        if (event == null) throw new IllegalArgumentException("Missing event");
        if (!Double.isFinite(timestamp) || timestamp <= 0)
            throw new IllegalArgumentException("Invalid source timestamp");
        String signal = event.getType();
        checkName(signal, "signal");
        if (!(event.getNewValue() instanceof Number))
            throw new IllegalArgumentException("Expected numeric signal value");
        double value = ((Number) event.getNewValue()).doubleValue();
        if (!Double.isFinite(value)) throw new IllegalArgumentException("Non-finite value");
        String body = "{\"device_id\":\"" + deviceId + "\",\"signal\":\"" + signal
            + "\",\"value\":" + Double.toString(value) + ",\"timestamp\":"
            + Double.toString(timestamp) + "}";
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        HttpURLConnection connection = (HttpURLConnection) endpoint.openConnection();
        try {
            connection.setConnectTimeout(2000);
            connection.setReadTimeout(2000);
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            connection.setRequestProperty("X-Bridge-Token", token);
            connection.setFixedLengthStreamingMode(bytes.length);
            connection.setDoOutput(true);
            try (OutputStream out = connection.getOutputStream()) { out.write(bytes); }
            int status = connection.getResponseCode();
            if (status < 200 || status >= 300) throw new IOException("Bridge rejected event: HTTP " + status);
        } finally {
            connection.disconnect();
        }
    }

    // fireEvent calls update on every read; forwarding both callbacks duplicates
    // changed signals. Change callback intentionally does nothing.
    @Override public void onVariableValueChange(CommunicationEvent event) { }
    @Override public void onVariableValueUpdate(CommunicationEvent event) {
        try { send(event); }
        catch (IOException | IllegalArgumentException error) {
            System.err.println("Event not delivered: " + error.getMessage());
        }
    }
}
