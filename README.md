Supervisord Notifier
===========================

Use classic Observer Pattern to implement a simple supervisord PROCESS_LOG listener, and send message to HipChat or Mail or else place.

## Why
<a href="http://supervisord.org/">Supervisord</a> is an useful tool to manage background processes,  and it is used in my project heavily to control <a href="https://www.rabbitmq.com/">RabbitMQ</a> consumer processes. And when the process is crashed by some unexpected conditions, supervisord will record the traceback information to log file. The log info is good for us to solve the problems.  

But the problem is now I always need to ssh to the remote server to find out the log file of the crashed process, and often after a long time that problem happened. It may create a great loss. The cause of these is no effective way to notify me, So I tried to create this simple script to send error log instantly to Hipchat(An Instance Message Application) and mail and other places.

## Demo
![alt text][demo]

**Left window is Hipchat, Right window is supervisord monitor page.**
[demo]: 
https://raw.githubusercontent.com/hanks/Supervisord_Notifier/master/demo/demo.gif "demo"

##Implementation
<ol>
  <li><a href="http://supervisord.org/events.html">Event Listener</a></li>
    <ol>This allows user to implement actions response to specified events sent by supervisord.
    </ol>
  </li>    
  <li><a href="http://supervisord.org/events.html#process-log-event-type">PROCESS_LOG</a>         
    <ol>This event type allows user to interact with supervisord server when supervisord writes error log and fetch the log content.
    </ol>
  </li>                
</ol>

## Configuration
Need to config process like below:

[eventlistener:crashlistenter] ;; **define a event listener process**   
command=python your_absolute_path/notifier.py    
events=PROCESS_LOG ;; **set event type to be listened to**  
redirect_stderr=true  
stdout_logfile=/tmp/crashlistenter.log  

[program:crash_demo]  
command=python your_absolute_path/notifier_error_demo.py  
stderr_logfile=/tmp/crash_demo.log  
autostart=false  
stderr_events_enabled=true  ;; **set to true, means to triggle stderr event when write error logs.**

## Lisence
MIT Lisence
