## **Chatbot para Consultórios Médicos**

Este repositório contém o código-fonte de um protótipo de chatbot desenvolvido para auxiliar na gestão de consultas médicas, atendendo à demanda por soluções tecnológicas que aprimorem a eficiência e a qualidade do atendimento na saúde pública. Inspirado pelos desafios enfrentados por instituições médicas, o chatbot busca otimizar a comunicação com os pacientes, substituindo ligações telefônicas por interações rápidas e eficazes via mensagens. Entre suas funcionalidades, destacam-se o envio de lembretes automáticos, a confirmação, o cancelamento e a remarcação de consultas. O protótipo integra a API do Telegram e utiliza o modelo de linguagem natural LLaMA-2 para oferecer respostas contextuais, simulando a interação com uma secretária médica.


**Funcionalidades**

- **Envio de lembretes**: Notifica os pacientes sobre consultas marcadas 24 horas antes do horário.
- **Gestão de consultas**: Permite confirmar, cancelar ou remarcar consultas de forma simples e automatizada.
- **Registro de interações**: Armazena logs de conversas para análise futura.
- **Integração com Telegram**: Facilita a comunicação com os pacientes diretamente pelo aplicativo.

## **Requisitos**

Para utilizar este protótipo, é necessário:

1. **Clonar o repositório do [LLaMA.cpp](https://github.com/ggerganov/llama.cpp)**  
   O LLaMA.cpp é usado para executar o modelo de linguagem natural localmente. Certifique-se de seguir as instruções no repositório para configurar o ambiente.

2. **Configurar um ambiente Conda**:  
   Certifique-se de que o Conda esteja instalado em seu sistema. No diretório do projeto, crie e ative um ambiente Conda
   
3. **Instalar dependências do projeto**:  
   Após ativar o ambiente Conda, instale as dependências do projeto usando o arquivo `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

   Além disso, se o LLaMA.cpp necessitar de bibliotecas adicionais, instale-as conforme indicado no repositório oficial.

4. **Configurar o banco de dados MySQL**

Certifique-se de ter o MySQL instalado e configurado no seu sistema. Utilize o código abaixo para criar o esquema do banco de dados e as tabelas necessárias. 

```sql
-- Esquema do banco de dados
CREATE SCHEMA IF NOT EXISTS `clinicdb` 
DEFAULT CHARACTER SET utf8mb4 
COLLATE utf8mb4_0900_ai_ci;
USE `clinicdb`;

-- Tabela de pacientes
CREATE TABLE IF NOT EXISTS `patients` (
  `patient_id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL,
  `telegram_id` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`patient_id`)
) ENGINE=InnoDB
DEFAULT CHARACTER SET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;

-- Tabela de agendamentos
CREATE TABLE IF NOT EXISTS `appointments` (
  `appointment_id` INT NOT NULL AUTO_INCREMENT,
  `patient_id` INT NULL,
  `appointment_date` DATE NOT NULL,
  `appointment_time` TIME NOT NULL,
  `reminder_sent` TINYINT(1) DEFAULT '0',
  PRIMARY KEY (`appointment_id`),
  INDEX `patient_id` (`patient_id`),
  CONSTRAINT `appointments_ibfk_1`
    FOREIGN KEY (`patient_id`)
    REFERENCES `patients` (`patient_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB
DEFAULT CHARACTER SET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;

-- Tabela de diálogos
CREATE TABLE IF NOT EXISTS `dialogues` (
  `dialogue_id` INT NOT NULL AUTO_INCREMENT,
  `telegram_id` VARCHAR(100) NOT NULL,
  `user_message` TEXT NOT NULL,
  `bot_response` TEXT NOT NULL,
  `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`dialogue_id`)
) ENGINE=InnoDB
DEFAULT CHARACTER SET=utf8mb4
COLLATE=utf8mb4_0900_ai_ci;
```

Esse código cria as seguintes tabelas no banco de dados `clinicdb`:

- **`patients`**: Armazena informações dos pacientes, como ID, nome e ID do Telegram.
- **`appointments`**: Gerencia compromissos médicos, associando pacientes às datas e horários.
- **`dialogues`**: Registra o histórico das interações entre o paciente e o chatbot, incluindo mensagens enviadas e respostas geradas.

5. **Configurar o token do Telegram**:  
   Crie um bot no Telegram utilizando o [BotFather](https://core.telegram.org/bots) e adicione o token gerado no arquivo `config.py`. Certifique-se de que o arquivo contém o seguinte formato:
   ```python
   TELEGRAM_TOKEN = "seu_token_aqui"
   ```

6. **Baixar o modelo LLaMA-2**:  
   Coloque o arquivo do modelo (por exemplo, `llama-2-7b-chat.Q4_K_M.gguf`) na pasta "llama.cpp/models/" e certifique-se de que o caminho do modelo seja configurado corretamente no arquivo `model.py`.

---


**Estrutura do Repositório**

- `bot.py`: Lógica principal do chatbot, incluindo integração com Telegram.
- `model.py`: Funções para carregar o modelo LLaMA-2 e gerar respostas.
- `db.py`: Conexão e operações com o banco de dados MySQL.
- `config.py`: Arquivo para configurar o token do Telegram e outras variáveis de ambiente.


**Permissões de Uso**

Este projeto está disponível sob a licença **MIT**. Isso significa que você pode usá-lo, modificá-lo e distribuí-lo livremente, desde que inclua os créditos originais.
