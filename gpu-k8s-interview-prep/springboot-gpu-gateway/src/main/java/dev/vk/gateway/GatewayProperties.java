package dev.vk.gateway;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;
import org.springframework.validation.annotation.Validated;

/** Typed, validated config: fails fast at startup if mis-set. */
@Validated
@ConfigurationProperties(prefix = "gateway.backend")
public record GatewayProperties(
        @NotBlank String baseUrl,
        @DefaultValue("8") @Min(1) int maxConcurrent,
        @DefaultValue("200ms") Duration acquireTimeout,
        @DefaultValue("2s") Duration connectTimeout,
        @DefaultValue("120s") Duration readTimeout) {
}
