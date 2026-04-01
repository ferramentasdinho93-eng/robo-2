import os
import requests
import logging
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Config Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

# Config Meta
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
WHATSAPP_NUMBER = os.environ.get("WHATSAPP_NUMBER")

# 🔥 PROMPT
SYSTEM_PROMPT = f"""
Você é um vendedor especialista em ferramentas para construção civil com foco TOTAL em conversão.

Leve o cliente para: https://wa.me/{WHATSAPP_NUMBER}

Cliente disse:
{{mensagem}}

Responda como vendedor experiente, persuasivo e que sempre tenta levar para o WhatsApp:
"""

# 🧠 memória
user_sessions = {}

def get_history(user_id):
    if user_id not in user_sessions:
        user_sessions[user_id] = []
    return user_sessions[user_id]

# 📤 enviar mensagem
def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"

    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }

    response = requests.post(url, json=payload)
    logging.info(response.json())

# 🎯 intenção
def detectar_intencao(msg):
    msg = msg.lower()

    if "preço" in msg or "valor" in msg:
        return "comprar"
    elif "oi" in msg or "olá" in msg:
        return "inicio"
    else:
        return "duvida"

# 🔐 verificação
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge')
    return 'Erro', 403

# 💬 webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    try:
        if data.get('object') == 'instagram':
            for entry in data.get('entry', []):
                for msg in entry.get('messaging', []):

                    if msg.get('message'):
                        sender_id = msg['sender']['id']
                        message_text = msg['message'].get('text')

                        if not message_text:
                            continue

                        logging.info(f"{sender_id}: {message_text}")

                        intencao = detectar_intencao(message_text)

                        # ⚡ resposta rápida
                        if intencao == "comprar":
                            send_message(
                                sender_id,
                                f"Temos a partir de R$299 🔥 mas no WhatsApp consigo desconto melhor 👇 https://wa.me/{WHATSAPP_NUMBER}"
                            )
                            continue

                        # 🤖 IA
                        history = get_history(sender_id)
                        chat = model.start_chat(history=history)

                        prompt = SYSTEM_PROMPT.replace("{{mensagem}}", message_text)

                        try:
                            response = chat.send_message(prompt)
                            resposta_texto = response.text
                        except Exception:
                            resposta_texto = f"Tive um probleminha aqui 😅 mas me chama no WhatsApp que te passo tudo 👇 https://wa.me/{WHATSAPP_NUMBER}"

                        send_message(sender_id, resposta_texto)

        return 'OK', 200

    except Exception as e:
        logging.error(f"Erro: {e}")
        return 'Erro', 500

if __name__ == '__main__':
    # Render usa a porta definida na variável de ambiente PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
