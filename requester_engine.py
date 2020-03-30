import pycurl
import time
import Queue
import timeloop
from timeloop import Timeloop
from datetime import timedelta, datetime
from tornado import ioloop, httpclient
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from argparse import ArgumentParser
import requests
import sys
import pytz
#import collect_metrics

i = 0
tl = Timeloop()
current_t = 0
global q,q2
global mymap
COUNTER_599= 0
START_TIME = ""
END_TIME = ""

def set_options():
    parser = ArgumentParser(description='Applying different test distribution on the microservices platform')
    parser.add_argument("--ip", "-i",  required=True, help="IP address of the entry point on the platform")
    args = parser.parse_args()
    return args


@tl.job(interval=timedelta(seconds=1))
def sample_job_every_1s():
    #if there is instance to execute
    if (q.empty() == False):
        io_loop = q.get(block=False)
        io_loop.make_current()

        ioloop.IOLoop.current().start()

        i = q2.get()
        print str(i)+' requests in {}'.format(get_time()) #FIX TIMEZONE
#        print str(i)+' requests in {}'.format(time.ctime())
	ioloop.IOLoop.current().close(all_fds=True)
        ioloop.IOLoop.clear_current()
    else:
	try:
	  tl.stop()
	except:
          print 'No jobs sent at {}'.format(get_time())
	  END_TIME = get_time()
	  collect_metrics.get_metrics(START_TIME, END_TIME)
	  sys.exit(1)
#        print 'No jobs sent at {}'.format(time.ctime())


def handle_request(response):
    global COUNTER_599
    if response.code == 599:
	COUNTER_599 += 1
    #Get the current instance
    current = ioloop.IOLoop.current()
    #Stop at the last request
    mymap[current] -= 1;
    if (mymap[current] == 0):
        ioloop.IOLoop.current().stop()


def get_time():
    tz_NY = pytz.timezone('America/New_York')
    datetime_NY = datetime.now(tz_NY)
    return str(datetime_NY.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    mymap = {}
    args = set_options()

    #Creating queues to store the HTTP requests
    q = Queue.Queue()
    q2 = Queue.Queue()

    #Creating task distribution from file
    for line in open('url_objects.file'):
        url,nbr_requests = line.split(" ")

        #Creates a request instance
        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient", defaults=dict(connect_timeout=500, request_timeout=500, max_clients=3350))
        io_loop = ioloop.IOLoop.current(instance=True)
        http_client = AsyncHTTPClient()

        #Iterates through the number of requests
        for x in range(int(nbr_requests)):
             http_client.fetch(url.strip(), handle_request, method ='HEAD')

        # Queues the instance
        q.put(io_loop)
        q2.put(int(nbr_requests))
        # Map the amount of requests
        mymap[io_loop] = int(nbr_requests)

        ioloop.IOLoop.clear_current()

    START_TIME = get_time()

    #Periodic task
    tl.start(block=True)

    print COUNTER_599

