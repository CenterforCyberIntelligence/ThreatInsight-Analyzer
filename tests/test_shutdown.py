import os
import time
import signal
import sys
from app.utilities.logger import logger

def graceful_shutdown(sig, frame):
    """Test shutdown handler with simple output"""
    logger.info("Graceful shutdown initiated...")
    # Add a brief delay to simulate cleanup
    time.sleep(0.5)
    logger.info("Cleanup complete, exiting...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler
    signal.signal(signal.SIGINT, graceful_shutdown)
    
    logger.info("Press CTRL+C to test graceful shutdown")
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
            print(".", end="", flush=True)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt caught in main")
    finally:
        logger.info("Finally block executed") 