#!/bin/bash

echo "Starting model generation..."

# generating 'commons'
fastapi-codegen --input common-v1.yaml --model-file common_v1.py --output _tmp
mv _tmp/common_v1.py ../src/model/api/generated
rm _tmp/*
rmdir _tmp

# generating 'banking-api'
fastapi-codegen --input banking-api-v1.yaml --model-file banking_api_v1.py --output _tmp
mv _tmp/banking_api_v1.py ../src/model/api/generated
rm _tmp/*
rmdir _tmp