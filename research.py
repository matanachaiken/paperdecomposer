import anthropic
import PyPDF2
import sys
import os

def extract_text(pdf_path):
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        print(f"Reading {len(reader.pages)} pages...")
        for i, page in enumerate(reader.pages):
            t = page.extract_text()
            if t:
                text += f"\n--- Page {i+1} ---\n{t}"
    return text

def decompose(pdf_text, api_key):
    client = anthropic.Anthropic(api_key=api_key)

    sections = {
        "OVERVIEW": "Extract the paper title, authors, year, and a 3-sentence plain-English summary of what this paper is about and why it matters.",
        "METHODOLOGY": "Describe the methodology in detail. What approach did the authors take? What techniques, models, or frameworks did they use?",
        "CORE ASSUMPTIONS": "What are the key assumptions the authors make? What must be true for their approach to work?",
        "DATA & INPUTS": "What data did the authors use? Where did it come from? How large is it? How was it collected or preprocessed?",
        "EXPERIMENTAL DESIGN": "How were the experiments structured? What were the conditions, baselines, and comparisons?",
        "EVALUATION METRICS": "What metrics did the authors use? Why did they choose these? What did they find?",
        "LIMITATIONS": "What are the limitations acknowledged? What additional weaknesses or gaps exist?",
        "KEY TAKEAWAYS": "What are the 3-5 most important things to know after reading this paper?"
    }

    output = ""
    for section, instruction in sections.items():
        print(f"Extracting {section}...")
        prompt = f"""You are an expert research analyst. Analyze this paper and answer:

{instruction}

Be specific and technical. Use bullet points. Be concise but complete.

Paper:
---
{pdf_text[:12000]}
---"""

        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        output += f"\n\n{'='*60}\n{section}\n{'='*60}\n{message.content[0].text}"

    return output

if __name__ == "__main__":
    api_key = "sk-ant-paste-your-key-here"

    pdf_path = sys.argv[1] if len(sys.argv) > 1 else input("Path to PDF: ").strip()

    if not os.path.exists(pdf_path):
        print("File not found.")
        sys.exit(1)

    text = extract_text(pdf_path)
    print("Sending to Claude...")
    result = decompose(text, api_key)

    output_path = pdf_path.replace(".pdf", "_breakdown.txt")
    with open(output_path, "w") as f:
        f.write(result)

    print(f"\nDone! Saved to: {output_path}")
    print(result)