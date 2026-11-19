package dev.vk.gateway;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import org.springframework.stereotype.Component;

/**
 * Caps in-flight calls to the GPU backend. Waits briefly for a slot, then sheds load.
 * Analogy: a lift with a weight limit — the 9th person waits a moment, then takes the stairs (429).
 */
@Component
class Bulkhead {

    private final Semaphore slots;
    private final GatewayProperties props;
    private final Counter rejected;

    Bulkhead(GatewayProperties props, MeterRegistry registry) {
        this.props = props;
        this.slots = new Semaphore(props.maxConcurrent(), true);
        this.rejected = Counter.builder("inference.rejected").description("Requests shed by bulkhead").register(registry);
        registry.gauge("inference.inflight", slots, s -> props.maxConcurrent() - s.availablePermits());
    }

    void acquireOrReject() {
        try {
            if (!slots.tryAcquire(props.acquireTimeout().toMillis(), TimeUnit.MILLISECONDS)) {
                rejected.increment();
                throw new OverloadedException();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new OverloadedException();
        }
    }

    void release() {
        slots.release();
    }
}
