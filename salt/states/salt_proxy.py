# -*- coding: utf-8 -*-
'''
    Salt proxy state

    .. versionadded:: 2015.8.2

    State to deploy and run salt-proxy processes
    on a minion.

    Set up pillar data for your proxies per the documentation.

    Run the state as below

    ..code-block:: yaml

        salt-proxy-configure:
            salt_proxy.configure_proxy:
                - proxyname: p8000
                - start: True

    This state will configure the salt proxy settings
    within /etc/salt/proxy (if /etc/salt/proxy doesn't exists)
    and start the salt-proxy process (default true),
    if it isn't already running.
'''
from __future__ import absolute_import

from salt.ext.six.moves import shlex_quote as quote
from salt.utils import fopen

import os
import logging

log = logging.getLogger(__name__)


def _write_proxy_conf(proxyfile):
    '''
    write to file
    '''
    msg = 'Invalid value for proxy file provided!, Supplied value = {0}' \
        .format(proxyfile)

    log.trace('Salt Proxy Module: write proxy conf')

    if proxyfile:
        log.debug('Writing proxy conf file')
        with fopen(proxyfile, 'w') as proxy_conf:
            proxy_conf.write('master = {0}'
                             .format(__grains__['master']))
        msg = 'Wrote proxy file {0}'.format(proxyfile)
        log.debug(msg)

    return msg


def _proxy_conf_file(proxyfile, test):
    '''
    Check if proxy conf exists and update
    '''
    changes_old = []
    changes_new = []
    success = True
    if not os.path.exists(proxyfile):
        try:
            if not test:
                changes_new.append(_write_proxy_conf(proxyfile))
                msg = 'Salt Proxy: Wrote proxy conf {0}'.format(proxyfile)
            else:
                msg = 'Salt Proxy: Update required to proxy conf {0}' \
                    .format(proxyfile)
        except (OSError, IOError) as err:
            success = False
            msg = 'Salt Proxy: Error writing proxy file {0}'.format(str(err))
            log.error(msg)
            changes_new.append(msg)
        changes_new.append(msg)
        log.debug(msg)
    else:
        msg = 'Salt Proxy: {0} already exists, skipping'.format(proxyfile)
        changes_old.append(msg)
        log.debug(msg)
    return success, changes_new, changes_old


def _is_proxy_running(proxyname):
    '''
    Check if proxy for this name is running
    '''
    cmd = ('ps ax | grep "salt-proxy --proxyid={0}" | grep -v grep'
           .format(proxyname))
    cmdout = __salt__['cmd.run_all'](
        cmd,
        timeout=5,
        python_shell=True)
    if not cmdout['stdout']:
        return False
    else:
        return True


def _proxy_process(proxyname, test):
    '''
    Check and execute proxy process
    '''
    changes_old = []
    changes_new = []
    if not _is_proxy_running(proxyname):
        if not test:
            __salt__['cmd.run'](
                'salt-proxy --proxyid={0} -l info -d'.format(proxyname),
                timeout=5)
            changes_new.append('Salt Proxy: Started proxy process for {0}'
                               .format(proxyname))
        else:
            changes_new.append('Salt Proxy: process {0} will be started'
                               .format(proxyname))
    else:
        changes_old.append('Salt Proxy: already running for {0}'
                           .format(proxyname))
    return True, changes_new, changes_old


def configure_proxy(name, proxyname='p8000', start=True):
    '''
    Create the salt proxy file and start the proxy process
    if required

    Parameters:
        name:
            The name of this state
        proxyname:
            Name to be used for this proxy (should match entries in pillar)
        start:
            Boolean indicating if the process should be started
    '''
    changes_new = []
    changes_old = []
    status_file = True
    test = __opts__['test']

    # write the proxy file if necessary
    proxyfile = '/etc/salt/proxy'
    status_file, msg_new, msg_old = _proxy_conf_file(proxyfile, test)
    changes_new.extend(msg_new)
    changes_old.extend(msg_old)
    status_proc = False

    # start the proxy process
    if start:
        status_proc, msg_new, msg_old = _proxy_process(quote(proxyname), test)
        changes_old.extend(msg_old)
        changes_new.extend(msg_new)
    else:
        changes_old.append('Start is False, not starting salt-proxy process')
        log.debug('Process not started')

    return {
        'result': status_file and status_proc,
        'changes': {
            'old': '\n'.join(changes_old),
            'new': '\n'.join(changes_new),
        },
        'name': proxyname,
        'comment': '{0} config messages'.format(name)
    }
