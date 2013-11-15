import sys
import os
import subprocess

import json
import time
import re


from requests_oauthlib import OAuth1Session

import logging
import logging.config

import settings

logging.config.dictConfig(settings.LOGGING)
logger = logging.getLogger('hackpad_backup')
console = logging.getLogger('console')

g_format = 'html'
g_timezone = '+0000'
g_delay = 1

# only if you know what it is
g_out_of_order_commit = True

api_keys = {}


class HackpadException(Exception):
    pass


def load_api_keys():
    logger.info('Loading of API Keys started')
    credentials_file = None

    # read from api_keys.txt file credentials_file variable
    try:
        credentials_file = file('api_keys.txt')
    except IOError:
        logger.error('Credentials file "api_keys.txt" is not provided or can not be opened')

    # set a guard
    if not credentials_file:
        return

    # read each line of api_keys.txt
    for line in credentials_file:
        line = re.sub('#.*', '', line)
        if not line:
            continue
        data = line.split()
        if len(data) == 3:
            key, secret, site = data
            logger.info('Site to update: %s' % site)
        else:
            site = ''
            key, secret = data
            logger.info('Site name not provided')
        api_keys[site] = key, secret
        logger.info('API keys saved')


class Hackpad:
    def __init__(self, site=''):
        if site not in api_keys:
            logger.error('The credentials provided are not valid for this site (site: %s)' % site)
            raise ValueError

        if site:
            self.base = 'https://%s.hackpad.com' % site
        else:
            self.base = 'https://hackpad.com'
        self.hackpad = OAuth1Session(*api_keys[site])

    def _get(self, url):
        console.debug('Retrieving from: %s' % url)
        r = self.hackpad.get(url)

        # for debug
        with file('tmp.txt', 'w') as f:
            f.write(r.content)

        return r

    def get_pad_content(self, padid, file_format='html', revision=None):
        if revision:
            url = self.base + '/api/1.0/pad/%s/content/%s.%s' % (padid, revision, file_format)
        else:
            url = self.base + '/api/1.0/pad/%s/content.%s' % (padid, file_format)

        r = self._get(url)

        return r.content

    def list_updated_pads(self, timestamp):
        url = self.base + '/api/1.0/edited-since/%d' % int(timestamp)
        r = self._get(url)
        o = json.loads(r.text)
        if 'success' in o and not o['success']:
            raise HackpadException, o['error']
        return o

    def list_revisions(self, padid):
        url = self.base + '/api/1.0/pad/%s/revisions' % padid
        r = self._get(url)
        o = json.loads(r.text)
        if 'success' in o and not o['success']:
            raise HackpadException, o['error']
        return o

    def list_all_pads(self):
        url = self.base + '/api/1.0/pads/all'
        r = self._get(url)
        o = json.loads(r.text)
        if 'success' in o and not o['success']:
            raise HackpadException, o['error']
        return o


class Storage:
    def __init__(self, site):
        self.site = site
        self.data = []

        try:
            assert re.match(r'^\w+$', site)
        except AssertionError:
            logger.critical('There is a problem with a pad name, please check your pads. Abborting...')

        self.base = 'data/%s' % (site or 'main')

        if not os.path.exists(self.base):
            os.makedirs(self.base)

        if not os.path.exists(os.path.join(self.base, '.git')):
            cmd = 'cd %s && git init' % self.base,
            subprocess.check_call(cmd, shell=True)

    def verify_padid(self, padid):
        if not re.match(r'^[\w%.-]+$', padid):
            logger.error('There is a problem with one of the pads name. '
                         'Please check your pads. Aborting...')
            raise ValueError

    def _get_store_filename(self, padid):
        self.verify_padid(padid)
        assert not re.match(r'^\.', padid)
        return '%s.%s' % (padid, g_format)

    def _get_store_path(self, padid):
        # check for security
        path = os.path.join(self.base, self._get_store_filename(padid))
        return path

    def _git_log(self, padid=None):
        if padid is None:
            cmd = 'cd %s && git log -n 1 --pretty="format:%%B"' % self.base
            console.debug('Initializing command: %s' % cmd)
            try:
                output = subprocess.check_output(cmd, shell=True)
            except subprocess.CalledProcessError:
                logger.error('Subprocess error on command: %s' % cmd)
                return None
        else:
            path = self._get_store_path(padid)
            if not os.path.exists(path):
                return None

            cmd = 'cd %s && git log -n 1 --pretty="format:%%B" "%s"' % (self.base, self._get_store_filename(padid))
            console.debug('Initializing command: %s' % cmd)
            output = subprocess.check_output(cmd, shell=True)
        return output

    def get_last_backup_time(self):
        log = self._git_log()
        if log is None:
            return 0
        console.debug(repr(log))
        m = re.search('^timestamp (\d+(?:\.\d+)?)$', log, re.M)
        assert m
        return float(m.group(1))

    def get_version(self, padid):
        log = self._git_log(padid)
        if log is None:
            return 0

        m = re.search('^version (\d+)$', log, re.M)
        assert m
        return int(m.group(1))

    def add(self, t, rev, padid, content):
        self.data.append((t, rev, padid, content))

    def _git_commit(self, padid, datestr, msg, content):
        path = self._get_store_path(padid)

        if os.path.exists(path):
            old_content = file(path).read()
            if old_content == content:
                console.debug('No new content in hackpad')
                return

        with open(path, 'w') as f:
            f.write(content)

        fn = self._get_store_filename(padid)
        cmd = 'cd %s && git add "%s" && git commit --date="%s" -a -F -' % (self.base, fn, datestr)
        console.debug('Commiting with command "%s"' % cmd)
        console.debug('Message with the commit: %s' % msg.encode('utf8'))
        p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE)
        stdout, stderr = p.communicate(msg.encode('utf8'))
        assert p.returncode == 0

    def commit(self):
        # sort by timestamp
        self.data.sort()

        for t, rev, padid, content in self.data:

            datestr = '%s %s' % (int(t), g_timezone)
            msg = ('timestamp %(timestamp)s\n' +
                   'version %(version)s\n' +
                   'authors %(authors)s\n') % dict(timestamp=t,
                                                   version=rev['endRev'],
                                                   authors=','.join(rev['authors']),
                                                   )

            self._git_commit(padid, datestr, msg, content)

        self.data = []


def backup_site(site):
    """
    Creates handlers connection to hackpad site and storing data
    """
    hackpad = Hackpad(site)
    storage = Storage(site)

    # checking previous backups
    if g_out_of_order_commit:
        last_backup = 0
    else:
        last_backup = storage.get_last_backup_time()

    now = time.time()

    try:
        padids = hackpad.list_updated_pads(last_backup)
    except HackpadException:
        logger.warning('Could not retrieve only updated pads. Retrieving all pads...')
        padids = hackpad.list_all_pads()

    for padid in padids:
        storage.verify_padid(padid)

    for padid in padids:
        if re.match(r'^[.-]', padid):
            console.debug(sys.stderr, "I don't like this padid: %s" % padid)
            continue

        last_version = storage.get_version(padid)
        console.debug('Latest vestion of this pad: %s' % last_version)

        for rev in hackpad.list_revisions(padid):
            del rev['htmlDiff']
            # sample after deletion:
            # {
            #  u'endRev': 215,
            #  u'authorPics': [u'https://graph.facebook.com/1234567/picture?type=square'],
            #  u'timestamp': 1375949266.528, u'startRev': 160,
            #  u'authors': [u'John Doe'],
            #  u'emails': []
            # }

            # ignore old revisions
            # NOTE: endRev=0 means just created and has not been modified yet
            if last_version >= rev['endRev']:
                continue
            # in order to avoid race condition, ignore recent changes
            if rev['timestamp'] > now - 60:
                continue

            content = hackpad.get_pad_content(padid, file_format=g_format, revision=rev['endRev'])

            storage.add(rev['timestamp'], rev, padid, content)
            time.sleep(g_delay)

        if g_out_of_order_commit:
            storage.commit()
    storage.commit()


def run_backup():
    """
    Reading from a backup_list.txt file
    Example of a file content:
    [name of the site]/[pad name]
    Note: Currently only implemented '*', for all pads on site
    TODO: Implement particular pad backup
    """
    backup_list = None

    try:
        backup_list = file('backup_list.txt')
    except IOError:
        logger.error('Info file "backup_list.txt" is not provided or can not be opened')

    # seting guard
    if not backup_list:
        return

    for line in backup_list:
        line = re.sub('#.*', '', line).strip()
        if not line:
            continue
        console.debug('Line: %s' % line)

        site, item = line.split('/')
        logger.info('Backup defined for: site %s and pad %s' % (site, item))

        try:
            assert re.match(r'^\w+$', site)
        except AssertionError:
            logger.error('Padname error: %s', item)
            logger.critical('There is a problem with a pad name, please check your pads. Abborting...')

        if item != '*':
            logger.critical('Backing up individual pads is not implemented. Aborting...')
            raise NotImplementedError
        else:
            backup_site(site)


def main():

    load_api_keys()
    logger.info('Loading of API keys done')

    run_backup()

if __name__ == '__main__':
    main()
