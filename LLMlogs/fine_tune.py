import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from peft import LoraConfig
from trl import SFTTrainer

def main():
    # --- Configuration ---
    model_name = "Qwen/Qwen2-1.5B-Instruct"
    dataset_path = "/Users/deepaksuresh/Desktop/SentinelLLM/generated_logs.jsonl"
    output_dir = "./fine-tuned-model"
    
    # --- Load Dataset ---
    print(f"Loading dataset from {dataset_path}...")
    dataset = load_dataset("json", data_files=dataset_path, split="train")

    # --- Tokenizer and Model ---
    print(f"Loading model and tokenizer for '{model_name}'...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True
    )

    # --- Formatting Function ---
    def formatting_prompts_func(example):
        text = f"""<|im_start|>system
You are an expert log analysis assistant. Your task is to classify log messages into one of the following categories: 'incident', 'preventive_action', or 'normal'.
- 'incident': Indicates a critical error, failure, or a significant security breach that requires immediate attention.
- 'preventive_action': Indicates a warning or a potential issue that should be addressed to prevent future problems.
- 'normal': Indicates a routine operational message.
Provide only the classification category as a single word.
<|im_end|>
<|im_start|>user
Classify the following log message:
Log Entry: {example['message']}
<|im_end|>
<|im_start|>assistant
{example['label']}
<|im_end|>"""
        return [text]

    # --- PEFT Configuration ---
    peft_config = LoraConfig(
        lora_alpha=16,
        lora_dropout=0.1,
        r=64,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # --- Training Arguments ---
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=1,   # safe for limited GPUs
        gradient_accumulation_steps=1,
        optim="adamw_torch",             # avoids bitsandbytes dependency
        save_steps=25,
        logging_steps=25,
        learning_rate=2e-4,
        weight_decay=0.001,
        fp16=False,                      # enable if GPU supports fp16
        bf16=False,                      # enable if GPU supports bf16 (A100, RTX 40xx)
        max_grad_norm=0.3,
        max_steps=-1,
        warmup_ratio=0.03,
        group_by_length=True,
        lr_scheduler_type="constant",
        report_to="tensorboard"
    )

    # --- Trainer ---
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        max_seq_length=tokenizer.model_max_length,
        tokenizer=tokenizer,
        args=training_args,
        formatting_func=formatting_prompts_func,
    )

    # --- Train the Model ---
    print("Starting model fine-tuning...")
    trainer.train()

    # --- Save the Fine-tuned Model ---
    print(f"Saving the fine-tuned model to {output_dir}...")
    trainer.save_model(output_dir)
    print("Fine-tuning complete!")

if __name__ == "__main__":
    main()
