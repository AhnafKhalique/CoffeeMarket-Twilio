"""Agent callback handlers for streaming and call management."""
import time
import threading
from langchain.callbacks.base import BaseCallbackHandler

class StreamingCallbackHandler(BaseCallbackHandler):
    """Handles LLM streaming with interstitial phrases during tool execution.
    
    Manages token streaming, tool execution timing, and automatic interstitial
    phrase injection to provide natural conversation flow during processing delays.
    """
    
    def __init__(self):
        """Initialize the streaming handler with interstitial configuration."""
        self.buffer = ""
        self.tokens = []
        self.tool_executing = False
        self.tool_start_time = None
        self.call_end_detected = False
        self.handoff_detected = False
        self.current_tool = None  # Track current executing tool
        self.interstitial_phrases = [
            "Let me check that for you...",
            "One moment please...",
            "I'm looking into that...",
            "Just a second...",
            "Let me find that information...",
            "Give me just a moment..."
        ]
        # Tools that should NOT trigger interstitials (call ending scenarios)
        self.no_interstitial_tools = [
            "end_call",
            "escalate_to_human_agent"
        ]
        self.phrase_index = 0
        self.interstitial_sent = False
        self.interstitial_ready = False
        self.sent_interstitials = []  # Track sent interstitials for conversation history
        
    def on_llm_new_token(self, token: str, **kwargs):
        """Handle new tokens from LLM streaming.
        
        Args:
            token (str): New token from LLM
        """
        self.buffer += token
        self.tokens.append(token)
        print(f"[STREAMING] Token received: '{token}' (total tokens: {len(self.tokens)}) - timestamp: {time.time()}")
        
        # Cancel interstitial timer when LLM tokens start arriving
        if hasattr(self, 'interstitial_timer') and self.interstitial_timer.is_alive():
            self.interstitial_timer.cancel()
            print(f"[STREAMING] Cancelled interstitial timer - LLM tokens arriving")
        
        # Reset interstitial state when actual content begins
        if self.interstitial_sent and token.strip():
            self.interstitial_sent = False
        
    def on_llm_start(self, serialized, prompts, **kwargs):
        """Handle LLM processing start.
        
        Args:
            serialized: Serialized LLM configuration
            prompts: Input prompts for LLM
        """
        self.llm_start_time = time.time()
        self.interstitial_sent = False
        self.interstitial_ready = False
        print(f"[STREAMING] LLM started - interstitials will be handled by tool calls")
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        """Handle tool execution start and manage interstitial timing.
        
        Args:
            serialized: Serialized tool configuration
            input_str: Tool input parameters
        """
        tool_name = serialized.get("name", "unknown")
        self.tool_executing = True
        self.tool_start_time = time.time()
        self.current_tool = tool_name
        
        if tool_name == "end_call":
            self.call_end_detected = True
            print(f"[STREAMING] end_call tool invoked - call will end")
        elif tool_name == "escalate_to_human_agent":
            self.handoff_detected = True
            print(f"[STREAMING] escalate_to_human_agent tool invoked - handoff will occur")
        else:
            print(f"[STREAMING] Tool {tool_name} started")
            # Start 0.4s timer for interstitial (except call-ending tools)
            if tool_name not in self.no_interstitial_tools:
                if not hasattr(self, 'interstitial_timer') or not self.interstitial_timer.is_alive():
                    self.interstitial_timer = threading.Timer(0.4, self._trigger_interstitial)
                    self.interstitial_timer.start()
                    print(f"[STREAMING] Timer started for tool interstitial")
        
    def on_llm_end(self, response, **kwargs):
        """Handle LLM processing completion.
        
        Args:
            response: LLM response data
        """
        # Cancel pending interstitial timer on LLM completion
        if hasattr(self, 'interstitial_timer') and self.interstitial_timer.is_alive():
            self.interstitial_timer.cancel()
        print(f"[STREAMING] LLM completed")
    
    def on_tool_end(self, output, **kwargs):
        """Handle tool execution completion.
        
        Args:
            output: Tool execution output
        """
        self.tool_executing = False
        self.tool_start_time = None
        self.current_tool = None
        
        if self.call_end_detected:
            print(f"[STREAMING] end_call tool completed with output: {output}")
        elif self.handoff_detected:
            print(f"[STREAMING] escalate_to_human_agent tool completed with output: {output}")
    
    def _trigger_interstitial(self):
        """Timer callback to trigger interstitial phrase after delay."""
        if not self.interstitial_sent and not self.interstitial_ready:
            # Skip interstitials when call is ending or transferring
            if self.call_end_detected or self.handoff_detected:
                print(f"[STREAMING] Timer triggered but skipping - call ending scenario detected")
                return
            
            self.interstitial_ready = True
            print(f"[STREAMING] Timer triggered - interstitial ready")
        
    def get_next_interstitial(self):
        """Get next interstitial phrase using round-robin selection.
        
        Returns:
            str: Next interstitial phrase from the rotation
        """
        phrase = self.interstitial_phrases[self.phrase_index]
        self.phrase_index = (self.phrase_index + 1) % len(self.interstitial_phrases)
        return phrase
        
    def should_send_interstitial(self):
        """Check if an interstitial phrase should be sent.
        
        Returns:
            bool: True if interstitial should be sent based on timing and state
        """
        # Send if timer triggered and not in call-ending scenario
        should_send = (self.interstitial_ready and 
                      not self.interstitial_sent and 
                      not self.call_end_detected and 
                      not self.handoff_detected)
        
        if self.interstitial_ready:
            print(f"[STREAMING] Interstitial check: ready={self.interstitial_ready}, sent={self.interstitial_sent}, tokens={len(self.tokens)}, result={should_send}")
        
        return should_send
