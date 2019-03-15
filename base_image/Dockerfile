# This image will contain all necessary software before we can actually create kcing

# https://hub.docker.com/r/sebp/elk/dockerfile
FROM sebp/elk

ENV KIBANA_PACKAGE kibana-7.0.0-beta1-linux-x86_64.tar.gz
ENV ES_PACKAGE elasticsearch-7.0.0-beta1-linux-x86_64.tar.gz

RUN apt-get install -y python3-pip git \
 && rm -rf ${ES_HOME}/* \
 && curl -O https://artifacts.elastic.co/downloads/elasticsearch/${ES_PACKAGE} \
 && tar xzf ${ES_PACKAGE} -C ${ES_HOME} --strip-components=1 \
 && echo >> /etc/elasticsearch/elasticsearch.yml \
 && echo "discovery.type: single-node" >> /etc/elasticsearch/elasticsearch.yml \
 && rm -f ${ES_PACKAGE} \
 && rm -rf ${KIBANA_HOME}/* \
 && curl -O https://artifacts.elastic.co/downloads/kibana/${KIBANA_PACKAGE} \
 && tar xzf ${KIBANA_PACKAGE} -C ${KIBANA_HOME} --strip-components=1 \
 && echo >> /opt/kibana/config/kibana.yml \
 && echo 'server.host: "0.0.0.0"' >> /opt/kibana/config/kibana.yml \
 && chown -R kibana:kibana ${KIBANA_HOME}/* \
 && rm -f ${KIBANA_PACKAGE}
