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

RESULT_FILE="cluster_state.json"
POD_IP = ''
APP_PORT = 0
URI = []
PROMETHEUS_URL = ''
QUERY_API = '/api/v1/query'
TIME = ''
counter_dict = OrderedDict()
dict_to_file = OrderedDict()
dict_to_file['Microservices'] = []
	
	
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


def get_cluster_metrics():
    cluster_state =  OrderedDict()
    cluster_state["Cluster"] = []
    cluster_state["Cluster"].append(get_cluster_state())

    cluster_state.update(get_server_metrics())
    cluster_state.update(get_service_metrics())
    write_file(cluster_state) 
	
	
	
#Collect metrics about the cluster nodes	
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
	
	#memory usage 
	QUERY_USAGE_memory = 'sum(container_memory_working_set_bytes{id="/",kubernetes_io_hostname=~"' +NODE_NAME + '"})'
	usage_metrics['RAM usage'] = get_byte_usage(QUERY_USAGE_memory, MEMORY_CAPACITY)
	
	#cpu usage 
	QUERY_USAGE_cpu = 'sum(rate(container_cpu_usage_seconds_total{id="/",kubernetes_io_hostname=~"' + NODE_NAME + '"}[5m]))'			
	usage_metrics['CPU usage'] =get_cpu_usage(QUERY_USAGE_cpu, CPU_CAPACITY)
	
	#disk usage 
	QUERY_USAGE_disk =  'sum(container_fs_usage_bytes{device=~"^/dev/[sv]d[a-z][1-9]$",id="/",kubernetes_io_hostname=~"' + NODE_NAME + '"})'
	usage_metrics['disk usage'] = get_byte_usage(QUERY_USAGE_disk, DISK_CAPACITY)
	
	#Network usage
	network =  OrderedDict()
	QUERY_RECEIVE = 'sum(rate (container_network_receive_bytes_total{image!="",name=~"^k8s_.*", instance="' + NODE_NAME + '"}[5m]))'
	QUERY_TRANSMIT = 'sum(rate (container_network_transmit_bytes_total{image!="",name=~"^k8s_.*", instance="' + NODE_NAME + '"}[5m]))'
	network = get_network_usage(QUERY_RECEIVE, QUERY_TRANSMIT)
	usage_metrics['network I/O'] = []
	usage_metrics['network I/O'].append(network)
	
	metrics_node['resource usage'] .append(usage_metrics) 
	metrics_server["Servers"].append(metrics_node)
	counter = counter +1
    return metrics_server


#Collect metrics about the cluster state
def get_cluster_state():
	load =  OrderedDict()
	QUERY_count_node = 'sum(node_uname_info)'
	NODE_COUNT = get_query_result(QUERY_count_node)[0].get('value')[1]
	load['Number of nodes'] = NODE_COUNT
		
	QUERY_cpu_load= '(sum (rate (container_cpu_usage_seconds_total{id="/"}[5m])) / sum(machine_cpu_cores) )* 100'
   	CLUSTER_CPU_LOAD = get_query_result(QUERY_cpu_load)[0].get('value')[1]
	load['Cluster CPU load'] = str("%.2f" % float(CLUSTER_CPU_LOAD)) + "%"
	
	QUERY_memory_load = 'sum (container_memory_working_set_bytes{id="/"}) / sum (machine_memory_bytes) * 100'
	CLUSTER_RAM_LOAD = get_query_result(QUERY_memory_load)[0].get('value')[1]
	load['Cluster RAM load'] =  str("%.2f" % float(CLUSTER_RAM_LOAD)) + "%"
	
	QUERY_disk_load = 'sum (container_fs_usage_bytes{device=~"^/dev/[sv]d[a-z][1-9]$",id="/"}) / sum (container_fs_limit_bytes{device=~"^/dev/[sv]d[a-z][1-9]$",id="/"}) * 100'
	CLUSTER_disk_LOAD = get_query_result(QUERY_disk_load)[0].get('value')[1]
	load['Cluster storage load'] =  str("%.2f" % float(CLUSTER_disk_LOAD)) + "%"
	
	QUERY_unavailable= 'sum(kube_node_spec_unschedulable)'
	COUNT_UNAVAILABLE = get_query_result(QUERY_unavailable)[0].get('value')[1]
	load['Nodes Unavailable'] = COUNT_UNAVAILABLE
	
	QUERY_diskPressure= 'sum(kube_node_status_condition{condition="DiskPressure", status="true"})'
	COUNT_diskPressure = get_query_result(QUERY_diskPressure)[0].get('value')[1]
	load['Nodes OutOfDisk'] = COUNT_diskPressure
	
	QUERY_RAMPressure= 'sum(kube_node_status_condition{condition="MemoryPressure", status="true"})'
	COUNT_RAMPressure = get_query_result(QUERY_RAMPressure)[0].get('value')[1]
	load['Nodes OutOfMemory'] = COUNT_RAMPressure
	
	QUERY_CPUPressure= 'sum(kube_node_status_condition{condition="MemoryPressure", status="true"})'
	COUNT_CPUPressure = get_query_result(QUERY_CPUPressure)[0].get('value')[1]
	load['Nodes OutOfMemory'] = COUNT_CPUPressure
        return load


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
		
#Collect metrics about the deployed microservices	
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
			StoragelimitRange = core_api.read_namespaced_limit_range("storagelimits", namespace_name)
			limitStorage=  StoragelimitRange.spec.limits[0].max.values()[0]
			containers_list = pod_list.items[0].spec.containers
			total_limit_cpu = 0
			total_limit_mem = 0
			total_limit_disk = 0
			for container in containers_list:
				limits = container.resources.limits
				total_limit_cpu = total_limit_cpu + int(limits["cpu"][:-1])
				total_limit_mem = total_limit_mem + int(limits["memory"][:-2])	
			metrics_app["limit CPU"] = float(total_limit_cpu) / 1000
			metrics_app["limit RAM"] = humanbytes(total_limit_mem * 1024 * 1024)
			metrics_app["limit Storage"] = limitStorage
        		metrics_app['replicas'] = []
			counter = 1
			for pod in pod_list.items:
				dynamic =  OrderedDict()
				pod_name = pod.metadata.name
				dynamic['instance'] = str(counter) + "/" + str(replicas_count)
				counter = counter + 1
				dynamic['server'] = pod.spec.node_name
			
				QUERY_USAGE_cpu =  'sum(rate(container_cpu_usage_seconds_total{pod_name!="", image!="", pod_name=~"' + pod_name + '"}[5m]))'
				dynamic['CPU usage'] = get_cpu_usage(QUERY_USAGE_cpu, float (total_limit_cpu)/ 1000)
				
		   		QUERY_USAGE_memory ='sum(container_memory_working_set_bytes{pod_name!="", image!="", pod_name=~"' + pod_name +'"})' 
				dynamic['RAM usage'] = get_byte_usage(QUERY_USAGE_memory, total_limit_mem * 1024 * 1024)
					
				QUERY_USAGE_disk ='sum(container_fs_usage_bytes{pod_name!="", image!="", pod_name=~"' + pod_name + '"})'
				dynamic['disk usage'] =  get_byte_usage(QUERY_USAGE_disk, float(limitStorage[:-2]) * 1024 * 1024 * 1024)
				
				#Network usage
				network =  OrderedDict()
				QUERY_RECEIVE = 'rate (container_network_receive_bytes_total{image!="", pod_name="' + pod_name + '"}[5m])'
				QUERY_TRANSMIT = 'rate (container_network_transmit_bytes_total{image!="", pod_name="' + pod_name + '"}[5m])'
				network = get_network_usage(QUERY_RECEIVE, QUERY_TRANSMIT)
				dynamic['network I/O'] = []
				dynamic['network I/O'].append(network)
				
				metrics_app['replicas'].append(dynamic)
			dict_to_file['Microservices'].append(metrics_app)
	return dict_to_file

	
def get_cpu_usage(QUERY_USAGE_cpu, CPU_CAPACITY):
	CPU_USAGE = get_query_result(QUERY_USAGE_cpu)[0].get('value')[1]
	QUERY_USAGE_cpu_percentage = (float(CPU_USAGE) / float (CPU_CAPACITY))*100
	return str ("%.2f" % float(CPU_USAGE)) + " (" + str(  "%.2f" % QUERY_USAGE_cpu_percentage) + "%)" 
	
def get_byte_usage(QUERY_USAGE, CAPACITY):	
	USAGE = get_query_result(QUERY_USAGE)[0].get('value')[1]
	QUERY_USAGE_percentage = (float(USAGE) / float(CAPACITY)) * 100 
	return  str(humanbytes(USAGE))  + " (" + str( "%.2f" % QUERY_USAGE_percentage) + "%)"
		

def get_network_usage(QUERY_RECEIVE, QUERY_TRANSMIT):
	network_usage =  OrderedDict()
	NETWORK_RECEIVE = "%.2f" % float(get_query_result(QUERY_RECEIVE)[0].get('value')[1])
	network_usage['received bytes'] = humanbytes(NETWORK_RECEIVE)
	
	NETWORK_TRANSMIT = "%.2f" % float(get_query_result(QUERY_TRANSMIT)[0].get('value')[1])
	network_usage['sent bytes'] = humanbytes(NETWORK_TRANSMIT)
	return network_usage
	

#Get Prometheus IP address and port from the platform
def get_prometheus_URL():
 	global PROMETHEUS_URL	
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
	get_cluster_metrics()
