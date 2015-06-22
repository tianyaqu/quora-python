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
    return '<a href="/u/%s" class="user">%s</a>' % (user.login,user.name)
        
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
        return u'刚刚'
    if(min < 60):
        return str(min) + u' 分钟前'
    hour = min/60
    if(hour < 24):
        return str(hour) + u' 小时前'
        
    day = hour/24
    return str(day) + u' 天前'
    

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

def avatar(user,size = 40,c_type = 0):
    gravatar_url = "/avatar?name=" + user.login
    type = 'avatar'
    if(c_type != 0):
        type = 'item-link-avatar'

    return "<a href=\"/u/%s\" class=\"%s\"><img src=\"%s\" style=\"width:%dpx;height:%dpx\" title=\"%s\" /></a>" % (user.login,type,gravatar_url,size,size,user.name)


def is_following(user,id):
    if(user and user.following):
        for x in user.following:
            if(x == id):
                return True
    return False

def num_human(num):
    if(num < 100):
        return str(num)
    elif(num < 1000):
        return str(num/100) + '00+'
    elif(num < 10000):
        return str(num/1000) + ',000+'
    else:
        return str(num/10000) + '0,000+'

        
    
    
