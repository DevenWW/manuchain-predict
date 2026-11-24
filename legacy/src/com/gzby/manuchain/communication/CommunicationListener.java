package com.gzby.manuchain.communication;

import java.util.EventListener;


public interface CommunicationListener extends EventListener{

	void onOpen(CommunicationEvent e);
	
	void onClose(CommunicationEvent e);
	
	void onError(CommunicationEvent e);
	
	void onMessage(CommunicationEvent e);
	
	void onRecieveError(CommunicationEvent e);
	
	void onRecieveSuccess(CommunicationEvent e);
}