from peft import LoraConfig
from trl import SFTTrainer
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from datasets import load_dataset
import torch

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
    # --- Configuration ---
    model_name = "Qwen/Qwen2-1.5B-Instruct"
    dataset_path = "generated_logs.jsonl"
    output_dir = "./fine-tuned-model"

    # --- Load Dataset ---
    print(f"Loading dataset from {dataset_path}...")
    dataset = load_dataset('json', data_files=dataset_path, split='train')

    # --- Format Dataset ---
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
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        optim="paged_adamw_32bit",
        save_steps=25,
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
        report_to="tensorboard"
    )

    # --- Trainer ---
    trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    peft_config=peft_config,
    args=training_args,
    formatting_func=lambda ex: ex["text"],
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
