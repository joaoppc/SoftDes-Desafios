# -*- coding: utf-8 -*-
"""
Created on Wed Jun 28 09:00:39 2017

@author: rauli
"""

from flask import Flask, request, jsonify, abort, make_response, session, render_template
from flask_httpauth import HTTPBasicAuth
from flask_babel import Babel
from flask_babel import _
from config import Config
from datetime import datetime
import sqlite3
import json
import hashlib

app = Flask(__name__, static_url_path='')
babel = Babel(app)

DBNAME = './quiz.db'

def lambda_handler(event, context):
    """Função usada para checar se a função é válida."""
    try:
        import json 
        import numbers
        
        def not_equals(first, second):
            """Checa se o resultado das funções não são iguais."""
            if isinstance(first, numbers.Number) and isinstance(second, numbers.Number):
                return abs(first - second) > 1e-3
            return first != second
        
        # TODO implement
        ndes = int(event['ndes'])
        code = event['code']
        args = event['args']
        resp = event['resp']
        diag = event['diag'] 
        exec(code, locals())
        
        
        test = []
        for index, arg in enumerate(args):
            if not 'desafio{0}'.format(ndes) in locals():
                return _("Nome da função inválido. Usar 'def desafio{0}(...)'".format(ndes))
            
            if not_equals(eval('desafio{0}(*arg)'.format(ndes)), resp[index]):
                test.append(diag[index])

        return _(" ".join(test))
    except:
        return _("Função inválida.")

def converteData(orig):
    """Coverte a data de AA/MM/DD para DD/MM/AA."""
    return orig[8:10]+'/'+orig[5:7]+'/'+orig[0:4]+' '+orig[11:13]+':'+orig[14:16]+':'+orig[17:]

def getQuizes(user):
    """Cria uma conexão com o banco de dados quiz.db e recupera os desafios do banco."""
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    if user == 'admin' or user == 'fabioja':
        cursor.execute("SELECT id, numb from QUIZ".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    else:
        cursor.execute("SELECT id, numb from QUIZ where release < '{0}'".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    info = [reg for reg in cursor.fetchall()]
    conn.close()
    return info

def getUserQuiz(userid, quizid):
    """Cria uma conexão com o banco de dados quiz.db e recupera os desafios respondidos pelo usuário."""
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute("SELECT sent,answer,result from USERQUIZ where userid = '{0}' and quizid = {1} order by sent desc".format(userid, quizid))
    info = [reg for reg in cursor.fetchall()]
    conn.close()
    return info

def setUserQuiz(userid, quizid, sent, answer, result):
    """Cria uma conexão com o banco de dados quiz.db e coloca no banco de dados o quiz que foi respondido pelo usuário."""
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    #print("insert into USERQUIZ(userid,quizid,sent,answer,result) values ('{0}',{1},'{2}','{3}','{4}');".format(userid, quizid, sent, answer, result))
    #cursor.execute("insert into USERQUIZ(userid,quizid,sent,answer,result) values ('{0}',{1},'{2}','{3}','{4}');".format(userid, quizid, sent, answer, result))
    cursor.execute("insert into USERQUIZ(userid,quizid,sent,answer,result) values (?,?,?,?,?);", (userid, quizid, sent, answer, result))
    #
    conn.commit()
    conn.close()

def getQuiz(id, user):
    """Cria uma conexão com o banco de dados quiz.db e recupera um determinado quiz e suas informações."""
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    if user == 'admin' or user == 'fabioja':
        cursor.execute("SELECT id, release, expire, problem, tests, results, diagnosis, numb from QUIZ where id = {0}".format(id))
    else:
        cursor.execute("SELECT id, release, expire, problem, tests, results, diagnosis, numb from QUIZ where id = {0} and release < '{1}'".format(id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    info = [reg for reg in cursor.fetchall()]
    conn.close()
    return info

def setInfo(pwd, user):
    """Cria uma conexão com o banco de dados quiz.db e define as informações do usuário como senha e nome do usuário."""
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE USER set pass = ? where user = ?",(pwd, user))
    conn.commit()
    conn.close()

def getInfo(user):
    """Cria uma conexão com o banco de dados quiz.db e recupera as informações do usuário como senha e nome do usuário."""
    conn = sqlite3.connect(DBNAME)
    cursor = conn.cursor()
    cursor.execute("SELECT pass, type from USER where user = '{0}'".format(user))
    print("SELECT pass, type from USER where user = '{0}'".format(user))
    info = [reg[0] for reg in cursor.fetchall()]
    conn.close()
    if len(info) == 0:
        return None
    else:
        return info[0]

auth = HTTPBasicAuth()


app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?TX'

@app.route('/', methods=['GET', 'POST'])
@auth.login_required
def main():
    """Função principal, na qual checa as respostas dos usuários com as respostas corretas, checa se há quiz para ser respondido e também faz a comunicação REST com o servidor web"""
    msg = ''
    p = 1
    challenges=getQuizes(auth.username())
    sent = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if request.method == 'POST' and 'ID' in request.args:
        id = request.args.get('ID')
        quiz = getQuiz(id, auth.username())
        if len(quiz) == 0:
            msg = _("Boa tentativa, mas não vai dar certo!")
            p = 2
            return render_template('index.html', username=auth.username(), challenges=challenges, p=p, msg=msg)

        
        quiz = quiz[0]
        if sent > quiz[2]:
            msg = _("Sorry... Prazo expirado!")
        
        f = request.files['code']
        filename = './upload/{0}-{1}.py'.format(auth.username(), sent)
        f.save(filename)
        with open(filename,'r') as fp:
            answer = fp.read()
        
        #lamb = boto3.client('lambda')
        args = {"ndes": id, "code": answer, "args": eval(quiz[4]), "resp": eval(quiz[5]), "diag": eval(quiz[6]) }

        #response = lamb.invoke(FunctionName="Teste", InvocationType='RequestResponse', Payload=json.dumps(args))
        #feedback = response['Payload'].read()
        #feedback = json.loads(feedback).replace('"','')
        feedback = lambda_handler(args,'')


        result = _('Erro')
        if len(feedback) == 0:
            feedback = _('Sem erros.')
            result = 'OK!'

        setUserQuiz(auth.username(), id, sent, feedback, result)


    if request.method == 'GET':
        if 'ID' in request.args:
            id = request.args.get('ID')
        else:
            id = 1

    if len(challenges) == 0:
        msg = _("Ainda não há desafios! Volte mais tarde.")
        p = 2
        return render_template('index.html', username=auth.username(), challenges=challenges, p=p, msg=msg)
    else:
        quiz = getQuiz(id, auth.username())

        if len(quiz) == 0:
            msg = _("Oops... Desafio invalido!")
            p = 2
            return render_template('index.html', username=auth.username(), challenges=challenges, p=p, msg=msg)

        answers = getUserQuiz(auth.username(), id)
    
    return render_template('index.html', username=auth.username(), challenges=challenges, quiz=quiz[0], e=(sent > quiz[0][2]), answers=answers, p=p, msg=msg, expi = converteData(quiz[0][2]))

@app.route('/pass', methods=['GET', 'POST'])
@auth.login_required
def change():
    """Função para trocar de senha"""
    if request.method == 'POST':
        velha = request.form['old']
        nova = request.form['new']
        repet = request.form['again']

        p = 1
        msg = ''
        if nova != repet:
            msg = _('As novas senhas nao batem')
            p = 3
        elif getInfo(auth.username()) != hashlib.md5(velha.encode()).hexdigest():
            msg = _('A senha antiga nao confere')
            p = 3
        else:
            setInfo(hashlib.md5(nova.encode()).hexdigest(), auth.username())
            msg = _('Senha alterada com sucesso')
            p = 3
    else:
        msg = ''
        p = 3

    return render_template('index.html', username=auth.username(), challenges=getQuizes(auth.username()), p=p, msg=msg)


@app.route('/logout')
def logout():
    """Faz um logout do usuário"""
    return render_template('index.html',p=2, msg=_("Logout com sucesso")), 401

@auth.get_password
def get_password(username):
    """Retorna a senha"""
    return getInfo(username)

@auth.hash_password
def hash_pw(password):
    """retorna o hash da senha"""
    return hashlib.md5(password.encode()).hexdigest()

if __name__ == '__main__':
    app.run(debug=True, host= '0.0.0.0', port=80)


@babel.localeselector
def get_locale():
    """utilizado pela biblioteca pybabel para tradução. Retorna a língua a ser traduzida"""
    return request.accept_languages.best_match(app.config['LANGUAGES'])

