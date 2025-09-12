import json
import argparse

# Define keywords for each label
# The order matters: we check for incident first, then preventive_action.
INCIDENT_KEYWORDS = [
    "failed", "error", "unreachable", "crashed", "denied", "timeout", 
    "exception", "500 internal server error", "terminated unexpectedly", "dead-lettered"
]

PREVENTIVE_ACTION_KEYWORDS = [
    "warning", "low", "high", "approaching", "throttling", "restarting",
    "nearing", "delayed", "almost consumed", "response time high", "retrying",
    "expiring soon", "packet loss"
]

def label_log_message(message):
    """Labels a single log message based on keywords."""
    msg_lower = message.lower()
    
    for keyword in INCIDENT_KEYWORDS:
        if keyword in msg_lower:
            return "incident"
            
    for keyword in PREVENTIVE_ACTION_KEYWORDS:
        if keyword in msg_lower:
            return "preventive_action"
            
    return "normal"

def main():
    parser = argparse.ArgumentParser(description="Programmatically label logs based on keywords.")
    parser.add_argument("input_file", type=str, help="Path to the input JSONL file with logs.")
    parser.add_argument("output_file", type=str, help="Path to the output JSONL file for labeled logs.")
    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output_file

    print(f"Reading logs from '{input_file}'...")

    labeled_logs = []
    label_counts = {"incident": 0, "preventive_action": 0, "normal": 0}

    with open(input_file, "r") as f:
        for line in f:
            try:
                log_entry = json.loads(line)
                message = log_entry.get("message", "")
                
                # Get the new label
                new_label = label_log_message(message)
                
                # Update the log entry with the new label
                log_entry["label"] = new_label
                
                labeled_logs.append(log_entry)
                label_counts[new_label] += 1

            except json.JSONDecodeError:
                print(f"Warning: Skipping malformed line: {line.strip()}")

    print(f"Writing {len(labeled_logs)} labeled logs to '{output_file}'...")

    with open(output_file, "w") as f:
        for log_entry in labeled_logs:
            f.write(json.dumps(log_entry) + "\n")

    print("\nLabeling complete.")
    print("--- Label Distribution ---")
    for label, count in label_counts.items():
        print(f"  {label}: {count}")
    print("------------------------")
    print(f"\nPlease review a sample of '{output_file}' to ensure the quality of the labels.")

if __name__ == "__main__":
    main()