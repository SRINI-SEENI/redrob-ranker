import json
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Reference date for ongoing roles
REF_DATE = datetime(2026, 7, 2)

def is_honeypot(cand):
    """
    Identifies impossible synthetic profiles (honeypots) to prevent disqualification.
    Check 1: Expert proficiency in a skill with 0 months of experience.
    Check 2: A job duration significantly exceeding its calendar start and end dates.
    """
    profile = cand.get("profile", {})
    career = cand.get("career_history", [])
    skills = cand.get("skills", [])
    
    # Check 1: Expert skill with 0 duration
    expert_zero_dur = [s for s in skills if s.get("proficiency") == "expert" and s.get("duration_months", 0) == 0]
    if len(expert_zero_dur) >= 1:
        return True
        
    # Check 2: Career job duration vs calendar date mismatch
    for job in career:
        start_s = job.get("start_date")
        end_s = job.get("end_date")
        dur_months = job.get("duration_months", 0)
        
        if start_s:
            try:
                start_d = datetime.strptime(start_s, "%Y-%m-%d")
                if end_s:
                    end_d = datetime.strptime(end_s, "%Y-%m-%d")
                else:
                    end_d = REF_DATE
                
                # Approximate number of months between start and end dates
                calendar_months = (end_d.year - start_d.year) * 12 + (end_d.month - start_d.month)
                if dur_months > calendar_months + 3:
                    return True
            except ValueError:
                pass
                
    return False

def load_candidates(filepath):
    """
    Loads candidates. Supports both JSON Array format (for sample files)
    and JSON Lines format (for full candidate pool).
    """
    path = Path(filepath)
    if not path.exists():
        print(f"Error: Candidate file {filepath} does not exist.")
        sys.exit(1)
        
    # Try reading first few characters to auto-detect JSON Array vs JSON Lines
    with open(path, "r", encoding="utf-8") as f:
        first_char = f.read(1).strip()
        while not first_char and f.read(1):
            first_char = f.read(1).strip()
            
    candidates = []
    if first_char == "[":
        # Load as JSON Array
        with open(path, "r", encoding="utf-8") as f:
            try:
                candidates = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON Array: {e}")
                sys.exit(1)
    else:
        # Load as JSON Lines
        with open(path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    candidates.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON Line at index {line_idx}: {e}")
                    sys.exit(1)
                    
    return candidates

def main():
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranker — Step 2")
    parser.add_argument("--candidates", required=True, help="Path to candidates file (.json or .jsonl)")
    parser.add_argument("--out", required=True, help="Path to write the submission CSV")
    args = parser.parse_args()
    
    print(f"Loading candidates from {args.candidates}...")
    candidates = load_candidates(args.candidates)
    print(f"Loaded {len(candidates)} candidates.")
    
    # Filter honeypots
    valid_candidates = []
    honeypot_count = 0
    for cand in candidates:
        if is_honeypot(cand):
            honeypot_count += 1
        else:
            valid_candidates.append(cand)
            
    print(f"Filtered out {honeypot_count} honeypot candidates. Valid candidates: {len(valid_candidates)}")

if __name__ == "__main__":
    main()
