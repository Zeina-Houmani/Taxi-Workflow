import csv
import requests
import sys
import logging
import time
import datetime
import copy
from argparse import ArgumentParser
import matplotlib.pyplot as plot
import matplotlib.colors
import collections
import matplotlib.legend
from matplotlib.ticker import AutoMinorLocator
import numpy as np

PROMETHEUS_URL = ''
QUERY_API = '/api/v1/query'
QUERY_RANGE_API = '/api/v1/query_range'
START = ''
END = ''
time_dict={}


def set_options():
    parser = ArgumentParser(description='Visualize the test results in matplotlib graphs')
    parser.add_argument("--ip", "-i", required=True, help="IP address of the prometheus service in the platform")
    parser.add_argument("--start", "-s", required=True, help="Start timestamp")
    parser.add_argument("--end", "-e", required=True, help="End timestamp")
    args = parser.parse_args()
    return args


def handle_args():
  global PROMETHEUS_URL
  global START
  global END
  args = set_options()
  PROMETHEUS_URL= "http://" + args.ip + ":9090"
  START= int(args.start)
  END= int(args.end)


def get_dic_timestamps():
  global time_dict
  print START
  print END
  for t in range(START, END+1):
 	time_dict[t] = 0.000
  time_dict = collections.OrderedDict(sorted(time_dict.items()))
  return time_dict


def convert_timestamps(results):
   time_new_dict = {}
   total_seconds=len(results)
   for x in range(total_seconds):
	time_new_dict[x] = results.values()[x]
   time_new_dict = collections.OrderedDict(sorted(time_new_dict.items()))
   return time_new_dict



def Convert_to_float(results):
  for result in results:
        for value in result['values']:
		value[1] = float('{0:.3f}'.format(float(value[1])))
  return results



def get_aggregated_results(time_dict, results):
  time_dict_copy = copy.deepcopy(time_dict)
  time_dict_copy2 = copy.deepcopy(time_dict)
  for result in results:
	for value in result['values']:
		if value[1] != 0.000 and value[1] != 'NaN':
			if float(time_dict_copy2[value[0]]) == 0.000:
				time_dict_copy2[value[0]] = float(value[1])
				time_dict_copy[value[0]] = 1
			else:
				time_dict_copy2[value[0]] = float(time_dict_copy2[value[0]]) + float(value[1])
				time_dict_copy[value[0]] += 1
  for key in time_dict_copy2:
	  if time_dict_copy2[key] != 0.000:
	  	time_dict_copy2[key] = float(time_dict_copy2[key])  / float(time_dict_copy[key])
		time_dict_copy2[key] = float("{0:.3f}".format(time_dict_copy2[key]))
  return time_dict_copy2




def create_matplotlib_file(title, ylabel, xlabel, results):
  now = datetime.datetime.now()
  filename= "matplotlib_" + now.strftime("%Y_%m_%d_%H-%M_%p") + ".png"
  f= open(filename,"w+")
  f.write("import matplotlib.pyplot as plot\nfrom matplotlib.ticker import AutoMinorLocator\nimport matplotlib.colors\nimport matplotlib.legend\n\n")
  f.write("ax = plot.subplot(1, 1, 1)\nplot.tick_params(axis=\"x\", pad=8)\nplot.ylabel(\"Response Time in seconds\")\nplot.xlabel(\"Time in seconds\")\n")
  f.write("ax.yaxis.set_minor_locator(AutoMinorLocator(10))\nplot.tick_params(axis=\"y\", pad=5)\n")
  nb_of_results = len(results)
  timestamps = results[0].keys()
  values = results[0].values()
  f.write("timestamps = %s\n" % (timestamps))
  f.write("values = %s\n" % (values))
  f.write("p1 = plot.plot(timestamps,values, linewidth=2)\nax.set_ylim(bottom=0)\nax.set_xlim(xmin=0)\n\n")
  f.write("ax2 = plot.twinx()\n")
  f.write("plot.ylabel(\"Percentage of accepted requests\", color=\"r\")\n")
  f.write("ax2.yaxis.set_minor_locator(AutoMinorLocator(10))\n")
  f.write("plot.tick_params(axis=\"y\", labelcolor=\"r\", pad=5)\nplot.ylim(0, 105)\n")
  values = results[1].values()
  f.write("\ntimestamps = %s\n" % (timestamps))
  f.write("values = %s\n" % (values))
  f.write("p2 = plot.plot(timestamps,values,  \"r-\", linewidth=2)\n")
  f.write("plot.title(\"%s\")\n" % (title))
  f.write("plot.grid(True , \"r-\", linewidth=0.1)\n")
  f.write("plot.savefig(\"%s\", dpi=120, format=\"png\")\n" % (filename))
  f.write("plot.show()\n")
  f.close()



def create_graph(title, ylabel, xlabel, results):
  now = datetime.datetime.now()
  filename= "matplotlib_" + now.strftime("%Y_%m_%d_%H-%M_%p" + ".png")
  nb_of_results = len(results)
  ax = plot.subplot(1, 1, 1)
  plot.tick_params(axis="x", pad=8)
  plot.ylabel("Response Time in seconds")
  plot.xlabel("Time in seconds")
  ax.yaxis.set_minor_locator(AutoMinorLocator(10))
  plot.tick_params(axis="y", pad=5)
  timestamps = results[0].keys()
  values = results[0].values()
  p1 = plot.plot(timestamps,values, linewidth=2)
  ax.set_ylim(bottom=0)
  ax.set_xlim(xmin=0)

  ax2 = plot.twinx()
  plot.ylabel("Percentage of accepted requests", color="r")
  ax2.yaxis.set_minor_locator(AutoMinorLocator(10))
  plot.tick_params(axis="y", labelcolor="r", pad=5)
  plot.ylim(0, 105)
  values = results[1].values()
  p2 = plot.plot(timestamps,values,  "r-", linewidth=2 )
  plot.title(title)
  plot.grid(True , "r-", linewidth=0.1)
  plot.savefig(filename, dpi=120, format="png")
  plot.ioff()



def average_request_duration():
  response = requests.get(PROMETHEUS_URL + QUERY_RANGE_API, params={'query': 'rate(istio_request_duration_seconds_sum{destination_app= "trip", \
  			source_app="istio-ingressgateway"}[10s:1s]) /rate(istio_request_duration_seconds_count{destination_app= "trip", \
			source_app="istio-ingressgateway"}[10s:1s])', 'start': START, 'end': END, 'step': '1'})

  status = response.json()['status']
  if status == "error":
        print(response.json())
	sys.exit(2)
  else:
	print("It's a success")
  results = response.json()['data']['result']
  get_dic_timestamps()
  agg_results = get_aggregated_results(time_dict, results)
  for k,v in agg_results.items():
                if v != 0.0:
			value=v
			break
  replace(agg_results, value)
  agg_results =  convert_timestamps(agg_results)
  return agg_results



def replace(dict, value):
	for k,v in dict.items():
   		if v == 0.0:
                   dict[k] = value;



def get_accepted_requests():
  response = requests.get(PROMETHEUS_URL + QUERY_RANGE_API, params={'query': '(sum(istio_requests_total{request_protocol="http", response_code="200", \
			source_app="istio-ingressgateway"}) / sum(istio_requests_total{request_protocol="http", response_code=~"200|503|500|404", \
			source_app="istio-ingressgateway"})) *100', 'start': START, 'end': END, 'step': '1'})
  status = response.json()['status']
  if status == "error":
        print(response.json())
        sys.exit(2)
  else:
        print("It's a success")
  results = response.json()['data']['result']
  results = Convert_to_float(results)
  dict_res = dict(results[0]['values'])

  agg_results = get_aggregated_results(time_dict, results)
  replace(agg_results, 100.0)
  agg_results =  convert_timestamps(agg_results)
  return agg_results


def save_csv(rq_duration):
	csv_columns = ['Time', 'latency']
	try:
	    with open("results.csv", 'w') as csvfile:
	        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
	        writer.writeheader()
        	for key in rq_duration.keys():
		    csvfile.write("%s,%s\n"%(key,rq_duration[key]))
	except IOError:
	    print("I/O error")

def main():
 handle_args()

 list = []
 request_duration = average_request_duration()
 save_csv(request_duration)
# accepted_requests = get_accepted_requests()
# list.append(request_duration)
# list.append(accepted_requests)
# create_matplotlib_file("Variation of response time and percentage of accepted requests", "Number of requests", "", list)
 #create_graph("Variation of response time and percentage of accepted requests", "Number of requests", "", list)


if __name__ == "__main__":
     main()
