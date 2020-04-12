import requests
import sys
import os
from datetime import datetime
import pytz
from argparse import ArgumentParser
from kubernetes import client, config
from pprint import pprint
import json
from collections import OrderedDict

RESULT_FILE="result.json"
POD_IP = ''
APP_PORT = 0
URI = []
PROMETHEUS_URL = ''
QUERY_API = '/api/v1/query'
TIME = ''
counter_dict = OrderedDict()
dict_to_file = OrderedDict()
dict_to_file['Microservices'] = []


#apps_api = client.AppsV1Api()
#deployment = apps_api.list_namespaced_deployment(namespace_name, label_selector=label)
#metrics_app["replicas"] =  deployment.items[0].spec.replicas
#containers_list = deployment.items[0].spec.template.spec.containers	
	
	
def get_query_result(QUERY):
    response = requests.get(PROMETHEUS_URL + QUERY_API, params={'query': QUERY, 'time': TIME})
    status = response.json()['status']
    if status == "error":
        print(response.json())
	return 'NaN'
    results = response.json()['data']['result']
    if not results:
	value = 'NaN'
    return results


#Collect general metric about server	
def get_server_metrics():
    metrics_server =  OrderedDict()
    metrics_capacity =  OrderedDict()
    metrics_server["Servers"] = []

    QUERY_nodes = 'node_uname_info'  
    nodes = get_query_result(QUERY_nodes)
    total_nodes = len(nodes)
    counter = 1
    for node in nodes:
	metrics_node = OrderedDict()
	NODE_NAME= node.get("metric").get("nodename")
	metrics_node['instance'] = str(counter) + "/" + str(total_nodes)
	metrics_node["name"] = NODE_NAME
	
	QUERY_memory =  'kube_node_status_capacity_memory_bytes{node=~"' + NODE_NAME + '"}'
	MEMORY_CAPACITY = get_query_result(QUERY_memory)[0].get('value')[1]
	metrics_node['memory capacity'] = humanbytes(MEMORY_CAPACITY)
	
	QUERY_cpu =  'kube_node_status_capacity_cpu_cores{node=~"' + NODE_NAME + '"}'
	CPU_CAPACITY = get_query_result(QUERY_cpu)[0].get('value')[1]
	metrics_node['cpu capacity'] = CPU_CAPACITY
	
	#QUERY_disk =  'node_filesystem_size_bytes{fstype="ext4", device!="rootfs"}'
	QUERY_disk = 'sum(container_fs_limit_bytes{device=~"^/dev/[sv]d[a-z][1-9]$",id="/", kubernetes_io_hostname=~"' + NODE_NAME + '"})'
	DISK_CAPACITY = get_query_result(QUERY_disk)[0].get('value')[1]
	metrics_node['disk capacity'] = humanbytes(DISK_CAPACITY)
	
	metrics_node['resource usage'] = []
	usage_metrics = OrderedDict() 
	
	QUERY_USAGE_memory = 'sum(container_memory_working_set_bytes{id="/",kubernetes_io_hostname=~"' +NODE_NAME + '"})'
	MEMORY_USAGE = get_query_result(QUERY_USAGE_memory)[0].get('value')[1]
	QUERY_USAGE_memory_percentage = str ("%.2f" % float(( float(MEMORY_USAGE) / float(MEMORY_CAPACITY)) * 100) ) + "%"
	usage_metrics['Memory used'] =  str(humanbytes(MEMORY_USAGE))  + " (" + str(QUERY_USAGE_memory_percentage) + ")"
	
	
	QUERY_USAGE_cpu = 'sum(rate(container_cpu_usage_seconds_total{id="/",kubernetes_io_hostname=~"' + NODE_NAME + '"}[5m]))'
	CPU_USAGE = "%.2f" % float(get_query_result(QUERY_USAGE_cpu)[0].get('value')[1])
	QUERY_USAGE_cpu_percentage = str ("%.2f" % float(( float(CPU_USAGE) / float(CPU_CAPACITY)) * 100) ) + "%"
	usage_metrics['cpu used'] = str (CPU_USAGE) + " (" + str(QUERY_USAGE_cpu_percentage) + ")"
	
	
	QUERY_USAGE_disk =  'sum(container_fs_usage_bytes{device=~"^/dev/sda.$",id="/",kubernetes_io_hostname=~"' + NODE_NAME + '"})'
	DISK_USAGE = get_query_result(QUERY_USAGE_disk)[0].get('value')[1]
	QUERY_USAGE_disk_percentage = str ("%.2f" % float(( float(DISK_USAGE) / float(DISK_CAPACITY)) * 100) ) + "%"
	usage_metrics['disk used'] =  str(humanbytes(DISK_USAGE))  + " (" + str(QUERY_USAGE_disk_percentage) + ")"
	
	metrics_node['resource usage'] .append(usage_metrics) 
	metrics_server["Servers"].append(metrics_node)
	counter = counter +1
    write_file( metrics_server)   



def write_file(DATA):
	if not os.path.isfile(RESULT_FILE):
		 with open(RESULT_FILE, 'w') as fp:
        		 json.dump(DATA, fp,  indent=4)
	else:
		 with open(RESULT_FILE) as fp:
			feeds = json.load(fp , object_pairs_hook=OrderedDict)
		 feeds.update(DATA)
        	 with open(RESULT_FILE, 'w') as fp:
        		 json.dump(feeds, fp,  indent=4)
		

def get_service_metrics():
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
			replicas_count = len(pod_list.items)
			metrics_app["replicas set"] = replicas_count
			containers_list = pod_list.items[0].spec.containers
			total_limit_cpu = 0
			total_limit_mem = 0
			total_limit_disk = 0
			for container in containers_list:
				limits = container.resources.limits
				total_limit_cpu = total_limit_cpu + int(limits["cpu"][:-1])
				total_limit_mem = total_limit_mem + int(limits["memory"][:-2])
				total_limit_disk = total_limit_disk + int(limits["ephemeral-storage"][:-2])	
			metrics_app["limit CPU"] = total_limit_cpu / 1000
			metrics_app["limit RAM"] = humanbytes(total_limit_mem * 1024 * 1024)
			metrics_app["limit Storage"] = humanbytes(total_limit_disk * 1024 * 1024 * 1024 ) 
        		metrics_app['replicas'] = []
			counter = 1
			for pod in pod_list.items:
				dynamic =  OrderedDict()
				pod_name = pod.metadata.name
				dynamic['instance'] = str(counter) + "/" + str(replicas_count)
				counter = counter + 1
				dynamic['server'] = pod.spec.node_name
			
	
				QUERY_USAGE_cpu =  'sum(rate(container_cpu_usage_seconds_total{pod_name!="", image!="", pod_name=~"' + pod_name + '.*", namespace=~"' + namespace_name + '"}[5m])) by (pod_name)'
				CPU_USAGE = get_query_result(QUERY_USAGE_cpu)[0].get('value')[1]
				QUERY_USAGE_cpu_percentage = (float(CPU_USAGE) / (float (total_limit_cpu)/ 1000))*100
			        dynamic['CPU usage'] =  str ("%.2f" % float(CPU_USAGE)) + " (" + str(  "%.2f" % QUERY_USAGE_cpu_percentage) + "%)"
				
				
		   		QUERY_USAGE_memory ='sum(container_memory_working_set_bytes{pod_name!="", image!="", pod_name=~"' + pod_name + '.*", namespace=~"' + namespace_name + '"}) by (pod_name)' 
				MEMORY_USAGE = get_query_result(QUERY_USAGE_memory)[0].get('value')[1]
			        QUERY_USAGE_memory_percentage = "%.2f" % float(( float(MEMORY_USAGE) / float(total_limit_mem * 1024 * 1024 )) * 100)
				dynamic['RAM usage'] =  str(humanbytes(MEMORY_USAGE))  + " (" + str(QUERY_USAGE_memory_percentage) + "%)"
				
					
				QUERY_USAGE_disk ='sum(container_fs_usage_bytes{pod_name!="", image!="", pod_name=~"' + pod_name + '.*", namespace=~"' + namespace_name + '"}) by (pod_name)'
				DISK_USAGE = get_query_result(QUERY_USAGE_disk)[0].get('value')[1]
				QUERY_USAGE_disk_percentage = "%.2f" % float(( float(DISK_USAGE) / float(total_limit_disk * 1024 * 1024 * 1024)) * 100) 
				dynamic['Disk usage'] = str(humanbytes(DISK_USAGE))  + " (" + str(QUERY_USAGE_disk_percentage) + "%)"
				
				#Network usage
				network =  OrderedDict()
				network = get_replicas_network_usage(pod_name)
				dynamic['network I/O'].append(network)
				
				metrics_app['replicas'].append(dynamic)
			dict_to_file['Microservices'].append(metrics_app)
	write_file(dict_to_file)

	
	
def get_replicas_network_usage(POD_NAME):
	network_usage =  OrderedDict()
	QUERY_RECEIVE = 'rate (container_network_receive_bytes_total{image!="", pod_name="' + POD_NAME + '"}[5m])'
	NETWORK_RECEIVE = "%.2f" % float(get_query_result(QUERY_RECEIVE)[0].get('value')[1])
	network_usage['received bytes'] = humanbytes(NETWORK_RECEIVE)
	
	QUERY_TRANSMIT = 'rate (container_network_transmit_bytes_total{image!="", pod_name="' + POD_NAME + '"}[5m])'
	NETWORK_TRANSMIT = "%.2f" % float(get_query_result(QUERY_TRANSMIT)[0].get('value')[1])
	network_usage['sent bytes'] = humanbytes(NETWORK_TRANSMIT)
	return network_usage
	
	
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

	
def get_utc_date():
    global TIME
    dt = datetime.utcnow()
    TIME= dt.strftime("%Y-%m-%dT%H:%M:%SZ")
	

	
def humanbytes(B):
   'Return the given bytes as a human friendly KB, MB, GB, or TB string'
   B = float(B)
   KB = float(1024)
   MB = float(KB ** 2) # 1,048,576
   GB = float(KB ** 3) # 1,073,741,824
   TB = float(KB ** 4) # 1,099,511,627,776
   if B < KB:
      return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
   elif KB <= B < MB:
      return '{0:.2f} KB'.format(B/KB)
   elif MB <= B < GB:
      return '{0:.2f} MB'.format(B/MB)
   elif GB <= B < TB:
      return '{0:.2f} GB'.format(B/GB)
   elif TB <= B:
      return '{0:.2f} TB'.format(B/TB)

			
if __name__ == "__main__":
	if get_prometheus_URL():
		print PROMETHEUS_URL
        get_utc_date()
	
	get_server_metrics()
	
	get_service_metrics()
