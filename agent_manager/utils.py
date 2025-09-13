# Agent utility functions for conversation management
def redact_conversation_history(session_id, utterance_until_interrupt, conversation_histories):
    """
    Redact unspoken text from conversation history for meaningful interruptions
    
    Args:
        session_id: Session identifier
        utterance_until_interrupt: Text that was actually spoken before interruption
        conversation_histories: Dict of conversation histories to update
    
    Returns:
        dict: Information about the redaction
    """
    if session_id not in conversation_histories or not conversation_histories[session_id]:
        return {"success": False, "message": "No conversation history found"}
    
    history = conversation_histories[session_id]
    
    # Find the most recent assistant message (skip interstitials)
    for i in range(len(history) - 1, -1, -1):
        if history[i].get("role") == "assistant":
            # Skip interstitials - they can't be meaningfully redacted against user speech
            if history[i].get("type") == "interstitial":
                print(f"[REDACTION] Skipping interstitial message: '{history[i]['content']}'")
                continue
                
            full_response = history[i]["content"]
            
            # Find what portion was actually spoken
            spoken_portion = find_spoken_portion(full_response, utterance_until_interrupt)
            
            if spoken_portion.strip():
                # Update with spoken portion only
                redacted_text = full_response[len(spoken_portion):] if len(spoken_portion) < len(full_response) else ""
                history[i]["content"] = spoken_portion
                print(f"[REDACTION] Session {session_id}:")
                print(f"  Original text: '{full_response}'")
                print(f"  Spoken portion: '{spoken_portion}'")
                print(f"  Redacted text: '{redacted_text}'")
            else:
                # Remove the assistant message entirely if nothing was spoken
                history.pop(i)
                print(f"[REDACTION] Session {session_id}:")
                print(f"  Completely removed unspoken message: '{full_response}'")
            
            return {
                "success": True,
                "message": "Conversation history redacted",
                "spoken_text": spoken_portion,
                "original_text": full_response,
                "redacted_text": full_response[len(spoken_portion):] if spoken_portion else full_response
            }
    
    return {"success": False, "message": "No assistant message found to redact"}


def find_spoken_portion(full_text, utterance_until_interrupt):
    """
    Find the portion of text that was actually spoken based on the utterance.
    """
    if not utterance_until_interrupt or not full_text:
        return ""
    
    # Convert both to lowercase for comparison
    full_lower = full_text.lower()
    utterance_lower = utterance_until_interrupt.lower()
    
    print(f"[REDACTION] Matching utterance: '{utterance_lower}' against text: '{full_lower}'")
    
    # Try exact substring match first
    if utterance_lower in full_lower:
        # Find the end position of the utterance in the original text
        start_pos = full_lower.find(utterance_lower)
        end_pos = start_pos + len(utterance_lower)
        result = full_text[:end_pos]
        print(f"[REDACTION] Exact match found - returning: '{result}'")
        return result
    
    # Split into words for word-by-word matching
    full_words = full_lower.split()
    utterance_words = utterance_lower.split()
    original_words = full_text.split()
    
    if not utterance_words or not full_words:
        return ""
    
    # Find how many words from the end of utterance match the text
    best_match_pos = 0
    for end_pos in range(1, len(full_words) + 1):
        text_words = full_words[:end_pos]
        
        # Check if the utterance ends with the same words as this text segment
        min_len = min(len(utterance_words), len(text_words))
        match_count = 0
        
        for i in range(min_len):
            if utterance_words[-(i+1)] == text_words[-(i+1)]:
                match_count += 1
            else:
                break
        
        # If we matched all utterance words, this is our best position
        if match_count == len(utterance_words):
            best_match_pos = end_pos
            break
        elif match_count > 0:
            best_match_pos = end_pos
    
    if best_match_pos > 0:
        result = ' '.join(original_words[:best_match_pos])
        print(f"[REDACTION] Word match found at position {best_match_pos} - returning: '{result}'")
        return result
    
    print(f"[REDACTION] Warning: Could not match utterance '{utterance_until_interrupt}' to generated text '{full_text}'")
    return ""
