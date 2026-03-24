import os
import time
from flask import request, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry, multiprocess

# Define Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total count of HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Histogram of HTTP request durations in seconds",
    ["method", "endpoint"]
)

def init_metrics(app):
    """
    Initializes Prometheus metrics for the Flask application.
    """
    
    @app.before_request
    def before_request():
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        # Avoid tracking metrics for the /metrics endpoint itself to keep it clean,
        # or include it if desired. The requirement says "not interfere with existing routes".
        # We also check if start_time exists in case of early returns/errors.
        if hasattr(g, "start_time"):
            duration = time.time() - g.start_time
            endpoint = str(request.url_rule) if request.url_rule else "unknown"
            method = request.method
            status = str(response.status_code)

            http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
        
        return response

    @app.route("/metrics")
    def metrics():
        """
        Endpoint to expose Prometheus metrics.
        """
        if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
            data = generate_latest(registry)
        else:
            data = generate_latest()
            
        return data, 200, {"Content-Type": CONTENT_TYPE_LATEST}
