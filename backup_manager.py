"""Database and configuration backup management."""

import os
import shutil
import logging
import json
import sqlite3
from datetime import datetime
import tarfile
import asyncio
from typing import List, Optional
import aiofiles
from prometheus_client import Counter, Gauge

logger = logging.getLogger('BackupManager')

class BackupManager:
    """Manages database and configuration backups."""
    
    def __init__(self,
                 backup_dir: str = 'backups',
                 max_backups: int = 10,
                 backup_interval: int = 86400):  # 24 hours
        """Initialize backup manager."""
        self.backup_dir = backup_dir
        self.max_backups = max_backups
        self.backup_interval = backup_interval
        
        # Ensure backup directory exists
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Prometheus metrics
        self.backup_success = Counter('backup_success_total',
                                    'Number of successful backups',
                                    ['type'])
        self.backup_failure = Counter('backup_failure_total',
                                    'Number of failed backups',
                                    ['type'])
        self.backup_size = Gauge('backup_size_bytes',
                               'Size of latest backup in bytes',
                               ['type'])
        self.backup_count = Gauge('backup_count',
                                'Number of backups stored')
        
    async def create_backup(self) -> Optional[str]:
        """Create a new backup of the database and configuration."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(self.backup_dir, f'backup_{timestamp}.tar.gz')
        
        try:
            # Create temporary directory for files to backup
            temp_dir = os.path.join(self.backup_dir, 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Backup database
            await self._backup_database(temp_dir)
            
            # Backup configuration
            await self._backup_config(temp_dir)
            
            # Create compressed archive
            with tarfile.open(backup_path, 'w:gz') as tar:
                tar.add(temp_dir, arcname='')
                
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
            # Update metrics
            self.backup_success.labels(type='full').inc()
            self.backup_size.labels(type='full').set(os.path.getsize(backup_path))
            self.backup_count.set(len(self._list_backups()))
            
            # Rotate old backups
            await self._rotate_backups()
            
            logger.info(f"Backup created successfully: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.backup_failure.labels(type='full').inc()
            logger.error(f"Backup failed: {e}")
            return None
            
    async def restore_backup(self, backup_path: str) -> bool:
        """Restore from a backup file."""
        try:
            # Create temporary directory for extraction
            temp_dir = os.path.join(self.backup_dir, 'restore_temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Extract backup
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(temp_dir)
                
            # Restore database
            await self._restore_database(temp_dir)
            
            # Restore configuration
            await self._restore_config(temp_dir)
            
            # Clean up
            shutil.rmtree(temp_dir)
            
            logger.info(f"Backup restored successfully from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
            
    async def _backup_database(self, temp_dir: str):
        """Backup SQLite database."""
        db_path = os.getenv('DB_PATH', 'trading.db')
        if os.path.exists(db_path):
            backup_db = os.path.join(temp_dir, 'database.sqlite')
            
            # Use SQLite backup API
            src = sqlite3.connect(db_path)
            dst = sqlite3.connect(backup_db)
            src.backup(dst)
            src.close()
            dst.close()
            
    async def _backup_config(self, temp_dir: str):
        """Backup configuration files."""
        config_files = [
            '.env',
            'config.yaml',
            'ip_whitelist.txt',
            'private_config.yaml'
        ]
        
        for file in config_files:
            if os.path.exists(file):
                shutil.copy2(file, os.path.join(temp_dir, file))
                
    async def _restore_database(self, temp_dir: str):
        """Restore SQLite database."""
        backup_db = os.path.join(temp_dir, 'database.sqlite')
        db_path = os.getenv('DB_PATH', 'trading.db')
        
        if os.path.exists(backup_db):
            # Create backup of current database
            if os.path.exists(db_path):
                shutil.copy2(db_path, f"{db_path}.bak")
                
            # Restore from backup
            src = sqlite3.connect(backup_db)
            dst = sqlite3.connect(db_path)
            src.backup(dst)
            src.close()
            dst.close()
            
    async def _restore_config(self, temp_dir: str):
        """Restore configuration files."""
        config_files = [
            '.env',
            'config.yaml',
            'ip_whitelist.txt',
            'private_config.yaml'
        ]
        
        for file in config_files:
            backup_file = os.path.join(temp_dir, file)
            if os.path.exists(backup_file):
                # Create backup of current config
                if os.path.exists(file):
                    shutil.copy2(file, f"{file}.bak")
                    
                # Restore from backup
                shutil.copy2(backup_file, file)
                
    def _list_backups(self) -> List[str]:
        """List all backup files."""
        backups = []
        for file in os.listdir(self.backup_dir):
            if file.startswith('backup_') and file.endswith('.tar.gz'):
                backups.append(os.path.join(self.backup_dir, file))
        return sorted(backups)
        
    async def _rotate_backups(self):
        """Remove old backups exceeding max_backups."""
        backups = self._list_backups()
        if len(backups) > self.max_backups:
            for backup in backups[:-self.max_backups]:
                try:
                    os.remove(backup)
                    logger.info(f"Removed old backup: {backup}")
                except Exception as e:
                    logger.error(f"Error removing old backup {backup}: {e}")
                    
    async def start_backup_scheduler(self):
        """Start periodic backup scheduler."""
        while True:
            try:
                await self.create_backup()
            except Exception as e:
                logger.error(f"Scheduled backup failed: {e}")
            await asyncio.sleep(self.backup_interval)
            
# Global backup manager instance
backup_manager = BackupManager()
