import json
import os
from huggingface_hub import hf_hub_download
from llama_cpp import Llama, LlamaGrammar

# GBNF Grammar — enforces strict JSON output with multi-digit number support
# number allows integers 0-100 and decimals (e.g. 22.5)
JSON_GRAMMAR = r"""
root   ::= "{" sp "\"function\":" sp string sp "," sp "\"value\":" sp number sp "}"
string ::= "\"" [a-zA-Z0-9_]+ "\""
number ::= "-"? [0-9]+ ("." [0-9]+)?
sp     ::= " "*
"""

class SLMInferenceEngine:
    def __init__(self, model_repo="bartowski/Llama-3.2-1B-Instruct-GGUF", filename="Llama-3.2-1B-Instruct-Q4_K_M.gguf"):
        self.model_path = self._download_model(model_repo, filename)
        
        print("Loading LLM locally via llama.cpp...")
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=2048,
            n_threads=4,
            verbose=False
        )
        self.grammar = LlamaGrammar.from_string(JSON_GRAMMAR)

    def _download_model(self, repo_id: str, filename: str) -> str:
        """Download the GGUF model from Hugging Face if not already present."""
        print(f"Checking for model {filename} in cache/downloading...")
        path = hf_hub_download(repo_id=repo_id, filename=filename)
        print(f"Model ready at: {path}")
        return path

    def extract_intent(self, text: str) -> dict:
        """
        Passes the user's natural language command to the SLM.
        Uses an extensive few-shot system prompt to handle contextual,
        colloquial phrases as well as explicit commands.
        Strictly returns JSON enforced by GBNF grammar.
        """
        system_prompt = """\
You are an automotive AI assistant embedded in a smart car cockpit.
Your ONLY job is to translate natural language — including feelings, idioms, and indirect requests — into a JSON car command.

Output ONLY this exact JSON format (no explanation, no extra text):
{"function": "<function_name>", "value": <number>}

Valid functions and their meaning:
- set_ac_temperature : set AC to exact degrees (value = 16-28)
- decrease_temperature : lower temperature by N degrees (value = 1-4)
- increase_temperature : raise temperature by N degrees (value = 1-4)
- turn_on_ac : turn AC on (value = 1)
- turn_off_ac : turn AC off (value = 0)
- set_fan_speed : set fan level (value = 0-6)
- open_sunroof : open sunroof to % (value = 0-100)
- close_sunroof : close sunroof (value = 0)
- open_window : open window to % (value = 0-100)
- close_window : close window (value = 0)
- turn_on_headlights : turn headlights on (value = 1)
- turn_off_headlights : turn headlights off (value = 0)

Few-shot examples (LEARN THESE PATTERNS):

CRITICAL RULE: For open_sunroof and open_window, if no percentage is stated, value = 50.
CRITICAL RULE: For close_sunroof and close_window, value is always 0.

User: I'm feeling hot
Assistant: {"function": "decrease_temperature", "value": 2}

User: It's too warm in here
Assistant: {"function": "decrease_temperature", "value": 2}

User: I feel cold
Assistant: {"function": "increase_temperature", "value": 2}

User: I want some fresh air
Assistant: {"function": "open_sunroof", "value": 50}

User: Open the sunroof
Assistant: {"function": "open_sunroof", "value": 50}

User: Open sunroof
Assistant: {"function": "open_sunroof", "value": 50}

User: Open the sunroof halfway
Assistant: {"function": "open_sunroof", "value": 50}

User: Open sunroof to 70 percent
Assistant: {"function": "open_sunroof", "value": 70}

User: Open sunroof to 30 percent
Assistant: {"function": "open_sunroof", "value": 30}

User: Set sunroof to 80 percent
Assistant: {"function": "open_sunroof", "value": 80}

User: Open the roof a little
Assistant: {"function": "open_sunroof", "value": 25}

User: Open it all the way
Assistant: {"function": "open_sunroof", "value": 100}

User: Close the sunroof
Assistant: {"function": "close_sunroof", "value": 0}

User: Open the window
Assistant: {"function": "open_window", "value": 50}

User: Open window
Assistant: {"function": "open_window", "value": 50}

User: Open window halfway
Assistant: {"function": "open_window", "value": 50}

User: Open window to 60 percent
Assistant: {"function": "open_window", "value": 60}

User: Set window to 40 percent
Assistant: {"function": "open_window", "value": 40}

User: Close the window
Assistant: {"function": "close_window", "value": 0}

User: It's starting to rain
Assistant: {"function": "close_sunroof", "value": 0}

User: It's getting dark outside
Assistant: {"function": "turn_on_headlights", "value": 1}

User: Set AC to 24 degrees
Assistant: {"function": "set_ac_temperature", "value": 24}

User: Make it 20 degrees
Assistant: {"function": "set_ac_temperature", "value": 20}

User: Turn up the fan
Assistant: {"function": "set_fan_speed", "value": 5}

User: Lower the fan speed
Assistant: {"function": "set_fan_speed", "value": 2}
"""

        prompt = (
            f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
            f"{system_prompt}<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n\n{text}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        )

        print(f"SLM Processing: '{text}'...")

        response = self.llm(
            prompt,
            max_tokens=64,
            stop=["<|eot_id|>"],
            grammar=self.grammar,
            temperature=0.05,   # Very low temp = more deterministic output
        )

        output_text = response["choices"][0]["text"].strip()
        print(f"SLM Output: {output_text}")

        try:
            return json.loads(output_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse SLM output as JSON: {e}")
            return None
