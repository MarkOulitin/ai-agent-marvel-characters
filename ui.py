import gradio as gr
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Get server configuration
SERVER_HOST = os.getenv('SERVER_HOST', 'localhost')
SERVER_PORT = os.getenv('SERVER_PORT', '8000')
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

def ask_question(question):
    """Send question to the /question endpoint"""
    if not question.strip():
        return "Please enter a question."
    
    try:
        payload = {"question": question}
        response = requests.post(
            f"{BASE_URL}/question",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "No response received")
        else:
            return f"Error {response.status_code}: {response.text}"
            
    except requests.exceptions.ConnectionError:
        return f"❌ Connection Error: Could not connect to server at {BASE_URL}. Make sure the server is running."
    except requests.exceptions.Timeout:
        return "⏰ Request timed out. The server might be processing a complex query."
    except Exception as e:
        return f"❌ Error: {str(e)}"

def get_character_graph(character_name):
    """Get character graph from the /graph/{character} endpoint"""
    if not character_name.strip():
        return "Please enter a character name."
    
    try:
        response = requests.get(
            f"{BASE_URL}/graph/{character_name}",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            # Format the JSON response nicely
            return json.dumps(result, indent=2)
        elif response.status_code == 404:
            return f"Character '{character_name}' not found in the graph."
        else:
            return f"Error {response.status_code}: {response.text}"
            
    except requests.exceptions.ConnectionError:
        return f"❌ Connection Error: Could not connect to server at {BASE_URL}. Make sure the server is running."
    except requests.exceptions.Timeout:
        return "⏰ Request timed out."
    except Exception as e:
        return f"❌ Error: {str(e)}"

def check_server_status():
    """Check if the server is accessible"""
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            return f"✅ Server is running at {BASE_URL}"
        else:
            return f"⚠️ Server responded with status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return f"❌ Server is not accessible at {BASE_URL}"
    except Exception as e:
        return f"❌ Error checking server: {str(e)}"

# Create Gradio interface
with gr.Blocks(title="X-Men Agent Server Tester", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🦸‍♂️ X-Men Agent Server Tester")
    gr.Markdown(f"Testing server at: `{BASE_URL}`")
    
    # Server status check
    with gr.Row():
        status_btn = gr.Button("Check Server Status", variant="secondary")
        status_output = gr.Textbox(label="Server Status", interactive=False)
    
    status_btn.click(check_server_status, outputs=status_output)
    
    gr.Markdown("---")
    
    # Question asking interface
    with gr.Tab("Ask Questions"):
        gr.Markdown("### Ask the X-Men Agent a Question")
        gr.Markdown("This uses the `/question` endpoint to process your question through the agentic workflow.")
        
        with gr.Row():
            with gr.Column(scale=3):
                question_input = gr.Textbox(
                    label="Your Question",
                    placeholder="e.g., Who is Wolverine? What are Storm's powers?",
                    lines=3
                )
            with gr.Column(scale=1):
                ask_btn = gr.Button("Ask Question", variant="primary", size="lg")
        
        question_output = gr.Textbox(
            label="Agent Response",
            lines=10,
            max_lines=20,
            interactive=False
        )
        
        # Example questions
        gr.Markdown("### Example Questions:")
        example_questions = [
            "Who is Wolverine and what are his powers?",
            "Tell me about the relationship between Professor X and Magneto",
            "What is Storm's background and abilities?",
            "Who are the main members of the X-Men team?",
            "What is the Brotherhood of Mutants?"
        ]
        
        for i, example in enumerate(example_questions):
            gr.Button(
                example,
                size="sm",
                variant="secondary"
            ).click(
                lambda x=example: x,
                outputs=question_input
            )
    
    # Character graph interface
    with gr.Tab("Character Graph"):
        gr.Markdown("### Explore Character Relationships")
        gr.Markdown("This uses the `/graph/{character}` endpoint to get a character's immediate neighbors in the graph.")
        
        with gr.Row():
            with gr.Column(scale=3):
                character_input = gr.Textbox(
                    label="Character Name",
                    placeholder="e.g., Wolverine, Storm, Professor X",
                    lines=1
                )
            with gr.Column(scale=1):
                graph_btn = gr.Button("Get Graph", variant="primary", size="lg")
        
        graph_output = gr.Textbox(
            label="Character Graph Data",
            lines=15,
            max_lines=25,
            interactive=False
        )
        
        # Example characters
        gr.Markdown("### Example Characters:")
        example_characters = [
            "Wolverine", "Storm", "Professor X", "Cyclops", "Jean Grey",
            "Magneto", "Mystique", "Beast", "Rogue", "Gambit"
        ]
        
        with gr.Row():
            for char in example_characters:
                gr.Button(
                    char,
                    size="sm",
                    variant="secondary"
                ).click(
                    lambda x=char: x,
                    outputs=character_input
                )
    
    # Wire up the main functionality
    ask_btn.click(
        ask_question,
        inputs=question_input,
        outputs=question_output
    )
    
    graph_btn.click(
        get_character_graph,
        inputs=character_input,
        outputs=graph_output
    )
    
    # Allow Enter key to submit
    question_input.submit(
        ask_question,
        inputs=question_input,
        outputs=question_output
    )
    
    character_input.submit(
        get_character_graph,
        inputs=character_input,
        outputs=graph_output
    )
    
    # Footer
    gr.Markdown("---")
    gr.Markdown("💡 **Tips:**")
    gr.Markdown("- Make sure your FastAPI server is running before using this interface")
    gr.Markdown("- Check the server status first if you encounter connection errors")
    gr.Markdown("- The question endpoint may take some time for complex queries")

if __name__ == "__main__":
    print(f"Starting Gradio UI for server at {BASE_URL}")
    print("Make sure your FastAPI server is running!")
    app.launch(
        server_port=7860,
        share=False,
        debug=True
    )