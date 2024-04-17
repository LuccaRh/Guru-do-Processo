from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO, emit
import random
from string import ascii_uppercase
from openai import OpenAI
from dotenv import load_dotenv
import os

#Criação do aplicativo Flask
app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)

#Dicionário com todas salas e suas conversas
#salas = {"sala_codigo": [{"nome":mensagem}, {"nome": mensagem}, ...]}
'''salas = {"sala_codigo": 
                {"celular": "11997844060", 
                "cpf": "37775331810", 
                "email": "lucca@gmail.com", 
                "nome": "Lucca", 
                "mensagens": [{"nome":mensagem}, {"nome": mensagem}, ...]
                }
            }
    Não precisa fazer desse jeito, informações do usuário são salvas na sessão da sala
'''
salas = {}

#key do openai
load_dotenv()
openaiApikey = os.getenv('openaiApikey')

#Criação do objeto openai
client = OpenAI(
    api_key= openaiApikey,
)

#Criar código da sala
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        if code not in salas:
            break
    return code

#Resposta do gpt para certa pergunta
def chat_com_gpt(pergunta, historico):
    # Concatenar o histórico de mensagens para formar um único texto
    nome = session.get("nome")
    cpf = session.get("cpf")
    celular = session.get("celular")
    email = session.get("email")
    historico_texto = f"Meu nome é {nome}, meu cpf é {cpf}, meu celular é {celular}, e meu email é {email} \n"
    historico_texto += " ".join([f"{msg["nome"]}: {msg["message"]} \n" for msg in historico])

    print("Histórico: " + historico_texto)
    # Enviar a pergunta para o GPT
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": historico_texto}]
    )
    return response.choices[0].message.content.strip()





# @app.route roda a função criada ao entrar na rota selecionada
# liberação do método Post, e identificar a solicitação Post mandada do html para fazer o comando
@app.route("/", methods=["POST", "GET"])
def forms():
    session.clear()
    if request.method == "POST":
        #Pegar variáveis criadas no forms
        nome = request.form['name']
        cpf = request.form['cpf']
        celular = request.form['phone']
        email = request.form['email']
        create = request.form.get("create", False)

        #Inserir cpf celular e email no prompt do gpt   

        sala_codigo = generate_unique_code(4) #Código da sala

        if not nome:
            return render_template("forms.html", error="Please enter a nome.")
        
        #Criação de uma sala
        if create != False:
            salas[sala_codigo] = {"messages": []}
        
        #Colocar informações do usuário e código da sala na sessão criada
        session["sala_codigo"] = sala_codigo
        session["nome"] = nome
        session["cpf"] = cpf
        session["celular"] = celular
        session["email"] = email


        return redirect(url_for("room"))

    return render_template("forms.html")


@app.route("/room")
def room():
    sala_codigo = session.get("sala_codigo") #Pegar código da sala/sessão

    if sala_codigo is None or session.get("nome") is None or sala_codigo not in salas:
        return redirect(url_for("home"))

    #Renderizar room, com todo o histórico de mensagens e o código da sala
    return render_template("room.html", sala_codigo=sala_codigo, messages=salas[sala_codigo]["messages"])

@socketio.on("message")
def message(data):
    sala_codigo = session.get("sala_codigo")
    if sala_codigo not in salas:
        return 
    
    user_nome = session.get("nome")
    user_message = data["data"]
    
    # Adiciona a mensagem do usuário ao histórico de mensagens da sala
    salas[sala_codigo]["messages"].append({"nome": user_nome, "message": user_message})
    emit("message", {"name": user_nome, "message": user_message}, sala_codigo=sala_codigo)

    # Enviar a pergunta para o chatbot e obter a resposta
    bot_response = chat_com_gpt(user_message, salas[sala_codigo]["messages"])
    # Adiciona a resposta do chatbot ao histórico de mensagens da sala
    salas[sala_codigo]["messages"].append({"nome": "ChatBot", "message": bot_response})
    #Emitir resposta no chat
    emit("message", {"name": "ChatBot", "message": bot_response}, sala_codigo=sala_codigo)

    #Mostrar conversa no terminal
    #print(f"{user_nome} asked: {user_message}")
    #print(f"ChatBot responded: {bot_response}")


@socketio.on("connect")
def connect(auth):
    sala_codigo = session.get("sala_codigo")
    nome = session.get("nome")

    if not sala_codigo or not nome:
        return
    if sala_codigo not in salas:
        leave_room(sala_codigo)
        return
    
    join_room(sala_codigo)
    send({"name": nome, "message": "has entered the room"}, to=sala_codigo)
    print(f"{nome} joined room {sala_codigo}")

if __name__ == "__main__":
    socketio.run(app, debug=True)