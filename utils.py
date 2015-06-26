# coding: utf-8
import hashlib, uuid
import datetime
import calendar
from dateutil.relativedelta import relativedelta

def truncate_lines(body, lines = 4, max_chars = 400):
    if not body: return ""
    body_lines = body.splitlines()
    summary = "\n".join(body_lines[0:lines])
    return summary
    summary = _truncate_lines(body_lines, lines - 1, summary, max_chars)
    return summary

def _truncate_lines(body_lines, lines, summary, max_chars):
    if len(summary) > max_chars:
        lines -= 1
        if lines > 1:
            body_lines = body_lines[0:lines]
            summary = "\n".join(body_lines)
            return _truncate_lines(body_lines, lines, summary, max_chars)
        else:
            summary = body_lines[0][0:max_chars]
            return summary
    else:
        return summary

def md5(str):
    m = hashlib.md5()
    m.update(str)
    return m.hexdigest()

def format_tags(str):
    str = str.replace(u"，",",")
    tags = str.split(",")
    tags = map(lambda tag: tag.strip(), tags)
    tags = filter(lambda tag: len(tag) > 0, tags)
    tags = list(set(tags))
    return tags

def sid():
    return uuid.uuid1().hex

def get_week_range(date):
    w = int(date.strftime('%w'))
    if(w == 0):
        w = 7
    date_t = date.date()
    start = date_t - relativedelta(days=w-1)
    end = start + relativedelta(days=7)
    return start,end

def get_month_range(date):
    date_t = date.date()
    start = date_t.replace(day = 1)
    end = start + relativedelta(months=1)
    return start,end