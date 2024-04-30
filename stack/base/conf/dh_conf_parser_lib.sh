#!/bin/bash

set -euo pipefail

DH_CONF_FILE="/etc/datahangar/datahangar.conf"

#Get data pipelines from conf file
PIPELINES="$(cat ${DH_CONF_FILE} | grep -E "pipeline\..*enabled:.*$" | sed 's/\.enabled:.*$//g')"

#$1: key
__get_val(){
	VAL="$(cat ${DH_CONF_FILE} | grep ${1} | sed "s/^${1}:\s*//g"| sed 's/^"\(.*\)"\s*$/\1/')"
	echo ${VAL}
}

#$1: pipeline
get_pipeline_enabled(){
	echo $(__get_val "$1.enabled")
}

#$1: pipeline
get_pipeline_desc(){
	echo $(__get_val "$1.description")
}

#$1: pipeline
get_pipeline_data_profiles(){
	echo $(__get_val "$1.dataProfiles")
}

#$1: pipeline
get_pipeline_kafka_nfacctd_output_topic(){
	echo $(__get_val "$1.kafka.nfacctdOutputTopic")
}

#$1: pipeline
get_pipeline_kafka_db_ingestion_topic(){
	echo $(__get_val "$1.kafka.dbIngestionTopic")
}
print_pipelines(){
	for PIPELINE in ${PIPELINES}; do
		echo "=== ${PIPELINE} ==="
		echo "Enabled: $(get_pipeline_enabled ${PIPELINE})"
		echo "Desc: $(get_pipeline_desc ${PIPELINE})"
		echo "Data Profiles: $(get_pipeline_data_profiles ${PIPELINE})"
		echo "Kafka nfacctd output topic: $(get_pipeline_kafka_nfacctd_output_topic ${PIPELINE})"
		echo "Kafka DB ingestion topic: $(get_pipeline_kafka_db_ingestion_topic ${PIPELINE})"
		echo ""
	done
}

if [ "${BASH_SOURCE[0]}" -ef "$0" ]; then
	print_pipelines
fi
