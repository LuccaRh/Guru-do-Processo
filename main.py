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
#rooms = {"room_code": [{"nome":mensagem}, {"nome": mensagem}, ...]}
rooms = {}

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
        if code not in rooms:
            break
    return code

#Resposta do gpt para certa pergunta
def chat_com_gpt(pergunta):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": pergunta}]
    )
    return response.choices[0].message.content.strip()





# @app.route roda a função criada ao entrar na rota selecionada
# liberação do método Post, e identificar a solicitação Post mandada do html para fazer o comando
@app.route("/", methods=["POST", "GET"])
def forms():
    session.clear()
    if request.method == "POST":
        #Pegar variáveis criadas no forms
        name = request.form['name']
        cpf = request.form['cpf']
        phone = request.form['phone']
        email = request.form['email']
        create = request.form.get("create", False)

        #Inserir cpf celular e email no prompt do gpt

        room_code = generate_unique_code(4) #Código da sala

        if not name:
            return render_template("forms.html", error="Please enter a name.", room_code=room_code, name=name)
        
        #Criação de uma sala
        if create != False:
            rooms[room_code] = {"messages": []}
        
        #Colocar código da sala e nome na sessão criada
        session["room_code"] = room_code
        session["name"] = name

        return redirect(url_for("room"))

    return render_template("forms.html")


@app.route("/room")
def room():
    room_code = session.get("room_code") #Pegar código da sala/sessão

    if room_code is None or session.get("name") is None or room_code not in rooms:
        return redirect(url_for("home"))

    #Renderizar room, com todo o histórico de mensagens e o código da sala
    return render_template("room.html", room_code=room_code, messages=rooms[room_code]["messages"])

@socketio.on("message")
def message(data):
    room_code = session.get("room_code")
    if room_code not in rooms:
        return 
    
    user_name = session.get("name")
    user_message = data["data"]
    
    # Adiciona a mensagem do usuário ao histórico de mensagens da sala
    rooms[room_code]["messages"].append({"name": user_name, "message": user_message})
    emit("message", {"name": user_name, "message": user_message}, room_code=room_code)

    # Enviar a pergunta para o chatbot e obter a resposta
    bot_response = chat_com_gpt(user_message)
    # Adiciona a resposta do chatbot ao histórico de mensagens da sala
    rooms[room_code]["messages"].append({"name": "ChatBot", "message": bot_response})
    #Emitir resposta no chat
    emit("message", {"name": "ChatBot", "message": bot_response}, room_code=room_code)

    #Mostrar conversa no terminal
    print(f"{user_name} asked: {user_message}")
    print(f"ChatBot responded: {bot_response}")
    print(session)


@socketio.on("connect")
def connect(auth):
    room_code = session.get("room_code")
    name = session.get("name")

    if not room_code or not name:
        return
    if room_code not in rooms:
        leave_room(room_code)
        return
    
    join_room(room_code)
    send({"name": name, "message": "has entered the room"}, to=room_code)
    print(f"{name} joined room {room_code}")

if __name__ == "__main__":
    socketio.run(app, debug=True)