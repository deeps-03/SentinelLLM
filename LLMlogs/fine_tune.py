from peft import LoraConfig, AutoPeftModelForCausalLM
from trl import SFTTrainer
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from datasets import load_dataset
from huggingface_hub import login
import torch
import os

# --- Formatting Function ---
def formatting_prompts_func(example):
    text = f"""<|im_start|>system
You are an expert log analysis assistant. Your task is to classify log messages into one of the following
categories: 'incident', 'preventive_action', or 'normal'.
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
    return {"text": text}

def main():
    # --- Login to Hugging Face ---
    login(token="hf_your_token_here")

    # --- Configuration ---
    model_name = "Qwen/Qwen2-1.5B-Instruct"
    dataset_path = "generated_logs.jsonl"
    output_dir = "./fine-tuned-model"
    repo_id = "Deeps03/qwen2-1.5b-log-classifier"

    # --- Load Dataset ---
    print(f"Loading dataset from {dataset_path}...")
    dataset = load_dataset('json', data_files=dataset_path, split='train')
    dataset = dataset.map(formatting_prompts_func)

    # --- Tokenizer and Model ---
    print(f"Loading model and tokenizer for '{model_name}'...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True
    )

    peft_config = LoraConfig(
    lora_alpha=16,
    lora_dropout=0.1,
    r=64,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],  # 👈 correct for Qwen2
    )


    # --- Training Arguments ---
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,    # train for all epochs
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        optim="paged_adamw_32bit",
        save_steps=100,
        logging_steps=25,
        learning_rate=2e-4,
        weight_decay=0.001,
        fp16=False,
        bf16=False,
        max_grad_norm=0.3,
        max_steps=-1,
        warmup_ratio=0.03,
        group_by_length=True,
        lr_scheduler_type="constant",
        report_to="tensorboard",
        push_to_hub=False,  # we’ll push manually after merging
        save_total_limit=2   # keep only latest 2 checkpoints
    )

    # --- Trainer ---
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        args=training_args,
        formatting_func=lambda ex: ex["text"],
    )

    # --- Resume if checkpoint exists ---
    resume_from_checkpoint = None
    if os.path.exists(output_dir) and any("checkpoint" in d for d in os.listdir(output_dir)):
        resume_from_checkpoint = True
        print("🔄 Resuming training from last checkpoint...")
    else:
        print("🚀 Starting fresh training...")

    # --- Train the Model ---
    trainer.train(resume_from_checkpoint=resume_from_checkpoint)

    # --- Save LoRA Fine-tuned Model ---
    print(f"💾 Saving LoRA fine-tuned model to {output_dir}...")
    trainer.save_model(output_dir)

    # --- Merge LoRA with Base ---
    print("🔗 Merging LoRA with base model...")
    merged_model = AutoPeftModelForCausalLM.from_pretrained(
        output_dir,
        device_map="auto",
        torch_dtype=torch.bfloat16
    ).merge_and_unload()

    # --- Save Merged Model ---
    merged_output_dir = "./merged-model"
    merged_model.save_pretrained(merged_output_dir, safe_serialization=True)
    tokenizer.save_pretrained(merged_output_dir)

    # --- Push to Hugging Face ---
    print(f"☁️ Pushing merged model to Hugging Face repo {repo_id}...")
    merged_model.push_to_hub(repo_id)
    tokenizer.push_to_hub(repo_id)

    print("✅ Fine-tuning complete and model uploaded to Hugging Face!")

if __name__ == "__main__":
    main()
