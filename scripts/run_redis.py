"""
Run Redis server in the background.
"""
import sys
import os
import asyncio
import logging
from pathlib import Path
import subprocess
import signal
import atexit
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from scripts.dev_redis_server import DevRedisServer

def setup_logging():
    """Configure logging."""
    log_file = project_root / "logs" / "redis.log"
    log_file.parent.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr)
        ]
    )

async def run_server():
    """Run the Redis server."""
    try:
        setup_logging()
        logging.info("Starting Redis server...")
        
        server = DevRedisServer()
        await server.start()
        
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        logging.error(f"Error running Redis server: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Create PID file
        pid_file = project_root / "redis.pid"
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        
        # Register cleanup
        def cleanup():
            pid_file.unlink(missing_ok=True)
        atexit.register(cleanup)
        
        # Run server
        asyncio.run(run_server())
        
    except KeyboardInterrupt:
        logging.info("Redis server stopped")
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
