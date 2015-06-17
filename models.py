# coding: utf-8
from mongoengine import *
from bson import objectid
import datetime

class User(Document):
    login = StringField(required=True,min_length=4,max_length=20)
    email = EmailField(required=True,unique=True)
    name = StringField(required=True,min_length=2)
    password = StringField(required=True)
    blog = URLField()
    bio = StringField(max_length=1000)
    followers = ListField(ReferenceField('self', dbref=False))
    following = ListField(ReferenceField('self', dbref=False))
    time_line = ListField(ObjectIdField())
    avatar = ImageField(thumbnail_size=(75,75,True))
    created_at = DateTimeField(default=datetime.datetime.now)

class Comment(EmbeddedDocument):
    id = StringField(required=True)
    body = StringField(required=True,min_length=4, max_length=2000)
    user = ReferenceField(User)
    created_at = DateTimeField(default=datetime.datetime.now)

class Vote(EmbeddedDocument):
    user = ReferenceField(User,required=True)
    up = BooleanField(required=True,default=True)
    
class Ask(Document):
    title = StringField(required=True,min_length=5,max_length=255)
    body = StringField()
    summary = StringField()
    user = ReferenceField(User)
    tags = ListField(StringField(max_length=30))
    comments = ListField(EmbeddedDocumentField(Comment))
    answers_count = IntField(required=True,default=0)
    flagged_users = ListField(ReferenceField(User))
    created_at = DateTimeField(default=datetime.datetime.now)
    replied_at = DateTimeField(default=datetime.datetime.now)

class Answer(Document):
    ask = ReferenceField(Ask)
    body = StringField()
    user = ReferenceField(User)
    comments = ListField(EmbeddedDocumentField(Comment))
    vote = IntField(required=True,default=0)
    votes = ListField(EmbeddedDocumentField(Vote))
    created_at = DateTimeField(default=datetime.datetime.now)

    @staticmethod
    def do_vote(id, up, user):
        answer = Answer.objects(id=id).first()
        if not answer: return 0

        new_vote = Vote(user=user,up=up)
        for old_vote in answer.votes:
            # if there exist this user's vote
            if old_vote.user.id == user.id:
                # check is vote type equal this time type
                if old_vote.up == up:
                    return -1
                else:
                    # remove old voted_user
                    Answer.objects(id=id).update_one(pull__votes=old_vote)
                    break

        if up == True:
            vote_num = 1
        else:
            vote_num = -1

        Answer.objects(id=id).update_one(inc__vote=vote_num,
                                     push__votes=new_vote)
        return 1

class UserEvent(Document):
    happended_at = DateTimeField(default=datetime.datetime.now)
    user = ReferenceField(User)
    type = StringField()
    target = ObjectIdField()
    
class Article():
    def __init__(self,event):
        if(event.type == 'ask'):
            stuff = Ask.objects(id=event.target).first()
            self.title = stuff.title
            self.body = stuff.body
            self.count = stuff.answers_count
            self.created_at = stuff.created_at
            self.url = '/ask/' + str(stuff.id)
            self.user = event.user
            self.type = event.type
        elif(event.type == 'answer'):
            stuff = Answer.objects(id=event.target).first()
            self.title = stuff.ask.title
            self.body = stuff.body
            self.count = stuff.vote
            self.created_at = stuff.created_at
            self.url = '/ask/' + str(stuff.ask.id)
            self.user = event.user
            self.type = event.type
