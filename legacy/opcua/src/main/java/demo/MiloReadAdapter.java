package demo;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.eclipse.milo.opcua.sdk.client.OpcUaClient;
import org.eclipse.milo.opcua.stack.core.types.builtin.DataValue;
import org.eclipse.milo.opcua.stack.core.types.builtin.NodeId;
import org.eclipse.milo.opcua.stack.core.types.enumerated.TimestampsToReturn;

/** Read-only adapter for an explicitly connected Milo 0.6.x client. */
public final class MiloReadAdapter {
    public interface Sink {
        void accept(String signal, double value, double sourceTimestamp) throws Exception;
    }

    private final OpcUaClient client;
    private final Map<String, NodeId> nodes;
    private final Sink sink;

    public MiloReadAdapter(OpcUaClient client, Map<String, NodeId> nodes, Sink sink) {
        if (client == null || nodes == null || nodes.isEmpty() || sink == null)
            throw new IllegalArgumentException("client, signal mapping and sink are required");
        this.nodes = new LinkedHashMap<>(nodes);
        for (Map.Entry<String, NodeId> entry : this.nodes.entrySet()) {
            if (entry.getKey() == null || !entry.getKey().matches("[A-Za-z0-9_-]{1,64}") || entry.getValue() == null)
                throw new IllegalArgumentException("Invalid signal or NodeId");
        }
        this.client = client;
        this.sink = sink;
    }

    /** Perform one batch read. Validate the entire batch before forwarding. */
    public void readOnce() throws Exception {
        List<DataValue> values = client.readValues(0.0, TimestampsToReturn.Both,
            new ArrayList<>(nodes.values())).get(5, TimeUnit.SECONDS);
        if (values == null || values.size() != nodes.size())
            throw new IllegalStateException("Unexpected OPC UA response size");
        List<Double> numeric = new ArrayList<>();
        List<Double> timestamps = new ArrayList<>();
        long now = System.currentTimeMillis();
        for (DataValue value : values) {
            if (value == null || value.getStatusCode() == null || !value.getStatusCode().isGood()
                    || value.getValue() == null || !(value.getValue().getValue() instanceof Number))
                throw new IllegalStateException("Bad OPC UA quality or non-numeric value");
            double number = ((Number) value.getValue().getValue()).doubleValue();
            if (!Double.isFinite(number)) throw new IllegalStateException("Non-finite OPC UA value");
            if (value.getSourceTime() == null)
                throw new IllegalStateException("Missing OPC UA source timestamp");
            long sourceMillis = value.getSourceTime().getJavaTime();
            // Match the Python event assembler's freshness and clock-skew limits.
            if (sourceMillis <= 0 || sourceMillis < now - 60_000 || sourceMillis > now + 5_000)
                throw new IllegalStateException("OPC UA source timestamp outside freshness window");
            numeric.add(number);
            timestamps.add(sourceMillis / 1000.0);
        }
        int i = 0;
        for (String signal : nodes.keySet()) {
            sink.accept(signal, numeric.get(i), timestamps.get(i));
            i++;
        }
    }
}
