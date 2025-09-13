"""Handles Twilio Intelligence operator webhooks and result processing."""
from pathlib import Path
from twilio.rest import Client
from fastapi import Request
from constants import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
from utils import setup_logging

logger = setup_logging()

async def operator_finished_webhook(request: Request):
    """Handle Twilio Intelligence operator completion webhook.
    
    Processes operator results from AgentImprovement and HumanAgent
    operators, saving their text generation outputs to organized files.
    
    Args:
        request (Request): FastAPI request containing webhook payload
    """
    logger.info("Operator webhook call")
    response = await request.json()
    logger.info("Response: ", response)

    transcript_id = response.get('transcript_sid')

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    transcript = client.intelligence.v2.transcripts(transcript_id).fetch()
    operator_results = transcript.operator_results.list()

    # Process each operator result
    for res in operator_results:
        if res.name == "AgentImprovement" or res.name == "HumanAgent":
            text_results = res.text_generation_results

            # Map operator names to directory structure
            dir_name = None
            if res.name == "AgentImprovement": dir_name = "agent_improvement"
            if res.name == "HumanAgent": dir_name = "agent_handoff"

            if text_results:
                # Create directory if it doesn't exist
                output_dir = Path('operators') / dir_name / transcript_id
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Create the file path safely
                output_file = output_dir / f'raw_text.txt'

                final_result = text_results["result"]
                
                with open(output_file, "w") as f:
                    f.write(final_result)
                
                # try:
                #     jsoned = final_result
                #     jsoned = jsoned.replace("\\n", "")
                #     jsoned = json.loads(jsoned)
                #     output_file = output_dir / f'json_cleaned_text.txt'
                #     with open(output_file, "w") as f:
                #         json.dump(jsoned, f, indent=4)
                # except Exception as e:
                #     logger.error(f"Error parsing JSON: {e}")
                #     continue