"""
Simple JSON-based user storage for MVP
No complex database needed for demo with few users
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UserStore:
    """Simple JSON file-based user storage"""
    
    def __init__(self, storage_file: str = "users.json"):
        self.storage_file = storage_file
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create storage file if it doesn't exist"""
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, 'w') as f:
                json.dump({}, f)
            logger.info(f"Created user storage file: {self.storage_file}")
    
    def _load_users(self) -> Dict[str, Any]:
        """Load all users from storage"""
        try:
            with open(self.storage_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return {}
    
    def _save_users(self, users: Dict[str, Any]):
        """Save all users to storage"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(users, f, indent=2, default=str)
            logger.info("Users saved successfully")
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a new user
        
        Args:
            user_data: Dictionary containing user information
                - email (required)
                - name (required)
                - google_id (required)
                - phone (optional)
                - unique_code (auto-generated if not provided)
        
        Returns:
            user_id if successful, None otherwise
        """
        try:
            users = self._load_users()
            
            # Check if user already exists by email
            for user_id, user in users.items():
                if user.get('email') == user_data.get('email'):
                    logger.info(f"User already exists: {user_data.get('email')}")
                    return user_id
            
            # Generate user_id and unique_code
            google_id = user_data.get('google_id')
            user_id = f"user_{google_id}"
            
            if 'unique_code' not in user_data:
                # Generate unique code from email
                email = user_data.get('email', '')
                user_data['unique_code'] = email.split('@')[0].replace('.', '').replace('-', '')[:10]
            
            # Add metadata
            user_data['user_id'] = user_id
            user_data['created_at'] = datetime.now().isoformat()
            user_data['updated_at'] = datetime.now().isoformat()
            user_data['gmail_connected'] = False
            user_data['calendar_connected'] = False
            
            # Save user
            users[user_id] = user_data
            self._save_users(users)
            
            logger.info(f"Created new user: {user_id}")
            return user_id
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        users = self._load_users()
        return users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        users = self._load_users()
        for user_id, user in users.items():
            if user.get('email') == email:
                return user
        return None
    
    def get_user_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Google ID"""
        users = self._load_users()
        for user_id, user in users.items():
            if user.get('google_id') == google_id:
                return user
        return None
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update user information
        
        Args:
            user_id: User ID to update
            updates: Dictionary of fields to update
        
        Returns:
            True if successful, False otherwise
        """
        try:
            users = self._load_users()
            
            if user_id not in users:
                logger.error(f"User not found: {user_id}")
                return False
            
            # Update fields
            users[user_id].update(updates)
            users[user_id]['updated_at'] = datetime.now().isoformat()
            
            self._save_users(users)
            logger.info(f"Updated user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        try:
            users = self._load_users()
            
            if user_id in users:
                del users[user_id]
                self._save_users(users)
                logger.info(f"Deleted user: {user_id}")
                return True
            
            logger.warning(f"User not found for deletion: {user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False
    
    def list_users(self) -> Dict[str, Any]:
        """List all users"""
        return self._load_users()


# Global instance
user_store = UserStore()
