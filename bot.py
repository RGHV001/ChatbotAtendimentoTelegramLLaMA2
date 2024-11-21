import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from model import generate_text
from config import TELEGRAM_TOKEN
from db import (create_connection, get_appointments_in_next_24_hours, 
                mark_reminder_sent, get_appointment_by_telegram_id, 
                save_dialogue, delete_appointment, check_availability, 
                add_appointment, find_next_available_time, get_appointment_by_patient_id, get_patient_by_telegram_id)
from dateutil import parser
from datetime import datetime, timedelta
import pytz
import re
import logging
from colorama import Fore, Style, init


# Inicializa o uso de cores no terminal
init()


# Configuração básica de logging com cores
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.INFO
)

#Formata os logs para mostrar o horário de Brasília e aplicar cores.
class BrazilFormatter(logging.Formatter):    
    def format(self, record):
        if record.levelname == 'ERROR':
            record.msg = f"{Fore.RED}{record.msg}{Style.RESET_ALL}"
        elif record.levelname == 'INFO':
            record.msg = f"{Fore.CYAN}{record.msg}{Style.RESET_ALL}"
        elif record.levelname == 'WARNING':
            record.msg = f"{Fore.YELLOW}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

# Aplicar o formato com cores a todos os handlers
for handler in logging.getLogger().handlers:
    handler.setFormatter(BrazilFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Fuso horário de Brasília
BRAZIL_TZ = pytz.timezone("America/Sao_Paulo")

# Estados da conversa
NEW_DATE, CONFIRM_REMARK = range(2)

# Função para converter timedelta em horas e minutos
def format_timedelta_as_time(timedelta_obj):
    """Converte um objeto timedelta para o formato HH:MM."""
    total_seconds = int(timedelta_obj.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}"

# Função para o LLaMA 2 gerar respostas
def llama_generate_response(prompt):
    return generate_text(prompt)

# Substitui expressões comuns para o bot entender.
def replace_common_expressions(user_input):
    now = datetime.now(BRAZIL_TZ)
    
    expressões = {
        "amanhã": (now + timedelta(days=1)).strftime('%d/%m/%Y'),
        "hoje": now.strftime('%d/%m/%Y'),
        "daqui a uma semana": (now + timedelta(weeks=1)).strftime('%d/%m/%Y'),
    }
    
    # Para expressões como 'daqui a X dias'
    dias_match = re.search(r'daqui a (\d+) dias', user_input)
    if dias_match:
        dias = int(dias_match.group(1))
        nova_data = (now + timedelta(days=dias)).strftime('%d/%m/%Y')
        user_input = re.sub(r'daqui a \d+ dias', nova_data, user_input)

    # Substituir expressões padrão
    for expressão, data in expressões.items():
        user_input = user_input.replace(expressão, data)

    return user_input

# Tenta interpretar a data e hora de um texto fornecido pelo usuário.
def parse_date_time(user_input):
    try:
        logging.info(f"{Fore.YELLOW}Recebido input para análise de data e hora: {user_input}{Style.RESET_ALL}")
        
        # Substituir expressões comuns e limpar o input
        user_input = replace_common_expressions(user_input.lower())
        user_input = " ".join(user_input.split())  # Remover espaços extras
        
        # Tenta analisar a data usando o parser e converter o formato
        parsed_datetime = parser.parse(user_input, dayfirst=True, fuzzy=True)
        new_date = convert_date_format(parsed_datetime.strftime('%d/%m/%Y'))  # Converte para formato YYYY-MM-DD
        new_time = parsed_datetime.strftime('%H:%M:%S')  # Horário em HH:MM:SS
        
        logging.info(f"{Fore.GREEN}Data e hora interpretadas com sucesso: {new_date} {new_time}{Style.RESET_ALL}")
        return new_date, new_time

    except ValueError:
        logging.error(f"{Fore.RED}Falha ao interpretar a data e hora fornecidas: {user_input}{Style.RESET_ALL}")
        return None, None

# Função chamada quando o comando /start é enviado
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Olá! Eu sou um bot de atendimento, como posso ajudar?')

# Função para enviar lembretes aos pacientes com horário no padrão brasileiro
async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    appointments = get_appointments_in_next_24_hours()
    
    for appointment in appointments:
        appointment_id, appointment_date, appointment_time, name, telegram_id = appointment
        
        # Convertendo a data para o formato brasileiro
        formatted_date = appointment_date.strftime('%d/%m/%Y')  # Formato: DD/MM/YYYY
        
        # Convertendo o timedelta em um formato de horas e minutos
        formatted_time = format_timedelta_as_time(appointment_time)
        
        # Mensagem humanizada com a data e hora no padrão brasileiro
        reminder_message = f"Olá {name}, lembrete do seu compromisso marcado para o dia {formatted_date} às {formatted_time}. Por favor, confirme, remarque ou cancele sua consulta."
        
        await context.bot.send_message(chat_id=telegram_id, text=reminder_message)
        mark_reminder_sent(appointment_id)

# Função para analisar a intenção do paciente
def analyze_intent(patient_response):
    response = patient_response.lower()

    if "confirmar" in response or "confirmo" in response or "sim" in response:
        return "confirmar"
    elif "remarcar" in response or "adiar" in response or "mudar" in response:
        return "remarcar"
    elif "cancelar" in response or "não posso" in response or "desmarcar":
        return "cancelar"
    else:
        return "intenção não identificada"

# Função para capturar a resposta do paciente e identificar a intenção
async def handle_patient_response(update: Update, context):
    """Captura a resposta do paciente e identifica a intenção"""
    patient_response = update.message.text
    patient_telegram_id = update.message.chat_id
    
    # Analisar a intenção do paciente
    intent = analyze_intent(patient_response)
    
    # Exibir a intenção no terminal
    print(f"Intenção identificada: {intent}")
    
    # Obter o compromisso do paciente
    appointment = get_appointment_by_telegram_id(patient_telegram_id)

    if appointment:
        # Ajustar para capturar os quatro valores retornados
        appointment_id, appointment_date, appointment_time, patient_id = appointment
    else:
        await update.message.reply_text("Não encontrei um compromisso agendado para você.")
        return
    
    # Se o paciente confirmou, nada muda
    if intent == "confirmar":
        response = llama_generate_response(f"O paciente confirmou que virá à consulta, nao diga nada antes da resposta, apenas diga que entendeu e a consulta esta confirmada, nada mais.")
    
    # Se o paciente deseja cancelar, apaga o compromisso
    elif intent == "cancelar":
        delete_appointment(appointment_id)
        response = llama_generate_response("O paciente cancelou a consulta. Marcar como cancelada e encerrar a conversa.")

    # Se o paciente deseja remarcar, pergunta o novo horário
    elif intent == "remarcar":
        response = llama_generate_response("O paciente deseja remarcar. Perguntar apenas para qual data remarcar.")
        await update.message.reply_text(response)
        
        # Iniciar o estado de aguardo para o novo horário
        return NEW_DATE

    else:
        response = llama_generate_response("A intenção do paciente não foi identificada, peça mais detalhes.")

    # Salvar o diálogo no banco de dados
    save_dialogue(patient_telegram_id, patient_response, response)

    # Envia a resposta gerada ao paciente
    await update.message.reply_text(response)

    return ConversationHandler.END

# Verifica se o formato do input é DD/MM/YYYY e converte para YYYY-MM-DD
def convert_date_format(user_date):
    try:
        parsed_date = datetime.strptime(user_date, '%d/%m/%Y')
        return parsed_date.strftime('%Y-%m-%d')
    except ValueError:
        return None

# Função para lidar com o novo horário
async def handle_reschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_response = update.message.text
    logging.info(f"{Fore.YELLOW}Recebido novo horário para remarcar: {new_response}{Style.RESET_ALL}")
    
    # Obter o patient_id associado ao user_id do Telegram (from_user.id)
    patient = get_patient_by_telegram_id(update.message.from_user.id)
    
    if not patient:
        await update.message.reply_text("Não encontrei nenhum paciente associado ao seu Telegram.")
        return ConversationHandler.END
    
    patient_id = patient[0]  # O patient_id será retornado
    
    logging.info(f"Patient ID encontrado: {patient_id}")
    
    # busca o compromisso associado a esse patient_id
    appointment = get_appointment_by_patient_id(patient_id)
    if not appointment:
        await update.message.reply_text("Não encontrei nenhum compromisso para você.")
        return ConversationHandler.END
    
    logging.info(f"Compromisso encontrado: {appointment}")
    
    appointment_id, original_date, original_time, patient_id = appointment
    # Tentar interpretar a nova data e hora
    new_date, new_time = parse_date_time(new_response)
    
    if not new_date:
        await update.message.reply_text("Data inválida, por favor tente novamente.")
        return NEW_DATE

    if not new_time:
        # Se a hora não for especificada, mantém o horário original
        new_time = original_time

    # Verifica se há disponibilidade para o novo horário
    if check_availability(new_date, new_time):
        delete_appointment(appointment_id)  # Apaga o compromisso antigo
        add_appointment(patient_id, new_date, new_time)  # Adiciona o novo compromisso para o mesmo paciente
        response = llama_generate_response(f"Consulta remarcada para {new_date} às {new_time}. Agradecer e encerrar a conversa")
        logging.info(f"{Fore.GREEN}Consulta remarcada com sucesso para {new_date} às {new_time}{Style.RESET_ALL}")
    else:
        # Sugere o próximo horário disponível se o solicitado não estiver livre
        next_time = find_next_available_time(new_date)
        if next_time:
            response = llama_generate_response(f"O horário solicitado está ocupado. O próximo horário disponível é {next_time}. Gostaria de marcar para esse horário?")
        else:
            response = llama_generate_response(f"Não há horários disponíveis para a data {new_date}. Por favor, escolha outra.")
    
    # Envia a resposta gerada pelo modelo
    await update.message.reply_text(response, reply_markup=ReplyKeyboardRemove())
    save_dialogue(update.message.from_user.id, new_response, response)

    return ConversationHandler.END

# Função principal para iniciar o bot e agendar os lembretes
def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    job_queue = application.job_queue

    now_brazil = datetime.now(BRAZIL_TZ)
    first_check = now_brazil + timedelta(seconds=60)
    first_check_utc = first_check.astimezone(pytz.utc)

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_patient_response)],
        states={
            NEW_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reschedule)],
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)
    job_queue.run_repeating(send_reminders, interval=30, first=first_check_utc)
    application.run_polling()

if __name__ == "__main__":
    main()
