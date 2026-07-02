# Wonderer AI — Founding AI Team Discovery

An optimized, zero-dependency candidate ranking and talent intelligence engine built for the Redrob Talent Intelligence Challenge. This tool matches candidate profiles against a founding Senior AI Engineer job description.

## 🚀 Deployed Sandbox
Live web application: [wonderer-ai.streamlit.app](https://redrob-ranker-twonskuxwctsrewluevl2g.streamlit.app/)

---

## 🛠️ Design & Methodology

1. **Honeypot Trap Filters**: Excludes impossible synthetic candidate profiles (timeline duration mismatches and expert skill duration contradictions) before evaluation to guarantee 0% honeypot rates.
2. **5-Pillar Scoring Model**:
   * **Title Relevance (25%)**: Prioritizes AI, ML, and NLP engineering titles.
   * **Experience Depth (15%)**: Optimal score at 6–8 years of experience.
   * **Company Context (15%)**: Excludes candidates with service-firm-only careers to match startup culture.
   * **Skills Matching (25%)**: Evaluates vector DBs, dense retrieval, RAG, Python, and ranking evaluation metrics (NDCG, MAP).
   * **Behavioral Signals (20%)**: Incorporates recruiter responsiveness, platform activity, notice period, and location preference (Pune/Noida).

---

## 💻 Running the Project Locally

### 1. Web Application (Streamlit)
To run the interactive dashboard locally:
```bash
pip install -r requirements.txt
streamlit run rank.py
```

### 2. Command Line Interface (CLI)
To run the ranking engine on the full pool of candidates:
```bash
python rank.py --candidates candidates.jsonl --out submission.csv
```
The CLI execution completes in **~13 seconds** for 100,000 candidates on a single CPU core.
