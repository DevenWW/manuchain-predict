package com.gzby.manuchain.communication;

// Interface recovered from the original phone assembly backend.
public interface PlcCommunicationListener {
    void onVariableValueChange(CommunicationEvent event);
    void onVariableValueUpdate(CommunicationEvent event);
}
