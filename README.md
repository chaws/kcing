# KernelCI New Generation (visualization) - KCING

This repository contains scripts and configuration files to support prototype to a visualization tool using ELK for displaying [kernelci.org](https://kernelci.org) data. ELK stands for ElasticSearch, Logstash and Kibana.

![KernelCI Workflow](img/KernelCI_Workflow.png "KernelCI Workflow")

The image above briefly shows the workflow of kernelci's build & boot infrastructure. `KernelCI Builders` are volunteer jenkins workers spreaded across the globe, running [kernelci-core](https://github.com/kernelci/kernelci-core) code to compile lots of Kernels. A master jenkins instance is run by kernelci maintainers to distribuite build workload. Once each builder has finished its job, it sends `api.kernelci.org/upload` the object file along with a `build.json` file containing metadata about the build just generated. The build is then saved into a MongoDB database and its artifacts saved in `storage.kernelci.org`.

With a build in hand, kernelci's jenkins will queue builds for booting/testing throughout [available labs](https://github.com/kernelci/kernelci-core/blob/master/labs.ini). Most of labs are running [LAVA](https://lavasoftware.org/). Each lab will then boot a build and run tests defined by kernelci maintainers. Lastly, labs will return boot/test results back to `api.kernelci.org/callback`, which saves to MongoDB and record results files named like `lava-json-board-name.json` into `storage.kernelci.org`. Once that loop has finished, the build and boot are publicaly available at `kernelci.org`.

## KCING

KCING currently acts as an alternative visualization tool for kernelci's jobs. Note from the image above that both `build.json` and `lava-*.json` files are also being sent to an extra stack. This is being worked out with kernelci maintainers to be available in the future. The files are received by a [Losgstash](https://www.elastic.co/products/logstash) instance, configured with [kcing_pipeline.conf](kcing_pipeline.conf).

During prototyping stage, we wrote `kcing.py` to emulate KernelCI Builders and Labs. It'll, daily, go to kernelci ajax api, query the past two days worth of boots and builds and use it to feed a running ElasticSearch instance. 

### List of available commands

- `./kcing.py feed_es [--how-many=N]` will attempt to download N (or last two days worth of data) lava files and builds from kernelci and submit them to a running ELK stack
- `./kcing.py gen_samples [--sample-size=N]` will attempt to download N (or last two days worth of data) lava files and builds recorded in kernelci website. Samples are stored in `samples` directory. 
- `./kcing.py test` will run available tests. For now, only `kernelci` tests are available

## Important parts of this repo

- `kcing.py` is the main file, responsible for calling other scripts
- `kernelci.py` contains all necessary code to retrieve boots and builds straight from kernelci.org while our patch allowing multiple callbacks isn't running on production kernelci.
- `feed_es.py` contains necessary scripting to get data sent to ES, overviewing LS/ES limitations

## Settings

Important settings that make kcing work properly are described below, they're present in `settings.py`. Please note that `settings.py` should NOT be changed, instead, write your settings to `local_settings.py`. Also it's worth mentioning that all the settings are also read from environment variables (overwrites `local_settings.py` and `settings.py`):

### KernelCI settings
- `KCI_HOST` host where to query data from kernelci, defaults to `kernelci`
- `KCI_SCHEME` scheme to use when making requests to `KCI_HOST`, defaults to `https`

### Logstash/ElasticSearch settings
- `ES_LAVA` and `ES_BUILD` urls where to post lava and build data to ES, respectivelly. This is usually a running Logstash instance, using [kcing_pipeline.conf](kcing_pipeline.conf) pipeline configuration.
- `ES_MAX_RETRIES` how many retries to post data to `ES_LAVA` or `ES_BUILD`, defaults to `3`
- `ES_LOAD_INTERVAL` is the number of seconds to sleep after every `LS_PIPELINE_BATCH_SIZE` objects are sent to ES, thus reducing load on logstash, defaults to `5`
- `LS_HOME` home is logstash's home folder, needed when customizing logstash `pipelines.yml` file
- `LS_QUEUE_TYPE` is lostash's queueing type: persisted (disk) or memory (ram), defaults to `persisted`
- `LS_PATH_CONFIG` is the pipeline configuration file path, defaults to [kcing_pipeline.conf](kcing_pipeline.conf)
- `LS_QUEUE_MAX_EVENTS` is the maximum number of unread events from the queue when `LS_QUEUE_TYPE` is set to `persisted`, defaults to `200`
- `LS_PIPELINE_BATCH_SIZE` is the maximum number of events a worker will collect from `inputs` section of the configuration file before starting `filters` and `outputs`, defaults to `100`
- `DRP_DAYS` is the number of days to keep processed data, defaults to `3`. 


## KernelCI matrix

As kernelci is intended to build, boot and test the maximum combinations possible of Linux Kernel trees. Each tree has selected branchs to be monitored.  

## What this is not

KCING is NOT intended to replace the kernelci builders, labs, regressions and bisections.
