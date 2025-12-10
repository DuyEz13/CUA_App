import re
import time
from io import BytesIO
from PIL import Image

from typing import Tuple, Dict

from prompt.prompt import PROMPT

import logging

logger = logging.getLogger("desktopenv.agent")


def create_pyautogui_code(agent, code: str, obs: Dict) -> str:
    """
    Attempts to evaluate the code into a pyautogui code snippet with grounded actions using the observation screenshot.

    Args:
        agent (ACI): The grounding agent to use for evaluation.
        code (str): The code string to evaluate.
        obs (Dict): The current observation containing the screenshot.

    Returns:
        exec_code (str): The pyautogui code to execute the grounded action.

    Raises:
        Exception: If there is an error in evaluating the code.
    """
    agent.assign_screenshot(obs)  # Necessary for grounding
    exec_code = eval(code)
    return exec_code


def call_llm_safe(
    agent, temperature: float = 0.0, use_thinking: bool = False, **kwargs
) -> str:
    # Retry if fails
    max_retries = 3  # Set the maximum number of retries
    attempt = 0
    response = ""
    while attempt < max_retries:
        try:
            response, full_rp = agent.get_response(
                temperature=temperature, use_thinking=use_thinking, **kwargs
            )
            assert response is not None, "Response from agent should not be None"
            print("Response success!")
            break  # If successful, break out of the loop
        except Exception as e:
            attempt += 1
            print(f"Attempt {attempt} failed: {e}")
            if attempt == max_retries:
                print("Max retries reached. Handling failure.")
        time.sleep(1.0)
    return response if response is not None else "", full_rp


def call_llm_formatted(generator, format_checkers, **kwargs):
    """
    Calls the generator agent's LLM and ensures correct formatting.

    Args:
        generator (ACI): The generator agent to call.
        obs (Dict): The current observation containing the screenshot.
        format_checkers (Callable): Functions that take the response and return a tuple of (success, feedback).
        **kwargs: Additional keyword arguments for the LLM call.

    Returns:
        response (str): The formatted response from the generator agent.
    """
    max_retries = 3  # Set the maximum number of retries
    attempt = 0
    response = ""
    if kwargs.get("messages") is None:
        messages = (
            generator.messages.copy()
        )  # Copy messages to avoid modifying the original
    else:
        messages = kwargs["messages"]
        del kwargs["messages"]  # Remove messages from kwargs to avoid passing it twice
    while attempt < max_retries:
        response = call_llm_safe(generator, messages=messages, **kwargs)

        # Prepare feedback messages for incorrect formatting
        feedback_msgs = []
        for format_checker in format_checkers:
            success, feedback = format_checker(response)
            if not success:
                feedback_msgs.append(feedback)
        if not feedback_msgs:
            # logger.info(f"Response formatted correctly on attempt {attempt} for {generator.engine.model}")
            break
        logger.error(
            f"Response formatting error on attempt {attempt} for {generator.engine.model}. Response: {response} {', '.join(feedback_msgs)}"
        )
        messages.append(
            {
                "role": "assistant",
                "content": [{"type": "text", "text": response}],
            }
        )
        logger.info(f"Bad response: {response}")
        delimiter = "\n- "
        formatting_feedback = f"- {delimiter.join(feedback_msgs)}"
        # messages.append(
        #     {
        #         "role": "user",
        #         "content": [
        #             {
        #                 "type": "text",
        #                 "text": PROCEDURAL_MEMORY.FORMATTING_FEEDBACK_PROMPT.replace(
        #                     "FORMATTING_FEEDBACK", formatting_feedback
        #                 ),
        #             }
        #         ],
        #     }
        # )
        logger.info("Feedback:\n%s", formatting_feedback)

        attempt += 1
        if attempt == max_retries:
            logger.error(
                "Max retries reached when formatting response. Handling failure."
            )
        time.sleep(1.0)
    return response


def split_thinking_response(full_response: str) -> Tuple[str, str]:
    try:
        # Extract thoughts section
        thoughts = full_response.split("<thoughts>")[-1].split("</thoughts>")[0].strip()

        # Extract answer section
        answer = full_response.split("<answer>")[-1].split("</answer>")[0].strip()

        return answer, thoughts
    except Exception as e:
        return full_response, ""


def parse_code_from_string(input_string):
    """Parses a string to extract each line of code enclosed in triple backticks (```)

    Args:
        input_string (str): The input string containing code snippets.

    Returns:
        str: The last code snippet found in the input string, or an empty string if no code is found.
    """
    input_string = input_string.strip()

    # This regular expression will match both ```code``` and ```python code```
    # and capture the `code` part. It uses a non-greedy match for the content inside.
    pattern = r"```(?:\w+\s+)?(.*?)```"

    # Find all non-overlapping matches in the string
    matches = re.findall(pattern, input_string, re.DOTALL)
    if len(matches) == 0:
        # return []
        return ""
    relevant_code = matches[
        -1
    ]  # We only care about the last match given it is the grounded action
    return relevant_code


def extract_agent_functions(code):
    """Extracts all agent function calls from the given code.

    Args:
        code (str): The code string to search for agent function calls.

    Returns:
        list: A list of all agent function calls found in the code.
    """
    pattern = r"(agent\.\w+\(\s*.*\))"  # Matches
    return re.findall(pattern, code)


def compress_image(image_bytes: bytes = None, image: Image = None) -> bytes:
    """Compresses an image represented as bytes.

    Compression involves resizing image into half its original size and saving to webp format.

    Args:
        image_bytes (bytes): The image data to compress.

    Returns:
        bytes: The compressed image data.
    """
    if not image:
        image = Image.open(BytesIO(image_bytes))
    output = BytesIO()
    image.save(output, format="WEBP")
    compressed_image_bytes = output.getvalue()
    return compressed_image_bytes

def parse_last_step(text: str):
    step_positions = [(m.group(0), m.start()) 
                      for m in re.finditer(r"Step\s+\d+/\d+", text)]

    if not step_positions:
        return None

    _, last_pos = step_positions[-1]
    last_step_text = text[last_pos:]

    screenshot_analysis = ""
    m = re.search(
        r"\(Screenshot Analysis\)(.*?)(?=\(\w|\Z)",
        last_step_text,
        re.DOTALL
    )
    if m:
        screenshot_analysis = m.group(1).strip()

    next_action = ""
    m = re.search(
        r"\(Next Action\)(.*?)(?=\(Grounded Action\)|\Z)",
        last_step_text,
        re.DOTALL
    )
    if m:
        next_action = m.group(1).strip()

    grounded_action = ""
    m = re.search(r"\(Grounded Action\)\s*```python(.*?)```",
                  last_step_text, re.DOTALL)
    if m:
        grounded_action = m.group(1).strip()

    if "agent.fail()" in grounded_action:
        signal = "Fail"
    elif "agent.done()" in grounded_action:
        signal = "Done"
    else:
        signal = "Unknown"

    step_str = re.search(r"Step\s+(\d+/\d+)", last_step_text)
    step_number = step_str.group(1) if step_str else None

    return {
        "screenshot_analysis": screenshot_analysis,
        "next_action": next_action,
        "grounded_action": grounded_action,
        "signal": signal
    }

STEP_RE = re.compile(r"🔄 Step (\d+)/\d+")
MODEL_RE = re.compile(r"model='([^']+)'")
PROMPT_RE = re.compile(r"prompt_tokens=(\d+)")
COMPLETION_RE = re.compile(r"completion_tokens=(\d+)")
TOTAL_RE = re.compile(r"total_tokens=(\d+)")

def parse_token_usage(stdout: str):
    calls = []

    last_step_context = "Unknown"

    inside_block = False
    buffer = []
    paren_balance = 0
    block_context = None

    for line in stdout.splitlines():
        # 1. Update step context
        step_match = STEP_RE.search(line)
        if step_match:
            step = step_match.group(1)
            last_step_context = f"Step {step}"
            continue

        # 2. Start ChatCompletion block
        if "ChatCompletion(" in line:
            inside_block = True
            buffer = [line]
            paren_balance = line.count("(") - line.count(")")
            block_context = last_step_context  # ✅ snapshot context
            continue

        # 3. Collect block
        if inside_block:
            buffer.append(line)
            paren_balance += line.count("(")
            paren_balance -= line.count(")")

            if paren_balance == 0:
                block = "\n".join(buffer)
                inside_block = False

                model = MODEL_RE.search(block)
                prompt = PROMPT_RE.search(block)
                completion = COMPLETION_RE.search(block)
                total = TOTAL_RE.search(block)

                if all([model, prompt, completion, total]):
                    calls.append({
                        "model": model.group(1),
                        "context": block_context,
                        "input_tokens": int(prompt.group(1)),
                        "output_tokens": int(completion.group(1)),
                        "total_tokens": int(total.group(1)),
                    })

    return calls

def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate estimated cost based on model pricing
        
        Pricing as of Dec 2024 (adjust these rates as needed):
        """
        pricing = {
            "gpt-5": {
                "input": 0.000002,  # $2 per 1M tokens (example)
                "output": 0.000006  # $6 per 1M tokens (example)
            },
            "gpt-4": {
                "input": 0.00003,   # $30 per 1M tokens
                "output": 0.00006   # $60 per 1M tokens
            },
            "gpt-4-turbo": {
                "input": 0.00001,   # $10 per 1M tokens
                "output": 0.00003   # $30 per 1M tokens
            },
            "gpt-3.5-turbo": {
                "input": 0.0000005,  # $0.50 per 1M tokens
                "output": 0.0000015  # $1.50 per 1M tokens
            },
            "gemini-2.5-flash": {
                "input": 0.00000003,   # $0.30 per 1M tokens
                "output": 0.00000025   # $2.50 per 1M tokens
            }
        }
        
        # Default to GPT-4 pricing if model not found
        rates = pricing.get(model, pricing.get("gpt-4"))
        
        input_cost = input_tokens * rates["input"]
        output_cost = output_tokens * rates["output"]
        
        return input_cost + output_cost

def write_token_log_txt(calls, path: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write("=" * 100 + "\n")
        f.write("TOKEN USAGE LOG\n")
        f.write("=" * 100 + "\n")

        for idx, call in enumerate(calls, 1):
            total_cost = _calculate_cost(call['model'], call['input_tokens'], call['output_tokens'])
            f.write(f"Call #{idx}\n")
            f.write(f"Model: {call['model']}\n")
            f.write(f"Context: {call['context']}\n")
            f.write(f"Input Tokens: {call['input_tokens']:,}\n")
            f.write(f"Output Tokens: {call['output_tokens']:,}\n")
            f.write(f"Total Tokens: {call['total_tokens']:,}\n")
            f.write(f"Total Estimated Cost: ${total_cost:.6f}\n")
            f.write("-" * 100 + "\n")