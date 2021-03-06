# coding: utf-8
import sys
import random
import json
import tornado.web
import tornado.auth
from tornado.httputil import HTTPFile
from jinja2 import Template, Environment, FileSystemLoader
from bson import objectid
from PIL import Image
from io import BytesIO


import filter, utils, session
from forms import *
from models import *

class BaseHandler(tornado.web.RequestHandler):

    def __init__(self, application, request, **kwargs):
        tornado.web.RequestHandler.__init__(self, application, request, **kwargs)
        self.session = session.TornadoSession(application.session_manager, self)
        self._title = self.settings['app_name']

    def render_string(self,template,**args):
        env = Environment(loader=FileSystemLoader(self.settings['template_path']))
        env.filters['markdown'] = filter.markdown
        env.filters['md_body'] = filter.md_body
        env.filters['tags_name_tag'] = filter.tags_name_tag
        env.filters['user_name_tag'] = filter.user_name_tag
        env.filters['strftime'] = filter.strftime
        env.filters['strfdate'] = filter.strfdate
        env.filters['avatar'] = filter.avatar
        env.filters['topic_avatar'] = filter.topic_avatar
        env.filters['is_following'] = filter.is_following
        env.filters['is_following_topic'] = filter.is_following_topic
        env.filters['num_human'] = filter.num_human
        env.filters['truncate_lines'] = utils.truncate_lines
        template = env.get_template(template)
        return template.render(settings=self.settings,
                               title=self._title,
                               notice_message=self.notice_message,
                               current_user=self.current_user,
                               static_url=self.static_url,
                               modules=self.ui['modules'],
                               xsrf_form_html=self.xsrf_form_html,
                               **args)

    def render(self, template, **args):
        self.finish(self.render_string(template, **args))

    def get_current_user(self):
        user_id = self.get_secure_cookie("user_id")
        if not user_id: return None
        try:
          return User.objects(id = user_id).first()
        except:
          return None

    def notice(self,msg,type = "success"):
        type = type.lower()
        if ['error','success','warring'].count(type) == 0:
            type = "success"
        self.session["notice_%s" % type] = msg 
        self.session.save()

    @property
    def notice_message(self):
        try:
          msg = self.session['notice_error']
          self.session['notice_error'] = None
          self.session['notice_success'] = None
          self.session['notice_warring'] = None
          self.session.save()
          if not msg:
            return ""
          else:
            return msg
        except:
          return ""

    def render_404(self):
        raise tornado.web.HTTPError(404)

    def set_title(self, str):
        self._title = u"%s - %s" % (str,self.settings['app_name'])

    def events_articles(self,events):
        articles = []
        if(events):
            for event in events:
                article = Article(event)
                if(article):
                    articles.append(article)
        return articles[::-1]
    
    def generate_hot_topics(self,n):
        topics = Topic.objects()
        sorted_list = sorted(topics, key=lambda x : len(x.threads),reverse=True)
        hot_topics = [{'name':x.name,'cnt':len(x.threads),'id':str(x.id)} for x in sorted_list]
        return hot_topics[:n]

class DiscoverHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        last_id = self.get_argument("last", None)
        if not last_id:
          asks = Ask.objects.order_by("-replied_at")[:5]
        else:
          asks = Ask.objects(id__lt = last_id).order_by("-replied_at")[:5]
        if not asks:
            self.redirect("/ask")
        else:
            #hot_topics = [{'name':u'精神病','cnt':7004},{'name':u'神经病','cnt':6074},{'name':u'弱智','cnt':5349},{'name':u'脑残','cnt':4301},\
            #    {'name':u'脑瘫','cnt':2315}]
            #ordered by vote
            now = datetime.datetime.now()
            week_start,week_end = utils.get_week_range(now)
            month_start,month_end = utils.get_month_range(now)
            daily = Answer.objects(created_at__gte=week_start,created_at__lt=week_end).order_by("-vote")[:5]
            monthly = Answer.objects(created_at__gte=month_start,created_at__lt=month_end).order_by("-vote")[:5]

            hot_topics = self.generate_hot_topics(5)
            self.render("discovery.html", asks=asks,daily_hots=daily,monthly_hots=monthly,hot_topics=hot_topics)


class HomeHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        last_id = self.get_argument("last", None)
        if not last_id:
            user = self.current_user
            articles = self.events_articles(user.time_line)
        else:
            asks = Ask.objects(id__lt = last_id).order_by("-replied_at").limit(10)
        self.render("home.html", articles=articles)

class AskHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        ask = Ask()
        self.set_title(u"提问题")
        self.render("ask.html",ask=ask)

    @tornado.web.authenticated
    def post(self):
        self.set_title(u"提问题")
        frm = AskForm(self)
        if not frm.validate():
            frm.render("ask.html")
            return

        ask = Ask(title=frm.title,
            body = frm.body,
            summary = utils.truncate_lines(frm.body,3,500),
            user = self.current_user,
            tags = utils.format_tags(frm.tags))
        try:
            ask.save()
            # this part could be put in a queue
            event = UserEvent(user=self.current_user.id,type="ask",target=ask.id)
            event.save()
            User.objects(id = self.current_user.id).update_one(push__user_events = event)

            for x in self.current_user.followers:
                User.objects(id = x.id).update_one(push__time_line = event)
            for x in ask.tags:
                Topic.objects(name = x).update_one(push__threads = event)
            self.redirect("/ask/%s" % ask.id)
        except Exception,exc:
            self.notice(exc,"error")
            frm.render("ask.html")

class AskShowHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self,id):
        ask = Ask.objects(id=id).first()
        if not ask:
            self.render_404()
        answers = Answer.objects(ask=ask).order_by("-vote","created_at")
        self.set_title(ask.title)
        self.render("ask_show.html",ask=ask, answers=answers)


class AnswerHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self,ask_id):
        self.redirect("/ask/%s" % ask_id)

    @tornado.web.authenticated
    def post(self,ask_id):
        ask = Ask.objects(id=ask_id).first()
        self.set_title(u"回答")
        frm = AnswerForm(self)
        if not frm.validate():
            frm.render("ask_show.html",ask=ask)
            return

        answer = Answer(ask=ask,
                        body=frm.answer_body,
                        user=self.current_user)
                        
        try:
            answer.save()
            Ask.objects(id=ask_id).update_one(inc__answers_count=1,set__replied_at=answer.created_at)

            # this part could be put in a queue
            event = UserEvent(user=self.current_user.id,type="answer",target=answer.id)
            event.save()
            User.objects(id = self.current_user.id).update_one(push__user_events = event)
            ask.update(push__user_events = event)

            for x in self.current_user.followers:
                User.objects(id = x.id).update_one(push__time_line = event)
            for x in ask.followers:
                User.objects(id = x.id).update_one(push__time_line = event)
            for x in ask.tags:
                Topic.objects(name = x).update_one(push__threads = event)

            self.redirect("/ask/%s" % ask_id)
        except Exception,exc:
            self.notice(exc,"error")
            frm.render("ask_show.html", ask=ask)

class AnswerVoteHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, id):
        up = True
        if self.get_argument("up","0") == "0":
            up = False
        result = Answer.do_vote(id, up, self.current_user)
        self.write(str(result))

class LogoutHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.set_secure_cookie("user_id","")
        self.redirect("/login")

class LoginHandler(BaseHandler):
    def get(self):
        self.set_title(u"登陆")
        self.render("login.html")

    def post(self):
        self.set_title(u"登陆")
        frm = LoginForm(self)
        if not frm.validate():
            frm.render("login.html")
            return

        password = utils.md5(frm.password)
        user = User.objects(login=frm.login,
                            password=password).first()
        if not user:
            frm.add_error("password", "不正确")
            frm.render("login.html")

        self.set_secure_cookie("user_id", str(user.id))
        self.redirect(self.get_argument("next","/"))

class RegisterHandler(BaseHandler):
    def get(self):
        self.set_title(u"注册")
        user = User()
        self.render("register.html", user=user)

    def post(self):
        self.set_title(u"注册")
        frm = RegisterForm(self)
        if not frm.validate():
            frm.render("register.html")
            return
        
        user = User(name=frm.name,
                    login=frm.login,
                    email=frm.email,
                    password=utils.md5(frm.password))
        try:
          user.save()
          self.set_secure_cookie("user_id",str(user.id))
          self.redirect("/")
        except Exception,exc:
          self.notice(exc,"error")
          frm.render("register.html")

class FeedHandler(BaseHandler):
    def get(self):
        self.render("feed.html")


class CommentHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self, commentable_type, commentable_id):
        commentable_type = commentable_type.lower()
        if ["ask","answer"].count(commentable_type) == 0: return ""
        comment = Comment(id=utils.sid(),
                          body=self.get_argument("body",None),
                          user=self.current_user)
        if commentable_type == "ask":
            Ask.objects(id=commentable_id).update_one(push__comments=comment)            
        elif commentable_type == "answer":
            Answer.objects(id=commentable_id).update_one(push__comments=comment) 
        comment_hash = { "success":1,
                "user_id":str(self.current_user.id),
                "name":self.current_user.name }
        self.write(tornado.escape.json_encode(comment_hash))

class FlagAskHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, id):
        ask = Ask.objects(id=id)
        flag = self.get_argument("flag","1")
        if not ask: 
            self.write("0")
            return

        if flag == "1":
            if ask.first().flagged_users.count(self.current_user):
                self.write("-1")
                return
            ask.update_one(push__flagged_users=self.current_user)
        else:
            ask.update_one(pull__flagged_users=self.current_user)

class ProfileHandler(BaseHandler):
    def get(self, login):
        user = User.objects(login=login).first()
        if not user: 
            self.render_404
            return
        self.set_title(user.name)
        articles = self.events_articles(user.user_events)
        self.render("profile.html",user=user,articles=articles)

class SettingsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.set_title(u"设置")
        self.render("settings.html")

    @tornado.web.authenticated
    def post(self):
        self.set_title(u"设置")
        frm = SettingsForm(self)
        if not frm.validate():
            frm.render("settings.html")
            return

        User.objects(id=self.current_user.id).update_one(set__name=frm.name,
                                                         set__email=frm.email,
                                                         set__blog=frm.blog,
                                                         set__bio=frm.bio)
        self.notice("保存成功", 'success')
        self.redirect("/settings")
        
class FollowHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        target = self.get_argument('id',None)
        if(target):
            me = self.get_current_user()
            he = User.objects(login = target).first()

            if(not he or me == he):
                #self.notice('有问题',"error")
                self.redirect("/")
                return

            he.update(add_to_set__followers = me)
            me.update(add_to_set__following = he)
            follow_event = UserEvent(user=self.current_user.id,type="followUser",target=he.id)
            follow_event.save()
            User.objects(id = self.current_user.id).update_one(push__user_events = follow_event)
            for event in he.user_events:
                me.update(push__time_line = event)
            for x in self.current_user.followers:
                User.objects(id = x.id).update_one(push__time_line = follow_event)

class UnfollowHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        target = self.get_argument('id',None)
        if(target):
            me = self.get_current_user()
            he = User.objects(login = target).first()
            if(me and he):
                he.update(pull__followers = me)
                me.update(pull__following = he)
                inter = list(set(me.time_line) & set(he.user_events))
                for event in inter:
                    me.update(pull__time_line = event)

class TopicFollowHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument('id',None)
        topic = Topic.objects(id=id).first()
        if(topic):
            if topic.followers.count(self.current_user):
                self.write("-1")
                return
            topic.update(add_to_set__followers=self.current_user)

            event = UserEvent(user=self.current_user.id,type="followTopic",target=topic.id)
            event.save()
            User.objects(id = self.current_user.id).update_one(push__user_events = event)
            User.objects(id = self.current_user.id).update_one(add_to_set__topics = topic.id)
            for x in self.current_user.followers:
                User.objects(id = x.id).update_one(push__time_line = event)

class UnFollowTopicHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument('id',None)
        topic = Topic.objects(id=id).first()
        me = User.objects(id = self.current_user.id).first()
        if(topic and me):
            topic.update(pull__followers=self.current_user)
            User.objects(id = self.current_user.id).update_one(pull__topics = topic.id)

class TopicEditHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument('id',None)
        self.set_title(u"添加话题")
        if(self.current_user.login == 'alex'):
            if(id):
                topic = Topic.objects(id = id).first()
                self.render('topic_edit.html',topic=topic)
            else:
                self.render('topic_edit.html',topic=None)
        else:
            self.redirect("/")

    @tornado.web.authenticated
    def post(self):
        self.set_title(u"添加话题")
        frm = TopicForm(self)

        if not frm.validate():
            frm.render("topic_edit.html")
            return
            
        img = frm.avatar['body']
        topic = Topic(name=frm.topic,
            desc = frm.desc)
        io_obj = BytesIO(img)
        topic.avatar.put(io_obj)
        try:
            topic.save()
        except Exception,exc:
            self.notice(exc,"error")
            frm.render("topic_edit.html")

        self.notice("保存成功", 'success')
        self.redirect("/topic_edit?id="+str(topic.id))

class TopicsHandler(BaseHandler):
    def get(self):
        last_id = self.get_argument("last", None)
        if not last_id:
          topics = Topic.objects().limit(10)
        else:
          topics = Topic.objects(id__gt = last_id)[:10]
        self.render('topics.html',topics=topics)
        
class TopicShowHandler(BaseHandler):
    def get(self,id):
        topic = Topic.objects(id=id).first()
        if not topic:
            self.render_404()
        if(topic):
            self.set_title(topic.name)
            articles = self.events_articles(topic.threads)
            self.render("topic.html",topic = topic,articles=articles)
        
class UploadUserImage(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        image = self.request.files.get('uploaded_image')
        if image:
            try:
                data_bytes = image[0]['body']
                io_obj = BytesIO(data_bytes)
                
                img_obj = Image.open(io_obj)

                new_obj = img_obj.resize((128,128))

                #io_obj = BytesIO()
                new_obj.save(io_obj,format='JPEG')

                io_obj = BytesIO(io_obj.getvalue())
                user = User.objects(id=self.current_user.id).first()
                user.avatar.replace(io_obj)
                user.save()
            except Exception,format_err:
                self.notice(format_err,"error")
        else:
            self.notice('No file in post',"error")
            
        self.redirect('settings')

class AvatarHandler(BaseHandler):
    def get(self):
        name = self.get_argument('name',None)
        topic = self.get_argument('topic',None)
        if(name):
            obj = User.objects(login=name).first()
        elif(topic):
            obj = Topic.objects(name=topic).first()
        else:
            return
        try:
            h = obj.avatar.get()
            content = h.read()
        except Exception,file_err:
            content = open('unknown.png','rb').read()
            
        io =  BytesIO(content)
        s = io.getvalue()
        self.set_header('Content-type', 'image/jpg')
        self.set_header('Content-length', len(s))
        self.write(s)

class FollowAskHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, id):
        ask = Ask.objects(id=id).first()
        if(ask):
            if ask.followers.count(self.current_user):
                self.write("-1")
                return
            ask.update(add_to_set__followers=self.current_user)
            event = UserEvent(user=self.current_user.id,type="followAsk",target=ask.id)
            event.save()
            User.objects(id = self.current_user.id).update_one(push__user_events = event)
            for x in self.current_user.followers:
                User.objects(id = x.id).update_one(push__time_line = event)

class UnFollowAskHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, id):
        ask = Ask.objects(id=id).first()
        me = User.objects(id = self.current_user.id).first()
        if(ask and me):
            ask.update(pull__followers=self.current_user)
            inter = list(set(me.time_line) & set(ask.user_events))
            if(inter):
                for event in inter:
                    me.update(pull__time_line = event)

class GetHotTopicHandler(BaseHandler):
    def get(self):
        hot_topics = [{'name':u'精神病','cnt':7004},{'name':u'神经病','cnt':6074},{'name':u'弱智','cnt':5349},{'name':u'脑残','cnt':4301},\
            {'name':u'脑瘫','cnt':2315},{'name':u'二逼','cnt':315},{'name':u'逗逼','cnt':208}]
        hots = self.generate_hot_topics(5)
        #hots = [random.choice(hot_topics) for x in range(0,5)]
        results = json.dumps(hots, ensure_ascii = False)
        return self.write(results)
