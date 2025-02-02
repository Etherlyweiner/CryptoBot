"""
Windows service for running the development Redis server.
"""
import sys
import time
import logging
import asyncio
from pathlib import Path
import win32serviceutil
import win32service
import win32event
import servicemanager

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from scripts.dev_redis_server import DevRedisServer

class RedisService(win32serviceutil.ServiceFramework):
    _svc_name_ = "CryptoBotRedis"
    _svc_display_name_ = "CryptoBot Redis Service"
    _svc_description_ = "Development Redis server for CryptoBot"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.server = None
        self.running = True
    
    def SvcStop(self):
        """Stop the service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False
        if self.server:
            self.server.stop()
    
    def SvcDoRun(self):
        """Run the service."""
        try:
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PID_INFO,
                ('Starting Redis service')
            )
            
            # Configure logging
            log_file = project_root / "logs" / "redis_service.log"
            log_file.parent.mkdir(exist_ok=True)
            
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
            
            # Start Redis server
            self.server = DevRedisServer()
            asyncio.run(self.server.start())
            
        except Exception as e:
            servicemanager.LogErrorMsg(str(e))
            logging.error(f"Service error: {str(e)}")

def install_service():
    """Install the Windows service."""
    try:
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(RedisService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            win32serviceutil.HandleCommandLine(RedisService)
    except Exception as e:
        logging.error(f"Error installing service: {str(e)}")

if __name__ == '__main__':
    install_service()
