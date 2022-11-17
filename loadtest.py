import requests, sys, logging

# Requests python module for sending HTTP requests and it returns an object with Response data (status, encoding, content etc)
# sys module for directly interacting with system interpreter
# logging - write status message to a file - info, debug, warning, error

import pandas as pd
import arrow as ar
import matplotlib.pyplot as plt
from time import time, sleep
from threading import Thread
from multiprocessing import Queue


class LoadTest(object):
    
    def __init__(self, urls):
        logging.basicConfig(filename='loadtestlog.log', level=logging.INFO)
        self.urls = urls
        self.li = []
        self.df = pd.DataFrame()

    # Function for getting Status for HTTP Request
    def _getStatus(self, url):
        try:
            response = requests.get(url=url)
        except Exception as e:
            print(e)
            return "error", url
        length = response.headers['content-length'] if 'content-length' in response.headers else 0
        return url, response.status_code, length

    def _handleResults(self):
        while True:
            url = self.q.get()
            url, status, length = self._getStatus(url)
            resultDict = dict(url=url,status=status,length=length,time=ar.now())
            self.li.extend([resultDict])

    def run(self, calls=100, concurrent=25):
        """
        Runs load test.

        Default : 
            calls : int
                Number of calls in test run [default 100]
            
            concurrent : int
                Number of concurrent connections [default 25]
        """
        self.calls = calls
        self.concurrent = concurrent
        self.q = Queue(self.concurrent)
        t0 = time()

        # start concurrent threads
        for i in range(self.concurrent):

            # target is the callable object or task to be invoked by the run() method
            self.t = Thread(target=self._handleResults)

            # flag evey thread has
            self.t.daemon = True

            self.t.start()

        # make calls
        for url in self.urls:
            msg = 'running test of %s calls (%s concurrently) to %s ...' % (self.calls, self.concurrent, url)
            logging.info(msg);  print(msg)

            try:
                for _ in range(self.calls):
                    self.q.put(url.strip())

            except KeyboardInterrupt:
                sys.exit(1)

        # wait for queue to finish
        while not self.q.empty():
            sleep(1)

        # results list to dataframe
        keepTrying = True
        while keepTrying:
            try:
                self.df = pd.DataFrame(self.li)
                keepTrying = False
            except Exception as e:
                print(e)
                sleep(1)

        msg = 'completed %s calls in %.2f seconds (%.2f calls/sec)' % (len(self.li), time()-t0, len(self.li)/(time()-t0) )
        logging.info(msg);  print(msg)

    def _plotGroupby(self, param, kind, marker, figsize):

        if len(self.df.columns) > 0:

            if 'pd' not in self.df.columns:
                self.df['pd'] = self.df.time.apply(lambda x: x.format('hh:mm:ss'))

            keepTrying = True

            while keepTrying:
                try:
                    tmp = self.df.groupby(param).count().time
                    if marker != '':
                        plot = tmp.plot(kind=kind,figsize=figsize,marker=marker)
                    else: 
                        plot = tmp.plot(kind=kind,figsize=figsize)                 
                    fig = plot.get_figure()
                    fig.savefig('loadtest_group_%s.png' % param)

                    if(param == 'pd'):
                        plt.xlabel("Time in HH:MM:SS")
                        plt.ylabel("Count of HTTP Responses")

                    else:
                        plt.xlabel("Status code response")
                        plt.ylabel("Count of HTTP Responses")
                        
                    plt.show()
                    keepTrying = False

                except Exception as e:
                    print(e)
                    sleep(1)
        
    def plotGroup(self, plot):
        """
        Plot results of SimpleLoadTest run.
        
        Params
        -----
            plot : str 
                'rate' : calls per second
                'code' : count of http request response codes  
        """
        if plot == 'rate':
            param,kind,marker,figsize = 'pd','line', 'o', (10,5)
        elif plot == 'code':
            param,kind,marker,figsize = 'status','bar', '',(6,4)
        else:
            raise ValueError('Specificy valid plot type.')
        self._plotGroupby(param,kind,marker,figsize)

# FINAL RUNNER FUNCTION

if __name__=='__main__':
    from argparse import ArgumentParser
    par = ArgumentParser(description="Load Tester")
    par.add_argument('url', type=str, help="url to test") 
    par.add_argument('--calls', type=int, default=100, help="number of calls to url [default 100]")
    par.add_argument('--concurrent', type=int, default=25, help="number of concurrent calls [default 25]")
    args = par.parse_args()
    urls = args.url.split(',')

    # instantiate test object and run test
    test = LoadTest(urls)
    test.run(args.calls, args.concurrent)

    # plotting function for rate and code
    test.plotGroup('rate')
    test.plotGroup('code')
    
    # function for csv dataframe
    test.df.to_csv('loadtestresponses.csv',index=False)
