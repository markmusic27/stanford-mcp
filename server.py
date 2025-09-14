import logging
import click

logger = logging.getLogger(__name__)

@click.command()
@click.option("--port", default="8000", help="Port to listen on for HTTP")
@click.option("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",)
def main(port: int, log_level: str):
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()), # -> converts log_level to logging.{log_level} (e.g, INFO -> logging.INFO)
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
