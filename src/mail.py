import os

"""
This is the start of a mail notification endpoint

It's very not implemented yet
"""


class MailSender:
    LOG_FILE = os.getenv("LOG_FILE", "/var/log/fastnetmon-notify.log")
    MAIL_HOSTNAME = os.getenv("MAIL_HOSTNAME", "localhost")
    MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@domain.com")
    MAIL_TO = os.getenv("MAIL_TO", "noc@domain.com")
    SUBJECT_PREFIX = os.getenv("SUBJECT_PREFIX", "Fastnetmon Guard:")
