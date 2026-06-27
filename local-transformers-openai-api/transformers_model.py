from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass(frozen=True)
class GenerationConfig:
    temperature: float = 0.0
    max_new_tokens: int = 128
    do_sample: bool = False


class LocalTransformerModel:
    def __init__(
        self,
        model_name_or_path: str,
        lora_path: str | None = None,
        device_map: str = "auto",
        torch_dtype: str = "auto",
        trust_remote_code: bool = True,
    ) -> None:
        self.model_name_or_path = model_name_or_path
        self.lora_path = lora_path
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name_or_path,
            trust_remote_code=trust_remote_code,
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name_or_path,
            device_map=device_map,
            torch_dtype=torch_dtype,
            trust_remote_code=trust_remote_code,
        )
        if lora_path:
            from peft import PeftModel

            self.model = PeftModel.from_pretrained(self.model, lora_path)
        self.model.eval()

    def apply_chat_template(self, messages: list[dict[str, str]]) -> str:
        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.chat_template:
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        return "\n".join(f"{message['role']}: {message['content']}" for message in messages) + "\nassistant:"

    @torch.inference_mode()
    def chat(self, messages: list[dict[str, str]], config: GenerationConfig) -> dict[str, Any]:
        prompt = self.apply_chat_template(messages)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        output_ids = self.model.generate(
            **inputs,
            max_new_tokens=config.max_new_tokens,
            temperature=config.temperature,
            do_sample=config.do_sample,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        generated_ids = output_ids[0][inputs["input_ids"].shape[-1] :]
        text = self.tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        return {
            "content": text,
            "prompt_tokens": int(inputs["input_ids"].shape[-1]),
            "completion_tokens": int(generated_ids.shape[-1]),
        }
