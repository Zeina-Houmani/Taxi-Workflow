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


def replace(dict, value):
	for k,v in dict.items():
   		if v == 0.0:
                   dict[k] = value;


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
 request_duration_one = get_average_request_duration(file1)
 request_duration_two = get_average_request_duration(file2)
 list.append(request_duration_one)
 list.append(request_duration_two)
# create_matplotlib_file("Variation of response time and percentage of accepted requests", "Number of requests", "", list)
 create_graph("Variation of response time", "Number of requests", "", list)


if __name__ == "__main__":
     main()
