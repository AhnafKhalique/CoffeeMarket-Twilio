import time
import threading
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from constants import AZURE_ENDPOINT, AZURE_API_KEY, AZURE_DEPLOYMENT, AZURE_API_VERSION
from agent_manager.handlers import StreamingCallbackHandler
from agent_manager.tools import (
    check_stock, 
    end_call, 
    get_coffeemart_info, 
    get_delivery_status, 
    escalate_to_human_agent, 
    get_coffee_recommendations
)

# Session storage for persistent agent instances with memory
AGENT_SESSIONS = {}

def create_agent(system_prompt, memory=None):
    """
    Create the LangChain agent with tools and optional memory.
    
    Sets up Azure OpenAI LLM, available tools, and chat prompt template.
    Supports both stateless and stateful (with memory) configurations.
    
    Args:
        system_prompt (str): System instructions for the agent
        memory (ConversationBufferWindowMemory, optional): Chat history memory
        
    Returns:
        AgentExecutor: Configured LangChain agent executor
    """
    clean_endpoint = AZURE_ENDPOINT.replace("/openai/v1/", "").rstrip("/")
    llm = AzureChatOpenAI(
        azure_endpoint=clean_endpoint,
        api_key=AZURE_API_KEY,
        azure_deployment=AZURE_DEPLOYMENT,
        api_version=AZURE_API_VERSION,
        streaming=True
    )
    
    tools = [check_stock, end_call, get_coffeemart_info, get_delivery_status, get_coffee_recommendations, escalate_to_human_agent]
    
    # Configure prompt template based on memory usage
    if memory:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
    else:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent, 
        tools=tools, 
        memory=memory,
        verbose=True, 
        stream_runnable=True
    )

def run_agent(agent_executor, conversation_context, stream_handler, response_container, exception_container):
    """
    Run the agent executor in a separate thread.
    
    Args:
        agent_executor (AgentExecutor): The LangChain agent to execute
        conversation_context (str): User input to process
        stream_handler (StreamingCallbackHandler): Callback handler for streaming
        response_container (dict): Container to store successful response
        exception_container (dict): Container to store any exceptions
    """
    try:
        response = agent_executor.invoke(
            {"input": conversation_context},
            {"callbacks": [stream_handler]}
        )
        response_container['result'] = response
    except Exception as e:
        exception_container['error'] = e

async def generate_agent_response_stream(session_id, user_message, system_prompt, conversation_histories):
    """
    Generate a streaming response using LangChain agent with tools.
    
    Manages session-specific agents with memory, handles tool execution,
    and streams responses with interstitial support.
    
    Args:
        session_id (str): Unique session identifier
        user_message (str): User input to process
        system_prompt (str): System instructions for the agent
        conversation_histories (dict): Session conversation histories
        
    Yields:
        dict: Streaming response chunks with metadata
    """
    # Initialize conversation history if it doesn't exist
    if session_id not in conversation_histories:
        conversation_histories[session_id] = []
    
    # Add user message to history
    conversation_histories[session_id].append({"role": "user", "content": user_message})
    
    try:
        # Get or create session-specific agent with memory
        if session_id not in AGENT_SESSIONS:
            # Create memory for this session (keep last 10 exchanges)
            memory = ConversationBufferWindowMemory(
                k=10,
                memory_key="chat_history",
                return_messages=True
            )
            AGENT_SESSIONS[session_id] = {
                'handler': StreamingCallbackHandler(),
                'agent': create_agent(system_prompt, memory),
                'memory': memory
            }
        
        stream_handler = AGENT_SESSIONS[session_id]['handler']
        agent_executor = AGENT_SESSIONS[session_id]['agent']
        
        # Reset handler state for new request (preserve phrase_index for round-robin)
        stream_handler.buffer = ""
        stream_handler.tokens = []
        stream_handler.tool_executing = False
        stream_handler.call_end_detected = False
        stream_handler.handoff_detected = False
        stream_handler.interstitial_sent = False
        stream_handler.interstitial_ready = False
        stream_handler.sent_interstitials = []
        # Cancel any existing timer to prevent multiple interstitials
        if hasattr(stream_handler, 'interstitial_timer') and stream_handler.interstitial_timer.is_alive():
            stream_handler.interstitial_timer.cancel()
        
        # With memory, we just pass the current user message
        # The agent's memory will handle conversation history automatically
        conversation_context = user_message
        
        # Start agent execution in background
        response_container = {}
        exception_container = {}
        
        # Execute agent in background thread
        thread = threading.Thread(target=run_agent, args=(agent_executor, conversation_context, stream_handler, response_container, exception_container))
        thread.start()
        
        # Stream tokens as they arrive with interstitial support
        last_token_count = 0
        interstitial_sent_this_response = False
        
        while thread.is_alive() or last_token_count < len(stream_handler.tokens):
            current_token_count = len(stream_handler.tokens)
            
            # Check if we need to send an interstitial phrase (only once per response)
            if stream_handler.should_send_interstitial() and not interstitial_sent_this_response:
                interstitial = stream_handler.get_next_interstitial()
                stream_handler.interstitial_sent = True
                stream_handler.interstitial_ready = False  # Reset flag
                interstitial_sent_this_response = True  # Mark as sent for this response
                stream_handler.sent_interstitials.append(interstitial)  # Track for conversation history
                print(f"[STREAMING] Sending interstitial: {interstitial}")
                yield {
                    "chunk": interstitial,
                    "is_final": True,
                    "should_end_call": False,
                    "should_handoff": False,
                    "is_interstitial": True
                }
            
            # Yield new tokens
            for i in range(last_token_count, current_token_count):
                token = stream_handler.tokens[i]
                yield {
                    "chunk": token,
                    "is_final": False,
                    "should_end_call": stream_handler.call_end_detected,
                    "should_handoff": stream_handler.handoff_detected,
                    "is_interstitial": False
                }
            
            last_token_count = current_token_count
            
            time.sleep(0.001)
        
        # Wait for thread to complete
        thread.join()
        
        # Check for exceptions
        if 'error' in exception_container:
            raise exception_container['error']
        
        # Final token to indicate completion
        full_response = "".join(stream_handler.tokens)
        
        # Process response and update conversation history
        if stream_handler.call_end_detected and "CALL_END:" in full_response:
            clean_response = full_response.split("CALL_END:", 1)[1].strip()
            conversation_histories[session_id].append({"role": "assistant", "content": clean_response})
        elif stream_handler.handoff_detected and "HANDOFF_HUMAN:" in full_response:
            clean_response = full_response.split("HANDOFF_HUMAN:", 1)[1].strip()
            conversation_histories[session_id].append({"role": "assistant", "content": clean_response})
        else:
            conversation_histories[session_id].append({"role": "assistant", "content": full_response})
        
        # Add any interstitials that were sent to conversation history
        if hasattr(stream_handler, 'sent_interstitials'):
            for interstitial in stream_handler.sent_interstitials:
                conversation_histories[session_id].append({"role": "assistant", "content": interstitial, "type": "interstitial"})
        
        # Final yield
        yield {
            "chunk": "",
            "is_final": True,
            "should_end_call": stream_handler.call_end_detected,
            "should_handoff": stream_handler.handoff_detected,
            "is_interstitial": False
        }
        
    except Exception as e:
        print(f"Error in streaming agent response: {e}")
        yield {
            "chunk": "I'm sorry, I'm having trouble processing your request right now.",
            "is_final": True,
            "should_end_call": False,
            "should_handoff": False,
            "is_interstitial": False
        }
