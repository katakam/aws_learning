package dev.vk.gateway;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.util.Map;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

/** Thin pass-through to an OpenAI-compatible server (e.g. vLLM), protected by a bulkhead. */
@RestController
class InferenceController {

    private static final ParameterizedTypeReference<Map<String, Object>> JSON_MAP = new ParameterizedTypeReference<>() { };

    private final RestClient backend;
    private final Bulkhead bulkhead;
    private final Timer latency;

    InferenceController(RestClient backendClient, Bulkhead bulkhead, MeterRegistry registry) {
        this.backend = backendClient;
        this.bulkhead = bulkhead;
        this.latency = Timer.builder("inference.latency").publishPercentileHistogram().register(registry);
    }

    /** Non-streaming completion. */
    @PostMapping("/v1/chat/completions")
    Map<String, Object> chat(@RequestBody Map<String, Object> request) {
        bulkhead.acquireOrReject();                       // 429 if saturated
        var sample = Timer.start();
        try {
            return backend.post().uri("/v1/chat/completions")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(request)
                    .retrieve()
                    .body(JSON_MAP);
        } finally {
            sample.stop(latency);
            bulkhead.release();                           // always give the slot back
        }
    }

    /**
     * Streaming (SSE) completion: bytes are copied through as they arrive.
     * The slot is acquired here (so we can still answer 429) and released when the stream ends.
     * If the client disconnects, the write throws, the copy loop exits, and the upstream
     * connection is closed — so the GPU stops generating for nobody.
     */
    @PostMapping(path = "/v1/chat/completions/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    StreamingResponseBody stream(@RequestBody Map<String, Object> request) {
        bulkhead.acquireOrReject();
        var body = new java.util.HashMap<>(request);
        body.put("stream", true);
        return out -> {
            try {
                backend.post().uri("/v1/chat/completions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .body(body)
                        .exchange((req, res) -> {
                            try (var in = res.getBody()) {
                                in.transferTo(out);       // for per-chunk flushing, loop and out.flush()
                            }
                            return null;
                        });
            } finally {
                bulkhead.release();
            }
        };
    }
}
