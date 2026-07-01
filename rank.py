import json
import csv
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Reference date for ongoing roles
REF_DATE = datetime(2026, 7, 2)

# Service companies list to penalize / exclude
SERVICE_COMPANIES = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", 
    "capgemini", "hcl", "mphasis", "tech mahindra"
}

# Preferred locations in India
PREFERRED_LOCATIONS = {
    "pune", "noida", "delhi", "delhi ncr", "ncr", "mumbai", "hyderabad", "bangalore"
}

def is_honeypot(cand):
    profile = cand.get("profile", {})
    career = cand.get("career_history", [])
    education = cand.get("education", [])
    skills = cand.get("skills", [])
    
    # 1. Expert skill with 0 duration
    expert_zero_dur = [s for s in skills if s.get("proficiency") == "expert" and s.get("duration_months", 0) == 0]
    if len(expert_zero_dur) >= 1:
        return True
        
    # 2. Career job duration vs calendar date mismatch
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
                
                calendar_months = (end_d.year - start_d.year) * 12 + (end_d.month - start_d.month)
                if dur_months > calendar_months + 3:
                    return True
            except ValueError:
                pass
                
    return False

def score_candidate(cand):
    profile = cand.get("profile", {})
    career = cand.get("career_history", [])
    skills = cand.get("skills", [])
    signals = cand.get("redrob_signals", {})
    
    score = 0.0
    
    # --- 1. TITLE MATCH (Max 25 pts) ---
    title = profile.get("current_title", "").lower()
    title_score = 0.0
    if "ai engineer" in title or "machine learning engineer" in title or "ml engineer" in title:
        title_score = 25.0
    elif "data scientist" in title:
        title_score = 20.0
    elif "nlp" in title or "search" in title or "ranking" in title or "retrieval" in title:
        title_score = 22.0
    elif "backend" in title or "software engineer" in title or "full stack" in title:
        title_score = 15.0
    score += title_score
    
    # --- 2. EXPERIENCE SCORE (Max 15 pts) ---
    years_exp = profile.get("years_of_experience", 0.0)
    exp_score = 0.0
    if 6.0 <= years_exp <= 8.0:
        exp_score = 15.0
    elif 5.0 <= years_exp < 6.0 or 8.0 < years_exp <= 9.0:
        exp_score = 12.0
    elif 4.0 <= years_exp < 5.0 or 9.0 < years_exp <= 11.0:
        exp_score = 8.0
    elif years_exp >= 1.0:
        exp_score = 3.0
    score += exp_score
    
    # --- 3. COMPANY BACKGROUND (Max 15 pts) ---
    # Check if they have ONLY worked at service companies
    companies_worked = [job.get("company", "").strip().lower() for job in career if job.get("company")]
    if not companies_worked:
        companies_worked = [profile.get("current_company", "").strip().lower()]
        
    all_service = all(c in SERVICE_COMPANIES for c in companies_worked) if companies_worked else False
    has_product = any(c not in SERVICE_COMPANIES for c in companies_worked) if companies_worked else True
    
    company_score = 15.0
    if all_service:
        company_score = 0.0
    elif has_product:
        current_comp = profile.get("current_company", "").strip().lower()
        if current_comp not in SERVICE_COMPANIES:
            company_score = 15.0
        else:
            company_score = 10.0
    score += company_score
    
    # --- 4. SKILLS SCORE (Max 25 pts) ---
    skill_names = {s.get("name", "").lower(): s for s in skills}
    
    # Check vector DBs
    vector_dbs = {"pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch", "faiss"}
    has_vector_db = any(vd in skill_names for vd in vector_dbs)
    
    # Check retrieval / embeddings
    retrieval_skills = {"embeddings", "sentence-transformers", "vector search", "rag", "nlp", "information retrieval", "semantic search"}
    has_retrieval = any(rs in skill_names for rs in retrieval_skills)
    
    # Check python
    has_python = "python" in skill_names
    
    # Check evaluations
    eval_skills = {"ndcg", "mrr", "map", "a/b testing", "evaluation frameworks", "learning-to-rank"}
    has_eval = any(es in skill_names for es in eval_skills)
    
    # Nice-to-haves
    nice_skills = {"lora", "qlora", "peft", "llm fine-tuning", "xgboost", "kubernetes", "spark", "ray", "distributed systems"}
    num_nice = sum(1 for ns in nice_skills if ns in skill_names)
    
    skills_score = 0.0
    if has_python:
        skills_score += 5.0
    if has_vector_db:
        skills_score += 7.0
    if has_retrieval:
        skills_score += 7.0
    if has_eval:
        skills_score += 6.0
        
    skills_score += min(5.0, num_nice * 1.5)
    score += skills_score
    
    # --- 5. BEHAVIORAL AND REDROB SIGNALS (Max 20 pts) ---
    # Location
    loc = profile.get("location", "").lower() + ", " + profile.get("country", "").lower()
    loc_score = 0.0
    if any(pl in loc for pl in PREFERRED_LOCATIONS):
        loc_score = 5.0
    score += loc_score
    
    # Active & response rate multiplier
    response_rate = signals.get("recruiter_response_rate", 0.0)
    open_flag = signals.get("open_to_work_flag", False)
    notice = signals.get("notice_period_days", 90)
    
    # Active date recency
    active_s = signals.get("last_active_date", "2020-01-01")
    try:
        active_d = datetime.strptime(active_s, "%Y-%m-%d")
        days_since_active = (REF_DATE - active_d).days
        if days_since_active <= 30:
            active_score = 5.0
        elif days_since_active <= 90:
            active_score = 3.0
        else:
            active_score = 0.0
    except ValueError:
        active_score = 0.0
    score += active_score
    
    resp_score = response_rate * 5.0
    score += resp_score
    
    if open_flag:
        score += 3.0
        
    if notice <= 30:
        score += 2.0
    elif notice <= 60:
        score += 1.0
        
    # Scale score to 0.0 - 1.0 range
    final_score = score / 100.0
    
    # Placeholder reasoning for Step 3
    reasoning = f"AI Engineer with {years_exp:.1f} years of experience."
    
    return final_score, reasoning

def load_candidates(filepath):
    path = Path(filepath)
    if not path.exists():
        print(f"Error: Candidate file {filepath} does not exist.")
        sys.exit(1)
        
    with open(path, "r", encoding="utf-8") as f:
        first_char = f.read(1).strip()
        while not first_char and f.read(1):
            first_char = f.read(1).strip()
            
    candidates = []
    if first_char == "[":
        with open(path, "r", encoding="utf-8") as f:
            try:
                candidates = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON Array: {e}")
                sys.exit(1)
    else:
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
    parser = argparse.ArgumentParser(description="Redrob Candidate Ranker — Step 3")
    parser.add_argument("--candidates", required=True, help="Path to candidates file (.json or .jsonl)")
    parser.add_argument("--out", required=True, help="Path to write the submission CSV")
    args = parser.parse_args()
    
    print(f"Loading candidates from {args.candidates}...")
    candidates = load_candidates(args.candidates)
    
    scored_candidates = []
    for cand in candidates:
        if is_honeypot(cand):
            continue
            
        score, reasoning = score_candidate(cand)
        scored_candidates.append({
            "candidate_id": cand.get("candidate_id"),
            "score": score,
            "reasoning": reasoning
        })
        
    # Sort candidates by score descending, then candidate_id ascending (deterministic tie-breaker)
    scored_candidates.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    
    # Get top 100
    top_100 = scored_candidates[:100]
    
    # Add rank
    for rank, entry in enumerate(top_100, 1):
        entry["rank"] = rank
        
    # Output to CSV
    out_path = Path(args.out)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        for entry in top_100:
            writer.writerow({
                "candidate_id": entry["candidate_id"],
                "rank": entry["rank"],
                "score": f"{entry['score']:.4f}",
                "reasoning": entry["reasoning"]
            })
            
    print(f"Successfully generated {args.out} with {len(top_100)} candidates.")

if __name__ == "__main__":
    main()
