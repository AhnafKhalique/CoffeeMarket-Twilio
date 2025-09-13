"""Utility functions for logging configuration and conversation tracking."""
import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure logging with both file and console output.
    
    Sets up rotating file handlers for application logs and errors,
    plus console output for real-time monitoring.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Get root logger
    root_logger = logging.getLogger()
    
    # Check if handlers are already configured to prevent duplicates
    if root_logger.handlers:
        return logging.getLogger(__name__)
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create file handler with rotation
    file_handler = RotatingFileHandler(
        'logs/coffeemarket_app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Create separate error log for critical issues
    error_handler = RotatingFileHandler(
        'logs/coffeemarket_errors.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    return logging.getLogger(__name__)

def setup_session_logging():
    """Setup separate logger for customer session tracking.
    
    Creates dedicated logger for session events with custom formatting
    that includes session_id and call_sid in log entries.
    
    Returns:
        logging.Logger: Session-specific logger instance
    """
    session_logger = logging.getLogger('session')
    
    # Check if handlers are already configured to prevent duplicates
    if session_logger.handlers:
        return session_logger
    
    session_handler = RotatingFileHandler(
        'logs/customer_sessions.log',
        maxBytes=20*1024*1024,  # 20MB
        backupCount=10,
        encoding='utf-8'
    )
    
    # Custom format includes session and call identifiers
    session_formatter = logging.Formatter(
        '%(asctime)s - SESSION_ID:%(session_id)s - CALL_SID:%(call_sid)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    session_handler.setFormatter(session_formatter)
    session_logger.addHandler(session_handler)
    session_logger.setLevel(logging.INFO)
    session_logger.propagate = False  # Don't propagate to root logger
    
    return session_logger

def setup_conversation_logging():
    """Setup separate logger for conversation history tracking.
    
    Creates dedicated logger for conversation turns with speaker
    identification and larger file rotation limits.
    
    Returns:
        logging.Logger: Conversation-specific logger instance
    """
    conversation_logger = logging.getLogger('conversation')
    
    # Check if handlers are already configured to prevent duplicates
    if conversation_logger.handlers:
        return conversation_logger
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    conversation_handler = RotatingFileHandler(
        'logs/conversation_history.log',
        maxBytes=50*1024*1024,  # 50MB
        backupCount=20,
        encoding='utf-8'
    )
    
    # Custom format includes speaker identification
    conversation_formatter = logging.Formatter(
        '%(asctime)s - SESSION:%(session_id)s - CALL:%(call_sid)s - %(speaker)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    conversation_handler.setFormatter(conversation_formatter)
    conversation_logger.addHandler(conversation_handler)
    conversation_logger.setLevel(logging.INFO)
    conversation_logger.propagate = False  # Don't propagate to root logger
    
    return conversation_logger

def log_conversation_turn(session_id, call_sid, speaker, message, conversation_logger):
    """Log a single conversation turn.
    
    Args:
        session_id (str): Unique session identifier
        call_sid (str): Twilio call SID
        speaker (str): Speaker identifier (USER/AGENT)
        message (str): Conversation message content
        conversation_logger: Logger instance for conversation tracking
    """
    conversation_logger.info(
        message,
        extra={
            'session_id': session_id,
            'call_sid': call_sid,
            'speaker': speaker
        }
    )

def setup_session_conversation_logging(session_id, call_sid):
    """Setup individual conversation log file for a specific session.
    
    Creates a dedicated log file for each conversation session
    for easy individual session review and debugging.
    
    Args:
        session_id (str): Unique session identifier
        call_sid (str): Twilio call SID
        
    Returns:
        logging.Logger: Session-specific conversation logger
    """
    session_conv_logger = logging.getLogger(f'conversation_{session_id}')
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs/conversations', exist_ok=True)
    
    session_conv_handler = logging.FileHandler(
        f'logs/conversations/conversation_{session_id}_{call_sid}.log',
        encoding='utf-8'
    )
    
    # Simplified format for per-session conversation files
    session_conv_formatter = logging.Formatter(
        '%(asctime)s - %(speaker)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    session_conv_handler.setFormatter(session_conv_formatter)
    session_conv_logger.addHandler(session_conv_handler)
    session_conv_logger.setLevel(logging.INFO)
    session_conv_logger.propagate = False
    
    return session_conv_logger
