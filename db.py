import mysql.connector
from mysql.connector import Error
import datetime
import pytz


# Fuso horário de Brasília (GMT-3)
BRAZIL_TZ = pytz.timezone("America/Sao_Paulo")

# Informações de conexão com o banco de dados
def create_connection():
    """Estabelece a conexão com o banco de dados MySQL"""
    try:
    connection = mysql.connector.connect(
        host="<endereço_host>",
        user="<usuario>",
        password="<senha>",
        database="<nome_do_banco>"
    	)
        if connection.is_connected():
            print("Conexão ao banco de dados MySQL estabelecida com sucesso")
        return connection
    except Error as e:
        print(f"Erro ao conectar ao MySQL: {e}")
        return None

# Função para obter compromissos nas próximas 24 horas e que ainda não receberam lembretes
def get_appointments_in_next_24_hours():
    """Recupera compromissos marcados nas próximas 24 horas que ainda não receberam lembrete"""
    connection = create_connection()
    if connection is not None:
        try:
            cursor = connection.cursor()
            now = datetime.datetime.now(BRAZIL_TZ)
            next_24_hours = now + datetime.timedelta(hours=24)

            # Consulta para encontrar compromissos nas próximas 24 horas e cujo lembrete ainda não foi enviado
            query = """
                SELECT a.appointment_id, a.appointment_date, a.appointment_time, p.name, p.telegram_id
                FROM appointments a
                JOIN patients p ON a.patient_id = p.patient_id
                WHERE a.appointment_date = %s AND a.reminder_sent = FALSE
            """
            cursor.execute(query, (next_24_hours.date(),))
            appointments = cursor.fetchall()
            return appointments
        except Error as e:
            print(f"Erro ao buscar compromissos: {e}")
        finally:
            cursor.close()
            connection.close()
    return []

# Função para armazenar diálogo no banco de dados
def save_dialogue(telegram_id, user_message, bot_response):
    """Armazena o diálogo no banco de dados"""
    connection = create_connection()
    if connection is not None:
        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO dialogues (telegram_id, user_message, bot_response)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (telegram_id, user_message, bot_response))
            connection.commit()
        except Error as e:
            print(f"Erro ao salvar diálogo: {e}")
        finally:
            cursor.close()
            connection.close()

# Apaga um compromisso do banco de dados
def delete_appointment(appointment_id):
    connection = create_connection()
    if connection is not None:
        try:
            cursor = connection.cursor()
            query = "DELETE FROM appointments WHERE appointment_id = %s"
            cursor.execute(query, (appointment_id,))
            connection.commit()
        except Error as e:
            print(f"Erro ao apagar compromisso: {e}")
        finally:
            cursor.close()
            connection.close()

# Verifica se há disponibilidade para um novo compromisso
def check_availability(date, time):
    connection = create_connection()
    if connection is not None:
        try:
            cursor = connection.cursor()
            query = """
                SELECT COUNT(*) FROM appointments
                WHERE appointment_date = %s AND appointment_time = %s
            """
            cursor.execute(query, (date, time))
            result = cursor.fetchone()
            return result[0] == 0  # Retorna True se estiver disponível
        except Error as e:
            print(f"Erro ao verificar disponibilidade: {e}")
        finally:
            cursor.close()
            connection.close()
    return False

# Adiciona um novo compromisso ao banco de dados
def add_appointment(patient_id, date, time):
    connection = create_connection()
    if connection is not None:
        try:
            cursor = connection.cursor()
            query = """
                INSERT INTO appointments (patient_id, appointment_date, appointment_time)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (patient_id, date, time))
            connection.commit()
        except Error as e:
            print(f"Erro ao adicionar compromisso: {e}")
        finally:
            cursor.close()
            connection.close()

# Encontra o próximo horário disponível em uma data específica
def find_next_available_time(date):
    connection = create_connection()
    if connection is not None:
        try:
            cursor = connection.cursor()
            query = """
                SELECT appointment_time FROM appointments
                WHERE appointment_date = %s
                ORDER BY appointment_time ASC
            """
            cursor.execute(query, (date,))
            occupied_times = cursor.fetchall()

            # Supondo que o horário de trabalho seja das 08:00 às 18:00
            available_times = generate_working_hours()

            for time in available_times:
                if (time,) not in occupied_times:
                    return time

            return None  # Não há horários disponíveis
        except Error as e:
            print(f"Erro ao encontrar próximo horário disponível: {e}")
        finally:
            cursor.close()
            connection.close()
    return None

# Gera os horários de trabalho (por exemplo, das 08:00 às 18:00
def generate_working_hours():
    working_hours = []
    for hour in range(8, 18):  # Horários das 08:00 às 17:00
        working_hours.append(f"{hour:02d}:00:00")
    return working_hours

# Busca o patient_id baseado no telegram_id do usuário
def get_patient_by_telegram_id(telegram_id):
    connection = create_connection()
    if connection is None:
        print("Conexão com o banco de dados falhou.")
        return None
    try:
        cursor = connection.cursor()
        query = "SELECT patient_id FROM patients WHERE telegram_id = %s"
        cursor.execute(query, (telegram_id,))
        result = cursor.fetchone()  # Captura uma linha do resultado
        
        # Certifique-se de consumir qualquer resultado restante
        cursor.fetchall()  # Isso consome todas as outras linhas não lidas, mesmo que você não as use
        
        return result  # Retorna a linha capturada (deveria ser o patient_id)
    
    except Error as e:
        print(f"Erro ao buscar patient_id: {e}")
    finally:
        cursor.close()
        connection.close()
    return None

# Busca o compromisso baseado no telegram_id do usuário
def get_appointment_by_telegram_id(telegram_id):
    connection = create_connection()
    if connection is not None:
        try:
            cursor = connection.cursor()
            query = """
            SELECT a.appointment_id, a.appointment_date, a.appointment_time, p.patient_id
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            WHERE p.telegram_id = %s
            """
            cursor.execute(query, (telegram_id,))
            
            # Ler o resultado da consulta
            appointment = cursor.fetchone()
            
            # Garantir que todos os resultados foram lidos antes de fechar o cursor
            if cursor.with_rows:
                cursor.fetchall()  # Ignorar quaisquer resultados não lidos
            
            return appointment
        
        except Error as e:
            print(f"Erro ao buscar compromisso: {e}")
        finally:
            cursor.close()
            connection.close()
    return None

# Busca o compromisso baseado no patient_id do usuário
def get_appointment_by_patient_id(patient_id):
    connection = create_connection()
    if connection is not None:
        try:
            cursor = connection.cursor()
            query = """
            SELECT appointment_id, appointment_date, appointment_time, patient_id
            FROM appointments
            WHERE patient_id = %s
            """
            cursor.execute(query, (patient_id,))
            result = cursor.fetchone()  # Captura uma linha do resultado (deve ser o compromisso)

            # Certifique-se de consumir qualquer resultado restante
            cursor.fetchall()  # Isso consome todas as outras linhas não lidas, mesmo que não as usemos
            
            return result  # Deve retornar o compromisso (appointment_id, date, time, patient_id)
        
        except Error as e:
            print(f"Erro ao buscar compromisso: {e}")
        finally:
            cursor.close()
            connection.close()
    return None

# Marca o lembrete como enviado para um compromisso
def mark_reminder_sent(appointment_id):
    connection = create_connection()
    if connection is not None:
        try:
            cursor = connection.cursor()
            query = "UPDATE appointments SET reminder_sent = TRUE WHERE appointment_id = %s"
            cursor.execute(query, (appointment_id,))
            connection.commit()
        except Error as e:
            print(f"Erro ao marcar lembrete como enviado: {e}")
        finally:
            cursor.close()
            connection.close()