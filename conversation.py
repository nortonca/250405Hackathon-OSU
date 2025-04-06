import logging
import json
import time
import threading
import os

logger = logging.getLogger(__name__)

class ConversationManager:
    """
    Manages conversation history and state.
    """
    
    def __init__(self, max_history=50, history_file=None):
        """
        Initialize conversation manager.
        
        Args:
            max_history (int): Maximum number of interactions to keep in history
            history_file (str, optional): File to persist conversation history
        """
        self.max_history = max_history
        self.history_file = history_file or os.environ.get("HISTORY_FILE", "conversation_history.json")
        
        # Conversation state
        self.history = []
        self.last_interaction_time = 0
        self.history_lock = threading.Lock()
        
        # Load existing history if available
        self._load_history()
        
        logger.info(f"ConversationManager initialized with max_history={max_history}")
    
    def add_interaction(self, user_input, system_response, metadata=None):
        """
        Add a new interaction to the conversation history.
        
        Args:
            user_input (str): User's input or transcribed speech
            system_response (str): System's response
            metadata (dict, optional): Additional metadata for the interaction
        """
        with self.history_lock:
            # Create interaction object
            interaction = {
                "timestamp": time.time(),
                "user_input": user_input,
                "system_response": system_response,
                "metadata": metadata or {}
            }
            
            # Add to history
            self.history.append(interaction)
            
            # Trim history if necessary
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
            
            # Update last interaction time
            self.last_interaction_time = interaction["timestamp"]
            
            # Save history
            self._save_history()
            
            logger.debug(f"Added interaction to history (total: {len(self.history)})")
    
    def get_history(self, limit=None):
        """
        Get conversation history.
        
        Args:
            limit (int, optional): Maximum number of recent interactions to return
            
        Returns:
            list: List of interaction objects
        """
        with self.history_lock:
            if limit is None or limit >= len(self.history):
                return self.history.copy()
            else:
                return self.history[-limit:].copy()
    
    def clear_history(self):
        """Clear conversation history."""
        with self.history_lock:
            self.history = []
            self._save_history()
            logger.info("Conversation history cleared")
    
    def get_conversation_summary(self):
        """
        Get a summary of the conversation.
        
        Returns:
            dict: Summary information about the conversation
        """
        with self.history_lock:
            return {
                "total_interactions": len(self.history),
                "last_interaction_time": self.last_interaction_time,
                "duration": (time.time() - self.history[0]["timestamp"]) if self.history else 0,
                "recent_topics": self._extract_recent_topics()
            }
    
    def _extract_recent_topics(self):
        """
        Extract recent topics from conversation - placeholder implementation.
        
        Returns:
            list: List of recent topics
        """
        # In a real implementation, this would use NLP to extract topics
        # For now, we'll just return a placeholder
        return ["general conversation"]
    
    def _save_history(self):
        """Save conversation history to file."""
        if not self.history_file:
            return
            
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
            logger.debug(f"Conversation history saved to {self.history_file}")
        except Exception as e:
            logger.error(f"Failed to save conversation history: {str(e)}")
    
    def _load_history(self):
        """Load conversation history from file."""
        if not self.history_file or not os.path.exists(self.history_file):
            logger.info("No history file found, starting with empty history")
            return
            
        try:
            with open(self.history_file, 'r') as f:
                loaded_history = json.load(f)
                
                # Validate loaded history
                if isinstance(loaded_history, list):
                    # Keep only valid entries
                    valid_entries = []
                    for entry in loaded_history:
                        if (isinstance(entry, dict) and 
                            "timestamp" in entry and 
                            "user_input" in entry and 
                            "system_response" in entry):
                            valid_entries.append(entry)
                    
                    with self.history_lock:
                        self.history = valid_entries[-self.max_history:] if len(valid_entries) > self.max_history else valid_entries
                        if self.history:
                            self.last_interaction_time = max(entry["timestamp"] for entry in self.history)
                    
                    logger.info(f"Loaded {len(self.history)} conversation history entries")
                else:
                    logger.warning("Invalid history format, starting with empty history")
        except Exception as e:
            logger.error(f"Failed to load conversation history: {str(e)}")
