package demo;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import org.eclipse.milo.opcua.sdk.client.OpcUaClient;
import org.eclipse.milo.opcua.stack.core.types.builtin.DataValue;
import org.eclipse.milo.opcua.stack.core.types.builtin.DateTime;
import org.eclipse.milo.opcua.stack.core.types.builtin.NodeId;
import org.eclipse.milo.opcua.stack.core.types.builtin.StatusCode;
import org.eclipse.milo.opcua.stack.core.types.builtin.Variant;
import org.eclipse.milo.opcua.stack.core.types.enumerated.TimestampsToReturn;
import org.junit.Test;
import static org.junit.Assert.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

public class MiloReadAdapterTest {
    private DataValue value(Object v, StatusCode status, Long millis) {
        return new DataValue(new Variant(v), status, millis == null ? null : new DateTime(new Date(millis)));
    }

    @Test public void preservesSourceTimesAndRejectsInvalidBatches() throws Exception {
        long now = System.currentTimeMillis();
        OpcUaClient client = mock(OpcUaClient.class);
        Map<String, NodeId> nodes = new LinkedHashMap<>();
        nodes.put("sensor_01", new NodeId(2, "one"));
        nodes.put("sensor_02", new NodeId(2, "two"));
        List<String> delivered = new ArrayList<>();
        MiloReadAdapter adapter = new MiloReadAdapter(client, nodes,
            (signal, v, t) -> delivered.add(signal + ":" + v + ":" + t));
        DataValue good = value(1, StatusCode.GOOD, now - 1000);
        when(client.readValues(anyDouble(), eq(TimestampsToReturn.Both), anyList()))
            .thenReturn(CompletableFuture.completedFuture(Arrays.asList(good, good)));
        adapter.readOnce();
        assertEquals(Arrays.asList("sensor_01:1.0:" + ((now - 1000) / 1000.0),
                                   "sensor_02:1.0:" + ((now - 1000) / 1000.0)), delivered);
        List<DataValue> badValues = Arrays.asList(
            value(2, StatusCode.BAD, now), value("text", StatusCode.GOOD, now),
            value(Double.NaN, StatusCode.GOOD, now), value(Double.POSITIVE_INFINITY, StatusCode.GOOD, now),
            value(2, StatusCode.GOOD, null), value(2, StatusCode.GOOD, now - 61000),
            value(2, StatusCode.GOOD, now + 6000));
        for (DataValue bad : badValues) {
            delivered.clear();
            when(client.readValues(anyDouble(), eq(TimestampsToReturn.Both), anyList()))
                .thenReturn(CompletableFuture.completedFuture(Arrays.asList(good, bad)));
            assertThrows(IllegalStateException.class, adapter::readOnce);
            assertTrue("invalid batch must not be sent", delivered.isEmpty());
        }
        when(client.readValues(anyDouble(), eq(TimestampsToReturn.Both), anyList()))
            .thenReturn(CompletableFuture.completedFuture(Arrays.asList(good)));
        assertThrows(IllegalStateException.class, adapter::readOnce);
    }
}
