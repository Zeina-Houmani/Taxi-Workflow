import requests
import sys
from datetime import datetime
import pytz
from argparse import ArgumentParser
from kubernetes import client, config
from pprint import pprint
import json
from collections import OrderedDict

POD_IP = ''
APP_PORT = 0
URI = []
PROMETHEUS_URL = ''
QUERY_API = '/api/v1/query'
TIME = ''
counter_dict = OrderedDict()
dict_to_file = OrderedDict()
dict_to_file['Microservices'] = []


def get_metrics(START_TIME, END_TIME):
	global POD_IP
	global APP_PORT
	global URI
	global counter_dict
	global dict_to_file

	config.load_kube_config()
	v1 = client.CoreV1Api()
	services_list= v1.list_namespaced_service("default")
	for service in services_list.items:
		APP_NAME = service.metadata.name
		APP_PORT = service.spec.ports[0].port
		key = service.metadata.labels.keys()[0]
		value = service.metadata.labels.values()[0]
		URI= value.split("-")
		if key != "component":
			print("collect metrics from *" + URI[0] + "* instances ... ")
			label = key + "=" + value
			service_counter =0
			pod_list = v1.list_namespaced_pod("default", label_selector=label)
			for pod in pod_list.items:
				POD_IP = pod.status.pod_ip
				#print("%s\t%s" % (pod.metadata.name, pod.status.pod_ip))
				result = get_Requests_counter()
				if result != "None":
					service_counter += int(result)
			counter_dict[APP_NAME] = service_counter
	dict_to_file['Received requests'].append(counter_dict)
	dict_to_file["Start time"] = START_TIME
	dict_to_file["End time"] = END_TIME
	get_metrics_app()
	with open('result.json', 'w') as fp:
        	 json.dump(dict_to_file, fp,  indent=4)



def get_metrics_app():
	global POD_IP
	global APP_PORT
	global URI
	metrics_app = {}
	app_counter =0
	config.load_kube_config()
	core_api = client.CoreV1Api()
	apps_api = client.AppsV1Api()
	namespace_name = "default"
        apps_list= core_api.list_namespaced_service(namespace_name)
	for app in apps_list.items:
		APP_NAME = app.metadata.name
		metrics_app["name"] = APP_NAME
		key = app.spec.selector.keys()[0]
		value = app.spec.selector.values()[0]
		label = key + "=" + value
		deployment = apps_api.list_namespaced_deployment(namespace_name, label_selector=label)
		metrics_app["replicas"] =  deployment.items[0].spec.replicas
		containers_list = deployment.items[0].spec.template.spec.containers
		total_limit_cpu = 0
		total_limit_mem = 0
		total_limit_disk = 0
		for container in containers_list:
			limits = container.resources.limits
			print container
			print limits
#			if not limits:
			total_limit_cpu = total_limit_cpu + int(limits["cpu"][:-1])
			total_limit_mem = total_limit_mem + int(limits["memory"][:-2])
			total_limit_disk = total_limit_disk + int(limits["ephemeral-storage"][:-2])	
		metrics_app["Limit CPU"] = str(total_limit_cpu) + "m"
		metrics_app["Limit RAM"] = str(total_limit_mem) + "Mi"
		metrics_app["Limit Storage"] = str(total_limit_disk) + "Gi"
        dict_to_file['Microservices'].append(metrics_app)
	#print dict_to_file


	
	
	
def get_static_metrics():
	global POD_IP
	global APP_PORT
	global URI
	app_counter =0
	config.load_kube_config()
	core_api = client.CoreV1Api()
	apps_api = client.AppsV1Api()
	namespace_name = "default"
        apps_list= core_api.list_namespaced_service(namespace_name)
	for app in apps_list.items:
		APP_NAME = app.metadata.name
		if APP_NAME != "kubernetes":
			metrics_app =  OrderedDict()
			metrics_app["name"] = APP_NAME
			key = app.spec.selector.keys()[0]
			value = app.spec.selector.values()[0]
			label = key + "=" + value
			pod_list = core_api.list_namespaced_pod(namespace_name, label_selector=label)
			metrics_app["replicas"] =  len(pod_list.items)
			containers_list = pod_list.items[0].spec.containers
			total_limit_cpu = 0
			total_limit_mem = 0
			total_limit_disk = 0
			for container in containers_list:
				limits = container.resources.limits
#				if not limits:
				total_limit_cpu = total_limit_cpu + int(limits["cpu"][:-1])
				total_limit_mem = total_limit_mem + int(limits["memory"][:-2])
				total_limit_disk = total_limit_disk + int(limits["ephemeral-storage"][:-2])	
			metrics_app["Limit CPU"] = str(total_limit_cpu) + "m"
			metrics_app["Limit RAM"] = str(total_limit_mem) + "Mi"
			metrics_app["Limit Storage"] = str(total_limit_disk) + "Gi"
        		#dict_to_file['Microservices'].append(metrics_app)
			for pod in pod_list:
				metrics_replicas =  OrderedDict()
				pod_name = pod.metadata.name
				print pod_name
				metrics_replicas['CPU usage']= get_CPU_usage(pod_name,namespace_name)
				#metrics_replicas['Memory usage']= get_RAM_usage(pod_name,namespace_name)
				#metrics_replicas['Disk usage']= get_DISK_usage(pod_name,namespace_name)
				metrics_app['Replicas'].append(metrics_replicas)
			dict_to_file['Microservices'].append(metrics_app)
	with open('result.json', 'w') as fp:
        	 json.dump(dict_to_file, fp,  indent=4)

			


def get_prometheus_URL():
 	global PROMETHEUS_URL	
 	#Get Prometheus IP address and port from the platform
	config.load_kube_config()
	core_api = client.CoreV1Api()
	namespace_name = "istio-system"
	PROMETHEUS_IP=''
	PROMETHEUS_PORT=''
        apps_list= core_api.list_namespaced_service(namespace_name, label_selector="app=prometheus")
	app = apps_list.items[0]
	APP_NAME = app.metadata.name
	if APP_NAME != "prometheus":
		print "Can't get prometheus IP address"
		return False
	else:
		PROMETHEUS_IP = app.spec.cluster_ip
		PROMETHEUS_PORT = app.spec.ports[0].port		
 		PROMETHEUS_URL= "http://" + PROMETHEUS_IP + ":" + str(PROMETHEUS_PORT)
		return True

	

	
def get_time():
    global TIME
    tz_NY = pytz.timezone('America/New_York')
    datetime_NY = datetime.now(tz_NY)
    TIME = str(datetime_NY.strftime("%Y-%m-%dT%H:%M:%SZ"))

	
def get_utc_date():
  global TIME
  dt = datetime.utcnow()
  TIME= dt.strftime("%Y-%m-%dT%H:%M:%SZ")
	

	
def get_CPU_usage(POD_NAME, NAMESPACE):
  QUERY =  'sum(rate(container_cpu_usage_seconds_total{pod_name!="", image!="", pod_name=~"' + POD_NAME + '.*", namespace=~"' + NAMESPACE + '"}[5m])) by (pod_name)'
  response = requests.get(PROMETHEUS_URL + QUERY_API, params={'query': QUERY, 'time': TIME})
  status = response.json()['status']
  if status == "error":
        print(response.json())
	#sys.exit(2)
	return 0.0
  else:
	print("It's a success")
  results = response.json()['data']['result']	
  print results
  print "***********"
  print results['value']
  #return "%.2f" % float(results['value'])
			
	
	
def get_RAM_usage(POD_NAME, NAMESPACE):
  QUERY =  'sum(rate(container_memory_usage_bytes{pod_name!="", image!="", pod_name=~"' + POD_NAME + '.*", namespace=~"' + NAMESPACE + '"}[5m])) by (pod_name)'
  response = requests.get(PROMETHEUS_URL + QUERY_API, params={'query': QUERY, 'time': TIME})
  status = response.json()['status']
  if status == "error":
        print(response.json())
	#sys.exit(2)
	return 0.0
  else:
	print("It's a success")
  results = response.json()['data']['result']	
  print results
  print "***********"
  print results['value']
  return "%.2f" % float(results['value'])
			
	
	
def get_DISK_usage(POD_NAME, NAMESPACE):
  QUERY =  'sum(rate(container_cpu_usage_seconds_total{pod_name!="", image!="", pod_name=~"' + POD_NAME + '.*", namespace=~"' + NAMESPACE + '"}[5m])) by (pod_name)'
  response = requests.get(PROMETHEUS_URL + QUERY_API, params={'query': QUERY, 'time': TIME})
  status = response.json()['status']
  if status == "error":
        print(response.json())
	#sys.exit(2)
	return 0.0
  else:
	print("It's a success")
  results = response.json()['data']['result']			
  return "%.2f" % float(results['value'])
			
			
if __name__ == "__main__":
 	#get_static_metrics()
	if get_prometheus_URL():
		print PROMETHEUS_URL
        get_utc_date():
	get_CPU_usage("billing", "default")
	
