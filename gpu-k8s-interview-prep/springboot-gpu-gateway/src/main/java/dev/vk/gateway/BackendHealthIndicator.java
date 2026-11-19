package dev.vk.gateway;

// NOTE: Boot 4 moved health contributor types to org.springframework.boot.health.contributor.
// On Boot 3.x use org.springframework.boot.actuate.health.{Health,HealthIndicator}.
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * Backend reachability. Wired into the READINESS group only (see application.yml).
 * Never put this in liveness: a backend outage would make Kubernetes restart healthy gateways.
 */
@Component("backend")
class BackendHealthIndicator implements HealthIndicator {

    private final RestClient backend;

    BackendHealthIndicator(RestClient backendClient) {
        this.backend = backendClient;
    }

    @Override
    public Health health() {
        try {
            backend.get().uri("/health").retrieve().toBodilessEntity();
            return Health.up().build();
        } catch (Exception e) {
            return Health.down().withDetail("error", e.getClass().getSimpleName()).build();
        }
    }
}
