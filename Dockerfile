# From ElasticSearch documentation, you need to have vm.max_map_count=262144
# in order for ElasticSearch to work. Set it by running `sysctl -w vm.max_map_count=262144`
# source: https://www.elastic.co/guide/en/elasticsearch/reference/current/vm-max-map-count.html#vm-max-map-count

# https://hub.docker.com/r/sebp/elk/dockerfile
FROM sebp/elk

# How many samples to add to the container
ARG sample_size=50
ARG SAMPLE_SIZE=$sample_size

# Configure kcing repo
ENV KCING_HOME /opt/kcing
ENV LS_HOME ${LOGSTASH_HOME}

# Copy kcing
RUN mkdir -p ${KCING_HOME}
COPY . ${KCING_HOME}

# Configure kcing
WORKDIR ${KCING_HOME}
RUN set -x \
 && apt-get install -y python3-pip \
 && pip3 install -r requirements.txt \
 && service elasticsearch start \
 && ./scripts/wait_elasticsearch.sh \
 && ./kcing.py setup_es \
 && ./kcing.py setup_kbn \
 && ./kcing.py setup_ls \
 && service logstash start \
 && ./scripts/wait_logstash.sh \
 && rm -f kcing.db \
 && (./kcing.py feed_es --how-many ${SAMPLE_SIZE} || exit 0)

# Our logstash pipelines ports
EXPOSE 5601 9200 8337 8338 8007

CMD [ "/usr/local/bin/start.sh" ]
