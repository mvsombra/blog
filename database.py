import psycopg2
import os
from datetime import datetime
from argon2 import PasswordHasher
from functions import gerar_url
from user import cria_usuario
from post import cria_post
from ad import cria_ad


class Database:
    def __init__(self):
        comando = os.environ['DATABASE_URL']
        self.conn = psycopg2.connect(comando, sslmode='require')
        self.cur = self.conn.cursor()

    def run_query(self, q):
        self.cur.execute(q)

    def commit(self):
        self.conn.commit()

    def fetch(self):
        return self.cur.fetchall()

    def cud_query(self, q):
        self.run_query(q)
        self.commit()

    def read_query(self, q):
        self.run_query(q)
        return self.fetch()


class Database_access:
    '''
    Classe para acesso ao banco de dados PostgreSQL
    '''

    def __init__(self):
        self.db = Database()

    def select_ads(self):
        '''
        Retorna a tabela de anúncios
        '''
        ads = self.db.read_query("SELECT * FROM ads;")
        new = []
        for ad in ads:
            new.append(cria_ad(ad))

        return new

    def select_users(self, nome=None, sobrenome=None, email=None,
                     max_results=0):
        '''
        Método para realizar buscas de usuários
        Parâmetros:
        nome: busca por um nome específico
        nome: busca por um sobrenome específico
        email: busca por um email eespecífico
        max_results: limita os resultados
        '''

        # query de busca
        q = "SELECT * FROM usuarios {}ORDER BY nome;"
        # adiciona possíveis condições na busca
        if(email):
            q = q.format("WHERE email='{}' ".format(email))
        elif(nome and sobrenome):
            c = "WHERE nome='{}' AND sobrenome='{}' ".format(nome, sobrenome)
            q = q.format(c)
        elif(nome):
            q = q.format("WHERE nome='{}' ".format(nome))
        else:
            q = q.format('')
        # executa a busca
        self.db.run_query(q)
        # limita os resultados e retorna
        if(max_results == 1):
            return cria_usuario(self.db.cur.fetchall()[0])

        users = self.db.fetch()
        new = []
        if(max_results > 1):
            for user in users[:max_results]:
                new.append(cria_usuario(user))
        else:
            for user in users:
                new.append(cria_usuario(user))

        return new

    def select_tags(self, post=None, inc=True):
        q = "SELECT t.id, nome FROM tags AS t{};"
        if(post):
            q = q.format(" WHERE id {}IN (SELECT tag FROM post_tags "
                         "WHERE post='{}')")
            if(inc):
                q = q.format("", post)
            else:
                q = q.format("NOT ", post)
        else:
            q = q.format('')

        return self. db.read_query(q)

    def select_posts(self, active_only=True, ultimos=0, busca=None, url=None,
                     populares=False):
        '''
        Método para realizar buscas de posts
        Parâmetros:
        active_only: apenas posts ativos
        ultimos: quantos posts devem ser exibidos (0 busca todos)
        busca: posts com algum conteudo especifico
        url: post com uma certa url
        populares: busca os posts mais visitados
        '''

        # caso populares seja true, utiliza uma estrutura diferente
        if(populares):
            q = "SELECT post_id, titulo, data, imagem, CONCAT(nome, ' ', " \
                "sobrenome), texto, ativo, url, autor, count FROM usuarios " \
                "as u INNER JOIN (select p.id AS post_id, p.titulo, " \
                "TO_CHAR(p.data, 'DD/MM/YYYY') as data, p.imagem, p.autor, " \
                "p.texto, p.ativo, p.url, count from posts as p inner join " \
                "(select url, COUNT(url) from (select ip_user as ip, " \
                "url_post as url from visitas group by ip, url) as q1 group " \
                "by url) as q2 on p.url=q2.url) AS q3 on u.id=q3.autor " \
                "where ativo=1 order by count desc;"

            # realiza a busca e retorna
            posts = self.db.read_query(q)
            new = []
            for post in posts:
                new.append(cria_post(post))

            return new
        # query de busca
        q = "SELECT p.id, titulo, TO_CHAR(data, 'DD/MM/YYYY'), imagem, " \
            "CONCAT(nome, ' ', sobrenome), texto, ativo, url FROM posts as p" \
            " INNER JOIN usuarios as u ON p.autor=u.id {}ORDER BY data desc"

        # configura a seleção de posts ativos ou não
        if(active_only):
            q = q.format('WHERE ativo=1 {}')
        else:
            q = q.format('WHERE ativo=0 {}')

        # caso haja uma busca, configura para buscar pelo titulo ou texto
        if(busca):
            busca = '%' + busca.lower() + '%'
            ultimos = 0
            s = "AND (LOWER(texto) LIKE '{}' OR LOWER(titulo) LIKE '{}') "
            s = s.format(busca, busca)
            q = q.format(s)
        # caso haja uma url, busca por url
        elif(url):
            q = q.format("AND url='{}' ".format(url))
        # busca todos os posts
        else:
            q = q.format('')

        # limita os resultados ou não
        if(ultimos > 0):
            q += " LIMIT {};".format(ultimos)
        else:
            q += ';'

        # realiza a busca e retorna
        posts = self.db.read_query(q)
        new = []
        for post in posts:
            new.append(cria_post(post))

        return new

    def insert_tag_post(self, tag, url):
        q = "INSERT INTO post_tags (tag, post) VALUES ({}, '{}')"
        q = q.format(tag, url)
        # executa a query
        self.db.cud_query(q)

    def insert_post(self, titulo, autor, data, img, texto, ativo):
        '''
        Método para inserir post no banco de dados
        Cada parâmetro é um campo da tabela
        '''

        # gera uma url para o post
        url = gerar_url(self, titulo, autor)
        # busca o id do autor do post
        autor = autor.split()
        autor = self.select_users(nome=autor[0], sobrenome=autor[1])[0].id
        # query para inserir o post
        q = "INSERT INTO posts (titulo, autor, data, imagem, texto, ativo, " \
            "url) VALUES ('{}', {}, '{}', '{}', '{}', {}, '{}');"
        q = q.format(titulo, autor, data, img, texto, ativo, url)
        # executa a query
        self.db.cud_query(q)

    def insert_visita(self, ip, url):
        '''
        Registra uma visita nova
        '''
        # não registra caso seja executado localmente
        if(ip == '127.0.0.1'):
            return

        hj = datetime.now().strftime('%Y-%m-%d')
        q = "INSERT INTO visitas (ip_user, data, url_post) " \
            "VALUES ('{}', '{}', '{}');".format(ip, hj, url)
        self.db.cud_query(q)

    def update_post(self, id_post, titulo, autor, texto, ativo):
        '''
        Método para alterar um post do banco de dados
        Cada parâmetro é um campo da tabela
        '''
        # busca o id do autor do post
        autor = autor.split()
        autor = self.select_users(nome=autor[0], sobrenome=autor[1])[0].id
        # query para editar o post
        q = "UPDATE posts SET titulo='{}', autor={}, texto='{}', ativo={} " \
            "WHERE id={};".format(titulo, autor, texto, ativo, id_post)
        # executa a query
        self.db.cud_query(q)

    def update_users(self, nome, sobrenome, fb, insta, github, linkedin,
                     pesquisa, descricao, email):
        '''
        Método para alterar um usuário do banco de dados
        Cada parâmetro é um campo da tabela
        '''
        # query para editar o usuário
        q = "UPDATE usuarios SET nome='{}', sobrenome='{}', facebook='{}'," \
            " instagram='{}', github='{}', linkedin='{}', pesquisa='{}', " \
            " descricao='{}' WHERE email='{}';"
        q = q.format(nome, sobrenome, fb, insta, github, linkedin, pesquisa,
                     descricao, email)
        # executa a query
        self.db.cud_query(q)

    def auth_user(self, email, senha):
        user = self.select_users(email=email, max_results=1)
        ph = PasswordHasher()
        try:
            ph.verify(user.senha, senha)
            return True
        except Exception:
            return False

    def delete_post(self, email, senha, url):
        r = self.auth_user(email, senha)
        if(r):
            self.delete_visita(url)
            self.delete_tag_post(url)
            q = "DELETE FROM posts WHERE url='{}';".format(url)
            self.db.cud_query(q)
            return 1
        else:
            return 0

    def delete_visita(self, url):
        q = "DELETE FROM visitas WHERE url_post='{}';".format(url)
        self.db.cud_query(q)

    def delete_tag_post(self, post, tag=None):
        q = "DELETE FROM post_tags WHERE post='{}'{};".format(post, '{}')
        if(tag):
            q = q.format(' AND tag={}'.format(tag))
        else:
            q = q.format('')
        self.db.cud_query(q)
