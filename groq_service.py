import os
import base64
import time
import logging
import functools
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Check API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables")

# Initialize client with efficient connection pooling
client = Groq(
    api_key=GROQ_API_KEY,
    # Additional configuration if needed for optimization
)

# Cache for API responses - simple in-memory cache
# In production, consider using Redis or another distributed cache
CACHE_SIZE = 200  # Maximum entries to store (increased)
CACHE_TTL = 60 * 60  # Cache time-to-live in seconds (1 hour)
api_cache = {}

# Cache performance metrics
cache_metrics = {
    'hits': 0,
    'misses': 0,
    'saved_time': 0,  # estimated time saved by cache hits in seconds
    'prunes': 0,      # number of cache pruning operations
}

# Define a single system prompt to be used for all interactions
LUMI_SYSTEM_PROMPT = "You are Lumi, a friendly and supportive assistant with a touch of playful sass. You always see an image and know you're interacting with a human friend—if the image shows a human, that's likely the user talking to you. Keep responses conversational and concise (1–3 sentences), ensuring a warm and genuine connection in every exchange."

# Enhanced cache decorator with better performance monitoring
def cache_api_response(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Optimize cache key generation - use only relevant parts of args
        # For get_ai_response, we'll hash only the transcription and a truncated image hash
        if func.__name__ == 'get_ai_response':
            # Extract key elements for caching
            transcription = args[0] if args else kwargs.get('transcription', '')
            
            # For image data, just use first 100 chars of hash if available
            image_data = args[1] if len(args) > 1 else kwargs.get('image_data', None)
            image_hash = None
            if image_data:
                # Generate a simple hash instead of storing the whole image data
                image_hash = str(hash(image_data[:100]))  # Just use beginning for faster hash
            
            # Use a more efficient cache key
            cache_key = f"{func.__name__}:{transcription}:{image_hash}"
        else:
            # Fallback for other functions
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
        
        # Check cache with performance timing
        current_time = time.time()
        
        if cache_key in api_cache:
            cache_entry = api_cache[cache_key]
            if current_time - cache_entry['timestamp'] < CACHE_TTL:
                cache_metrics['hits'] += 1
                # Estimate time saved (using the original execution time)
                saved_time = cache_entry.get('execution_time', 1.0)  # Default to 1s if not recorded
                cache_metrics['saved_time'] += saved_time
                logger.debug(f"Cache hit for {func.__name__}, saved ~{saved_time:.2f}s")
                return cache_entry['result']
        
        # Execute function if not in cache
        cache_metrics['misses'] += 1
        execution_start = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - execution_start
        
        # Store in cache with execution time
        api_cache[cache_key] = {
            'result': result,
            'timestamp': current_time,
            'execution_time': execution_time
        }
        
        # Prune cache if too large - more efficient pruning approach
        if len(api_cache) > CACHE_SIZE:
            # Remove oldest entries more efficiently (batch remove)
            cache_metrics['prunes'] += 1
            prune_count = max(1, int(CACHE_SIZE * 0.1))  # Remove 10% of cache entries
            
            # Sort by timestamp and remove oldest entries
            sorted_keys = sorted(api_cache.keys(), key=lambda k: api_cache[k]['timestamp'])
            for key in sorted_keys[:prune_count]:
                del api_cache[key]
            
            logger.debug(f"Cache pruned, removed {prune_count} oldest entries")
            
        return result
    return wrapper

# Don't cache transcription as audio files are usually unique
def transcribe_audio(file_path):
    """Transcribe audio to text using Groq's API"""
    start_time = time.time()
    logger.debug(f"Starting audio transcription")
    
    try:
        with open(file_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                file=audio_file,
                model="distil-whisper-large-v3-en"
            )
            
        elapsed = time.time() - start_time
        logger.debug(f"Transcription completed in {elapsed:.2f}s")
        return response.text
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise

@cache_api_response  # Apply caching to AI responses
def get_ai_response(transcription, image_data=None, conversation_history=None):
    """
    Get a response from the AI model using either text-only or image+text
    
    Args:
        transcription: The user's transcribed speech
        image_data: Optional base64 image data for vision model
        conversation_history: Optional conversation history
    """
    preprocessing_start = time.time()
    
    # Initialize conversation with system message if needed
    if not conversation_history or not isinstance(conversation_history, list) or len(conversation_history) == 0:
        conversation_history = [
            {"role": "system", "content": LUMI_SYSTEM_PROMPT}
        ]
    
    # Make sure there's a system message at the beginning
    if conversation_history[0]["role"] != "system":
        conversation_history.insert(0, {"role": "system", "content": LUMI_SYSTEM_PROMPT})
    
    # Create appropriate message format based on whether we have an image
    # Use smaller model for text-only queries, larger for multimodal
    has_image = bool(image_data)
    
    # Use a single model regardless of input type
    model = "meta-llama/llama-4-scout-17b-16e-instruct"

    # Prepare messages with optimized handling
    if has_image:
        # Extract the base64 part if it includes the data URL prefix - optimize string operations
        base64_image = image_data.split(',', 1)[1] if ',' in image_data else image_data
        
        # Log truncated image data for debugging
        logger.debug(f"Processing image data (truncated): {base64_image[:50]}... (length: {len(base64_image)})")
        
        # Create user message with image and text
        user_message = {
            "role": "user", 
            "content": [
                {"type": "text", "text": transcription},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                    },
                },
            ]
        }
        
        # Start with system prompt and add user message - avoid unnecessary list copying
        messages = [
            {"role": "system", "content": LUMI_SYSTEM_PROMPT},
        ]
        
        # Optimize history management to reduce processing time
        if conversation_history and len(conversation_history) > 2:
            # Take only the last few messages more efficiently
            history_limit = 6  # Maximum history messages
            
            # Skip the system message (index 0) and take the most recent messages only
            # More efficient than filtering and then slicing
            history_start = max(1, len(conversation_history) - history_limit)
            messages.extend(conversation_history[history_start:])
        
        # Always add the current user message at the end
        messages.append(user_message)
    else:
        # For text-only interactions, optimize with direct conversation history usage
        # Check if we need to add the user message to history
        if (not conversation_history or len(conversation_history) == 0 or 
            conversation_history[-1]["role"] != "user" or 
            conversation_history[-1]["content"] != transcription):
            # Avoid modifying the original conversation_history by creating a copy only when needed
            conversation_history = list(conversation_history)  # Shallow copy
            conversation_history.append({"role": "user", "content": transcription})
            
        # Use the prepared conversation history directly
        messages = conversation_history
    
    # Log preprocessing time for optimization analysis
    preprocessing_time = time.time() - preprocessing_start
    logger.debug(f"API request preprocessing completed in {preprocessing_time:.4f}s")
    
    # Start timing for API call
    start_time = time.time()
    logger.debug(f"Starting Groq API call for response generation")
    
    try:
        # Get response from Groq API with performance-optimized parameters
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_completion_tokens=512,  # Reduced token count for faster response
            top_p=1,
            stream=False,
            stop=None,
        )
        
        # Extract response text directly from the completion object
        response_text = completion.choices[0].message.content
        
        # Log timing information with more details
        elapsed = time.time() - start_time
        total_elapsed = elapsed + preprocessing_time
        logger.debug(f"Groq API response generated in {elapsed:.2f}s (total with preprocessing: {total_elapsed:.2f}s)")
        
        return response_text
    except Exception as e:
        # Enhanced error handling with more detailed diagnostics
        elapsed = time.time() - start_time
        error_type = type(e).__name__
        error_msg = str(e)
        
        logger.error(f"Groq API error after {elapsed:.2f}s: {error_type} - {error_msg}")
        
        # Provide a graceful fallback response based on error type
        if "rate limit" in error_msg.lower():
            return "I'm handling too many requests right now. Could you try again in a moment?"
        elif "timeout" in error_msg.lower():
            return "The response is taking longer than expected. Could you try a shorter or simpler question?"
        else:
            return "I'm having trouble processing that right now. Could you try again in a moment?"