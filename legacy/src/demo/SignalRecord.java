package demo;

import com.gzby.manuchain.communication.CommunicationEvent;
import com.gzby.manuchain.constant.PlcVariableConstant;

/** New adapter: safely turn a legacy device-status event into a CSV record. */
public final class SignalRecord {
    private SignalRecord() {}

    public static String toCsv(CommunicationEvent event) {
        if (!PlcVariableConstant.DEVICE_STATUS.equals(event.getType())) {
            throw new IllegalArgumentException("Expected device_status event");
        }
        if (!(event.getTarget() instanceof String) || !(event.getNewValue() instanceof Number)) {
            throw new IllegalArgumentException("Expected string device ID and numeric status");
        }
        String id = (String) event.getTarget();
        double value = ((Number) event.getNewValue()).doubleValue();
        if (!id.matches("[A-Za-z0-9_-]+") || !Double.isFinite(value)) {
            throw new IllegalArgumentException("Invalid device ID or status");
        }
        return id + "," + PlcVariableConstant.DEVICE_STATUS + "," + value;
    }

    public static void main(String[] args) {
        CommunicationEvent sample = new CommunicationEvent(
            "DEMO_01", 0, 1, PlcVariableConstant.DEVICE_STATUS, "synthetic demonstration");
        System.out.println("device_id,signal,value");
        System.out.println(toCsv(sample));
    }
}
