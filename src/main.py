"""Main FastAPI application."""

import logging
import os

from agent_framework.observability import enable_instrumentation
from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.config import API_TRACES_INSTRUMENTATION_KEY, ASPIRE_OTLP_ENDPOINT
from src.routes import agent, health, workflow, workflow_viz

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
logging.info("Loading configuration settings.")

# Configure Azure Monitor
if API_TRACES_INSTRUMENTATION_KEY:
    try:
        configure_azure_monitor(
            connection_string=API_TRACES_INSTRUMENTATION_KEY,
            enable_live_metrics=True,
        )
        logger.info("Azure Monitor configured successfully")
    except Exception as e:
        logger.warning(f"Failed to configure Azure Monitor: {e}")

# Enable instrumentation from agent_framework
enable_instrumentation(enable_sensitive_data=True)

# Configure OTLP exporter for Aspire (after enable_instrumentation)
try:
    # Parse endpoint - remove http:// or https:// if present
    otlp_endpoint = ASPIRE_OTLP_ENDPOINT
    if otlp_endpoint.startswith("http://"):
        otlp_endpoint = otlp_endpoint[7:]
    elif otlp_endpoint.startswith("https://"):
        otlp_endpoint = otlp_endpoint[8:]

    # Get the existing tracer provider or create a new one
    tracer_provider = trace.get_tracer_provider()

    # If it's not an SDK tracer provider, create one
    if not isinstance(tracer_provider, TracerProvider):
        resource = Resource.create({"service.name": "custom-agent"})
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)

    # Configure OTLP exporter for Aspire (gRPC)
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,  # Use insecure for local development
    )

    # Add batch span processor to existing tracer provider
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    logger.info(f"OTLP exporter configured for Aspire at {otlp_endpoint}")
except Exception as e:
    logger.warning(f"Failed to configure OTLP exporter for Aspire: {e}")

# Create FastAPI app
app = FastAPI(
    title="Custom Agent API",
    version="1.0.0",
    description="Custom Agent API",
)

# Include routers
app.include_router(agent.router)
app.include_router(health.router)
app.include_router(workflow.router)
app.include_router(workflow_viz.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Custom Agent API", "version": "1.0.0"}
