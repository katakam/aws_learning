package dev.vk.gateway;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.ResourceAccessException;

@RestControllerAdvice
class ApiErrors {

    @ExceptionHandler(OverloadedException.class)
    ResponseEntity<ProblemDetail> overloaded(OverloadedException e) {
        var pd = ProblemDetail.forStatusAndDetail(HttpStatus.TOO_MANY_REQUESTS, "Model backend is busy, retry shortly");
        return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS).header(HttpHeaders.RETRY_AFTER, "2").body(pd);
    }

    @ExceptionHandler(ResourceAccessException.class)   // connect/read timeout, connection refused
    ResponseEntity<ProblemDetail> backendUnavailable(ResourceAccessException e) {
        var pd = ProblemDetail.forStatusAndDetail(HttpStatus.GATEWAY_TIMEOUT, "Model backend unreachable or too slow");
        return ResponseEntity.status(HttpStatus.GATEWAY_TIMEOUT).body(pd);
    }
}
