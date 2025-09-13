# app.py
# Main FastAPI application for Twilio ConversationRelay Voice Assistant
# Handles incoming voice calls, TwiML generation, and WebSocket connections

import uvicorn
import json
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import Connect, ConversationRelay, VoiceResponse
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import Response
from utils import setup_logging
from conversation import conversationrelay, call_sid_to_session_id, cleanup_session_data
from constants import HUMAN_SERVICE_OPERATOR_SID, SERVICE_OPERATOR_SID, SERVICE_URL, WELCOME_GREETING, PORT, ENVIRONMENT, TWILIO_AUTH_TOKEN
from operators import operator_finished_webhook
from loaders import STT_HINTS

# Initialize logging and Twilio request validation
logger = setup_logging()
validator = RequestValidator(TWILIO_AUTH_TOKEN)

# Initialize FastAPI application
app = FastAPI(
    title="CoffeeMarket Voice Assistant",
    description="Twilio ConversationRelay powered voice assistant for CoffeeMarket",
    version="1.0.0"
)

def connect_customer(
    call_sid,
    from_number,
    to_number,
    intelligence_service_id
):
    """
    Generate TwiML response to connect customer to ConversationRelay.
    
    This function creates the TwiML that instructs Twilio to:
    1. Connect the call to our WebSocket endpoint
    2. Use ConversationRelay for AI-powered conversation
    3. Include welcome greeting and speech-to-text hints
    4. Set up session end webhook for call completion handling
    
    Args:
        call_sid (str): Unique identifier for the Twilio call
        from_number (str): Caller's phone number
        to_number (str): Called phone number (your Twilio number)
        intelligence_service_id (str): Twilio operator service ID (AI or human)
    
    Returns:
        Response: XML response containing TwiML instructions
    """
    try:
        # Validate required environment variables
        if not SERVICE_URL:
            logger.error("SERVICE_URL environment variable not set")
            raise HTTPException(status_code=500, detail="Service configuration error")
        
        logger.info(f"Incoming call - CallSid: {call_sid}, From: {from_number}, To: {to_number}")
        
        domain = SERVICE_URL
        ws_url = f"wss://{domain}/ws"
        
        response = VoiceResponse()
        connect = Connect(action=f"https://{SERVICE_URL}/session_end")
        cr = ConversationRelay(
            url=ws_url,
            welcomeGreeting=WELCOME_GREETING,
            hints=STT_HINTS,
            intelligence_service=intelligence_service_id,
        )

        connect.append(cr)
        response.append(connect)
        
        logger.info(f"Generated TwiML for CallSid {call_sid}: {str(response)}")
        
        return Response(content=str(response), media_type="application/xml")
    except Exception as e:
        logger.error(f"Error in voice_webhook: {e}")
        response = VoiceResponse()
        response.say("Sorry, we're experiencing technical difficulties. Please try again later.")
        return Response(content=str(response), media_type="application/xml")

async def voice_webhook(request: Request):
    """
    Handle incoming voice calls from Twilio.
    
    This is the main webhook endpoint that Twilio calls when someone
    dials your Twilio phone number. It extracts call information and
    generates TwiML to connect the caller to the AI assistant.
    
    Args:
        request (Request): FastAPI request object containing Twilio webhook data
    
    Returns:
        Response: TwiML XML response to connect caller to ConversationRelay
    """

    form_data = await request.form()
    call_sid = form_data.get('CallSid', 'Unknown')
    from_number = form_data.get('From', 'Unknown')
    to_number = form_data.get('To', 'Unknown')

    return connect_customer(
        call_sid=call_sid,
        from_number=from_number,
        to_number=to_number,
        intelligence_service_id=SERVICE_OPERATOR_SID
    )

async def session_end(request: Request):
    """
    Handle ConversationRelay session end events.
    
    Called by Twilio when a ConversationRelay session ends. This can happen when:
    1. The AI assistant ends the call
    2. The customer hangs up
    3. A handoff to human agent is requested
    
    If handoff data indicates a live agent transfer, this function will
    generate new TwiML to connect the customer to a human operator.
    
    Args:
        request (Request): FastAPI request containing session end data
    
    Returns:
        Response: Either empty response or TwiML for human agent connection
    """
    response = await request.form()
    call_sid = response.get("CallSid")
    
    # Clean up conversation data using call_sid to find session_id
    if call_sid and call_sid in call_sid_to_session_id:
        session_id = call_sid_to_session_id[call_sid]
        cleanup_session_data(session_id, call_sid)

    handoff_data = response.get("HandoffData")
    if handoff_data:    
        reason_block = json.loads(handoff_data)
        reason_code = reason_block.get("reasonCode")
        if reason_code == "live-agent-handoff":
            return connect_customer(
                call_sid=call_sid,
                from_number=response.get("From"),
                to_number=response.get("To"),
                intelligence_service_id=HUMAN_SERVICE_OPERATOR_SID
            )
    
    return Response(content="", media_type="text/plain", status_code=200)

async def validate_twilio_request(request: Request):
    """
    Validate that incoming requests are actually from Twilio.
    
    Uses Twilio's request validation to verify the X-Twilio-Signature header.
    This prevents unauthorized access to webhook endpoints by ensuring
    requests originate from Twilio's servers.
    
    Args:
        request (Request): FastAPI request object
    
    Returns:
        Response: 403 Forbidden if validation fails, None if valid
    """
    twilio_signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    form_data = await request.form()
    params = dict(form_data)

    if not validator.validate(url, params, twilio_signature):
        return Response("Unauthorized", status_code=status.HTTP_403_FORBIDDEN)

app.add_api_route("/start", voice_webhook, methods=["POST"], dependencies=[Depends(validate_twilio_request)])
app.add_api_route("/operator_output", operator_finished_webhook, methods=["POST"], dependencies=[Depends(validate_twilio_request)])
app.add_api_route("/session_end", session_end, methods=["POST"], dependencies=[Depends(validate_twilio_request)])
app.add_websocket_route("/ws", conversationrelay)

if __name__ == "__main__":
    port = int(PORT)
    is_production = ENVIRONMENT == "production"
    
    if is_production:
        uvicorn.run(
            "app:app", 
            host="0.0.0.0", 
            port=port, 
            log_level="info",
            access_log=True
        )
    else:
        uvicorn.run(
            "app:app", 
            host="0.0.0.0", 
            port=port, 
            reload=True,
            log_level="debug"
        )
