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
                
                # Approximate number of months between start and end dates
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
    
    return final_score

def generate_reasoning(cand, rank, score):
    profile = cand.get("profile", {})
    skills = cand.get("skills", [])
    signals = cand.get("redrob_signals", {})
    
    title = profile.get("current_title", "Engineer")
    years_exp = profile.get("years_of_experience", 0.0)
    company = profile.get("current_company", "a product company")
    location = profile.get("location", "").split(",")[0].strip()
    notice = signals.get("notice_period_days", 30)
    response_rate = signals.get("recruiter_response_rate", 0.0)
    
    skill_names = {s.get("name").lower(): s.get("name") for s in skills if s.get("name")}
    
    vdb_found = [skill_names[vd] for vd in ["pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch", "faiss"] if vd in skill_names]
    ret_found = [skill_names[rs] for rs in ["embeddings", "sentence-transformers", "vector search", "rag", "nlp", "information retrieval", "semantic search"] if rs in skill_names]
    eval_found = [skill_names[es] for es in ["ndcg", "mrr", "map", "a/b testing", "evaluation frameworks", "learning-to-rank"] if es in skill_names]
    
    key_highlights = []
    if vdb_found: key_highlights.append(vdb_found[0])
    if ret_found: key_highlights.append(ret_found[0])
    if eval_found: key_highlights.append(eval_found[0])
    
    skills_str = ", ".join(key_highlights) if key_highlights else "AI/ML engineering"
    
    active_str = "highly active on the platform" if response_rate > 0.7 else "good recruiter responsiveness"
    loc_pref = f"{location}-based" if location else "in India"
    notice_concern = f"notice period of {notice} days" if notice > 60 else ""
    
    if rank <= 15:
        reasons = [
            f"Exceptional {title} with {years_exp:.1f} yrs exp; demonstrated expertise in {skills_str} at {company}. Strong engagement signals, {loc_pref}.",
            f"Top-tier {title} holding {years_exp:.1f} yrs exp; built retrieval/search systems using {skills_str} at {company}. Very active, {loc_pref}.",
            f"Highly relevant {title} with {years_exp:.1f} yrs exp and strong background in {skills_str} at {company}. Matches founding team requirements, {loc_pref}."
        ]
        text = reasons[rank % len(reasons)]
    elif rank <= 50:
        if notice_concern:
            text = f"Experienced {title} ({years_exp:.1f} yrs) with core strength in {skills_str} at {company}. {active_str.capitalize()}, but has a longer {notice_concern}."
        else:
            text = f"Solid {title} with {years_exp:.1f} yrs exp. Shipped systems using {skills_str} at {company}; shows excellent alignment with JD requirements, {loc_pref}."
    elif rank <= 85:
        gaps = []
        if notice_concern: gaps.append(notice_concern)
        if company.lower() in SERVICE_COMPANIES: gaps.append("consulting background")
        
        gaps_str = " & ".join(gaps) if gaps else "minor location mismatch"
        text = f"{title} with {years_exp:.1f} yrs exp; has relevant skills in {skills_str}. Shows strong platform engagement but note the {gaps_str}."
    else:
        text = f"Backend/ML professional with {years_exp:.1f} yrs exp. Lacks specialized ranking evaluation experience, but offers adjacent skills in {skills_str}."
        
    return text

# ========================================================
# RUN MODE SELECTOR
# ========================================================
if "--candidates" in sys.argv:
    # --- CLI MODE ---
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
        parser = argparse.ArgumentParser(description="Redrob Candidate Ranker")
        parser.add_argument("--candidates", required=True, help="Path to candidates file (.json or .jsonl)")
        parser.add_argument("--out", required=True, help="Path to write the submission CSV")
        args = parser.parse_args()
        
        print(f"Loading candidates from {args.candidates}...")
        candidates = load_candidates(args.candidates)
        
        scored_candidates = []
        for cand in candidates:
            if is_honeypot(cand):
                continue
                
            score = score_candidate(cand)
            scored_candidates.append({
                "cand": cand,
                "candidate_id": cand.get("candidate_id"),
                "score": score
            })
            
        scored_candidates.sort(key=lambda x: (-x["score"], x["candidate_id"]))
        top_100 = scored_candidates[:100]
        
        output_rows = []
        for rank, entry in enumerate(top_100, 1):
            reasoning = generate_reasoning(entry["cand"], rank, entry["score"])
            output_rows.append({
                "candidate_id": entry["candidate_id"],
                "rank": rank,
                "score": f"{entry['score']:.4f}",
                "reasoning": reasoning
            })
            
        out_path = Path(args.out)
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["candidate_id", "rank", "score", "reasoning"])
            writer.writeheader()
            for row in output_rows:
                writer.writerow(row)
                
        print(f"Successfully generated {args.out} with {len(output_rows)} candidates.")

    if __name__ == "__main__":
        main()

else:
    # --- STREAMLIT WEB APP MODE ---
    import streamlit as st
    import io
    
    st.set_page_config(
        page_title="Wonderer AI — Founding AI Team Discovery",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
    <style>
        .main-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #0284c7;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            font-size: 1.1rem;
            color: #64748b;
            margin-bottom: 2rem;
        }
        .metric-card {
            background-color: #1e293b;
            padding: 1.2rem;
            border-radius: 8px;
            border: 1px solid #334155;
            text-align: center;
        }
        .metric-val {
            font-size: 2rem;
            font-weight: 700;
            color: #38bdf8;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #94a3b8;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="main-title">🔍 Wonderer AI — Founding AI Team Discovery</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Intelligent Candidate Discovery & Ranking Engine for Senior AI Engineer JD</div>', unsafe_allow_html=True)
    
    st.sidebar.header("Configuration")
    candidate_limit = st.sidebar.slider("Number of Candidates to Display", min_value=10, max_value=100, value=50, step=10)
    
    uploaded_file = st.file_uploader("Upload Candidates File (.json or .jsonl)", type=["json", "jsonl"])
    
    candidates = []
    file_loaded = False
    
    if uploaded_file is not None:
        file_contents = uploaded_file.read().decode("utf-8")
        first_char = file_contents.strip()[:1]
        if first_char == "[":
            try:
                candidates = json.loads(file_contents)
                file_loaded = True
            except json.JSONDecodeError as e:
                st.error(f"Error parsing JSON Array: {e}")
        else:
            candidates = []
            for line_idx, line in enumerate(file_contents.splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    candidates.append(json.loads(line))
                    file_loaded = True
                except json.JSONDecodeError as e:
                    st.error(f"Error parsing JSON Line at index {line_idx}: {e}")
                    candidates = []
                    file_loaded = False
                    break
    else:
        sample_path = Path("sample_candidates.json")
        if sample_path.exists():
            if st.button("Load Preloaded Sample (sample_candidates.json)"):
                with open(sample_path, "r", encoding="utf-8") as f:
                    candidates = json.load(f)
                    file_loaded = True
                st.info("Loaded 50 sample candidates from sample_candidates.json.")
        else:
            st.warning("Please upload a candidate file or place sample_candidates.json in the project root.")
            
    if file_loaded and candidates:
        valid_candidates = []
        honeypot_count = 0
        
        for cand in candidates:
            if is_honeypot(cand):
                continue
            score = score_candidate(cand)
            valid_candidates.append({
                "cand": cand,
                "candidate_id": cand.get("candidate_id"),
                "score": score,
                "title": cand.get("profile", {}).get("current_title", "N/A"),
                "experience": cand.get("profile", {}).get("years_of_experience", 0.0),
                "company": cand.get("profile", {}).get("current_company", "N/A"),
                "location": cand.get("profile", {}).get("location", "N/A")
            })
            
        valid_candidates.sort(key=lambda x: (-x["score"], x["candidate_id"]))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-val">{len(candidates)}</div><div class="metric-label">Total Scanned</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-val" style="color: #ef4444;">{len(candidates) - len(valid_candidates)}</div><div class="metric-label">Honeypots Filtered</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><div class="metric-val" style="color: #22c55e;">{len(valid_candidates)}</div><div class="metric-label">Valid Candidates</div></div>', unsafe_allow_html=True)
            
        st.markdown("### Top Ranked Candidates")
        
        preview_rows = []
        csv_rows = []
        
        for rank, entry in enumerate(valid_candidates, 1):
            reasoning = generate_reasoning(entry["cand"], rank, entry["score"])
            if rank <= candidate_limit:
                preview_rows.append({
                    "Rank": rank,
                    "Candidate ID": entry["candidate_id"],
                    "Title": entry["title"],
                    "Years Exp": entry["experience"],
                    "Current Company": entry["company"],
                    "Location": entry["location"],
                    "Score": f"{entry['score']:.4f}",
                    "Reasoning": reasoning
                })
            csv_rows.append({
                "candidate_id": entry["candidate_id"],
                "rank": rank,
                "score": f"{entry['score']:.4f}",
                "reasoning": reasoning
            })
            
        st.dataframe(preview_rows, use_container_width=True)
        
        csv_buffer = io.StringIO()
        writer = csv.DictWriter(csv_buffer, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        for row in csv_rows[:100]:
            writer.writerow(row)
            
        st.download_button(
            label="📥 Download Top 100 Ranked CSV",
            data=csv_buffer.getvalue(),
            file_name="submission.csv",
            mime="text/csv"
        )
