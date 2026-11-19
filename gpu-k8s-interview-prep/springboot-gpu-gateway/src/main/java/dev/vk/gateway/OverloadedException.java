package dev.vk.gateway;

class OverloadedException extends RuntimeException {
    OverloadedException() {
        super("GPU backend saturated", null, false, false);   // no stack trace: cheap under load
    }
}
