import os
from configparser import ConfigParser
from stat import S_IWUSR as OWNER_WRITE_PERMISSION
from shutil import ignore_patterns, copy2, copystat
import gunicorn.app.base
from nproxypool.utils.exceptions import NotInProject


IGNORE = ignore_patterns('*.pyc', '__pycache__', '.svn')


def _make_writable(path):
    current_permissions = os.stat(path).st_mode
    os.chmod(path, current_permissions | OWNER_WRITE_PERMISSION)


class GunicornStandalone(gunicorn.app.base.BaseApplication):
    def __init__(self, application, options=None):
        """ Construct the Application. Default gUnicorn configuration is loaded """

        self.application = application
        self.options = options or {}
        print(self.options)

        # if port, or host isn't set-- run from os.environments
        #
        super(GunicornStandalone, self).__init__()

    def init(self, parser, opts, args):
        """ Apply our custom settings """

        cfg = {}
        for k, v in self.options.items():
            if k.lower() in self.cfg.settings and v is not None:
                cfg[k.lower()] = v
        return cfg

    def load_config(self):
        config = dict([(key, value) for key, value in self.options.items()
                       if key in self.cfg.settings and value is not None])
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def get_config_object(dir):
    file_path = os.path.join(dir, './pool.cfg')
    if not os.path.exists(file_path):
        raise NotInProject()
    config = ConfigParser()
    config.read(file_path)
    return config


def get_gunicorn_config(dir):
    config = get_config_object(dir)
    g_conf = dict()
    section = 'gunicorn'
    for opt in config.options(section):
        if opt in ('pidfile', 'accesslog', 'errorlog'):
            g_conf[opt] = os.path.join(dir, config.get(section, opt))
        else:
            g_conf[opt] = config.get(section, opt)
    return g_conf


def get_redis_config(dir):
    config = get_config_object(dir)
    conf_redis = dict()
    conf_redis['host'] = config.get('redis', 'host')
    conf_redis['port'] = config.getint('redis', 'port')
    conf_redis['password'] = config.get('redis', 'password')
    return conf_redis


def get_fetcher_insert_db(dir):
    config = get_config_object(dir)
    for section in config.sections():
        if 'init' in section:
            return dict(db=config.getint(section, 'from_db'))


def get_logfile_dir(dir):
    config = get_config_object(dir)
    logfile_dir_name = config.get('logfile', 'dirname')
    if not logfile_dir_name.startswith('./'):
        logfile_dir_name = './{}'.format(logfile_dir_name)
    return os.path.join(dir, logfile_dir_name)


def get_verifier_config(dir):
    config = get_config_object(dir)
    conf_list = []
    opt_bool = (
        'is_from_db_zset',
        'is_to_db_zset'
    )
    opt_int = (
        'from_db',
        'to_db',
        'score_threshold',
        'score_decrease_by',
        'time_out',
        'to_sleep',
        'max_worker'
    )
    for section in config.sections():
        s = dict()
        if section in ('redis',):
            continue
        for opt in config.options(section):
            if opt in opt_bool:
                s[opt] = config.getboolean(section, opt)
            elif opt in opt_int:
                s[opt] = config.getint(section, opt)
            else:
                s[opt] = config.get(section, opt)
        conf_list.append(s)
    return conf_list


def get_sychronizer_config(dir):
    config = get_config_object(dir)
    conf_sync = dict()
    second_db_keys = []
    for section in config.sections():
        if section in ('redis',):
            for opt in config.options(section):
                conf_sync[opt] = config.get(section, opt)
        elif 'init' in section:
            conf_sync['first_db'] = config.getint(section, 'from_db')
        elif 'sync' in section:
            conf_sync['to_sleep'] = config.getint(section, 'to_sleep')
        elif 'verifier' in section:
            conf_sync['second_db'] = config.getint(section, 'to_db')
            second_db_keys.append(config.get(section, 'to_db_key'))
        else:
            pass
    conf_sync['second_db_keys'] = list(set(second_db_keys))
    return conf_sync


def get_fetcher_config(dir):
    config = get_config_object(dir)
    conf_fetcher = dict()
    conf_fetcher['to_sleep'] = config.getint('fetcher', 'to_sleep')
    for section in config.sections():
        if 'init' in section:
            conf_fetcher['db'] = config.getint(section, 'from_db')
    return conf_fetcher


def copytree(src, dst):
    ignore = IGNORE
    names = os.listdir(src)
    ignored_names = ignore(src, names)
    if not os.path.exists(dst):
        os.makedirs(dst)
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        if os.path.isdir(srcname):
            copytree(srcname, dstname)
        else:
            copy2(srcname, dstname)
            _make_writable(dstname)
    copystat(src, dst)
    _make_writable(dst)
