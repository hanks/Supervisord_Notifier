#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from supervisor import childutils
from hypchat import HypChat
try:
    import pit
except ImportError:
    def _pit_get(*args, **kwargs):
        raise ImportError('please pip install pit firstly!')
else:
    def _pit_get(*args, **kwargs):
        if not os.environ.get('EDITOR'):
            os.environ['EDITOR'] = 'vi'

        return pit.Pit.get(*args, **kwargs)

class AbstractNotificationObserver(object):
    def update(self, event):
        raise NotImplementedError

class AbstractNotificationPublisher(object):
    def register_observer(self, observer):
        raise NotImplementedError

    def remove_observer(self, observer):
        raise NotImplementedError

    def notify(self, event):
        raise NotImplementedError

class NotificationPublisher(AbstractNotificationPublisher):
    def __init__(self, target_event_name_list):
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.observer_list = []
        self.target_event_name_list = target_event_name_list

    def register_observer(self, observer):
        self.observer_list.append(observer)

    def remove_observer(self, observer):
        self.observer_list.remove(observer)

    def notify(self, event):
        for observer in self.observer_list:
            observer.update(event)
        
    def runforever(self):
        while True:
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)

            if headers['eventname'] not in self.target_event_name_list:
                 childutils.listener.ok(self.stdout)
                 continue

            pheaders, pdata = childutils.eventdata(payload+'\n')
            if int(pheaders['expected']):
                childutils.listener.ok(self.stdout)
                continue

            self.stderr.write('{} happened, notification\n'.format(headers['eventname']))
            self.stderr.flush()

            event = {'processname': pheaders.get('processname', None),
                     'groupname': pheaders.get('groupname', None),
                     'pid': pheaders.get('pid', None),
                     'from_state': pheaders.get('from_state', None),
                     'happened_at': childutils.get_asctime(),
                     'data': pdata}
            
            self.notify(event)
            
            childutils.listener.ok(self.stdout)
    

class HipchatObserver(AbstractNotificationObserver):
    def __init__(self):
        self.rooms = ['Kemono - Production Deploy Notification']
        self.color = 'green'
        self.is_notify = False

    def add_room(self, room_name):
        self.rooms.append(room_name)
    
    def remove_room(self, room_name):
        self.rooms.remove(room_name)
    
    def update(self, event):
        h = HypChat(self._get_token())
        
        msg = self._build_msg(event)
        
        for room in self.rooms:
            r = h.get_room(room)
            r.message(msg, color=self.color, notify=self.is_notify)

    def _build_msg(self, event):
        msg = u'Process %(processname)s in group %(groupname)s exited unexpectedly (pid %(pid)s) from state %(from_state)s at %(happened_at)s<br /><br />Data: %(data)s' % event
        return msg
        
    def _get_token(self):
        config = _pit_get('hipchat',
                      {'require': {'token': 'your hipchat access token'}})
        return config['token']

class MailObserver(AbstractNotificationObserver):
    def update(self, event):
        pass

def main(argv=sys.argv):
    if not 'SUPERVISOR_SERVER_URL' in os.environ:
        sys.stderr.write('Must be run as a supervisor event '
                         'listener\n')
        sys.stderr.flush()
        return

    #'PROCESS_STATE_EXITED'
    crash_publisher = NotificationPublisher(['PROCESS_LOG_STDERR'])
    
    hipchat_observer = HipchatObserver()
    mail_observer = MailObserver()

    crash_publisher.register_observer(hipchat_observer)
    crash_publisher.register_observer(mail_observer)
    
    crash_publisher.runforever()

if __name__ == '__main__':
    main()
