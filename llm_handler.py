"""Handles streaming LLM responses and WebSocket communication with Twilio."""
import asyncio
from typing import Dict
from fastapi import WebSocket
from agent import  generate_agent_response_stream
from utils import setup_logging
from utils import log_conversation_turn

logger = setup_logging()

async def end_call(websocket: WebSocket):
    """End the call gracefully.
    
    Sends hangup message to Twilio ConversationRelay to terminate
    the call connection.
    
    Args:
        websocket (WebSocket): Active WebSocket connection to Twilio
    """
    await websocket.send_json({
        "type": "end",
    })

async def human_agent_handoff(websocket: WebSocket):
    """Handle handoff to human agent.
    
    Sends handoff message to Twilio ConversationRelay to transfer
    the customer to a human agent.
    
    Args:
        websocket (WebSocket): Active WebSocket connection to Twilio
    """
    await websocket.send_json({
        "type": "end",
        "handoffData": "{\"reasonCode\":\"live-agent-handoff\", \"reason\":\"Escalation to Human Agent\"}"
    })

async def llm_call_response_streaming(websocket: WebSocket, session_id: str, text: str, flow_state: Dict, session_logger, system_prompt, conversation_histories, conversation_logger=None, session_conv_logger=None, session_state=None):
    """Stream LLM response to WebSocket with real-time token delivery.
    
    Processes user input through the AI agent and streams the response
    back to Twilio. Handles interstitials, call endings, and human handoffs.
    
    Args:
        websocket (WebSocket): Active WebSocket connection to Twilio
        session_id (str): Unique session identifier
        text (str): User input to process
        flow_state (Dict): Current session state data
        session_logger: Logger for session-specific events
        system_prompt (str): System instructions for the agent
        conversation_histories (Dict): Session conversation histories
        conversation_logger: Logger for conversation events
        session_conv_logger: Per-session conversation logger
        session_state (Dict): Additional session metadata
    """
    try:
        call_sid = flow_state.get(session_id, {}).get('call_sid', 'unknown')
        full_response_parts = []
        should_end_call = False
        should_handoff = False
        end_call_logged = False
        handoff_logged = False
        
        # Buffer tokens for optimal streaming
        token_buffer = ""
        
        async for chunk_data in generate_agent_response_stream(session_id, text, system_prompt, conversation_histories):
            chunk = chunk_data["chunk"]
            is_final = chunk_data["is_final"]
            chunk_should_end_call = chunk_data["should_end_call"]
            chunk_should_handoff = chunk_data.get("should_handoff", False)
            is_interstitial = chunk_data.get("is_interstitial", False)
            
            # Send quick responses immediately
            if is_interstitial:
                await websocket.send_json({
                    "type": "text",
                    "token": chunk,
                    "lang": "en-US",
                    "last": True
                })
                logger.debug(f"Sent interstitial to session {session_id}: '{chunk}'")
                continue
            
            full_response_parts.append(chunk)
            token_buffer += chunk
            
            # Track call state changes
            if chunk_should_end_call and not end_call_logged:
                should_end_call = True
                end_call_logged = True
                logger.info(f"DEBUG: should_end_call detected for session {session_id}")
            if chunk_should_handoff and not handoff_logged:
                should_handoff = True
                handoff_logged = True
                logger.info(f"DEBUG: should_handoff detected for session {session_id}")
            
            # Batch tokens for natural speech
            words_in_buffer = len(token_buffer.strip().split())
            
            # Send on word count or punctuation
            should_send = (
                is_final or 
                words_in_buffer >= 3 or 
                chunk.strip().endswith(('.', '!', '?', ',', ';', ':'))
            )
            
            if should_send and token_buffer.strip():
                # Validate chunk length
                send_chunk = token_buffer
                if len(send_chunk) > 200:
                    send_chunk = send_chunk[:197] + "..."
                    logger.warning(f"Chunk truncated for session {session_id}")
                
                # Stream to ConversationRelay
                await websocket.send_json({
                    "type": "text",
                    "token": send_chunk,
                    "lang": "en-US",
                    "last": False  # Never set last=True here, handle it separately - cannot properly due to Langchain
                })
                
                logger.debug(f"Sent chunk to session {session_id}: '{send_chunk.strip()}' (should_end_call: {chunk_should_end_call})")
                
                # Clear buffer
                token_buffer = ""
        
        # Send remaining tokens and completion
        if token_buffer.strip():
            # Send remaining tokens
            await websocket.send_json({
                "type": "text",
                "token": token_buffer,
                "lang": "en-US",
                "last": False
            })
            logger.debug(f"Sent final buffered tokens to session {session_id}: '{token_buffer.strip()}'")
        
        # Send final completion message
        await websocket.send_json({
            "type": "text",
            "token": "",
            "lang": "en-US",
            "last": True
        })
        logger.debug(f"Sent final completion message to session {session_id}")
        
        # Log complete response
        full_response = "".join(full_response_parts)
        logger.info(f"Sent streaming response to session {session_id}: '{full_response[:100]}...'")
        
        # Fallback handoff detection - check for marker in response text
        if not should_handoff and "HANDOFF_HUMAN:" in full_response:
            should_handoff = True
            # Extract the message part after the marker
            handoff_parts = full_response.split("HANDOFF_HUMAN:", 1)
            if len(handoff_parts) > 1:
                full_response = handoff_parts[1].strip()
                logger.info(f"Human agent handoff detected via string parsing for session {session_id}")
        elif should_handoff:
            logger.info(f"Human agent handoff detected via streaming for session {session_id}")
            # Also clean the response if it contains the marker
            if "HANDOFF_HUMAN:" in full_response:
                handoff_parts = full_response.split("HANDOFF_HUMAN:", 1)
                if len(handoff_parts) > 1:
                    full_response = handoff_parts[1].strip()
        
        session_logger.info(
            f"AI streaming response: '{full_response}' (Call ending: {should_end_call}, Handoff: {should_handoff})",
            extra={'session_id': session_id, 'call_sid': call_sid}
        )
        
        # Log conversation turn for agent response
        if conversation_logger:
            log_conversation_turn(session_id, call_sid, "AGENT", full_response, conversation_logger)
        
        if session_conv_logger:
            session_conv_logger.info(full_response, extra={'speaker': 'AGENT'})
        
        # Execute call actions with speech timing
        if should_handoff:
            logger.info(f"Initiating human agent handoff for session {session_id}")
            session_logger.info(
                "Escalating to human agent",
                extra={'session_id': session_id, 'call_sid': call_sid}
            )
            # Calculate appropriate delay based on message length
            word_count = len(full_response.split())
            speech_time = max(1.0, word_count * 0.4)  # 0.4 seconds per word for natural speech
            logger.info(f"Waiting {speech_time:.1f} seconds for {word_count} words before handoff")
            await asyncio.sleep(speech_time)
            await human_agent_handoff(websocket)
        elif should_end_call:
            logger.info(f"Ending call for session {session_id}")
            session_logger.info(
                "Call ended by AI assistant",
                extra={'session_id': session_id, 'call_sid': call_sid}
            )
            # Calculate appropriate delay based on message length
            word_count = len(full_response.split())
            speech_time = max(1.0, word_count * 0.4)  # 0.4 seconds per word for natural speech
            logger.info(f"Waiting {speech_time:.1f} seconds for {word_count} words to complete")
            await asyncio.sleep(speech_time)
            await end_call(websocket)
        
    except Exception as e:
        logger.error(f"Error generating streaming LLM response for session {session_id}: {e}")
        # Send fallback response
        await websocket.send_json({
            "type": "text",
            "token": "I'm sorry, I'm having trouble processing your request right now. Please try again.",
            "lang": "en-US",
            "last": True
        })
