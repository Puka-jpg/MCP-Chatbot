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
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()        
        self.available_tools = []
        self.sessions = {}
        self.conversation_history = []

    async def connect_to_server(self, server_name, server_config):
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
             
            response = await session.list_tools()
            
            # Load all available tools
            for tool in response.tools:
                self.sessions[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
                print(f"Loaded tool: {tool.name}")
                
        except Exception as e:
            print(f"Error connecting to {server_name}: {e}")

    async def connect_to_servers(self):
        with open("server_config.json", "r") as file:
            data = json.load(file)
        servers = data.get("mcpServers", {})
        
        print("Connecting to MCP servers...")
        for server_name, server_config in servers.items():
            await self.connect_to_server(server_name, server_config)
        
        print(f"Connected to {len(servers)} server(s)")
        print(f"Loaded {len(self.available_tools)} tools")
    
    async def process_query(self, query):
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
- Any company-related questions

CONTACT COLLECTION:
When users want to be contacted:
1. Collect name, phone, and email through natural conversation
2. Call save_contact_info(name, phone, email) when you have everything

APPOINTMENT BOOKING:
When users want to book appointments:
1. Collect name, email, phone, and date through natural conversation
2. Execute workflow: save_appointment → send_email → update_appointment_status
3. Handle each step intelligently

COMPANY BASICS:
NeuralFlow is an AI/ML company with 12+ years experience and 250+ completed projects.

Remember: Have conversations, then take action."""
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
                    
                    session = self.sessions.get(content.name)
                    if not session:
                        print(f"Tool '{content.name}' not found.")
                        break
                    
                    print(f" {content.name}")
                    result = await session.call_tool(content.name, arguments=content.input)
                    
                    self.conversation_history.append({'role': 'assistant', 'content': assistant_content})
                    self.conversation_history.append({
                        "role": "user", 
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content
                        }]
                    })
            
            if not has_tool_use:
                break
    
    async def chat_loop(self):
        print("\n" + "="*50)
        print("NeuralFlow AI Assistant ")
        print("="*50)
        print("Hi! I'm Neuron from NeuralFlow Technology.")
        print("Ask me about our AI solutions, team, services, or book an appointment!")
        print("="*50)
        
        while True:
            try:
                query = input("\n You: ").strip()
                if not query:
                    continue
        
                if query.lower() in ['quit', 'exit', 'bye']:
                    print("\nNeuron: Thanks for chatting! Feel free to reach out anytime. ")
                    break
                
                print("\nNeuron:")
                await self.process_query(query)
                    
            except KeyboardInterrupt:
                print("\nNeuron: Thanks for chatting! Feel free to reach out anytime. ")
                break
            except Exception as e:
                print(f"\nSorry, something went wrong: {str(e)}")
    
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