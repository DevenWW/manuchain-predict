package com.gzby.manuchain.communication;


public class CommunicationEvent {

	private Object target;
	private Object oldValue;
	private Object newValue;
	private String type;
	private String message;
	public CommunicationEvent(Object target, Object oldValue, Object newValue, String type, String message) {
		super();
		this.target = target;
		this.oldValue = oldValue;
		this.newValue = newValue;
		this.type = type;
		this.message = message;
	}
	public Object getTarget() {
		return target;
	}
	public void setTarget(Object target) {
		this.target = target;
	}
	public Object getOldValue() {
		return oldValue;
	}
	public void setOldValue(Object oldValue) {
		this.oldValue = oldValue;
	}
	public Object getNewValue() {
		return newValue;
	}
	public void setNewValue(Object newValue) {
		this.newValue = newValue;
	}
	public String getType() {
		return type;
	}
	public void setType(String type) {
		this.type = type;
	}
	public String getMessage() {
		return message;
	}
	public void setMessage(String message) {
		this.message = message;
	}
	
	@Override
	public String toString() {
		return "CommunicationEvent [target=" + target + ", oldValue=" + oldValue + ", newValue=" + newValue + ", type="
				+ type + ", message=" + message + "]";
	}
}