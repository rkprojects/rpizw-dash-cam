#!/bin/bash

for py in src/*.py
do 
	python3 -m py_compile $py
	if [ $? -ne 0 ]; then
		break
	fi
done

