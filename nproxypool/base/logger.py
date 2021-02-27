import os
import logging
from logging import handlers, getLogger


class FileFilter(logging.Filter):
    def filter(self, record):
        try:
            filter_key = record.levelname
        except AttributeError:
            filter_key = None
        if filter_key in ['WARNING', 'ERROR', 'CRITICAL']:
            result = 1
        else:
            result = 0
        return result


class Logger(object):
    level_relations = {
        'notset': logging.NOTSET,
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    def __init__(self, name='', filename=None, filedir=None, level='info', when='D', back_count=2, fmt=''):
        self.logger = getLogger(name=name)
        self.logger.setLevel(logging.INFO)
        if not fmt:
            fmt = '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'

        format_str = logging.Formatter(fmt) 
        if filename and filedir:
            filename = os.path.join(filedir, filename)
            f = handlers.TimedRotatingFileHandler(
                filename=filename, when=when, interval=1, backupCount=back_count, encoding='utf-8')
            f.setFormatter(format_str)
            f.setLevel(self.level_relations.get(level))
            filter_ = FileFilter()
            f.addFilter(filter_)
            self.logger.addHandler(f)

        t = logging.StreamHandler()
        t.setLevel(logging.INFO)
        t.setFormatter(format_str)
        self.logger.addHandler(t)
        logging.getLogger('apscheduler').setLevel(logging.WARNING)

    def __call__(self):
        return self.logger


def get_logger(name='', filename=None, filedir=None, level='info', when='D', back_count=2, fmt=''):
    _logger = Logger(
        name=name,
        filename=filename,
        filedir=filedir,
        level=level,
        when=when,
        back_count=back_count,
        fmt=fmt
    )()
    return _logger
