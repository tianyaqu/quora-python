# coding: utf-8
import re
import markdown as Markdown
from jinja2.utils import urlize, escape
import urllib, hashlib
import datetime

def markdown(value):
    return Markdown.markdown(value)

def md_body(value):
    value = urlize(value,32,True)
    return markdown(value)
    
def tags_name_tag(tags,limit = 0):
    html = []
    if not tags: return ""
    if limit > 0:
      tags = tags[0:limit]
    for tag in tags:
        html.append('<a class="tag" href="/tag/%s">%s</a>' % (tag,tag))
    return ",".join(html)

def user_name_tag(user):
    return '<a href="/%s" class="user">%s</a>' % (user.login,user.name)
        
def strftime(value, type='normal'):
    """
    if type == 'normal':
        format="%Y-%m-%d %H:%M"
    elif type == 'long':
        format="%Y-%m-%d %H:%M:%S"
    else:
        format="%m-%d %H:%M"
    return value.strftime(format)
    """
    total_secs = (datetime.datetime.now() - value).total_seconds()
    min = int(total_secs)/60
    if(min <= 0):
        return ' '
    if(min < 60):
        return str(min) + ' min'
    hour = min/60
    if(hour < 24):
        return str(hour) + ' hour'
        
    day = hour/24
    return str(day) + ' day'
    

def strfdate(value,type='normal'):
    if type == 'normal':
        format="%Y-%m-%d"
    elif type == "long":
        format="%Y-%m-%d"
    else:
        format="%m-%d"
    return value.strftime(format)

# check value is in list
def inlist(value,list):
    if list.count(value) > 0:
        return True
    return false

def avatar(user, size = 40):
    #gravatar_url = "http://www.gravatar.com/avatar/" + hashlib.md5(user.email).hexdigest() +  "?" 
    #gravatar_url += urllib.urlencode({'s':str(size)})
    gravatar_url = "/avatar?name=" + user.login
    return "<a href=\"/%s\" class=\"avatar\"><img src=\"%s\" style=\"width:%dpx;height:%dpx\" title=\"%s\" /></a>" % (user.login,gravatar_url,size,size,user.name)

def is_following(user,id):
    for x in user.following:
        if(x == id):
            return True
    return False
    
    
