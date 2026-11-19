package dev.vk.gateway;

import java.net.http.HttpClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
class BackendConfig {

    /** One RestClient for the model server. Timeouts are explicit: never rely on defaults. */
    @Bean
    RestClient backendClient(GatewayProperties props, RestClient.Builder builder) {
        var http = HttpClient.newBuilder().connectTimeout(props.connectTimeout()).build();
        var factory = new JdkClientHttpRequestFactory(http);
        factory.setReadTimeout(props.readTimeout());
        return builder.baseUrl(props.baseUrl()).requestFactory(factory).build();
    }
}
