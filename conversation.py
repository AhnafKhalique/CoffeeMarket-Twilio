# Handles Twilio ConversationRelay WebSocket connections and message processing
import json
import asyncio
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
from utils import setup_logging, setup_session_logging, setup_conversation_logging, log_conversation_turn, setup_session_conversation_logging
from llm_handler import llm_call_response_streaming
from loaders import SYSTEM_PROMPT
from agent_manager.utils import redact_conversation_history

# Logging setup
logger = setup_logging()
session_logger = setup_session_logging()
conversation_logger = setup_conversation_logging()

# Session management
session_state: Dict[str, Dict] = {}  # Session data by session_id
connections: Dict[str, WebSocket] = {}  # Active WebSocket connections
session_conversation_loggers: Dict[str, any] = {}  # Per-session loggers
conversation_histories: Dict[str, list] = {}  # Chat history by session
call_sid_to_session_id: Dict[str, str] = {}  # Call SID to session mapping

def cleanup_session_data(session_id: str, call_sid: str = None):
    """
    Clean up session data when call ends.
    
    Removes all session-related data including WebSocket connections,
    conversation loggers, and session state mappings.
    
    Args:
        session_id (str): Unique session identifier
        call_sid (str, optional): Twilio call SID for additional cleanup
    """
    if not session_id:
        return
    
    # Calculate session duration if available
    if session_id in session_state:
        session_duration = asyncio.get_event_loop().time() - session_state[session_id].get('start_time', 0)
        logger.info(f"Session {session_id} ended after {session_duration:.2f} seconds")
        
        # Get call_sid from session_state if not provided
        if not call_sid:
            call_sid = session_state[session_id].get('call_sid')
        
        del session_state[session_id]
    
    # Clean up other session data
    if session_id in connections:
        del connections[session_id]
    if session_id in session_conversation_loggers:
        del session_conversation_loggers[session_id]
    
    # Remove the mapping if call_sid is available
    if call_sid and call_sid in call_sid_to_session_id:
        del call_sid_to_session_id[call_sid]
    
    logger.info(f"Cleaned up session data for {session_id}" + (f" (call_sid: {call_sid})" if call_sid else ""))

async def conversationrelay(websocket: WebSocket):
    """
    Handle Twilio ConversationRelay WebSocket messages.
    
    Main WebSocket handler that processes incoming messages from Twilio's
    ConversationRelay service. Manages session setup, user voice prompts,
    interruptions, and error handling.
    
    Args:
        websocket (WebSocket): Active WebSocket connection from Twilio
    """
    await websocket.accept()
    session_id: Optional[str] = None
    
    logger.info("WebSocket connection established")

    try:
        while True:
            msg = await websocket.receive_text()
            logger.debug(f"Received raw message: {msg}")
            
            try:
                data = json.loads(msg)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                continue
                
            typ = data.get("type")
            logger.debug(f"Message type: {typ}")

            # Initialize session on first connection
            if typ == "setup":
                session_id = data.get("sessionId")
                call_sid = data.get("callSid")
                
                if not session_id:
                    logger.error("Setup message missing sessionId")
                    continue
                    
                # Store connection and session state
                connections[session_id] = websocket
                session_state[session_id] = {
                    'call_sid': call_sid,
                    'call_state': 'on_call',
                    'start_time': asyncio.get_event_loop().time()
                }
                call_sid_to_session_id[call_sid] = session_id

                # Setup per-session conversation logger
                session_conv_logger = setup_session_conversation_logging(session_id, call_sid)
                session_conversation_loggers[session_id] = session_conv_logger
                
                logger.info(f"Session {session_id} initialized with call_sid {call_sid}")
                session_logger.info(
                    f"Session started",
                    extra={'session_id': session_id, 'call_sid': call_sid}
                )
                
                # Log conversation start
                log_conversation_turn(session_id, call_sid, "SYSTEM", "Conversation started", conversation_logger)
                session_conv_logger.info("Conversation started", extra={'speaker': 'SYSTEM'})
                
            # Handle user voice input
            elif typ == "prompt":
                if not session_id:
                    logger.error("Received prompt without session setup")
                    continue
                    
                voice_prompt = data.get("voicePrompt", "")
                lang = data.get("lang", "en-US")

                if "en" not in lang:
                    logger.warning(f"Unsupported language: {lang}")
                    await websocket.send_json({
                        "type": "text",
                        "token": "I'm sorry, I don't understand that language. Please try again in English.",
                        "lang": "en-US",
                        "last": True
                    })
                    continue
                
                # Validate input
                if not voice_prompt.strip():
                    logger.warning(f"Empty voice prompt received for session {session_id}")
                    continue
                
                text = voice_prompt.strip()
                logger.info(f"Session {session_id} received prompt: '{text}'")
                
                # Log user input and process with AI agent
                call_sid = session_state.get(session_id, {}).get('call_sid', 'unknown')
                session_logger.info(
                    f"Customer input: '{text}'",
                    extra={'session_id': session_id, 'call_sid': call_sid}
                )
                log_conversation_turn(session_id, call_sid, "USER", text, conversation_logger)
                if session_id in session_conversation_loggers:
                    session_conversation_loggers[session_id].info(text, extra={'speaker': 'USER'})
                    await llm_call_response_streaming(websocket, session_id, text, session_state, session_logger, SYSTEM_PROMPT, conversation_histories, conversation_logger, session_conversation_loggers.get(session_id), session_state.get(session_id))

            # Handle user interruptions
            elif typ == "interrupt":
                if not session_id:
                    logger.error("Received interrupt without session setup")
                    continue
                
                utterance = data.get("utteranceUntilInterrupt", "")
                duration_ms = data.get("durationUntilInterruptMs", 0)

                logger.info(f"Session {session_id} interrupted. Utterance: '{utterance}', Duration: {duration_ms}ms")
                
                # Log the interruption
                call_sid = session_state.get(session_id, {}).get('call_sid', 'unknown')
                session_logger.info(
                    f"User interrupted. Spoken: '{utterance}', Duration: {duration_ms}ms",
                    extra={'session_id': session_id, 'call_sid': call_sid}
                )

                redaction_result = redact_conversation_history(session_id, utterance, conversation_histories)
                
                if redaction_result["success"]:
                    logger.info(f"Conversation history redacted for session {session_id}")
                else:
                    logger.warning(f"Failed to redact conversation history for session {session_id}: {redaction_result['message']}")

            # Handle error messages
            elif typ == "error":
                logger.error(f"Error received for session {session_id}: {data.get('description')}")
            else:
                logger.warning(f"Unknown message type '{typ}' from session {session_id}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        # Try to send error message if connection is still active
        try:
            await websocket.send_json({
                "type": "text",
                "token": "I'm sorry, there was a technical issue. Please try calling again.",
                "lang": "en-US",
                "last": True
            })
        except:
            pass  # Connection might be closed

    finally:
        # Clean up session data
        if session_id:
            cleanup_session_data(session_id)