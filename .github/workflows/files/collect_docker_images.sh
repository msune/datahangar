#!/bin/bash

#
# Look for all images to be able to cache them as part of the pipeline
#
# $1 root folder
YAML_FILES=`find $1 -name "*.yaml" -o -name "*.yaml"`

IMAGES=""
for FILE in ${YAML_FILES}; do
	IMAGES="${IMAGES} $(cat ${FILE} | grep "image:" | sed 's/\s*[-]*\s*image:\s*//g' | tr -d '"')"
done

echo $(echo ${IMAGES} | sed 's/\s/\n/g' | sort | uniq)
