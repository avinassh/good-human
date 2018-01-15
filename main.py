#!/usr/bin/env python

import time
import json
import random
import os

import praw
import prawcore
from peewee import (SqliteDatabase, Model, CharField, OperationalError,
                    DoesNotExist)

from settings import (app_key, app_secret, username, password,
                      user_agent, ignore_subs)

reddit_client = praw.Reddit(user_agent=user_agent, client_id=app_key,
                            client_secret=app_secret, username=username,
                            password=password)


replied_comments = []
last_checked_comment = []
thanked_comments = []
db = SqliteDatabase(os.getenv('DB_LOCATION', 'good-human.db'))


with open('welcome_messages.json') as f:
    welcome_messages = json.load(f)['messages']


class RepliedComments(Model):
    comment_id = CharField()
    author = CharField()
    subreddit = CharField()

    class Meta:
        database = db


class ThankedComments(Model):
    comment_id = CharField()
    author = CharField()
    subreddit = CharField()

    class Meta:
        database = db


def initialize_db():
    db.connect()
    try:
        db.create_tables([RepliedComments, ThankedComments])
    except OperationalError:
        # Table already exists. Do nothing
        pass


def deinit():
    db.close()


def is_already_replied(comment_id):
    if comment_id in replied_comments:
        return True
    try:
        RepliedComments.select().where(
            RepliedComments.comment_id == comment_id).get()
        return True
    except DoesNotExist:
        return False


def is_already_thanked(comment_id):
    if comment_id in thanked_comments:
        return True


def log_this_comment(comment, TableName=RepliedComments):
    comment_data = TableName(comment_id=comment.id,
                             author=comment.author.name,
                             subreddit=comment.subreddit.display_name)
    comment_data.save()
    replied_comments.append(comment.id)


def get_a_random_message():
    return random.choice(welcome_messages)


def get_message():
    return 'good human\n\n---\n\n^(I am a bot and I thank these amazing humans who are transcribing for the community)'


def take_a_nap():
    time.sleep(30)


def does_comment_has_signature(comment_body):
    signature = 'human volunteer content transcriber for Reddit'.lower()
    for key in signature.split():
        if key not in comment_body.lower():
            return False
    return True


def serve():
    global last_checked_comment
    for comment in reddit_client.subreddit('all').stream.comments():
        # ignore comments from main sub
        subreddit_name = comment.subreddit.display_name
        if subreddit_name.lower() in ignore_subs:
            continue
        if comment.id in last_checked_comment:
            break
        last_checked_comment.append(comment.id)
        if not does_comment_has_signature(comment_body=comment.body):
            continue
        author = comment.author
        if author.name == 'you_are_good_human':
            continue
        if is_already_replied(comment.id):
            break
        comment.reply(get_message())
        log_this_comment(comment)
        replied_comments.append(comment.id)


def reply_to_self_comments():
    for comment in reddit_client.inbox.comment_replies():
        if is_already_thanked(comment_id=comment.id) or not comment.new:
            break
        comment.mark_read()
        if 'thank' in comment.body.lower():
            comment.reply(get_a_random_message())
            thanked_comments.append(comment.id)
            log_this_comment(comment, TableName=ThankedComments)


def main():
    while True:
        try:
            reply_to_self_comments()
            serve()
        except prawcore.exceptions.RequestException:
            pass
        take_a_nap()


if __name__ == '__main__':
    initialize_db()
    main()
    deinit()
