# Twilio AI Certification Project

## CoffeeMarket Virtual Agent

This application is a Twilio ConversationRelay-powered virtual agent primarily designed for **coffee order status enquiries**. Customers can call in to check their order status, get delivery updates, and receive assistance with their coffee orders. The system also handles general coffee shop enquiries and can transfer to human agents when needed.

### Main Features

- **Order Status Lookup** - Primary use case for checking coffee order status and delivery information
- **Inventory Enquiries** - Information about available coffee products and stock levels
- **General Support** - Coffee shop hours, locations, and product information
- **Intelligent Handoffs** - Seamless transfer to human agents when needed
- **Conversation Analytics** - Insights and performance metrics for continuous improvement

### Agent Operators

The system uses two specialized Twilio Intelligence operators for post-conversation analysis:

1. **Agent Handoff Operator** - Analyses human agent performance after handoffs
   - Reviews and scores human agent interactions (friendliness, clarity, accuracy, responsiveness)
   - Summarises key topics, customer concerns, and resolution status
   - Provides enhancement suggestions for future human interactions

2. **Agent Improvement Operator** - Analyses AI agent conversation quality
   - Identifies customer intent, topics discussed, and resolution status
   - Detects unmet requests and suggests feature gaps to address
   - Evaluates sentiment changes and agent performance strengths/weaknesses
   - Recommends improvements for agent training and customer experience

### Usage Examples

Customers can interact with the CoffeeMarket Virtual Agent using natural language. Here are common conversation examples:

#### Order Status Enquiries
- "What's the status of my order CM12345?"
- "Has my coffee order shipped yet?"
- "When will order CM67890 be delivered?"
- "Can you check if my order has been processed?"

#### Stock and Product Enquiries
- "Do you have Colombian Supremo coffee in stock?"
- "What French press coffee makers do you have available?"
- "Is the Ethiopian Yirgacheffe still available?"
- "What's the price of your House Blend?"

#### Coffee Recommendations
- "I like strong, bold coffee - what do you recommend?"
- "Can you suggest something with chocolate notes?"
- "What's good for espresso brewing?"
- "I prefer mild, smooth coffee - any suggestions?"

#### General Information
- "What are your store hours?"
- "Where are your locations?"
- "Do you have a loyalty programme?"
- "What's your return policy?"
- "How do I clean my coffee grinder?"

#### Human Agent Transfer
- "I'd like to speak to a person"
- "Can I talk to someone?"
- "I need human help with my order"
- "Transfer me to customer service"

### Setup Instructions

#### Prerequisites
- Python 3.8+
- Twilio account with ConversationRelay enabled
- ngrok for local development tunneling

#### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd twilio
   ```

2. **Install dependencies**
   ```bash
   python setup.py
   ```
   This will create a virtual environment and install all required packages.

3. **Environment Configuration**
   Copy the template environment file and configure your credentials:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` with your actual values

4. **Start ngrok tunnel** (for local development)
   ```bash
   ./ngrok.exe http 5000
   ```
   Copy the domain part (without https://) to your SERVICE_URL environment variable

5. **Activate virtual environment and run**
   ```bash
   # Windows
   .venv\Scripts\activate
   python app.py
   ```

6. **Configure Twilio ConversationRelay**
   - Set your webhook URL to: `https://your-ngrok-domain.ngrok-free.app/start`
   - Configure your Twilio phone number to use ConversationRelay
   - Set operator output webhook to: `https://your-ngrok-domain.ngrok-free.app/operator_output`

### Project Structure

- `app.py` - Main FastAPI application with webhook endpoints
- `agent.py` - Core agent logic and conversation handling
- `conversation.py` - ConversationRelay WebSocket handler
- `llm_handler.py` - Azure OpenAI streaming integration
- `operators.py` - Twilio Intelligence operator webhook handlers
- `loaders.py` - Data loading utilities for knowledge bases and databases
- `utils.py` - Logging configuration and conversation utilities
- `constants.py` - Application constants and configuration
- `prompt.txt` - Main system prompt for the AI agent
- `stt_hints.txt` - Speech-to-text hints for improved transcription
- `requirements.txt` - Python dependencies
- `setup.py` - Environment setup and dependency installation
- `agent_manager/` - Agent management utilities, tools, and handlers
- `operators/` - Operator prompt templates and training data
- `knowledge/` - Coffee database and knowledge base files
- `store/` - Inventory and delivery status data
- `logs/` - Application and conversation logs