# KernelCI New Generation (visualization) - KCING

This repository contains scripts and configuration files to support prototype to a visualization tool using ELK for displaying [kernelci.org](https://kernelci.org) data. ELK stands for ElasticSearch, Logstash and Kibana.

![KernelCI Workflow](img/KernelCI_Workflow.png "KernelCI Workflow")

The image above briefly shows the workflow of kernelci's build & boot infrastructure. `KernelCI Builders` are volunteer jenkins workers spreaded across the globe, running [kernelci-core](https://github.com/kernelci/kernelci-core) code to compile lots of Kernels. Once each builder has finished its job, it sends `api.kernelci.org/upload` the object file along with a `build.json` file containing metadata for the job just executed. The build is then saved into a MongoDB database and its artifacts saved in `storage.kernelci.org`.

With a build in hand, kernelci's jenkins will queue builds for booting/testing throughout [available labs](https://github.com/kernelci/kernelci-core/blob/master/labs.ini). Most of labs are running [LAVA](https://lavasoftware.org/). Each lab will then boot a build and run tests stablished by kernelci developers. Lastly, labs will call return boot/test results back to `api.kernelci.org/callback`, which saves to MongoDB and record results files named like `lava-json-board-name.json` into `storage.kernelci.org`. Once that loop has finished, the build and boot are publicaly available at `kernelci.org`.

## KCING

KCING currently acts as an alternative visualization tool for kernelci's jobs. Note from the image above that both `build.json` and `lava-*.json` files are also being sent to an extra stack. This is being worked out with kernelci developers to be available in the future. The files are received by a [Losgstash](https://www.elastic.co/products/logstash) instance, configured with [kcing_pipeline.conf]()

## Important parts of this repo

- `kcing.py` is the main file, responsible for calling other scripts
- `kernelci.py` contains all necessary code to retrieve boots and builds straight from kernelci.org while our patch allowing multiple callbacks isn't running on production kernelci.
- `feed_es.py` contains necessary scripting to get data sent to ES, overviewing LS/ES limitations


## KernelCI matrix

As kernelci is intended to build, boot and test the maximum combinations possible of Linux Kernel trees. Each tree has selected branchs to be monitored.  

## What this is not

KCING is NOT intended to replace the kernelci builders, labs, regressions and bisections.
