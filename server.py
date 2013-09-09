# Copyright 2013 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Web app for mongo-perf"""

import sys
import json
import pymongo
import pprint
import time 
from bottle import *
import logging as logr
import logging.handlers
from datetime import datetime
from collections import defaultdict

MONGO_PERF_HOST = "localhost"
MONGO_PERF_PORT = 27017
MP_DB_NAME = "bench_results"
db = pymongo.Connection(host=MONGO_PERF_HOST, 
                         port=MONGO_PERF_PORT)[MP_DB_NAME]


@route('/static/:filename#.*#')
def send_static(filename):
    return static_file(filename, root='./static')


@route("/host")
def host_page():
    result = {}
    result['timestamp'] = request.GET.get('timestamp', '')
    result['label'] = request.GET.get('label', '')
    result['version'] = request.GET.get('version', '')
    host = db.host.find_one({"build_info.version": result['version'],
                                "label": result['label'],
                                "run_ts": result['timestamp']
                            })
    return template('host.tpl', host=host)


#Note: refactored form simply gets all the results and returns them as a list
def raw_data(versions, labels, multidb, dates, platforms, start, end, limit):
    """ Pulls and aggregates raw data from database matching query parameters
        :Parameters:
        - ``"versions"``: specific mongod versions we want to view tests for
        - ``"labels"``: test host label
        - ``"multidb"``: single db or multi db
        - ``"dates"``: specific dates for tests to be viewed
        - ``"platforms"``: specific platforms we want to view tests for
        - ``"start"``: tests run from this date (used in range query)
        - ``"end"``: tests run before this date (used in range query)
        - ``"limit"``: # of tests to return
    """

    if start:
        start_query = {'run_ts': {'$gte': start}}
    else:
        start_query = {}

    if end:
        end_query = {'run_ts': {'$lte': end}}
    else:
        end_query = {}

    if limit:
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
    else:
        limit = 10

    if versions:
        if versions.startswith('/') and versions.endswith('/'):
            version_query = {'version': {'$regex':
                                         versions[1:-1], '$options': 'i'}}
        else:
            version_query = {'version': {'$in': versions.split(" ")}}
    else:
        version_query = {}

    if platforms:
        if platforms.startswith('/') and platforms.endswith('/'):
            platforms_query = {'platform': {'$regex':
                                            platforms[1:-1], '$options': 'i'}}
        else:
            platforms_query = {'platform': {'$in': platforms.split(" ")}}
    else:
        platforms_query = {}

    #this gets broken with timestamp, TODO fix
    if dates:
        if dates.startswith('/') and dates.endswith('/'):
            date_query = {'run_ts': {'$regex':
                                       dates[1:-1], '$options': 'i'}}
        else:
            date_query = {'run_ts': {'$in': dates.split(" ")}}
    else:
        date_query = {}

    if labels:
        if labels.startswith('/') and labels.endswith('/'):
            label_query = {'label': {'$regex':
                                     labels[1:-1], '$options': 'i'}}
        else:
            label_query = {'label': {'$in': labels.split(" ")}}
    else:
        label_query = {}

    query ={"$and": [version_query, label_query, platforms_query, date_query, start_query, end_query]}
    pprint.pprint(query)
    cursor = db.raw.find(query)\
        .sort([ ('run_ts', pymongo.DESCENDING), 
                ('platform', pymongo.DESCENDING)])\
        .limit(limit)

    return list(cursor)

"""
    for index in xrange(0, result_size):
        entry = cursor[index]
        if multidb in entry:
            results = entry[multidb]

            for result in results:
                row = dict(commit=entry['commit'],
                           platform=entry['platform'],
                           version=entry['version'],
                           label=entry['label'],
                           timestamp=entry['run_ts'])
                #for (n, res) in result['results'].iteritems():
                #    row[n] = res
                row[
                aggregate[result['name']].append(row)

    aggregate = sorted(aggregate.iteritems(), key=lambda (k, v): k)
    out = []

    for item in aggregate:
        out.append({'name': item[0], 'results': item[1]})

    return out
"""

"""
#TODO this is bad, need to refactor results_page method
def get_new_flot_data():
    #TODO format description is not right here...
    #format needed ['[{data: [[ts, ops/sec], ...], label: "blah"}]',...]
    #each string is for a test
    #each ele in string list is for a different label
    datacol = db['raw']
    labeldict = defaultdict(list)
    for ele in datacol.find():
        ts = ele['run_ts']
        label = ele['label']
        #need to figure out whole single vs multidb thing...
        #for now we just assume multidb = 0...need to work on this
        multidb = ele['multidb']
        for testResult in multidb:
            #store data appropriately
        """
        

@route("/results")
def results_page():
    """Handler for results page
    """
    # specific platforms we want to view tests for
    platforms = ' '.join(request.GET.getall('platforms'))
    # specific mongod versions we want to view tests for
    versions = ' '.join(request.GET.getall('versions'))
    # specific dates for tests to be viewed
    dates = ' '.join(request.GET.getall('dates'))
    # special data structure for recent tests
    home = ' '.join(request.GET.getall('home'))
    # test host label
    labels = ' '.join(request.GET.getall('labels'))
    # test metric of interest
    metric = request.GET.get('metric', 'ops_per_sec')
    # # of tests to return
    limit = request.GET.get('limit')
    # tests run from this date (used in range query)
    start = request.GET.get('start')
    # tests run before this date (used in range query)
    end = request.GET.get('end')
    # single db or multi db
    multidb = request.GET.get('multidb', '0')
    multidb = 'singledb' if multidb == '0' else 'multidb'

    # handler for home page to display recent tests
    # we need to query for each recent test separately and
    # then merge the results for subsequent display
    if home:
        results = []
        try:
            from ast import literal_eval
            for platform in literal_eval(home):
                result = literal_eval(json.dumps(platform))
                for attrib in result:
                    result[attrib] = '/' + result[attrib] + '/'
                tmp = raw_data(result['version'], result['label'], multidb,
                               result['run_ts'], result['platform'], None, None, limit)
                for result in tmp:
                    results.append(result)
            results = merge(results)
        except BaseException, e:
            print e
    else:
        results = raw_data(versions, labels, multidb, dates,
                           platforms, start, end, limit)

    pprint.pprint(results)
    #format of results:
    threads = set()
    flot_results = []
    #from this section we need to generate the flot results and the threads set
    new_flot_results = []
    newer_flot_results = []
    target_keys = ['8', '12', '16']
    dates = set()
    #keys are thread nums, vals are the data list
    for outer_result in results:
        flot_dict = {}
        newer_flot_dict = {}
        flot_list = []
        result_section = []
        for result in outer_result['results']:
            sum = 0
            for key in result.keys():
                if key.isdigit() and key in target_keys:
                    sum += result[key]['ops_per_sec']
                    #this is a thread num
                    #ensure it is in dict
                    if key not in flot_dict.keys():
                        flot_dict[key] = []

                    date = time.mktime(datetime.strptime(result['date'], '%Y-%m-%d').timetuple()) * 1000
                    dates.add(date)
                    datapoint = [date, result[key]['ops_per_sec']]
                    flot_dict[key].append(datapoint)

            avg = sum / len(target_keys)
            date = time.mktime(datetime.strptime(result['date'], '%Y-%m-%d').timetuple()) * 1000
            datapoint = [date, avg]
            flot_list.append(datapoint)

        for key in flot_dict.keys():
            tmpele = {'data': flot_dict[key], 'label': key}
            result_section.append(tmpele)
        
        tmptwo = { 'data': flot_list, 'label': 'avg'}

        new_flot_results.append(json.dumps(result_section))
        newer_flot_results.append(json.dumps([tmptwo]))
            
    pprint.pprint(newer_flot_results)
    print "that was newer flot results"
    print "******************************************"
    

    """
    pprint.pprint(flot_dict)
    print "results length: " + str(len(results))
    dateset = set()
    #now take flot_dict, convert it into form that we need
    for key in flot_dict.keys():
        tmpele = {'data': flot_dict[key], 'label': key}
        new_flot_results.append(tmpele)
    """

    """
    for outer_result in results:
        out = []
        for i, result in enumerate(outer_result['results']):
            out.append({'label': " - ".join((result['label'], result['version'], 
                    str(result['timestamp']))), 'data': sorted([int(k), v[metric]]
                        for (k, v) in result.iteritems() if k.isdigit())
                        })
            threads.update(int(k) for k in result if k.isdigit())
        flot_results.append(json.dumps(out))
    """

    """
    pprint.pprint(new_flot_results)
    print "new_flot_results length: " + str(len(new_flot_results))
    pprint.pprint(flot_results)
    print "flot_results length: " + str(len(flot_results))
    """
    return template('results.tpl', results=results, flot_results=newer_flot_results,
                     request=request, threads=sorted(threads), datelist=sorted(dates))

@route("/results2")
def results2():
    # specific platforms we want to view tests for
    platforms = ' '.join(request.GET.getall('platforms'))
    # specific mongod versions we want to view tests for
    versions = ' '.join(request.GET.getall('versions'))
    # specific dates for tests to be viewed
    dates = ' '.join(request.GET.getall('dates'))
    # special data structure for recent tests
    home = ' '.join(request.GET.getall('home'))
    # test host label
    labels = ' '.join(request.GET.getall('labels'))
    # test metric of interest
    metric = request.GET.get('metric', 'ops_per_sec')
    # # of tests to return
    limit = request.GET.get('limit')
    # tests run from this date (used in range query)
    start = request.GET.get('start')
    # tests run before this date (used in range query)
    end = request.GET.get('end')
    # single db or multi db
    multidb = request.GET.get('multidb', '0')
    multidb = 'singledb' if multidb == '0' else 'multidb'

    #TODO "home" handling ... do we want to do that at all?
    
    #first we get the raw data
    data = raw_data(versions, labels, multidb, dates,
                    platforms, start, end, limit)

    #generate the "results" data
    #first we need to generate a list of documents that have the "name field"
    #TODO pull this out into functions later
    aggregate = defaultdict(list)
    for i in range(len(data)):
        entry = data[i]
        if "multidb" not in entry:
            print "CRAP BAD" #TODO handle better
        else:
            results = entry['multidb']
            for result in results:
                aggele = { 'commit': entry['commit'], 
                           'platform': entry['platform'],
                           'version': entry['version'],
                           'run_ts': entry['run_ts'],
                           'label': entry['label'],
                           'result': result }
                aggregate[result['name']].append(aggele)

    #TODO what exactly is this doing?
    #turns into a sorted list of (testname, [aggele,...]
    aggregate = sorted(aggregate.iteritems(), key=lambda (k, v): k)

    results = []
    for item in aggregate:
        results.append({'name': item[0], 'results': item[1]})

    pprint.pprint(results)
    #generate the "flot_results" data
    flot_results = []
    for test in results:
        testlist = []
        for run in test['results']:
            testdoc = {'label': run['run_ts']}
            #TODO working here....

    #return template('results.tpl', results=results, flot_results=newer_flot_results,
    #                 request=request, datelist=sorted(dates))
    return 'hello world'

def merge(results):
    """This takes separate results that have been pulled
        and aggregated - using the raw_data function, and
        reaggregates them in the same way raw_data does
    """
    aggregate = defaultdict(list)
    for result in results:
        row = dict(label=result['results'][0]['label'],
                   platform=result['results'][0]['platform'],
                   version=result['results'][0]['version'],
                   commit=result['results'][0]['commit'],
                   timestamp=result['results'][0]['run_ts'])
        for (n, res) in result['results'][0].iteritems():
            row[n] = res
        aggregate[result['name']].append(row)

    aggregate = sorted(aggregate.iteritems(), key=lambda (k, v): k)
    out = []

    for item in aggregate:
        out.append({'name': item[0], 'results': item[1]})

    return out


@route("/")
def main_page():
    """Handler for main page
    """
    platforms = db.raw.distinct("platform")
    versions = db.raw.distinct("version")
    labels = db.raw.distinct("label")
    platforms = filter(None, platforms)
    versions = filter(None, versions)
    labels = filter(None, labels)
    versions = sorted(versions, reverse=True)
    rows = None
    
    # restricted to benchmark tests for most recent MongoDB version
    if versions:
        cursor = db.raw.find({"version": versions[0]},
                             {"_id" : 0, "singledb" : 0, 
                             "multidb" : 0, "commit" : 0})\
            .limit(len(labels)).sort([('run_ts', pymongo.DESCENDING)])
        rows = []

        for record in cursor:
            rows.append(record)

        rows = sorted([dict(t) for t in set([tuple(d.items())
                       for d in rows])], key=lambda t:
                     (t['run_ts'], t['label']), reverse=True)

    return template('main.tpl', rows=rows, labels=labels,
                    versions=versions, platforms=platforms)

if __name__ == '__main__':
    do_reload = '--reload' in sys.argv
    run(host='0.0.0.0', server=AutoServer)
