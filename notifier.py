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
    """Abstract class for observer
    """
    def update(self, event):
        """Notify new event information to observer
        """
        raise NotImplementedError

class AbstractNotificationPublisher(object):
    """Abstract class for publisher
    """
    def register_observer(self, observer):
        raise NotImplementedError

    def remove_observer(self, observer):
        raise NotImplementedError

    def notify(self, event):
        """Use registered observer class to do actual notify job
        """
        raise NotImplementedError

class NotificationPublisher(AbstractNotificationPublisher):
    """Implemetation of abstract publisher
    """
    def __init__(self, target_event_name_list):
        # be used to communicate with supervisord server
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

        # observer list
        self.observer_list = []
        # event name list that want to listen to 
        self.target_event_name_list = target_event_name_list

    def register_observer(self, observer):
        self.observer_list.append(observer)

    def remove_observer(self, observer):
        self.observer_list.remove(observer)

    def notify(self, event):
        for observer in self.observer_list:
            observer.update(event)
        
    def runforever(self):
        """another listenter implementation, used to 
        listen to event emmitted from supervisord server
        """
        
        # infinite loop to listen to supervisord event        
        while True:
            headers, payload = childutils.listener.wait(self.stdin, self.stdout)

            if headers['eventname'] not in self.target_event_name_list:
                # if not target event, just ignore
                childutils.listener.ok(self.stdout)
                continue

            pheaders, pdata = childutils.eventdata(payload+'\n')
            # 'PROCESS_STATE_EXITED' event has expected field, other event type has no this filed,
            # so just set to None
            is_expected = pheaders.get('expected', None)
            if is_expected:
                if int(is_expected):
                    # when is a expected process exited, just igore
                    childutils.listener.ok(self.stdout)
                    continue

            self.stderr.write('{} happened, notification\n'.format(headers['eventname']))
            self.stderr.flush()

            # collect event informations, header in differe event will be different, 
            # here just use a general dictionary
            event = {'processname': pheaders.get('processname', None),
                     'groupname': pheaders.get('groupname', None),
                     'pid': pheaders.get('pid', None),
                     'from_state': pheaders.get('from_state', None),
                     'happened_at': childutils.get_asctime(),
                     'data': pdata}
            
            self.notify(event)

            # job of supervisord event listener is finished, send ok sign
            childutils.listener.ok(self.stdout)
    

class HipchatObserver(AbstractNotificationObserver):
    """Implementation of observer to notify with HipChat 
    """
    def __init__(self):
        self.rooms = ['Kemono - Production Deploy Notification']
        self.color = 'green'
        self.is_notify = False
        self.hip_chat = HypChat(self._get_token())

    def add_room(self, room_name):
        self.rooms.append(room_name)
    
    def remove_room(self, room_name):
        self.rooms.remove(room_name)
    
    def update(self, event):
        """use hitchat API to send message to specified rooms
        """
        msg = self._build_msg(event)
        
        for room in self.rooms:
            r = self.hip_chat.get_room(room)
            r.message(msg, color=self.color, notify=self.is_notify)

    def _build_msg(self, event):
        """build message for event with default HTML format of hipchat message
        """
        msg = u'Process %(processname)s in group %(groupname)s exited unexpectedly (pid %(pid)s) from state %(from_state)s at %(happened_at)s<br /><br />Error log:<br />%(data)s' % event
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
