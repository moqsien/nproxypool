class PoolEmptyException(Exception):

    def __init__(self):
        Exception.__init__(self)

    def __str__(self):
        return repr('Proxy pool is empty.')


class NotInProject(Exception):

    def __init__(self):
        Exception.__init__(self)

    def __str__(self):
        return repr('Please execute this command in a proxypool project.')
