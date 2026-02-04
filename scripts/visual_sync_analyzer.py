import os
import sys
import json
import subprocess
import requests
from typing import Dict, Any, Optional

def get_git_diff() -> str:
    """Gets the diff of the last commit."""
    try:
        # Get diff of the last commit
        result = subprocess.run(
            ["git", "diff", "HEAD~1..HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except Exception as e:
        print(f"Error getting git diff: {e}")
        return ""

def analyze_diff_with_llm(diff_text: str) -> Optional[Dict[str, Any]]:
    """Sends the diff to an LLM for analysis."""
    api_key = os.environ.get("AKITA_API_KEY")
    if not api_key:
        print("AKITA_API_KEY not found in environment.")
        return None

    prompt = f"""
Você é um agente de análise de mudanças entre repositórios.

Contexto:
- Este repositório é o CORE do projeto (motor lógico).
- Existe um repositório secundário responsável apenas pela camada visual (React/UI).

Entrada:
- Um diff de código referente à última alteração no repositório CORE.

Tarefa:
1. Analise o diff e determine se a mudança é PUBLICAMENTE RELEVANTE para a camada visual, ou seja, se altera comportamento observável, interface pública (CLI, API), ou fluxos que exigem adaptação na UI.
2. Ignore mudanças internas (testes, refatorações invisíveis).

Diff:
{diff_text}

Saída (formato obrigatório em JSON):
{{
  "requires_visual_update": true | false,
  "summary": "Resumo curto e técnico da mudança",
  "reason": "Justificativa objetiva",
  "suggested_issue_title": "Título conciso para o issue",
  "suggested_issue_body": "Descrição clara do que deve ser feito no repositório visual"
}}
"""

    # Detect model and provider
    model_to_use = "gpt-4o-mini" # Default
    if api_key.startswith("AIza"):
        model_to_use = "gemini/gemini-3-flash-preview"
    elif api_key.startswith("sk-ant-"):
        model_to_use = "anthropic/claude-3-5-sonnet-latest"
    elif api_key.startswith("gsk_"):
        model_to_use = "groq/llama-3.3-70b-versatile"

    try:
        # We'll try to use litellm since it's already a dependency of the project
        import litellm
        print(f"Using model: {model_to_use}")
        response = litellm.completion(
            model=model_to_use,
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key,
            # Gemini support for json_object requires 1.5+ and specific config in LiteLLM
        )
        content = response.choices[0].message.content
        
        # Clean up Markdown formatting if present
        if content.startswith("```json"):
            content = content.replace("```json", "", 1).replace("```", "", 1).strip()
        
        return json.loads(content)
    except Exception as e:
        print(f"Error during LLM analysis: {e}")
        return None

def create_github_issue(issue_data: Dict[str, Any]):
    """Creates an issue in the visual repository."""
    token = os.environ.get("VISUAL_REPO_TOKEN")
    repo = "KerubinDev/AkitaLLM-Visual"
    
    if not token:
        print("VISUAL_REPO_TOKEN not found.")
        return

    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    payload = {
        "title": issue_data["suggested_issue_title"],
        "body": f"{issue_data['suggested_issue_body']}\n\n---\n**Racional do Core:** {issue_data['reason']}"
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 201:
        print(f"Successfully created issue in {repo}")
    else:
        print(f"Failed to create issue: {response.status_code} - {response.text}")

def main():
    diff = get_git_diff()
    if not diff:
        print("No diff found or error retrieving diff.")
        return

    print("Analyzing diff...")
    analysis = analyze_diff_with_llm(diff)
    
    if not analysis:
        print("Failed to analyze diff.")
        return

    print(f"Analysis result: {analysis.get('requires_visual_update')}")
    
    if analysis.get("requires_visual_update"):
        print("Creating issue in visual repository...")
        create_github_issue(analysis)
    else:
        print("No visual update required.")

if __name__ == "__main__":
    main()
