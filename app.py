import streamlit as st
import asyncio
import os
import sys
import threading
import time
import json
from pathlib import Path
import uuid

# Fix path for imports
try:
    from mcpclient.client import MCPClient
except ImportError:
    # When running as standalone
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    from mcpclient.client import MCPClient

# Set Windows event loop policy
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Page config
st.set_page_config(page_title="MCP Client", page_icon="🤖", layout="wide")

# Initialize session state variables
if "client" not in st.session_state:
    st.session_state.client = None
if "config_path" not in st.session_state:
    st.session_state.config_path = "mcp_config.json"
if "available_servers" not in st.session_state:
    st.session_state.available_servers = []
if "connected_server" not in st.session_state:
    st.session_state.connected_server = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "session_id" not in st.session_state:
    # Generate a unique session ID for this Streamlit session
    st.session_state.session_id = str(uuid.uuid4())

# Create a directory for temporary files
temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
os.makedirs(temp_dir, exist_ok=True)


# Run async code
def run_async(coro):
    """Run an async coroutine and return the result"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# Load configuration file
def load_config():
    """Load the configuration file and initialize the client"""
    try:
        path = st.session_state.config_input
        if not os.path.exists(path):
            st.error(f"Configuration file not found: {path}")
            return

        # Create new client
        client = MCPClient(config_path=path)
        st.session_state.client = client

        # Get available servers
        available_servers = run_async(client.get_available_servers())
        if not available_servers:
            st.error("No servers found in configuration")
            return

        # Update state
        st.session_state.available_servers = available_servers
        st.session_state.config_path = path

        st.success(f"Configuration loaded with {len(available_servers)} servers")
    except Exception as e:
        st.error(f"Error loading configuration: {str(e)}")
        st.session_state.client = None
        st.session_state.available_servers = []


# Connect to selected server
def connect_to_server():
    """Connect to the selected server"""
    if not st.session_state.client:
        st.error("Client not initialized")
        return

    try:
        server_name = st.session_state.server_select

        # If already connected to this server, do nothing
        if st.session_state.connected_server == server_name:
            st.info(f"Already connected to {server_name}")
            return

        # Disconnect if connected to a different server
        if st.session_state.connected_server:
            run_async(st.session_state.client.disconnect())
            st.session_state.connected_server = None
            st.session_state.chat_history = []

        # Connect to the selected server
        with st.spinner(f"Connecting to {server_name}..."):
            run_async(st.session_state.client.connect_to_server(server_name))

        # Update state
        st.session_state.connected_server = server_name
        st.session_state.chat_history = []

        st.success(f"Connected to {server_name}")
    except Exception as e:
        st.error(f"Error connecting to server: {str(e)}")


# Disconnect from server
def disconnect_from_server():
    """Disconnect from the current server"""
    if not st.session_state.client or not st.session_state.connected_server:
        return

    try:
        server_name = st.session_state.connected_server

        with st.spinner(f"Disconnecting from {server_name}..."):
            run_async(st.session_state.client.disconnect())

        st.session_state.connected_server = None
        st.session_state.chat_history = []

        st.info(f"Disconnected from {server_name}")
    except Exception as e:
        st.error(f"Error disconnecting: {str(e)}")


# Process query in a background thread
def process_query_thread(config_path, server_name, query, session_id):
    """Process a query in a background thread using a new client instance"""
    # Create temp files for this session
    response_file = os.path.join(temp_dir, f"response_{session_id}.txt")
    status_file = os.path.join(temp_dir, f"status_{session_id}.json")

    # Initialize files
    with open(response_file, "w", encoding="utf-8") as f:
        f.write("")
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump({"complete": False, "tool": None, "error": None}, f)

    try:
        # Create a new client instance specifically for this thread
        # This avoids sharing event loops between threads
        client = MCPClient(config_path=config_path)

        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Define the async processing function
        async def process_streaming():
            # Connect to the server
            try:
                await client.connect_to_server(server_name)

                # Full response accumulator
                full_response = []
                current_tool = None

                # Process the streaming response
                async for chunk in client.process_query_streaming(query):
                    # Look for tool execution indicators
                    if "Using tool:" in chunk:
                        import re

                        tool_match = re.search(r"Using tool: (\w+)", chunk)
                        if tool_match:
                            current_tool = tool_match.group(1)

                    # Append chunk to response
                    full_response.append(chunk)

                    # Write current response to file
                    with open(response_file, "w", encoding="utf-8") as f:
                        f.write("".join(full_response))

                    # Update status
                    with open(status_file, "w", encoding="utf-8") as f:
                        json.dump(
                            {"complete": False, "tool": current_tool, "error": None}, f
                        )

                # Streaming complete
                with open(status_file, "w", encoding="utf-8") as f:
                    json.dump({"complete": True, "tool": None, "error": None}, f)

            except Exception as e:
                # Handle streaming errors
                error_msg = f"\n\nError: {str(e)}"
                with open(response_file, "a", encoding="utf-8") as f:
                    f.write(error_msg)

                with open(status_file, "w", encoding="utf-8") as f:
                    json.dump({"complete": True, "tool": None, "error": str(e)}, f)

            finally:
                # Always disconnect
                try:
                    await client.disconnect()
                except:
                    pass

        # Run the async function
        loop.run_until_complete(process_streaming())

        # Clean up
        loop.close()

    except Exception as e:
        # Handle thread-level errors
        with open(response_file, "a", encoding="utf-8") as f:
            f.write(f"\n\nThread Error: {str(e)}")

        with open(status_file, "w", encoding="utf-8") as f:
            json.dump({"complete": True, "tool": None, "error": str(e)}, f)


# Submit a query
def submit_query(query):
    """Submit a query for processing"""
    if not st.session_state.client or not st.session_state.connected_server:
        st.error("Not connected to a server")
        return

    if st.session_state.is_processing:
        st.warning("Already processing a query")
        return

    # Update state
    st.session_state.is_processing = True
    st.session_state.chat_history.append({"role": "user", "content": query})

    # Get reference values
    config_path = st.session_state.config_path
    server_name = st.session_state.connected_server
    session_id = st.session_state.session_id

    # Start processing thread with isolated client
    thread = threading.Thread(
        target=process_query_thread,
        args=(config_path, server_name, query, session_id),
        daemon=True,
    )
    thread.start()

    # Force UI update
    st.rerun()


def check_streaming_status():
    """Check the status of streaming response"""
    if not st.session_state.is_processing:
        return False

    session_id = st.session_state.session_id
    response_file = os.path.join(temp_dir, f"response_{session_id}.txt")
    status_file = os.path.join(temp_dir, f"status_{session_id}.json")

    # Default values
    current_response = ""
    is_complete = False
    current_tool = None
    error = None

    # Read current response
    if os.path.exists(response_file):
        try:
            with open(response_file, "r", encoding="utf-8") as f:
                current_response = f.read()
        except Exception as e:
            st.error(f"Error reading response file: {e}")

    # Read status
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                status = json.load(f)
                is_complete = status.get("complete", False)
                current_tool = status.get("tool")
                error = status.get("error")
        except Exception as e:
            st.error(f"Error reading status file: {e}")
            is_complete = True  # Force completion on error

    # Return a dictionary with the status info
    return {
        "complete": is_complete,
        "response": current_response,
        "tool": current_tool,
        "error": error
    }


with st.sidebar:
    st.title("MCP Client")

    # Configuration
    st.header("Configuration")
    st.text_input("Config Path", value=st.session_state.config_path, key="config_input")
    st.button("Load Configuration", on_click=load_config)

    # Server selection
    if st.session_state.available_servers:
        st.header("Server")
        selected_server = st.selectbox(
            "Select Server",
            options=st.session_state.available_servers,
            key="server_select",
        )

        col1, col2 = st.columns(2)
        with col1:
            st.button(
                "Connect",
                on_click=connect_to_server,
                disabled=st.session_state.is_processing,
            )
        with col2:
            st.button(
                "Disconnect",
                on_click=disconnect_from_server,
                disabled=st.session_state.is_processing
                or not st.session_state.connected_server,
            )

        # Display connection status
        if st.session_state.connected_server:
            st.success(f"Connected: {st.session_state.connected_server}")

    # Add debug info expander
    with st.expander("Debug Info", expanded=False):
        st.write(f"Session ID: {st.session_state.session_id[:8]}...")
        st.write(f"Processing: {st.session_state.is_processing}")
        st.write(f"Connected Server: {st.session_state.connected_server}")
        if st.session_state.client and st.session_state.client.active_session:
            tools = st.session_state.client.active_session.available_tools
            st.write(f"Available Tools: {len(tools) if tools else 0}")

st.title("MCP Chat")

# Connection status
if not st.session_state.client:
    st.info("Please load a configuration file")
elif not st.session_state.connected_server:
    st.warning("Please connect to a server")
else:
    st.success(f"Connected to {st.session_state.connected_server}")

# Chat history (including current streaming message if applicable)
for i, message in enumerate(st.session_state.chat_history):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

    # If this is the last user message and we're processing, show assistant response right after
    if (st.session_state.is_processing and
        i == len(st.session_state.chat_history) - 1 and
        message["role"] == "user"):
        # Streaming response will come next
        pass  # The streaming section below will handle showing the response


# Streaming response (if processing)
if st.session_state.is_processing:
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        status_placeholder = st.empty()

        # Initialize last response length to track changes
        last_response_length = 0

        while True:
            # Get the latest status and response
            status = check_streaming_status()

            # Show response if we have one
            if status and "response" in status:
                current_response = status["response"]

                # Only update if the response has changed
                if len(current_response) != last_response_length:
                    # Add cursor or tool indicator
                    display_text = current_response
                    if status.get("tool"):
                        display_text += f" (Executing tool {status['tool']}...)"
                    else:
                        display_text += "▌" if not status.get("complete") else ""

                    # Update the message placeholder
                    message_placeholder.markdown(display_text)
                    last_response_length = len(current_response)

                # Show error if there is one
                if status.get("error"):
                    status_placeholder.error(f"Error: {status['error']}")

                # If complete, add to chat history and break the loop
                if status.get("complete", False):
                    # Add the final response to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": current_response})
                    st.session_state.is_processing = False
                    break

            # Brief pause before checking again
            time.sleep(0.3)

# Chat input
disabled_chat = not st.session_state.connected_server or st.session_state.is_processing
placeholder = (
    "Processing..." if st.session_state.is_processing else "Enter your query..."
)

if prompt := st.chat_input(placeholder, disabled=disabled_chat):
    submit_query(prompt)
