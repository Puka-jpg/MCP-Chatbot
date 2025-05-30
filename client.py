from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack
import json
import asyncio
import nest_asyncio

nest_asyncio.apply()
load_dotenv()

class NeuralFlowChatBot:
    def __init__(self):
        self.exit_stack = AsyncExitStack()  #manages async resources
        self.anthropic = Anthropic()        
        # Tools list required for Anthropic API
        self.available_tools = []
        # Sessions dict maps tool names to MCP client sessions
        self.sessions = {}      #map tool names to mcp session
        self.conversation_history = []

    async def connect_to_server(self, server_name, server_config): # individual server connection process
        try:
            #create server parameters from config
            server_params = StdioServerParameters(**server_config)
            #start the MCP server process and get stdio transport
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            #create mcp client session
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
             
            try:
                response = await session.list_tools()
                
                # Updated allowed tools - RAG 
                if server_name == "rag_neuralflow":
                    allowed_tools = ['semantic_search']
                elif server_name == "tools_neuralflow":
                    allowed_tools = ['save_contact_info', 'save_appointment']  
                else:
                    allowed_tools = []
                    
                for tool in response.tools:
                    if tool.name in allowed_tools:
                        self.sessions[tool.name] = session
                        self.available_tools.append({
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema
                        })
                        print(f"Loaded tool: {tool.name}")
            
            except Exception as e:
                print(f"Error loading tools from {server_name}: {e}")
                
        except Exception as e:
            print(f"Error connecting to {server_name}: {e}")

    async def connect_to_servers(self):
        try:
            with open("server_config.json", "r") as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            
            print("🔗 Connecting to MCP servers...")
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
            
            print(f"✅ Connected to {len(servers)} server(s)")
            print(f"Loaded {len(self.available_tools)} tools")
            
        except Exception as e:
            print(f"Error loading server config: {e}")
            raise
    
    async def process_query(self, query):
        """Process user query and handle tool calls"""
        if not hasattr(self, 'conversation_history'):
            self.conversation_history = []
        
        self.conversation_history.append({'role': 'user', 'content': query})
        
        while True:
            response = self.anthropic.messages.create(
                max_tokens=2024,
                model='claude-3-5-sonnet-20241022', 
                tools=self.available_tools,
                messages=self.conversation_history,
                system="""You are Neuron, a friendly AI assistant for NeuralFlow Technology.

CONVERSATION STYLE:
- Be natural, conversational, and helpful
- Keep responses concise and engaging
- Have complete conversations before taking actions

WHEN TO USE TOOLS:

USE semantic_search for company questions:
- "What services do you offer?"
- "Tell me about your company"
- "Do you have testimonials?"
- Any company-related questions

CONTACT COLLECTION:
When users want to be contacted or need a phone call:
1. Collect name, phone, and email through natural conversation
2. You must have ALL THREE pieces before calling save_contact_info
3. Ask follow-up questions until you have complete information
4. Call save_contact_info(name, phone, email) ONLY when you have everything
5. Call the tool ONCE per contact request

APPOINTMENT BOOKING:
When users want to book appointments:
1. Collect name and date through natural conversation
2. Try to also collect phone and email for better service
3. Have a complete conversation about their needs
4. Call save_appointment(name, date, phone, email) ONLY when ready to finalize
5. Call the tool ONCE per appointment request

CONVERSATION MANAGEMENT RULES:
- Gather information through natural dialogue
- Don't rush to call tools immediately
- Ensure the conversation feels complete before taking action
- Each tool should be called exactly ONCE per user request
- Use information from earlier in the conversation (don't ask for the same details twice)

COMPANY BASICS (use without tools):
NeuralFlow is an AI/ML company with 12+ years experience and 250+ completed projects, offering AI agents for customer experience, internal teams, and workflow automation.

Remember: Have conversations, then take action. One tool call per request."""
            )
            
            assistant_content = []
            has_tool_use = False
            
            for content in response.content:
                if content.type == 'text':
                    print(content.text)
                    assistant_content.append(content)
                elif content.type == 'tool_use':
                    has_tool_use = True
                    assistant_content.append(content)
                    
                    # Getting session and calling tool
                    session = self.sessions.get(content.name)
                    if not session:
                        print(f" Tool '{content.name}' not found.")
                        break
                    
                    try:
                        # Show tool usage for legitimate requests
                        if any(keyword in query.lower() for keyword in 
                               ['service', 'company', 'team', 'testimonial', 'about', 'what', 'tell me', 
                                'contact', 'call', 'reach', 'appointment', 'book', 'schedule', 'meeting']):
                            print(f"🔧 {content.name}")
                        
                        result = await session.call_tool(content.name, arguments=content.input)
                        
                        # Print results for contact/appointment tools
                        if result.content and content.name in ['collect_contact_info', 'book_appointment']:
                            for item in result.content:
                                if hasattr(item, 'text'):
                                    print(item.text)
                        
                        # Add assistant message
                        self.conversation_history.append({'role': 'assistant', 'content': assistant_content})
                        
                        # Add tool result
                        self.conversation_history.append({
                            "role": "user", 
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": content.id,
                                    "content": result.content
                                }
                            ]
                        })
                        
                    except Exception as e:
                        print(f"Error calling tool {content.name}: {e}")
                        break
            
            # Exit loop if no tool was used
            if not has_tool_use:
                break
    
    async def chat_loop(self):
        """Main chat interface"""
        print("\n" + "="*50)
        print("🤖 NeuralFlow AI Assistant ")
        print("="*50)
        print("Hi! I'm Neuron from NeuralFlow Technology.")
        print("Ask me about our AI solutions, team, services, or book an appointment!")
        print("="*50)
        
        while True:
            try:
                query = input("\n💬 You: ").strip()
                if not query:
                    continue
        
                if query.lower() in ['quit', 'exit', 'bye']:
                    print("\n🤖 Neuron: Thanks for chatting! Feel free to reach out anytime. 👋")
                    break
                
                print("\n🤖 Neuron:")
                await self.process_query(query)
                    
            except KeyboardInterrupt:
                print("\n🤖 Neuron: Thanks for chatting! Feel free to reach out anytime. 👋")
                break
            except Exception as e:
                print(f"\nSorry, something went wrong: {str(e)}")
                print("Please try asking your question differently.")
    
    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    chatbot = NeuralFlowChatBot()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()


if __name__ == "__main__":
    asyncio.run(main())