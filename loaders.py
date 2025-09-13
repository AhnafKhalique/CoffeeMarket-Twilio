"""Data loaders for knowledge bases, databases, and configuration files."""
import json
from utils import setup_logging

logger = setup_logging()

def load_stt_hints():
    """Load speech-to-text hints for improved transcription accuracy.
    
    Returns:
        str: Hints content for STT processing, empty string if file not found
    """
    try:
        with open('stt_hints.txt', 'r', encoding='utf-8') as f:
            hints_content = f.read().strip()
            return hints_content
    except FileNotFoundError:
        logger.warning("stt_hints.txt not found, using empty hints")
        return ""
    except Exception as e:
        logger.error(f"Error loading stt_hints.txt: {e}")
        return ""

def load_coffee_database():
    """Load coffee product database from JSON file.
    
    Returns:
        dict: Coffee database content, empty dict if file not found
    """
    try:
        with open('knowledge/coffee_database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: knowledge/coffee_database.json not found")
        return {}
    except Exception as e:
        print(f"Error loading coffee database: {e}")
        return {}

def load_knowledge_base():
    """Load CoffeeMarket knowledge base from JSON file.
    
    Returns:
        dict: Knowledge base content, empty dict if file not found
    """
    try:
        with open('knowledge/coffeemart_knowledge_base.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: knowledge/coffeemart_knowledge_base.json not found")
        return {}
    except Exception as e:
        print(f"Error loading knowledge base: {e}")
        return {}

def load_delivery_status_db():
    """Load delivery status database from JSON file.
    
    Returns:
        dict: Delivery status data, empty dict if file not found
    """
    try:
        with open('store/delivery_status.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: store/delivery_status.json not found")
        return {}
    except Exception as e:
        print(f"Error loading delivery status database: {e}")
        return {}

def load_inventory_db():
    """Load inventory database from JSON file.
    
    Returns:
        dict: Inventory data, empty dict if file not found
    """
    try:
        with open('store/inventory.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: store/inventory.json not found")
        return {}
    except Exception as e:
        print(f"Error loading inventory database: {e}")
        return {}

def load_system_prompt():
    """Load the system prompt from prompt.txt file.
    
    Returns:
        str: System prompt content, default prompt if file not found
    """
    try:
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning("prompt.txt not found, using default prompt")
        return "You are a helpful CoffeeMarket customer service assistant."
    except Exception as e:
        logger.error(f"Error loading prompt.txt: {e}")
        return "You are a helpful CoffeeMarket customer service assistant."

# Load all data sources at module import
SYSTEM_PROMPT = load_system_prompt()
STT_HINTS = load_stt_hints()
COFFEE_DB = load_coffee_database()
KNOWLEDGE_BASE = load_knowledge_base()
DELIVERY_STATUS_DB = load_delivery_status_db()
INVENTORY_DB = load_inventory_db()
