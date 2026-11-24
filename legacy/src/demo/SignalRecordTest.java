package demo;

import com.gzby.manuchain.communication.CommunicationEvent;
import com.gzby.manuchain.constant.PlcVariableConstant;

public final class SignalRecordTest {
    public static void main(String[] args) {
        CommunicationEvent event = new CommunicationEvent("D_1", 0, 1,
            PlcVariableConstant.DEVICE_STATUS, "demo");
        if (!"D_1,device_status,1.0".equals(SignalRecord.toCsv(event))) throw new AssertionError();
        event.setTarget("D,2");
        try {
            SignalRecord.toCsv(event);
            throw new AssertionError("CSV delimiter must be rejected");
        } catch (IllegalArgumentException expected) { }
        event.setTarget("D_2");
        event.setType("unknown");
        try {
            SignalRecord.toCsv(event);
            throw new AssertionError("Unknown type must be rejected");
        } catch (IllegalArgumentException expected) { }
        System.out.println("SignalRecord tests passed");
    }
}
