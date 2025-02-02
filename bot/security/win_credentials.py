"""Windows credential manager integration for secure storage."""

import win32cred
import logging
import base64
import binascii

logger = logging.getLogger(__name__)

class WindowsCredManager:
    """Windows credential manager wrapper for secure storage."""
    
    def __init__(self):
        """Initialize credential manager."""
        self.target = "CryptoBotPhantomKey"
        logger.debug(f"Initialized WindowsCredManager with target: {self.target}")
    
    def _debug_bytes(self, data: bytes, name: str) -> None:
        """Debug helper to inspect byte data."""
        try:
            logger.debug(f"{name} length: {len(data)}")
            logger.debug(f"{name} hex: {binascii.hexlify(data).decode()}")
            logger.debug(f"{name} first 8 bytes: {list(data[:8])}")
        except Exception as e:
            logger.error(f"Failed to debug {name}: {str(e)}")
    
    def store_phantom_credentials(self, keypair_bytes: bytes) -> None:
        """Store Phantom wallet keypair securely."""
        try:
            logger.debug("=== BEGIN STORE CREDENTIALS ===")
            self._debug_bytes(keypair_bytes, "Input keypair")
            
            # Convert bytes to base64 for safer storage
            b64_data = base64.b64encode(keypair_bytes)
            self._debug_bytes(b64_data, "Base64 encoded")
            
            # Convert to string for storage
            cred_string = b64_data.decode('utf-8')
            logger.debug(f"Credential string length: {len(cred_string)}")
            
            credential = {
                'Type': win32cred.CRED_TYPE_GENERIC,
                'TargetName': self.target,
                'UserName': 'PhantomBotKey',
                'CredentialBlob': cred_string,
                'Persist': win32cred.CRED_PERSIST_LOCAL_MACHINE
            }
            
            logger.debug(f"Credential dict: {credential}")
            
            # Delete existing credentials if they exist
            try:
                logger.debug("Attempting to delete existing credentials")
                win32cred.CredDelete(self.target, win32cred.CRED_TYPE_GENERIC, 0)
                logger.debug("Successfully deleted existing credentials")
            except Exception as e:
                logger.debug(f"No existing credentials to delete: {str(e)}")
                
            logger.debug("Writing new credentials")
            win32cred.CredWrite(credential, 0)
            logger.debug("=== END STORE CREDENTIALS ===")
            
        except Exception as e:
            logger.error(f"Failed to store credentials: {str(e)}", exc_info=True)
            raise
    
    def get_credentials(self, key: str) -> bytes:
        """Retrieve stored credentials."""
        try:
            logger.debug("=== BEGIN GET CREDENTIALS ===")
            logger.debug(f"Retrieving credentials for key: {key}")
            
            cred = win32cred.CredRead(self.target, win32cred.CRED_TYPE_GENERIC, 0)
            logger.debug(f"Retrieved credential type: {type(cred)}")
            logger.debug(f"Credential keys: {cred.keys()}")
            
            if cred['UserName'] != key:
                logger.error(f"Username mismatch. Expected {key}, got {cred['UserName']}")
                raise ValueError(f"No credentials found for {key}")
            
            # Get credential blob
            cred_blob = cred['CredentialBlob']
            logger.debug(f"Credential blob type: {type(cred_blob)}")
            
            # If bytes, decode to string
            if isinstance(cred_blob, bytes):
                cred_blob = cred_blob.decode('utf-8')
                logger.debug("Decoded credential blob from bytes to string")
            
            # Decode base64 string back to bytes
            try:
                keypair_bytes = base64.b64decode(cred_blob)
                self._debug_bytes(keypair_bytes, "Decoded keypair")
                logger.debug("=== END GET CREDENTIALS ===")
                return keypair_bytes
            except Exception as e:
                logger.error(f"Failed to decode base64: {str(e)}", exc_info=True)
                raise
            
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {str(e)}", exc_info=True)
            raise
    
    def delete_credentials(self) -> None:
        """Delete stored credentials."""
        try:
            logger.debug("Attempting to delete credentials")
            win32cred.CredDelete(self.target, win32cred.CRED_TYPE_GENERIC, 0)
            logger.info("Successfully deleted stored credentials")
        except Exception as e:
            logger.error(f"Failed to delete credentials: {str(e)}", exc_info=True)
            raise
