import os
from llama_cpp import Llama
from colorama import Fore, Style

# Caminho onde o modelo LLaMA será salvo localmente
MODEL_PATH = "<Caminho para o diretório do projeto no sistema local>llama.cpp/models/llama-2-7b-chat.Q4_K_M.gguf"

# Carrega o modelo Llama
def load_model():
    llm = Llama(model_path=MODEL_PATH, n_ctx=4096)
    return llm


# Gera texto a partir do modelo Llama
def generate_text(user_prompt):
    llm = load_model()

    # Prompt simplificado
    structured_prompt = (
        f"[INST] Você é uma secretária de um consultório médico. Responda as solicitação de forma breve e educada. O paciente enviou a seguinte solicitação: {user_prompt}. [/INST]"
    )

    try:
        print(f"{Fore.CYAN}Prompt enviado ao modelo: {structured_prompt}{Style.RESET_ALL}")  # Log do prompt

        # Gera a resposta com um limite de tokens e tokens de parada claros
        output = llm(structured_prompt, max_tokens=100, stop=["\n", "</s>"])

        # Captura a resposta gerada
        generated_text = output['choices'][0]['text'].strip()
        print(f"{Fore.GREEN}Tokens gerados: {generated_text}{Style.RESET_ALL}")  # Log da resposta

        # Verifica se a resposta está vazia ou repetitiva
        response = generated_text if generated_text else "Desculpe, não consegui entender sua pergunta. Tente novamente."

    except Exception as e:
        response = f"Desculpe, ocorreu um erro: {str(e)}"

    return response

