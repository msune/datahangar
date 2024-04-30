#!/bin/bash

set -Eeuo pipefail

#
# This script generated nfacctd configuration based on several inputs:
#
# * datahangar configuration files. Inputs are the pipelines defined, dataProfiles
#   Kafka topics etc.
# * Kafka secrets
#

NFACCTD_CONF_FILE=/etc/pmacct/nfacctd.conf

##DataHangar parsing utilities
source /etc/datahangar/dh_conf_parser_lib.sh

patch_librdkafka_conf(){
	sed "s/__KAFKA_USERNAME__/${KAFKA_USERNAME}/g" /etc/pmacct/librdkafka.conf.template > /etc/pmacct/librdkafka.conf
	sed -i "s/__KAFKA_PASSWORD__/${KAFKA_PASSWORD}/g" /etc/pmacct/librdkafka.conf
}

#$1: pipeline
nfacctd_aggregate_dataprofiles(){
	DATA_FIELDS=""
	PROFILES=$(get_pipeline_data_profiles $1 | sed 's/,/ /g')
	for DP in ${PROFILES}; do
		if [[ "${DP}" =~ "net.raw." ]]; then
			#Raw field
			DATA_FIELDS="${DATA_FIELDS}, $(echo ${DP} | sed 's/^net\.raw\.//g')"
			continue
		fi

		DP_FILE=/etc/datahangar/data-profiles/${DP}
		if [[ ! -f ${DP_FILE} ]]; then
			echo "ERROR: unable to load profile '${DP}' for pipeline '$1'. Aborting!"
			exit 1
		fi
		DP_CONTENTS=$(cat ${DP_FILE})
		DATA_FIELDS="${DATA_FIELDS}, ${DP_CONTENTS}"
	done

	#Return and remove trailing ,
	echo "${DATA_FIELDS}" | sed 's/\s*,\s*$//g' | sed 's/^\s*,\s*//g'
}

#$1: pipeline
nfacctd_conf_add_pipeline(){
	if [[  "$(get_pipeline_enabled $1)" != "true" ]]; then
		echo "![Autogen] DataHangar pipeline '${1}' DISABLED" >> ${NFACCTD_CONF_FILE}
		return;
	fi
	echo "" >> ${NFACCTD_CONF_FILE}
	echo "![Autogen] DataHangar pipeline '${1}'" >> ${NFACCTD_CONF_FILE}
	ID="${1}" #(echo ${1} | sed 's/pipeline\./pipeline-/g')"
	echo "![Autogen] Id: ${ID}" >> ${NFACCTD_CONF_FILE}
	echo "![Autogen] Description: '$(get_pipeline_desc ${1})'" >> ${NFACCTD_CONF_FILE}
	KAFKA_TOPIC=$(get_pipeline_kafka_nfacctd_output_topic ${1})
	if [[ "${KAFKA_TOPIC}" =~ "ERROR: " || "${KAFKA_TOPIC}" == "" ]]; then
		echo "${KAFKA_TOPIC}"
		echo "ERROR: unable to aggregate dataprofiles for ${1}. Aborting!"
		exit 1
	fi
	echo "kafka_topic[${ID}]: ${KAFKA_TOPIC}" >> ${NFACCTD_CONF_FILE}
	echo "kafka_config_file[${ID}]: /etc/pmacct/librdkafka.conf" >> ${NFACCTD_CONF_FILE}
	echo "kafka_broker_host[${ID}]: kafka-headless-service" >> ${NFACCTD_CONF_FILE}
	echo "kafka_broker_port[${ID}]: 9092" >> ${NFACCTD_CONF_FILE}
	echo "kafka_refresh_time[${ID}]: 1" >> ${NFACCTD_CONF_FILE}
	AGGR=$(nfacctd_aggregate_dataprofiles ${1})
	if [[ "${AGGR}" =~ "ERROR: " || "${AGGR}" == "" ]]; then
		echo "${AGGR}"
		echo "ERROR: unable to aggregate dataprofiles for ${1}. Aborting!"
		exit 1
	fi
	echo "aggregate[${ID}]: ${AGGR}" >> ${NFACCTD_CONF_FILE}
	echo "" >> ${NFACCTD_CONF_FILE}
}

##Base nfacctd from template
cat ${NFACCTD_CONF_FILE}.template > ${NFACCTD_CONF_FILE}

##Create a Kafka plugin instance per pipeline
KAFKA_PIPELINE_INSTANCES=""
for PIPELINE in ${PIPELINES}; do
	KAFKA_PIPELINE_INSTANCES="${KAFKA_PIPELINE_INSTANCES}kafka[${PIPELINE}],"
done

#Remove trailing comma
KAFKA_PIPELINE_INSTANCES="$(echo ${KAFKA_PIPELINE_INSTANCES} | sed 's/\s*,\s*$//g')"
echo "!Kafka Plugin instances" >> ${NFACCTD_CONF_FILE}
echo "plugins: ${KAFKA_PIPELINE_INSTANCES}" >> ${NFACCTD_CONF_FILE}

##Add nfacctd sections for each pipeline
for PIPELINE in ${PIPELINES}; do
	nfacctd_conf_add_pipeline ${PIPELINE}
done

# Finally patch librdkafka
patch_librdkafka_conf

cat /etc/pmacct/nfacctd.conf
