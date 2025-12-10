import datetime
import os
from typing import Dict, Any
import json
import logging
from pathlib import Path

class TokenUsageLogger:
    """Tracks and logs token usage across all LLM calls"""
    
    def __init__(self, log_dir=""):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        datetime_str = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
        self.token_log_file = os.path.join(log_dir, f"token-usage-{datetime_str}.log")
        self.token_json_file = os.path.join(log_dir, f"token-usage-{datetime_str}.json")
        
        # Initialize tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.call_count = 0
        self.usage_history = []
        
        # Initialize log file with header
        with open(self.token_log_file, 'w', encoding='utf-8') as f:
            f.write("="*100 + "\n")
            f.write("TOKEN USAGE LOG\n")
            f.write(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*100 + "\n\n")
    
    def log_usage(self,
                  model: str,
                  input_tokens: int,
                  output_tokens: int,
                  total_tokens: int,
                  context: str = "",
                  metadata: Dict[str, Any] = None):
        """
        Log token usage for a single LLM call
        
        Args:
            model: Model name (e.g., "gpt-5")
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
            total_tokens: Total tokens used
            context: Description of what the call was for
            metadata: Additional metadata to log
        """
        self.call_count += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_tokens += total_tokens
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        # Calculate cost (example rates, adjust as needed)
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        
        # Create usage record
        usage_record = {
            "timestamp": timestamp,
            "call_number": self.call_count,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": cost,
            "context": context,
            "metadata": metadata or {}
        }
        
        self.usage_history.append(usage_record)
        
        # Log to text file
        with open(self.token_log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] Call #{self.call_count}\n")
            f.write(f"  Model: {model}\n")
            f.write(f"  Context: {context}\n")
            f.write(f"  Input Tokens: {input_tokens:,}\n")
            f.write(f"  Output Tokens: {output_tokens:,}\n")
            f.write(f"  Total Tokens: {total_tokens:,}\n")
            f.write(f"  Estimated Cost: ${cost:.6f}\n")
            if metadata:
                f.write(f"  Metadata: {json.dumps(metadata, indent=4)}\n")
            f.write("-"*100 + "\n\n")
        
        # Update JSON file with all history
        with open(self.token_json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "summary": {
                    "total_calls": self.call_count,
                    "total_input_tokens": self.total_input_tokens,
                    "total_output_tokens": self.total_output_tokens,
                    "total_tokens": self.total_tokens,
                    "total_estimated_cost_usd": self._calculate_total_cost()
                },
                "usage_history": self.usage_history
            }, f, indent=2)
        
        # Log to console
        logging.info(f"💰 Token Usage - Call #{self.call_count}: {total_tokens:,} tokens "
                    f"(in: {input_tokens:,}, out: {output_tokens:,}) | Cost: ${cost:.6f}")
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
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
    
    def _calculate_total_cost(self) -> float:
        """Calculate total cost from all usage history"""
        return sum(record["estimated_cost_usd"] for record in self.usage_history)
    
    def print_summary(self):
        """Print summary of token usage"""
        total_cost = self._calculate_total_cost()
        
        summary = f"""
{'='*100}
TOKEN USAGE SUMMARY
{'='*100}
Total LLM Calls: {self.call_count}
Total Input Tokens: {self.total_input_tokens:,}
Total Output Tokens: {self.total_output_tokens:,}
Total Tokens: {self.total_tokens:,}
Total Estimated Cost: ${total_cost:.6f}
{'='*100}
        """
        
        print(summary)
        
        # Also append to log file
        with open(self.token_log_file, 'a', encoding='utf-8') as f:
            f.write("\n" + summary)
        
        return summary